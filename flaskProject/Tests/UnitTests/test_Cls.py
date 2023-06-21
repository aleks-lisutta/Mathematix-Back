import unittest
from pony.orm import db_session, Database
from flaskProject import app
from flaskProject.Tests.UnitTests import initiate_database
from flaskProject.app import DB, Cls



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

    def test_openClass_successful(self):
        # Add test data
        with db_session:
            app.register_buisness('John', 'password', 1)
            app.login_buisness('John', 'password')
        # Test that makeClass returns "successful" and status code 200
            response, status_code = app.openClass_buisness("John", "Math")

            self.assertEqual(response, "successful")
            self.assertEqual(status_code, 200)

            # Assert that the class was added to the database
            cls = Cls.get(name="Math")
            self.assertIsNotNone(cls)
            self.assertEqual(cls.teacher.name, "John")

    def test_openClass_same_name_fail(self):
        # Add test data
        with db_session:
            app.register_buisness('John', 'password', 1)
            app.login_buisness('John', 'password')
            # Test that makeClass returns "successful" and status code 200
            response, status_code = app.openClass_buisness("John", "Math")
            self.assertEqual(status_code, 200)
            # Try creating the same class again and assert that it raises an exception
            response, status_code = app.openClass_buisness("John", "Math")
            self.assertIn("Math already exists", response )
            self.assertEqual(status_code, 400)



    def test_makeClass_wrong_type(self):
        # Add test data
        with db_session:
            app.register_buisness('Alice', 'password', 2)
            app.login_buisness('Alice', 'password')
        # Test that makeClass returns "failed wrong type" and status code 400
            response, status_code = app.openClass_buisness("Alice", "Science")

            self.assertEqual(response, "failed wrong type")
            self.assertEqual(status_code, 400)

            # Assert that no class was added to the database
            cls = Cls.get(name="Science")
            self.assertIsNone(cls)

    def test_removeClass_not_teacher(self):
        with db_session:
            app.register_buisness('John', 'password', 2)
            app.login_buisness('John', 'password')
            app.openClass_buisness('teacher1', 'Math')


        # Test that removeClass returns "successful" and status code 200
        response, status_code = app.removeClass_buisness("John", "Math")
        self.assertEqual(response, "user John is not a teacher")
        self.assertEqual(status_code, 400)

    def test_removeClass_successful(self):
        with db_session:
            # Add test data
            app.register_buisness('John', 'password', 1)
            app.login_buisness('John', 'password')
            app.openClass_buisness('John', 'Math')
        # Test that removeClass returns "successful" and status code 200
        response, status_code = app.removeClass_buisness("John", "Math")
        self.assertEqual(response, "successful")
        self.assertEqual(status_code, 200)
        with db_session:
            # Assert that the class was removed from the database
            self.assertIsNone(Cls.get(name="Math"))


    def test_remove_nonexistent_class(self):
        # Test that attempting to remove a non-existent class returns "failed" and status code 400
        with db_session:
            app.register_buisness('John', 'password', 1)
            app.login_buisness('John', 'password')
            response, status_code = app.removeClass_buisness("John", "Science")
            self.assertEqual(response, "Cls['Science']")
            self.assertEqual(status_code, 400)

            # Test that attempting to remove a class with a non-matching teacher returns "failed" and status code 400
            app.register_buisness('Jane', 'password', 1)
            app.login_buisness('Jane', 'password')
            app.openClass_buisness('Jane', 'Science')
            response, status_code = app.removeClass_buisness("John", "Science")
            self.assertEqual(response, "failed")
            self.assertEqual(status_code, 400)

    def test_remove_class_twice(self):
        with db_session:
            # Add test data
            app.register_buisness('John', 'password', 1)
            app.login_buisness('John', 'password')
            app.openClass_buisness('John', 'Math')
        # Test that removeClass returns "successful" and status code 200
        app.removeClass_buisness("John", "Math")
        response, status_code = app.removeClass_buisness("John", "Math")
        self.assertEqual(response, "Cls['Math']")
        self.assertEqual(status_code, 400)
        with db_session:
            # Assert that the class was removed from the database
            self.assertIsNone(Cls.get(name="Math"))


    def test_editClass_successful(self):
        # Add test data
        with db_session:
            app.register_buisness('John', 'password', 1)
            app.login_buisness('John', 'password')
            app.openClass_buisness('John', 'Math')
            # Test that editClass returns "successful" and status code 200
            response, status_code = app.editClass_buisness("John", "Math", "Mathematics")

            self.assertEqual(response, "successful")
            self.assertEqual(status_code, 200)

            # Assert that the class was renamed in the database
            self.assertIsNotNone(Cls.get(name="Mathematics"))
            self.assertIsNone(Cls.get(name="Math"))



    def test_editClass_failed_nonexisting_teacher(self):
        # Test that attempting to edit a class with a non-existing teacher returns "failed" and status code 400
        with db_session:
            app.register_buisness('Jane', 'password', 1)
            app.login_buisness('Jane', 'password')
            app.openClass_buisness('Jane', 'Science')
            response, status_code = app.editClass_buisness("John", "Science", "History")

            self.assertEqual(response, "user John is not a teacher")
            self.assertEqual(status_code, 400)


    def test_editClass_failed_nonexisting_class(self):
        with db_session:
            app.register_buisness('John', 'password', 1)
            app.login_buisness('John', 'password')
            app.openClass_buisness('John', 'Math')
            # Test that attempting to edit a non-existent class returns "failed" and status code 400
            response, status_code = app.editClass_buisness("John", "Science", "Biology")
            self.assertEqual(response, "Cls['Science']")
            self.assertEqual(status_code, 400)

    def test_editClass_not_teacher(self):
        with db_session:
            # Type == 2
            app.register_buisness('John', 'password', 2)
            app.login_buisness('John', 'password')
            app.openClass_buisness('John', 'Math')

            # Test that editClass returns "successful" and status code 200
            response, status_code = app.editClass_buisness("John", "Math", "Mathematics")

            self.assertEqual(response, "user John is not a teacher")
            self.assertEqual(status_code, 400)
            cls = Cls.get(name="Mathematics")
            self.assertIsNone(cls)

    def test_editClass_userNotTeacher(self):
        # Test that attempting to edit a class with a user that is not logged in returns "user not logged in" and status code 400
        response, status_code = app.editClass_buisness("John", "Math", "Mathematics")
        self.assertEqual(response, "user John is not a teacher")
        self.assertEqual(status_code, 400)



    def test_approveStudentToClass(self):
        with db_session:
            with app.app.app_context():
                # Create teacher account and open a class
                app.register_buisness('teacher1', 'password', 1)
                app.login_buisness('teacher1', 'password')
                app.openClass_buisness('teacher1', 'class1')
                # Create student account and register to class
                app.register_buisness('student1', 'password', 2)
                app.login_buisness('student1', 'password')
                app.registerClass_buisness('student1', 'class1')
                app.approveStudentToClass_buisness('teacher1', 'student1', 'class1', 'True')
                result = app.Cls_User.select(lambda x: x.cls.name == 'class1' and x.user.name == 'student1')
                self.assertEqual((result[:].to_list()[0]).approved, True)

    def test_declineStudentToClass(self):
        with db_session:
            with app.app.app_context():
                # Create teacher account and open a class
                app.register_buisness('teacher1', 'password', 1)
                app.login_buisness('teacher1', 'password')
                app.openClass_buisness('teacher1', 'class1')
                # Create student account and register to class
                app.register_buisness('student1', 'password', 2)
                app.login_buisness('student1', 'password')
                app.registerClass_buisness('student1', 'class1')
                app.approveStudentToClass_buisness('teacher1', 'student1', 'class1', 'False')
                result = app.Cls_User.select(lambda x: x.cls.name == 'class1' and x.user.name == 'student1')

                self.assertEqual([] ,result[:].to_list())

    def test_approveStudentToClassAfterCancel(self):
        with db_session:
            with app.app.app_context():
                # Create teacher account and open a class
                app.register_buisness('teacher1', 'password', 1)
                app.login_buisness('teacher1', 'password')
                app.openClass_buisness('teacher1', 'class1')
                # Create student account and register to class
                app.register_buisness('student1', 'password', 2)
                app.login_buisness('student1', 'password')
                app.registerClass_buisness('student1', 'class1')
                app.removeRegistrationClass_Buisness("student1", "class1")
                # app.approveStudentToClass_buisness('teacher1', 'student1', 'class1', 'True')
                result = app.Cls_User.select(lambda x: x.cls.name == 'class1' and x.user.name == 'student1')
                self.assertEqual([] ,result[:].to_list())

    def test_declineStudentToClassAfterCancel(self):
        with db_session:
            with app.app.app_context():
                # Create teacher account and open a class
                app.register_buisness('teacher1', 'password', 1)
                app.login_buisness('teacher1', 'password')
                app.openClass_buisness('teacher1', 'class1')
                # Create student account and register to class
                app.register_buisness('student1', 'password', 2)
                app.login_buisness('student1', 'password')
                app.registerClass_buisness('student1', 'class1')
                app.removeRegistrationClass_Buisness("student1", "class1")
                # app.approveStudentToClass_buisness('teacher1', 'student1', 'class1', 'False')
                result = app.Cls_User.select(lambda x: x.cls.name == 'class1' and x.user.name == 'student1')
                self.assertEqual([] ,result[:].to_list())


    def test_openClass_success(self):
        with db_session:
            app.register_buisness('John Doe', 'password', 1)
            app.login_buisness('John Doe', 'password')
            result = app.openClass_buisness("John Doe", "English Class")

            # Verify the result
            self.assertEqual(result, ("successful", 200))

            # Verify that the class was created in the database
            cls = Cls.get(name="English Class")
            self.assertIsNotNone(cls)
            self.assertEqual(cls.teacher.name, "John Doe")

    def test_openClass_not_teacher(self):
        with db_session:
            #Type ==2
            app.register_buisness('John Doe', 'password', 2)
            app.login_buisness('John Doe', 'password')
            # Call the makeClass function
            result = app.openClass_buisness("John Doe", "English Class")

            # Verify the result
            self.assertEqual(('failed wrong type', 400), result)

            # Verify that the class not created in the database

            cls = Cls.get(name="English Class")
            self.assertIsNone(cls)


    def test_openClass_existing_name(self):
        with db_session:
            app.register_buisness('John Doe', 'password', 1)
            app.login_buisness('John Doe', 'password')
            # cls_record = Cls(name="Math", teacher=teacher, students=[], hasUnits=[])
            app.openClass_buisness("John Doe", "Math")
            result = app.openClass_buisness("John Doe", "Math")

            # Verify the result
            self.assertEqual(('Cannot create Cls: instance with primary key Math already exists', 400), result)

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

    # def test_getUnapprovedStudents_no_teacher_fail_successful(self):
    #     with app.app.app_context():
    #         # Check request
    #         res = app.getUnapprovedStudents_buisness('teacher1')
    #         self.assertEqual(200, res.status_code, 'Request failed')
    #         self.assertEqual(0, len(res.json), 'classes in list')

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




if __name__ == '__main__':
    unittest.main()
