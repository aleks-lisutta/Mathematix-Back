import unittest
import os
from pony.orm import db_session, Database, PrimaryKey, Required, Optional, Set, CacheIndexError, commit
from flaskProject import app
from flaskProject.app import User, DB, teacherCont, studentCont, Cls, Unit
from unittest import mock
from unittest.mock import patch, MagicMock

TEACHER = 1
STUDENT = 2


class MyTestCase(unittest.TestCase):
    def setUp(self):
        DB = Database()
        DB.bind(provider='sqlite', filename='dbtest.sqlite', create_db=True)

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

        # Mock the User class
        class UserMock(MagicMock):
            name = "test_user"
            password = "test_password"
            type = 1
            teaching = set()
            inClass = set()
            activeUnits = set()

        # Create some initial data for testing
        # self.teacher1 = app.makeUser("teacher1", "123", 1)  # teacher=1
        # self.student1 = app.makeUser("student1", "123", 2)
        # self.class1 = app.makeClass("teacher1", "class1")
        # self.unit1 = app.teacherOpenUnit("unit1", "teacher1", "class1", "intersection_linear_5,5,5,5", 3, 0, "Tue Apr 04 2023 17:42:48 GMT 0300 (Israel Daylight Time)", True, None, "desc1")
        # self.active_unit1 = app.addQuestions("class1", "unit1", "student1")

    def tearDown(self):
        DB.disconnect()
        # Remove the test database file after testing
        os.remove('dbtest.sqlite')

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

            # Test that adding another class with the same name fails
            with self.assertRaises(CacheIndexError):
                Cls(name="Math", teacher=User.get(name="John"))
                db_session.commit()

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
            url = "http://example.com?username=John&className=Math"
            response, status_code = app.removeClass_for_tests(url)
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
            url = "http://example.com?username=John&className=Math"
            response, status_code = app.removeClass_for_tests(url)

            self.assertEqual(response, "successful")
            self.assertEqual(status_code, 200)

            # Assert that the class was removed from the database
            self.assertIsNone(Cls.get(name="Math"))

        # Test that attempting to remove a non-existent class returns "failed" and status code 400
        with db_session:
            url = "http://example.com?username=John&className=Science"
            response, status_code = app.removeClass_for_tests(url)
            print(response)
            print(status_code)
            self.assertEqual(response, "Cls['Science']")
            self.assertEqual(status_code, 400)

        # Test that attempting to remove a class with a non-matching teacher returns "failed" and status code 400
        with db_session:
            teacher = User(name="Jane", password="456", type=1)
            Cls(name="Science", teacher=teacher)

            url = "http://example.com?username=John&className=Science"
            response, status_code = app.removeClass_for_tests(url)

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
            url = "http://example.com?username=John&className=Math&newClassName=Mathematics"
            response, status_code = app.editClass_for_tests(url)

            self.assertEqual(response, "successful")
            self.assertEqual(status_code, 200)

            # Assert that the class was renamed in the database
            self.assertIsNotNone(Cls.get(name="Mathematics"))
            self.assertIsNone(Cls.get(name="Math"))

        # Test that attempting to edit a non-existent class returns "failed" and status code 400
        with db_session:
            url = "http://example.com?username=John&className=Science&newClassName=Biology"
            response, status_code = app.editClass_for_tests(url)

            self.assertEqual(response, "Cls['Science']")
            self.assertEqual(status_code, 400)

        # Test that attempting to edit a class with a non-matching teacher returns "failed" and status code 400
        with db_session:
            teacher = User(name="Jane", password="456", type=1)
            c = Cls(name="Science", teacher=teacher)

            url = "http://example.com?username=John&className=Science&newClassName=History"
            response, status_code = app.editClass_for_tests(url)

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
            url = "http://example.com?username=John&className=Math&newClassName=Mathematics"
            response, status_code = app.editClass_for_tests(url)

            self.assertEqual(response, "user John is not a teacher")
            self.assertEqual(status_code, 400)

    @patch('flaskProject.app.isLogin')
    def test_editClass_userNotLoggedIn(self, mock_isLogin):
        # Test that attempting to edit a class with a user that is not logged in returns "user not logged in" and status code 400
        mock_isLogin.return_value = False
        url = "http://example.com?username=John&className=Math&newClassName=Mathematics"
        response, status_code = app.editClass_for_tests(url)
        self.assertEqual(response, "user John not logged in.")
        self.assertEqual(status_code, 400)

    @patch('flaskProject.app.isLogin')
    def test_editUnit_userNotLoggedIn(self, mock_isLogin):
        # Set up the mock
        mock_isLogin.return_value = False
        mock_isLogin.side_effect = lambda x: False

        # Add test data
        with db_session:
            teacher = User(name="John", password="123", type=1)
            c = Cls(name="Math", teacher=teacher)
            u = Unit(
                name="Math",
                cls=c,
                desc="Basic algebra",
                template="template1",
                Qnum="10",
                maxTime="60",
                subDate="2023-05-31",
                order=1,
                # next=None
            )

            # Check that the unit was not edited
            with db_session:
                unit = Unit.get(name="Math")
                self.assertEqual(unit.desc, "Basic algebra")
                self.assertEqual(unit.template, "template1")
                self.assertEqual(unit.Qnum, "10")
                self.assertEqual(unit.maxTime, "60")
                self.assertEqual(unit.subDate, "2023-05-31")
                self.assertEqual(unit.order, 1)
                self.assertEqual(unit.next, '')

        # Test that editUnit returns "user <teacherName> not logged in." and status code 400
        url = "http://example.com?teacherName=John&unitName=Math&className=Math&Qnum=10&maxTime=60&subDate=2023-05-31&newUnitName=Calculus&newDesc=Advanced calculus"
        response, status_code = app.editUnit_for_tests(url)
        self.assertEqual(response, "user John not logged in.")
        self.assertEqual(status_code, 400)

    @patch('flaskProject.app.isLogin')
    def test_editUnit_non_existent_unit(self, mock_isLogin):
        # Set up the mock
        mock_isLogin.return_value = True

        # Add test data
        with db_session:
            teacher = User(name="John", password="123", type=1)
            c = Cls(name="Math", teacher=teacher)
            u = Unit(
                name="Mathx",
                cls=c,
                desc="Basic algebra",
                template="template1",
                Qnum="10",
                maxTime="60",
                subDate="2023-05-31",
                order=1,
                # next=None
            )

        # Test that attempting to edit a non-existent unit returns an error message and status code 400
        with db_session:
            url = "http://example.com?teacherName=John&unitName=Math&className=Math&Qnum=10&maxTime=60&subDate=2023-05-31&newUnitName=Calculus&newDesc=Advanced calculus"
            response, status_code = app.editUnit_for_tests(url)

            self.assertEqual(response, "Unit['Math',Cls['Math']] not found")
            self.assertEqual(status_code, 400)

    @patch('flaskProject.app.isLogin')
    def test_editUnit_successful(self, mock_isLogin):
        # Set up the mock
        mock_isLogin.return_value = True

        # Add test data
        with db_session:
            teacher = User(name="John", password="123", type=1)
            c = Cls(name="Math", teacher=teacher)
            u = Unit(
                name="Math",
                cls=c,
                desc="Basic algebra",
                template="template1",
                Qnum="10",
                maxTime="60",
                subDate="2023-05-31",
                order=1,
                # next=None
            )

            # Test that editUnit returns "successful" and status code 200
            url = "http://example.com?teacherName=John&unitName=Math&className=Math&Qnum=10&maxTime=60&subDate=2023-05-31&newUnitName=Calculus&newDesc=Advanced calculus"
            response, status_code = app.editUnit_for_tests(url)
            self.assertEqual(response, {"message": "successful"})
            self.assertEqual(status_code, 200)

            # Assert that the unit was renamed and updated in the database
            self.assertIsNotNone(Unit.get(name="Calculus", cls=c))

            self.assertIsNone(Unit.get(name="Algebra", cls=c))

            unit = Unit.get(name="Calculus", cls=c)
            self.assertEqual(unit.desc, "Advanced calculus")
            self.assertEqual(unit.Qnum, "10")
            self.assertEqual(unit.maxTime, "60")
            self.assertEqual(unit.subDate, "2023-05-31")

        # success test
        with db_session:
            teacher = User(name="Jane", password="456", type=1)
            c = Cls(name="Science", teacher=teacher)
            u = Unit(
                name="Chemistry",
                cls=c,
                desc="Basic chemistry",
                template="template1",
                Qnum="15",
                maxTime="90",
                subDate="2023-06-30",
                order=1,
                # next=None
            )

            url = "http://example.com?teacherName=John&unitName=Chemistry&subDate=2023-05-31&Qnum=10&maxTime=60&className=Science&newUnitName=Biology&newDesc=Basic biology"
            response, status_code = app.editUnit_for_tests(url)

            self.assertEqual(response, {"message": "successful"})
            self.assertEqual(status_code, 200)

    @patch('flaskProject.app.isLogin')
    def test_editUnit_not_teacher(self, mock_isLogin):
        # Set up the mock
        mock_isLogin.return_value = True

        # Add test data
        with db_session:
            teacher = User(name="John", password="123", type=2)
            c = Cls(name="Math", teacher=teacher)
            u = Unit(
                name="Math",
                cls=c,
                desc="Basic algebra",
                template="template1",
                Qnum="10",
                maxTime="60",
                subDate="2023-05-31",
                order=1,
                # next=None
            )

            # Test that editUnit returns "successful" and status code 200
            url = "http://example.com?teacherName=John&unitName=Math&className=Math&Qnum=10&maxTime=60&subDate=2023-05-31&newUnitName=Calculus&newDesc=Advanced calculus"
            response, status_code = app.editUnit_for_tests(url)
            self.assertEqual(response, "user John is not a teacher")
            self.assertEqual(status_code, 400)

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

    def test_valid_registration(self):
        response = app.register_for_test('/register?username=johndoe&password=secret123&typ=1')
        self.assertEqual(response.status_code, 200, f"Registration failed with response {response}")

    def test_invalid_username(self):
        # existing teacher with same username
        app.makeUser("existing_teacher", "123", 1)
        response = app.register_for_test('/register?username=existing_teacher&password=secret123&typ=1')
        self.assertEqual(response.status_code, 400, f"Registration failed with response {response}")
        # existing student with same username
        app.makeUser("existing_student", "123", 2)
        response = app.register_for_test('/register?username=existing_student&password=secret123&typ=2')
        self.assertEqual(response.status_code, 400, f"Registration failed with response {response}")

    def test_invalid_password(self):
        # invalid password for teacher
        response = app.register_for_test('/register?username=teacher_1&password= &typ=1')
        self.assertEqual(response.status_code, 400, f"Registration failed with response {response}")
        # invalid password for student
        response = app.register_for_test('/register?username=student_1&password=7 &typ=2')
        self.assertEqual(response.status_code, 400, f"Registration failed with response {response}")

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
    def test_openClass_success(self, mock_makeClass):
        # Set up the mock
        mock_makeClass.return_value = "Class opened successfully"

        # Call the openClass function with mock arguments
        result = app.openClass_for_tests('http://example.com/openClass?teacher=John%20Doe&className=English%20Class')

        # Verify the result
        self.assertEqual(result, "Class opened successfully")

    @patch('flaskProject.app.makeClass')
    def test_openClass_exception(self, mock_makeClass):
        # Set up the mock
        mock_makeClass.side_effect = Exception("Error opening class")

        # Call the openClass function with mock arguments
        response = app.openClass_for_tests('http://example.com/openClass?teacher=John%20Doe&className=English%20Class')

        # Verify the result
        self.assertEqual(('Error opening class', 400), response)
        # Verify that the class is not created in the database
        with db_session:
            cls = Cls.get(name="English")
            self.assertIsNone(cls)

    @patch('flaskProject.app.checkUserPass')
    @patch('flaskProject.app.loadController')
    def test_login_for_tests_teacher_correct_username(self, mock_loadController, mock_checkUserPass):
        # login with correct teacher name and password
        # setup
        mock_checkUserPass.return_value = True
        mock_teacherCont = MagicMock(spec=teacherCont)
        app.activeControllers['teacher1'] = mock_teacherCont

        # call the function
        response = app.login_for_tests('http://localhost:5000/login?username=teacher1&password=password')

        # assert that the correct objects were queried and created
        mock_checkUserPass.assert_called_once_with('teacher1', 'password')
        mock_loadController.assert_called_once_with('teacher1')

        # assert that the correct response and status code were returned
        self.assertEqual('1 teacher1', response)

    @patch('flaskProject.app.checkUserPass')
    @patch('flaskProject.app.loadController')
    def test_login_for_tests_teacher_incorrect_username(self, mock_loadController, mock_checkUserPass):
        # setup
        mock_checkUserPass.side_effect = lambda u, p: u == 'teacher1' and p == 'password'
        mock_teacherCont = MagicMock(spec=teacherCont)
        app.activeControllers['teacher1'] = mock_teacherCont

        # call the function with incorrect username
        response = app.login_for_tests('http://localhost:5000/login?username=incorrect&password=password')

        # assert that the correct objects were queried and created
        mock_checkUserPass.assert_called_once_with('incorrect', 'password')
        mock_loadController.assert_not_called()

        # assert that the correct response and status code were returned
        self.assertEqual(('invalid username or password', 400), response)

    @patch('flaskProject.app.checkUserPass')
    @patch('flaskProject.app.loadController')
    def test_login_for_tests_teacher_incorrect_password(self, mock_loadController, mock_checkUserPass):
        # setup
        mock_checkUserPass.side_effect = lambda u, p: u == 'teacher1' and p == 'password'
        mock_teacherCont = MagicMock(spec=teacherCont)
        app.activeControllers['teacher1'] = mock_teacherCont

        # call the function with incorrect password
        response = app.login_for_tests('http://localhost:5000/login?username=teacher1&password=incorrect')

        # assert that the correct objects were queried and created
        mock_checkUserPass.assert_called_once_with('teacher1', 'incorrect')
        mock_loadController.assert_not_called()

        # assert that the correct response and status code were returned
        self.assertEqual(('invalid username or password', 400), response)

    @patch('flaskProject.app.checkUserPass')
    @patch('flaskProject.app.loadController')
    def test_login_for_tests_student_succesfully(self, mock_loadController, mock_checkUserPass):
        # setup
        mock_checkUserPass.return_value = True
        mock_studentCont = MagicMock(spec=studentCont)
        app.activeControllers['student1'] = mock_studentCont

        # call the function
        response = app.login_for_tests('http://localhost:5000/login?username=student1&password=password')

        # assert that the correct objects were queried and created
        mock_checkUserPass.assert_called_once_with('student1', 'password')
        mock_loadController.assert_called_once_with('student1')

        # assert that the correct response and status code were returned
        self.assertEqual('2 student1', response)

    @patch('flaskProject.app.checkUserPass')
    @patch('flaskProject.app.loadController')
    def test_login_for_tests_student_incorrect_password(self, mock_loadController, mock_checkUserPass):
        # setup
        mock_checkUserPass.side_effect = lambda u, p: u == 'student1' and p == 'password'
        mock_studentCont = MagicMock(spec=studentCont)
        app.activeControllers['student1'] = mock_studentCont

        # call the function with incorrect password
        response = app.login_for_tests('http://localhost:5000/login?username=teacher1&password=incorrect')

        # assert that the correct objects were queried and created
        mock_checkUserPass.assert_called_once_with('teacher1', 'incorrect')
        mock_loadController.assert_not_called()

        # assert that the correct response and status code were returned
        self.assertEqual(('invalid username or password', 400), response)

    @patch('flaskProject.app.checkUserPass')
    @patch('flaskProject.app.loadController')
    def test_login_for_tests_student_incorrect_username(self, mock_loadController, mock_checkUserPass):
        # setup
        mock_checkUserPass.side_effect = lambda u, p: u == 'student1' and p == 'password'
        mock_studentCont = MagicMock(spec=studentCont)
        app.activeControllers['student1'] = mock_studentCont

        # call the function with incorrect username
        response = app.login_for_tests('http://localhost:5000/login?username=incorrect&password=password')

        # assert that the correct objects were queried and created
        mock_checkUserPass.assert_called_once_with('incorrect', 'password')
        mock_loadController.assert_not_called()

        # assert that the correct response and status code were returned
        self.assertEqual(('invalid username or password', 400), response)

    @patch('flaskProject.app.checkUserPass')
    @patch('flaskProject.app.loadController')
    def test_login_for_tests_student_incorrect_password(self, mock_loadController, mock_checkUserPass):
        # setup
        mock_checkUserPass.side_effect = lambda u, p: u == 'student1' and p == 'password'
        mock_studentCont = MagicMock(spec=studentCont)
        app.activeControllers['student1'] = mock_studentCont

        # call the function with incorrect password
        response = app.login_for_tests('http://localhost:5000/login?username=student1&password=wrongpassword')

        # assert that the correct objects were queried and created
        mock_checkUserPass.assert_called_once_with('student1', 'wrongpassword')
        mock_loadController.assert_not_called()

        # assert that the correct response and status code were returned
        self.assertEqual(('invalid username or password', 400), response)

    @patch('flaskProject.app.activeControllers', {'student1': 'controller'})
    def test_logout_student_succesfully(self):
        # Set up initial state
        mock_studentCont = MagicMock(spec=studentCont)
        app.activeControllers['student1'] = mock_studentCont
        app.activeControllers['student2'] = mock_studentCont

        # Make request to logout_for_tests with student1 username
        response = app.logout_for_tests('/logout?username=student1')

        self.assertEqual(response, 'student1 1')

        # Assert that student1 has been removed from activeControllers
        self.assertNotIn('student1', app.activeControllers)

    @patch('flaskProject.app.activeControllers', {'student1': 'controller'})
    def test_logout_student_non_exist_user(self):
        # Set up initial state
        mock_studentCont = MagicMock(spec=studentCont)
        app.activeControllers['student1'] = mock_studentCont
        # Make request to logout_for_tests with non-existent username
        response = app.logout_for_tests('/logout?username=nonexistent')

        # Assert that the response is correct
        self.assertEqual('nonexistent 1', response)

        # Assert that activeControllers has not been modified
        self.assertEqual(len(app.activeControllers), 1)

    @patch('flaskProject.app.activeControllers', {'teacher1': 'controller'})
    def test_logout_teacher_succesfully(self, teachertCont=None):
        # Set up initial state
        mock_teacherCont = MagicMock(spec=teachertCont)
        app.activeControllers['teacher1'] = mock_teacherCont
        app.activeControllers['student2'] = mock_teacherCont

        # Make request to logout_for_tests with student1 username
        response = app.logout_for_tests('/logout?username=teacher1')

        self.assertEqual(response, 'teacher1 1')

        # Assert that student1 has been removed from activeControllers
        self.assertNotIn('teacher1', app.activeControllers)

    @patch('flaskProject.app.activeControllers', {'teacher1': 'controller'})
    def test_logout_teacher_non_exist_user(self, teachertCont=None):
        # Set up initial state
        mock_teacherCont = MagicMock(spec=teachertCont)
        app.activeControllers['teacher1'] = mock_teacherCont
        # Make request to logout_for_tests with non-existent username
        response = app.logout_for_tests('/logout?username=nonexistent')

        # Assert that the response is correct
        self.assertEqual(response, 'nonexistent 1')

        # Assert that activeControllers has not been modified
        self.assertEqual(len(app.activeControllers), 1)

    @patch('flaskProject.app.isLogin')
    def test_removeUnit_successful(self, mock_isLogin):
        # Set up the mock
        mock_isLogin.return_value = True

        # Add test data
        with db_session:
            teacher = User(name="John", password="123", type=1)
            c = Cls(name="Math", teacher=teacher)
            u = Unit(
                name="Calculus",
                cls=c,
                desc="Advanced calculus",
                template="template1",
                Qnum="10",
                maxTime="60",
                subDate="2023-05-31",
                order=1,
                # next=None
            )

            # Test that removeUnit_for_test returns "successful" and status code 200
            url = "http://example.com?teacherName=John&unitName=Calculus&className=Math"
            response, status_code = app.removeUnit_for_test(url)
            self.assertEqual(response, "successful")
            self.assertEqual(status_code, 200)

            # Assert that the unit was removed from the database
            self.assertIsNone(Unit.get(name="Calculus", cls=c))

    @patch('flaskProject.app.isLogin')
    def test_removeUnit_failed(self, mock_isLogin):
        # Set up the mock
        mock_isLogin.return_value = True

        # Add test data
        with db_session:
            teacher = User(name="John", password="123", type=1)
            c = Cls(name="Math", teacher=teacher)
            u = Unit(
                name="Calculus",
                cls=c,
                desc="Advanced calculus",
                template="template1",
                Qnum="10",
                maxTime="60",
                subDate="2023-05-31",
                order=1,
                # next=None
            )

            # Test that removeUnit_for_test returns an error message and status code 400
            url = "http://example.com?teacherName=John&unitName=Calculus&className=English"
            response, status_code = app.removeUnit_for_test(url)
            self.assertIn("Cls['English']", response)
            self.assertEqual(status_code, 400)

            # Assert that the unit was not removed from the database
            self.assertIsNotNone(Unit.get(name="Calculus", cls=c))

    def test_teacherOpenUnit_exception_class_not_found(self):
        unitName = "Unit 2"
        teacherName = "John Doe"
        className = "Math Class"
        template = "Template B"
        Qnum = "15"
        maxTime = "90"
        subDate = "2023-05-25"
        first = 'true'
        prev = "Prev Unit"
        desc = "Unit 2 description"

        result = app.teacherOpenUnit(unitName, teacherName, className, template, Qnum, maxTime, subDate, first, prev,
                                     desc)
        self.assertIsInstance(result, tuple)
        self.assertEqual(result[0], "Cls['Math Class']")
        self.assertEqual(result[1], 400)

    def test_teacherOpenUnit_success(self):
        unitName = "Unit 1"
        teacherName = "John Doe"
        className = "English Class"
        template = "Template A"
        Qnum = "10"
        maxTime = "60"
        subDate = "2023-05-20"
        first = 'true'
        prev = None
        desc = "Unit 1 description"
        with db_session:
            teacher = app.makeUser("teacher1", "123", 1)
            app.makeClass("teacher1", "English Class")
            result = app.teacherOpenUnit(unitName, teacherName, className, template, Qnum, maxTime, subDate, first,
                                         prev, desc)
            self.assertEqual(result, "success")
            result = app.teacherOpenUnit(unitName, teacherName, className, template, Qnum, maxTime, subDate,
                                         first,
                                         prev, desc)
            self.assertEqual(result, (
            "Cannot create Unit: instance with primary key Unit 1, Cls['English Class'] "'already exists', 400))

    @patch('flaskProject.app.db_session')
    def test_teacherOpenUnit_fail_name_unique(self, mock_isLogin=None):
        # Set up the mock
        mock_isLogin.return_value = True

        unitName = "Unit 2"
        teacherName = "John Doe"
        className = "English Class"
        template = "Template A"
        Qnum = "10"
        maxTime = "60"
        subDate = "2023-05-20"
        first = 'true'
        prev = None
        desc = "Unit 2 description"
        with db_session:
            teacher = app.makeUser("teacher1", "123", 1)
            app.makeClass("teacher1", "English Class")
            result = app.teacherOpenUnit(unitName, teacherName, className, template, Qnum, maxTime, subDate, first,
                                         prev, desc)
            self.assertEqual(result, "success")
            result = app.teacherOpenUnit(unitName, teacherName, className, template, Qnum, maxTime, subDate,
                                         first,
                                         prev, desc)
            self.assertEqual(result, (
                "Cannot create Unit: instance with primary key Unit 2, Cls['English Class'] "'already exists', 400))

    @patch('flaskProject.app.db_session')
    def test_teacherOpenUnit_failure_incorrect_class_name(self, mock_db_session):
        unitName = "Unit 1"
        teacherName = "John Doe"
        className = "English Class"
        template = "Template A"
        Qnum = "10"
        maxTime = "60"
        subDate = "2023-05-20"
        first = 'true'
        prev = None
        desc = "Unit 3 description"

        # Raise an exception within the db_session context
        mock_db_session.side_effect = Exception("Something went wrong")

        with db_session:
            teacher = app.makeUser("teacher1", "123", 1)
            app.makeClass("teacher1", "English Classs")
            result = app.teacherOpenUnit(unitName, teacherName, className, template, Qnum, maxTime, subDate, first,
                                         prev, desc)

            self.assertEqual(result, ("Cls['English Class']", 400))

    @patch('flaskProject.app.isLogin')
    def test_deleteUnit_success(self, mock_isLogin):
        # Set up the mock
        mock_isLogin.return_value = True
        with db_session:
            teacher = User(name="John Doe", password="password", type=1)
            cls = Cls(name="English Class", teacher=teacher)
            unit = Unit(name="Unit", cls=cls, desc="Unit description", template="Template A",
                        Qnum="10", maxTime="60", subDate="2023-05-20", order=1)
            commit()
            # Call the deleteUnit function
            result = app.deleteUnit(
                'http://example.com/delete?unitName=Unit&className=English%20Class&teacherName=John%20Doe')

            # Verify that the unit was deleted successfully
            with db_session:
                units = app.select(u for u in Unit if u.name == "Unit" and u.cls.name == "English Class")[:]
                self.assertEqual(len(units), 0)

            # Assert that the correct response was returned
            self.assertEqual(result, "deleted successfully")

    @patch('flaskProject.app.isLogin')
    def test_deleteUnit_incorrect_unit_name(self, mock_isLogin):
        # Set up the mock
        mock_isLogin.return_value = True
        with db_session:
            teacher = User(name="John Doe", password="password", type=1)
            cls = Cls(name="English Class", teacher=teacher)
            unit = Unit(name="Unitt", cls=cls, desc="Unit description", template="Template A",
                        Qnum="10", maxTime="60", subDate="2023-05-20", order=1)
            commit()
        # Call the deleteUnit function
        result = app.deleteUnit(
            'http://example.com/delete?unitName=Unit&className=English%20Class&teacherName=Jane%20Smith')

        # Verify that the unit was not deleted
        with db_session:
            units = app.select(u for u in Unit if u.name == "Unit" and u.cls.name == "English Class")[:]
            self.assertEqual(len(units), 0)

        # Assert that the correct response was returned
        self.assertEqual(result, ("Unit['Unit',Cls['English Class']]", 400))

    @patch('flaskProject.app.isLogin')
    def test_getClassUnits_success(self, mock_isLogin):
        # Set up the mock
        mock_isLogin.return_value = True
        with db_session:
            teacher = User(name="John Doe", password="password", type=1)
            cls = Cls(name="English Class", teacher=teacher)
            unit1 = Unit(name="Unit 1", cls=cls, desc="Unit 1 description", template="Template A",
                         Qnum="10", maxTime="60", subDate="2023-05-20", order=1)
            unit2 = Unit(name="Unit 2", cls=cls, desc="Unit 2 description", template="Template B",
                         Qnum="5", maxTime="30", subDate="2023-06-01", order=2)
            commit()
        # Call the getClassUnits function
        result = app.getClassUnits('http://example.com/units?className=English%20Class&teacherName=John%20Doe')

        # Verify the returned units
        expected_units = [
            {
                "id": 1,
                "primary": "Unit 1",
                "secondary": "Unit 1 description",
                "due": "2023-05-20"
            }
        ]
        self.assertEqual(result, expected_units)

    @patch('flaskProject.app.isLogin')
    def test_getClassUnits_not_logged_in(self, mock_isLogin):
        # Set up the mock
        mock_isLogin.return_value = False
        mock_isLogin.side_effect = lambda x: False
        with db_session:
            teacher = User(name="John Doe", password="password", type=1)
            cls = Cls(name="English Class", teacher=teacher)
            unit1 = Unit(name="Unit 1", cls=cls, desc="Unit 1 description", template="Template A",
                         Qnum="10", maxTime="60", subDate="2023-05-20", order=1)
            unit2 = Unit(name="Unit 2", cls=cls, desc="Unit 2 description", template="Template B",
                         Qnum="5", maxTime="30", subDate="2023-06-01", order=2)
            commit()

        # Call the getClassUnits function
        result = app.getClassUnits('http://example.com/units?className=English%20Class&teacherName=Jane%20Smith')

        # Verify that the user is not logged in
        self.assertEqual(result, ('user Jane Smith not logged in.', 400))

    def test_getUnitDetails_existing_unit(self):
        with db_session:
            teacher = User(name="John", password="password", type=1)
            cls = Cls(name="English Class", teacher=teacher)
            unit = Unit(name="Unit 1", cls=cls, desc="Unit 1 description", template="Template A",
                        Qnum="10", maxTime="60", subDate="2023-05-20", order=1)
            commit()
        # Call the getUnitDetails_for_tests function with an existing unit
        result = app.getUnitDetails_for_tests(
            'http://example.com/unit?className=English%20Class&unitName=Unit%201&teacherName=John%20Doe')

        # Verify the returned unit details
        expected_unit = {'Qnum': '10',
                         'desc': 'Unit 1 description',
                         'maxTime': '60',
                         'name': 'Unit 1',
                         'next': '',
                         'order': 1,
                         'subDate': '2023-05-20',
                         'template': 'Template A'}

        self.assertEqual(result, expected_unit)

    def test_getUnitDetails_nonexistent_unit(self):
        # Set up a test database with a sample class and a nonexistent unit
        with db_session:
            teacher = User(name="John Doe", password="password", type=1)
            cls = Cls(name="English Class", teacher=teacher)
            commit()

        # Call the getUnitDetails_for_tests function with the query parameters for a nonexistent unit
        result = app.getUnitDetails_for_tests(
            'http://example.com/unit?className=English%20Class&unitName=Unit%202&teacherName=John%20Doe')

        # Verify that an empty string is returned
        self.assertEqual(result, "")

    def test_find_min(self):
        # Call the find_min_max function with parameters for a minimum
        result = app.find_min_max(1, 2, 1)

        # Verify that the result contains the minimum coordinates
        expected_result = {
            "minimum": {"x": -1.0, "y": 0.0}
        }
        self.assertEqual(result, expected_result)

    def test_find_max(self):
        # Call the find_min_max function with parameters for a maximum
        result = app.find_min_max(-1, 2, 1)

        # Verify that the result contains the maximum coordinates
        expected_result = {
            "maximum": {'x': 1.0, 'y': 2.0}
        }
        self.assertEqual(result, expected_result)

    def test_quadQuestion_discriminant_positive(self):
        # Call the quadQuestion function with parameters that result in a positive discriminant
        result = app.quadQuestion(1, -3, 2)

        # Verify the returned answer
        expected_result = ((0, 2), ((2.0, 0), (1.0, 0)))
        self.assertEqual(result, expected_result)

    def test_quadQuestion_discriminant_zero(self):
        # Call the quadQuestion function with parameters that result in a zero discriminant
        result = app.quadQuestion(1, -2, 1)

        # Verify the returned answer
        expected_result = ((0, 1), (1.0, 0))
        self.assertEqual(result, expected_result)

    def test_quadQuestion_discriminant_negative(self):
        # Call the quadQuestion function with parameters that result in a negative discriminant
        result = app.quadQuestion(1, 1, 1)

        # Verify the returned answer
        expected_result = ((0, 1), ())
        self.assertEqual(result, expected_result)

    def test_registerClass_for_tests(self):
        # Mock the URL with query parameters for testing
        url = 'http://example.com/registerClass?studentName=John&className=Math'

        # Create a mock database session for testing
        with db_session:
            # Create necessary entities (User, Cls, Cls_User) for testing
            user = User(name='John', password='password', type=1)
            cls = Cls(name='Math', teacher=user)

        # Call the registerClass_for_tests function with the mocked URL

        result = app.registerClass_for_tests(url)

        # Verify the result
        self.assertEqual(result, ('successful', 200))

    def test_approveStudentToClass(self):
        # Mock the URL with query parameters for testing
        url = 'http://example.com/approveStudentToClass?studentName=John&teacherName=Mary&className=Math&approve=True'

        # Create a mock database session for testing
        with db_session:
            # Create necessary entities (User, Cls, Cls_User) for testing
            teacher = User(name='Mary', password='password', type=1)
            student = User(name='John', password='password', type=1)
            cls = Cls(name='Math', teacher=teacher)
            cls_user = app.Cls_User(cls=cls, user=student, approved=False)
            commit()  # Commit the entities to the mock database session

        # Call the approveStudentToClass function with the mocked URL

        result = app.approveStudentToClass_tests(url)

        # Verify the result
        expected_result = "successful"
        self.assertEqual(result, ('successful', 200))

    # def test_acceptance1(self):
    #     # Set up a test database with a sample class and a nonexistent unit
    #     with db_session:
    #         teacher = User(name="teacher1", password="password", type=1)
    #         cls = Cls(name="English Class", teacher=teacher)
    #         app.teacherOpenUnit("unit1", "John Doe", "English Class", "template", 4, "60", "2023-05-31", True, "", "desc")
    #         student1 = app.makeUser("student1", "123", 2)
    #         app.registerClass_for_tests('http://example.com/registerClass?studentName=student1&className=English Class')
    #         app.approveStudentToClass_tests('http://example.com/approveStudentToClass?studentName=student1&teacher=teacher1&className=English Class&approve=True')
    #         commit()


if __name__ == '__main__':
    unittest.main()
