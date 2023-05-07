import logging
import random
from fractions import Fraction

from flask import Flask, request, jsonify
from flask_pony import Pony
from flask_cors import CORS
from pony.orm import *
from scipy.optimize import minimize_scalar
import numpy as np
from pony_database_facade import DatabaseFacade

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)
CORS(app)
pony = Pony(app)

DB = pony.db
DB.bind(provider='sqlite', filename='dbtest', create_db=True)

DATATYPE_SIZE = 3
QUESTIONTYPE_SIZE = 4
QUESTIONS_TO_GENERATE = 10
MAX_RANGE = 10
MIN_RANGE = -10


class User(DB.Entity):
    name = PrimaryKey(str)
    password = Required(str)
    type = Required(int)
    teaching = Set('Cls', reverse='teacher',cascade_delete=False)
    inClass = Set('Cls_User',cascade_delete=False)
    activeUnits = Set("ActiveUnit", reverse='student')


class Cls(DB.Entity):
    name = PrimaryKey(str)
    teacher = Required(User, reverse='teaching')
    students = Set('Cls_User')
    hasUnits = Set('Unit', reverse='cls',cascade_delete=False)


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
    active_unit = Required('ActiveUnit',reverse='questions')
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
    PrimaryKey(unit, student, attempt)


DB.generate_mapping(create_tables=True)

activeControllers = {}


@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'


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
        return str(e), 400

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

    ans = makeUser(username, password, typ)
    if ans is None:
        return username + " " + password + " " + typ
    return ans


def checkUserPass(username, password):
    try:
        with db_session:
            result = User[username]
            if result:
                return result.password == password
            return False
    except Exception:
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
    loadController(username)
    if isinstance(activeControllers[username], teacherCont):
        return '1 ' + username
    return '2 ' + username


@app.route('/changePassword')
def change_password():
    username = request.args.get('username')
    password = request.args.get('password')
    new_password = request.args.get('newPassword')
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
    activeControllers.pop(username)
    return username + " " + str(len(activeControllers))


@app.route('/openClass')
def openClass():
    teacherName = request.args.get('teacher')
    className = request.args.get('className')
    try:
        with db_session:
            t = User[teacherName]
            if t.type == 1:
                Cls(name=className, teacher=User[teacherName])
                return "successful", 200
            return "failed wrong type", 400
    except Exception as e:
        return str(e), 400


@app.route('/removeClass')
def removeClass():
    teacherName = request.args.get('teacher')
    className = request.args.get('className')
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
    try:
        with db_session:
            c = Cls[className]
            u = Unit[unitName,c]
            ins = u.instances #
            order = u.order
            nex = u.next
            temp = u.template
            Qnum = u.Qnum
            maxTime = u.maxTime
            subDate = u.subDate
            if newUnitName!=unitName:
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
    try:
        with db_session:
            c = Cls[className]
            u = Unit[unitName,c]
            ins = u.instances #
            order = u.order
            nex = u.next
            temp = u.template
            if newUnitName != unitName:
                Unit(cls=c, name=newUnitName, desc=newDesc, template=temp, Qnum=Qnum, maxTime=maxTime, subDate=subDate,
                     instances=ins, order=order, next=nex)
                Unit[unitName, c].delete()
            else:
                u.set(desc=newDesc, Qnum=Qnum, maxTime=maxTime, subDate=subDate)
            return {"message": "successful"}
    except Exception as e:
        return str(e), 400


@app.route('/removeUnit')
def removeUnit():
    unitName = request.args.get('unitName')
    className = request.args.get('className')
    try:
        with db_session:
            u = Unit[unitName, Cls[className]]
            u.delete()
            return "successful", 200
    except Exception as e:
        return str(e), 400


@app.route('/getAllClassesNotIn')
def getAllClassesNotIn():
    ret = []
    student = request.args.get('username')
    id = 0

    try:
        with db_session:
            already_in = list()
            for aUnit in Cls_User.select(user=student):
                already_in.append( aUnit.cls.name)
            for singleClass in Cls.select(lambda p: True):
                if singleClass.name in already_in:
                    continue
                single_obj = dict()
                id += 1
                single_obj["id"] = id
                single_obj["className"] = singleClass.name
                single_obj["teacher"]=  singleClass.teacher.name
                ret.append(single_obj)

        return jsonify(ret)
    except Exception as e:
        return str(e), 400

@app.route('/getAllClassesWaiting')
def getAllClassesWaiting():
    ret = []
    student = request.args.get('username')
    id = 0

    try:
        with db_session:
            for aUnit in Cls_User.select(user=student,approved=False):
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
    try:
        with db_session:
            c = Cls[className]
            u = User[studentName]
            c_u = Cls_User(cls=c, user=u, approved=False)


            commit()
            return "successful", 200
    except Exception as e:
        return str(e), 400

@app.route('/removeRegistrationClass')
def removeRegistrationClass():
    studentName = request.args.get('student')
    className = request.args.get('className')
    try:
        with db_session:
            c = Cls[className]
            u = User[studentName]
            Cls_User.select(cls=c,user=u).delete(bulk=True)
            commit()
            return "successful", 200
    except Exception as e:
        return str(e), 400


@app.route('/getUnapprovedStudents')
def getUnapprovedStudents():
    teacher = request.args.get('teacher')
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
    studentName = request.args.get('student')
    className = request.args.get('className')
    approve = request.args.get('approve')
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
        return str(e), 400


@app.route('/removeFromClass')
def removeFromClass():
    studentName = request.args.get('student')
    className = request.args.get('className')
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
            print("DB")
            ord = 1
            if first != 'true':
                p = Unit[prev, Cls[className]]
                print(p)
                p.next = unitName
                ord = p.order+1
            print(className, unitName,template,Qnum,maxTime,subDate,ord)
            print(Cls[className])
            u = Unit(cls=Cls[className], name=unitName,desc=desc, template=template, Qnum=Qnum, maxTime=maxTime, subDate=subDate,
                     order=ord)
            print(u)
            commit()
            return "success"
    except Exception as e:
        print(e)
        return str(e), 400, 400


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

    result = teacherOpenUnit(unitName, teacherName, className, template, Qnum, maxTime, subDate, first, prev,desc)
    print(result)
    return result


@app.route('/getUnit')
def getUnit():
    unitName = request.args.get('unitName')
    className = request.args.get('className')
    try:
        with db_session:
            retUnit = Unit[unitName, Cls[className]]
            return retUnit.name
    except Exception as e:
        return str(e), 400


@app.route('/deleteUnit')
def deleteUnit():
    unitName = request.args.get('unitName')
    className = request.args.get('className')
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
                ret.append(single_obj)
            return ret
    except Exception as e:
        print(e)
        return str(e), 400


@app.route('/getClassesStudent')
def getClassesStudent():
    student = request.args.get('student')
    try:
        with db_session:
            ret = []
            id = 0
            for aUnit in Cls_User.select(user=student,approved=True):
                single_obj = dict()
                id += 1
                single_obj["id"] = id
                single_obj["primary"] = aUnit.cls.name
                single_obj["secondary"] = "lalala"
                ret.append(single_obj)

            return jsonify(ret)
    except Exception as e:
        return str(e), 400


@app.route('/getClassesTeacher')
def getClassesTeacher():
    teacher = request.args.get('teacher')
    try:
        with db_session:
            ret = []
            id = 0
            for aUnit in Cls.select(teacher=teacher):
                single_obj = dict()
                id += 1
                single_obj["id"] = id
                single_obj["primary"] = aUnit.name
                single_obj["secondary"] = "lalala"
                ret.append(single_obj)

            return jsonify(ret)
    except Exception as e:
        return str(e), 400


@app.route('/getUnitDetails')
def getUnitDetails():
    className = request.args.get('className')
    unitName = request.args.get('unitName')
    try:
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
    except Exception as e:
        print(e)
        return str(e), 400

def get_random_result(zero,up_down):
    if not up_down:
        x_a = random.randint(0,3)
        x_b = random.randint(0,3)
        a = random.randint(-10, 10) + x_a / 4
        b = random.randint(-10, 10) + x_b / 4
        if zero:
            return ((a,0),(0,b))
        else:
            return (a,b)
    else:
        x_a = random.randint(0,3)
        a = random.randint(-10, 10) + x_a / 4
        ans=dict()
        ans["up"] = "x > " + str(a)
        ans["down"] = "x < " + str(a)
        up_down = random.randint(0, 1)
        if (up_down):
            return ( ans["down"] + " ירידה:")
        else:
            return (ans["up"] + " עלייה:")


def func_to_string(a, b, c):
    if b == 0 and c == 0:
        return "f(x) = {}*x^2".format(a)
    elif b == 0:
        return "f(x) = {}*x^2+{}".format(a, c)
    elif c == 0:
        return "f(x) = {}*x^2+{}*x".format(a, b)
    else:
        return "f(x) = {}*x^2+{}*x+{}".format(a, b, c)

def getQuadratic(a_min,a_max,b_min,b_max,c_min,c_max):
    a = 0
    while a == 0:
        a = random.randint(int(a_min), int(a_max))
    b = random.randint(int(b_min), int(b_max))
    c = random.randint(int(c_min), int(c_max))
    return a,b,c

def inc_dec(function_types, params):

    if ("linear" in function_types):
        raise Exception("Cannot create a linear min,max question")
    if ("quadratic" in function_types):
        preamble = "מצא תחומי עלייה וירידה:"
        a,b,c = getQuadratic(params[0],params[1],params[2],params[3],params[4],params[5])

        ans = dict()
        result  = find_min_max(a,b,c)
        if a<0:
            ans["down"] = "x > " + str (result["maximum"]["x"])
            ans["up"] = "x < " + str (result["maximum"]["x"])
        else:
            ans["up"] = "x > " + str (result["minimum"]["x"])
            ans["down"] = "x < " + str (result["minimum"]["x"])

        question_string = func_to_string(a,b,c)

        result2 = get_random_result(False,True)
        result3 = get_random_result(False,True)
        result4 = get_random_result(False,True)

        up_down  = random.randint(0,1)
        if (up_down):
            return (preamble, question_string, (ans["down"] + " ירידה:" ), result2, result3, result4,1)
        else:
            return (preamble, question_string, (ans["up"] + " עלייה:" ), result2, result3, result4,1)



def min_max_points(function_types, params):
    minimum_range = MIN_RANGE
    maximum_range = MAX_RANGE
    if ("linear" in function_types):
        raise Exception("Cannot create a linear min,max question")
    if ("quadratic" in function_types):
        preamble = "מצא את נקודת הקיצון:"
        a, b, c = getQuadratic(params[0], params[1], params[2], params[3], params[4], params[5])
        result  = find_min_max(a,b,c)

        result2 = get_random_result(False,False)
        result3 = get_random_result(False,False)
        result4 = get_random_result(False,False)
        if a>0:
            result1 = result["minimum"]
        else:
            result1 = result["maximum"]

        question_string = func_to_string(a,b,c)

    return (preamble, question_string, (result1["x"],result1["y"]),result2,result3,result4,0)


def generate_cut_axis(function_types, params):
    preamble ="מצא את נקודות החיתוך עם הצירים:"

    minimum_range = MIN_RANGE
    maximum_range = MAX_RANGE

    # linear
    if ("linear" in function_types):
        m_minimum = int(params[0])
        m_maximum = int(params[1])
        b_minimum = int(params[2])
        b_maximum = int(params[3])
        m = random.randint(m_minimum, m_maximum)
        b = random.randint(b_minimum, b_maximum)
        """
        else:
            m = random.randint(minimum_range, maximum_range)
            while m == 0:
                m = random.randint(minimum_range, maximum_range)
            b = random.randint(minimum_range, maximum_range)
            """

        ans_x = round( -b/m,2)
        if (ans_x == round(ans_x)):
            ans_x=round(ans_x)
        ans_xf = (ans_x, 0)
        ans_y = (0, b)

        ans2 = get_random_result(True,False)
        ans3 = get_random_result(True,False)
        ans4 = get_random_result(True,False)

        if (b == 0):
            questions_string = "y=" + str(m) + "x"
        else:
            questions_string = ("y=" + str(m) + "x" + ('+' if b > 0 else "") + str(b))


    return (preamble, questions_string, (ans_xf, ans_y), ans2, ans3, ans4,0)

def find_min_max(a, b, c):
    # Define the function to find the minima and maxima of
    def f(x):
        return a*x**2 + b*x + c

    if a>0:
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
        if (ans_place ==2):
            new_single_question = (single_question[0],single_question[1],single_question[3],single_question[2],single_question[4],single_question[5],1,single_question[6] )
        elif (ans_place ==3):
            new_single_question = (single_question[0],single_question[1],single_question[3],single_question[2],single_question[4],single_question[5], 2,single_question[6])
        elif (ans_place ==4):
            new_single_question = (single_question[0], single_question[1], single_question[4], single_question[3], single_question[2],single_question[5],3,single_question[6])
        elif (ans_place == 5):
            new_single_question = (single_question[0], single_question[1], single_question[5], single_question[3], single_question[4],single_question[2],4,single_question[6])
        questions_scrambled.append(new_single_question)
    return questions_scrambled

# template - [0] = type of function
#           [1] = type of question
#           [2] = list of variable restrictions

# question format - [0] = preamble
#                - [1] = question string
#                - [2] = ans (list?)

def parse_template(template):
    parts = template.split('_')
    questions = parts[1].split(',')
    params = parts[2].split(',')
    return parts[0], questions, params



def get_questions(unit):
    questions = list()
    for i in range(QUESTIONS_TO_GENERATE):
        question_type,function_types, params = parse_template(unit.template)
        question =random.choice(question_type)
        if('intersection' in question):
            q = generate_cut_axis(function_types, params)
        elif ('minMaxPoints' in question):
            q = min_max_points(function_types, params)
        elif('incDec' in question):
            q =inc_dec(function_types, params)
        questions.append(q)
    return change_order(questions)


def get_max_unit(unit, user):
    maxAttempt = 0
    for activeU in ActiveUnit.select(unit=unit, student=user):
        if activeU.attempt > maxAttempt:
            maxAttempt = activeU.attempt
    return maxAttempt

def addQuestions(className,unitName,username):
    try:
        with db_session:
            unit = Unit[unitName, Cls[className]]
            user = User[username]

            maxAttempt = get_max_unit(unit, user)
            if (maxAttempt == 0):
                ActiveUnit(inProgress=True, unit=unit, student=user, attempt=maxAttempt + 1,currentQuestion=0, consecQues=0, quesAmount=0)
                maxAttempt += 1

            active = ActiveUnit[unit, user, (maxAttempt)]

            if(active.currentQuestion < active.quesAmount ):
                return "enough questions"
            id = active.quesAmount + 1
            active.quesAmount += 10
            for single_question in get_questions(unit):
                if (single_question[7]==0):
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
            return "added unit"
    except Exception as e:
        return str(e), 400



#now all this does is add 10 questions to the active unit
@app.route('/startUnit')
def startUnit():
    className = request.args.get('className')
    unitName = request.args.get('unitName')
    username = request.args.get('username')

    return addQuestions(className,unitName,username)







@app.route('/getQuestion')
def getQuestion():

    user = request.args.get('username')
    unit_name = request.args.get('unitName')
    class_name = request.args.get('className')
    question_number = request.args.get('qnum')
    ret = []
    try:
        with db_session:
            unit = Unit[unit_name, Cls[class_name]]
            attempt = get_max_unit(unit, user)
            active = ActiveUnit[unit,user,attempt]
            question = Question[active,active.currentQuestion+1]
            single_question = dict()
            single_question["id"]=question.id
            #single_question["question_preamble"] = question.question_preamble
            single_question["primary"] = question.question
            single_question["answer1"] = question.answer1
            single_question["answer2"] = question.answer2
            single_question["answer3"] = question.answer3
            single_question["answer4"] = question.answer4
            single_question["correct_ans"] = question.correct_ans
            single_question["preamble"] = question.question_preamble

            ret.append(single_question)
        return jsonify(ret)
    except Exception as e:
        return str(e), 400



#201 and the correct answer if answered incorrectly,
#200 if answered correctly but not enough consecutive
#204 if answered correctly and enough consecutive
@app.route('/submitQuestion', methods=['GET', 'POST'])
def submitQuestion():
    user = request.args.get('username')
    unit_name = request.args.get('unitName')
    class_name = request.args.get('className')
    question_number = request.args.get('qnum')
    ans_number = int(request.args.get('ans'))

    try:
        with db_session:
            retValue = 200
            unit = Unit[unit_name, Cls[class_name]]
            attempt = get_max_unit(unit, user)
            activeUnit = ActiveUnit[unit, user, attempt]
            question = Question[activeUnit, question_number]
            activeUnit.currentQuestion+=1

            if (not activeUnit.currentQuestion < activeUnit.quesAmount):
                addQuestions(class_name,unit_name,user)

            if question.correct_ans == ans_number:
                question.solved_correctly=True
                activeUnit.consecQues +=1

            else:
                question.solved_correctly=False
                activeUnit.consecQues =0
                return "incorrect",(200+question.correct_ans)

            if(activeUnit.consecQues == int (unit.Qnum) or activeUnit.consecQues > int(unit.Qnum)  ):
                activeUnit.inProgress=False
                activeUnit.grade=100
                return "answered enough consecutive questions",205

            return "correct"


            return "question answered",retValue
    except Exception as e:
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
