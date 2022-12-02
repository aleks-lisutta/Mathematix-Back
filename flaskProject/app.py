import email.message

from flask import Flask, request
from flask_pony import Pony
from pony.orm import *
from pony_database_facade import DatabaseFacade

app = Flask(__name__)
pony = Pony(app)

DB = pony.db
DB.bind(provider='sqlite', filename='dbtest', create_db=True)


class User(DB.Entity):
    name = PrimaryKey(str)
    password = Required(str)
    type = Required(int)
    teaching = Set('Cls', reverse='teacher')
    inClass = Set('Cls', reverse='students')
    activeUnits = Set("ActiveUnit", reverse='student')


class Cls(DB.Entity):
    name = PrimaryKey(str)
    teacher = Required(User, reverse='teaching')
    students = Set('User', reverse='inClass')
    hasUnits = Set('Unit', reverse='cls')


class Template(DB.Entity):
    name = PrimaryKey(str)
    temp = Required(str)
    inUnits = Set('Unit', reverse='template')


class Unit(DB.Entity):
    name = Required(str)
    cls = Required(Cls,  reverse='hasUnits')
    template = Required(Template, reverse='inUnits')
    Qnum = Required(int)
    maxTime = Required(int)
    subDate = Required(int)
    instances = Set('ActiveUnit', reverse='unit')
    PrimaryKey(name, cls)


class ActiveUnit(DB.Entity):
    unit = Required(Unit, reverse='instances')
    student = Required(User, reverse='activeUnits')
    PrimaryKey(unit, student)


DB.generate_mapping(create_tables=True)


activeControllers = {}


@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'


def checkValidUsername(username):
    return True


def checkValidPassword(password):
    return True


def makeUser(username, password, type):
    try:
        with db_session:
            User(name=username, password=password, type=type)
            commit()
            result = DB.select("select * from User")
            return str(result)
    except Exception as e:
        return str(e)


@app.route('/register')
def register():
    username = request.args.get('username')
    password = request.args.get('password')
    type = request.args.get('type')
    if not checkValidUsername(username) or not checkValidPassword(password):
        return "invalid username or password", 403
    makeUser(username, password, type)
    return username + " " + password + " " + type


def checkUserPass(username, password):
    return True


def checkType(username):
    return 1


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


@app.route('/logout')
def logout():
    username = request.args.get('username')
    activeControllers.pop(username)
    return username + " " + str(len(activeControllers))

class userCont:

    def __init__(self, username):
        self.username = username


class studentCont(userCont):

    def registerClass(self, Cname):
        return "registerClass", Cname

    def getClassUnits(self, Cname):
        return "getClassUnits", Cname

    def getUnit(self, Uname):
        return "getUnit", Uname

    def startUnit(self, Uname):
        return "startUnit", Uname

    def getQuestion(self, Uname, Qnum):
        return "getQuestion", Uname, Qnum

    def answerQuestion(self, Uname, Qnum, answer):
        return "answerQuestion", Uname, Qnum, answer

    def submitUnit(self, Uname):
        return "submitUnit", Uname


class teacherCont(userCont):

    def openUnit(self, Uname, cls, template, Qnum, maxTime, subDate):
        return "openUnit", Uname, cls, template, Qnum, maxTime, subDate

    def editUnit(self, Uname, cls, newUname, template, Qnum, maxTime, subDate):
        return "editUnit", Uname, cls, newUname, template, Qnum, maxTime, subDate

    def getUnit(self, Uname):
        return "getUnit" + " " + Uname

    def deleteUnit(self, Uname):
        return "deleteUnit", Uname

    def openClass(self, Cname):
        return "openClass", Cname


if __name__ == '__main__':
    app.run()
