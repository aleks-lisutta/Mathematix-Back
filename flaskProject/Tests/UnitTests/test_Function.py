import unittest

import numpy as np
from pony.orm import db_session, Database


from flaskProject import app
from flaskProject.Tests.UnitTests import initiate_database
from flaskProject.app import DB

from sympy import pi



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




    def testPoly(self):
        p = [-3, 7, -4, 1]
        c = 0
        b = 2
        a = app.makeFunc(p, c=c, b=b)
        self.assertTrue(-219 == a(5))
        dom = app.makeDomain(p, c)
        self.assertTrue([(float('-inf'), float('inf'))] == dom)
        self.assertTrue(app.makeIntersections(a, c=c, r=dom) == [(1.65, 0.0)])
        self.assertTrue(app.makeExtremes(p, c=c) == [(0.38, 0.326), (1.18, 1.098)])
        self.assertTrue(app.makeIncDec(p, c=c) == ([(0.38, 1.18)], [(float('-inf'), 0.38), (1.18, float('inf'))]))
        self.assertTrue(app.funcString(p, c=c) == "y=-3x^3+7x^2-4x+1")
        self.assertTrue(app.deriveString(p, c=c) == "y'=-9x^2+14x-4")
        self.assertTrue(app.makePosNeg(p, c=c) == ([(float('-inf'), 1.65)], [(1.65, float('inf'))]))
        self.assertTrue(app.makeAsym(p, c=c) == ([], []))
        self.assertTrue(app.make_extreme_question(b, c, p)[2] == [(0.38, 0.326), (1.18, 1.098)])
        self.assertEqual("∪: [(-inf, 0.778)]\n∩: [(0.778, inf)]", str(app.make_convex_concave_question(b, c, p)[2]))
        self.assertEqual("(0.778, 0.712)", str(app.make_inflection_question(b, c, p)[2]))



    def testExp(self):
        p = [-3, 7, -4, 1]
        c = 1
        b = 2
        a = app.makeFunc(p, c=c, b=b)
        self.assertTrue(1.0000000000000568 == a(5))
        dom = app.makeDomain(p, c)
        r1 = -6
        r2 = 2
        result = app.definite_integral_question(b, c, a, (r1, r2), p)[2] #y=2^(-3x^2+7x-4)+1 integral
        assert np.isclose(result, 9.244126319885254, rtol=1e-6)
        self.assertTrue([(float('-inf'), float('inf'))] == dom)
        self.assertTrue(app.makeIntersections(a, c=c, r=dom) == [])
        self.assertIn("(-2.0, 1.0), (-1.98, 1.0), (-1.96, 1.0), (-1.94, 1.0)" ,str(app.makeExtremes(p, c=c, b=b)))
        self.assertIn("[(-inf, -2.0), (-1.44, 1.17)], [(1.17, inf)]", str(app.makeIncDec(p, c=c, b=b)))
        self.assertTrue(app.funcString(p, c=c, b=b) == "y=2^{-3x^2+7x-4}+1")
        self.assertTrue(app.deriveString(p, c=c, b=b) == "y'=ln(2)(-6x+7) \cdot 2^{-3x^2+7x-4}")
        self.assertTrue(app.makePosNeg(p, c=c, b=b) == ([(float('-inf'), float('inf'))], []))
        self.assertTrue(app.makeAsym(p, c=c, b=b) == ([], [(float('inf'), 1.0), (float('-inf'), 1.0)]))
        self.assertIn("(-2.0, 1.0), (-1.98, 1.0), (-1.96, 1.0), (-1.94, 1.0)", str(app.make_extreme_question(b, c, p)[2]))
        self.assertEqual("∪: [(1.657, inf), (-inf, 0.676)]\n∩: [(0.676, 1.657)]", str(app.make_convex_concave_question(b, c, p)[2]))
        print(app.make_inflection_question(b, c, p)[2])
        self.assertTrue(str(app.make_inflection_question(b, c, p)[2]) in ["(1.657, 1.643)", "(0.676, 1.642)"])



    def testLog(self):
        p = [-3, 7, -4, 1]
        c = 2
        b = 2
        a = app.makeFunc(p, c=c, b=b)
        self.assertTrue(None == a(5))
        dom = app.makeDomain(p, c)
        r1 = -6
        r2 = 2
        result = app.definite_integral_question(b, c, a, (r1, r2), p)[2]  # y=log2(-3x^2+7x-4)+1 integral
        self.assertEqual(result, 0)
        self.assertTrue([(1.0, 1.333)] == dom)
        self.assertTrue(app.makeIntersections(a, c=c, r=dom) == [])
        e = app.makeExtremes(p, c=c, b=b)
        self.assertTrue(e == [(1.17, -2.586)])
        self.assertTrue(app.makeIncDec(p, c=c, b=b) == ([(1.0, 1.17)], [(1.17, 1.333)]))
        self.assertTrue(app.funcString(p, c=c, b=b) == "y=log_2(-3x^2+7x-4)+1")
        self.assertTrue(app.deriveString(p, c=c, b=b) == r"y'=\frac{-6x+7}{-3x^2+7x-4}")
        self.assertTrue(app.makePosNeg(p, c=c, b=b) == ([], [(1.0, 1.333)]))
        self.assertEqual([(1.17, -2.586)], app.make_extreme_question(b, c, p)[2])
        self.assertEqual("∪: []\n∩: [(1.0, 1.333)]", str(app.make_convex_concave_question(b, c, p)[2]))
        self.assertIn("[(1.0, -10.0), (1.333, -9.2)], []", str(app.makeAsym(p, c=c, b=b)))
        self.assertEqual("אין נקודות פיתול", str(app.make_inflection_question(b, c, p)[2]))


    def testSin(self):
        p = [-3, 7, -4, 1]
        c = 3
        b = 2
        a = app.makeFunc(p, c=c, b=b)
        r1 = -6
        r2 = 2
        result = app.definite_integral_question(b, c, a, (r1, r2), p)[2]  # y=sin(-3x^2+7x-4)+1 integral
        self.assertEqual(result, 7.270272731781006)
        self.assertTrue(0.9822980748945864 == a(5))
        dom = app.makeDomain(p, c)
        self.assertTrue([(float('-inf'), float('inf'))] == dom)
        self.assertIn("(-0.46, 0.0)", str(app.makeIntersections(a, c=c, r=dom)))
        self.assertIn("(-1.99, 1.999), (-1.82, 0.0), (-1.64, 2.0), (-1.45, 0.001)", str(app.makeExtremes(p, c=c, b=b)))
        self.assertIn("(-inf, -1.99), (-1.82, -1.64), (-1.45, -1.24)", str(app.makeIncDec(p, c=c, b=b)))
        self.assertTrue(app.funcString(p, c=c, b=b) == "y=sin(-3x^2+7x-4)+1")
        self.assertTrue(app.deriveString(p, c=c, b=b) == "y'=cos(-3x^2+7x-4)(-6x+7)")
        self.assertTrue(app.makePosNeg(p, c=c, b=b) == ([(float('-inf'), -0.46), (-0.46, float('inf'))], []))
        self.assertTrue(app.makeAsym(p, c=c, b=b) ==  ([], []))
        self.assertIn("(-1.99, 1.999), (-1.82, 0.0), (-1.64, 2.0)", str(app.make_extreme_question(b, c, p)[2]))

    def testCos(self):
        p = [-3, 7, -4, 1]
        c = 4
        b = 2
        a = app.makeFunc(p, c=c, b=b)
        self.assertTrue(1.9998433086476912 == a(5))
        r1 = -6
        r2 = 2
        result = app.definite_integral_question(b, c, a, (r1, r2), p)[2]  # y=cos(-3x^2+7x-4)+1 integral
        self.assertEqual(result, 8.960036277770996)
        dom = app.makeDomain(p, c)
        self.assertTrue([(float('-inf'), float('inf'))] == dom)
        self.assertIn("[]", str(app.makeIntersections(a, c=c, r=dom)))
        self.assertIn("(-1.91, 0.001), (-1.73, 1.999), (-1.55, 0.002)", str(app.makeExtremes(p, c=c, b=b)))
        self.assertIn("(-1.91, -1.73), (-1.55, -1.35), (-1.13, -0.89)", str(app.makeIncDec(p, c=c, b=b)))
        self.assertTrue(app.funcString(p, c=c, b=b) == "y=cos(-3x^2+7x-4)+1")
        self.assertTrue(app.deriveString(p, c=c, b=b) == "y'=-sin(-3x^2+7x-4)(-6x+7)")
        self.assertTrue(app.makePosNeg(p, c=c, b=b) == ([(float('-inf'), float('inf'))], []))
        self.assertTrue(app.makeAsym(p, c=c, b=b) == ([], []))
        self.assertIn("(-1.91, 0.001), (-1.73, 1.999), (-1.55, 0.002), (-1.35, 1.998)", str(app.make_extreme_question(b, c, p)[2]))

    def testTan(self):
        p = [-3, 7, -4, 1]
        c = 5
        b = 2
        a = app.makeFunc(p, c=c, b=b)
        self.assertTrue(0.9822953007213142 == a(5))
        r1 = -6
        r2 = 2
        result = app.definite_integral_question(b, c, a, (r1, r2), p)[2]  # y=tan(-3x^2+7x-4)+1 integral
        self.assertEqual(result, 1.7480018138885498)
        dom = app.makeDomain(p, c)
        self.assertIn("(-2.9934459652364747, -2.865620503322687)", str(dom))
        self.assertIn("(-2.96, 0.0), (-2.83, 0.0), (-2.7, 0.0)", str(app.makeIntersections(a, c=c, r=dom)))
        self.assertIn("(-2.96, -2.865620503322687), (-2.83, -2.7336079492722396)", str(app.makePosNeg(p, c=c)))
        self.assertIn("[(0.42411877993373426, 1.9092144399939124)], []", str(app.makeIncDec(p, c=c, b=b)))
        self.assertTrue(app.funcString(p, c=c, b=b) == "y=tan(-3x^2+7x-4)+1")
        self.assertTrue(app.deriveString(p, c=c, b=b) == r"y'=\frac{-6x+7}{cos^2(-3x^2+7x-4)}")
        self.assertEqual("אין נקודות קיצון", str(app.make_extreme_question(b, c, p)[2]))
        self.assertIn("[(-0.09768086093997672, -262.8), (1.9092144399939124, 449.4)", str(app.makeAsym(p, c=c, b=b)))


    def testCot(self): #need good assert values
        p = [-3, 7, -4, 1]
        c = 6
        b = 2
        a = app.makeFunc(p, c=c, b=b)
        self.assertTrue(-55.48217935019511 == a(5))
        r1 = -6
        r2 = 2
        result = app.definite_integral_question(b, c, a, (r1, r2), p)[2]  # y=cot(-3x^2+7x-4)+1 integral
        self.assertEqual(result, -6.302616119384766)
        dom = app.makeDomain(p, c)
        self.assertIn("(-2.930031977039845, -2.83), (-2.800163226766728, -2.7)", str(app.makePosNeg(p, c=c)))
        dom = app.makeDomain(p, c)
        self.assertIn("(-2.930031977039845, -2.800163226766728)", str(dom))
        self.assertIn("(-2.83, 0.0), (-2.7, 0.0)", str(app.makeIntersections(a, c=c, r=dom)))
        self.assertIn("[]", str(app.makeExtremes(p, c=c, b=b)))
        self.assertIn("[], [(1.0000000000000029, 1.333333324050148)]", str(app.makeIncDec(p, c=c, b=b)))
        self.assertTrue(app.funcString(p, c=c, b=b) == "y=cot(-3x^2+7x-4)+1")
        self.assertTrue(app.deriveString(p, c=c, b=b) == r"y'=-\frac{-6x+7}{sin^2(-3x^2+7x-4)}")
        self.assertEqual("אין נקודות קיצון", str(app.make_extreme_question(b, c, p)[2]))
        self.assertIn("(0.12985622674574937, 322.7), (-1.1276231218208512, 146.3)", str(app.makeAsym(p, c=c, b=b)))

    def testRational(self):
        p = [-3, 7, -4, 1]
        c = 7
        b = 2
        a = app.makeFunc(p, c=c, b=b)
        self.assertTrue(0.42105263157894735 == a(5))
        r1 = -6
        r2 = 2
        result = app.definite_integral_question(b, c, a, (r1, r2), p)[2]  # y=(-3x+7) / (-4x+1) integral
        self.assertEqual(result, 7.939740180969238)
        dom = app.makeDomain(p, c)
        self.assertTrue([(float('-inf'), 0.25), (0.25, float('inf'))] == dom)
        self.assertTrue(app.makeIntersections(a, c=c, r=dom) == [(2.33, 0.0)])
        self.assertTrue(app.makeExtremes(p, c=c) == [])
        self.assertTrue(app.makeIncDec(p, c=c) == ([(float('-inf'), 0.25), (0.25, float('inf'))], []))
        self.assertTrue(app.funcString(p, c=c) == "y=(-3x+7) / (-4x+1)")
        self.assertTrue(app.deriveString(p, c=c) == "y'=(((-3) \cdot (-4x+1)) - ((-4) * (-3x+7))) / (-4x+1)^2")
        self.assertTrue(app.makePosNeg(p, c=c) == ([(float('-inf'), 0.25), (2.33, float('inf'))], [(0.25, 2.33)]))
        self.assertTrue(app.makeAsym(p, c=c) == ([(0.25, float('-inf'))], [(float('-inf'), 0.75), (float('inf'), 0.75)]))
        self.assertEqual("אין נקודות קיצון", str(app.make_extreme_question(b, c, p)[2]))
        self.assertEqual("∪: [(-inf, 0.25)]\n∩: [(0.25, inf)]", str(app.make_convex_concave_question(b, c, p)[2]))
        self.assertEqual("אין נקודות פיתול", str(app.make_inflection_question(b, c, p)[2]))



    def testRoot(self):
        p = [-3, 7, -4, 1]
        c = 8
        b = 2
        a = app.makeFunc(p, c=c, b=b)
        self.assertTrue(None == a(5))
        r1 = -6
        r2 = 2
        result = app.definite_integral_question(b, c, a, (r1, r2), p)[2]  # y=(-3x^2+7x-4)^(0.5)+1 integral
        self.assertEqual(result, 0)
        dom = app.makeDomain(p, c)
        self.assertTrue([(1.0, 1.33)] == dom)
        self.assertTrue(app.makeIntersections(a, c=c, r=dom) == [])
        self.assertTrue(app.makeExtremes(p, c=c, b=b) == [(1.17, 1.289)])
        self.assertTrue(app.makeIncDec(p, c=c, b=b) == ([(1.17, 1.33)], [(1.0, 1.17)]))
        self.assertTrue(app.funcString(p, c=c, b=b) == "y=\sqrt{-3x^2+7x-4}")
        self.assertTrue(app.deriveString(p, c=c, b=b) == r"y'=\frac{-6x+7}{2\sqrt{-3x^2+7x-4}}")
        self.assertTrue(app.makePosNeg(p, c=c, b=b) == ([(1.0, 1.33)], []))
        self.assertTrue(app.makeAsym(p, c=c, b=b) == ([(1.0, 1.0),(1.33, 1.1)], []))
        self.assertEqual([(1.17, 1.289)], app.make_extreme_question(b, c, p)[2])
        self.assertEqual("∪: []\n∩: [(1.0, 1.33)]", str(app.make_convex_concave_question(b, c, p)[2]))
        self.assertEqual("אין נקודות פיתול", str(app.make_inflection_question(b, c, p)[2]))




    def test_get_answers_for_odd_even_poly(self):
        with app.app.app_context():
            expr = app.make_sympy_function((1, 0, 0), 0, 0)  # (x^2)
            domains = [(-10, 10)]

            result = app.get_answers_for_odd_even(expr[0], expr[1], domains)

            # Perform your assertions based on the expected output
            assert result == 'זוגית', "Expected 'זוגית'"
            expr = app.make_sympy_function((2, 0, 6, 0, 5), 0, 0)  # (2x^4+6x^2+5)
            domains = [(-10, 10)]
            result = app.get_answers_for_odd_even(expr[0], expr[1], domains)

            # Perform your assertions based on the expected output
            assert result == 'זוגית', "Expected 'זוגית'"
            expr = app.make_sympy_function((2, 0, -1, 0), 0, 0)  # (2x^3-x)
            domains = [(-10, 10)]

            result = app.get_answers_for_odd_even(expr[0], expr[1], domains)

            # Perform your assertions based on the expected output
            assert result == 'אי זוגית', "Expected 'אי זוגית'"

            expr = app.make_sympy_function((1, 0, 0, 0), 0, 0)  # (x^3)
            domains = [(-10, 10)]
            result = app.get_answers_for_odd_even(expr[0], expr[1], domains)

            # Perform your assertions based on the expected output
            assert result == 'אי זוגית', "Expected 'אי זוגית'"

    def test_get_answers_for_odd_even_ln(self):
        with app.app.app_context():
            expr = app.make_sympy_function((1, 0, 0, 0), 2, 0)  # ln(x^2)
            domains = [(-10, 10)]

            result = app.get_answers_for_odd_even(expr[0], expr[1], domains)

            # Perform your assertions based on the expected output
            assert result == 'זוגית', "Expected 'זוגית'"

    def test_get_answers_for_odd_even_cos(self):
        with app.app.app_context():
            expr = app.make_sympy_function((0, 1, 1, 0), 4, 0)  # cos(x+1)
            domains = [(-10, 10)]

            result = app.get_answers_for_odd_even(expr[0], expr[1], domains)

            # Perform your assertions based on the expected output
            assert result == 'לא זוגית ולא אי זוגית', "Expected 'לא זוגית ולא אי זוגית'"

            expr = app.make_sympy_function((1, 1, 0, 0), 4, 0)  # cos(x^2+x)
            domains = [(-10, 10)]

            result = app.get_answers_for_odd_even(expr[0], expr[1], domains)

            # Perform your assertions based on the expected output
            assert result == 'לא זוגית ולא אי זוגית', "Expected 'לא זוגית ולא אי זוגית'"

            expr = app.make_sympy_function((1, 0, 0, 0), 4, 0)  # cos(x^2)
            domains = [(-10, 10)]

            result = app.get_answers_for_odd_even(expr[0], expr[1], domains)

            # Perform your assertions based on the expected output
            assert result == 'זוגית', "Expected זוגית'"

    def test_get_answers_for_odd_even_tan(self):
        with app.app.app_context():
            expr = app.make_sympy_function((1, 1, 0, 0), 5, 0)  # tan(x^2+x)
            domains = [(-10, 10)]

            result = app.get_answers_for_odd_even(expr[0], expr[1], domains)

            # Perform your assertions based on the expected output
            assert result == 'לא זוגית ולא אי זוגית', "Expected 'לא זוגית ולא אי זוגית'"

            expr = app.make_sympy_function((1, 0, 0, 0), 5, 0)  # tan(x^2)
            domains = [(-10, 10)]

            result = app.get_answers_for_odd_even(expr[0], expr[1], domains)

            # Perform your assertions based on the expected output
            assert result == 'זוגית', "Expected 'זוגית'"

    def test_get_answers_for_odd_even_sin(self):
        with app.app.app_context():
            expr = app.make_sympy_function((1, 1, 0, 0), 3, 0)  # sin(x^2+x)
            domains = [(-pi, pi)]

            result = app.get_answers_for_odd_even(expr[0], expr[1], domains)

            # Perform your assertions based on the expected output
            assert result == 'לא זוגית ולא אי זוגית', "Expected 'לא זוגית ולא אי זוגית'"

            expr = app.make_sympy_function((1, 0, 0, 0), 3, 0)  # sin(x^2)
            domains = [(-pi, pi)]

            result = app.get_answers_for_odd_even(expr[0], expr[1], domains)

            # Perform your assertions based on the expected output
            assert result == 'זוגית', "Expected 'זוגית'"

    def test_get_answers_for_odd_even_pow(self):
        with app.app.app_context():
            expr = app.make_sympy_function((1, 0, 0, 0), 1, 2)  # 2^x^2
            domains = [(-10, 10)]

            result = app.get_answers_for_odd_even(expr[0], expr[1], domains)

            # Perform your assertions based on the expected output
            assert result == 'זוגית', "Expected 'זוגית'"

            expr = app.make_sympy_function((0, 1, 0, 0), 1, 2)  # 2^x
            domains = [(-10, 10)]

            result = app.get_answers_for_odd_even(expr[0], expr[1], domains)

            # Perform your assertions based on the expected output
            assert result == 'לא זוגית ולא אי זוגית', "Expected 'לא זוגית ולא אי זוגית'"

    def test_get_answers_for_odd_even_root(self):
        with app.app.app_context():
            expr = app.make_sympy_function((1, 0, 0, 0, 0), 8, 2)  # root2 (x^3)
            domains = [(-10, 10)]

            result = app.get_answers_for_odd_even(expr[0], expr[1], domains)

            # Perform your assertions based on the expected output
            assert result == 'לא זוגית ולא אי זוגית', "Expected 'לא זוגית ולא אי זוגית'"

            expr = app.make_sympy_function((1, 0, 1, 0), 8, 2)  # root2 (x^2 + 1)
            domains = [(-10, 10)]

            result = app.get_answers_for_odd_even(expr[0], expr[1], domains)

            # Perform your assertions based on the expected output
            assert result == 'זוגית', "Expected 'זוגית'"

    def test_get_answers_for_symmetry_asymmetry_ln(self):
        with app.app.app_context():
            expr = app.make_sympy_function((1, 0, 0, 0), 2, 0)  # ln(x^2)
            domains = [(-100, 100)]

            result = app.get_answers_for_symmetry_asymmetry(expr[0], expr[1], 0, domains)

            # Perform your assertions based on the expected output
            assert result[1] == 'סימטריה', "Expected 'סימטריה'"

    def test_get_answers_for_symmetry_asymmetry_constant(self):
        with app.app.app_context():
            expr = app.make_sympy_function((5), 0, 0)  # (5)
            domains = [(-10, 10)]

            result = app.get_answers_for_symmetry_asymmetry(expr[0], expr[1], 0, domains)

            # Perform your assertions based on the expected output
            assert result[1] == 'סימטריה לכל x', "Expected 'סימטריה לכל x'"

    def test_get_answers_for_symmetry_asymmetry_cos(self):
        with app.app.app_context():
            expr = app.make_sympy_function((1, 0), 4, 0)  # cos(x)
            domains = [(-pi, pi)]

            result = app.get_answers_for_symmetry_asymmetry(expr[0], expr[1], 0, domains)

            # Perform your assertions based on the expected output
            assert result[1] == 'סימטריה לכל x', "Expected 'סימטריה'"

    def test_get_answers_for_symmetry_asymmetry_sin(self):
        with app.app.app_context():
            expr = app.make_sympy_function((1, 0), 3, 0)  # sin(x)
            domains = [(-pi, pi)]

            result = app.get_answers_for_symmetry_asymmetry(expr[0], expr[1], 0, domains)

            # Perform your assertions based on the expected output
            assert result[1] == 'סימטריה לכל x', "Expected 'סימטריה'"

            expr = app.make_sympy_function((1, 0, 0, 0), 3, 0)  # sin(x^2)
            domains = [(-pi, pi)]

            result = app.get_answers_for_symmetry_asymmetry(expr[0], expr[1], 0, domains)

            # Perform your assertions based on the expected output
            assert result[1] == 'סימטריה', "Expected 'סימטריה'"

    def test_get_answers_for_symmetry_asymmetry_root(self):
        with app.app.app_context():
            expr = app.make_sympy_function((1, 0, 1, 0), 8, 2)  # root2 (x^2 + 1)
            domains = [(-10, 10)]

            result = app.get_answers_for_symmetry_asymmetry(expr[0], expr[1], 0, domains)

            # Perform your assertions based on the expected output
            assert result[1] == 'סימטריה', "Expected 'סימטריה'"
            expr = app.make_sympy_function((0, 1, 0, 0), 8, 3)  # root3 (x)
            domains = [(-10, 10)]

            result = app.get_answers_for_symmetry_asymmetry(expr[0], expr[1], 0, domains)

            # Perform your assertions based on the expected output
            assert result[1] == 'אין סימטריה', "Expected 'אין סימטריה'"

    def test_make_poly(self):
        # Define the polynomial coefficients
        p = [2, 1, -3]

        # Call the makePoly function
        result = app.makePoly(p)

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
        expected_points = [(-1.0, 0.0), (1.0, 0.0), (2.0, 0.0)]

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
        np.testing.assert_allclose(np.round(result), expected_points)


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
        expected_result = "2x^2-3x+1"

        # Assert that the result matches the expected string representation of the polynomial
        self.assertEqual(result, expected_result)





if __name__ == '__main__':
    unittest.main()
