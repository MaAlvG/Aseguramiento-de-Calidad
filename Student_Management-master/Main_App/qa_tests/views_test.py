from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from Main_App.models import MyUser
from Main_App.models import Teacher
from Main_App.models import Student
from unittest.mock import patch # para simular el comportamiento de los mensajes
from django.contrib import messages

User = get_user_model()

class ViewsTests(TestCase):
    def setUp(self):
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


    # ID: V-01
    # Descripción: Verificar que la vista loginpage se renderiza correctamente con la plantilla esperada.
    # Método a Probar: loginpage (GET)
    # Datos de la Prueba: Ninguno (vista pública)
    # Resultado Esperado: HTTP 200 y uso de plantilla 'loginpage.html'

    def test_loginpage_renders_correctly(self):
        response = self.client.get('')  # o usa reverse('loginpage') si tiene nombre en urls.py

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'loginpage.html')

    # ID: V-02
    # Descripción: Verificar poder iniciar sesion como un administrador verificado
    # Método a Probar: loginuser (POST)
    # Datos de la Prueba: {loginuser}
    # Resultado Esperado: HTTP 302 y uso de url '/adminhome'
    def test_loginuser_success_admin(self):
        response = self.client.post('/loginuser', {
            'email': 'admin@example.com',
            'password': 'adminpass123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/adminhome')


    # ID: V-03
    # Descripción: Verificar poder iniciar sesion como un profesor verificado
    # Método a Probar: loginuser (POST)
    # Datos de la Prueba: {loginuser}
    # Resultado Esperado: HTTP 302 y uso de url '/teacherhome'
    def test_loginuser_success_teacher(self):
        response = self.client.post('/loginuser', {
            'email': 'teacher@example.com',
            'password': 'teacherpass123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/teacherhome')

    # ID: V-04
    # Descripción: Verificar poder iniciar sesion como un estudiante verificado
    # Método a Probar: loginuser (POST)
    # Datos de la Prueba: {loginuser}
    # Resultado Esperado: HTTP 302 y uso de url '/studenthome'
    def test_loginuser_success_student(self):
        response = self.client.post('/loginuser', {
            'email': 'student@example.com',
            'password': 'studentpass123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/studenthome')

    # ID: V-05
    # Descripción: Verificar no poder iniciar sesion como un usuario no verificado
    # Método a Probar: loginuser (POST)
    # Datos de la Prueba: {loginuser}
    # Resultado Esperado: HTTP 302 y uso de url '/loginpage'
    def test_loginuser_invalid_credentials(self):
        response = self.client.post('/loginuser', {
            'email': 'fake@example.com',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/loginpage')

    # ID: V-06
    # Descripción: Verificar que se pueda cerrar sesion de un usuario verificado
    # Método a Probar: logoutuser (GET)
    # Datos de la Prueba: Ninguno (vista pública)
    # Resultado Esperado: HTTP 302 y el usuario deja de estar autenticado
    def test_logoutuser_redirects_and_logs_out(self):
        response = self.client.get('/logoutuser')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')

        response_after_logout = self.client.get('/')
        user = response_after_logout.wsgi_request.user
        self.assertFalse(user.is_authenticated)