import unittest
import os
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

    def test_valid_username(self):
        # Test that a valid username returns True
        result = app.checkValidUsername("new_user")
        self.assertTrue(result)

        # @db_session

    def test_invalid_username(self):
        # Test that an invalid username returns False
        app.makeUser("existing_user", "123", 1)
        result = app.checkValidUsername("existing_user")
        self.assertFalse(result)


    def test_valid_password(self):
        result = app.checkValidPassword("abc123")
        self.assertTrue(result)

    def test_invalid_password(self):
        result = app.checkValidPassword(" ")
        self.assertFalse(result)


    def test_valid_registration_teacher(self):
        with db_session:
            response, status_code = app.register_buisness("johndoe", "secret123", 1)
            # Assert that the user was added to the database
            self.assertIsNotNone(User.get(name="johndoe"))
        self.assertEqual(status_code, 200)

    def test_valid_registration_student(self):
        with db_session:
            response, status_code = app.register_buisness("johndoe", "secret123", 2)
            # Assert that the user was added to the database
            self.assertIsNotNone(User.get(name="johndoe"))
        self.assertEqual(status_code, 200)

    def test_invalid_username_teacher(self):
        # existing teacher with same username
        app.register_buisness("existing_teacher", "secret123", 1)
        response, status_code = app.register_buisness("existing_teacher", "secret123", 1)
        self.assertEqual(status_code, 400, f"Registration failed with response {response}")


    def test_invalid_username_student(self):
        # existing student with same username
        app.register_buisness("existing_student", "secret123", 2)
        response, status_code = app.register_buisness("existing_student", "secret123", 2)
        self.assertEqual(status_code, 400, f"Registration failed with response {response}")

    def test_invalid_password_teacher(self):
        # invalid password for teacher
        response, status_code = app.register_buisness("teacher_1", " ", 1)
        self.assertEqual(status_code, 400, f"Registration failed with response {response}")

    def test_invalid_password_student(self):
        # invalid password for student
        response, status_code = app.register_buisness("student_1", " ", 2)
        self.assertEqual(status_code, 400, f"Registration failed with response {response}")

    def test_login_details_correct(self):
        with db_session:
            app.register_buisness("teacher1", "secret123", 1)
            # Valid user and password
            self.assertTrue(app.checkUserPass('teacher1', 'secret123'))
            app.register_buisness("student1", "secret123", 2)
            # Valid user and password
            self.assertTrue(app.checkUserPass('student1', 'secret123'))

    def test_login_buisness_details_correct(self):
        with db_session:
            app.register_buisness("teacher1", "secret123", 1)
            # Valid user and password
            self.assertTrue(app.login_buisness('teacher1', 'secret123'))
            app.register_buisness("student1", "secret123", 2)
            # Valid user and password
            self.assertTrue(app.login_buisness('student1', 'secret123'))

    def test_login_password_incorrect(self):
        with db_session:
            app.register_buisness("teacher1", "secret123", 1)
            # Valid user and password
            self.assertFalse(app.checkUserPass('teacher1', 'secret12'))
            app.register_buisness("student1", "secret123", 2)
            # Valid user and password
            self.assertFalse(app.checkUserPass('student1', 'secre123'))

    def test_login_buisness_username_incorrect(self):
        with db_session:
            app.register_buisness("teacher1", "secret123", 1)
            # Valid user and password
            self.assertFalse(app.login_buisness('teacher', 'secret123'))
            app.register_buisness("student1", "secret123", 2)
            # Valid user and password
            self.assertFalse(app.login_buisness('student', 'secret123'))

    def test_login_username_incorrect(self):
        with db_session:
            app.register_buisness("teacher1", "secret123", 1)
            # Valid user and password
            self.assertFalse(app.checkUserPass('teacher', 'secret123'))
            app.register_buisness("student1", "secret123", 2)
            # Valid user and password
            self.assertFalse(app.checkUserPass('student', 'secret123'))



    @patch('flaskProject.app.activeControllers', {'student1': 'controller'})
    def logout_student_succesfully(self):
        # Set up initial state
        mock_studentCont = MagicMock(spec=studentCont)
        app.activeControllers['student1'] = mock_studentCont
        app.activeControllers['student2'] = mock_studentCont

        # Make request to logout_for_tests with student1 username
        response = app.logout_buisness("student1")

        self.assertEqual(response, 'student1 1')

        # Assert that student1 has been removed from activeControllers
        self.assertNotIn('student1', app.activeControllers)

    @patch('flaskProject.app.activeControllers', {'student1': 'controller'})
    def logout_student_non_exist_user(self):
        # Set up initial state
        mock_studentCont = MagicMock(spec=studentCont)
        app.activeControllers['student1'] = mock_studentCont
        # Make request to logout_for_tests with non-existent username
        response = app.logout_buisness("nonexistent")

        # Assert that the response is correct
        self.assertEqual('nonexistent 1', response)

        # Assert that activeControllers has not been modified
        self.assertEqual(len(app.activeControllers), 1)

    @patch('flaskProject.app.activeControllers', {'teacher1': 'controller'})
    def logout_teacher_succesfully(self, teachertCont=None):
        # Set up initial state
        mock_teacherCont = MagicMock(spec=teachertCont)
        app.activeControllers['teacher1'] = mock_teacherCont
        app.activeControllers['student2'] = mock_teacherCont

        # Make request to logout_for_tests with student1 username
        response = app.logout_buisness("teacher1")

        self.assertEqual(response, 'teacher1 1')

        # Assert that student1 has been removed from activeControllers
        self.assertNotIn('teacher1', app.activeControllers)

    @patch('flaskProject.app.activeControllers', {'teacher1': 'controller'})
    def logout_teacher_non_exist_user(self, teachertCont=None):
        # Set up initial state
        mock_teacherCont = MagicMock(spec=teachertCont)
        app.activeControllers['teacher1'] = mock_teacherCont
        # Make request to logout_for_tests with non-existent username
        response = app.logout_buisness("nonexistent")

        # Assert that the response is correct
        self.assertEqual(response, 'nonexistent 1')

        # Assert that activeControllers has not been modified
        self.assertEqual(len(app.activeControllers), 1)


if __name__ == '__main__':
    unittest.main()
