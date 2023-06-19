import json
import random
import unittest
import os

import numpy as np
from pony.orm import db_session, Database, PrimaryKey, Required, Optional, Set, CacheIndexError, commit

import flaskProject
from flaskProject import app
from flaskProject.Tests.UnitTests import initiate_database
from flaskProject.app import User, DB, teacherCont, studentCont, Cls, Unit
from unittest import mock
from unittest.mock import patch, MagicMock


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


    def test_1good_1bad_successful(self):
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
            # student answers correctly
            ques = app.getQuestion_buisness('student1', 'unit1', 'class1', '1')
            self.assertEqual(200, ques.status_code, 'Failed getQuestion request')
            data = json.loads(ques.get_data(as_text=True))
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', 1, data[0]['correct_ans'])
            self.assertEqual(205, res[1], 'Failed getQuestion request')
            # student answers incorrectly
            ques = app.getQuestion_buisness('student1', 'unit1', 'class1', '2')
            self.assertEqual(200, ques.status_code, 'Failed getQuestion request')
            data2 = json.loads(ques.get_data(as_text=True))
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', 2, (data2[0]['correct_ans']-1) % 4)
            self.assertNotEqual(205, res[1], 'Failed submitQuestion_buisness request')
            #check statistics
            stats = app.getAllLessonQuestionsB('class1', 'unit1')
            self.assertEqual(200, stats[1], 'Failed getAllLessonQuestionsB request')
            self.assertEqual(1, len(stats[0]))
            self.assertEqual(2, len(stats[0]['student1']), 'Failed getAllLessonQuestionsB request')
            self.assertEqual(data[0]['answer'+str(data[0]['correct_ans'])], stats[0]['student1'][0]['answer'+str(data[0]['correct_ans'])])
            self.assertEqual(data2[0]['answer' + str(data2[0]['correct_ans'])], stats[0]['student1'][1]['answer' + str(data2[0]['correct_ans'])])

    def test_2students_successful(self):
        with app.app.app_context():
            # Create teacher account and open a class and a unit
            app.register_buisness('teacher1', 'password', 1)
            app.login_buisness('teacher1', 'password')
            app.openClass_buisness('teacher1', 'class1')
            app.teacherOpenUnit('unit1', 'teacher1', 'class1', 'intersection_linear_-10,0,1,6', '1', '60', '2023-07-01',
                                'true', 'new', 'desc')
            # Create student account and register to class
            app.register_buisness('student1', 'password', 2)
            app.register_buisness('student2', 'password', 2)

            app.login_buisness('student1', 'password')
            app.registerClass_buisness('student1', 'class1')
            app.approveStudentToClass_buisness('teacher1', 'student1', 'class1', 'True')
            app.login_buisness('student2', 'password')
            app.registerClass_buisness('student2', 'class1')
            app.approveStudentToClass_buisness('teacher1', 'student2', 'class1', 'True')
            # Student starts unit
            app.startUnit_buisness('class1', 'unit1', 'student1')
            # student answers correctly
            ques = app.getQuestion_buisness('student1', 'unit1', 'class1', '1')
            self.assertEqual(200, ques.status_code, 'Failed getQuestion request')
            data = json.loads(ques.get_data(as_text=True))
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', 1, data[0]['correct_ans'])
            self.assertEqual(205, res[1], 'Failed getQuestion request')
            # student answers incorrectly
            ques = app.getQuestion_buisness('student1', 'unit1', 'class1', '2')
            self.assertEqual(200, ques.status_code, 'Failed getQuestion request')
            data2 = json.loads(ques.get_data(as_text=True))
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', 2, (data2[0]['correct_ans']-1) % 4)
            self.assertNotEqual(205, res[1], 'Failed submitQuestion_buisness request')

            # Student starts unit
            app.startUnit_buisness('class1', 'unit1', 'student2')
            # student answers correctly
            ques = app.getQuestion_buisness('student2', 'unit1', 'class1', '1')
            self.assertEqual(200, ques.status_code, 'Failed getQuestion request')
            data3 = json.loads(ques.get_data(as_text=True))
            res = app.submitQuestion_buisness('student2', 'unit1', 'class1', 1, data3[0]['correct_ans'])
            self.assertEqual(205, res[1], 'Failed getQuestion request')
            # student answers incorrectly
            ques = app.getQuestion_buisness('student2', 'unit1', 'class1', '2')
            self.assertEqual(200, ques.status_code, 'Failed getQuestion request')
            data4 = json.loads(ques.get_data(as_text=True))
            res = app.submitQuestion_buisness('student2', 'unit1', 'class1', 2, (data4[0]['correct_ans']-1) % 4)
            self.assertNotEqual(205, res[1], 'Failed submitQuestion_buisness request')
            #check statistics
            stats = app.getAllLessonQuestionsB('class1', 'unit1')
            self.assertEqual(200, stats[1], 'Failed getAllLessonQuestionsB request')
            self.assertEqual(2, len(stats[0]))
            self.assertEqual(2, len(stats[0]['student1']), 'Failed getAllLessonQuestionsB request')
            self.assertEqual(2, len(stats[0]['student2']), 'Failed getAllLessonQuestionsB request')
            self.assertEqual(data[0]['answer'+str(data[0]['correct_ans'])], stats[0]['student1'][0]['answer'+str(data[0]['correct_ans'])])
            self.assertEqual(data2[0]['answer' + str(data2[0]['correct_ans'])], stats[0]['student1'][1]['answer' + str(data2[0]['correct_ans'])])
            self.assertEqual(data3[0]['answer' + str(data3[0]['correct_ans'])], stats[0]['student2'][0]['answer' + str(data3[0]['correct_ans'])])
            self.assertEqual(data4[0]['answer' + str(data4[0]['correct_ans'])], stats[0]['student2'][1]['answer' + str(data4[0]['correct_ans'])])

    def test_2attempts_successful(self):
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
            # student answers correctly
            ques = app.getQuestion_buisness('student1', 'unit1', 'class1', '1')
            self.assertEqual(200, ques.status_code, 'Failed getQuestion request')
            data = json.loads(ques.get_data(as_text=True))
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', 1, data[0]['correct_ans'])
            self.assertEqual(205, res[1], 'Failed getQuestion request')
            # student answers incorrectly
            ques = app.getQuestion_buisness('student1', 'unit1', 'class1', '2')
            self.assertEqual(200, ques.status_code, 'Failed getQuestion request')
            data2 = json.loads(ques.get_data(as_text=True))
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', 2, (data2[0]['correct_ans']-1) % 4)
            self.assertNotEqual(205, res[1], 'Failed submitQuestion_buisness request')

            # Student starts unit
            app.startUnit_buisness('class1', 'unit1', 'student1')
            # student answers correctly
            ques = app.getQuestion_buisness('student1', 'unit1', 'class1', '1')
            self.assertEqual(200, ques.status_code, 'Failed getQuestion request')
            data3 = json.loads(ques.get_data(as_text=True))
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', 1, data3[0]['correct_ans'])
            self.assertEqual(205, res[1], 'Failed getQuestion request')
            # student answers incorrectly
            ques = app.getQuestion_buisness('student1', 'unit1', 'class1', '2')
            self.assertEqual(200, ques.status_code, 'Failed getQuestion request')
            data4 = json.loads(ques.get_data(as_text=True))
            res = app.submitQuestion_buisness('student1', 'unit1', 'class1', 2, (data4[0]['correct_ans']-1) % 4)
            self.assertNotEqual(205, res[1], 'Failed submitQuestion_buisness request')
            #check statistics
            stats = app.getAllLessonQuestionsB('class1', 'unit1')
            self.assertEqual(200, stats[1], 'Failed getAllLessonQuestionsB request')
            self.assertEqual(1, len(stats[0]))
            self.assertEqual(4, len(stats[0]['student1']), 'Failed getAllLessonQuestionsB request')
            self.assertEqual(data[0]['answer'+str(data[0]['correct_ans'])], stats[0]['student1'][0]['answer'+str(data[0]['correct_ans'])])
            self.assertEqual(data2[0]['answer' + str(data2[0]['correct_ans'])], stats[0]['student1'][1]['answer' + str(data2[0]['correct_ans'])])
            self.assertEqual(data3[0]['answer' + str(data3[0]['correct_ans'])], stats[0]['student1'][2]['answer' + str(data3[0]['correct_ans'])])
            self.assertEqual(data4[0]['answer' + str(data4[0]['correct_ans'])], stats[0]['student1'][3]['answer' + str(data4[0]['correct_ans'])])






if __name__ == '__main__':
    unittest.main()
