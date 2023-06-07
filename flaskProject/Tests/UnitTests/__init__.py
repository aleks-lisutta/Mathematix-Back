from pony.orm import db_session, Database, PrimaryKey, Required, Optional, Set, CacheIndexError, commit


def initiate_database(db):
    db.bind(provider='sqlite', filename='..\\..\\dbtest.sqlite', create_db=True)

    class User(db.Entity):
        name = PrimaryKey(str)
        password = Required(str)
        type = Required(int)
        teaching = Set('Cls', reverse='teacher', cascade_delete=False)
        inClass = Set('Cls_User', cascade_delete=False)
        activeUnits = Set("ActiveUnit", reverse='student')

    class Cls(db.Entity):
        name = PrimaryKey(str)
        teacher = Required(User, reverse='teaching')
        students = Set('Cls_User')
        hasUnits = Set('Unit', reverse='cls', cascade_delete=False)

    class Cls_User(db.Entity):
        cls = Required(Cls)
        user = Required(User)
        approved = Required(bool)
        PrimaryKey(cls, user)

    class Unit(db.Entity):
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

    class Question(db.Entity):
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

    class ActiveUnit(db.Entity):
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

    # Generate mapping and create tables
    db.generate_mapping(create_tables=True)
