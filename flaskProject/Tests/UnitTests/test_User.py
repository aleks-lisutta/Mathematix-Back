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

        # @db_session

    def test_database_error(self):
        # Test that a database error returns false
        app.makeUser("existing_user", "123", 1)
        self.assertEqual(app.checkValidUsername("existing_user"), False)

    def test_valid_password(self):
        result = app.checkValidPassword("abc123")
        self.assertTrue(result)

    def test_invalid_password(self):
        result = app.checkValidPassword(" ")
        self.assertFalse(result)

    @patch('flaskProject.app.checkValidPassword')
    @patch('flaskProject.app.checkValidUsername')
    def test_valid_registration(self, mock_checkValidUsername=None, mock_checkValidPassword=None):
        mock_checkValidUsername.return_value = True
        mock_checkValidPassword.return_value = True
        with db_session:
            response, status_code = app.register_buisness("johndoe", "secret123", 1)
            # Assert that the user was added to the database
            self.assertIsNotNone(User.get(name="johndoe"))
        self.assertEqual(status_code, 200)

    def test_invalid_username_2(self):
        # existing teacher with same username
        app.makeUser("existing_teacher", "123", 1)
        response, status_code = app.register_buisness("existing_teacher", "secret123", 1)
        self.assertEqual(status_code, 400, f"Registration failed with response {response}")
        # existing student with same username
        app.makeUser("existing_student", "123", 2)
        response, status_code = app.register_buisness("existing_student", "secret123", 2)
        self.assertEqual(status_code, 400, f"Registration failed with response {response}")

    def test_invalid_password_2(self):
        # invalid password for teacher
        response, status_code = app.register_buisness("teacher_1", " ", 1)
        self.assertEqual(status_code, 400, f"Registration failed with response {response}")
        # invalid password for student
        response, status_code = app.register_buisness("student_1", " ", 2)
        self.assertEqual(status_code, 400, f"Registration failed with response {response}")

    @mock.patch('flaskProject.app.User')
    def test_checkUserPass(self, mock_db):
        # Mocking the User object
        mock_user = mock.MagicMock()
        mock_user.password = 'pass1'
        mock_db.__getitem__.return_value = mock_user

        # Valid user and password
        self.assertTrue(app.checkUserPass('user1', 'pass1'))

        # Valid user, invalid password
        self.assertFalse(app.checkUserPass('user1', 'wrongpass'))

        # Invalid user
        self.assertFalse(app.checkUserPass('nonexistentuser', 'anypassword'))

        # Empty username
        self.assertFalse(app.checkUserPass('', 'anypassword'))

        # Empty password
        self.assertFalse(app.checkUserPass('user1', ''))

        # Null username
        self.assertFalse(app.checkUserPass(None, 'anypassword'))

        # Null password
        self.assertFalse(app.checkUserPass('user1', None))

    @patch('flaskProject.app.checkUserPass')
    @patch('flaskProject.app.loadController')
    def login_teacher_correct_username(self, mock_loadController, mock_checkUserPass):
        # login with correct teacher name and password
        # setup
        mock_checkUserPass.return_value = True
        mock_teacherCont = MagicMock(spec=teacherCont)
        app.activeControllers['teacher1'] = mock_teacherCont

        # call the function
        response = app.login_buisness("teacher1", "password")

        # assert that the correct objects were queried and created
        mock_checkUserPass.assert_called_once_with('teacher1', 'password')
        mock_loadController.assert_called_once_with('teacher1')

        # assert that the correct response and status code were returned
        self.assertEqual('1 teacher1', response)

    @patch('flaskProject.app.checkUserPass')
    @patch('flaskProject.app.loadController')
    def login_teacher_incorrect_username(self, mock_loadController, mock_checkUserPass):
        # setup
        mock_checkUserPass.side_effect = lambda u, p: u == 'teacher1' and p == 'password'
        mock_teacherCont = MagicMock(spec=teacherCont)
        app.activeControllers['teacher1'] = mock_teacherCont

        # call the function with incorrect username
        response = app.login_buisness("incorrect", "password")

        # assert that the correct objects were queried and created
        mock_checkUserPass.assert_called_once_with('incorrect', 'password')
        mock_loadController.assert_not_called()

        # assert that the correct response and status code were returned
        self.assertEqual(('invalid username or password', 400), response)

    @patch('flaskProject.app.checkUserPass')
    @patch('flaskProject.app.loadController')
    def login_teacher_incorrect_password(self, mock_loadController, mock_checkUserPass):
        # setup
        mock_checkUserPass.side_effect = lambda u, p: u == 'teacher1' and p == 'password'
        mock_teacherCont = MagicMock(spec=teacherCont)
        app.activeControllers['teacher1'] = mock_teacherCont

        # call the function with incorrect password
        response = app.login_buisness("teacher1", "incorrect")

        # assert that the correct objects were queried and created
        mock_checkUserPass.assert_called_once_with('teacher1', 'incorrect')
        mock_loadController.assert_not_called()

        # assert that the correct response and status code were returned
        self.assertEqual(('invalid username or password', 400), response)

    @patch('flaskProject.app.checkUserPass')
    @patch('flaskProject.app.loadController')
    def login_student_succesfully(self, mock_loadController, mock_checkUserPass):
        # setup
        mock_checkUserPass.return_value = True
        mock_studentCont = MagicMock(spec=studentCont)
        app.activeControllers['student1'] = mock_studentCont

        # call the function
        response = app.login_buisness("student1", "password")

        # assert that the correct objects were queried and created
        mock_checkUserPass.assert_called_once_with('student1', 'password')
        mock_loadController.assert_called_once_with('student1')

        # assert that the correct response and status code were returned
        self.assertEqual('2 student1', response)

    @patch('flaskProject.app.checkUserPass')
    @patch('flaskProject.app.loadController')
    def login_student_incorrect_password(self, mock_loadController, mock_checkUserPass):
        # setup
        mock_checkUserPass.side_effect = lambda u, p: u == 'student1' and p == 'password'
        mock_studentCont = MagicMock(spec=studentCont)
        app.activeControllers['student1'] = mock_studentCont

        # call the function with incorrect password
        response = app.login_buisness("teacher1", "incorrect")

        # assert that the correct objects were queried and created
        mock_checkUserPass.assert_called_once_with('teacher1', 'incorrect')
        mock_loadController.assert_not_called()

        # assert that the correct response and status code were returned
        self.assertEqual(('invalid username or password', 400), response)

    @patch('flaskProject.app.checkUserPass')
    @patch('flaskProject.app.loadController')
    def login_student_incorrect_username(self, mock_loadController, mock_checkUserPass):
        # setup
        mock_checkUserPass.side_effect = lambda u, p: u == 'student1' and p == 'password'
        mock_studentCont = MagicMock(spec=studentCont)
        app.activeControllers['student1'] = mock_studentCont

        # call the function with incorrect username
        response = app.login_buisness("incorrect", "password")

        # assert that the correct objects were queried and created
        mock_checkUserPass.assert_called_once_with('incorrect', 'password')
        mock_loadController.assert_not_called()

        # assert that the correct response and status code were returned
        self.assertEqual(('invalid username or password', 400), response)

    @patch('flaskProject.app.checkUserPass')
    @patch('flaskProject.app.loadController')
    def login_student_incorrect_password(self, mock_loadController, mock_checkUserPass):
        # setup
        mock_checkUserPass.side_effect = lambda u, p: u == 'student1' and p == 'password'
        mock_studentCont = MagicMock(spec=studentCont)
        app.activeControllers['student1'] = mock_studentCont

        # call the function with incorrect password
        response = app.login_buisness("student1", "wrongpassword")

        # assert that the correct objects were queried and created
        mock_checkUserPass.assert_called_once_with('student1', 'wrongpassword')
        mock_loadController.assert_not_called()

        # assert that the correct response and status code were returned
        self.assertEqual(('invalid username or password', 400), response)

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
