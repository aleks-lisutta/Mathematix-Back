import unittest
import os
from pony.orm import db_session, Database, PrimaryKey, Required, Optional, Set, CacheIndexError, commit
from flaskProject import app
from flaskProject.Tests.UnitTests import initiate_database
from flaskProject.app import User, DB, teacherCont, studentCont, Cls, Unit, QUESTIONS_TO_GENERATE
from unittest import mock
from unittest.mock import patch, MagicMock


class TestGetMaxUnit(unittest.TestCase):
    DB = None

    @classmethod
    def setUpClass(cls):
        cls.DB = Database()
        DB = cls.DB
        initiate_database(DB)

    @classmethod
    def tearDownClass(cls):
        cls.DB.drop_all_tables()
        cls.DB.disconnect()

    def tearDown(self) -> None:
        with app.app.app_context():
            app.activeControllers = {}
        with db_session:
            DB.execute('DELETE FROM ActiveUnit WHERE 1=1;')
            DB.execute('DELETE FROM Question WHERE 1=1;')
            DB.execute('DELETE FROM Unit WHERE 1=1;')
            DB.execute('DELETE FROM Cls_User WHERE 1=1;')
            DB.execute('DELETE FROM Cls WHERE 1=1;')
            DB.execute('DELETE FROM User WHERE 1=1;')

    def test_get_max_unit_success(self):
        with app.app.app_context():
            # Create teacher account and open a class and a unit
            app.register_buisness('teacher1', 'password', 1)
            app.login_buisness('teacher1', 'password')
            app.openClass_buisness('teacher1', 'class1')
            app.teacherOpenUnit('unit1', 'teacher1', 'class1', 'intersection_linear_-10,0,1,6', '1', '60', '2023-07-01',
                                'true', 'new', 'desc')
            # Create student account and register to class
            app.register_buisness('student1', 'password', 2)
            app.login_buisness('student1', 'password')
            app.registerClass_buisness('student1', 'class1')
            app.approveStudentToClass_buisness('teacher1', 'student1', 'class1', 'True')
            # Student starts unit
            app.startUnit_buisness('class1', 'unit1', 'student1')
            res = app.getQuestion_buisness('student1', 'unit1', 'class1', '1')
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', '1', res.json[0]['correct_ans'])
            app.startUnit_buisness('class1', 'unit1', 'student1')
            res = app.getQuestion_buisness('student1', 'unit1', 'class1', '1')
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', '1', res.json[0]['correct_ans'])
            app.startUnit_buisness('class1', 'unit1', 'student1')
            res = app.getQuestion_buisness('student1', 'unit1', 'class1', '1')
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', '1', res.json[0]['correct_ans'])
            app.startUnit_buisness('class1', 'unit1', 'student1')
            res = app.getQuestion_buisness('student1', 'unit1', 'class1', '1')
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', '1', res.json[0]['correct_ans'])
            with db_session:
                student1 = app.User.select(lambda au: au.name == 'student1')[:].to_list()[0]
                unit = app.Unit.select(lambda au: au.name == 'unit1')[:].to_list()[0]
                # Call the function under test
                max_attempt = app.get_max_unit(unit, student1)

            # Assert the expected result
            self.assertEqual(max_attempt, 4)


    def test_addQuestions_successful(self):
        with db_session:
            with app.app.app_context():
                # Create a test User and Unit
                student = User(name="student1", password="123", type=2)
                teacher = User(name="teacher1", password="123", type=1)
                c = Cls(name="Math", teacher=teacher)
                unit = Unit(
                    name="Math",
                    cls=c,
                    desc="Basic algebra",
                    template="intersection_linear_-10,0,1,6",
                    Qnum="10",
                    maxTime="60",
                    subDate="2023-05-31",
                    order=1,
                    # next=None
                )
                app.ActiveUnit(unit=unit, student=student, attempt=1, inProgress=True, consecQues=2,
                               quesAmount=0, currentQuestion=0, totalCorrect=0)
                res = app.addQuestions_buisness('Math', 'Math', 'student1')
                self.assertEqual(200, res.status_code, 'request failed')
                active = app.ActiveUnit.select(lambda au: au.student.name == 'student1')[:].to_list()[0]
                self.assertEqual(QUESTIONS_TO_GENERATE, active.quesAmount, 'question not added')

    def test_addQuestions_unit_has_enough_questions_successful(self):
        with db_session:
            with app.app.app_context():
                # Create a test User and Unit
                student = User(name="student1", password="123", type=2)
                teacher = User(name="teacher1", password="123", type=1)
                c = Cls(name="Math", teacher=teacher)
                unit = Unit(
                    name="Math",
                    cls=c,
                    desc="Basic algebra",
                    template="intersection_linear_-10,0,1,6",
                    Qnum="10",
                    maxTime="60",
                    subDate="2023-05-31",
                    order=1,
                    # next=None
                )
                app.ActiveUnit(unit=unit, student=student, attempt=1, inProgress=True, consecQues=2,
                               quesAmount=10, currentQuestion=2, totalCorrect=0)
                res = app.addQuestions_buisness('Math', 'Math', 'student1')
                self.assertEqual(200, res.status_code, 'request failed')
                active = app.ActiveUnit.select(lambda au: au.student.name == 'student1')[:].to_list()[0]
                self.assertEqual(10, active.quesAmount, 'question not added')

    def test_individualStats_successful(self):
        with app.app.app_context():
            # Create teacher account and open a class and a unit
            app.register_buisness('teacher1', 'password', 1)
            app.login_buisness('teacher1', 'password')
            app.openClass_buisness('teacher1', 'class1')
            app.teacherOpenUnit('unit1', 'teacher1', 'class1', 'intersection_linear_-10,0,1,6', '5', '60', '2023-07-01',
                                'true', 'new', 'desc')
            # Create student account and register to class
            app.register_buisness('student1', 'password', 2)
            app.login_buisness('student1', 'password')
            app.registerClass_buisness('student1', 'class1')
            app.approveStudentToClass_buisness('teacher1', 'student1', 'class1', 'True')
            # Student starts unit
            app.startUnit_buisness('class1', 'unit1', 'student1')
            # Student answers 2 correctly and 1 incorrectly
            res = app.getQuestion_buisness('student1', 'unit1', 'class1', '1')
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', '1', res.json[0]['correct_ans'])
            self.assertEqual('correct', res, 'Wrong return value for submitQuestion')
            res = app.getQuestion_buisness('student1', 'unit1', 'class1', '1')
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', '2', res.json[0]['correct_ans'])
            self.assertEqual('correct', res, 'Wrong return value for submitQuestion')
            res = app.getQuestion_buisness('student1', 'unit1', 'class1', '3')
            correct_ans = res.json[0]['correct_ans']
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', '3', '-1')
            self.assertEqual(2, len(res), 'Wrong return value for submitQuestion')
            self.assertEqual(200 + int(correct_ans), res[1], 'Failed submitQuestion request')
            res = app.individualStats_buisness('class1', 'unit1', 'teacher1', 'student1')
            self.assertEqual([2, 1], res.json['correctIncorrect'])
            self.assertEqual([66, 0, 0, 0, 0], res.json['L5']) # 66 == 2/3, correct/total for unit1

    def test_individualStats_multiple_units_successful(self):
        with app.app.app_context():
            # Create teacher account and open a class and a unit
            app.register_buisness('teacher1', 'password', 1)
            app.login_buisness('teacher1', 'password')
            app.openClass_buisness('teacher1', 'class1')
            app.teacherOpenUnit('unit1', 'teacher1', 'class1', 'intersection_linear_-10,0,1,6', '5', '60', '2023-07-01',
                                'true', 'new', 'desc')
            app.teacherOpenUnit('unit2', 'teacher1', 'class1', 'intersection_linear_-10,0,1,6', '5', '60', '2023-07-01',
                                'true', 'new', 'desc')
            # Create student account and register to class
            app.register_buisness('student1', 'password', 2)
            app.login_buisness('student1', 'password')
            app.registerClass_buisness('student1', 'class1')
            app.approveStudentToClass_buisness('teacher1', 'student1', 'class1', 'True')
            # Student starts unit1
            app.startUnit_buisness('class1', 'unit1', 'student1')
            # Student answers 2 correctly and 1 incorrectly
            res = app.getQuestion_buisness('student1', 'unit1', 'class1', '1')
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', '1', res.json[0]['correct_ans'])
            self.assertEqual('correct', res, 'Wrong return value for submitQuestion')
            res = app.getQuestion_buisness('student1', 'unit1', 'class1', '1')
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', '2', res.json[0]['correct_ans'])
            self.assertEqual('correct', res, 'Wrong return value for submitQuestion')
            res = app.getQuestion_buisness('student1', 'unit1', 'class1', '3')
            correct_ans = res.json[0]['correct_ans']
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', '3', '-1')
            self.assertEqual(2, len(res), 'Wrong return value for submitQuestion')
            self.assertEqual(200 + int(correct_ans), res[1], 'Failed submitQuestion request')
            # Student starts unit2
            app.startUnit_buisness('class1', 'unit2', 'student1')
            # Student answers 1 correctly
            res = app.getQuestion_buisness('student1', 'unit2', 'class1', '1')
            res = app.submitQuestion_buisness('student1', 'unit2', 'class1', '1', res.json[0]['correct_ans'])
            self.assertEqual('correct', res, 'Wrong return value for submitQuestion')
            # Check stats
            res = app.individualStats_buisness('class1', 'unit1', 'teacher1', 'student1')
            self.assertEqual([2, 1], res.json['correctIncorrect'])
            self.assertEqual([100, 66, 0, 0, 0], res.json['L5'])  # 66 == 2/3, correct/total for unit1
            res = app.individualStats_buisness('class1', 'unit2', 'teacher1', 'student1')
            self.assertEqual([1, 0], res.json['correctIncorrect'])
            self.assertEqual([100, 66, 0, 0, 0], res.json['L5'])  # 100 == 1/1, correct/total for unit1

    def test_quitActiveUnit_successful(self):
        with app.app.app_context():
            # Create teacher account and open a class and a unit
            app.register_buisness('teacher1', 'password', 1)
            app.login_buisness('teacher1', 'password')
            app.openClass_buisness('teacher1', 'class1')
            app.teacherOpenUnit('unit1', 'teacher1', 'class1', 'intersection_linear_-10,0,1,6', '5', '60', '2023-07-01',
                                'true', 'new', 'desc')
            # Create student account and register to class
            app.register_buisness('student1', 'password', 2)
            app.login_buisness('student1', 'password')
            app.registerClass_buisness('student1', 'class1')
            app.approveStudentToClass_buisness('teacher1', 'student1', 'class1', 'True')
            # Student starts unit
            app.startUnit_buisness('class1', 'unit1', 'student1')
            # Quit active unit
            res = app.quitActiveUnit_buisness('student1', 'unit1', 'class1')
            self.assertEqual('done', res, 'Quit active unit failure.')
            with db_session:
                active = app.ActiveUnit.select(lambda au: au.student.name == 'student1')[:].to_list()[0]
                self.assertFalse(active.inProgress)

    def test_quitActiveUnit_quit_before_start_failure(self):
        with app.app.app_context():
            # Create teacher account and open a class and a unit
            app.register_buisness('teacher1', 'password', 1)
            app.login_buisness('teacher1', 'password')
            app.openClass_buisness('teacher1', 'class1')
            app.teacherOpenUnit('unit1', 'teacher1', 'class1', 'intersection_linear_-10,0,1,6', '5', '60', '2023-07-01',
                                'true', 'new', 'desc')
            # Create student account and register to class
            app.register_buisness('student1', 'password', 2)
            app.login_buisness('student1', 'password')
            app.registerClass_buisness('student1', 'class1')
            app.approveStudentToClass_buisness('teacher1', 'student1', 'class1', 'True')
            # Quit active unit
            res = app.quitActiveUnit_buisness('student1', 'unit1', 'class1')
            self.assertEqual(2, len(res), 'Wrong return value for submitQuestion')
            self.assertEqual(400, res[1], 'Failed submitQuestion request')


if __name__ == '__main__':
    unittest.main()
