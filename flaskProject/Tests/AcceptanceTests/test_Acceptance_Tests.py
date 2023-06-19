import random
import unittest
from functools import reduce

from pony.orm import db_session, Database, PrimaryKey, Required, Optional, Set, CacheIndexError, commit
from flaskProject import app
from flaskProject.Tests.UnitTests import initiate_database
from flaskProject.app import User, DB, teacherCont, studentCont, Cls, Unit

import json


class AcceptanceTests(unittest.TestCase):
    DB = None

    @classmethod
    def setUpClass(cls):
        cls.DB = Database()
        DB = cls.DB
        initiate_database(DB)
        app.app.testing = True

    @classmethod
    def tearDownClass(cls):
        cls.DB.drop_all_tables()
        cls.DB.disconnect()
        app.app.testing = False

    def tearDown(self) -> None:
        with db_session:
            DB.execute('DELETE FROM ActiveUnit WHERE 1=1;')
            DB.execute('DELETE FROM Question WHERE 1=1;')
            DB.execute('DELETE FROM Unit WHERE 1=1;')
            DB.execute('DELETE FROM Cls_User WHERE 1=1;')
            DB.execute('DELETE FROM Cls WHERE 1=1;')
            DB.execute('DELETE FROM User WHERE 1=1;')

    @staticmethod
    def create_request(route, **kwargs):
        return '/' + route + '?' + reduce(lambda cur, nxt: cur + '&' + str(nxt) + '=' + str(kwargs[nxt]),
                                          list(kwargs.keys()),
                                          '')

    def test__acceptance__check_unit_deletion_works__success(self):
        # Register a teacher account and create a new class and a new unit, register a student account and register
        # to the class, approve the student and then delete the unit and check that the unit is no longer available
        # for solving.
        with app.app.test_client() as client:
            # Teacher registers and creates the class and unit
            res = client.get(self.create_request('register', username='teacher1', password='password', typ=1))
            self.assertEqual(res.status_code, 200, 'Register Teacher Failure')
            res = client.get(self.create_request('login', username='teacher1', password='password'))
            self.assertEqual(res.status_code, 200, 'Login Teacher Failure')
            res = client.get(self.create_request('openClass', teacher='teacher1', className='MathQuestions'))
            self.assertEqual(res.status_code, 200, 'Open Class Failure')
            res = client.get(self.create_request('openUnit', teacher='teacher1', desc='desc', unitName='unit1',
                                                 className='MathQuestions', template='intersection_linear_-10,0,1,6',
                                                 Qnum='4', maxTime='60', subDate='2023-07-01', first='true',
                                                 prev='new'))
            self.assertEqual(res.status_code, 200, 'Open Unit Failure')
            # Student registers to class and starts unit
            res = client.get(self.create_request('register', username='student1', password='password', typ=2))
            self.assertEqual(res.status_code, 200, 'Register Student Failure')
            res = client.get(self.create_request('login', username='student1', password='password'))
            self.assertEqual(res.status_code, 200, 'Login Student Failure')
            res = client.get(self.create_request('registerClass', student='student1', className='MathQuestions'))
            self.assertEqual(res.status_code, 200, 'Register to Class Failure')
            res = client.get(self.create_request('approveStudentToClass', teacher='teacher1', student='student1',
                                                 className='MathQuestions', approve='True'))
            self.assertEqual(res.status_code, 200, 'Approve Student Failure')
            res = client.get(self.create_request('deleteUnit', unitName='unit1', className='MathQuestions',
                                                 teacher='teacher1'))
            self.assertEqual(res.status_code, 200, 'Delete Unit Failure')
            # User starts unit after deletion
            res = client.get(self.create_request('startUnit', className='MathQuestions', unitName='unit1',
                                                 username='student1'))
            self.assertEqual(res.status_code, 400, 'Start Unit Failure')

    def test__acceptance__first_correct_second_incorrect_works_with_compound_units__success(self):
        # Register a teacher account and create a new class and a new compound unit (two units one after another),
        # register a student account and register them to the class, approve the student.
        # The student correctly solves the first unit, and incorrectly solves the second unit.
        with app.app.test_client() as client:
            # Teacher registers and creates the class and unit
            res = client.get(self.create_request('register', username='teacher1', password='password', typ=1))
            self.assertEqual(res.status_code, 200, 'Register Teacher Failure')
            res = client.get(self.create_request('login', username='teacher1', password='password'))
            self.assertEqual(res.status_code, 200, 'Login Teacher Failure')
            res = client.get(self.create_request('openClass', teacher='teacher1', className='MathQuestions'))
            self.assertEqual(res.status_code, 200, 'Open Class Failure')
            res = client.get(self.create_request('openUnit', teacher='teacher1', desc='desc', unitName='compundUnit',
                                                 className='MathQuestions',
                                                 template='intersection_quadratic_-10,10,-10,10,-10,10',
                                                 Qnum='1', maxTime='0', subDate='2023-07-01', first='true',
                                                 prev='new'))
            self.assertEqual(res.status_code, 200, 'Open Unit 1 Failure')
            res = client.get(self.create_request('openUnit', teacher='teacher1', desc='desc', unitName='compundUnitn',
                                                 className='MathQuestions',
                                                 template='minMaxPoints_quadratic_-10,10,-10,10,-10,10,-10,10',
                                                 Qnum='2', maxTime='0', subDate='2023-07-01', first='false',
                                                 prev='compundUnit'))
            self.assertEqual(res.status_code, 200, 'Open Unit 2 Failure')
            # Student registers to class and starts unit
            res = client.get(self.create_request('register', username='student1', password='password', typ=2))
            self.assertEqual(res.status_code, 200, 'Register Student Failure')
            res = client.get(self.create_request('login', username='student1', password='password'))
            self.assertEqual(res.status_code, 200, 'Login Student Failure')
            res = client.get(self.create_request('registerClass', student='student1', className='MathQuestions'))
            self.assertEqual(res.status_code, 200, 'Register to Class Failure')
            res = client.get(self.create_request('approveStudentToClass', teacher='teacher1', student='student1',
                                                 className='MathQuestions', approve='True'))
            self.assertEqual(res.status_code, 200, 'Approve Student Failure')
            # User starts unit and answer 1 question correctly
            res = client.get(self.create_request('startUnit', className='MathQuestions', unitName='compundUnit',
                                                 username='student1'))
            self.assertEqual(res.status_code, 200, 'Start Unit 1 Failure')
            res = client.get(self.create_request('getQuestion', username='student1', unitName='compundUnit',
                                                 className='MathQuestions', qnum='1'))
            self.assertEqual(res.status_code, 200, 'Get Question 1 Unit 1 Failure')
            correct_ans = json.loads(res.data)[0]['correct_ans']
            unit_1_preamble = json.loads(res.data)[0]['preamble']
            res = client.get(self.create_request('submitQuestion', username='student1', unitName='compundUnit',
                                                 className='MathQuestions', qnum='1', ans=str(correct_ans)))
            self.assertEqual(res.status_code, 206, 'Submit Question 1 Unit 1 Failure')
            # User starts the second unit and fails it
            res = client.get(self.create_request('startUnit', className='MathQuestions', unitName='compundUnitn',
                                                 username='student1'))
            self.assertEqual(res.status_code, 200, 'Start Unit 2 Failure')
            res = client.get(self.create_request('getQuestion', username='student1', unitName='compundUnitn',
                                                 className='MathQuestions', qnum='1'))
            self.assertEqual(res.status_code, 200, 'Get Question 1 Unit 2 Failure')
            self.assertNotEqual(unit_1_preamble, json.loads(res.data)[0]['preamble'], 'Same question type failure')
            correct_ans = json.loads(res.data)[0]['correct_ans']
            res = client.get(self.create_request('submitQuestion', username='student1', unitName='compundUnitn',
                                                 className='MathQuestions', qnum='1',
                                                 ans='-1'))
            self.assertEqual(res.status_code, 200 + int(correct_ans), 'Submit Question 1 Unit 2 Failure')

    def test__acceptance__start_unit_then_leave_and_come_back__success(self):
        # Register a teacher account and create a new class and a new unit,
        # register a student account and register them to the class, approve the student.
        # The student correctly solves the first question, then leaves and comes back. Check that he gets the
        # same question.
        with app.app.test_client() as client:
            # Teacher registers and creates the class and unit
            res = client.get(self.create_request('register', username='teacher1', password='password', typ=1))
            self.assertEqual(res.status_code, 200, 'Register Teacher Failure')
            res = client.get(self.create_request('login', username='teacher1', password='password'))
            self.assertEqual(res.status_code, 200, 'Login Teacher Failure')
            res = client.get(self.create_request('openClass', teacher='teacher1', className='MathQuestions'))
            self.assertEqual(res.status_code, 200, 'Open Class Failure')
            res = client.get(self.create_request('openUnit', teacher='teacher1', desc='desc', unitName='unit1',
                                                 className='MathQuestions',
                                                 template='intersection_quadratic_-10,10,-10,10,-10,10',
                                                 Qnum='3', maxTime='0', subDate='2023-07-01', first='true',
                                                 prev='new'))
            self.assertEqual(res.status_code, 200, 'Open Unit Failure')
            # Student registers to class and starts unit and answers 1 question correctly
            res = client.get(self.create_request('register', username='student1', password='password', typ=2))
            self.assertEqual(res.status_code, 200, 'Register Student Failure')
            res = client.get(self.create_request('login', username='student1', password='password'))
            self.assertEqual(res.status_code, 200, 'Login Student Failure')
            res = client.get(self.create_request('registerClass', student='student1', className='MathQuestions'))
            self.assertEqual(res.status_code, 200, 'Register to Class Failure')
            res = client.get(self.create_request('approveStudentToClass', teacher='teacher1', student='student1',
                                                 className='MathQuestions', approve='True'))
            self.assertEqual(res.status_code, 200, 'Approve Student Failure')
            res = client.get(self.create_request('startUnit', className='MathQuestions', unitName='unit1',
                                                 username='student1'))
            self.assertEqual(res.status_code, 200, 'Start Unit Failure')
            res = client.get(self.create_request('getQuestion', username='student1', unitName='unit1',
                                                 className='MathQuestions', qnum='1'))
            self.assertEqual(res.status_code, 200, 'Get Question 1 Failure')
            correct_ans = json.loads(res.data)[0]['correct_ans']
            res = client.get(self.create_request('submitQuestion', username='student1', unitName='unit1',
                                                 className='MathQuestions', qnum='1', ans=str(correct_ans)))
            self.assertEqual(res.status_code, 200, 'Submit Question 1 Failure')
            res = client.get(self.create_request('getUnitDetails', className='MathQuestions', unitName='unit1',
                                                 teacher='teacher1'))
            self.assertEqual(res.status_code, 200, 'Get Unit Details Failure')
            qnum = json.loads(res.data)['Qnum']
            unit_name = json.loads(res.data)['name']
            max_time = json.loads(res.data)['maxTime']
            sub_date = json.loads(res.data)['subDate']
            desc = json.loads(res.data)['desc']
            # User quits unit and comes back
            res = client.get(self.create_request('quitActiveUnit', username='student1', unitName='unit1',
                                                 className='MathQuestions'))
            self.assertEqual(res.status_code, 200, 'Quit Unit Failure')
            res = client.get(self.create_request('startUnit', className='MathQuestions', unitName='unit1',
                                                 username='student1'))
            self.assertEqual(res.status_code, 200, 'Start Unit Failure')
            res = client.get(self.create_request('getUnitDetails', className='MathQuestions', unitName='unit1',
                                                 teacher='teacher1'))
            self.assertEqual(res.status_code, 200, 'Get Unit Details Failure')
            self.assertEqual(json.loads(res.data)['Qnum'], qnum, 'Wrong Qnum')
            self.assertEqual(json.loads(res.data)['name'], unit_name, 'Wrong name')
            self.assertEqual(json.loads(res.data)['maxTime'], max_time, 'Wrong maxTime')
            self.assertEqual(json.loads(res.data)['subDate'], sub_date, 'Wrong subDate')
            self.assertEqual(json.loads(res.data)['desc'], desc, 'Wrong desc')

    def test__acceptance__multiple_students_start_unit_then_delete_unit__success(self):
        # Register a teacher account and create a new class and a new unit,
        # register 2 student accounts and register them to the class, approve the students.
        # The students correctly solve the first question, then the teacher deletes the unit and the students
        # can't answer anymore.
        with app.app.test_client() as client:
            # Teacher registers and creates the class and unit
            res = client.get(self.create_request('register', username='teacher1', password='password', typ=1))
            self.assertEqual(res.status_code, 200, 'Register Teacher Failure')
            res = client.get(self.create_request('login', username='teacher1', password='password'))
            self.assertEqual(res.status_code, 200, 'Login Teacher Failure')
            res = client.get(self.create_request('openClass', teacher='teacher1', className='MathQuestions'))
            self.assertEqual(res.status_code, 200, 'Open Class Failure')
            res = client.get(self.create_request('openUnit', teacher='teacher1', desc='desc', unitName='unit1',
                                                 className='MathQuestions',
                                                 template='intersection_quadratic_-10,10,-10,10,-10,10',
                                                 Qnum='3', maxTime='0', subDate='2023-07-01', first='true',
                                                 prev='new'))
            self.assertEqual(res.status_code, 200, 'Open Unit Failure')
            # Student 1 registers to class
            res = client.get(self.create_request('register', username='student1', password='password', typ=2))
            self.assertEqual(res.status_code, 200, 'Register Student 1 Failure')
            res = client.get(self.create_request('login', username='student1', password='password'))
            self.assertEqual(res.status_code, 200, 'Login Student 1 Failure')
            res = client.get(self.create_request('registerClass', student='student1', className='MathQuestions'))
            self.assertEqual(res.status_code, 200, 'Register 1 to Class Failure')
            res = client.get(self.create_request('approveStudentToClass', teacher='teacher1', student='student1',
                                                 className='MathQuestions', approve='True'))
            self.assertEqual(res.status_code, 200, 'Approve Student 1 Failure')
            # Student 2 registers to class
            res = client.get(self.create_request('register', username='student2', password='password', typ=2))
            self.assertEqual(res.status_code, 200, 'Register Student 2 Failure')
            res = client.get(self.create_request('login', username='student2', password='password'))
            self.assertEqual(res.status_code, 200, 'Login Student 2 Failure')
            res = client.get(self.create_request('registerClass', student='student2', className='MathQuestions'))
            self.assertEqual(res.status_code, 200, 'Register 2 to Class Failure')
            res = client.get(self.create_request('approveStudentToClass', teacher='teacher1', student='student2',
                                                 className='MathQuestions', approve='True'))
            self.assertEqual(res.status_code, 200, 'Approve Student 2 Failure')
            # Both students start unit
            res = client.get(self.create_request('startUnit', className='MathQuestions', unitName='unit1',
                                                 username='student1'))
            self.assertEqual(res.status_code, 200, 'Student 1 Start Unit Failure')
            res = client.get(self.create_request('startUnit', className='MathQuestions', unitName='unit1',
                                                 username='student2'))
            self.assertEqual(res.status_code, 200, 'Student 2 Start Unit Failure')
            # Both students get the first question
            res = client.get(self.create_request('getQuestion', username='student1', unitName='unit1',
                                                 className='MathQuestions', qnum='1'))
            self.assertEqual(res.status_code, 200, 'Student 1 Get Question 1 Failure')
            correct_ans_1 = json.loads(res.data)[0]['correct_ans']
            res = client.get(self.create_request('getQuestion', username='student2', unitName='unit1',
                                                 className='MathQuestions', qnum='1'))
            self.assertEqual(res.status_code, 200, 'Student 2 Get Question 1 Failure')
            correct_ans_2 = json.loads(res.data)[0]['correct_ans']
            # Teacher deletes unit
            res = client.get(self.create_request('deleteUnit', unitName='unit1', className='MathQuestions',
                                                 teacher='teacher1'))
            self.assertEqual(res.status_code, 200, 'Delete Unit Failure')
            # Students attempt to answer the question
            res = client.get(self.create_request('submitQuestion', username='student1', unitName='unit1',
                                                 className='MathQuestions', qnum='1', ans=str(correct_ans_1)))
            self.assertEqual(res.status_code, 400, 'Student 1 Submit Question 1 Success')
            res = client.get(self.create_request('submitQuestion', username='student2', unitName='unit1',
                                                 className='MathQuestions', qnum='1', ans=str(correct_ans_2)))
            self.assertEqual(res.status_code, 400, 'Student 2 Submit Question 1 Success')

    def test__acceptance__student_joins_class_then_it_gets_deleted__success(self):
        # Register a teacher account and create a new class,register a student account and register them to the class,
        # approve the students.
        # The teacher then deletes the class. Check that the students are no longer registered.
        with app.app.test_client() as client:
            # Teacher registers and creates the class
            res = client.get(self.create_request('register', username='teacher1', password='password', typ=1))
            self.assertEqual(res.status_code, 200, 'Register Teacher Failure')
            res = client.get(self.create_request('login', username='teacher1', password='password'))
            self.assertEqual(res.status_code, 200, 'Login Teacher Failure')
            res = client.get(self.create_request('openClass', teacher='teacher1', className='MathQuestions'))
            self.assertEqual(res.status_code, 200, 'Open Class Failure')
            # Student registers to class
            res = client.get(self.create_request('register', username='student1', password='password', typ=2))
            self.assertEqual(res.status_code, 200, 'Register Student Failure')
            res = client.get(self.create_request('login', username='student1', password='password'))
            self.assertEqual(res.status_code, 200, 'Login Student Failure')
            res = client.get(self.create_request('registerClass', student='student1', className='MathQuestions'))
            self.assertEqual(res.status_code, 200, 'Register to Class Failure')
            res = client.get(self.create_request('approveStudentToClass', teacher='teacher1', student='student1',
                                                 className='MathQuestions', approve='True'))
            self.assertEqual(res.status_code, 200, 'Approve Student Failure')
            # Teacher deletes the class
            res = client.get(self.create_request('removeClass', teacher='teacher1', className='MathQuestions'))
            self.assertEqual(res.status_code, 200, 'Remove Class Failure')
            res = client.get(self.create_request('getClassesStudent', student='student1'))
            self.assertEqual(res.status_code, 200, 'Get Classes Failure')
            self.assertEqual(len(json.loads(res.data)), 0, 'Class still appears for student.')

    def test__acceptance__student_answers_unit_then_teacher_edits_unit__success(self):
        # Register a teacher account and create a new class and unit,register a student account and register them to
        # the class, approve the students. The student completes the unit once. Then the teacher edits the unit and
        # we check that the unit updated.
        with app.app.test_client() as client:
            # Teacher registers and creates the class and unit
            res = client.get(self.create_request('register', username='teacher1', password='password', typ=1))
            self.assertEqual(res.status_code, 200, 'Register Teacher Failure')
            res = client.get(self.create_request('login', username='teacher1', password='password'))
            self.assertEqual(res.status_code, 200, 'Login Teacher Failure')
            res = client.get(self.create_request('openClass', teacher='teacher1', className='MathQuestions'))
            self.assertEqual(res.status_code, 200, 'Open Class Failure')
            res = client.get(self.create_request('openUnit', teacher='teacher1', desc='desc', unitName='unit1',
                                                 className='MathQuestions', template='intersection_linear_-10,0,1,6',
                                                 Qnum='1', maxTime='0', subDate='2023-07-01', first='true',
                                                 prev='new'))
            self.assertEqual(res.status_code, 200, 'Open Unit Failure')
            # Student registers to class and starts unit
            res = client.get(self.create_request('register', username='student1', password='password', typ=2))
            self.assertEqual(res.status_code, 200, 'Register Student Failure')
            res = client.get(self.create_request('login', username='student1', password='password'))
            self.assertEqual(res.status_code, 200, 'Login Student Failure')
            res = client.get(self.create_request('registerClass', student='student1', className='MathQuestions'))
            self.assertEqual(res.status_code, 200, 'Register to Class Failure')
            res = client.get(self.create_request('approveStudentToClass', teacher='teacher1', student='student1',
                                                 className='MathQuestions', approve='True'))
            self.assertEqual(res.status_code, 200, 'Approve Student Failure')
            # Student answers the unit
            res = client.get(self.create_request('startUnit', className='MathQuestions', unitName='unit1',
                                                 username='student1'))
            self.assertEqual(res.status_code, 200, 'Start Unit Failure')
            res = client.get(self.create_request('getQuestion', username='student1', unitName='unit1',
                                                 className='MathQuestions', qnum='1'))
            self.assertEqual(res.status_code, 200, 'Get Question 1 Failure')
            correct_ans = json.loads(res.data)[0]['correct_ans']
            res = client.get(self.create_request('submitQuestion', username='student1', unitName='unit1',
                                                 className='MathQuestions', qnum='1', ans=str(correct_ans)))
            self.assertEqual(res.status_code, 205, 'Submit Question 1 Failure')
            # Teacher edits unit
            new_qnum = '10'
            new_unit_name = 'unit1'
            new_max_time = '600'
            new_sub_date = '2023-08-01'
            new_desc = 'CoolDesc'
            res = client.get(self.create_request('editUnit', unitName='unit1', className='MathQuestions',
                                                 newUnitName=new_unit_name, newQnum=new_qnum, newMaxTime=new_max_time,
                                                 newSubDate=new_sub_date, newDesc=new_desc, teacher='teacher1'))
            self.assertEqual(res.status_code, 200, 'Edit Unit Failure')
            # Check for change
            res = client.get(self.create_request('getUnitDetails', className='MathQuestions', unitName='unit1',
                                                 teacher='teacher1'))
            self.assertEqual(res.status_code, 200, 'Get Unit Details Failure')
            self.assertEqual(json.loads(res.data)['Qnum'], new_qnum, 'Wrong Qnum')
            self.assertEqual(json.loads(res.data)['name'], new_unit_name, 'Wrong name')
            self.assertEqual(json.loads(res.data)['maxTime'], new_max_time, 'Wrong maxTime')
            self.assertEqual(json.loads(res.data)['subDate'], new_sub_date, 'Wrong subDate')
            self.assertEqual(json.loads(res.data)['desc'], new_desc, 'Wrong desc')

    def test__acceptance__multistudent_statistics(self):
        with app.app.app_context():
            # Create teacher account and open a class and a unit
            app.register_buisness('teacher1', 'password', 1)
            app.login_buisness('teacher1', 'password')
            app.openClass_buisness('teacher1', 'class1')
            app.teacherOpenUnit('unit1', 'teacher1', 'class1', 'intersection_linear_-10,0,1,6', '1', '60', '2023-07-01',
                                'true', 'new', 'desc')
            # Create student account and register to class
            student_num = random.randint(3,10)
            questions = {}
            for i in range(student_num):
                app.register_buisness('student'+str(i), 'password', 2)
                questions['student'+str(i)] = []
            for i in range(student_num):
                app.login_buisness('student'+str(i), 'password')
                app.registerClass_buisness('student'+str(i), 'class1')
                app.approveStudentToClass_buisness('teacher1', 'student'+str(i), 'class1', 'True')
            # Student starts unit
            for i in range(student_num):
                attempts = random.randint(1, 5)
                questions
                for j in range(attempts):
                    app.startUnit_buisness('class1', 'unit1', 'student'+str(i))
                    # student answers correctly
                    ques_num = random.randint(2,10)
                    for k in range(1, ques_num):
                        ques = app.getQuestion_buisness('student'+str(i), 'unit1', 'class1', k)
                        self.assertEqual(200, ques.status_code, 'Failed getQuestion request')
                        data = json.loads(ques.get_data(as_text=True))
                        res = app.submitQuestion_buisness('student'+str(i), 'unit1', 'class1', k, data[0]['correct_ans'])
                        self.assertEqual(205, res[1], 'Failed getQuestion request')
                        questions['student'+str(i)].append(data[0])

            #check statistics
            stats = app.getAllLessonQuestionsB('class1', 'unit1')
            self.assertEqual(200, stats[1], 'Failed getAllLessonQuestionsB request')
            self.assertEqual(len(questions), len(stats[0]))
            for i in range(len(stats[0])):
                self.assertEqual(len(questions['student'+str(i)]), len(stats[0]['student'+str(i)]), 'Failed getAllLessonQuestionsB request')
                for j in range(len(stats[0]['student'+str(i)])):
                     self.assertEqual(questions['student'+str(i)][j]['answer' + str(questions['student'+str(i)][j]['correct_ans'])],
                                      stats[0]['student'+str(i)][j]['answer' + str(questions['student'+str(i)][j]['correct_ans'])])

if __name__ == '__main__':
    unittest.main()
