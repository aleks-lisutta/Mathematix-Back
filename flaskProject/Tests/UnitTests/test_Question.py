import unittest
from pony.orm import db_session, Database
from flaskProject import app
from flaskProject.Tests.UnitTests import initiate_database
from flaskProject.app import DB



class MyTestCase(unittest.TestCase):
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



    def test_getQuestion_successful(self):
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
            # Check that student gets question
            res = app.getQuestion_buisness('student1', 'unit1', 'class1', '1')
            self.assertEqual(200, res.status_code, 'Failed getQuestion request')

    def test_getQuestion_no_unit_failure(self):
        with app.app.app_context():
            # Create teacher account and open a class
            app.register_buisness('teacher1', 'password', 1)
            app.login_buisness('teacher1', 'password')
            app.openClass_buisness('teacher1', 'class1')
            # Create student account and register to class
            app.register_buisness('student1', 'password', 2)
            app.login_buisness('student1', 'password')
            app.registerClass_buisness('student1', 'class1')
            app.approveStudentToClass_buisness('teacher1', 'student1', 'class1', 'True')
            # Student starts unit
            app.startUnit_buisness('class1', 'unit1', 'student1')
            # Check that student gets question
            res = app.getQuestion_buisness('student1', 'unit1', 'class1', '1')
            self.assertEqual(2, len(res), 'Wrong return value for getQuestion')
            self.assertEqual(400, res[1], 'Succeeded getQuestion request')

    def test_submitQuestion_successful(self):
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
            # Check that student submitQuestion works
            res = app.getQuestion_buisness('student1', 'unit1', 'class1', '1')
            self.assertEqual(200, res.status_code, 'Failed getQuestion request')
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', '1', res.json[0]['correct_ans'])
            self.assertEqual(2, len(res), 'Wrong return value for getQuestion')
            self.assertEqual(205, res[1], 'Failed submitQuestion request')

    def test_submitQuestion_two_in_a_row_successful(self):
        with app.app.app_context():
            # Create teacher account and open a class and a unit
            app.register_buisness('teacher1', 'password', 1)
            app.login_buisness('teacher1', 'password')
            app.openClass_buisness('teacher1', 'class1')
            app.teacherOpenUnit('unit1', 'teacher1', 'class1', 'intersection_linear_-10,0,1,6', '2', '60', '2023-07-01',
                                'true', 'new', 'desc')
            # Create student account and register to class
            app.register_buisness('student1', 'password', 2)
            app.login_buisness('student1', 'password')
            app.registerClass_buisness('student1', 'class1')
            app.approveStudentToClass_buisness('teacher1', 'student1', 'class1', 'True')
            # Student starts unit
            app.startUnit_buisness('class1', 'unit1', 'student1')
            # Check that student submitQuestion works
            res = app.getQuestion_buisness('student1', 'unit1', 'class1', '1')
            prehamble_1 = res.json[0]["preamble"]
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', '1', res.json[0]['correct_ans'])
            self.assertEqual('correct', res, 'Wrong return value for submitQuestion')
            res = app.getQuestion_buisness('student1', 'unit1', 'class1', '2')
            prehamble_2 = res.json[0]["preamble"]
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', '2', res.json[0]['correct_ans'])
            self.assertEqual(prehamble_1,prehamble_2)
            self.assertEqual(2, len(res), 'Wrong return value for submitQuestion')
            self.assertEqual(205, res[1], 'Failed submitQuestion request')


    def test_submitQuestion_one_wrong_two_correct_finish_successful(self):
        with app.app.app_context():
            # Create teacher account and open a class and a unit
            app.register_buisness('teacher1', 'password', 1)
            app.login_buisness('teacher1', 'password')
            app.openClass_buisness('teacher1', 'class1')
            app.teacherOpenUnit('unit1', 'teacher1', 'class1', 'intersection_linear_-10,0,1,6', '2', '60', '2023-07-01',
                                'true', 'new', 'desc')
            # Create student account and register to class
            app.register_buisness('student1', 'password', 2)
            app.login_buisness('student1', 'password')
            app.registerClass_buisness('student1', 'class1')
            app.approveStudentToClass_buisness('teacher1', 'student1', 'class1', 'True')
            # Student starts unit
            app.startUnit_buisness('class1', 'unit1', 'student1')
            # Check that student submitQuestion works
            res = app.getQuestion_buisness('student1', 'unit1', 'class1', '1')
            prehamble_1 = res.json[0]["preamble"]
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', '1', res.json[0]['correct_ans'])
            self.assertEqual('correct', res, 'Wrong return value for submitQuestion')
            res = app.getQuestion_buisness('student1', 'unit1', 'class1', '2')
            prehamble_2 = res.json[0]["preamble"]
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', '2', '-1')
            self.assertEqual(prehamble_1,prehamble_2)
            self.assertEqual(2, len(res), 'Wrong return value for submitQuestion')
            #from the begining answerint 2 in a row
            res = app.getQuestion_buisness('student1', 'unit1', 'class1', '3')
            prehamble_3 = res.json[0]["preamble"]
            self.assertEqual(prehamble_3, prehamble_2)
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', '3', res.json[0]['correct_ans'])
            self.assertEqual('correct', res, 'Wrong return value for submitQuestion')
            res = app.getQuestion_buisness('student1', 'unit1', 'class1', '4')
            prehamble_4 = res.json[0]["preamble"]
            self.assertEqual(prehamble_3, prehamble_4)
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', '4', res.json[0]['correct_ans'])
            self.assertEqual(205, res[1], 'Failed submitQuestion request')


    def test_submitQuestion_wrong_answer_successful(self):
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
            # Check that student submitQuestion works
            res = app.getQuestion_buisness('student1', 'unit1', 'class1', '1')
            correct_ans = res.json[0]['correct_ans']
            self.assertEqual(200, res.status_code, 'Failed getQuestion request')
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', '1', '-1')
            self.assertEqual(2, len(res), 'Wrong return value for getQuestion')
            self.assertEqual(200 + int(correct_ans), res[1], 'Failed submitQuestion request')

    def test_submitQuestion_before_start_unit_failure(self):
        with app.app.app_context():
            # Create teacher account and open a class
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
            # Check that submitQuestion doesnt work
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', '1', '1')
            self.assertEqual(2, len(res), 'Wrong return value for getQuestion')
            self.assertEqual(400, res[1], 'Succeeded getQuestion request')







if __name__ == '__main__':
    unittest.main()
