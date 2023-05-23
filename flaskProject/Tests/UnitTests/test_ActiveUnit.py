import unittest
import os
from pony.orm import db_session, Database, PrimaryKey, Required, Optional, Set, CacheIndexError, commit
from flaskProject import app
from flaskProject.app import User, DB, teacherCont, studentCont, Cls, Unit
from unittest import mock
from unittest.mock import patch, MagicMock



class TestGetMaxUnit(unittest.TestCase):
    def setUp(self):
        DB = Database()
        DB.bind(provider='sqlite', filename='..\\..\\dbtest.sqlite', create_db=True)



        # Generate mapping and create tables

        DB.generate_mapping(create_tables=True)

    def tearDown(self):
        DB.disconnect()
        # Remove the test database file after testing
        cwd = os.getcwd()
        os.remove('\\'.join(cwd.split('\\')[:-2]) + r'\dbtest.sqlite')

    def test_get_max_unit_sucess(self):
        with db_session:
            # Create a test User and Unit
            student1 = User(name="student1", password="123", type=2)
            student2 = User(name="student2", password="123", type=2)
            teacher = User(name="teacher1", password="123", type=1)
            c = Cls(name="Math", teacher=teacher)
            unit = Unit(
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
            app.ActiveUnit(unit=unit, student=student2, attempt=1, inProgress=False, consecQues=2, quesAmount=1,
                           currentQuestion=5, totalCorrect=2)
            # Create multiple ActiveUnit instances for the given User and Unit
            active_units = [
                app.ActiveUnit(unit=unit, student=student1, attempt=1, inProgress=False, consecQues=2, quesAmount=1,
                               currentQuestion=5, totalCorrect=2),
                app.ActiveUnit(unit=unit, student=student1, attempt=2, inProgress=False, consecQues=2, quesAmount=1,
                               currentQuestion=5, totalCorrect=2),
                app.ActiveUnit(unit=unit, student=student1, attempt=3, inProgress=False, consecQues=2, quesAmount=1,
                               currentQuestion=5, totalCorrect=2),
                app.ActiveUnit(unit=unit, student=student1, attempt=4, inProgress=False, consecQues=2, quesAmount=1,
                               currentQuestion=5, totalCorrect=2)
            ]
            # Call the function under test
            max_attempt = app.get_max_unit(unit, student1)

            # Assert the expected result
            self.assertEqual(max_attempt, 4)

if __name__ == '__main__':
    unittest.main()


