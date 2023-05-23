import unittest
import os
from pony.orm import db_session, Database, PrimaryKey, Required, Optional, Set, CacheIndexError, commit
from flaskProject import app
from flaskProject.app import User, DB, teacherCont, studentCont, Cls, Unit
from unittest import mock
from unittest.mock import patch, MagicMock


class MyTestCase(unittest.TestCase):
    def setUp(self):
        DB = Database()
        DB.bind(provider='sqlite', filename='..\\..\\dbtest.sqlite', create_db=True)

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


        # Generate mapping and create tables

        DB.generate_mapping(create_tables=True)

    def tearDown(self):
        DB.disconnect()
        # Remove the test database file after testing
        cwd = os.getcwd()
        os.remove('\\'.join(cwd.split('\\')[:-2]) + r'\dbtest.sqlite')

    def test_acceptance1(self):
        # Set up a test database with a sample class and a nonexistent unit
        with db_session:
            teacher = User(name="teacher1", password="password", type=1)
            cls = Cls(name="English", teacher=teacher)
            app.teacherOpenUnit("unit1", "teacher1", "English Class", "intersection_linear_-10,10,0,10", 4, "60", "2023-05-31", True, "", "desc")
            student1 = app.makeUser("student1", "123", 2)
            app.registerClass_buisness("student1", "English")
            app.approveStudentToClass_buisness("teacher1", "student1", "English", True)
            app.deleteUnit_buisness("unit1", "English", "teacher1")
            app.startUnit("English", "unit1", "student1")



if __name__ == '__main__':
    unittest.main()
