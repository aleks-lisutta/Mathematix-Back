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
        with db_session:
            DB.execute('DELETE FROM ActiveUnit WHERE 1=1;')
            DB.execute('DELETE FROM Question WHERE 1=1;')
            DB.execute('DELETE FROM Unit WHERE 1=1;')
            DB.execute('DELETE FROM Cls_User WHERE 1=1;')
            DB.execute('DELETE FROM Cls WHERE 1=1;')
            DB.execute('DELETE FROM User WHERE 1=1;')

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

    @patch('builtins.print')
    def test_make_poly(self, mock_print):
        # Define the polynomial coefficients
        p = [2, 1, -3]

        # Call the makePoly function
        result = app.makePoly(p)

        # Assert that the print statement was called with the expected output
        mock_print.assert_called_with(['2*(x**2)', '1*(x**1)', '-3*(x**0)'])

        # Test the returned lambda function
        # Evaluate the lambda function at x = 2
        self.assertEqual(result(2), 2 * (2 ** 2) + 1 * (2 ** 1) - 3 * (2 ** 0))

    def test_regula_falsi(self):
        # Define the functions f1 and f2
        def f1(x):
            return x ** 2 - 4

        def f2(x):
            return np.sin(x)

        # Define the initial values
        x1 = 1
        x2 = 3
        a = 0
        b = 5
        maxerr = 0.0001

        # Call the regulaFalsi function
        result = app.regulaFalsi(f1, f2, x1, x2, a, b, maxerr)

        # Assert that the result is within the expected range and has the desired accuracy
        self.assertIsNotNone(result)
        self.assertTrue(a - maxerr <= result <= b + maxerr)
        self.assertLessEqual(np.abs(f1(result) - f2(result)), maxerr)

    def test_make_intersections(self):
        # Define a polynomial function
        def poly(x):
            return x ** 3 - 2 * x ** 2 - x + 2

        # Call the makeIntersections function
        result = app.makeIntersections(poly)

        # Define the expected intersection points
        expected_points = [(-1.0, 0.0), (1.0, 0.0), (2.0, 0.0), (0.0, 2.0)]

        # Assert that the result matches the expected intersection points
        self.assertEqual(result, expected_points)

    def test_intersections(self):
        # Define two functions
        def f1(x):
            return x ** 2 - 4

        def f2(x):
            return x - 2

        # Call the intersections function
        result = app.intersections(f1, f2, -10, 10)

        # Define the expected intersection points
        expected_points = np.array([-1.0, 2.0])

        # Assert that the result matches the expected intersection points
        np.testing.assert_allclose(result, expected_points)

    def test_makeIntersections2(self):
        # Define a polynomial function
        def poly(x):
            return x ** 3 - 2 * x ** 2 - x + 2

        # Call the makeIntersections2 function
        result = app.makeIntersections2(poly, error=1e-3, xmin=-20, xmax=20, step=0.0003)

        # Define the expected intersection points
        expected_points = [(-1.0, 0), (1.0, 0), (2.0, 0), (0, 2)]

        # Assert that the result matches the expected intersection points
        self.assertEqual(result, expected_points)

    def test_makeDer(self):
        # Define the parameters of the polynomial
        params = [2, -3, 1]  # Represents the polynomial 2x^2 - 3x + 1

        # Call the makeDer function
        result = app.makeDer(params)

        # Define the expected derivative
        expected_derivative = [4, -3]  # Represents the derivative of the polynomial: 4x - 3

        # Assert that the result matches the expected derivative
        self.assertEqual(result, expected_derivative)


    def test_makeExtremes(self):
        # Define the parameters of the polynomial
        params = [2, -3, 1]  # Represents the polynomial 2x^2 - 3x + 1

        # Call the makeExtremes function
        result = app.makeExtremes(params)

        # Define the expected extremes
        expected_extremes = [
            (0.75, -0.125)]  # Represents the x-coordinate and y-coordinate of the extreme point (0.75, 0.875)

        # Assert that the result matches the expected extremes
        self.assertEqual(result, expected_extremes)

    def test_makeIncDec(self):
        # Define the parameters of the polynomial
        params = [2, -3, 1]  # Represents the polynomial 2x^2 - 3x + 1

        # Call the makeIncDec function
        inc_ranges, dec_ranges = app.makeIncDec(params)

        # Define the expected increasing and decreasing ranges
        expected_inc_ranges = [(0.75, float('inf'))]  # Represents the range of increasing values: (0.75, infinity)
        expected_dec_ranges = [(-float('inf'), 0.75)]  # Represents the range of decreasing values: (-infinity, 0.75)

        # Assert that the result matches the expected ranges
        self.assertEqual(inc_ranges, expected_inc_ranges)
        self.assertEqual(dec_ranges, expected_dec_ranges)

    def test_polySrting(self):
        # Define the parameters of the polynomial
        params = [2, -3, 1]  # Represents the polynomial 2x^2 - 3x + 1

        # Call the polySrting function
        result = app.polySrting(params)

        # Define the expected result
        expected_result = "y=2x^2-3x+1"

        # Assert that the result matches the expected string representation of the polynomial
        self.assertEqual(result, expected_result)




if __name__ == '__main__':
    unittest.main()
