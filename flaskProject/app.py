
from flask import Flask, request
from flask_pony import Pony
from flask_cors import CORS
from pony.orm import *
from pony_database_facade import DatabaseFacade

app = Flask(__name__)
CORS(app)
pony = Pony(app)

DB = pony.db
DB.bind(provider='sqlite', filename='dbtest', create_db=True)

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
class Template(DB.Entity):
    name = PrimaryKey(str)
    temp = Required(str)
    inUnits = Set('Unit', reverse='template')
class Unit(DB.Entity):
    name = Required(str)
    cls = Required(Cls, reverse='hasUnits')
    template = Required(Template, reverse='inUnits')
    Qnum = Required(int)
    maxTime = Required(int)
    subDate = Required(int)
    instances = Set('ActiveUnit', reverse='unit')
    PrimaryKey(name, cls)
class ActiveUnit(DB.Entity):
    inProgress = Required(bool)
    attempt = Required(int)
    unit = Required(Unit, reverse='instances')
    student = Required(User, reverse='activeUnits')
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
        return str(e)


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







def teacherOpenUnit(unitName, teacherName, className, template, Qnum, maxTime, subDate):
    try:
        with db_session:
            Unit(cls=Cls[className], name = unitName,template=template,Qnum=Qnum,maxTime=maxTime,subDate=subDate)
            commit()
            return
    except Exception as e:
        return str(e)

@app.route('/register')
def register():
    username = request.args.get('username')
    password = request.args.get('password')
    typ = request.args.get('typ')
    if not checkValidUsername(username) or not checkValidPassword(password):
        return "invalid username or password", 403

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
        return "invalid username or password", 403
    loadController(username)
    return username + " " + password + " " + str(len(activeControllers))


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
                return "wrong username or password",403
    except Exception:
        return "wrong username or password", 403


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
            if t.type ==1:
                Cls(name=className, teacher=User[teacherName])
                return "successful",200
            return "failed wrong type",403
    except Exception as e:
        return str(e),403

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
            return "failed",403
    except Exception as e:
        return str(e),403

@app.route('/editClass')
def editClass():
    teacherName = request.args.get('teacher')
    className = request.args.get('className')
    newClassName = request.args.get('newClassName')
    try :
        with db_session:
            t = User[teacherName]
            c = Cls[className]
            if c.teacher == t:
                c.name = newClassName
                return "successful",200
            return "failed",403
    except Exception as e:
        return str(e),403

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
        return str(e),403


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
        return str(e),403

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
        return str(e),403

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
        return str(e),403

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
        return str(e),403



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
        return "inactive user", 403
    AC = activeControllers[teacherName]
    if AC.typ == 1:
        return teacherOpenUnit(unitName, teacherName, className, template, Qnum, maxTime, subDate)
    return "invalid permissions"

@app.route('/getUnit')
def getUnit():
    unitName = request.args.get('unitName')
    className = request.args.get('className')
    try:
        with db_session:
            retUnit = Unit[unitName, Cls[className]]
            return retUnit.name +"dan "
    except Exception as e:
        return str(e)

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
        return str(e)

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
        return str(e)

@app.route('/getUnitDetails')
def getUnitDetails():
    className = request.args.get('className')
    unitName = request.args.get('unitName')
    try:
        with db_session:
            return Unit[unitName,Cls[className]]
    except Exception as e:
        return str(e)

@app.route('/startUnit')
def startUnit():
    className = request.args.get('className')
    unitName = request.args.get('unitName')
    username = request.args.get('username')

    try:
        with db_session:
            unit = Unit[unitName, Cls[className]]
            user = User[username]
            maxAttempt=0
            for activeU in ActiveUnit.select(unit =unit, student=user):
                if(activeU.inProgress == True):
                    return "Already in progress, end attempt before starting another",403
                if activeU.attempt>maxAttempt :
                    maxAttempt = activeU.attempt
            ActiveUnit(inProgress=True, unit = unit, student = user, attempt = maxAttempt+1)
            commit ()
            return "added unit"
    except Exception as e:
        return str(e)
    return "added unit"

    #PrimaryKey(unit, student)

@app.route('/submitUnit')
def submitUnit():
    className = request.args.get('className')
    unitName = request.args.get('unitName')
    username = request.args.get('username')

    try:
        with db_session:
            unit = Unit[unitName, Cls[className]]
            user = User[username]
            ActiveUnit[unit,user].inProgress=False
            commit ()
            return "ended Unit"
    except Exception as e:
        return str(e)
    return "added unit"
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
