import unittest
import os
from pony.orm import db_session, Database, PrimaryKey, Required, Optional, Set, CacheIndexError, commit
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

    def test_makeClass_successful(self):
        # Add test data
        with db_session:

            User(name="John", password="123", type=1)
        # Test that makeClass returns "successful" and status code 200
        with db_session:
            response, status_code = app.makeClass("John", "Math")

            self.assertEqual(response, "successful")
            self.assertEqual(status_code, 200)

            # Assert that the class was added to the database
            cls = Cls.get(name="Math")
            self.assertIsNotNone(cls)
            self.assertEqual(cls.teacher.name, "John")

    def test_makeClass_same_name_fail(self):
        # Add test data
        with db_session:
            User(name="John", password="123", type=1)
        # Test that makeClass returns "successful" and status code 200
        with db_session:
            response, status_code = app.makeClass("John", "Math")

        # Try creating the same class again and assert that it raises an exception
        with self.assertRaises(Exception):
            app.makeClass("John", "Math")



    def test_makeClass_wrong_type(self):
        # Add test data
        with db_session:
            User(name="Alice", password="456", type=2)
        # Test that makeClass returns "failed wrong type" and status code 400
        with db_session:
            response, status_code = app.makeClass("Alice", "Science")

            self.assertEqual(response, "failed wrong type")
            self.assertEqual(status_code, 400)

            # Assert that no class was added to the database
            cls = Cls.get(name="Science")
            self.assertIsNone(cls)

    @patch('flaskProject.app.isLogin')
    def test_removeClass_not_teacher(self, mock_isLogin):
        # Set up the mock
        mock_isLogin.return_value = True
        # Add test data
        with db_session:
            teacher = User(name="John", password="123", type=2)
            Cls(name="Math", teacher=teacher)

        # Test that removeClass returns "successful" and status code 200
        with db_session:
            response, status_code = app.removeClass_buisness("John", "Math")
            self.assertEqual(response, "user John is not a teacher")
            self.assertEqual(status_code, 400)

    @patch('flaskProject.app.isLogin')
    def test_removeClass_successful(self, mock_isLogin):
        # Set up the mock
        mock_isLogin.return_value = True
        # Add test data
        with db_session:
            teacher = User(name="John", password="123", type=1)
            Cls(name="Math", teacher=teacher)

        # Test that removeClass returns "successful" and status code 200
        with db_session:
            response, status_code = app.removeClass_buisness("John", "Math")


            self.assertEqual(response, "successful")
            self.assertEqual(status_code, 200)

            # Assert that the class was removed from the database
            self.assertIsNone(Cls.get(name="Math"))


        # Test that attempting to remove a non-existent class returns "failed" and status code 400
        with db_session:
            response, status_code = app.removeClass_buisness("John", "Science")
            print(response)
            print(status_code)
            self.assertEqual(response, "Cls['Science']")
            self.assertEqual(status_code, 400)

        # Test that attempting to remove a class with a non-matching teacher returns "failed" and status code 400
        with db_session:
            teacher = User(name="Jane", password="456", type=1)
            Cls(name="Science", teacher=teacher)
            response, status_code = app.removeClass_buisness("John", "Science")


            self.assertEqual(response, "failed")
            self.assertEqual(status_code, 400)



    @patch('flaskProject.app.isLogin')
    def test_editClass_successful(self, mock_isLogin):
        # Set up the mock
        mock_isLogin.return_value = True
        # Add test data
        with db_session:
            teacher = User(name="John", password="123", type=1)
            c = Cls(name="Math", teacher=teacher)

        # Test that editClass returns "successful" and status code 200
        with db_session:
            response, status_code = app.editClass_buisness("John", "Math", "Mathematics")

            self.assertEqual(response, "successful")
            self.assertEqual(status_code, 200)

            # Assert that the class was renamed in the database
            self.assertIsNotNone(Cls.get(name="Mathematics"))
            self.assertIsNone(Cls.get(name="Math"))

        # Test that attempting to edit a non-existent class returns "failed" and status code 400
        with db_session:
            response, status_code = app.editClass_buisness("John", "Science", "Biology")
            self.assertEqual(response, "Cls['Science']")
            self.assertEqual(status_code, 400)

        # Test that attempting to edit a class with a non-matching teacher returns "failed" and status code 400
        with db_session:
            teacher = User(name="Jane", password="456", type=1)
            c = Cls(name="Science", teacher=teacher)
            response, status_code = app.editClass_buisness("John", "Science", "History")

            self.assertEqual(response, "failed")
            self.assertEqual(status_code, 400)

    @patch('flaskProject.app.isLogin')
    def test_editClass_not_teacher(self, mock_isLogin):
        # Set up the mock
        mock_isLogin.return_value = True
        # Add test data
        with db_session:
            teacher = User(name="John", password="123", type=2)
            c = Cls(name="Math", teacher=teacher)

        # Test that editClass returns "successful" and status code 200
        with db_session:
            response, status_code = app.editClass_buisness("John", "Math", "Mathematics")

            self.assertEqual(response, "user John is not a teacher")
            self.assertEqual(status_code, 400)
        with db_session:
            cls = Cls.get(name="Mathematics")
            self.assertIsNone(cls)

    @patch('flaskProject.app.isLogin')
    def test_editClass_userNotTeacher(self, mock_isLogin):
        # Test that attempting to edit a class with a user that is not logged in returns "user not logged in" and status code 400
        mock_isLogin.return_value = False
        response, status_code = app.editClass_buisness("John", "Math", "Mathematics")
        self.assertEqual(response, "user John is not a teacher")
        self.assertEqual(status_code, 400)



    def test_registerClass_for_tests(self):
        # Create a mock database session for testing
        with db_session:
            # Create necessary entities (User, Cls, Cls_User) for testing
            user = User(name='John', password='password', type=1)
            cls = Cls(name='Math', teacher=user)


        # Call the registerClass_for_tests function with the mocked URL

        result = app.registerClass_buisness("John", "Math")

        # Verify the result
        self.assertEqual(result, ('successful', 200))

    def test_approveStudentToClass(self):
        # Create a mock database session for testing
        with db_session:
            # Create necessary entities (User, Cls, Cls_User) for testing
            teacher = User(name='Mary', password='password', type=1)
            student = User(name='John', password='password', type=1)
            cls = Cls(name='Math', teacher=teacher)
            cls_user = app.Cls_User(cls=cls, user=student, approved=False)
            commit()  # Commit the entities to the mock database session

        # Call the approveStudentToClass function with the mocked URL

        result = app.approveStudentToClass_buisness("Mary", "John", "Math", True)

        # Verify the result
        expected_result = "successful"
        self.assertEqual(result, ('successful', 200))

    def test_makeClass_success(self):
        with db_session:
            user = User(name="John Doe", password="password", type=1)
            commit()
        # Call the makeClass function
        result = app.makeClass("John Doe", "English Class")

        # Verify the result
        self.assertEqual(result, ("successful", 200))

        # Verify that the class is not created in the database
        with db_session:
            cls = Cls.get(name="English Class")
            self.assertIsNotNone(cls)
            self.assertEqual(cls.teacher.name, "John Doe")

    def test_makeClass_not_teacher(self):
        with db_session:
            user = User(name="John Doe", password="password", type=2)
            commit()
        # Call the makeClass function
        result = app.makeClass("John Doe", "English Class")

        # Verify the result
        self.assertEqual(('failed wrong type', 400), result)

        # Verify that the class is created in the database
        with db_session:
            cls = Cls.get(name="English Class")
            self.assertIsNone(cls)


    @patch('flaskProject.app.makeClass')
    def test_openClass_exception(self, mock_makeClass):
        # Set up the mock
        mock_makeClass.side_effect = Exception("Error opening class")

        # Call the openClass function with mock arguments
        response = app.openClass_buisness("John Doe", "English")

        # Verify the result
        self.assertEqual(("User['John Doe']", 400), response)
        # Verify that the class is not created in the database
        with db_session:
            cls = Cls.get(name="English")
            self.assertIsNone(cls)


    @patch('flaskProject.app.Cls')
    @patch('flaskProject.app.User')
    def test_make_class_successful(self, mock_db_user, mock_db_cls):
        # setup
        mock_user = mock.MagicMock()
        mock_cls = mock.MagicMock()

        mock_user.type = 1

        mock_db_user.__getitem__.return_value = mock_user
        # mock_db_cls.__setitem__.return_value = "successful", 200

        # call the function
        response, status_code = app.makeClass('teacher1', 'class1')

        self.assertEqual(response, 'successful')
        self.assertEqual(status_code, 200)

    @patch('flaskProject.app.User')
    @patch('flaskProject.app.Cls')
    def test_openn_class_successful(self, mock_db_cls, mock_db_user):
        # setup
        mock_user = MagicMock()
        mock_user.type = 1
        mock_db_user.__getitem__.return_value = mock_user

        # call the function
        response, status_code = app.openClass_buisness('teacher1', 'class1')

        self.assertEqual(response, 'successful')
        self.assertEqual(status_code, 200)

    def test_getAllClassesNotIn_successful(self):
        with app.app.app_context():
            # Create teacher account and open a class
            app.register_buisness('teacher1', 'password', 1)
            app.login_buisness('teacher1', 'password')
            app.openClass_buisness('teacher1', 'class1')
            app.openClass_buisness('teacher1', 'class2')
            # Create student account and register to class
            app.register_buisness('student1', 'password', 2)
            app.login_buisness('student1', 'password')
            app.registerClass_buisness('student1', 'class1')
            app.approveStudentToClass_buisness('teacher1', 'student1', 'class1', 'True')
            # Check request
            res = app.getAllClassesNotIn_Buisness('student1')
            self.assertEqual(200, res.status_code, 'Request failed')
            self.assertEqual(1, len(res.json), 'Not 1 class not in')
            self.assertEqual('class2', res.json[0]['className'], 'Not class2')

    def test_getAllClassesNotIn_no_student_failure(self):
        with app.app.app_context():
            # Create teacher account and open a class
            app.register_buisness('teacher1', 'password', 1)
            app.login_buisness('teacher1', 'password')
            app.openClass_buisness('teacher1', 'class1')
            app.openClass_buisness('teacher1', 'class2')
            # Check request
            res = app.getAllClassesNotIn_Buisness('student1')
            self.assertEqual(2, len(res), 'Request failed')
            self.assertEqual(400, res[1], 'Request failed')

    def test_getAllClassesNotIn_student_in_all_classes_successful(self):
        with app.app.app_context():
            # Create teacher account and open a class
            app.register_buisness('teacher1', 'password', 1)
            app.login_buisness('teacher1', 'password')
            app.openClass_buisness('teacher1', 'class1')
            app.openClass_buisness('teacher1', 'class2')
            # Create student account and register to class
            app.register_buisness('student1', 'password', 2)
            app.login_buisness('student1', 'password')
            app.registerClass_buisness('student1', 'class1')
            app.approveStudentToClass_buisness('teacher1', 'student1', 'class1', 'True')
            app.registerClass_buisness('student1', 'class2')
            app.approveStudentToClass_buisness('teacher1', 'student1', 'class2', 'True')
            # Check request
            res = app.getAllClassesNotIn_Buisness('student1')
            self.assertEqual(200, res.status_code, 'Request failed')
            self.assertEqual(0, len(res.json), 'Not 1 class not in')

    def test_getUnapprovedStudents_successful(self):
        with app.app.app_context():
            # Create teacher account and open a class
            app.register_buisness('teacher1', 'password', 1)
            app.login_buisness('teacher1', 'password')
            app.openClass_buisness('teacher1', 'class1')
            app.openClass_buisness('teacher1', 'class2')
            # Create student account and register to class
            app.register_buisness('student1', 'password', 2)
            app.login_buisness('student1', 'password')
            app.registerClass_buisness('student1', 'class1')
            app.register_buisness('student2', 'password', 2)
            app.login_buisness('student2', 'password')
            app.registerClass_buisness('student2', 'class1')
            # Check request
            res = app.getUnapprovedStudents_buisness('teacher1')
            self.assertEqual(200, res.status_code, 'Request failed')
            self.assertEqual(2, len(res.json), 'Not 1 class not in')
            for item in res.json:
                if item['primary'] != 'student1' and item['primary'] != 'student2':
                    self.fail('students not in class')

    def test_getUnapprovedStudents_no_teacher_fail_successful(self):
        with app.app.app_context():
            # Check request
            res = app.getUnapprovedStudents_buisness('teacher1')
            self.assertEqual(200, res.status_code, 'Request failed')
            self.assertEqual(0, len(res.json), 'classes in list')

    def test_getUnapprovedStudents_no_unapproved_students_successful(self):
        with app.app.app_context():
            # Create teacher account and open a class
            app.register_buisness('teacher1', 'password', 1)
            app.login_buisness('teacher1', 'password')
            app.openClass_buisness('teacher1', 'class1')
            app.openClass_buisness('teacher1', 'class2')
            # Create student account and register to class
            app.register_buisness('student1', 'password', 2)
            app.login_buisness('student1', 'password')
            app.registerClass_buisness('student1', 'class1')
            app.approveStudentToClass_buisness('teacher1', 'student1', 'class1', 'True')
            app.register_buisness('student2', 'password', 2)
            app.login_buisness('student2', 'password')
            app.registerClass_buisness('student2', 'class1')
            app.approveStudentToClass_buisness('teacher1', 'student2', 'class1', 'True')
            # Check request
            res = app.getUnapprovedStudents_buisness('teacher1')
            self.assertEqual(200, res.status_code, 'Request failed')
            self.assertEqual(0, len(res.json), 'Not 1 class not in')

    def test_getClassesTeacher_successful(self):
        with app.app.app_context():
            # Create teacher account and open 2 classes
            app.register_buisness('teacher1', 'password', 1)
            app.login_buisness('teacher1', 'password')
            app.openClass_buisness('teacher1', 'class1')
            app.openClass_buisness('teacher1', 'class2')
            res = app.getClassesTeacher_buisness('teacher1')
            self.assertEqual(200, res.status_code, 'Get classes teacher failed')
            class_names = []
            for elem in res.json:
                class_names.append(elem['primary'])
            self.assertTrue('class1' in class_names and 'class2' in class_names, 'wrong classes returned')

    def test_getClassesTeacher_no_classes_successful(self):
        with app.app.app_context():
            # Create teacher account and open 2 classes
            app.register_buisness('teacher1', 'password', 1)
            app.login_buisness('teacher1', 'password')
            res = app.getClassesTeacher_buisness('teacher1')
            self.assertEqual(200, res.status_code, 'Get classes teacher failed')
            self.assertEqual(0, len(res.json), 'wrong classes returned')

    def test_getClassesTeacher_no_teacher_successful(self):
        with app.app.app_context():
            # Create teacher account and open 2 classes
            app.register_buisness('teacher1', 'password', 1)
            app.login_buisness('teacher1', 'password')
            res = app.getClassesTeacher_buisness('teacher2')
            self.assertEqual(200, res.status_code, 'Get classes teacher failed')
            self.assertEqual(0, len(res.json), 'wrong classes returned')

    def test_getClassesStudent_successful(self):
        with app.app.app_context():
            # Create teacher account and open 2 classes
            app.register_buisness('teacher1', 'password', 1)
            app.login_buisness('teacher1', 'password')
            app.openClass_buisness('teacher1', 'class1')
            app.openClass_buisness('teacher1', 'class2')
            app.openClass_buisness('teacher1', 'class3')
            # Create student account and register to class
            app.register_buisness('student1', 'password', 2)
            app.login_buisness('student1', 'password')
            app.registerClass_buisness('student1', 'class1')
            app.approveStudentToClass_buisness('teacher1', 'student1', 'class1', 'True')
            app.registerClass_buisness('student1', 'class2')
            app.approveStudentToClass_buisness('teacher1', 'student1', 'class2', 'True')
            # get classes for student
            res = app.getClassesStudent_buisness('student1')
            self.assertEqual(200, res.status_code, 'Get classes teacher failed')
            class_names = []
            for elem in res.json:
                class_names.append(elem['primary'])
            self.assertTrue('class1' in class_names and 'class2' in class_names, 'wrong classes returned')

    def test_getClassesStudent_no_classes_successful(self):
        with app.app.app_context():
            # Create teacher account and open 2 classes
            app.register_buisness('teacher1', 'password', 1)
            app.login_buisness('teacher1', 'password')
            # Create student account
            app.register_buisness('student1', 'password', 2)
            app.login_buisness('student1', 'password')
            res = app.getClassesStudent_buisness('student1')
            self.assertEqual(200, res.status_code, 'Get classes teacher failed')
            self.assertEqual(0, len(res.json), 'wrong classes returned')

    def test_getClassesStudent_no_student_successful(self):
        with app.app.app_context():
            # Create teacher account and open 2 classes
            app.register_buisness('teacher1', 'password', 1)
            app.login_buisness('teacher1', 'password')
            app.openClass_buisness('teacher1', 'class1')
            app.openClass_buisness('teacher1', 'class2')
            res = app.getClassesTeacher_buisness('student2')
            self.assertEqual(200, res.status_code, 'Get classes teacher failed')
            self.assertEqual(0, len(res.json), 'wrong classes returned')


if __name__ == '__main__':
    unittest.main()
