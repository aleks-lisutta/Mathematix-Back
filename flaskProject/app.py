import logging
import math
import random
import traceback
from datetime import datetime
from unittest.mock import MagicMock

from flask import Flask, request, jsonify, make_response
from collections.abc import Iterable

from flask_pony import Pony
from flask_cors import CORS
from pony.orm import *
from scipy.optimize import minimize_scalar
import json

import pony.orm as pony
from flask import Response

from urllib.parse import urlparse, parse_qs
from flask import jsonify

import numpy as np
from pony_database_facade import DatabaseFacade

# app = Flask(__name__)
# app.logger.setLevel(logging.DEBUG)
# CORS(app)
# p = Pony(app)
# print(p)
# DB = p.db
# print(DB)
# DB.bind(provider='sqlite', filename='dbtest', create_db=True)

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)
CORS(app)
DB = pony.Database()
Pony(app)

DB.bind(provider='sqlite', filename='dbtest.sqlite', create_db=True)

DATATYPE_SIZE = 3
QUESTIONTYPE_SIZE = 4
QUESTIONS_TO_GENERATE = 10
MAX_RANGE = 10
MIN_RANGE = -10


class User(DB.Entity):
    name = PrimaryKey(str)
    password = Required(str)
    type = Required(int)
    teaching = Set('Cls', reverse='teacher', cascade_delete=False)
    inClass = Set('Cls_User', cascade_delete=False)
    activeUnits = Set("ActiveUnit", reverse='student')


class Cls(DB.Entity):
    name = PrimaryKey(str)
    teacher = Required(User, reverse='teaching')
    students = Set('Cls_User')
    hasUnits = Set('Unit', reverse='cls', cascade_delete=False)


class Cls_User(DB.Entity):
    cls = Required(Cls)
    user = Required(User)
    approved = Required(bool)
    PrimaryKey(cls, user)


class Unit(DB.Entity):
    name = Required(str)
    cls = Required(Cls, reverse='hasUnits')
    desc = Optional(str)
    template = Required(str)
    Qnum = Required(str)
    maxTime = Required(str)
    subDate = Required(str)
    instances = Set('ActiveUnit', reverse='unit')
    order = Required(int)
    next = Optional(str)
    PrimaryKey(name, cls)


class Question(DB.Entity):
    id = Required(int)
    question_preamble = Required(str)
    question = Required(str)
    answer1 = Required(str)
    answer2 = Required(str)
    answer3 = Required(str)
    answer4 = Required(str)
    correct_ans = Required(int)
    active_unit = Required('ActiveUnit', reverse='questions')
    solved_correctly = Optional(bool)
    PrimaryKey(active_unit, id)


class ActiveUnit(DB.Entity):
    inProgress = Required(bool)
    attempt = Required(int)
    questions = Set('Question', reverse='active_unit')
    unit = Required(Unit, reverse='instances')
    student = Required(User, reverse='activeUnits')
    grade = Optional(int)
    consecQues = Required(int)
    quesAmount = Required(int)
    currentQuestion = Required(int)
    totalCorrect = Required(int)
    lastTimeAnswered = Optional(str)
    PrimaryKey(unit, student, attempt)


DB.generate_mapping(create_tables=True)

activeControllers = {}


@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'


def isLogin(username):
    return True
    if username not in activeControllers.keys():
        # print(username, activeControllers.keys())
        return False
    return True


@db_session
def isTeacher(username):
    user = User.get(name=username)
    if user is None:
        return False  # User does not exist
    return user.type == 1


def checkValidUsername(username):
    try:
        with db_session:
            return User[username] is None
    except Exception as e:
        return str(e), 400


def checkValidPassword(password):
    return len(password) > 2


def makeUser(username, password, type):
    try:
        with db_session:
            User(name=username, password=password, type=type)
            commit()
            return None
    except Exception as e:
        return str(e)


def is_legal_template(template: str):
    parts = template.split(',')
    data_type = int(parts[0])
    question_type = int(parts[1])
    if (not ((data_type >= 0 and data_type < DATATYPE_SIZE) and (
            question_type >= 0 and question_type < QUESTIONTYPE_SIZE))):
        return False
    # todo check the tuples are correct
    return True


@app.route('/register')
def register():
    username = request.args.get('username')
    password = request.args.get('password')
    typ = request.args.get('typ')
    if not checkValidUsername(username) or not checkValidPassword(password):
        return "invalid username or password", 400
    return register_buisness(username, password, typ)


def register_buisness(username, password, typ):
    ans = makeUser(username, password, typ)
    if ans is None:
        return username + " " + password + " " + typ, 200
    return ans, 400


def checkUserPass(username, password):
    try:
        with db_session:
            result = User[username]
            if result:
                return result.password == password
            return False
    except Exception as e:
        print("in excpetion and the user is")
        print(e)
        return False


def checkType(username):
    try:
        with db_session:
            result = User[username]
            if result.type:
                return result.type
            return 0
    except Exception:
        return 0


#
def loadController(username):
    type = checkType(username)
    if type == 1:
        activeControllers[username] = teacherCont(username)
    elif type == 2:
        activeControllers[username] = userCont(username)
    return


@app.route('/login')
def login():
    username = request.args.get('username')
    password = request.args.get('password')
    if not checkUserPass(username, password):
        return "invalid username or password", 400
    return login_buisness(username, password)


def login_buisness(username, password):
    loadController(username)
    if isinstance(activeControllers[username], teacherCont):
        return str(1) + " " + username
    return str(2) + " " + username


@app.route('/changePassword')
def change_password():
    username = request.args.get('username')
    password = request.args.get('password')
    new_password = request.args.get('newPassword')
    if not isLogin(username):
        return "user " + username + "not logged in.", 400
    try:
        with db_session:
            u = User[username]
            if u.password == password:
                u.password = new_password
                return "successful password change", 200
            else:
                return "wrong username or password", 400
    except Exception:
        return "wrong username or password", 400


@app.route('/logout')
def logout():
    username = request.args.get('username')
    return logout_buisness(username)


@app.route('/logout')
def logout_buisness(username):
    if username in activeControllers.keys():
        # print(activeControllers)
        activeControllers.pop(username)
        # print(activeControllers)
    return username + " " + str(len(activeControllers))


@app.route('/openClass')
def openClass():
    teacherName = request.args.get('teacher')
    if not isLogin(teacherName):
        return "user " + str(teacherName) + "not logged in.", 400
    className = request.args.get('className')
    try:
        return openClass_buisness(teacherName, className)
    except Exception as e:
        return str(e), 400


def openClass_buisness(teacherName, className):
    try:
        with db_session:
            t = User[teacherName]
            if t.type == 1:
                Cls(name=className, teacher=User[teacherName])
                return "successful", 200
            return "failed wrong type", 400
    except Exception as e:
        return str(e), 400


def makeClass(teacherName, className):
    with db_session:
        t = User[teacherName]
        if t.type == 1:
            Cls(name=className, teacher=User[teacherName])
            return "successful", 200
        return "failed wrong type", 400


@app.route('/removeClass')
def removeClass():
    teacherName = request.args.get('teacher')
    className = request.args.get('className')
    if not isLogin(teacherName):
        return "user " + str(teacherName) + "not logged in.", 400
    try:
        return removeClass_buisness(teacherName, className)
    except Exception as e:
        return str(e), 400


def removeClass_buisness(teacherName, className):
    if not isTeacher(teacherName):
        return "user " + str(teacherName) + " is not a teacher", 400
    try:
        with db_session:
            t = User[teacherName]
            c = Cls[className]
            if c.teacher == t:
                c.delete()
                return "successful", 200
            return "failed", 400
    except Exception as e:
        return str(e), 400


@app.route('/editClass')
def editClass():
    teacherName = request.args.get('teacher')
    className = request.args.get('className')
    newClassName = request.args.get('newClassName')
    if not isLogin(teacherName):
        return "user " + str(teacherName) + "not logged in.", 400
    try:
        return editClass_buisness(teacherName, className, newClassName)
    except Exception as e:
        return str(e), 400


def editClass_buisness(teacherName, className, newClassName):
    if not isTeacher(teacherName):
        return "user " + str(teacherName) + " is not a teacher", 400
    try:
        with db_session:
            t = User[teacherName]
            c = Cls[className]
            if c.teacher == t:
                Cls(name=newClassName, teacher=User[teacherName], students=c.students, hasUnits=c.hasUnits)
                c.delete()
                return "successful", 200
            return "failed", 400
    except Exception as e:
        return str(e), 400


@app.route('/quickEditUnit')
def quickEditUnit():
    unitName = request.args.get('unitName')
    className = request.args.get('className')
    newDesc = request.args.get('newDesc')
    newUnitName = request.args.get('newUnitName')
    teacherName = request.args.get('teacher')
    if not isLogin(teacherName):
        return "user " + str(teacherName) + "not logged in.", 400
    try:
        with db_session:
            c = Cls[className]
            u = Unit[unitName, c]
            ins = u.instances  #
            order = u.order
            nex = u.next
            temp = u.template
            Qnum = u.Qnum
            maxTime = u.maxTime
            subDate = u.subDate
            if newUnitName != unitName:
                Unit(cls=c, name=newUnitName, desc=newDesc, template=temp, Qnum=Qnum, maxTime=maxTime, subDate=subDate,
                     instances=ins, order=order, next=nex)
                Unit[unitName, c].delete()
            else:
                u.set(desc=newDesc)
            commit()
        return "successful", 200
    except Exception as e:
        print(e)
        return str(e), 400


@app.route('/editUnit')
def editUnit():
    unitName = request.args.get('unitName')
    className = request.args.get('className')
    newUnitName = request.args.get('newUnitName')
    Qnum = request.args.get('newQnum')
    maxTime = request.args.get('newMaxTime')
    subDate = request.args.get('newSubDate')
    newDesc = request.args.get('newDesc')
    teacherName = request.args.get('teacher')
    if not isLogin(teacherName):
        return "user " + str(teacherName) + "not logged in.", 400
    try:
        return editUnit_buisness(unitName, className, newUnitName, Qnum, maxTime, subDate, newDesc, teacherName)
    except Exception as e:
        return str(e), 400


def editUnit_buisness(unitName, className, newUnitName, Qnum, maxTime, subDate, newDesc, teacherName):
    try:
        with db_session:
            c = Cls[className]
            u = Unit[unitName, c]
            ins = u.instances
            order = u.order
            nex = u.next
            temp = u.template
            if not isTeacher(teacherName):
                return "user " + str(teacherName) + " is not a teacher", 400
            if newUnitName != unitName:
                Unit(cls=c, name=newUnitName, desc=newDesc, template=temp, Qnum=Qnum, maxTime=maxTime, subDate=subDate,
                     instances=ins, order=order, next=nex)
                Unit[unitName, c].delete()
            else:
                u.set(desc=newDesc, Qnum=Qnum, maxTime=maxTime, subDate=subDate)
            return {"message": "successful"}, 200
    except Exception as e:
        print(e)
        return str(e), 400


@app.route('/removeUnit')
def removeUnit():
    unitName = request.args.get('unitName')
    className = request.args.get('className')
    teacherName = request.args.get('teacher')
    if not isLogin(teacherName):
        return "user " + str(teacherName) + "not logged in.", 400
    try:
        return removeUnit_buisness(unitName, className, teacherName)
    except Exception as e:
        return str(e), 400


def removeUnit_buisness(unitName, className, teacherName):
    try:
        with db_session:
            u = Unit[unitName, Cls[className]]
            u.delete()
            return "successful", 200
    except Exception as e:
        print(e)
        return str(e), 400


@app.route('/getAllClassesNotIn')
def getAllClassesNotIn():
    ret = []
    student = request.args.get('username')
    if not isLogin(student):
        return "user " + student + "not logged in.", 400
    id = 0

    try:
        with db_session:
            already_in = list()
            for aUnit in Cls_User.select(user=student):
                already_in.append(aUnit.cls.name)
            for singleClass in Cls.select(lambda p: True):
                if singleClass.name in already_in:
                    continue
                single_obj = dict()
                id += 1
                single_obj["id"] = id
                single_obj["className"] = singleClass.name
                single_obj["teacher"] = singleClass.teacher.name
                ret.append(single_obj)

        return jsonify(ret)
    except Exception as e:
        return str(e), 400


def getAllClassesNotIn_Buisness(student):
    ret = []
    if not isLogin(student):
        return "user " + student + "not logged in.", 400
    id = 0

    try:
        with db_session:
            already_in = list()
            for aUnit in Cls_User.select(user=student):
                already_in.append(aUnit.cls.name)
            for singleClass in Cls.select(lambda p: True):
                if singleClass.name in already_in:
                    continue
                single_obj = dict()
                id += 1
                single_obj["id"] = id
                single_obj["className"] = singleClass.name
                single_obj["teacher"] = singleClass.teacher.name
                ret.append(single_obj)

        return jsonify(ret)
    except Exception as e:
        return str(e), 400


@app.route('/getAllClassesWaiting')
def getAllClassesWaiting():
    ret = []
    student = request.args.get('username')
    if not isLogin(student):
        return "user " + student + "not logged in.", 400
    id = 0

    try:
        with db_session:
            for aUnit in Cls_User.select(user=student, approved=False):
                single_obj = dict()
                id += 1
                single_obj["id"] = id
                single_obj["className"] = aUnit.cls.name
                single_obj["teacher"] = aUnit.cls.teacher.name
                ret.append(single_obj)

        return jsonify(ret)
    except Exception as e:
        return str(e), 400


@app.route('/registerClass')
def registerClass():
    studentName = request.args.get('student')
    className = request.args.get('className')
    if not isLogin(studentName):
        return "user " + studentName + "not logged in.", 400
    try:
        return registerClass_buisness(studentName, className)
    except Exception as e:
        print(e)
        return str(e), 400


@app.route('/registerClass')
def registerClass_buisness(studentName, className):
    with db_session:
        c = Cls[className]
        u = User[studentName]
        c_u = Cls_User(cls=c, user=u, approved=False)

        commit()
        return "successful", 200


@app.route('/removeRegistrationClass')
def removeRegistrationClass():
    studentName = request.args.get('student')
    className = request.args.get('className')
    if not isLogin(studentName):
        return "user " + studentName + "not logged in.", 400
    try:
        return removeRegistrationClass_Buisness(studentName, className)
    except Exception as e:
        return str(e), 400


def removeRegistrationClass_Buisness(studentName, className):
    with db_session:
        c = Cls[className]
        u = User[studentName]
        Cls_User.select(cls=c, user=u).delete(bulk=True)
        commit()
        return "successful", 200


@app.route('/getUnapprovedStudents')
def getUnapprovedStudents():
    teacher = request.args.get('teacher')
    if not isLogin(teacher):
        return "user " + teacher + "not logged in.", 400
    ret = []
    id = 0
    try:
        with db_session:
            for singleClass in Cls.select(teacher=teacher):
                for unapproveRequest in Cls_User.select(cls=singleClass):
                    if (unapproveRequest.approved == False):
                        single_obj = dict()
                        id += 1
                        single_obj["id"] = id
                        single_obj["secondary"] = singleClass.name
                        single_obj["primary"] = unapproveRequest.user.name
                        ret.append(single_obj)
        return jsonify(ret)
    except Exception as e:
        return str(e), 400


@app.route('/approveStudentToClass')
def approveStudentToClass():
    teacherName = request.args.get('teacher')
    studentName = request.args.get('student')
    className = request.args.get('className')
    approve = request.args.get('approve')
    if not isLogin(teacherName):
        return "user " + teacherName + "not logged in.", 400
    try:
        return approveStudentToClass_buisness(teacherName, studentName, className, approve)
    except Exception as e:
        print(e)
        return str(e), 400


def approveStudentToClass_buisness(teacherName, studentName, className, approve):
    try:
        with db_session:
            c = Cls[className]
            u = User[studentName]
            if approve == "True":
                b = Cls_User[c, u]
                Cls_User[c, u].approved = True
                u.inClass.add(b)
                c.students.add(b)
            else:
                Cls_User[c, u].delete()
            return "successful", 200
    except Exception as e:
        print(e)
        return str(e), 400


@app.route('/removeFromClass')
def removeFromClass():
    studentName = request.args.get('student')
    className = request.args.get('className')
    if not isLogin(studentName):
        return "user " + studentName + "not logged in.", 400
    try:
        with db_session:
            c = Cls[className]
            u = User[studentName]
            u.inClass.remove(c)
            c.students.remove(u)
            commit()
            return "successful", 200
    except Exception as e:
        return str(e), 400


def teacherOpenUnit(unitName, teacherName, className, template, Qnum, maxTime, subDate, first, prev, desc):
    # if not is_legal_template(template):
    #    return "illegal template", 400
    try:
        with db_session:
            ord = 1
            if first != 'true':
                p = Unit[prev, Cls[className]]
                p.next = unitName
                ord = p.order + 1
            Unit(cls=Cls[className], name=unitName, desc=desc, template=template, Qnum=Qnum, maxTime=maxTime,
                 subDate=subDate,
                 order=ord)
            commit()
            return "success"
    except Exception as e:
        print(e)
        return str(e), 400


@app.route('/openUnit')
def openUnit():
    teacherName = request.args.get('teacher')
    desc = request.args.get('desc')
    unitName = request.args.get('unitName')
    className = request.args.get('className')
    template = request.args.get('template')
    Qnum = request.args.get('Qnum')
    maxTime = request.args.get('maxTime')
    subDate = request.args.get('subDate')
    first = request.args.get('first')
    prev = request.args.get('prev')

    if not isLogin(teacherName):
        return "user " + str(teacherName) + "not logged in.", 400

    result = teacherOpenUnit(unitName, teacherName, className, template, Qnum, maxTime, subDate, first, prev, desc)
    return result


@app.route('/getUnit')
def getUnit():
    unitName = request.args.get('unitName')
    className = request.args.get('className')
    teacherName = request.args.get('teacher')
    if not isLogin(teacherName):
        return "user " + str(teacherName) + "not logged in.", 400
    try:
        return getUnitName_buisness(unitName, className)
    except Exception as e:
        return str(e), 400


def getUnitName_buisness(unitName, className):
    try:
        with db_session:
            retUnit = Unit[unitName, Cls[className]]
            return retUnit.name
    except Exception as e:
        return str(e), 400


def getUnit_buisness(unitName, className):
    try:
        with db_session:
            retUnit = Unit[unitName, Cls[className]]
            return retUnit
    except Exception as e:
        return str(e), 400


@app.route('/deleteUnit')
def deleteUnit():
    unitName = request.args.get('unitName')
    className = request.args.get('className')
    teacherName = request.args.get('teacher')
    if not isLogin(teacherName):
        return "user " + str(teacherName) + "not logged in.", 400
    try:
        return deleteUnit_buisness(unitName, className, teacherName)
    except Exception as e:
        return str(e), 400


def deleteUnit_buisness(unitName, className, teacherName):
    try:
        with db_session:
            Unit[unitName, Cls[className]].delete()
            commit()
            return "deleted successfully"
    except Exception as e:
        return str(e), 400


@app.route('/getClassUnits')
def getClassUnits():
    className = request.args.get('className')
    teacherName = request.args.get('teacher')
    if not isLogin(teacherName):
        return "user " + str(teacherName) + "not logged in.", 400
    try:
        return getClassUnits_buisness(className, teacherName)
    except Exception as e:
        print(e)
        return str(e), 400


def getClassUnits_buisness(className, teacherName):
    try:
        with db_session:
            ret = []
            id = 0
            for aUnit in Cls[className].hasUnits:
                if not aUnit.order == 1:
                    continue
                single_obj = dict()
                id += 1
                single_obj["id"] = id
                single_obj["primary"] = aUnit.name
                single_obj["secondary"] = aUnit.desc
                single_obj["due"] = aUnit.subDate
                ret.append(single_obj)
            return ret
    except Exception as e:
        print(e)
        return str(e), 400


@app.route('/getClassesStudent')
def getClassesStudent():
    student = request.args.get('student')
    if not isLogin(student):
        return "user " + student + "not logged in.", 400
    try:
        with db_session:
            ret = []
            id = 0
            for aUnit in Cls_User.select(user=student, approved=True):
                single_obj = dict()
                id += 1
                single_obj["id"] = id
                single_obj["primary"] = aUnit.cls.name
                single_obj["secondary"] = "la la la"
                ret.append(single_obj)

            return jsonify(ret)
    except Exception as e:
        return str(e), 400


@app.route('/getClassesTeacher')
def getClassesTeacher():
    teacher = request.args.get('teacher')
    if not isLogin(teacher):
        return "user " + teacher + "not logged in.", 400
    try:
        with db_session:
            ret = []
            id = 0
            for aUnit in Cls.select(teacher=teacher):
                single_obj = dict()
                id += 1
                single_obj["id"] = id
                single_obj["primary"] = aUnit.name
                single_obj["secondary"] = "la la la"
                ret.append(single_obj)

            return jsonify(ret)
    except Exception as e:
        print(e)
        return str(e), 400


@app.route('/getUnitDetails')
def getUnitDetails():
    className = request.args.get('className')
    unitName = request.args.get('unitName')
    teacherName = request.args.get('teacher')
    if not isLogin(teacherName):
        return "user " + str(teacherName) + "not logged in.", 400
    try:
        return getUnitDetails_buisness(className, unitName, teacherName)
    except Exception as e:
        print(e)
        return str(e), 400


def getUnitDetails_buisness(className, unitName, teacherName):
    with db_session:
        unit = Unit.get(name=unitName, cls=className)
        if unit:
            return {
                "name": unit.name,
                "desc": unit.desc,
                "template": unit.template,
                "Qnum": unit.Qnum,
                "maxTime": unit.maxTime,
                "subDate": unit.subDate,
                "order": unit.order,
                "next": unit.next
            }
        else:
            return ""


def get_random_result(zero, up_down):
    if not up_down:
        x_a = random.randint(0, 3)
        x_b = random.randint(0, 3)
        a = random.randint(-10, 10) + x_a / 4
        b = random.randint(-10, 10) + x_b / 4
        if zero:
            return ((a, 0), (0, b))
        else:
            return (a, b)
    else:
        x_a = random.randint(0, 3)
        a = random.randint(-10, 10) + x_a / 4
        ans = dict()
        ans["up"] = "x > " + str(a)
        ans["down"] = "x < " + str(a)
        up_down = random.randint(0, 1)
        if (up_down):
            return (ans["up"] + " :עלייה" + ans["down"] + " :ירידה")
        else:
            return (ans["up"] + " :עלייה" + ans["down"] + " :ירידה")


def func_to_string(a, b, c):
    if b == 0 and c == 0:
        return "f(x) = {}*x^2".format(a)
    elif b == 0:
        return "f(x) = {}*x^2+{}".format(a, c)
    elif c == 0:
        return "f(x) = {}*x^2+{}*x".format(a, b)
    else:
        return "f(x) = {}*x^2+{}*x+{}".format(a, b, c)


def getQuadratic(a_min, a_max, b_min, b_max, c_min, c_max):
    a = 0
    while a == 0:
        a = random.randint(int(a_min), int(a_max))
    b = random.randint(int(b_min), int(b_max))
    c = random.randint(int(c_min), int(c_max))
    return a, b, c


def inc_dec(function_types, params):
    params = [int(p) for p in params]
    preamble = "מצא תחומי עלייה וירידה:"
    if ("linear" in function_types):
        m = 0
        b = 0
        while m == 0:
            m = random.randint(params[0], params[1])
        while b == 0:
            b = random.randint(params[2], params[3])
        if (b == 0):
            question_string = "y=" + str(m) + "x"
        else:
            question_string = ("y=" + str(m) + "x" + ('+' if b > 0 else "") + str(b))
        result2 = " " + get_random_result(False, True)
        result3 = " " + get_random_result(False, True)
        return (preamble, question_string, " תמיד עולה " if m > 0 else " תמיד יורד ", result2, result3,
                " תמיד עולה " if m < 0 else " תמיד יורד ", 0)
    if ("quadratic" in function_types):

        a, b, c = getQuadratic(params[0], params[1], params[2], params[3], params[4], params[5])

        ans = dict()
        result = find_min_max(a, b, c)
        if a < 0:
            ans["down"] = "x > " + str(result["maximum"]["x"])
            ans["up"] = "x < " + str(result["maximum"]["x"])
        else:
            ans["up"] = "x > " + str(result["minimum"]["x"])
            ans["down"] = "x < " + str(result["minimum"]["x"])

        question_string = funcString([a, b, c])

        result2 = get_random_result(False, True)
        result3 = get_random_result(False, True)
        result4 = get_random_result(False, True)

        up_down = random.randint(0, 1)
        if (up_down):
            return (
                preamble, question_string, (ans["up"] + " :עלייה" + ans["down"] + " :ירידה"), result2, result3, result4,
                1)
        else:
            return (
                preamble, question_string, (ans["up"] + " :עלייה" + ans["down"] + " :ירידה"), result2, result3, result4,
                1)


def min_max_points(function_types, params):
    minimum_range = MIN_RANGE
    maximum_range = MAX_RANGE
    if ("linear" in function_types):
        preamble = "מצא את נקודת הקיצון:"
        if ("linear" in function_types):
            m = 0
            b = 0
            while m == 0:
                m = random.randint(params[0], params[1])
            while b == 0:
                b = random.randint(params[2], params[3])
            if (b == 0):
                question_string = "y=" + str(m) + "x"
            else:
                question_string = ("y=" + str(m) + "x" + ('+' if b > 0 else "") + str(b))
            result2 = get_random_result(False, False)
            result3 = get_random_result(False, False)
            result4 = get_random_result(False, False)
            return (preamble, question_string, "אין נקודות קיצון", result2, result3, result4, 0)
    if ("quadratic" in function_types):
        preamble = "מצא את נקודת הקיצון:"
        a, b, c = getQuadratic(params[0], params[1], params[2], params[3], params[4], params[5])
        result = find_min_max(a, b, c)

        result2 = get_random_result(False, False)
        result3 = get_random_result(False, False)
        result4 = get_random_result(False, False)
        if a > 0:
            result1 = result["minimum"]
        else:
            result1 = result["maximum"]

        question_string = funcString([a, b, c])

    return (preamble, question_string, (result1["x"], result1["y"]), result2, result3, result4, 0)


def generate_cut_axis(function_types, params):
    preamble = "מצא את נקודות החיתוך עם הצירים:"

    minimum_range = MIN_RANGE
    maximum_range = MAX_RANGE

    # linear
    if ("linear" in function_types):
        m_minimum = int(params[0])
        m_maximum = int(params[1])
        b_minimum = int(params[2])
        b_maximum = int(params[3])
        m = 0
        b = 0
        while m == 0:
            m = random.randint(m_minimum, m_maximum)
        while b == 0:
            b = random.randint(b_minimum, b_maximum)
        """
        else:
            m = random.randint(minimum_range, maximum_range)
            while m == 0:
                m = random.randint(minimum_range, maximum_range)
            b = random.randint(minimum_range, maximum_range)
            """
        ans_x = round(-b / m, 2)
        if (ans_x == round(ans_x)):
            ans_x = round(ans_x)
        ans_xf = (ans_x, 0)
        ans_y = (0, b)

        if (b == 0):
            questions_string = "y=" + str(m) + "x"
        else:
            questions_string = ("y=" + str(m) + "x" + ('+' if b > 0 else "") + str(b))

        ans1 = (ans_xf, ans_y)
        ans2 = get_random_result(True, False)
        ans3 = get_random_result(True, False)
        ans4 = get_random_result(True, False)

    elif ("quadratic" in function_types):
        a_minimum = int(params[0])
        a_maximum = int(params[1])
        b_minimum = int(params[2])
        b_maximum = int(params[3])
        c_minimum = int(params[4])
        c_maximum = int(params[5])
        a = random.randint(a_minimum, a_maximum)
        while a == 0:
            a = random.randint(a_minimum, a_maximum)
        b = random.randint(b_minimum, b_maximum)
        c = random.randint(c_minimum, c_maximum)

        questions_string = "y=" + (((str(a) if a != 1 else "") + "x^2" + ("+" if b > 0 else "")) if a != 0 else "") + \
                           (((str(b) if b != 1 else "") + "x" + ("+" if c > 0 else "")) if b != 0 else "") + \
                           (str(c) if c != 0 else "")

        ans1 = quadQuestion(a, b, c)
        ans2 = quadQuestion(-a, b + random.randint(1, 5), c + random.randint(1, 5))
        ans3 = quadQuestion(a + random.randint(1, 10) if a > 0 else a + random.randint(-10, -1),
                            b + random.randint(1, 5), c)
        ans4 = ((random.randint(1, 10), random.randint(1, 10)),
                ((random.randint(1, 10), random.randint(1, 10)), (random.randint(1, 10), random.randint(1, 10))))

    return (preamble, questions_string, ans1, ans2, ans3, ans4, 0)


def quadQuestion(a, b, c):
    ans_y = (0, c)
    d = b ** 2 - 4 * a * c
    if d > 0:
        d = math.sqrt(d)
        x1 = (-b + d) / (2 * a)
        x2 = (-b - d) / (2 * a)
        ans_xf = (round(x1, 2), 0), (round(x2, 2), 0)
    elif d == 0:
        x = (-b) / (2 * a)
        ans_xf = (x, 0)
    else:
        ans_xf = ()
    return ans_y, ans_xf


def find_min_max(a, b, c):
    # Define the function to find the minima and maxima of
    def f(x):
        return a * x ** 2 + b * x + c

    if a > 0:
        minimum = minimize_scalar(f)
        minimum_x, minimum_y = round(minimum.x, 2), round(minimum.fun, 2)
        return {"minimum": {"x": minimum_x, "y": minimum_y}}

    else:
        maximum = minimize_scalar(lambda x: -f(x))
        maximum_x, maximum_y = round(maximum.x, 2), round(-maximum.fun, 2)
        return {"maximum": {"x": maximum_x, "y": maximum_y}}


def change_order(questions):
    questions_scrambled = list()
    for single_question in questions:
        ans_place = random.randint(2, 5)
        if (ans_place == 2):
            new_single_question = (
                single_question[0], single_question[1], single_question[2], single_question[3], single_question[4],
                single_question[5], 1, single_question[6])
        elif (ans_place == 3):
            new_single_question = (
                single_question[0], single_question[1], single_question[3], single_question[2], single_question[4],
                single_question[5], 2, single_question[6])
        elif (ans_place == 4):
            new_single_question = (
                single_question[0], single_question[1], single_question[4], single_question[3], single_question[2],
                single_question[5], 3, single_question[6])
        elif (ans_place == 5):
            new_single_question = (
                single_question[0], single_question[1], single_question[5], single_question[3], single_question[4],
                single_question[2], 4, single_question[6])
        questions_scrambled.append(new_single_question)
    return questions_scrambled


# template - [0] = type of function
#           [1] = type of question
#           [2] = list of variable restrictions
# template=intersection_linear_-10,10,10,20

# question format - [0] = preamble
#                - [1] = question string
#                - [2] = ans (list?)

def parse_template(template):
    parts = template.split('_')
    questions = parts[0].split(',')
    params = parts[2].split(',')
    if len(parts) == 3:
        return questions, parts[1], params
    integral_range = parts[3].split(',')
    print("integral format:")
    print(questions, parts[1], params, integral_range)
    return questions, parts[1], params, integral_range


def integrate(f: callable, a: float, b: float, n: int) -> np.float32:
    if n == 1:
        h = float(b - a)
        x0 = (a + b) / 2.0
        return np.float32(h * f(x0))
    elif n == 2:
        return np.float32(((float(b - a)) / 2.0) * (f(a) + f(b)))

    if n % 2 == 0:
        n -= 2
    else:
        n -= 1

    h = (b - a) / float(n)
    # result = f(a) + f(b)
    result_of_even = 0
    result_of_odds = 0

    for i in range(1, n, 1):
        if i % 2 == 0:
            result_of_even += f(a + i * h)
        else:
            result_of_odds += f(a + i * h)
    result = 2 * result_of_even + 4 * result_of_odds + f(a) + f(b)
    result *= (h / 3.0)
    return np.float32(result)


def get_questions(unit):
    intMap = {'linear': 0, 'quadratic': 0, 'polynomial': 0, '2exp': 1, '3exp': 1, 'eexp': 1, 'log': 2, 'sin': 3,
              'cos': 4, 'tan': 5, 'cot': 6, 'rational': 7}
    questions = list()
    for i in range(QUESTIONS_TO_GENERATE):
        question_type = []
        function_types = ""
        params = []
        integral_range = []

        if "definiteIntegral" in unit.template:
            question_type, function_types, params, integral_range = parse_template(unit.template)
        else:
            question_type, function_types, params = parse_template(unit.template)
        question = random.choice(question_type)
        if function_types in ['linear', 'quadratic', 'polynomial', '2exp', '3exp', 'eexp', 'log', 'sin', 'cos', 'tan',
                              'cot', 'rational']:
            c = intMap[function_types]
            b = 2 if function_types == '2exp' else (3 if function_types == '3exp' else math.e)
            p = [random.randint(int(params[2 * i]), int(params[2 * i + 1])) for i in range(int(len(params) / 2))]
            f = makeFunc(p, c, b)
            if ('definiteIntegral' in question):
                min_range = int(integral_range[0])
                max_range = int(integral_range[1])
                ans = integrate(f, min_range, max_range, int((max_range - min_range) * 100))
                string_range = str(max_range) + "," + str(min_range)
                preamble = string_range + "מצא את האינטגרל בתחום: "
                ans2 = ans + random.randint(1, 5)
                ans3 = ans - random.randint(1, 5)
                ans4 = ans + random.randint(7, 12)
                q = (preamble, funcString(p, c, b), ans, ans2, ans3, ans4, 0)
                questions.append(q)
            if ('intersection' in question):
                if not any(p):
                    points = "כל הנקודות"
                else:
                    dom = makeDomain(p, c)
                    points = makeIntersections(f, c, dom)
                    if (not points is None):
                        if abs(f(0)) >= 0.001:
                            points.append((0.0, float(round(f(0), 3))))
                preamble = "מצא את נקודות החיתוך עם הצירים:"
                ans2 = [(random.randint(-10000, 10000) / 1000, 0.0) for i in range(len(p) - 1)]
                ans2.append((0.0, (random.randint(-10000, 10000) / 1000)))
                ans3 = [(random.randint(-10000, 10000) / 1000, 0.0) for i in range(len(p) - 1)]
                ans3.append((0.0, (random.randint(-10000, 10000) / 1000)))
                ans4 = [(random.randint(-10000, 10000) / 1000, 0.0) for i in range(len(p) - 1)]
                ans4.append((0.0, (random.randint(-10000, 10000) / 1000)))
                q = (preamble, funcString(p, c, b), points, ans2, ans3, ans4, 0)
                questions.append(q)

            elif ('minMaxPoints' in question):
                points = makeExtremes(p, c, b)
                if points == []:
                    points = 'אין נקודות קיצון'
                to_put_no_extreme_points = 0
                if points != 'אין נקודות קיצון':
                    to_put_no_extreme_points = random.randint(1, 4)
                if to_put_no_extreme_points == 1:
                    ans2 = 'אין נקודות קיצון'
                else:
                    ans2 = [(random.randint(-10000, 10000) / 1000, (random.randint(-10000, 10000) / 1000)) for i in
                            range(max(len(p) - 2, 1))]
                ans3 = [(random.randint(-10000, 10000) / 1000, (random.randint(-10000, 10000) / 1000)) for i in
                        range(max(len(p) - 2, 1))]
                ans4 = [(random.randint(-10000, 10000) / 1000, (random.randint(-10000, 10000) / 1000)) for i in
                        range(max(len(p) - 2, 1))]
                preamble = "מצא את נקודת הקיצון:"
                q = (preamble, funcString(p, c, b), points, ans2, ans3, ans4, 0)
                questions.append(q)
            elif ('incDec' in question):
                inc, dec = makeIncDec(p, c, b)
                preamble = "מצא תחומי עלייה וירידה:"
                i1, d1 = randFillPair(len(inc) + len(dec))
                result2 = (" עלייה: " + str(i1) + " ירידה: " + str(d1) + " ")
                i1, d1 = randFillPair(len(inc) + len(dec))
                result3 = (" עלייה: " + str(i1) + " ירידה: " + str(d1) + " ")
                i1, d1 = randFillPair(len(inc) + len(dec))
                result4 = (" עלייה: " + str(i1) + " ירידה: " + str(d1) + " ")
                q = (
                    preamble, funcString(p, c, b), (" עלייה: " + str(dec) + " ירידה: " + str(inc) + " "), result2,
                    result3,
                    result4, 0)
                questions.append(q)
            elif ('deriveFunc' in question):
                preamble = "מצא מהי הנגזרת של הפונקציה"
                ans1 = deriveString(p, c, b)
                p2 = makeDer(p)
                ans2 = deriveString(p2, c, b)
                p3 = [x + 1 if (x > 1 or x < -1) else x + 3 for x in p]
                ans3 = deriveString(p3, c, b)
                p4 = makeDer(p3)
                ans4 = deriveString(p4, c, b)
                q = (
                    preamble, funcString(p, c, b), ans1, ans2,
                    ans3,
                    ans4, 0)
                questions.append(q)

    return change_order(questions)


def randFillPair(n):
    n = n - 1
    if n < 1:
        n = 1
    sort = sorted([random.randint(-10000, 10000) / 1000 for _ in range(n)])
    dec, inc = [], []
    dec.append((float('-inf'), sort[0]))
    for i, s in enumerate(sort[:-1]):
        if i % 2:
            inc.append((s, sort[i + 1]))
        else:
            dec.append((s, sort[i + 1]))
    inc.append((sort[-1], float('inf')))
    # print("fake incdec ",n,inc, dec)
    return inc, dec


def get_questions2(unit):
    questions = list()
    for i in range(QUESTIONS_TO_GENERATE):
        question_type, function_types, params = parse_template(unit.template)
        question = random.choice(question_type)
        if ('intersection' in question):
            q = generate_cut_axis(function_types, params)
        elif ('minMaxPoints' in question):
            q = min_max_points(function_types, params)
        elif ('incDec' in question):
            q = inc_dec(function_types, params)
        questions.append(q)
    return change_order(questions)


def get_max_unit(unit, user):
    maxAttempt = 0
    for activeU in ActiveUnit.select(unit=unit, student=user):
        if activeU.attempt > maxAttempt:
            maxAttempt = activeU.attempt
    return maxAttempt


def addQuestions(className, unitName, username):
    try:
        with db_session:
            unit = Unit[unitName, Cls[className]]
            user = User[username]

            maxAttempt = get_max_unit(unit, user)
            if (maxAttempt == 0):
                ActiveUnit(inProgress=True, unit=unit, student=user, attempt=maxAttempt + 1, currentQuestion=0,
                           consecQues=0, quesAmount=0, totalCorrect=0, grade=0)
                maxAttempt += 1
            active = ActiveUnit[unit, user, (maxAttempt)]
            if not active.inProgress:
                active = ActiveUnit(inProgress=True, unit=unit, student=user, attempt=maxAttempt + 1, currentQuestion=0,
                                    consecQues=0, quesAmount=0, totalCorrect=0, grade=0)
                maxAttempt += 1

            if (active.currentQuestion < active.quesAmount):
                return jsonify(unit.maxTime)
            id = active.quesAmount + 1
            active.quesAmount += 10
            for single_question in get_questions(unit):
                # if (single_question[7] == 0):
                #      print("==============================================================\n", single_question)
                #     Question(id=id, question_preamble=single_question[0], question=single_question[1],
                #              correct_ans=single_question[6], answer1=str(single_question[2])[1:-1],
                #              answer2=str(single_question[3])[1:-1], answer3=str(single_question[4])[1:-1],
                #              answer4=str(single_question[5])[1:-1],
                #              active_unit=ActiveUnit[unit, user, maxAttempt])
                # else:
                Question(id=id, question_preamble=single_question[0], question=single_question[1],
                         correct_ans=single_question[6], answer1=str(single_question[2]),
                         answer2=str(single_question[3]), answer3=str(single_question[4]),
                         answer4=str(single_question[5]),
                         active_unit=ActiveUnit[unit, user, maxAttempt])
                id += 1

            commit()
            return jsonify(unit.maxTime)
    except Exception as e:
        print(traceback.format_exc())
        print(e)
        return str(e), 400


def addQuestions_for_tests(className, unitName, username):
    try:
        with db_session:
            unit = Unit[unitName, Cls[className]]
            user = User[username]

            maxAttempt = get_max_unit(unit, user)
            if maxAttempt == 0:
                ActiveUnit(inProgress=True, unit=unit, student=user, attempt=maxAttempt + 1, currentQuestion=0,
                           consecQues=0, quesAmount=0, totalCorrect=0, grade=0)
                maxAttempt += 1
            active = ActiveUnit[unit, user, maxAttempt]

            if active.currentQuestion < active.quesAmount:
                return str(unit.maxTime)

            id = active.quesAmount + 1
            active.quesAmount += 10
            for single_question in get_questions(unit):
                if single_question[7] == 0:
                    Question(id=id, question_preamble=single_question[0], question=single_question[1],
                             correct_ans=single_question[6], answer1=str(single_question[2])[1:-1],
                             answer2=str(single_question[3])[1:-1], answer3=str(single_question[4])[1:-1],
                             answer4=str(single_question[5])[1:-1],
                             active_unit=ActiveUnit[unit, user, maxAttempt])
                else:
                    Question(id=id, question_preamble=single_question[0], question=single_question[1],
                             correct_ans=single_question[6], answer1=str(single_question[2]),
                             answer2=str(single_question[3]), answer3=str(single_question[4]),
                             answer4=str(single_question[5]),
                             active_unit=ActiveUnit[unit, user, maxAttempt])
                id += 1

            commit()
            return str(unit.maxTime)
    except Exception as e:
        print(traceback.format_exc())
        print(e)
        return str(e), 400


# now all this does is add 10 questions to the active unit
@app.route('/startUnit')
def startUnit():
    className = request.args.get('className')
    unitName = request.args.get('unitName')
    username = request.args.get('username')
    if not isLogin(username):
        return "user " + username + "not logged in.", 400
    return startUnit(className, unitName, username)


def startUnit(className, unitName, username):
    return addQuestions(className, unitName, username)


# now all this does is add 10 questions to the active unit
@app.route('/individualStats')
def individualStats():
    className = request.args.get('className')
    unitName = request.args.get('unitName')
    teacherUsername = request.args.get('usernameT')
    studentUsername = request.args.get('usernameS')
    if not isLogin(teacherUsername):
        return "user " + teacherUsername + "not logged in.", 400
    try:
        with db_session:
            ret = dict()
            unit = Unit[unitName, Cls[className]]
            user = User[studentUsername]

            active = ActiveUnit[unit, user, 1]
            ans = list()
            ans.append(active.totalCorrect)
            ans.append((active.currentQuestion - active.totalCorrect))
            ret["correctIncorrect"] = ans

            entity_count = ActiveUnit.select(student=user).count()
            last_five_entities = ActiveUnit.select(student=user).order_by(lambda e: e.lastTimeAnswered)[
                                 max(0, entity_count - 2):]
            last5grades = list()

            for entity in last_five_entities:
                last5grades.append(entity.grade)
                print(entity.lastTimeAnswered)

            last5grades.reverse()
            if (len(last_five_entities) < 5):
                for i in range(5 - len(last_five_entities)):
                    last5grades.append(0)

            ret["L5"] = last5grades

            return jsonify(ret)
    except Exception as e:
        print(e)
        return str(e), 400


def getActiveUnits(className, unitName, username):  # this is for dab

    try:
        with db_session:
            active_units = ActiveUnit.select(lambda au: au.unit.cls.name == className and
                                                        au.unit.name == unitName and
                                                        au.student.name == username)[:]
            json_data = json.dumps(active_units)
            return jsonify(json_data)
    except Exception as e:
        print(e)
        return str(e), 400


def itemByName(lst, name):
    for item in lst:
        if item["name"] == name:
            return item
    return None


def getAllActiveUnits(className, unitName):
    try:
        with db_session:
            active_units = ActiveUnit.select(lambda au: au.unit.cls.name == className and au.unit.name == unitName)[:]
            students = []
            names = []
            for au in active_units:
                if au.student.name not in names:
                    names.append(au.student.name)
                    single_obj = dict()
                    single_obj["name"] = au.student.name
                    single_obj["correct"] = au.totalCorrect
                    single_obj["bad"] = (au.currentQuestion - au.totalCorrect)
                    students.append(single_obj)
                else:
                    item = itemByName(students, au.student.name)
                    item["correct"] += au.totalCorrect
                    item["bad"] += (au.currentQuestion - au.totalCorrect)
            return jsonify(students)
    except Exception as e:
        print(e)
        return str(e), 400


def getAllActiveUnits_for_tests(className, unitName):
    try:
        with db_session:
            active_units = ActiveUnit.select(lambda au: au.unit.cls.name == className and au.unit.name == unitName)[:]
            students = []
            names = []
            for au in active_units:
                if au.student.name not in names:
                    names.append(au.student.name)
                    single_obj = dict()
                    single_obj["name"] = au.student.name
                    single_obj["correct"] = au.totalCorrect
                    single_obj["bad"] = (au.currentQuestion - au.totalCorrect)
                    students.append(single_obj)
                else:
                    item = itemByName(students, au.student.name)
                    item["correct"] += au.totalCorrect
                    item["bad"] += (au.currentQuestion - au.totalCorrect)

            result = ""
            for student in students:
                result += f"Name: {student['name']}, Correct: {student['correct']}, Bad: {student['bad']}\n"

            return result
    except Exception as e:
        return f"Error: {str(e)}", 400


@app.route('/getStats')
def getStats():
    className = request.args.get('className')
    unitName = request.args.get('unitName')
    username = request.args.get('username')
    if not isLogin(username):
        return "user " + username + "not logged in.", 400

    return getAllActiveUnits(className, unitName)


@app.route('/getQuestion')
def getQuestion():
    user = request.args.get('username')
    unit_name = request.args.get('unitName')
    class_name = request.args.get('className')
    question_number = request.args.get('qnum')
    if not isLogin(user):
        return "user " + user + "not logged in.", 400
    try:
        return getQuestion_buisness(user, unit_name, class_name, question_number)
    except Exception as e:
        print(e)
        return str(e), 400


def getQuestion_buisness(user, unit_name, class_name, question_number):
    try:
        with db_session:
            ret = []
            unit = Unit[unit_name, Cls[class_name]]
            attempt = get_max_unit(unit, user)
            active = ActiveUnit[unit, user, attempt]
            question = Question[active, active.currentQuestion + 1]
            single_question = dict()
            single_question["id"] = question.id
            # single_question["question_preamble"] = question.question_preamble
            single_question["primary"] = question.question
            single_question["answer1"] = question.answer1
            single_question["answer2"] = question.answer2
            single_question["answer3"] = question.answer3
            single_question["answer4"] = question.answer4
            single_question["correct_ans"] = question.correct_ans
            single_question["preamble"] = question.question_preamble
            single_question["currentQuestion"] = active.consecQues
            single_question["questionsNeeded"] = unit.Qnum

            ret.append(single_question)
            print("ret=", ret)
        return jsonify(ret)
    except Exception as e:
        print(e)
        return str(e), 400


# 201 and the correct answer if answered incorrectly,
# 200 if answered correctly but not enough consecutive
# 204 if answered correctly and enough consecutive
@app.route('/submitQuestion', methods=['GET', 'POST'])
def submitQuestion():
    user = request.args.get('username')
    unit_name = request.args.get('unitName')
    class_name = request.args.get('className')
    question_number = request.args.get('qnum')
    ans_number = int(request.args.get('ans'))
    if not isLogin(user):
        return "user " + user + "not logged in.", 400

    try:
        return submitQuestion_buisness(user, unit_name, class_name, question_number, ans_number)
    except Exception as e:
        print(e)
        return str(e), 400


def submitQuestion_buisness(user, unit_name, class_name, question_number, ans_number):
    try:
        with db_session:
            now = datetime.now()
            date_string = now.strftime("%d.%m.%Y")
            retValue = 200
            unit = Unit[unit_name, Cls[class_name]]
            attempt = get_max_unit(unit, user)
            activeUnit = ActiveUnit[unit, user, attempt]
            question = Question[activeUnit, question_number]
            activeUnit.currentQuestion += 1
            activeUnit.lastTimeAnswered = date_string

            if (not activeUnit.currentQuestion < activeUnit.quesAmount):
                addQuestions(class_name, unit_name, user)

            if question.correct_ans == ans_number:
                question.solved_correctly = True
                activeUnit.consecQues += 1
                activeUnit.totalCorrect += 1
                activeUnit.grade = int(((activeUnit.totalCorrect / activeUnit.currentQuestion) * 100))

            else:
                question.solved_correctly = False
                activeUnit.consecQues = 0
                activeUnit.grade = int(((activeUnit.totalCorrect / activeUnit.currentQuestion) * 100))
                return "incorrect", (200 + question.correct_ans)

            if (activeUnit.consecQues == int(unit.Qnum) or activeUnit.consecQues > int(unit.Qnum)):
                activeUnit.inProgress = False
                if activeUnit.unit.next:
                    return jsonify(activeUnit.unit.next), 206
                else:
                    return "answered enough consecutive questions", 205

            return "correct"

            return "question answered", retValue
    except Exception as e:
        print(e)
        return str(e), 400


@app.route('/quitActiveUnit')
def quitActiveUnit():
    user = request.args.get('username')
    unit_name = request.args.get('unitName')
    class_name = request.args.get('className')
    with db_session:
        unit = Unit[unit_name, Cls[class_name]]
        attempt = get_max_unit(unit, user)
        activeUnit = ActiveUnit[unit, user, attempt]
        activeUnit.inProgress = False
    return 'done'


def makePoly(p):
    # print([str(p[i]) + '*(x**' + str(len(p) - i - 1) + ')' for i in range(len(p))])
    return (lambda x:
            float(sum([
                p[i] * (x ** (len(p) - i - 1))
                for i in range(len(p))
            ])))


def makeRationalOfTwoFuncs(f1, f2):
    def res(x):
        if f2(x) == 0:
            return None
        return f1(x) / f2(x)

    return res


def makeMultOfTwoFuncs(f1, f2):
    return (lambda x:
            f1(x) * f2(x)
            )


def makeNegateFunc(f):
    return (lambda x:
            -f(x)
            )


def regulaFalsi(f1: callable, f2: callable, x1: float, x2: float, a: float, b: float, maxerr=0.0001) -> float:
    max_amount_of_iteration_loop = 30
    f_x1 = f1(x1) - f2(x1)
    f_x2 = f1(x2) - f2(x2)
    if f_x1 == f_x2:
        return None
    x = (x1 * f_x2 - x1 * f_x1) / (f_x2 - f_x1)

    i = 0
    while np.abs(f1(x) - f2(x)) >= maxerr and a - maxerr <= x <= b + maxerr and i < max_amount_of_iteration_loop:

        x = (x1 * f_x2 - x2 * f_x1) / (f_x2 - f_x1)

        if np.abs(f1(x) - f2(x)) <= maxerr:
            break
        elif f_x1 * (f1(x) - f2(x)) < 0:
            x1 = x
            f_x1 = f1(x1) - f2(x1)
        else:
            x2 = x
            f_x2 = f1(x2) - f2(x2)
        i += 1
    if i > max_amount_of_iteration_loop or (x > b or x < a) or np.abs(f1(x) - f2(x)) > maxerr:
        return None
    return x


def helper(f1: callable, f2: callable, a: float, b: float, maxerr=0.001) -> Iterable:
    diff = b - a
    int_of_diff = int(diff)

    max_amount_of_points = int_of_diff * 50
    x1 = a

    # check this if
    if max_amount_of_points == 0:
        max_amount_of_points = 50

    delta = (b - a) / max_amount_of_points
    x2 = x1

    f_x1 = f1(x1) - f2(x1)
    f_x2 = f1(x2) - f2(x2)
    while x1 <= b + maxerr and x2 <= b + maxerr:

        if abs(f_x1) <= maxerr:
            yield x1
            x1 += delta
            x2 = x1 + delta
            f_x1 = f1(x1) - f2(x1)
        elif abs(f_x2) <= maxerr:
            yield x2
            x1 = x2 + delta
            x2 = x1 + delta
            # x2 = x2 + delta
            # x1 = x2 + delta
            f_x1 = f1(x1) - f2(x1)
        elif f_x1 * f_x2 < 0 and f_x1 != f_x2:
            x = regulaFalsi(f1, f2, x1, x2, a, b, maxerr)
            # print("here x="+str(x))
            # print("f1(x)-f2(x)="+str(f1(x))+"-"+str(f2(x))+"="+str(f1(x)-f2(x)))
            if x is not None:
                yield x
            x1 = x2 + delta
            x2 = x2 + delta
            f_x1 = f1(x1) - f2(x1)
        else:
            x1 = x2
            x2 += delta
        if x2 < b and x2 > a:
            f_x2 = f1(x2) - f2(x2)
        elif x2 > b:
            # print(x2, b, b - 100 * maxerr)
            f_x2 = f1(b - 100 * maxerr) - f2(b - 100 * maxerr)
        else:
            # print(x2, a, a+100*maxerr)
            f_x2 = f1(a + 100 * maxerr) - f2(a + 100 * maxerr)


def intersections(f1: callable, f2: callable, a: float, b: float, maxerr=0.00001) -> Iterable:
    iterator = helper(f1, f2, a + 0.01, b - 0.01, maxerr)
    arr = np.array([])
    for x in iterator:
        if len(arr) == 0 or abs(x - arr[len(arr) - 1]) > maxerr:
            arr = np.append(arr, [x])
    return arr


def makeDomain(params, c=0):
    if c == 0:
        return [(-100, 100)]
    elif c in [1, 3, 4]:
        r = [(-math.pi, math.pi)]
        return r
    elif c == 2:
        r = []
        coefficient = params[:-1]
        f = makeFunc(coefficient)
        inters = [x for x in intersections(f, lambda x: 0, -100, 100)]
        inters.append(-100)
        inters.append(100)
        inters = sorted([round(x, 3) for x in inters])
        # print(inters)
        for i in range(len(inters) - 1):
            a = (inters[i] + inters[i + 1]) / 2
            if f(a) > 0:
                r.append((inters[i], inters[i + 1]))
        return r
    elif c in [5, 6]:
        r = []
        coefficient = params[:-1] + [0]
        f = makeFunc(coefficient, 3 if c == 6 else 4)
        inters = sorted(intersections(lambda x: 0, f, -3, 3))
        if len(inters) == 0:
            return [(-100, 100)]
        for i in range(len(inters) - 1):
            r.append((inters[i], inters[i + 1]))
        return r
    elif c == 7:
        p2 = p[int(len(p) / 2):]
        poly = makePoly(p2)
        zeroes = sorted([x[0] for x in makeIntersections(poly)])
        if len(zeroes) == 0:
            return [(-100, 100)]
        r = []
        r.append((-100, zeroes[0]))
        for i in range(len(zeroes) - 1):
            r.append((zeroes[i], zeroes[i + 1]))
        r.append(((zeroes[-1]), 100))
        return r
    elif c == 8:
        poly = makePoly(params[:-1])
        zeroes = [x[0] for x in makeIntersections(poly)]
        if len(zeroes) == 0:
            return [(-100, 100)]
        r = []
        zeroes.append(-100)
        zeroes.append(100)
        zeroes = sorted(zeroes)
        for i in range(len(zeroes) - 1):
            z = (zeroes[i] + zeroes[i + 1]) / 2
            if poly(z) >=0:
                r.append((zeroes[i], zeroes[i + 1]))
        return r


def makeIntersections(poly, c=0, r=[(-100, 100)]):
    xs = []
    for i in r:
        inters = (intersections(poly, lambda x: 0, i[0], i[1]))
        for x in inters:
            xs.append(x)

    points = [(float(round(i, 3)), 0.0) if abs(round(i, 3)) > 0.001 else (0.0, 0.0) for i in xs]

    # if 0 not in [float(round(i, 3)) for i in xs]:
    #     points.append((0.0, float(round(poly(0), 3))))
    print("points: ", points)
    return points


def makeIntersections2(poly, error=1e-3, xmin=-20, xmax=20, step=0.0003):
    intersections = []
    x = xmin
    unique_x_values = set()  # Set to store unique x-values
    while x <= xmax:
        fx = poly(x)
        if abs(fx) < error:
            if round(x, int(-math.log(error, 10) - 1)) not in unique_x_values:  # Check if x-value is unique
                print(round(x, int(-math.log(error, 10) - 1)), unique_x_values)
                intersections.append((round(x, int(-math.log(error, 10) - 1)), 0))
                unique_x_values.add(round(x, int(-math.log(error, 10) - 1)))
        x += step
    # Add the intersection point at x = 0 if it is unique
    if 0 not in unique_x_values:
        intersections.append((0, poly(0)))
    return intersections


def makeDer(params):
    return [(len(params) - 1 - i) * params[i] for i in range(len(params) - 1)]


def deriveString(p, c, b):

    if c == 0:
        return "y=" + polySrting(makeDer(p))
    elif c == 1:
        return "y=(" + polySrting(makeDer(p[:-1])) + ") * " + ("e" if b == math.e else str(b)) + "^(" + polySrting(
            p[:-1]) + ")"
    elif c == 2:
        return "y=(" + polySrting(makeDer(p[:-1])) + " / " + polySrting(p[:-1]) + ")"
    elif c == 3:
        return "y=" + polySrting(makeDer(p[:-1])) + " * cos(" + polySrting(p[:-1]) + ")"
    elif c == 4:
        return "y=" + polySrting(makeDer(p[:-1])) + " * -sin(" + polySrting(p[:-1]) + ")"
    elif c == 5:
        return "y=(1/cos^2(" + polySrting(p[:-1]) + ")"
    elif c == 6:
        return "y=(-1/sin^2(" + polySrting(p[:-1]) + ")"
    elif c == 7:
        l = int(len(p)/2)
        return "y=((" + polySrting(makeDer(p[:l]))+ ") * (" + polySrting(p[l:]) + ")) / ((" + polySrting(makeDer(p[l:]))+ ") * (" + polySrting(p[:l]) + "))"
    elif c == 8:
        return "y=("+ polySrting(makeDer(p[:-1])) +") * (" + polySrting(p[:-1]) + ")^("+str(1/b)+")"


def derive(params, c=0, b=math.e):
    if c == 0:
        return makeFunc(makeDer(params))
    elif c == 1:
        def res(x):
            polyx = makePoly(params[:-1])(x)
            derx = makeFunc(makeDer(params[:-1]))(x)
            return derx * math.pow(b, polyx) * math.log(b, math.e)

        return res

    elif c == 2:
        numerator = makeFunc(makeDer(params[:-1]))
        denominator = makeFunc(params[:-1])
        new_denominator = lambda x: denominator(x) * math.log(b, math.e)
        return makeRationalOfTwoFuncs(numerator, new_denominator)
    elif c == 3:
        coefficients = params[:-1]
        innerDerive = makeFunc(makeDer(coefficients))

        def cosElement(x):
            return math.cos((makePoly(coefficients))(x))

        return makeMultOfTwoFuncs(cosElement, innerDerive)
    elif c == 4:
        coefficients = params[:-1]
        innerDerive = makeFunc(makeDer(coefficients))

        def sinElement(x):
            return math.sin((makePoly(coefficients))(x))

        return makeMultOfTwoFuncs(makeNegateFunc(sinElement), innerDerive)
    if c == 5:
        return lambda x: 1 / (makeFunc(params[:-1] + [0], 4)(x) ** 2)
    if c == 6:
        return lambda x: -1 / (makeFunc(params[:-1] + [0], 3)(x) ** 2)
    if c == 7:
        p1 = p[:int(len(p) / 2)]
        p2 = p[int(len(p) / 2):]
        poly1 = makePoly(p1)
        poly2 = makePoly(p2)
        return lambda x: (derive(p1)(x)*poly2(x)-poly1(x)*derive(p2)(x)) / (poly2(x)**2)
    if c == 8:
        poly = makePoly(p[:-1])
        return lambda x: derive(p[:-1])(x)*(1/b)*math.pow(1/b-1, poly(x))


def makeExtremes(params, c=0, b=math.e):
    # Calculate the derivative of the polynomial
    if not any(params):
        return "אין נקודות קיצון"
    # if c == 0:
    #     f = makeFunc(params)
    #     derivative = makeDer(params)
    #     realDerive = derive(params, function_types)
    #     poly = makeFunc(derivative)
    #     extreme_points = makeIntersections(poly, c,function_types)
    #
    #     for i in range(len(extreme_points)):
    #         tuple_value = extreme_points[i]
    #         updated_tuple = (tuple_value[0], round(f(tuple_value[0]), 3))
    #         extreme_points[i] = updated_tuple
    #
    #     return extreme_points

    realDerive = derive(params, c, b)
    dom = makeDomain(params, c)
    extreme_points = makeIntersections(realDerive, c, dom)
    print("extreme_points", extreme_points)
    f = makeFunc(params, c, b)

    extremes = [(e[0], round(f(e[0]), 3)) for e in extreme_points]
    return extremes


def getSymmetry2(p, c=0, b=math.e):
    f = makeFunc(p, c, b)
    fa = lambda a, b, x: a * f(-x + b)
    err = 0.002
    m = 10.0
    a = -m / 5
    b = -m
    while a < m:
        b = -m
        while b < m:
            found = True
            x = -m
            while x < m:
                if round(f(x), 1) != round(fa(a, b, x), 1):
                    found = False
                    break
                x += 10 * err

            if found:
                return round(a, 2), round(b, 2)
            b += err
        a += 10 * err
    return None


def getSymmetry(p, c=0, b=math.e):
    f = makeFunc(p, c, b)
    err = 0.001
    m = 10
    center = -m
    while center < m:
        x = 10 * err
        sign = None
        while x < m / 10:
            if sign is None:

                l = round(f(center + x) - f(center), 1)
                r = round(f(center - x) - f(center), 1)
                if abs(center) < err:
                    print(l, r)
                if abs(l - r) < err:
                    sign = 1
                elif abs(l + r) < err:
                    sign = -1
                else:
                    sign = None
                    break
            else:
                center = round(center, 3)
                x = round(x, 3)
                if abs(round((f(center + x) - f(center)) - sign * (f(center - x) - f(center)), 1)) > 10 * err:
                    if (abs(center) < err):
                        print("BAD ", center, x,
                              abs(round((f(center + x) - f(center)) - sign * (f(center - x) - f(center)), 1)))
                    sign = None
                    break
            x += 10 * err
        if sign is not None:
            return sign, round(center, 2)
        center += err
    return None


def makeIncDec(p, c=0, b=math.e):
    if not any(p[:-1]):
        return [], []
    extremes = makeExtremes(p, c, b)
    dom = makeDomain(p, c)
    # print("dom, ext",dom, extremes)
    ext = set()
    f = makeFunc(p, c, b)
    for i in extremes:
        ext.add(i)
    for i in dom:
        if i[0] not in [-100, 100, math.pi, -math.pi]:
            if f(i[0] + 0.001):
                ext.add((i[0], float('-inf') if f(i[0] + 0.001) < 0 else float('inf')))
            else:
                ext.add((i[0], float('-inf') if f(i[0] - 0.001) < 0 else float('inf')))
        if i[1] not in [-100, 100, math.pi, -math.pi]:
            if f(i[1] + 0.001):
                ext.add((i[1], float('-inf') if f(i[1] + 0.001) < 0 else float('inf')))
            else:
                ext.add((i[1], float('-inf') if f(i[1] - 0.001) < 0 else float('inf')))
    print(ext)
    # Sort the extreme points by their x-values
    sorted_extremes = sorted(list(ext))
    print("sorted", sorted_extremes)
    f = derive(p, c, b)
    if len(sorted_extremes) == 0:
        dom = makeDomain(p, c)
        sample = random.randint(dom[0][0] * 1000, dom[0][1] * 1000) / 1000
        if f(sample) > 0:
            return [(float('-inf'), float('inf'))], []
        else:
            return [], [(float('-inf'), float('inf'))]
    s = f(sorted_extremes[0][0] - 1)

    inc_ranges = []
    dec_ranges = []

    # Add the initial range
    if s < 0:
        dec_ranges.append((float('-inf'), sorted_extremes[0][0]))
    else:
        inc_ranges.append((float('-inf'), sorted_extremes[0][0]))

    # Iterate over the sorted extreme points
    for i in range(len(sorted_extremes) - 1):
        x1, y1 = sorted_extremes[i]
        x2, y2 = sorted_extremes[i + 1]

        if y1 < y2:
            inc_ranges.append((x1, x2))
        elif y1 > y2:
            dec_ranges.append((x1, x2))
    s = f(sorted_extremes[-1][0] + 1)
    # Add the final range
    if s < 0:
        dec_ranges.append((sorted_extremes[-1][0], float('inf')))
    else:
        inc_ranges.append((sorted_extremes[-1][0], float('inf')))

    return inc_ranges, dec_ranges


def makePosNeg(p, c=0, b=math.e):
    if not any(p[:-1]):
        return [], []
    dom = makeDomain(p, c)

    # print("dom, ext",dom, extremes)
    f = makeFunc(p, c, b)
    inters = makeIntersections(f, c, dom)
    points = set()
    for i in inters:
        points.add(i)
    for i in dom:
        if i[0] not in [-100, 100, math.pi, -math.pi]:
            if f(i[0] + 0.001):
                points.add((i[0], float('-inf') if f(i[0] + 0.001) < 0 else float('inf')))
            else:
                points.add((i[0], float('-inf') if f(i[0] - 0.001) < 0 else float('inf')))
        if i[1] not in [-100, 100, math.pi, -math.pi]:
            if f(i[1] + 0.001):
                points.add((i[1], float('-inf') if f(i[1] + 0.001) < 0 else float('inf')))
            else:
                points.add((i[1], float('-inf') if f(i[1] - 0.001) < 0 else float('inf')))
    # Sort the extreme points by their x-values
    sorted_points = sorted(list(points))
    print("sorted", sorted_points)
    if len(sorted_points) == 0:
        dom = makeDomain(p, c)
        sample = random.randint(dom[0][0] * 1000, dom[0][1] * 1000) / 1000
        if f(sample) > 0:
            return [(float('-inf'), float('inf'))], []
        else:
            return [], [(float('-inf'), float('inf'))]

    pos = []
    neg = []
    if any([sorted_points[0][0] - 1 in d for d in dom]):
        s = f(sorted_points[0][0] - 1)


        # Add the initial range
        if s < 0:
            neg.append((float('-inf'), sorted_points[0][0]))
        else:
            pos.append((float('-inf'), sorted_points[0][0]))

    # Iterate over the sorted extreme points
    for i in range(len(sorted_points) - 1):
        x1, y1 = sorted_points[i]
        x2, y2 = sorted_points[i + 1]
        x = (x1 + x2) / 2
        y = f(x)
        if y is None:
            continue
        if y > 0:
            pos.append((x1, x2))
        elif y < 0:
            neg.append((x1, x2))
    s = f(sorted_points[-1][0] + 1)
    # Add the final range
    if s < 0:
        neg.append((sorted_points[-1][0], float('inf')))
    else:
        pos.append((sorted_points[-1][0], float('inf')))

    return pos, neg


def makeIncDec2(p, c=0, b=math.e):
    if not any(p[:-1]):
        return [], []
    extremes = makeExtremes(p, c, b)
    dom = makeDomain(p, c)
    print("dom, ext", dom, extremes)
    ext = set()
    f = makeFunc(p, c, b)
    for i in extremes:
        ext.add(i)
    for i in dom:
        if i[0] not in [-100, 100]:
            if f(i[0] + 0.001):
                ext.add((i[0], float('-inf') if f(i[0] + 0.001) < 0 else float('inf')))
            else:
                ext.add((i[0], float('-inf') if f(i[0] - 0.001) < 0 else float('inf')))
        if i[1] not in [-100, 100]:
            if f(i[1] + 0.001):
                ext.add((i[1], float('-inf') if f(i[1] + 0.001) < 0 else float('inf')))
            else:
                ext.add((i[1], float('-inf') if f(i[1] - 0.001) < 0 else float('inf')))
    print(ext)
    # Sort the extreme points by their x-values
    sorted_extremes = sorted(list(ext))
    print("sorted", sorted_extremes)
    f = lambda x: makeFunc(makeDer(p))(x) * makeFunc(p[:-1] + [0], c, b)(x)
    if len(sorted_extremes) == 0:
        dom = makeDomain(p, c)
        sample = random.randint(dom[0][0] * 1000, dom[0][1] * 1000) / 1000
        if f(sample) > 0:
            return [(float('-inf'), float('inf'))], []
        else:
            return [], [(float('-inf'), float('inf'))]
    s = f(sorted_extremes[0][0] - 1)

    inc_ranges = []
    dec_ranges = []

    # Add the initial range
    if s < 0:
        dec_ranges.append((float('-inf'), sorted_extremes[0][0]))
    else:
        inc_ranges.append((float('-inf'), sorted_extremes[0][0]))

    # Iterate over the sorted extreme points
    for i in range(len(sorted_extremes) - 1):
        x1, y1 = sorted_extremes[i]
        x2, y2 = sorted_extremes[i + 1]

        if y1 < y2:
            inc_ranges.append((x1, x2))
        elif y1 > y2:
            dec_ranges.append((x1, x2))
    s = f(sorted_extremes[-1][0] + 1)
    # Add the final range
    if s < 0:
        dec_ranges.append((sorted_extremes[-1][0], float('inf')))
    else:
        inc_ranges.append((sorted_extremes[-1][0], float('inf')))

    return inc_ranges, dec_ranges


def funcString(p, c=0, b=math.e):
    if c == 0:
        return "y=" + polySrting(p)
    elif c == 1:
        return "y=" + ("e" if b == math.e else str(b)) + "^(" + polySrting(p[:-1]) + ")" + (
            ("+" if p[-1] > 0 else "") + str(p[-1]) if p[-1] else "")
    elif c == 2:
        return "y=" + ("ln" if b == math.e else "log" + str(b)) + "(" + polySrting(p[:-1]) + ")" + (
            ("+" if p[-1] > 0 else "") + str(p[-1]) if p[-1] else "")
    elif c == 3:
        return "y=sin(" + polySrting(p[:-1]) + ")" + (("+" if p[-1] > 0 else "") + str(p[-1]) if p[-1] else "")
    elif c == 4:
        return "y=cos(" + polySrting(p[:-1]) + ")" + (("+" if p[-1] > 0 else "") + str(p[-1]) if p[-1] else "")
    elif c == 5:
        return "y=tan(" + polySrting(p[:-1]) + ")" + (("+" if p[-1] > 0 else "") + str(p[-1]) if p[-1] else "")
    elif c == 6:
        return "y=cot(" + polySrting(p[:-1]) + ")" + (("+" if p[-1] > 0 else "") + str(p[-1]) if p[-1] else "")
    elif c == 7:
        l = int(len(p)/2)
        return "y=(" + polySrting(p[:l]) + ") / (" + polySrting(p[l:]) + ")"
    elif c == 8:
        return "y=(" + polySrting(p[:-1]) + ")^("+str(1/b)+")" + (("+" if p[-1] > 0 else "") + str(p[-1]) if p[-1] else "")


def polySrting(params):
    ret = ""
    for i in range(len(params)):
        if params[i] != 0:
            if ret != "":
                ret += '+' if params[i] > 0 else ''
            ret += (
                       str(params[i])
                       if not (params[i] == 1 or params[i] == -1) or len(params) - 1 - i == 0
                       else ("" if params[i] == 1 else "-")) \
                   + (
                       ('x' +
                        (('^' + str(len(params) - 1 - i))
                         if len(params) - 1 - i > 1
                         else "")
                        )
                       if len(params) - 1 - i > 0
                       else ""
                   )
    if ret == "":
        return "0"
    return ret


def makeExpo(p, base=math.e):
    if len(p) < 1:
        return lambda x: 0
    else:
        return lambda x: math.pow(base, makePoly(p[:-1])(x)) + p[-1]


def makeLog(p, base=math.e):
    if len(p) < 1:
        return lambda x: 0
    else:

        def func(x):
            temp = makePoly(p[:-1])(x)
            if temp > 0:
                return math.log(makePoly(p[:-1])(x), base) + p[-1]
            else:
                print("LOGNONE", funcString(p, 2, base), x)
                return None

        return func


def makeSin(p):
    if len(p) < 1:
        return lambda x: 0
    else:
        return lambda x: math.sin(makePoly(p[:-1])(x)) + p[-1]


def makeCos(p):
    if len(p) < 1:
        return lambda x: 0
    else:
        return lambda x: math.cos(makePoly(p[:-1])(x)) + p[-1]


def makeTan(p):
    if len(p) < 1:
        return lambda x: 0
    else:
        return lambda x: math.tan(makePoly(p[:-1])(x)) + p[-1]


def makeTan(p):
    if len(p) < 1:
        return lambda x: 0
    else:
        return lambda x: math.tan(makePoly(p[:-1])(x)) + p[-1]


def makeCot(p):
    if len(p) < 1:
        return lambda x: 0
    else:
        return lambda x: 1 / math.tan(makePoly(p[:-1])(x)) + p[-1]


def makeRational(p):
    p1 = p[:int(len(p) / 2)]
    p2 = p[int(len(p) / 2):]
    return lambda x: makePoly(p1)(x) / makePoly(p2)(x)

def makeRoot(p, b):
    if len(p) < 1:
        return lambda x: 0
    else:
        return lambda x: math.pow(makePoly(p[:-1])(x), 1/b) + p[-1]


def makeFunc(p, c=0, b=math.e):
    if c == 0:
        return makePoly(p)
    elif c == 1:
        return makeExpo(p, b)
    elif c == 2:
        return makeLog(p, b)
    elif c == 3:
        return makeSin(p)
    elif c == 4:
        return makeCos(p)
    elif c == 5:
        return makeTan(p)
    elif c == 6:
        return makeCot(p)
    elif c == 7:
        return makeRational(p)
    elif c == 8:
        return makeRoot(p, b)


# [random.randint(params[2*i], params[2*i+1]) for i in range(int(len(params)/2))]

p = [1, 1, 0]
c = 8
b = 2
a = makeFunc(p, c=c, b=b)
print()
print("f: " + str(a))
print("f(2): " + str(a(2)))
dom = makeDomain(p, c)
print("Domain: " + str(dom))
print("Intersections: " + str(makeIntersections(a, c=c, r=dom)))
print("Extremes: " + str(makeExtremes(p, c=c)))
#print("IncDec: " + str(makeIncDec(p, c=c)))
print("funcString: " + str(funcString(p, c=c,b=b)))
print("deriveString: " + str(deriveString(p, c=c, b=b)))
print("PosNeg: " + str(makePosNeg(p, c=c, b=b)))
#sym = getSymmetry(p, c)
#print("symmetry: " + ("f(x)=" + str(sym[0]) + "*f(-x+" + str(2 * sym[1]) + ")") if sym else sym)


def getLessonGrade(user, unit_name, class_name):
    try:
        with db_session:
            unit_name_n = unit_name
            total_correct = 0
            total_solved = 0
            try:
                while (True):
                    unit = Unit[unit_name_n, Cls[class_name]]
                    activeUnit = ActiveUnit[unit, user, 1]
                    total_correct += activeUnit.totalCorrect
                    total_solved += activeUnit.currentQuestion

                    unit_name_n += "n"
            except Exception as e:
                print("does not exists " + str(e))

            grade = int(((total_correct / total_solved) * 100))
            return grade


    except Exception as e:
        print(e)
        return str(e), 400


class userCont:

    def __init__(self, username):
        self.username = username
        self.typ = 0


class studentCont(userCont):

    def __init__(self, username):
        self.username = username
        self.typ = 2

    def registerClass(self, Cname):
        return "registerClass", Cname

    def getClassUnits(self, Cname):
        return "getClassUnits", Cname

    # def getUnit(self, Uname):
    #     return "getUnit", Uname

    def startUnit(self, Uname):
        return "startUnit", Uname

    def getQuestion(self, Uname, Qnum):
        return "getQuestion", Uname, Qnum

    def answerQuestion(self, Uname, Qnum, answer):
        return "answerQuestion", Uname, Qnum, answer

    def submitUnit(self, Uname):
        return "submitUnit", Uname


class teacherCont(userCont):

    def __init__(self, username):
        self.username = username
        self.typ = 1

    def openUnit(self, Uname, cls, template, Qnum, maxTime, subDate):
        # add open unit logic
        return "openUnit" + Uname + cls + template + Qnum + maxTime + subDate

    def editUnit(self, Uname, cls, newUname, template, Qnum, maxTime, subDate):
        return "editUnit", Uname, cls, newUname, template, Qnum, maxTime, subDate

    # def getUnit(self, Uname):
    #     return "getUnit" + " " + Uname

    def deleteUnit(self, Uname):
        return "deleteUnit", Uname

    def openClass(self, Cname):
        return "openClass", Cname


if __name__ == '__main__':
    app.run()
