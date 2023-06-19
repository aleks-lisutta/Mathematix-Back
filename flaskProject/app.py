import logging
import math
import random
import traceback
from datetime import datetime
from flask import Flask, request, jsonify, make_response
from collections.abc import Iterable
from flask_pony import Pony
from flask_cors import CORS
from pony.orm import *
import json
import pony.orm as pony
from flask import jsonify
import numpy as np

# import random
from math import inf, e
# import time
#
from sympy import symbols, Poly, Pow, ln, sin, cos, tan, cot, degree, diff, solve, log, N, pi, Add, Rational, Mul, sign, \
    I, Union, Interval, root, S, sympify
from sympy.calculus.util import continuous_domain

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
    solve_time = Optional(str)
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
    if username not in activeControllers.keys():
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
        return username + " " + str(password) + " " + str(typ), 200
    return ans, 400


def checkUserPass(username, password):
    try:
        with db_session:
            result = User[username]
            if result:
                return result.password == password
            return False
    except Exception as e:
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
    try:
        loadController(username)
        if isinstance(activeControllers[username], teacherCont):
            return str(1) + " " + username
        return str(2) + " " + username
    except Exception as e:
        return False


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
        activeControllers.pop(username)
    return username + " " + str(len(activeControllers))


@app.route('/getOnlineStudentsOfTeacher')
def getOnlineStudentsOfTeacher():
    teacher = request.args.get('teacher')
    if not isTeacher(teacher) or not isLogin(teacher):
        return 'Error: Either user is not a teacher or is not logged in', 400
    return getOnlineStudentsOfTeacher_business(teacher)


# This function returns all online students from all of {teacher}'s classes.
#
# Return format:
# Dictionary of - student names -> list of class names
# For example: {'john': ['class1', 'class2'], 'doe': []}
# (Both john and doe are online, and have been approved to the class)
def getOnlineStudentsOfTeacher_business(teacher):
    with db_session:
        classes = Cls.select(lambda c: c.teacher.name == teacher)[:].to_list()
        classes_users = []
        for cls in classes:
            cls_users = Cls_User.select(lambda cu: (cu.cls == cls) and cu.approved)[:].to_list()
            classes_users.extend(cls_users)

        ret_dic = {}
        for cls_user in classes_users:
            if cls_user.user.name not in ret_dic:
                ret_dic[cls_user.user.name] = []
            if cls_user.user.name in activeControllers:
                ret_dic[cls_user.user.name].append(cls_user.cls.name)

        ret = []
        i = 0
        for name in ret_dic:
            single_obj = dict()
            single_obj["id"] = i
            single_obj["username"] = name
            # single_obj["secondary"] = ret_dic[name]
            single_obj["isLoggedIn"] = len(ret_dic[name]) > 0
            ret.append(single_obj)
            # ret.append({'id': i, 'primary': name, 'secondary': ret_dic[name], 'online': len(ret_dic[name]) > 0})
            i += 1

    return ret


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
            while u.next:
                t = Unit[u.next, Cls[className]]
                u.delete()
                u = t
            u.delete()
            commit()
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
    try:
        return getUnapprovedStudents_buisness(teacher)
    except Exception as e:
        return str(e), 400


def getUnapprovedStudents_buisness(teacher):
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
        return getClassesStudent_buisness(student)
    except Exception as e:
        return str(e), 400


def getClassesStudent_buisness(student):
    try:
        with db_session:
            ret = []
            id = 0
            for aUnit in Cls_User.select(user=student, approved=True):
                single_obj = dict()
                id += 1
                single_obj["id"] = id
                single_obj["primary"] = aUnit.cls.name
                single_obj["secondary"] = ""
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
        return getClassesTeacher_buisness(teacher)
    except Exception as e:
        print(e)
        return str(e), 400


def getClassesTeacher_buisness(teacher):
    try:
        with db_session:
            ret = []
            id = 0
            for aUnit in Cls.select(teacher=teacher):
                single_obj = dict()
                id += 1
                single_obj["id"] = id
                single_obj["primary"] = aUnit.name
                single_obj["secondary"] = ""
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


def parse_template(template):
    parts = template.split('_')
    questions = parts[0].split(',')
    params = parts[2].split(',')
    if len(parts) == 3:
        return questions, parts[1], params
    integral_range = parts[3].split(',')
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


def func_value_question(domain, f, fString):
    preamble = "חשב מה ערך הפונקציה בנקודה"
    if (len(domain) == 0) or (len(domain) == 1 and len(domain[0]) == 0):
        ans1 = "הפונקציה לא מוגדרת בנקודה"
        ans2 = round(random.randint(-10000, 10000) / 1000, 2)
        ans3 = round(random.randint(-20000, 20000) / 567, 2)
        ans4 = round(random.randint(-500, 500) + random.uniform(0.0, 1.0), 2)
        x = round(random.uniform(-20, 20), 2)
        preamble = "x={} ".format(x) + preamble
    else:
        x = round(random.uniform(domain[0][0], domain[0][1]), 2)
        preamble = "x={} ".format(x) + preamble
        ans1 = round(f(x), 2) if f(x) else "הפונקציה לא מוגדרת בנקודה"
        to_put_no_solution = random.randint(1, 4)
        ans2 = round((f(x) if f(x) else random.randint(1, 5)) + random.randint(1, 5) + random.uniform(0.0, 0.99), 2)
        if to_put_no_solution == 1:
            ans2 = 'הפונקציה לא מוגדרת בנקודה'
        ans3 = round((f(x) if f(x) else random.randint(1, 5)) + random.randint(-5, -1) + random.uniform(-0.99, 0.0), 2)
        ans4 = round((f(x) if f(x) else random.randint(1, 5)) + random.randint(7, 20), 2)
        if domain[0][0] < x + 1 < domain[0][1]:
            if f(x + 1) != ans1:
                ans4 = f(x + 1)
    q = (
        preamble, fString, ans1, ans2,
        ans3,
        ans4, 0)
    return q


def find_real_domain(p, c):
    return [(round(x, 2), round(y, 2)) for x, y in makeDomain(p, c)]


def make_sympy_poly(p):
    x = symbols('x')
    return Poly(p, x).as_expr(), x


def make_sympy_function(p, c, b):
    if c == 0:
        return make_sympy_poly(p)
    elif c == 1:
        expr, x = make_sympy_poly(p[:-1])
        return Pow(b, expr) + p[-1], x
    elif c == 2:
        expr, x = make_sympy_poly(p[:-1])
        return ln(expr) + p[-1], x
    elif c == 3:
        expr, x = make_sympy_poly(p[:-1])
        return sin(expr) + p[-1], x
    elif c == 4:
        expr, x = make_sympy_poly(p[:-1])
        return cos(expr) + p[-1], x
    elif c == 5:
        expr, x = make_sympy_poly(p[:-1])
        return tan(expr) + p[-1], x
    elif c == 6:
        expr, x = make_sympy_poly(p[:-1])
        return cot(expr) + p[-1], x
    elif c == 7:
        numerator, x = make_sympy_poly(p[:len(p) // 2])
        denominator, x = make_sympy_poly(p[len(p) // 2:])
        return numerator / denominator, x
    elif c == 8:
        expr, x = make_sympy_poly(p[:-1])
        return root(expr, b) + p[-1], x


def filter_and_generate_correct_answers_for_sym(expr, sym_expr, ans, x, c, domains, sym):
    MAX_CS_TO_ADD = 100

    def check_in_range(val):
        for dom in domains:
            if dom[0] <= val <= dom[1]:
                return True
        return False

    possible_cs = list(map(lambda elem: elem[c],
                           list(filter(lambda elem: c in elem and not elem[c].has(I) and not elem[c].has(x),
                                       ans))))
    possible_xs = list(map(lambda elem: elem[x],
                           list(filter(
                               lambda elem: x in elem and elem[x] != 0 and not elem[x].has(I) and not elem[x].has(x),
                               ans))))
    possible_cs_in_range = list(filter(lambda elem: check_in_range(elem), possible_cs))
    -6
    x ^ 3 - 4
    x ^ 2 + 9
    x + 8
    epsilon = 0.0001
    all_possible_cs_in_range = set(possible_cs_in_range)
    for possible_c in possible_cs_in_range:
        for possible_x in possible_xs:
            for i in range(1, MAX_CS_TO_ADD + 1):  # Add multiples of x to c
                new_c = possible_c + possible_x * i
                if check_in_range(new_c) and \
                        (sym == 'symmetry' and expr.subs(x, new_c + epsilon) == expr.subs(x, new_c - epsilon) or
                         sym == 'asymmetry' and expr.subs(x, new_c + epsilon) == -expr.subs(x, new_c - epsilon)):
                    all_possible_cs_in_range.add(new_c)
                else:
                    break
            for i in range(1, MAX_CS_TO_ADD + 1):  # Subtract multiples of x from c
                new_c = possible_c - possible_x * i
                if check_in_range(new_c) and \
                        (sym == 'symmetry' and expr.subs(x, new_c + epsilon) == expr.subs(x, new_c - epsilon) or
                         sym == 'asymmetry' and expr.subs(x, new_c + epsilon) == -expr.subs(x, new_c - epsilon)):
                    all_possible_cs_in_range.add(new_c)
                else:
                    break
    epsilon = 0.0001
    for i in range(len(domains) - 1):
        if domains[i][1] == domains[i + 1][0]:
            left_of_asymptote = expr.subs(x, domains[i][1] - epsilon)
            right_of_asymptote = expr.subs(x, domains[i][1] + epsilon)
            if left_of_asymptote == right_of_asymptote or left_of_asymptote == -right_of_asymptote:
                all_possible_cs_in_range.add(domains[i][1])

    expr_domain = continuous_domain(expr, x, S.Reals)
    for pos_c in possible_cs:
        if not pos_c.has(x) and (-pos_c not in expr_domain or sym_expr.subs(c, -pos_c) == 0):
            all_possible_cs_in_range.add(-pos_c)

    return all_possible_cs_in_range


def check_special_cases_symmetry(expr, x):
    def filter_complex(arr):
        return list(filter(lambda x: not x.has(I), arr))

    if len(expr.args) == 2:
        if x in expr.as_coefficients_dict() and 1 in expr.as_coefficients_dict():
            val = solve(expr)
            return [val[0]], 'אסימטריה'

    if expr.has(log) or expr.has(ln):
        if degree(expr.args[0]) == 2:  # Special log case. log(x^2...)
            poly_tag = diff(expr.args[0])
            val = solve(poly_tag, x)
            val = filter_complex(val)
            if len(val) == 0:
                return [], 'אין סימטריה'
            return [val[0]], 'סימטריה'
        if degree(expr.args[0]) == 1:  # Special log case. log(x...)
            return [], 'אין סימטריה'
    if len(expr.args) > 1 and (expr.args[1].has(log) or expr.args[1].has(ln)):
        if degree(expr.args[1].args[0]) == 2:  # Special log case. log(x^2...) + d
            poly_tag = diff(expr.args[1].args[0])
            val = solve(poly_tag, x)
            val = filter_complex(val)
            if len(val) == 0:
                return [], 'אין סימטריה'
            return [val[0]], 'סימטריה'
        if degree(expr.args[1].args[0]) == 1:  # Special log case. log(x...) + d
            return [], 'אין סימטריה'

    if expr.is_Pow:
        if degree(expr.args[1]) == 2:  # Special Pow case. Pow(x^2...)
            poly_tag = diff(expr.args[1])
            val = solve(poly_tag, x)
            val = filter_complex(val)
            if len(val) == 0:
                return [], 'אין סימטריה'
            return [val[0]], 'סימטריה'
        if degree(expr.args[1]) == 1:  # Special Pow case. Pow(x...)
            return [], 'אין סימטריה'
        if expr.args[1].is_Rational:  # Special root case. root(x^2...)
            if expr.args[1].denominator % 2 == 0 and degree(expr.args[0]) == 1:
                return [], 'אין סימטריה'
            poly_tag = diff(expr.args[0])
            val = solve(poly_tag, x)
            val = filter_complex(val)
            if len(val) == 0:
                return [], 'אין סימטריה'
            return [val[0]], 'סימטריה'
    if len(expr.args) > 1 and expr.args[1].is_Pow:
        if degree(expr.args[1].args[1]) == 2:  # Special Pow case. Pow(x^2...) + d
            poly_tag = diff(expr.args[1].args[1])
            val = solve(poly_tag, x)
            val = filter_complex(val)
            if len(val) == 0:
                return [], 'אין סימטריה'
            return [val[0]], 'סימטריה'
        if degree(expr.args[1].args[1]) == 1:  # Special Pow case. Pow(x...) + d
            return [], 'אין סימטריה'
        if expr.args[1].args[1].is_Rational:  # Special root case. root(x^2...) + d
            if expr.args[1].args[1].denominator % 2 == 0 and degree(expr.args[1].args[0]) == 1:
                return [], 'אין סימטריה'
            poly_tag = diff(expr.args[1].args[0])
            val = solve(poly_tag, x)
            val = filter_complex(val)
            if len(val) == 0:
                return [], 'אין סימטריה'
            return [val[0]], 'סימטריה'

    if expr.has(sin) or expr.has(cos) or expr.has(tan) or expr.has(cot):
        trig_func = None
        if expr.is_Mul:
            trig_func = expr.args[1].args[0]
        elif expr.is_Add:
            if expr.args[1].is_Mul:
                trig_func = expr.args[1].args[1].args[0]
            else:
                trig_func = expr.args[1].args[0]
        else:
            trig_func = expr.args[0]
        if degree(trig_func) == 2:  # Special trig case. trig(x^2...)
            poly_tag = diff(trig_func)
            val = solve(poly_tag, x)
            val = filter_complex(val)
            if len(val) == 0:
                return [], 'אין סימטריה'
            return [val[0]], 'סימטריה'
        if degree(trig_func) == 1:  # Special trig case. trig(x...)
            x_coeff = trig_func.coeff(x)
            frequency = 2 * pi / x_coeff
            val = solve(trig_func, x)
            val = filter_complex(val)
            if len(val) == 0:
                return [], 'אין סימטריה'
            if expr.has(cos):
                return frequency, val[0], 'cos'
            elif expr.has(sin):
                return frequency, val[0], 'sin'
            elif expr.has(tan):
                return frequency, val[0], 'tan'
            else:
                return frequency, val[0], 'cot'

    return None


def generate_answers_symmetry_special_cases(frequency, point, jumps, check_in_range):
    MAX_TO_ADD = 100
    ans = []
    for i in range(1, MAX_TO_ADD + 1):  # Subtract multiples of frequency from point
        if not jumps(i):
            continue
        new_point = point - frequency * i
        if check_in_range(new_point):
            ans.append(new_point)
        else:
            break
    for i in range(1, MAX_TO_ADD + 1):  # Add multiples of frequency from point
        if not jumps(i):
            continue
        new_point = point + frequency * i
        if check_in_range(new_point):
            ans.append(new_point)
        else:
            break
    return ans


def get_answers_for_symmetry_asymmetry(expr, x, c, domains):
    if len(domains) == 0:
        return [], 'אין סימטריה'

    if expr.is_number:
        return [], 'סימטריה לכל x'

    def check_in_range(val):
        for dom in domains:
            if dom[0] <= val <= dom[1]:
                return True
        return False

    special_case = check_special_cases_symmetry(expr, x)
    if special_case is not None:
        if len(special_case) == 3:
            MAX_TO_ADD = 100
            ans = []
            if special_case[2] == 'tan' or special_case[2] == 'cot':
                ans = generate_answers_symmetry_special_cases(special_case[0] / 4, special_case[1],
                                                              lambda x: True, check_in_range)
                return ans, 'אסימטריה'
            if special_case[2] == 'sin':
                if random.choice([True, False]):
                    # Symmetry
                    ans = generate_answers_symmetry_special_cases(special_case[0] / 4, special_case[1],
                                                                  lambda x: x % 2 == 1, check_in_range)
                    return ans, 'סימטריה'
                else:
                    # Asymmetry
                    ans = generate_answers_symmetry_special_cases(special_case[0] / 4, special_case[1],
                                                                  lambda x: x % 2 == 0, check_in_range)
                    return ans, 'אסימטריה'
        else:
            return special_case

    expr_x = expr.subs(x, x + c)
    expr_neg_x = expr.subs(x, -x + c)
    neg_expr_neg_x = -expr.subs(x, -x + c)
    ans = []
    sym_expr = expr_x - expr_neg_x
    try:
        ans = solve(sym_expr)
    except Exception as e:
        pass
    if ans != [{x: 0}] and len(ans) > 0 and (type(ans) == float or type(ans) == float):
        symmetries = filter_and_generate_correct_answers_for_sym(expr, sym_expr, ans, x, c, domains, 'symmetry')
        if len(symmetries) > 0 and ans != [{x: 0}]:
            return list(map(lambda x: round(float(N(x)), 3), symmetries)), 'סימטריה'

    sym_expr = expr_x - neg_expr_neg_x
    try:
        ans = solve(sym_expr)
    except Exception as e:
        pass
    if ans != [{x: 0}] and len(ans) > 0 and (type(ans) == float or type(ans) == float):
        asymmetries = filter_and_generate_correct_answers_for_sym(expr, sym_expr, ans, x, c, domains, 'asymmetry')
        if len(asymmetries) > 0 and ans != [{x: 0}]:
            return list(map(lambda x: round(float(N(x)), 3), asymmetries)), 'אסימטריה'

    return [], 'אין סימטריה'


def filter_and_generate_answers_for_inflection(ans, expr_tagtag, x, domains):
    def check_in_range(val):
        for dom in domains:
            if dom[0] < val < dom[1]:
                return True
        return False

    n = symbols('n')
    MAX_TO_ADD = 100
    is_trigonometric = False
    new_ans = []
    if expr_tagtag.has(sin):
        for sub_expr in expr_tagtag.args:
            if sub_expr.has(sin):
                sin_expr = sub_expr
                new_ans_1 = solve(sin_expr.args[0] - 0 - 2 * pi * n, x)
                new_ans_2 = solve(sin_expr.args[0] - pi - 2 * pi * n, x)
                new_ans += new_ans_1 + new_ans_2
        is_trigonometric = True
    elif expr_tagtag.has(cos):
        for sub_expr in expr_tagtag.args:
            if sub_expr.has(cos):
                cos_expr = sub_expr
                new_ans_1 = solve(cos_expr.args[0] - pi / 2 - 2 * pi * n, x)
                new_ans_2 = solve(cos_expr.args[0] - 3 * pi / 2 - 2 * pi * n, x)
                new_ans += new_ans_1 + new_ans_2
        is_trigonometric = True
    elif expr_tagtag.has(tan):
        for sub_expr in expr_tagtag.args:
            if sub_expr.has(tan):
                tan_expr = sub_expr
                new_ans += solve(tan_expr.args[0] - 0 - pi * n, x)
        is_trigonometric = True
    elif expr_tagtag.has(cot):
        for sub_expr in expr_tagtag.args:
            if sub_expr.has(cot):
                cot_expr = sub_expr
                new_ans += solve(cot_expr.args[0] - pi / 2 - pi * n, x)
        is_trigonometric = True

    if is_trigonometric:
        for ans_template in new_ans:
            check_2_deep = True
            for sub_n in range(MAX_TO_ADD):
                check_pos_sub_n = check_in_range(ans_template.subs(n, sub_n))
                check_neg_sub_n = check_in_range(ans_template.subs(n, -sub_n))
                if not check_pos_sub_n and not check_neg_sub_n:
                    if check_2_deep:
                        check_2_deep = False
                    else:
                        break
                if check_pos_sub_n:
                    ans.append(ans_template.subs(n, sub_n))
                if check_neg_sub_n:
                    ans.append(ans_template.subs(n, -sub_n))

    ans = list(set(ans))

    return list(filter(lambda elem: not sympify(elem).has(I) and check_in_range(elem), ans))


def get_possible_inflection_points(expr_tagtag, x, domains):
    ans = []
    try:
        ans = solve(expr_tagtag)
    except Exception as e:
        return ans

    union = Union()
    for (left, right) in domains:
        union = Union(union, Interval.open(left, right))

    for i in range(len(domains) - 1):
        if domains[i][1] == domains[i + 1][0]:
            ans.append(domains[i][1])

    # try:
    #     asymptotes = continuous_domain(expr_tagtag, x, union).boundary
    #     ans.extend(asymptotes)
    # except:
    #     pass

    return filter_and_generate_answers_for_inflection(ans, expr_tagtag, x, domains)


def get_answers_for_inflection_points(possible_inflection_points, domains, expr_tagtag, x):
    epsilon = 0.0001

    for i in range(len(domains) - 1):
        if domains[i][1] == domains[i + 1][0]:
            left_of_asymptote = expr_tagtag.subs(x, domains[i][1] - epsilon)
            right_of_asymptote = expr_tagtag.subs(x, domains[i][1] + epsilon)
            if sign(left_of_asymptote) != sign(right_of_asymptote):
                possible_inflection_points.append(domains[i][1])

    sorted_possible_points = list(sorted(possible_inflection_points))
    sorted_domains = list(sorted(domains, key=lambda x: x[0]))
    inflection_points = []

    for i in range(len(sorted_possible_points)):
        possible_point = sorted_possible_points[i]
        for domain in sorted_domains:
            if domain[0] < possible_point < domain[1]:
                prev_possible_point = sorted_possible_points[i - 1] + epsilon if i > 0 \
                    else domain[0] + epsilon
                next_possible_point = sorted_possible_points[i + 1] - epsilon if i < len(sorted_possible_points) - 1 \
                    else domain[1] - epsilon
                region_before = expr_tagtag.subs(x, prev_possible_point)
                region_after = expr_tagtag.subs(x, next_possible_point)
                if sign(region_before) != sign(region_after):
                    inflection_points.append(N(possible_point))

    return list(map(lambda x: round(float(N(x)), 3), inflection_points))


# POSSIBLY REDUNDANT
def merge_regions(regions):
    if len(regions) == 0:
        return []

    regions.sort()
    stack = [regions[0]]
    for i in regions[1:]:
        if stack[-1][0] <= i[0] <= stack[-1][-1]:
            stack[-1][-1] = max(stack[-1][-1], i[-1])
        else:
            stack.append(i)
    return list(map(lambda x: tuple(x), stack))


def get_answers_for_concave_convex(possible_inflection_points, domains, expr_tagtag, x):
    if expr_tagtag == 0 or len(domains) == 0:
        return {'convex': [], 'concave': []}

    asymptotes = set()
    for i in range(len(domains) - 1):
        if domains[i][1] == domains[i + 1][0]:
            asymptotes.add(domains[i][1])
    asymptotes = list(asymptotes)

    convex_regions = set()
    concave_regions = set()
    if len(possible_inflection_points) == 0:
        for domain in domains:
            if expr_tagtag.subs(x, (domain[0] + domain[1]) / 2) > 0:
                convex_regions.add(domain)
            else:
                concave_regions.add(domain)
        return {'convex': list(map(lambda x: tuple(x), convex_regions)),
                'concave': list(map(lambda x: tuple(x), concave_regions))}

    possible_inflection_points.extend(asymptotes)

    sorted_possible_points = list(sorted(possible_inflection_points))
    sorted_domains = list(sorted(domains, key=lambda x: x[0]))

    for i in range(len(sorted_possible_points)):
        possible_point = sorted_possible_points[i]
        for domain in sorted_domains:
            if domain[0] < possible_point < domain[1]:
                prev_possible_point = sorted_possible_points[i - 1] if i > 0 \
                    else domain[0]
                next_possible_point = sorted_possible_points[i + 1] if i < len(sorted_possible_points) - 1 \
                    else domain[1]
                region_before = expr_tagtag.subs(x, (possible_point + prev_possible_point) / 2)
                region_before_calculated = rec_calc_evaluation(region_before)
                region_after = expr_tagtag.subs(x, (possible_point + next_possible_point) / 2)
                region_after_calculated = rec_calc_evaluation(region_after)
                reg_1 = round(float(N(prev_possible_point)), 3)
                reg_2 = round(float(N(possible_point)), 3)
                reg_3 = round(float(N(next_possible_point)), 3)
                if sign(region_before_calculated) == 1:
                    convex_regions.add((reg_1, reg_2))
                else:
                    concave_regions.add((reg_1, reg_2))
                if sign(region_after_calculated) == 1:
                    convex_regions.add((reg_2, reg_3))
                else:
                    concave_regions.add((reg_2, reg_3))

    return {'convex': list(map(lambda x: tuple(x), convex_regions)),
            'concave': list(map(lambda x: tuple(x), concave_regions))}


def odd_even_special_cases(expr, x):
    if expr.has(sin) or expr.has(tan) or expr.has(cot) or expr.has(cos):
        if expr.is_Mul:
            trig_func = expr.args[1].args[0]
        elif expr.is_Add:
            if expr.args[1].is_Mul:
                trig_func = expr.args[1].args[1].args[0]
            else:
                trig_func = expr.args[1].args[0]
        else:
            trig_func = expr.args[0]
        if expr.has(sin) or expr.has(tan) or expr.has(cot):
            if trig_func.coeff(x ** 2) == 0:  # tan/sin/cot(x...)
                if 1 in trig_func.as_coefficients_dict():  # cos(x + d)
                    return 'לא זוגית ולא אי זוגית'
                else:
                    return 'אי זוגית'
            elif trig_func.coeff(x ** 2) != 0 and trig_func.coeff(x) != 0:  # tan/sin/cot(x^2+x...)
                return 'לא זוגית ולא אי זוגית'
            elif trig_func.coeff(x ** 2) != 0 and trig_func.coeff(x) == 0:  # tan/sin/cot(x^2...)
                return 'זוגית'
        else:
            if trig_func.coeff(x ** 2) == 0:  # cos(x...)
                if 1 in trig_func.as_coefficients_dict():  # cos(x + d)
                    return 'לא זוגית ולא אי זוגית'
                else:
                    return 'אי זוגית'
            elif trig_func.coeff(x ** 2) != 0 and trig_func.coeff(x) != 0:  # cos(x^2+x...)
                return 'לא זוגית ולא אי זוגית'
            elif trig_func.coeff(x ** 2) != 0 and trig_func.coeff(x) == 0:  # cos(x^2...)
                return 'זוגית'
    if expr.is_Pow:
        if degree(expr.args[1]) == 2:  # Pow(x^2...)
            if expr.args[1].coeff(x) == 0:
                return 'זוגית'
            else:
                return 'לא זוגית ולא אי זוגית'
        if degree(expr.args[1]) == 1:  # Pow(x...)
            return 'לא זוגית ולא אי זוגית'
        if expr.args[1].is_Rational:  # root(x^2...)
            if expr.args[0].coeff(x ** 2) != 0 and expr.args[0].coeff(x) != 0:
                return 'לא זוגית ולא אי זוגית'
            elif expr.args[0].coeff(x ** 2) != 0 and expr.args[0].coeff(x) == 0:
                return 'זוגית'
            else:
                if expr.args[1].denominator % 2 == 0:
                    return 'לא זוגית ולא אי זוגית'
                else:
                    return 'אי זוגית'
    if len(expr.args) > 1 and expr.args[1].is_Pow:
        if degree(expr.args[1].args[1]) == 2:  # Pow(x^2...) + d
            if expr.args[1].args[1].coeff(x) == 0:
                return 'זוגית'
            else:
                return 'לא זוגית ולא אי זוגית'
        if degree(expr.args[1].args[1]) == 1:  # Pow(x...) + d
            return 'לא זוגית ולא אי זוגית'
        if expr.args[1].args[1].is_Rational:  # root(x^2...) + d
            if expr.args[1].args[0].coeff(x ** 2) != 0 and expr.args[1].args[0].coeff(x) != 0:
                return 'לא זוגית ולא אי זוגית'
            elif expr.args[1].args[0].coeff(x ** 2) != 0 and expr.args[1].args[0].coeff(x) == 0:
                return 'זוגית'
            else:
                if expr.args[1].args[1].denominator % 2 == 0:
                    return 'לא זוגית ולא אי זוגית'
                else:
                    return 'אי זוגית'
    if expr.has(log) or expr.has(ln):
        if degree(expr.args[0]) == 2:  # log(x^2...)
            if expr.args[0].coeff(x) == 0:
                return 'זוגית'
            else:
                return 'לא זוגית ולא אי זוגית'
        if degree(expr.args[0]) == 1:  # log(x...)
            return 'לא זוגית ולא אי זוגית'
    if len(expr.args) > 1 and (expr.args[1].has(log) or expr.args[1].has(ln)):
        if degree(expr.args[1].args[0]) == 2:  # log(x^2...) + d
            if expr.args[1].args[0].coeff(x) == 0:
                return 'זוגית'
            else:
                return 'לא זוגית ולא אי זוגית'
        if degree(expr.args[1].args[0]) == 1:  # log(x...) + d
            return 'לא זוגית ולא אי זוגית'

    return None


def get_answers_for_odd_even(expr, x, domains):
    if len(domains) == 0:
        return 'לא זוגית ולא אי זוגית'

    special_cases = odd_even_special_cases(expr, x)
    if special_cases is not None:
        return special_cases

    rand_value = (domains[0][0] + domains[0][1]) / 2
    is_even = len(solve(expr - expr.subs(x, -x))) == 0 and \
              expr.subs(x, rand_value) == expr.subs(x, -rand_value)
    is_odd = len(solve(expr + expr.subs(x, -x))) == 0 and \
             expr.subs(x, rand_value) == -expr.subs(x, -rand_value)
    if is_even and is_odd:
        return 'גם זוגית וגם אי זוגית'
    elif is_even:
        return 'זוגית'
    elif is_odd:
        return 'אי זוגית'
    else:
        return 'לא זוגית ולא אי זוגית'


def rec_calc_evaluation(to_calc):
    if type(to_calc) == Mul:
        ret = '('
        for arg in to_calc.args:
            ret += rec_calc_evaluation(arg) + '*'
        ret = ret[:-1]
        return ret + ')'
    elif type(to_calc) == Pow:
        base = rec_calc_evaluation(to_calc.args[0])
        expo = rec_calc_evaluation(to_calc.args[1])
        return f'{base}**{expo}'
    elif type(to_calc) == Add:
        ret = '('
        for arg in to_calc.args:
            ret += rec_calc_evaluation(arg) + '+'
        ret = ret[:-1]
        return ret + ')'
    elif type(to_calc) == Rational:
        return f'{to_calc.p}/{to_calc.q}'
    else:
        return f'({to_calc})'


def generate_random_answer_symmetry(options, expr, x):
    fake_ans = random.choice(options)
    too_long_trigger = 5
    while fake_ans in options:
        choice = random.choice(options)
        fake_ans = choice + random.uniform(-3, 3)
        if too_long_trigger == 0:
            return round(fake_ans, 3), random.choice(['סימטריה', 'אסימטריה'])
        too_long_trigger -= 1
    return round(fake_ans, 3), random.choice(['סימטריה', 'אסימטריה'])


def generate_fake_answers_symmetry(real_options, expr, x):
    options, desc = real_options
    real_ans = round(random.choice(options), 3) if len(options) > 0 else None, desc
    if len(options) != 0:
        answer_1 = None, 'אין סימטריה'
        answer_2 = generate_random_answer_symmetry(options, expr, x)
        answer_3 = generate_random_answer_symmetry(options, expr, x)
        return real_ans, answer_1, answer_2, answer_3
    else:
        options = [round(random.uniform(-20, 20), 3) for _ in range(20)]
        answer_1 = generate_random_answer_symmetry(options, expr, x)
        answer_2 = generate_random_answer_symmetry(options, expr, x)
        answer_3 = generate_random_answer_symmetry(options, expr, x)
        return real_ans, answer_1, answer_2, answer_3


def generate_random_answer_inflection(real_points, expr, x, domains):
    def check_in_range(val):
        for dom in domains:
            if dom[0] < val < dom[1]:
                return True
        return False

    fake_ans = -inf
    too_long_trigger = 5
    while fake_ans in real_points or not check_in_range(fake_ans):
        choice = random.choice(real_points)
        fake_ans = choice * random.randint(-2, 2)
        if too_long_trigger == 0:
            return round(fake_ans, 3), round(choice * fake_ans, 3)
        too_long_trigger -= 1
    try:
        y_val = round(float(N(expr.subs(x, fake_ans))), 3)
        return round(fake_ans, 3), y_val
    except:
        return round(fake_ans, 3), round(random.uniform(-2, 2) * fake_ans, 3)


def generate_fake_answers_inflection(real_points, expr, x, domains):
    real_ans = random.choice(real_points) if len(real_points) > 0 else None
    if real_ans is not None:
        real_ans = (real_ans, round(float(N(expr.subs(x, real_ans))), 3))
    else:
        real_ans = 'אין נקודות פיתול'
    if len(real_points) != 0:
        answer_1 = 'אין נקודות פיתול'
        answer_2 = generate_random_answer_inflection(real_points, expr, x, domains)
        answer_3 = generate_random_answer_inflection(real_points, expr, x, domains)
        return real_ans, answer_1, answer_2, answer_3
    else:
        options = [round(random.uniform(-20, 20), 3) for _ in range(20)]
        answer_1 = generate_random_answer_inflection(options, expr, x, domains)
        answer_2 = generate_random_answer_inflection(options, expr, x, domains)
        answer_3 = generate_random_answer_inflection(options, expr, x, domains)
        return real_ans, answer_1, answer_2, answer_3


def generate_random_answer_convex_concave(min_val, max_val, fake_min, fake_max):
    temp_max_val = max_val
    temp_min_val = min_val
    if max_val == inf:
        temp_max_val = fake_min
    if min_val == -inf:
        temp_min_val = fake_max
    number_of_splits = random.choice([2, 3, 4])
    all_splits = sorted([temp_min_val, temp_max_val] +
                        [round(random.uniform(temp_min_val, temp_max_val), 3) for _ in range(number_of_splits)])
    all_splits = list(map(lambda elem: max_val if elem == temp_max_val else (min_val if elem == temp_min_val else elem),
                          all_splits))
    fake_convex = []
    fake_concave = []
    for i in range(number_of_splits + 1):
        if random.choice([True, False]):
            fake_convex.append((all_splits[i], all_splits[i + 1]))
        else:
            fake_concave.append((all_splits[i], all_splits[i + 1]))
    return '\u222A: {convex}\n\u2229: {concave}'.format(convex=fake_convex, concave=fake_concave)


def return_domain_to_inf(domains, bottom_val, top_val, real_bottom, real_top):
    new_domains = []
    for dom in domains:
        new_dom = list(dom)
        if dom[0] == bottom_val:
            new_dom[0] = real_bottom
        if dom[1] == top_val:
            new_dom[1] = real_top
        new_domains.append(tuple(new_dom))
    return new_domains


def generate_fake_answers_convex_concave(real_regions, domains):
    min_val = inf
    max_val = -inf
    for dom in domains:
        if dom[0] < min_val:
            min_val = dom[0]
        if dom[1] > max_val:
            max_val = dom[1]
    convex, concave = real_regions['convex'], real_regions['concave']
    convex = return_domain_to_inf(convex, -100, 100, min_val, max_val)
    concave = return_domain_to_inf(concave, -100, 100, min_val, max_val)
    if len(domains) != 1:
        answer_1 = generate_random_answer_convex_concave(min_val, max_val, -100, 100)
        answer_2 = generate_random_answer_convex_concave(min_val, max_val, -100, 100)
        answer_3 = generate_random_answer_convex_concave(min_val, max_val, -100, 100)
        return '\u222A: {convex}\n\u2229: {concave}'.format(convex=convex, concave=concave), \
               answer_1, \
               answer_2, \
               answer_3
    else:
        answer_1 = generate_random_answer_convex_concave(min_val, max_val, -10, 10)
        answer_2 = generate_random_answer_convex_concave(min_val, max_val, -10, 10)
        answer_3 = generate_random_answer_convex_concave(min_val, max_val, -10, 10)
        return '\u222A: {convex}\n\u2229: {concave}'.format(convex=convex, concave=concave), \
               answer_1, \
               answer_2, \
               answer_3


def generate_fake_answers_odd_even(ans):
    all_options = {'גם זוגית וגם אי זוגית', 'זוגית', 'אי זוגית', 'לא זוגית ולא אי זוגית'}
    fake_ans = []
    for i in range(3):
        fake_ans.append(random.choice(list(all_options - {ans} - set(fake_ans))))
    return fake_ans


def get_questions(unit):
    intMap = {'linear': 0, 'quadratic': 0, 'polynomial': 0, '2exp': 1, '3exp': 1, 'eexp': 1, 'log': 2, 'sin': 3,
              'cos': 4, 'tan': 5, 'cot': 6, 'rational': 7, 'root': 8, '3root': 8}
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
                              'cot', 'rational', 'root', '3root']:
            c = intMap[function_types]
            b = 2 if function_types == '2exp' else (3 if function_types == '3exp' else math.e)
            if function_types == 'root':
                b = 2
            elif function_types == '3root':
                b = 3
            elif function_types == 'log':
                b = math.e
            p = [random.randint(int(params[2 * i]), int(params[2 * i + 1])) for i in range(int(len(params) / 2))]
            f = makeFunc(p, c, b)
            q = ""
            if ('definiteIntegral' in question):
                q = definite_integral_question(b, c, f, integral_range, p)
                questions.append(q)
            elif ('intersection' in question):
                q = make_intersection_question(b, c, f, p)
            elif ('minMaxPoints' in question):
                q = make_extreme_question(b, c, p)
            elif ('incDec' in question):
                q = make_incDec_question(b, c, p)
            elif ('deriveFunc' in question):
                q = make_derive_question(b, c, p)
            elif ('funcValue' in question):
                domain = makeDomain(p, c)
                q = func_value_question(domain, f, funcString(p, c, b))
            elif ('domain' in question):
                q = make_domain_question(b, c, p)
            elif ('posNeg' in question):
                q = make_pos_neg_question(b, c, p)
            elif ('asym' in question):
                preamble = "חשב מה האסימפטוטות של הפונקציה"
                result1 = makeAsym(p, c, b)
                if not len(result1[0]):
                    result1[0] = "אין אסימפטוטות אנכיות"
                if not len(result1[1]):
                    result1[1] = "אין אסימפטוטות אופקיות"
                result2 = randFillPair(2)
                result3 = randFillPair(2)
                result4 = randFillPair(2)
                q = (
                    preamble, funcString(p, c, b), result1, result2,
                    result3,
                    result4, 0)
            elif ('symmetry' in question):
                if c == 2:
                    b = e
                q = make_symmetry_question(b, c, p)
            elif ('inflection' in question):
                if c == 3 or c == 4 or c == 5 or c == 6:
                    p = [random.randint(int(params[2 * i]), int(params[2 * i + 1])) for i in range(3)]
                if c == 2:
                    b = e
                q = make_inflection_question(b, c, p)
            elif ('convexConcave' in question):
                if c == 3 or c == 4 or c == 5 or c == 6:
                    p = [random.randint(int(params[2 * i]), int(params[2 * i + 1])) for i in range(3)]
                if c == 2:
                    b = e
                q = make_convex_concave_question(b, c, p)
            elif ('oddEven' in question):
                if c == 2:
                    b = e
                q = make_odd_even_question(b, c, p)
            questions.append(q)

    return change_order(questions)


def make_odd_even_question(b, c, p):
    domain = makeDomain(p, c)
    domain_to_use = []
    for dom in domain:
        dom_to_add = list(dom)
        if dom_to_add[0] == -inf:
            dom_to_add[0] = -100
        if dom_to_add[1] == inf:
            dom_to_add[1] = 100
        domain_to_use.append(tuple(dom_to_add))

    expr, x = make_sympy_function(p, c, b)
    ans = get_answers_for_odd_even(expr, x, domain_to_use)
    fake_ans = generate_fake_answers_odd_even(ans)
    real = ans + ' ' + funcString(p, c, b) + 'הפונקציה '
    answer_1 = fake_ans[0] + ' ' + funcString(p, c, b) + 'הפונקציה '
    answer_2 = fake_ans[1] + ' ' + funcString(p, c, b) + 'הפונקציה '
    answer_3 = fake_ans[2] + ' ' + funcString(p, c, b) + 'הפונקציה '
    preamble = 'בחר את בטענה הנכונה בהקשר לזוגיות ואי זוגיות הפונקציה'

    print(expr)

    q = (preamble,
         funcString(p, c, b),
         real,
         answer_1,
         answer_2,
         answer_3,
         0)
    return q


def make_convex_concave_question(b, c, p):
    expr, x = make_sympy_function(p, c, b)
    if c == 3 or c == 4:
        domain = [(-pi, pi)]
    else:
        domain = makeDomain(p, c)
    domain_to_use = []
    for dom in domain:
        dom_to_add = list(dom)
        if dom_to_add[0] == -inf:
            dom_to_add[0] = -100
        if dom_to_add[1] == inf:
            dom_to_add[1] = 100
        domain_to_use.append(tuple(dom_to_add))
    diff_1 = diff(expr, x)
    diff_2 = diff(diff_1, x)

    print(expr)

    points = get_possible_inflection_points(diff_2, x, domain_to_use)
    ans = get_answers_for_concave_convex(points, domain_to_use, diff_2, x)
    real, answer_1, answer_2, answer_3 = generate_fake_answers_convex_concave(ans, domain)

    preamble = 'בחר בתחומי הקמירות והקעירות של הפונקציה'
    q = (preamble,
         funcString(p, c, b),
         real,
         answer_1,
         answer_2,
         answer_3,
         0)
    return q


def make_inflection_question(b, c, p):
    expr, x = make_sympy_function(p, c, b)
    if c == 3 or c == 4:
        domain = [(-pi, pi)]
    else:
        domain = makeDomain(p, c)
    diff_1 = diff(expr, x)
    diff_2 = diff(diff_1, x)

    print(expr)

    points = get_possible_inflection_points(diff_2, x, domain)
    ans = get_answers_for_inflection_points(points, domain, diff_2, x)
    real, answer_1, answer_2, answer_3 = generate_fake_answers_inflection(ans, expr, x, domain)

    preamble = 'בחר בנקודת פיתול אפשרית של הפונקציה'
    q = (preamble,
         funcString(p, c, b),
         real if real is not None else 'אין נקודות פיתול',
         answer_1,
         answer_2,
         answer_3,
         0)
    return q


def make_symmetry_question(b, c, p):
    expr, x = make_sympy_function(p, c, b)
    if c == 3 or c == 4:
        domain = [(-pi, pi)]
    else:
        domain = makeDomain(p, c)
    c_symbol = symbols('c')

    print(expr)

    ans = get_answers_for_symmetry_asymmetry(expr, x, c_symbol, domain)
    real, answer_1, answer_2, answer_3 = generate_fake_answers_symmetry(ans, expr, x)

    preamble = 'בחר בציר סימטריה אנכי אפשרי של הפונקציה'
    q = (preamble,
         funcString(p, c, b),
         real,
         answer_1,
         answer_2,
         answer_3,
         0)
    return q


def make_pos_neg_question(b, c, p):
    pos, neg = makePosNeg(p, c, b)
    preamble = "מצא תחומי חיוביות שליליות"
    p1, n1 = randFillPair(len(pos) + len(neg))
    result2 = (" חיוביות: " + str(p1) + " שליליות: " + str(n1) + " ")
    i1, d1 = randFillPair(len(pos) + len(neg))
    result3 = (" חיוביות: " + str(i1) + " שליליות: " + str(d1) + " ")
    i1, d1 = randFillPair(len(pos) + len(neg))
    result4 = (" חיוביות: " + str(i1) + " שליליות: " + str(d1) + " ")
    q = (
        preamble, funcString(p, c, b), (
            " חיוביות: " + str(n1) if len(n1) else "אין תחומי שליליות" + " שליליות: " + str(p1) if len(
                p1) else "אין תחומי חיוביות" + " "), result2,
        result3,
        result4, 0)
    return q


def definite_integral_question(b, c, f, integral_range, p):
    dom = makeDomain(p, c)
    ranges = []
    for d in dom:
        if integral_range[1] < d[0] or integral_range[0] > d[1]:
            continue
        if integral_range[0] > d[0] and integral_range[1] < d[1]:
            ranges = [integral_range]
            break
        if integral_range[0] > d[0] and integral_range[1] > d[1]:
            ranges.append((integral_range[0], d[1] - 0.001))
        if integral_range[0] < d[0] and integral_range[1] < d[1]:
            ranges.append((d[0] + 0.001, integral_range[1]))

    ans = 0
    for r in ranges:
        ans += integrate(f, r[0], r[1], int((r[1] - r[0]) * 100))
    string_range = str(integral_range[0]) + "," + str(integral_range[1])
    preamble = string_range + "מצא את האינטגרל בתחום: "
    ans2 = ans + random.randint(1, 5)
    ans3 = ans - random.randint(1, 5)
    ans4 = ans + random.randint(7, 12)
    q = (preamble, funcString(p, c, b), ans, ans2, ans3, ans4, 0)
    return q


def make_intersection_question(b, c, f, p):
    if not any(p):
        points = "כל הנקודות"
    else:
        dom = makeDomain(p, c)
        points = makeIntersections(f, c, dom)

        intersect_with_y_axis = False
        for item in points:
            if item[0] == 0:
                intersect_with_y_axis = True
        print("points:",points)
        if (not f(0) is None):
            if (abs(f(0)) >= 0.001) or (not intersect_with_y_axis):
                points.append((0.0, float(round(f(0), 2))))
        else:
            if len(points) == 0:
                points = "אין נקודות חיתוך"

    preamble = "מצא את נקודות החיתוך עם הצירים:"
    ans2 = [(random.randint(-10000, 10000) / 1000, 0.0) for i in range(len(p) - 1)]
    ans2.append((0.0, (random.randint(-10000, 10000) / 1000)))
    ans3 = [(random.randint(-10000, 10000) / 1000, 0.0) for i in range(len(p) - 1)]
    ans3.append((0.0, (random.randint(-10000, 10000) / 1000)))
    ans4 = [(random.randint(-10000, 10000) / 1000, 0.0) for i in range(len(p) - 1)]
    ans4.append((0.0, (random.randint(-10000, 10000) / 1000)))
    q = (preamble, funcString(p, c, b), points, ans2, ans3, ans4, 0)
    return q


def make_derive_question(b, c, p):
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
    return q


def make_incDec_question(b, c, p):
    inc, dec = makeIncDec(p, c, b)
    preamble = "מצא תחומי עלייה וירידה:"
    i1, d1 = randFillPair(len(inc) + len(dec))
    result2 = (" עלייה: " + str(i1) + " ירידה: " + str(d1) + " ")
    i1, d1 = randFillPair(len(inc) + len(dec))
    result3 = (" עלייה: " + str(i1) + " ירידה: " + str(d1) + " ")
    i1, d1 = randFillPair(len(inc) + len(dec))
    result4 = (" עלייה: " + str(i1) + " ירידה: " + str(d1) + " ")
    q = (
        preamble, funcString(p, c, b), (
            " עלייה: " + str(dec) if len(dec) else "אין תחומי ירידה" + " ירידה: " + str(inc) if len(
                inc) else "אין תחומי עלייה" + " "), result2,
        result3,
        result4, 0)
    return q


def make_extreme_question(b, c, p):
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
    return q


def make_domain_question(b, c, p):
    preamble = "מצא מה תחום ההגדרה של הפונקציה"
    ans1 = "הפונקציה מוגדרת לכל x"
    x1 = random.randint(-100, 0)
    x2 = -x1
    ans2 = [(x1, x2)]
    if c in [2, 5, 6, 7, 8]:
        ans1 = find_real_domain(p, c)
        if len(ans1) == 0:
            ans1 = "הפונקציה לא מוגדרת עבור אף x".format('x')
        flag = True

        p2 = p
        while flag or ans1 == ans2:
            flag = False
            p2 = [x - 1 for x in p2]
            ans2 = find_real_domain(p2, c)

        if len(ans2) == 0 and ans1 == "הפונקציה לא מוגדרת עבור אף x":
            x1 = round(random.randint(-10000, 0) / 1000, 2)
            x2 = -x1
            ans2 = [(x1, x2), (x2, x2 + 2)]

        to_put_define_for_all = random.randint(1, 4)
        if to_put_define_for_all == 1:
            ans2 = 'הפונקציה מוגדרת לכל x'

        if len(ans2) == 0:
            ans2 = "הפונקציה לא מוגדרת עבור אף x"
    x1 = round(random.randint(-10000, 0) / 1000, 2)
    x2 = -x1
    ans3 = [(float('-inf'), x1), (x1, x2), (x2, float('inf'))]
    x1 = round(random.randint(-10000, 0) / 1000, 2)
    x2 = -x1
    ans4 = [(float('-inf'), x1), (x1, x2), (x2, float('inf'))]
    q = (
        preamble, funcString(p, c, b), ans1, ans2,
        ans3,
        ans4, 0)
    return q


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
    return inc, dec


def get_max_unit(unit, user):
    maxAttempt = 0
    for activeU in ActiveUnit.select(unit=unit, student=user):
        if activeU.attempt > maxAttempt:
            maxAttempt = activeU.attempt
    return maxAttempt


def addQuestions_buisness(className, unitName, username):
    try:
        with db_session:
            unit = Unit[unitName, Cls[className]]
            c = 1
            print("AQB")
            tu = unit
            while tu.next:
                c += 1
                tu = Unit[tu.next, Cls[className]]
            user = User[username]

            print("step1")
            maxAttempt = get_max_unit(unit, user)
            if (maxAttempt == 0):
                ActiveUnit(inProgress=True, unit=unit, student=user, attempt=maxAttempt + 1, currentQuestion=0,
                           consecQues=0, quesAmount=0, totalCorrect=0, grade=0)
                maxAttempt += 1
            active = ActiveUnit[unit, user, (maxAttempt)]
            print("step2")
            if not active.inProgress:
                active = ActiveUnit(inProgress=True, unit=unit, student=user, attempt=maxAttempt + 1, currentQuestion=0,
                                    consecQues=0, quesAmount=0, totalCorrect=0, grade=0)
                maxAttempt += 1
            print("step3")

            if (active.currentQuestion < active.quesAmount):
                return jsonify(unit.maxTime,str(c))
            id = active.quesAmount + 1
            active.quesAmount += 10
            for single_question in get_questions(unit):
                Question(id=id, question_preamble=single_question[0], question=single_question[1],
                         correct_ans=single_question[6], answer1=str(single_question[2]),
                         answer2=str(single_question[3]), answer3=str(single_question[4]),
                         answer4=str(single_question[5]),
                         active_unit=ActiveUnit[unit, user, maxAttempt])
                id += 1
            print("step4")

            commit()
            print(jsonify(unit.maxTime, str(c)))
            return jsonify(unit.maxTime, str(c))
    except Exception as e:
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
    return startUnit_buisness(className, unitName, username)


def startUnit_buisness(className, unitName, username):
    return addQuestions_buisness(className, unitName, username)


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
        return individualStats_buisness(className, unitName, teacherUsername, studentUsername)
    except Exception as e:
        print(e)
        return str(e), 400


def individualStats_buisness(className, unitName, teacherUsername, studentUsername):
    try:
        with db_session:
            ret = dict()
            user = User[studentUsername]
            unit = Unit[unitName, Cls[className]]
            # active = ActiveUnit[unit, user, 1]
            ans = list()
            totalCorrect, totalIncorrect = getLessonCorrectIncorrect(user, unitName, className)
            ans.append(totalCorrect)
            ans.append(totalIncorrect)
            ret["correctIncorrect"] = ans

            entity_count = ActiveUnit.select(student=user).count()
            last_five_entities = ActiveUnit.select(student=user).order_by(lambda e: e.lastTimeAnswered)[
                                 max(0, entity_count - 2):]
            last5grades = list()

            for entity in last_five_entities:
                last5grades.append(entity.grade)

            last5grades.reverse()
            if (len(last_five_entities) < 5):
                for i in range(5 - len(last_five_entities)):
                    last5grades.append(0)

            ret["L5"] = last5grades

            return jsonify(ret)
    except Exception as e:
        print(e)
        return str(e), 400


def getActiveUnits_buisness(className, unitName, username):  # this is for dab

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


def getAllActiveUnits2(className, unitName):
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


# needs to be deleted
def getAllActiveUnits_buisness(className, unitName):
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


def getAllActiveUnits(className, unitName, student=None):
    try:
        with db_session:
            unames = []
            names = []
            units = []
            actives = []
            students = []
            u = Unit[unitName, className]
            stop = False
            while not stop:
                unames.append(u.name)
                units.append(u)
                if student:
                    instances = ActiveUnit.select(unit=u, student=student)
                else:
                    instances = ActiveUnit.select(unit=u)
                for i in instances:
                    if i.student.name not in names:
                        names.append(i.student.name)
                        single_obj = dict()
                        single_obj["name"] = i.student.name
                        single_obj["correct"] = i.totalCorrect
                        single_obj["bad"] = (i.currentQuestion - i.totalCorrect)
                        students.append(single_obj)
                    else:
                        item = itemByName(students, i.student.name)
                        item["correct"] += i.totalCorrect
                        item["bad"] += (i.currentQuestion - i.totalCorrect)
                if u.next:
                    u = Unit[u.next, className]
                else:
                    stop = True
            return students
    except Exception as e:
        print(e)
        return str(e), 400


def getAllActiveUnits(className, unitName, student=None):
    try:
        with db_session:
            unames = []
            names = []
            units = []
            actives = []
            students = []
            u = Unit[unitName, className]
            stop = False
            while not stop:
                unames.append(u.name)
                units.append(u)
                if student:
                    instances = ActiveUnit.select(unit=u, student=student)
                else:
                    instances = ActiveUnit.select(unit=u)
                for i in instances:
                    if i.student.name not in names:
                        names.append(i.student.name)
                        single_obj = dict()
                        single_obj["name"] = i.student.name
                        single_obj["correct"] = i.totalCorrect
                        single_obj["bad"] = (i.currentQuestion - i.totalCorrect)
                        students.append(single_obj)
                    else:
                        item = itemByName(students, i.student.name)
                        item["correct"] += i.totalCorrect
                        item["bad"] += (i.currentQuestion - i.totalCorrect)
                if u.next:
                    u = Unit[u.next, className]
                else:
                    stop = True
            return students
    except Exception as e:
        print(e)
        return str(e), 400


@app.route('/getStats')
def getStats():
    className = request.args.get('className')
    unitName = request.args.get('unitName')
    username = request.args.get('username')
    if not isLogin(username):
        return "user " + username + "not logged in.", 400

    return jsonify(getAllActiveUnits(className, unitName)), 200


@app.route('/getStudentStats')
def getStudentStats():
    className = request.args.get('className')
    unitName = request.args.get('unitName')
    student = request.args.get('student')
    username = request.args.get('username')
    if not isLogin(username):
        return "user " + username + "not logged in.", 400
    t = getAllActiveUnits(className, unitName, student)
    return jsonify(t[0]), 200


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
            currentUnit, totalUnits = getLessonIndex(user, unit_name, class_name)
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
            single_question["currentUnit"] = currentUnit
            single_question["totalUnits"] = totalUnits

            ret.append(single_question)
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
            current_time = datetime.now()
            current_time_millis = int(current_time.timestamp() * 1000)
            current_time_millis_str = str(current_time_millis)
            question.solve_time = current_time_millis_str

            if (not activeUnit.currentQuestion < activeUnit.quesAmount):
                addQuestions_buisness(class_name, unit_name, user)

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
    try:
        return quitActiveUnit_buisness(user, unit_name, class_name)
    except Exception as e:
        print(e)
        return str(e), 400


def quitActiveUnit_buisness(user, unit_name, class_name):
    try:
        with db_session:
            unit = Unit[unit_name, Cls[class_name]]
            attempt = get_max_unit(unit, user)
            activeUnit = ActiveUnit[unit, user, attempt]
            activeUnit.inProgress = False
            return 'done'
    except Exception as e:
        print(e)
        return str(e), 400


def makePoly(p):
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

        if f1(x) is None or f2(x) is None:
            if x < a:
                x = a + maxerr
            elif x > b:
                x = b - maxerr

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
            f_x1 = f1(x1) - f2(x1)
        elif f_x1 * f_x2 < 0 and f_x1 != f_x2:
            x = regulaFalsi(f1, f2, x1, x2, a, b, maxerr)
            if x is not None:
                yield x
            x1 = x2 + delta
            x2 = x2 + delta
            if f1(x1) is None or f2(x1) is None:
                return
            f_x1 = f1(x1) - f2(x1)
        else:
            x1 = x2
            x2 += delta
        if x2 < b and x2 > a:
            f_x2 = f1(x2) - f2(x2)
        elif x2 > b:
            f_x2 = f1(b - 0.01) - f2(b - 0.01)
        else:
            f_x2 = f1(a + 0.01) - f2(a + 0.01)


def intersections(f1: callable, f2: callable, a: float, b: float, maxerr=0.00001) -> Iterable:
    while (f1(a) is None or f2(a) is None) and a < b:
        a += 100 * maxerr
    while (f1(b) is None or f2(b) is None) and a < b:
        b -= 100 * maxerr
    if a >= b:
        return []
    iterator = helper(f1, f2, a, b, maxerr)
    arr = np.array([])
    for x in iterator:
        if len(arr) == 0 or abs(x - arr[len(arr) - 1]) > maxerr:
            arr = np.append(arr, [x])
    return arr


def makeDomain(params, c=0):
    if c in [0, 1, 3, 4]:
        r = [(float('-inf'), float('inf'))]
        return r
    elif c == 2:
        r = []
        coefficient = params[:-1]
        f = makeFunc(coefficient)
        inters = [x for x in intersections(f, lambda x: 0, -100, 100)]
        inters.append(float('-inf'))
        inters.append(float('inf'))
        inters = sorted([round(x, 3) for x in inters])
        for i in range(len(inters) - 1):
            it = inters[i]
            it2 = inters[i + 1]
            if it == float('inf'):
                it = 100
            if it == float('-inf'):
                it = -100

            if it2 == float('inf'):
                it2 = 100
            if it2 == float('-inf'):
                it2 = -100

            a = (it + it2) / 2
            if f(a) > 0:
                r.append((inters[i], inters[i + 1]))
        return r
    elif c in [5, 6]:
        r = []
        coefficient = params[:-1] + [0]
        f = makeFunc(coefficient, 3 if c == 6 else 4)
        inters = sorted(intersections(lambda x: 0, f, -3, 3))
        if len(inters) == 0:
            return [(float('-inf'), float('inf'))]
        for i in range(len(inters) - 1):
            r.append((inters[i], inters[i + 1]))
        return r
    elif c == 7:
        p2 = params[int(len(params) / 2):]
        poly = makePoly(p2)
        zeroes = sorted([x[0] for x in makeIntersections(poly)])
        print(params, p2, zeroes)
        if len(zeroes) == 0:
            return [(float('-inf'), float('inf'))]
        r = []
        r.append((float('-inf'), zeroes[0]))
        for i in range(len(zeroes) - 1):
            r.append((zeroes[i], zeroes[i + 1]))
        r.append(((zeroes[-1]), float('inf')))
        return r
    elif c == 8:
        poly = makePoly(params[:-1])
        zeroes = [x[0] for x in makeIntersections(poly)]
        if len(zeroes) == 0:
            if poly(0) > 0:
                return [(float('-inf'), float('inf'))]
            else:
                return []
        r = []

        zeroes.append(float('-inf'))
        zeroes.append(float('inf'))
        zeroes = sorted(zeroes)
        for i in range(len(zeroes) - 1):
            it = zeroes[i]
            it2 = zeroes[i + 1]
            if it == float('inf'):
                it = 100
            if it == float('-inf'):
                it = -100

            if it2 == float('inf'):
                it2 = 100
            if it2 == float('-inf'):
                it2 = -100

            z = (it + it2) / 2
            if poly(z) >= 0:
                r.append((zeroes[i], zeroes[i + 1]))
        return r


def makeIntersections(poly, c=0, r=[(-100, 100)]):
    if c == 0:
        r = [(-100, 100)]
    elif c in [1, 3, 4]:
        r = [(-2, 2)]
    else:
        r = [(d[0] if d[0] not in [float('-inf')] else -100, d[1] if d[1] not in [float('inf')] else 100) for d in r]
    xs = []
    for i in r:
        inters = (intersections(poly, lambda x: 0, i[0], i[1]))
        for x in inters:
            xs.append(x)

    points = [(float(round(i, 2)), 0.0) if abs(round(i, 2)) > 0.01 else (0.0, 0.0) for i in xs]
    return points


def makeDer(params):
    return [(len(params) - 1 - i) * params[i] for i in range(len(params) - 1)]


def isParenthesisNeeded(s):
    if (s.count("+") + s.count("-")) > 1:
        return True
    if (not s.startswith("-")) and (s.count("+") + s.count("-")) >= 1:
        return True
    return False


def deriveString(p, c=0, b=math.e):
    if c == 0:
        return "y'=" + polySrting(makeDer(p))
    elif c == 1:
        innerDerive = polySrting(makeDer(p[:-1]))
        exponent = polySrting(p[:-1])
        if isParenthesisNeeded(innerDerive):
            innerDerive = "(" + innerDerive + ")"

        if b != math.e:
            if innerDerive.startswith("("):
                innerDerive = "ln(" + str(b) + ")" + innerDerive + " * "
            else:
                innerDerive = innerDerive + "ln(" + str(b) + ") * "
            return "y'=" + innerDerive + str(b) + "^{" + exponent + "}"
        return "y'=" + innerDerive + ("e" if b == math.e else str(b)) + "^{" + exponent + "}"

    elif c == 2:
        numerator = polySrting(makeDer(p[:-1]))
        if numerator == "0":
            return "y'=0"
        denominator = polySrting(p[:-1])
        equation = f"y'=\\frac{{{numerator}}}{{{denominator}}}"
        return equation

    elif c == 3:
        innerDerive = polySrting(makeDer(p[:-1]))
        isCompoundDerive = isParenthesisNeeded(innerDerive)
        if isCompoundDerive:
            return "y'=cos(" + polySrting(p[:-1]) + ")" + "(" + innerDerive + ")"

        return "y'=" + innerDerive + "cos(" + polySrting(p[:-1]) + ")"
    elif c == 4:
        innerDerive = polySrting(makeDer(p[:-1]))
        isCompoundDerive = isParenthesisNeeded(innerDerive)
        if isCompoundDerive:
            return "y'=-sin(" + polySrting(p[:-1]) + ")" + "(" + innerDerive + ")"
        if innerDerive.startswith("-"):
            return "y'=" + innerDerive + "sin(" + polySrting(p[:-1]) + ")"
        return "y'=-" + innerDerive + "sin(" + polySrting(p[:-1]) + ")"
    elif c == 5:
        innerDerive = polySrting(makeDer(p[:-1]))
        return f"y'=\\frac{{{innerDerive}}}{{{'cos^2(' + polySrting(p[:-1]) + ')'}}}"
    elif c == 6:
        innerDerive = polySrting(makeDer(p[:-1]))
        if innerDerive == "0":
            return "y=0"
        return f"y'=-\\frac{{{innerDerive}}}{{{'sin^2(' + polySrting(p[:-1]) + ')'}}}"
        # return "y=(-1/sin^2(" + polySrting(p[:-1]) + ")"
    elif c == 7:
        l = int(len(p) / 2)
        return "y'=(((" + polySrting(makeDer(p[:l])) + ") * (" + polySrting(p[l:]) + ")) - ((" + polySrting(
            makeDer(p[l:])) + ") * (" + polySrting(p[:l]) + "))) / (" + polySrting(p[l:]) + ")^2"
    elif c == 8:
        innerDerive = polySrting(makeDer(p[:-1]))
        if innerDerive == "0":
            return "y'=0"

        # return f"y=\\sqrt[{b}]{{{polySrting(p[:-1])}}}"
        denominator = funcString(p, 8, b)
        return f"y'=\\frac{{{innerDerive}}}{{{'2'+denominator[2:]}}}"



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
        p1 = params[:int(len(params) / 2)]
        p2 = params[int(len(params) / 2):]
        poly1 = makePoly(p1)
        poly2 = makePoly(p2)
        return lambda x: (derive(p1)(x) * poly2(x) - poly1(x) * derive(p2)(x)) / (poly2(x) ** 2) if poly2(
            x) != 0 else None
    if c == 8:
        poly = makePoly(params[:-1])
        der = derive(params[:-1])

        def rootElement(x):
            if poly(x) > 0:
                return der(x) * (1 / b) * math.pow(poly(x), 1 / b - 1)
            print("ROOTNONE", funcString(p, 8, b), x)
            return None

        return rootElement


def makeExtremes(params, c=0, b=math.e):
    # Calculate the derivative of the polynomial
    if not any(params):
        return "אין נקודות קיצון"

    realDerive = derive(params, c, b)
    dom = makeDomain(params, c)
    extreme_points = makeIntersections(realDerive, c, dom)
    f = makeFunc(params, c, b)

    extremes = [(e[0], round(f(e[0]), 3)) for e in extreme_points if f(e[0])]
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
                    pass
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
    if dom == []:
        return [], []
    ext = set()
    f = makeFunc(p, c, b)
    for i in extremes:
        ext.add(i)
    for i in dom:
        if i[0] not in [float('-inf'), float('inf')]:
            if f(i[0] + 0.001):
                ext.add((i[0], float('-inf') if f(i[0] + 0.001) < 0 else float('inf')))
            else:
                ext.add((i[0], float('-inf') if f(i[0] - 0.001) < 0 else float('inf')))
        if i[1] not in [float('-inf'), float('inf')]:
            if f(i[1] + 0.001):
                ext.add((i[1], float('-inf') if f(i[1] + 0.001) < 0 else float('inf')))
            else:
                ext.add((i[1], float('-inf') if f(i[1] - 0.001) < 0 else float('inf')))
    sorted_extremes = sorted(list(ext))
    f = derive(p, c, b)
    if len(sorted_extremes) == 0:
        if dom == [(float('-inf'), float('inf'))]:
            dom = [(-100, 100)]
        sample = random.randint(dom[0][0] * 1000, dom[0][1] * 1000) / 1000
        if f(sample) > 0:
            return [(float('-inf'), float('inf'))], []
        else:
            return [], [(float('-inf'), float('inf'))]
    inc_ranges = []
    dec_ranges = []
    if any([(sorted_extremes[0][0] - 1) < d[1] and (sorted_extremes[0][0] - 1) > d[0] in d for d in dom]):
        s = f(sorted_extremes[0][0] - 1)
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
    # Add the final ranges
    if any([(sorted_extremes[-1][0] + 1) < d[1] and (sorted_extremes[-1][0] + 1) > d[0] in d for d in dom]):
        s = f(sorted_extremes[-1][0] + 1)
        if s < 0:
            dec_ranges.append((sorted_extremes[-1][0], float('inf')))
        else:
            inc_ranges.append((sorted_extremes[-1][0], float('inf')))

    print(inc_ranges, dec_ranges)

    return inc_ranges, dec_ranges


def makePosNeg(p, c=0, b=math.e):
    if not any(p[:-1]):
        return [], []
    dom = makeDomain(p, c)
    if dom == []:
        return [], []
    f = makeFunc(p, c, b)
    inters = makeIntersections(f, c, dom)
    points = set()
    for i in inters:
        points.add(i)
    for i in dom:
        if i[0] not in [float('-inf'), float('inf')]:
            if f(i[0] + 0.001):
                points.add((i[0], float('-inf') if f(i[0] + 0.001) < 0 else float('inf')))
            else:
                points.add((i[0], float('-inf') if f(i[0] - 0.001) < 0 else float('inf')))
        if i[1] not in [float('-inf'), float('inf')]:
            if f(i[1] + 0.001):
                points.add((i[1], float('-inf') if f(i[1] + 0.001) < 0 else float('inf')))
            else:
                points.add((i[1], float('-inf') if f(i[1] - 0.001) < 0 else float('inf')))
    # Sort the extreme points by their x-values
    sorted_points = sorted(list(points))
    if len(sorted_points) == 0:
        if dom == [(float('-inf'), float('inf'))]:
            dom = [(-100, 100)]
        sample = random.randint(int(dom[0][0] * 1000), int(dom[0][1] * 1000)) / 1000
        if f(sample) > 0:
            return [(float('-inf'), float('inf'))], []
        else:
            return [], [(float('-inf'), float('inf'))]

    pos = []
    neg = []
    if any([(sorted_points[0][0] - 1) < d[1] and (sorted_points[0][0] - 1) > d[0] in d for d in dom]):
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
    if any([(sorted_points[-1][0] + 1) < d[1] and (sorted_points[-1][0] + 1) > d[0] in d for d in dom]):
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

    sorted_extremes = sorted(list(ext))

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


def makeAsym(p, c=0, b=math.e):
    if c in [0, 3, 4]:
        return [], []
    else:
        s = set()
        dom = makeDomain(p, c)
        f = makeFunc(p, c, b)
        for i in dom:
            if i[0] not in [float('-inf'), float('inf')]:
                if f(i[0] + 0.0005):
                    s.add((i[0], round(f(i[0] + 0.0005), 1)) if abs(f(i[0] + 0.0005)) < 1000 else (
                        (i[0], float('-inf') if f(i[0] + 0.0005) < -1000 else float('inf'))))
                else:
                    s.add((i[0], round(f(i[0] - 0.0005), 1)) if abs(f(i[0] - 0.0005)) < 1000 else (
                        (i[0], float('-inf') if f(i[0] - 0.0005) < 1000 else float('inf'))))
            if i[1] not in [float('-inf'), float('inf')]:
                if f(i[1] + 0.0005):
                    s.add((i[1], round(f(i[1] + 0.0005), 1)) if abs(f(i[1] + 0.0005)) < 1000 else (
                        (i[1], float('-inf') if f(i[1] + 0.0005) < -1000 else float('inf'))))
                else:
                    s.add((i[1], round(f(i[1] - 0.0005), 1)) if abs(f(i[1] - 0.0005)) < 1000 else (
                        (i[1], float('-inf') if f(i[1] - 0.0005) < 1000 else float('inf'))))
        l = set()
        if f(10000):
            l.add((float('inf'), round(f(10000), 2)) if abs(f(10000)) < 1000 else (
                float('inf'), (float('inf')) if f(10000) > 0 else (float('inf'), float('-inf'))))
        if f(-10000):
            l.add((float('-inf'), round(f(-10000), 2)) if abs(f(-10000)) < 1000 else (
                float('-inf'), (float('inf')) if f(-10000) > 0 else (float('-inf'), float('-inf'))))
        print(s, l)
        return list(s), list(l)


def funcString(p, c=0, b=math.e):
    if c == 0:
        return "y=" + polySrting(p)
    elif c == 1:
        return "y=" + ("e" if b == math.e else str(b)) + "^{" + polySrting(p[:-1]) + "}" + (
            ("+" if p[-1] > 0 else "") + str(p[-1]) if p[-1] else "")
    elif c == 2:
        return "y=" + ("ln" if b == math.e else "log_" + str(b)) + "(" + polySrting(p[:-1]) + ")" + (
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
        l = int(len(p) / 2)
        return "y=(" + polySrting(p[:l]) + ") / (" + polySrting(p[l:]) + ")"
    elif c == 8:
        if b == 2:
            return "y=\\sqrt{" + polySrting(p[:-1]) + "}"
        return f"y=\\sqrt[{b}]{{{polySrting(p[:-1])}}}"
        # return "y=\\sqrt{" + polySrting(p[:-1]) + "}"
        # return "y=(" + polySrting(p[:-1]) + ")^(" + str(1 / b) + ")" + (
        #     ("+" if p[-1] > 0 else "") + str(p[-1]) if p[-1] else "")


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
    return lambda x: None if makePoly(p2)(x) == 0 else makePoly(p1)(x) / makePoly(p2)(x)


def makeRoot(p, b):
    if len(p) < 1:
        return lambda x: 0
    else:
        return lambda x: None if makePoly(p[:-1])(x) < 0 else math.pow(makePoly(p[:-1])(x), 1 / b) + p[-1]


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


@app.route('/getAllLessonQuestions')
def getAllLessonQuestions():
    teacher = request.args.get('teacher')
    unitName = request.args.get('unitName')
    className = request.args.get('className')

    return getAllLessonQuestionsB(className, unitName)


def getAllLessonQuestionsB(className, unitName):
    try:
        with db_session:
            names = []
            units = []
            actives = []
            questions = {}
            u = Unit[unitName, className]
            stop = False
            while not stop:
                names.append(u.name)
                units.append(u)
                instances = ActiveUnit.select(unit=u)
                for i in instances:
                    actives.append(i)
                    for q in Question.select(active_unit=i):
                        if q.solve_time:
                            question_data = {
                                "id": q.id,
                                "question_preamble": q.question_preamble,
                                "question": q.question,
                                "answer1": q.answer1,
                                "answer2": q.answer2,
                                "answer3": q.answer3,
                                "answer4": q.answer4,
                                "correct_ans": q.correct_ans,
                                "active_unit": q.active_unit.unit.name,
                                "active_unit_attempt": q.active_unit.attempt,
                                "solved_correctly": q.solved_correctly,
                                "solve_time": q.solve_time
                            }
                            if i.student.name not in questions.keys():
                                questions[i.student.name] = []
                            questions[i.student.name].append(question_data)
                if u.next:
                    u = Unit[u.next, className]
                else:
                    stop = True

            for s, qs in questions.items():
                questions[s] = sorted(qs, key=lambda x: x['solve_time'], reverse=False)
            return questions, 200
    except Exception as e:
        print(e)
        return str(e), 400


@app.route('/getStudentLessonQuestions')
def getStudentLessonQuestions():
    teacher = request.args.get('teacher')
    student = request.args.get('student')
    unitName = request.args.get('unitName')
    className = request.args.get('className')

    return getStudentLessonQuestionsB(className, student, unitName)


def getStudentLessonQuestionsB(className, student, unitName):
    try:
        with db_session:
            names = []
            units = []
            actives = []
            questions = []
            u = Unit[unitName, className]
            stop = False
            while not stop:
                names.append(u.name)
                units.append(u)
                instances = ActiveUnit.select(unit=u)
                for i in instances:
                    if i.student.name == student:
                        actives.append(i)
                        for q in Question.select(active_unit=i):
                            if q.solve_time:
                                question_data = {
                                    "id": q.id,
                                    "question_preamble": q.question_preamble,
                                    "question": q.question,
                                    "answer1": q.answer1,
                                    "answer2": q.answer2,
                                    "answer3": q.answer3,
                                    "answer4": q.answer4,
                                    "correct_ans": q.correct_ans,
                                    "active_unit": q.active_unit.name,
                                    "solved_correctly": q.solved_correctly,
                                    "solve_time": q.solve_time
                                }
                                questions.append(question_data)
                if u.next:
                    u = Unit[u.next, className]
                else:
                    stop = True
            return questions, 200
    except Exception as e:
        print(e)
        return str(e), 400


# [random.randint(params[2*i], params[2*i+1]) for i in range(int(len(params)/2))]


p = [0, 0, -4, 0]
c = 0

b = 2
a = makeFunc(p, c=c, b=b)
r1 = -6
r2 = 2
print()
print("f: " + str(a))
print("f(5): " + str(a(5)))
dom = makeDomain(p, c)
print("Domain: " + str(dom))
print("Intersections: " + str(makeIntersections(a, c=c, r=dom)))
print("Extremes: " + str(makeExtremes(p, c=c, b=b)))
print("IncDec: " + str(makeIncDec(p, c=c)))
print("funcString: " + str(funcString(p, c=c, b=b)))
print("deriveString: " + str(deriveString(p, c=c, b=b)))
print("PosNeg: " + str(makePosNeg(p, c=c, b=b)))
print("makeAsym: " + str(makeAsym(p, c, b)))
print("integral from", r1, "to", r2, ": ", definite_integral_question(b, c, a, (r1, r2), p)[2])


#
# print(register_buisness("aleks","123",1))
# print(register_buisness("aleks1","123",2))
# print(openClass_buisness("aleks","c1"))
# registerClass_buisness("aleks1","c1")
# approveStudentToClass_buisness("aleks","aleks1","c1","True")


# sym = getSymmetry(p, c)
# print("symmetry: " + ("f(x)=" + str(sym[0]) + "*f(-x+" + str(2 * sym[1]) + ")") if sym else sym)


def getLessonIndex(user, unit_name, class_name):
    try:
        with db_session:
            unitsAbove = 0
            unitsBelow = 0
            try:
                unit_name_n = unit_name
                unit_name_n += "n"
                while (True):
                    unit = Unit[unit_name_n, Cls[class_name]]
                    activeUnit = ActiveUnit[unit, user, 1]
                    unitsAbove += 1
                    unit_name_n += "n"
            except Exception as e:
                a = 8
                # print("does not exists " + str(e))

            try:
                unit_name_n = unit_name
                unit_name_n = unit_name_n[:-1]
                while (True):
                    unit = Unit[unit_name_n, Cls[class_name]]
                    activeUnit = ActiveUnit[unit, user, 1]
                    unitsBelow += 1
                    unit_name_n = unit_name_n[:-1]

            except Exception as e:
                a = 8
                # print("does not exists " + str(e))

            return (1 + unitsBelow, 1 + unitsAbove + unitsBelow)

    except Exception as e:
        print(e)
        return str(e)


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
                a = 8
                # print("does not exists " + str(e))

            grade = int(((total_correct / total_solved) * 100))
            return grade


    except Exception as e:
        print(e)
        return str(e)


def getLessonCorrectIncorrect(user, unit_name, class_name):
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
                a = 8
            # print("does not exists " + str(e))

            return (total_correct, total_solved - total_correct)


    except Exception as e:
        print(e)
        return str(e)


@app.route('/getLessonCorrect')
def getLessonCorrectIncorrectQuestions():
    user = request.args.get('usernameS')
    unit_name = request.args.get('unitName')
    class_name = request.args.get('className')
    correct = request.args.get('correct')
    if (correct == "Correct"):
        correctBool = True
    else:
        correctBool = False

    try:
        with db_session:
            unit_name_n = unit_name
            total_correct = 0
            total_solved = 0
            ret = []
            try:
                id = 1
                while (True):
                    unit = Unit[unit_name_n, Cls[class_name]]
                    activeUnit = ActiveUnit[unit, user, 1]
                    for question in Question.select(active_unit=activeUnit, solved_correctly=correctBool):
                        singleQuestion = dict()
                        singleQuestion["questionPreamble"] = question.question_preamble
                        singleQuestion["question"] = question.question
                        singleQuestion["id"] = id
                        id += 1
                        ret.append(singleQuestion)

                    unit_name_n += "n"
            except Exception as e:
                a = 8
                # print("does not exists " + str(e))
            return jsonify(ret), 200



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
        return "startUnit_buisness", Uname

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
