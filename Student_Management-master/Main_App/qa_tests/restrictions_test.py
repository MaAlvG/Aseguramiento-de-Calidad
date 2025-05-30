from django.test import TestCase, RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from unittest.mock import Mock, patch
from Main_App.models import MyUser
from Main_App.restrictions import is_authenticated, is_admin, is_teacher, is_student


class RestrictionsTestCase(TestCase):
    # Configuracion de Pruebas
    def setUp(self):
        self.factory = RequestFactory()
        
        self.admin_user = MyUser.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='admin123',
            user_type='1'
        )
        self.teacher_user = MyUser.objects.create_user(
            username='teacher',
            email='teacher@test.com',
            password='profe123',
            user_type='2'
        )
        self.student_user = MyUser.objects.create_user(
            username='student',
            email='student@test.com',
            password='1234',
            user_type='3'
        )
        
        # Funcion mock para pruebas
        def dummy_view(request):
            return HttpResponse("Success")
        
        self.dummy_view = dummy_view

    # ID: RES-1
    # Descripcion: Es posible acceder con un usuario autenticado.
    # Metodo a Probar: @is_authenticated.
    # Datos de la Prueba: {admin_user, teacher_user, student_user}.
    # Resultado Esperado: Success accediendo con el usuario.
    def test_is_authenticated_with_authenticated_user(self):
        @is_authenticated
        def test_view(request):
            return HttpResponse("Success")
        
        request = self.factory.get('/')
        request.user = self.student_user
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Success")

    # ID: RES-2
    # Descripcion: Es posible acceder con un usuario autenticado.
    # Metodo a Probar: @is_authenticated.
    # Datos de la Prueba: N/A
    # Resultado Esperado: La pagina no permite la autenticacion y brinda una redireccion  "/loginpage".
    def test_is_authenticated_with_anonymous_user(self):
        @is_authenticated
        def test_view(request):
            return HttpResponse("Success")
        
        request = self.factory.get('/')
        request.user = AnonymousUser()
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/loginpage')

    # ID: RES-3
    # Descripcion: Es posible autenticar y permitir el acceso de una cuenta MyUser de tipo Admin.
    # Metodo a Probar: @is_admin.
    # Datos de la Prueba: {admin_user}
    # Resultado Esperado: Se detecta que el usuario es admin.
    def test_is_admin_with_admin_user(self):
        @is_admin
        def test_view(request):
            return HttpResponse("Admin Success")
        
        request = self.factory.get('/')
        request.user = self.admin_user
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Admin Success")

    # ID: RES-4
    # Descripcion: No es posible autenticar y permitir el acceso de una cuenta MyUser distinta de tipo a Admin.
    # Metodo a Probar: @is_admin.
    # Datos de la Prueba: {teacher_user, student_user}
    # Resultado Esperado: Se detecta que el usuario no es admin y lo redirige a una pagina indicando
    #   <h3>You are not authorised to view this page</h3>
    def test_is_admin_with_non_admin_user(self):
        @is_admin
        def test_view(request):
            return HttpResponse("Admin Success")
        
        request = self.factory.get('/')
        request.user = self.teacher_user
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("You are not authorised to view this page", response.content.decode())

    # ID: RES-5
    # Descripcion: No es posible autenticar y permitir el acceso sin una cuenta existente de MyUser.
    # Metodo a Probar: @is_admin.
    # Datos de la Prueba: MOCK
    #                       id: 9999
    # Resultado Esperado: Se detecta que el usuario no es admin y lo redirige a una pagina indicando
    #   <h3>You are not authorised to view this page.</h3>
    #
    # Nota del QA: Quiero restaltar que el autor original del codigo hizo dos respuestas que
    #               solo se diferencian por un . al final.
    def test_is_admin_with_nonexistent_user(self):
        @is_admin
        def test_view(request):
            return HttpResponse("Admin Success")
        
        # Crear un mock user que no existe en MyUser
        mock_user = Mock()
        mock_user.id = 9999  # ID que no existe
        
        request = self.factory.get('/')
        request.user = mock_user
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("You are not authorised to view this page.", response.content.decode())

    # ID: RES-6
    # Descripcion: Corroborar que una cuenta MyUser de tipo Teacher sea valida.
    # Metodo a Probar: @is_teacher.
    # Datos de la Prueba: {teacher_user}
    # Resultado Esperado: Exito en la comprobacion para la cuenta.
    def test_is_teacher_with_teacher_user(self):
        @is_teacher
        def test_view(request):
            return HttpResponse("Teacher Success")
        
        request = self.factory.get('/')
        request.user = self.teacher_user
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Teacher Success")

    # ID: RES-7
    # Descripcion: Corroborar que una cuenta MyUser de tipo distinto a Teacher sea invalida y redirigida.
    # Metodo a Probar: @is_teacher.
    # Datos de la Prueba: {admin_user, student_user}
    # Resultado Esperado: Exito en la comprobacion para la cuenta y se redirecciona a una pagina con el mensaje.
    #      "<h3>You are not authorised to view this page</h3>" 
    def test_is_teacher_with_non_teacher_user(self):
        """Test: Usuario no teacher es rechazado"""
        @is_teacher
        def test_view(request):
            return HttpResponse("Teacher Success")
        
        request = self.factory.get('/')
        request.user = self.admin_user
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("You are not authorised to view this page", response.content.decode())

    # ID: RES-8
    # Descripcion: Corroborar que no se pueda acceder con permisos de Teacher sin cuenta MyUser.
    # Metodo a Probar: @is_teacher.
    # Datos de la Prueba: MOCK
    #                       id: 9999
    # Resultado Esperado: Exito en la comprobacion para la cuenta y se redirecciona a una pagina con el mensaje.
    #      "<h3>You are not authorised to view this page.</h3>" 
    # Nota del QA: Quiero restaltar que el autor original del codigo hizo dos respuestas que
    #               solo se diferencian por un . al final, este error parece repetirse en mas respuestas, por
    #               lo cual no se enfatizara nuevamente.
    def test_is_teacher_with_nonexistent_user(self):
        @is_teacher
        def test_view(request):
            return HttpResponse("Teacher Success")
        
        mock_user = Mock()
        mock_user.id = 9999
        
        request = self.factory.get('/')
        request.user = mock_user
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("You are not authorised to view this page.", response.content.decode())

    # ID: RES-9
    # Descripcion: Corroborar que una cuenta MyUser de tipo Student sea valida.
    # Metodo a Probar: @is_student.
    # Datos de la Prueba: {student_user}
    # Resultado Esperado: Exito en la comprobacion para la cuenta.
    def test_is_student_with_student_user(self):
        @is_student
        def test_view(request):
            return HttpResponse("Student Success")
        
        request = self.factory.get('/')
        request.user = self.student_user
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Student Success")

    # ID: RES-10
    # Descripcion: Corroborar que una cuenta MyUser de tipo distinto a Student sea invalida y redirigida.
    # Metodo a Probar: @is_student.
    # Datos de la Prueba: {admin_user, teacher_user}
    # Resultado Esperado: Exito en la comprobacion para la cuenta y se redirecciona a una pagina con el mensaje.
    #      "<h3>You are not authorised to view this page</h3>" 
    def test_is_student_with_non_student_user(self):
        @is_student
        def test_view(request):
            return HttpResponse("Student Success")
        
        request = self.factory.get('/')
        request.user = self.admin_user
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("Log in as student to view this page", response.content.decode())

    # ID: RES-11
    # Descripcion: Corroborar que no se pueda acceder con permisos de Teacher sin cuenta MyUser.
    # Metodo a Probar: @is_student.
    # Datos de la Prueba: MOCK
    #                       id: 9999
    # Resultado Esperado: Exito en la comprobacion para la cuenta y se redirecciona a una pagina con el mensaje.
    #      "<h3>You are not authorised to view this page.</h3>" 
    def test_is_student_with_nonexistent_user(self):
        """Test: Usuario que no existe en MyUser es rechazado"""
        @is_student
        def test_view(request):
            return HttpResponse("Student Success")
        
        mock_user = Mock()
        mock_user.id = 9999
        
        request = self.factory.get('/')
        request.user = mock_user
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("Log in as student to view this page", response.content.decode())

    # ID: RES-12
    # Descripcion: Corroborar preservacion de los datos incluidos a is_authenticated.
    # Metodo a Probar: @is_authenticated
    # Datos de la Prueba:
    #   arg1 = pan
    #   arg2 = pan
    #   kwarg = jamon
    # Resultado Esperado:
    def test_decorators_preserve_function_arguments(self):
        @is_authenticated
        def test_view_with_args(request, arg1, arg2, kwarg1=None):
            return HttpResponse(f"Args: {arg1}, {arg2}, {kwarg1}")
        
        request = self.factory.get('/')
        request.user = self.admin_user
        
        response = test_view_with_args(request, "pan", "queso", kwarg1="jamon")
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("Args: pan, queso, jamon", response.content.decode())

    # ID: RES-13
    # Descripcion: Comprobar que se pueden aplicar combinaciones de decoradores de restrictions.py
    # Metodo a Probar: @is_authenticated, {@is_admin, @is_teacher, @is_student}
    # Datos de la Prueba: {admin_user, teacher_user, student_user}
    # Resultado Esperado:
    # Nota del QA: @is_admin, @is_teacher y @is_student se pueden considerar de una misma clase de metodo
    #                para el contexto de la prueba y estos no se esperan que se combinen entre si.
    def test_multiple_decorators_combination(self):
        @is_authenticated
        @is_admin
        def test_view(request):
            return HttpResponse("Authenticated and Role decorators success")
        
        request = self.factory.get('/')
        request.user = self.admin_user
        
        response = test_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Authenticated and Role decorators success")
        
    # Limpieza de basura despues de cada test.
    def tearDown(self):
        MyUser.objects.all().delete()