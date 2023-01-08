import random
from fractions import Fraction

from flask import Flask, request, jsonify
from flask_pony import Pony
from flask_cors import CORS
from pony.orm import *
from pony_database_facade import DatabaseFacade

app = Flask(__name__)
CORS(app)
pony = Pony(app)

DB = pony.db
DB.bind(provider='sqlite', filename='dbtest', create_db=True)

DATATYPE_SIZE = 3
QUESTIONTYPE_SIZE =4

class User(DB.Entity):
    name = PrimaryKey(str)
    password = Required(str)
    type = Required(int)
    teaching = Set('Cls', reverse='teacher')
    inClass = Set('Cls_User')
    activeUnits = Set("ActiveUnit", reverse='student')

class Cls(DB.Entity):
    name = PrimaryKey(str)
    teacher = Required(User, reverse='teaching')
    students = Set('Cls_User')
    hasUnits = Set('Unit', reverse='cls')
class Cls_User(DB.Entity):
    cls = Required(Cls)
    user = Required(User)
    approved = Required(bool)
    PrimaryKey(cls, user)

class Unit(DB.Entity):
    name = Required(str)
    cls = Required(Cls, reverse='hasUnits')
    template = Required(str)
    Qnum = Required(int)
    maxTime = Required(int)
    subDate = Required(int)
    instances = Set('ActiveUnit', reverse='unit')
    PrimaryKey(name, cls)

class Question(DB.Entity):
    id = Required(int)
    question_preamble = Required(str)
    question = Required(str)
    answer = Required(str)
    active_unit = Required('ActiveUnit',reverse='questions')
    solved_correctly = Optional(bool)
    PrimaryKey(active_unit,id)


class ActiveUnit(DB.Entity):
    inProgress = Required(bool)
    attempt = Required(int)
    questions = Set('Question',reverse= 'active_unit' )
    unit = Required(Unit, reverse='instances')
    student = Required(User, reverse='activeUnits')
    grade = Optional(int)
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





def is_legal_template(template:str):
    parts = template.split(',')
    data_type = int (parts[0])
    question_type = int (parts[1])

    if (not(( data_type>= 0 and data_type<DATATYPE_SIZE ) and ( question_type>= 0 and question_type<QUESTIONTYPE_SIZE ))):
        return False
    #todo check the tuples are correct
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
            print(result)
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
    if isinstance(activeControllers[username],teacherCont):
        return '1 '+ username
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
                return "successful password change",200
            else:
                return "wrong username or password",400
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
    try :
        with db_session:
            t = User[teacherName]
            if t.type == 1:
                Cls(name=className, teacher=User[teacherName])
                return "successful",200
            return "failed wrong type",400
    except Exception as e:
        return str(e), 400

@app.route('/removeClass')
def removeClass():
    teacherName = request.args.get('teacher')
    className = request.args.get('className')
    try :
        with db_session:
            t = User[teacherName]
            c = Cls[className]
            if c.teacher == t:
                c.delete()
                return "successful",200
            return "failed",400
    except Exception as e:
        return str(e), 400

@app.route('/editClass')
def editClass():
    teacherName = request.args.get('teacher')
    className = request.args.get('className')
    newClassName = request.args.get('newClassName')
    try :
        with db_session:
            print("a")
            t = User[teacherName]
            print(t)
            c = Cls[className]
            print(c)
            if c.teacher == t:
                print("b")
                Cls(name=newClassName, teacher=User[teacherName], students=c.students, hasUnits=c.hasUnits)
                c.delete()
                print("c")
                return "successful",200
            return "failed",400
    except Exception as e:
        print(e)
        return str(e), 400

@app.route('/editUnit')
def editUnit():
    unitName = request.args.get('unitName')
    className = request.args.get('className')

    teacherName = request.args.get('newTeacher')
    unitName = request.args.get('newUnitName')
    className = request.args.get('newClassName')
    template = request.args.get('newTemplate')
    Qnum = request.args.get('newQnum')
    maxTime = request.args.get('newMaxTime')
    subDate = request.args.get('newSubDate')
    try :
        with db_session:
            c = Cls[className]
            Unit[unitName,c].delete()
            commit()
            Unit(cls=c, name = unitName,template=template,Qnum=Qnum,maxTime=maxTime,subDate=subDate)
            return "successful",200
    except Exception as e:
        return str(e), 400


@app.route('/removeUnit')
def removeUnit():
    unitName = request.args.get('unitName')
    className = request.args.get('className')
    try :
        with db_session:
            u = Unit[unitName,Cls[className]]
            u.delete()
            return "successful",200
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
            c_u= Cls_User(cls=c,user=u,approved=False)
            u.inClass.add(c_u)
            c.students.add(c_u)

            commit()
            return "successful",200
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
                for unapproveRequest in Cls_User.select(cls = singleClass):
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
                b = Cls_User[c,u]
                Cls_User[c,u].approved = True
            else:
                Cls_User[c, u].delete()
            return "successful",200
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
            return "successful",200
    except Exception as e:
        return str(e), 400


def teacherOpenUnit(unitName, teacherName, className, template, Qnum, maxTime, subDate):
    if not is_legal_template(template):
        return "illegal template",400
    try:
        with db_session:
            Unit(cls=Cls[className], name = unitName,template=template,Qnum=Qnum,maxTime=maxTime,subDate=subDate)
            commit()
            return "success"
    except Exception as e:
        return str(e), 400 ,400

@app.route('/openUnit')
def openUnit():
    teacherName = request.args.get('teacher')
    unitName = request.args.get('unitName')
    className = request.args.get('className')
    template = request.args.get('template')
    Qnum = request.args.get('Qnum')
    maxTime = request.args.get('maxTime')
    subDate = request.args.get('subDate')

    if teacherName not in activeControllers:
        return "inactive user", 400
    AC = activeControllers[teacherName]
    if AC.typ == 1:
        return teacherOpenUnit(unitName, teacherName, className, template, Qnum, maxTime, subDate)
    return "invalid permissions" ,400

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
            ret =""
            for aUnit in Cls[className].hasUnits:
                ret += aUnit.name
            return ret
    except Exception as e:
        return str(e), 400

@app.route('/getClassesStudent')
def getClassesStudent():
    student = request.args.get('student')
    try:
        with db_session:
            ret =[]
            id =0
            for aUnit in Cls_User.select( user= student):
                single_obj = dict()
                id +=1
                single_obj["id"] = id
                single_obj ["primary"] = aUnit.cls.name
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
            ret =[]
            id =0
            for aUnit in Cls.select(teacher = teacher):
                single_obj = dict()
                id +=1
                single_obj["id"] = id
                single_obj ["primary"] = aUnit.name
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
            return Unit[unitName,Cls[className]]
    except Exception as e:
        return str(e), 400

def generate_cut_axis(parsed_template):
    preamble =\
    """Please enter the point in which the function cuts the x,y axis.
    The answer should be in the format (cuts with x axis, cuts with y axis).
    Round the answers to 2 digis"""


    minimum_range = -10
    maximum_range = 10


    #linear
    if(parsed_template[0]==0):
        if len(parsed_template) > 2:
            m_minimum = parsed_template[2][0][0]
            m_maximum = parsed_template[2][0][1]
            b_minimum = parsed_template[2][1][0]
            b_maximum = parsed_template[2][1][1]
            m= random.randint(m_minimum,m_maximum)
            b= random.randint(b_minimum,b_maximum)
        else:
            m= random.randint(minimum_range,maximum_range)
            while m==0:
                m = random.randint(minimum_range, maximum_range)
            b = random.randint(minimum_range, maximum_range)
        ans_x = (round( -b/m,2),0)
        if (ans_x == round(ans_x)):
            ans_x=round(ans_x)
        ans_y = (0,b)
        if (b==0):
            questions_string ="y=" + str(m)+"x"
        else:
            questions_string= ("y="+str(m)+"x"+ ('+' if b>0 else "") + str(b))

    return (preamble,questions_string,(ans_x,ans_y))







#template - [0] = type of function
#           [1] = type of question
#           [2] = list of variable restrictions

#question format - [0] = preamble
#                - [1] = question string
#                - [2] = ans (list?)


def parse_template(template):
    parts = template.split(',')
    return (int(parts[0]),int(parts[1]),parts[2:]) if len(parts)==3 else (int(parts[0]),int(parts[1]))


def get_questions(unit):
    questions = list()
    for i in range(unit.Qnum):
        parsed_template = parse_template(unit.template)
        if(parsed_template[1]==0):
            q = generate_cut_axis(parsed_template)
        # elif(parsed_template[1]==0):
        #     q =generate_maxima_and_minima(parsed_template)
        # elif(parsed_template[1]==0):
        #     q =generate_cut_axis(parsed_template)
        questions.append(q)
    return questions

def get_max_unit(unit,user):
    maxAttempt = 0
    for activeU in ActiveUnit.select(unit=unit, student=user):
        if activeU.attempt > maxAttempt:
            maxAttempt = activeU.attempt
    return maxAttempt

@app.route('/startUnit')
def startUnit():
    className = request.args.get('className')
    unitName = request.args.get('unitName')
    username = request.args.get('username')

    try:
        with db_session:
            unit = Unit[unitName, Cls[className]]
            user = User[username]
            maxAttempt=get_max_unit(unit,user)
            for activeU in ActiveUnit.select(unit =unit, student=user):
                if(activeU.inProgress == True):
                    return "Already in progress, end attempt before starting another",400

            id=1
            ActiveUnit(inProgress=True, unit=unit, student=user, attempt=maxAttempt + 1)
            for single_question in get_questions(unit):
                Question(id=id, question_preamble=single_question[0],question=single_question[1], answer= str(single_question[2])[1:-1],active_unit= ActiveUnit[unit,user,(maxAttempt+1)])
                id+=1
            commit()
            return "added unit"
    except Exception as e:
        return str(e), 400
    return "added unit"

@app.route('/getQuestion')
def getQuestion():

    user = request.args.get('username')
    unit_name = request.args.get('unitName')
    class_name = request.args.get('className')

    ret = []
    try:
        with db_session:
            unit = Unit[unit_name, Cls[class_name]]
            attempt = get_max_unit(unit, user)
            for i in range (1,unit.Qnum):
                question = Question[ActiveUnit[unit,user,attempt],i]
                single_question = dict()
                single_question["id"]=question.id
                #single_question["question_preamble"] = question.question_preamble
                single_question["primary"] = question.question
                ret.append(single_question)
        return jsonify(ret)
    except Exception as e:
        return str(e), 400


@app.route('/submitQuestions',methods = ['GET', 'POST'])
def submitQuestions():
    user = request.args.get('username')
    unit_name = request.args.get('unitName')
    class_name = request.args.get('className')
    answers = request.get_json()

    try:
        with db_session:
            unit = Unit[unit_name, Cls[class_name]]
            attempt = get_max_unit(unit, user)
            correct = 0

            for key in answers:
                if(key == '0'):
                    continue
                question = Question[ActiveUnit[unit,user,attempt],key]
                solved_correctly = (answers[key].replace(" ", "") == question.answer.replace(" ", ""))
                question.solved_correctly = solved_correctly
                if question.solved_correctly :correct +=1


            #finish the unit
            user = User[user]
            active_unit = ActiveUnit[unit,user,attempt]
            active_unit.inProgress=False
            active_unit.grade = round ((correct/unit.Qnum)*100)
            print(active_unit.grade)
        return "ended Unit with grade " + str(active_unit.grade)
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
        #add open unit logic
        return "openUnit"+Uname+cls+template+Qnum+maxTime+subDate

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