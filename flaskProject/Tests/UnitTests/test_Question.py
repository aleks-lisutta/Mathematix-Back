import unittest
import os
from pony.orm import db_session, Database, PrimaryKey, Required, Optional, Set, CacheIndexError, commit

import flaskProject
from flaskProject import app
from flaskProject.app import User, DB, teacherCont, studentCont, Cls, Unit
from unittest import mock
from unittest.mock import patch, MagicMock


class MyTestCase(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
