import unittest
import os
from pony.orm import db_session, Database, PrimaryKey, Required, Optional, Set, CacheIndexError, commit
from flaskProject import app
from flaskProject.Tests.UnitTests import initiate_database
from flaskProject.app import User, DB, teacherCont, studentCont, Cls, Unit
from unittest import mock
from unittest.mock import patch



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

    @patch('flaskProject.app.isLogin')
    def test_editUnit_incorrect_teacher(self, mock_isLogin):
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
        response, status_code = app.editUnit_buisness("Math", "Math", "Calculus", "10", "60", "2023-05-31", "Advanced calculus", "Johny")
        self.assertEqual(response, "user Johny is not a teacher")
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
            response = app.editUnit_buisness("Math", "Math", "Calculus", "10", "60", "2023-05-31", "Advanced calculus", "John")
            error_message, status_code = response
            self.assertEqual(error_message, "Unit['Math',Cls['Math']]")
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
            response = app.editUnit_buisness("Math", "Math", "Calculus", "10", "60", "2023-05-31", "Advanced calculus", "John")
            self.assertEqual(response, ({'message': 'successful'}, 200))


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

            response, status_code = app.editUnit_buisness("Chemistry", "Science", "Biology", "10", "60", "2023-05-31", "Basic biology", "John")

            self.assertEqual(response, {"message": "successful"})
            self.assertEqual(status_code, 200)

    @patch('flaskProject.app.isLogin')
    def test_editUnit_not_teacher(self, mock_isLogin):
        # Set up the mock
        mock_isLogin.return_value = True

        # Add test data
        with db_session:
            teacher = User(name="teacher", password="123", type=2)
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
            response = app.editUnit_buisness("Math", "Math", "Calculus", "10", "60", "2023-05-31", "Advanced calculus", "John")
            self.assertEqual(response, ('user John is not a teacher', 400))


    @patch('flaskProject.app.isLogin')
    def test_removeUnit_incorrect_class(self, mock_isLogin):
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
            response, status_code = app.removeUnit_buisness("Calculus", "English", "John")
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
            result = app.teacherOpenUnit(unitName, teacherName, className, template, Qnum, maxTime, subDate, first, prev, desc)
            self.assertEqual(result, "success")
            result = app.teacherOpenUnit(unitName, teacherName, className, template, Qnum, maxTime, subDate,
                                         first,
                                         prev, desc)
            self.assertEqual(result, ("Cannot create Unit: instance with primary key Unit 1, Cls['English Class'] "'already exists', 400))

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
            result = app.deleteUnit_buisness("Unit", "English Class", "John Doe")
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
        result = app.deleteUnit_buisness("Unit", "English", "Jane Smith")
        # Verify that the unit was not deleted
        with db_session:
            units = app.select(u for u in Unit if u.name == "Unit" and u.cls.name == "English Class")[:]
            self.assertEqual(len(units), 0)

        # Assert that the correct response was returned
        self.assertEqual(result, ("Cls['English']", 400))

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
        result = app.getClassUnits_buisness("English Class", "John Doe")

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
    def test_getClassUnits_incorrect_class(self, mock_isLogin):
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
        result = app.getClassUnits_buisness("English", "Jane Smith")

        # Verify that the user is not logged in
        self.assertEqual(result, ("Cls['English']", 400))

    def test_getUnitDetails_existing_unit(self):
        with db_session:
            teacher = User(name="John", password="password", type=1)
            cls = Cls(name="English Class", teacher=teacher)
            unit = Unit(name="Unit 1", cls=cls, desc="Unit 1 description", template="Template A",
                        Qnum="10", maxTime="60", subDate="2023-05-20", order=1)
            commit()
        # Call the getUnitDetails_for_tests function with an existing unit
        result = app.getUnitDetails_buisness("English Class", "Unit 1", "John Doe")

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
        result = app.getUnitDetails_buisness("English", "Unit", "John Doe")

        # Verify that an empty string is returned
        self.assertEqual(result, "")

    @patch('flaskProject.app.isLogin')
    def test_editUnit_nonexistent_class(self, mock_isLogin):
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
        response, status_code = app.editUnit_buisness("Math", "Mathemathic", "Calculus", "10", "60", "2023-05-31", "Advanced calculus", "John")
        self.assertEqual(response, "Cls['Mathemathic']")
        self.assertEqual(status_code, 400)

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
            response, status_code = app.removeUnit_buisness("Calculus", "Math", "John")
            self.assertEqual(response, "successful")
            self.assertEqual(status_code, 200)

            # Assert that the unit was removed from the database
            self.assertIsNone(Unit.get(name="Calculus", cls=c))

    def test_getAllActiveUnits_successful(self):
        with app.app.app_context():
            # Create teacher account and open a class and a unit
            app.register_buisness('teacher1', 'password', 1)
            app.login_buisness('teacher1', 'password')
            app.openClass_buisness('teacher1', 'class1')
            app.teacherOpenUnit('unit1', 'teacher1', 'class1', 'intersection_linear_-10,0,1,6', '1', '60', '2023-07-01',
                                'true', 'new', 'desc')
            # Create 2 students and register to class
            app.register_buisness('student1', 'password', 2)
            app.login_buisness('student1', 'password')
            app.registerClass_buisness('student1', 'class1')
            app.approveStudentToClass_buisness('teacher1', 'student1', 'class1', 'True')
            app.register_buisness('student2', 'password', 2)
            app.login_buisness('student2', 'password')
            app.registerClass_buisness('student2', 'class1')
            app.approveStudentToClass_buisness('teacher1', 'student2', 'class1', 'True')
            # Both students start unit
            app.startUnit_buisness('class1', 'unit1', 'student1')
            app.startUnit_buisness('class1', 'unit1', 'student2')
            # Student1 answers correctly, Student2 fails
            res = app.getQuestion_buisness('student1', 'unit1', 'class1', '1')
            app.submitQuestion_buisness('student1', 'unit1', 'class1', '1', res.json[0]['correct_ans'])
            app.getQuestion_buisness('student2', 'unit1', 'class1', '1')
            app.submitQuestion_buisness('student2', 'unit1', 'class1', '1', '-1')
            # Check function
            res = app.getAllActiveUnits_buisness('class1', 'unit1')
            self.assertEqual(2, len(res.json), 'JSON returned with less then 2 values.')
            for dic in res.json:
                if dic['name'] == 'student1':
                    self.assertEqual(1, dic['correct'], 'Not 1 correct for student1')
                    self.assertEqual(0, dic['bad'], 'Not 0 mistakes for student1')
                else:
                    self.assertEqual(1, dic['bad'], 'Not 1 mistakes for student1')
                    self.assertEqual(0, dic['correct'], 'Not 0 correct for student1')

    def test_getAllActiveUnits_no_class_failure(self):
        with app.app.app_context():
            # Create teacher account and open a class and a unit
            app.register_buisness('teacher1', 'password', 1)
            app.login_buisness('teacher1', 'password')
            res = app.getAllActiveUnits_buisness('class1', 'unit1')
            self.assertEqual(0, len(res.json), 'Retrieved a active units')

    def test_getAllActiveUnits_no_unit_failure(self):
        with app.app.app_context():
            # Create teacher account and open a class and a unit
            app.register_buisness('teacher1', 'password', 1)
            app.login_buisness('teacher1', 'password')
            app.openClass_buisness('teacher1', 'class1')
            res = app.getAllActiveUnits_buisness('class1', 'unit1')
            self.assertEqual(0, len(res.json), 'Retrieved a active units')


if __name__ == '__main__':
    unittest.main()
