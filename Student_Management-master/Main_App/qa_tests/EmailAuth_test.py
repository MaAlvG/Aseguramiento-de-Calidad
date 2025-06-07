from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend, UserModel

from Main_App.EmailAuthentication import authenticate



class EmailAuth_test(TestCase):
    def setUp(self):
        # Crear usuarios de prueba para cada tipo
        self.admin_user = User.objects.create_user(
            username='admin@example.com',
            email='admin@example.com',
            password='adminpass123',
            user_type='1'
        )
        self.teacher_user = User.objects.create_user(
            username='teacher@example.com',
            email='teacher@example.com',
            password='teacherpass123',
            user_type='2'
        )
        self.student_user = User.objects.create_user(
            username='student@example.com',
            email='student@example.com',
            password='studentpass123',
            user_type='3'
        )

    def authenticate_user_succes(self):
        authenticated_user = authenticate(username='admin@example.com', password='adminpass')
        self.assertIsNotNone(authenticated_user)
        self.assertEqual(authenticated_user, self.user)

