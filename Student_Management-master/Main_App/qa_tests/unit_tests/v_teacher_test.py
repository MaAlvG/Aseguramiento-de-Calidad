from django.test import TestCase, Client
from django.urls import reverse
from Main_App.models import MyUser
from Main_App.models import Teacher
from Main_App.models import Student
from unittest.mock import patch # para simular el comportamiento de los mensajes
from django.contrib import messages # para inspecccionar los mensajes
from Main_App.models import Notification # para pruebas de notificaciones
from django.core.files.uploadedfile import SimpleUploadedFile
from Main_App.models import Result
from Main_App.models import Notes
from unittest.mock import patch


class TeacherViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher_user = MyUser.objects.create_user(
            username='profe', password='clave123', user_type=2
        )
        # evitar conflicto si ya existe una instancia Teacher con ese admin
        if not Teacher.objects.filter(admin=self.teacher_user).exists(): 
            Teacher.objects.create(admin=self.teacher_user, address='San José', gender='Female') 

        self.admin_user = MyUser.objects.create_user( # usuario administrador para pruebas
            username='admin', password='admin123', user_type=1
        )

    # ID: VTCH-1
    # Descripcion: Revisar que un usuario NO autenticado es redirigido al intentar
    # acceder a la vista t_home (proteccion @is_authenticated + @is_teacher).
    # Metodo a Probar: t_home (GET)
    # Datos de la Prueba: {AnonymousUser}
    # Resultado Esperado: El sistema redirige a /loginpage (HTTP 302)
    def test_t_home_unauthenticated_user_redirects_to_login(self):
        response = self.client.get(reverse('t_home'))  # sin iniciar sesión

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/loginpage')

    # ID: VTCH-2
    # Descripcion: Revisar que un usuario con rol de profesor puede acceder a la vista t_home.
    # Metodo a Probar: t_home (GET)
    # Datos de la Prueba: {teacher_user}
    # Resultado Esperado: El sistema permite el acceso a la vista, devuelve HTTP 200, 
    # entonces sabemos que la vista es accesible para el rol de profesor
    def test_t_home_status_code(self):
        self.client.force_login(self.teacher_user)
        response = self.client.get(reverse('t_home'))
        self.assertEqual(response.status_code, 200)
    
    # ID: VTCH-3
    # Descripcion: Revisar que una cuenta que no sea Teacher no tenga acceso a vista t_home.
    # Metodo a Probar: t_home (GET)
    # Datos de la Prueba: {student_user, admin_user}
    # Resultado Esperado: El sistema no permite el acceso a la vista, devuelve HTTP 302, 
    # entonces sabemos que la vista es inaccesible. Ademas redirige a /loginpage.
    def test_t_home_not_teacher_user(self):
        student_user = MyUser.objects.create_user(
            username='est_no_teacher', password='pwd2003', user_type=3
        )
        self.client.login(username=student_user.username, 
                          password=student_user.password)
        
        response = self.client.get(reverse('t_home'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/loginpage')

    # ID: VTCH-4
    # Descripcion: Revisar que un usuario con rol de profesor puede acceder a la vista t_profile.
    # Metodo a Probar: t_profile (GET)
    # Datos de la Prueba: {teacher_user}
    # Resultado Esperado: Se devuelve un 200 y se renderiza la info del perfil, 
    # resvisando que el usuario tiene un objeto Teacher relacionado y permisos suficientes
    def test_t_profile_view(self):
        self.client.force_login(self.teacher_user)
        response = self.client.get(reverse('t_profile'))
        self.assertEqual(response.status_code, 200)

    # ID: VTCH-5
    # Descripcion: Revisar que un profesor puede actualizar exitosamente los campos editables de su perfil.
    # Metodo a Probar: t_saveprofile (POST)
    # Datos de la Prueba: {teacher_user, post_data}
    # Resultado Esperado: Se actualiza el perfil del profesor con los nuevos datos, 
    # el sistema redirige a la vista del perfil sin error
    def test_t_saveprofile_post_success(self):
        self.client.force_login(self.teacher_user)
        post_data = {
            'teacher_id': self.teacher_user.id,
            'firstname': 'Carlos',
            'lastname': 'Mendez',
            'email': 'carlos.mendez@test.com',
            'address': 'Alajuela',
            'gender': 'Male',
            'password': ''
        }
        response = self.client.post('/t_saveprofile', data=post_data)

        self.assertEqual(response.status_code, 302)  # redireccion despues de guardar

        updated_teacher = MyUser.objects.get(id=self.teacher_user.id)
        self.assertEqual(updated_teacher.first_name, 'Carlos')
        self.assertEqual(updated_teacher.last_name, 'Mendez')
        self.assertEqual(updated_teacher.email, 'carlos.mendez@test.com')

        teacher_profile = Teacher.objects.get(admin=updated_teacher)
        self.assertEqual(teacher_profile.address, 'Alajuela')
        self.assertEqual(teacher_profile.gender, 'Male')

    # ID: VTCH-6
    # Descripcion: Revisar que un usuario con rol de profesor puede acceder a la vista t_addstudent.
    # Metodo a Probar: t_addstudent (GET)
    # Datos de la Prueba: {teacher_user}
    # Resultado Esperado: Se devuelve un 200 y se renderiza la vista correspondiente con lo que se espera que nos muestre
    # los generos, niveles y mediums disponibles
    def test_t_addstudent_view_get(self):
        self.client.force_login(self.teacher_user)
        response = self.client.get('/t_addstudent/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'teacher/t_addstudent.html')
        self.assertIn('genders', response.context)
        self.assertIn('stds', response.context)
        self.assertIn('mediums', response.context)

    # ID: VTCH-7
    # Descripcion: Revisar que se puede crear un estudiante desde la vista t_savestudent con POST.
    # Metodo a Probar: t_savestudent (POST)
    # Datos de la Prueba: {teacher_user, student_data}
    # Resultado Esperado: Se crea bien el usuario tipo estudiante y su registro en el modelo Student
    def test_t_savestudent_post_creates_student(self):
        self.client.force_login(self.teacher_user)
        post_data = {
            'firstname': 'Alejandro',
            'lastname': 'Gomez',
            'email': 'est1@test.com',
            'address': 'Cartago',
            'gender': 'Male',
            'std': '10',
            'medium': 'English'
        }

        response = self.client.post('/t_savestudent', data=post_data)

        self.assertEqual(response.status_code, 302)  # redireccion despues de guardar

        created_user = MyUser.objects.filter(user_type=3, email='est1@test.com').first()
        self.assertIsNotNone(created_user)
        self.assertEqual(created_user.first_name, 'Alejandro')
        self.assertEqual(created_user.last_name, 'Gomez')

        student_profile = Student.objects.get(admin=created_user)
        self.assertEqual(student_profile.address, 'Cartago')
        self.assertEqual(student_profile.gender, 'Male')
        self.assertEqual(student_profile.std, '10')
        self.assertEqual(student_profile.medium, 'English')

    # ID: VTCH-8
    # Descripcion: Revisar que un usuario con rol de profesor puede acceder a la vista t_viewstudent.
    # Metodo a Probar: t_viewstudent (GET)
    # Datos de la Prueba: {teacher_user}
    # Resultado Esperado: El sistema permite el acceso a la vista, 
    # devuelve HTTP 200 y renderiza bien la lista de estudiantes
    def test_t_viewstudent_status_code(self):
        self.client.force_login(self.teacher_user)
        response = self.client.get('/t_viewstudent/')
        self.assertEqual(response.status_code, 200)
    
    # ID: VTCH-9
    # Descripcion: Un usuario con rol Teacher accede a t_addnotification.
    # Metodo a Probar: t_addnotification (GET)
    # Datos de la Prueba: {teacher_user}
    # Resultado Esperado: HTTP 200 y se renderiza 'teacher/t_addnotification.html'
    def test_t_addnotification_teacher_access(self):
        self.client.force_login(self.teacher_user)
        response = self.client.get('/t_addnotification/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'teacher/t_addnotification.html')

    # ID: VTCH-10
    # Descripcion: Un usuario autenticado pero que no sea Teacher es rechazado.
    # Metodo a Probar: t_addnotification (GET)
    # Datos de la Prueba: {admin_user}
    # Resultado Esperado: HTTP 200 con mensaje “You are not authorised to view this page”
    def test_t_addnotification_non_teacher_denied(self):
        self.client.force_login(self.admin_user)
        response = self.client.get('/t_addnotification/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "You are not authorised to view this page",
            response.content.decode()
        )

    # ID: VTCH-11
    # Descripcion: Un usuario anonimo es redirigido a /loginpage.
    # Metodo a Probar: t_addnotification (GET)
    # Datos de la Prueba: {AnonymousUser}
    # Resultado Esperado: HTTP 302 y redireccion a '/loginpage'
    def test_t_addnotification_anonymous_redirect(self):
        # asegurarse de estar sin sesion
        self.client.logout()
        response = self.client.get('/t_addnotification/', follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/loginpage')

    # ID: VTCH-12
    # Descripcion: Verificar que un profesor pueda crear una notificacion con un POST valido.
    # Metodo a Probar: t_savenotification (POST)
    # Datos de la Prueba: {teacher_user, heading='Examen', message='El examen sera el lunes'}
    # Resultado Esperado: Se crea un registro en Notification, se añade el mensaje de éxito y
    # se redirige a /t_addnotification (HTTP 302)
    def test_t_savenotification_post_success(self):
        self.client.force_login(self.teacher_user)

        post_data = {
            'heading': 'Examen',
            'message': 'El examen sera el lunes'
        }
        response = self.client.post('/t_savenotification', data=post_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/t_addnotification')

        notif = Notification.objects.filter(heading='Examen', message='El examen sera el lunes', created_by=self.teacher_user.username).first()
        self.assertIsNotNone(notif)

        storage = list(messages.get_messages(response.wsgi_request))
        self.assertTrue(any(m.message == "Notification added successfully" for m in storage))

    # ID: VTCH-13
    # Descripcion: Confirmar que el metodo responda “Method not Allowed..!” cuando se
    # accede con GET en vez de POST.
    # Metodo a Probar: t_savenotification (GET)
    # Datos de la Prueba: {teacher_user}
    # Resultado Esperado: Respuesta HTTP 200 con el texto “Method not Allowed..!”
    def test_t_savenotification_get_not_allowed(self):
        self.client.force_login(self.teacher_user)

        response = self.client.get('/t_savenotification') # intento de acceso con GET

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Method not Allowed..!")

    # ID: VTCH-14
    # Descripcion: Simular un error interno al crear la notificacion y ver que se
    # muestra el mensaje de error y se redirige bien.
    # Metodo a Probar: t_savenotification (POST)
    # Datos de la Prueba: {teacher_user, heading='Falla', message='esto no deberia guardarse'} + mock para forzar excepción
    # Resultado Esperado: No se crea el registro, que tire el mensaje “Failed to add Notification”
    # y se redirija a /t_addnotification (HTTP 302)
    def test_t_savenotification_post_exception_path(self):
        self.client.force_login(self.teacher_user)

        with patch('Main_App.v_teacher.Notification.objects.create', side_effect=Exception("DB down")):
            post_data = {'heading': 'Falla', 'message': 'esto no deberia guardarse'}
            response = self.client.post('/t_savenotification', data=post_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/t_addnotification')

        self.assertFalse(Notification.objects.filter(heading='Falla').exists()) # no se debe crear la notificacion

        storage = list(messages.get_messages(response.wsgi_request))
        self.assertTrue(any(m.message == "Failed to add Notification" for m in storage)) # mensaje de error esperado

    # ID: VTCH-15
    # Descripcion: Revisa que un usuario con rol Teacher pueda acceder a la vista t_deletenotification
    # y que las notificaciones creadas por ese usuario se incluyen en el contexto.
    # Metodo a Probar: t_deletenotification (GET)
    # Datos de la Prueba: {teacher_user}
    # Resultado Esperado: Respuesta HTTP 200, uso del template 'teacher/t_deletenotification.html',
    # y que en el contexto se incluyan las notificaciones creadas por el usuario autenticado
    def test_t_deletenotification_view(self):
        self.client.force_login(self.teacher_user)

        # creamos una notificacion asociada al usuario teacher
        Notification.objects.create(
            heading='Tarea',
            message='Entregar el martes',
            created_by=self.teacher_user.username
        )

        response = self.client.get('/t_deletenotification/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'teacher/t_deletenotification.html')
        self.assertIn('notifications', response.context)
        self.assertEqual(len(response.context['notifications']), 1)
        self.assertEqual(response.context['notifications'][0].created_by, self.teacher_user.username)

    # ID: VTCH-16
    # Descripcion: Revisamos que si ocurre un error al obtener las notificaciones (como un fallo en base de datos)
    # la vista t_deletenotification aun responde bien con el template esperado, sin romperlo
    # Metodo a Probar: t_deletenotification (GET)
    # Datos de la Prueba: {teacher_user} + mock para lanzar excepcion
    # Resultado Esperado: La vista devuelve HTTP 200 usando el mismo template pero no con 'notifications'
    @patch('Main_App.v_teacher.Notification.objects.filter', side_effect=Exception("DB fail")) # simulamos un error al obtener las notificaciones
    def test_t_deletenotification_exception_path(self, mock_filter): # mock_filter simula el fallo
        self.client.force_login(self.teacher_user)

        response = self.client.get('/t_deletenotification/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'teacher/t_deletenotification.html')
        # como hubo excepcion, 'notifications' no esta en el contexto
        self.assertNotIn('notifications', response.context)

    # ID: VTCH-17
    # Descripcion: Revisamos que un usuario con rol de profesor puede eliminar bien una notificacion
    # Metodo a Probar: t_removenotification (GET)
    # Datos de la Prueba: {teacher_user, notification_id valido}
    # Resultado Esperado: Se elimina la notificacion, se muestra mensaje de exito y redirige a /t_deletenotification
    def test_t_removenotification_success(self):
        self.client.force_login(self.teacher_user)

        notif = Notification.objects.create(
            heading='Eliminar',
            message='Notificación de prueba para borrar',
            created_by=self.teacher_user.username
        )

        response = self.client.get(f'/t_removenotification/{notif.id}')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/t_deletenotification')

        # ver que fue eliminada
        self.assertFalse(Notification.objects.filter(id=notif.id).exists())

        # ver mensaje de éxito
        storage = list(messages.get_messages(response.wsgi_request))
        self.assertTrue(any(m.message == "Notification deleted successfully" for m in storage))

    # ID: VTCH-18
    # Descripcion: Revisamos que si pasa un error al eliminar una notificacion en t_removenotification,
    # se maneje bien mostrando el mensaje de error y redirigiendo sin romper la ejecucion.
    # Metodo a Probar: t_removenotification (GET)
    # Datos de la Prueba: {teacher_user, notification_id valido} + mock que fuerza excepcion al hacer delete()
    # Resultado Esperado: No se elimina, se lanza mensaje de error y se redirige a /t_deletenotification
    @patch('Main_App.v_teacher.Notification.delete', side_effect=Exception("Fallo al eliminar")) # simulamos un fallo al eliminar
    def test_t_removenotification_exception_path(self, mock_delete):
        self.client.force_login(self.teacher_user)

        notif = Notification.objects.create(
            heading='Va a fallar',
            message='Simulacion de error en delete',
            created_by=self.teacher_user.username
        )

        with patch.object(Notification, 'delete', side_effect=Exception("Fallo al eliminar")):
            response = self.client.get(f'/t_removenotification/{notif.id}')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/t_deletenotification')

        # ver que no fue eliminada
        self.assertTrue(Notification.objects.filter(id=notif.id).exists())

        # ver mensaje de error
        storage = list(messages.get_messages(response.wsgi_request))
        self.assertTrue(any(m.message == "Failed to delete Notification" for m in storage))

    # ID: VTCH-19
    # Descripcion: Revisamos que un usuario con rol de profesor puede acceder a la vista t_viewnotification,
    # y que las notificaciones existentes se cargan bien
    # Metodo a Probar: t_viewnotification (GET)
    # Datos de la Prueba: {teacher_user}
    # Resultado Esperado: HTTP 200, uso del template esperado, y que salgan las notificaciones del usuario
    def test_t_viewnotification_success(self):
        self.client.force_login(self.teacher_user)

        # creamos una notificacion asociada al usuario teacher
        Notification.objects.create(
            heading='Aviso importante',
            message='Examen el viernes',
            created_by=self.teacher_user.username
        )

        response = self.client.get('/t_viewnotification/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'teacher/t_viewnotification.html')
        self.assertIn('notifications', response.context)
        self.assertEqual(len(response.context['notifications']), 1)
        self.assertEqual(response.context['notifications'][0].created_by, self.teacher_user.username) # ver que la notificacion sea del profesor

    # ID: VTCH-20
    # Descripcion: Revisamos que si ocurre un error al obtener las notificaciones (como un fallo en la base de datos)
    # la vista t_viewnotification responde bien mostrando el template sin romperse
    # Metodo a Probar: t_viewnotification (GET)
    # Datos de la Prueba: {teacher_user} + simulacion de excepcion con mock
    # Resultado Esperado: HTTP 200, uso del template esperado y ausencia del contexto 'notifications'
    @patch('Main_App.v_teacher.Notification.objects.all', side_effect=Exception("DB error")) # simulamos un error al obtener las notificaciones
    def test_t_viewnotification_exception_path(self, mock_all):
        self.client.force_login(self.teacher_user)

        response = self.client.get('/t_viewnotification/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'teacher/t_viewnotification.html')
        self.assertNotIn('notifications', response.context)

    # ID: VTCH-21
    # Descripcion: Revisamos que un usuario con rol de profesor pueda acceder bien a la vista t_addresult,
    # y que se carguen las listas de niveles academicos (stds) y mediums en el contexto.
    # Metodo a Probar: t_addresult (GET)
    # Datos de la Prueba: {teacher_user}
    # Resultado Esperado: HTTP 200, uso del template esperado, y que salgan de 'stds' y 'mediums' en el contexto
    def test_t_addresult_view(self):
        self.client.force_login(self.teacher_user)

        response = self.client.get('/t_addresult/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'teacher/t_addresult.html')
        self.assertIn('stds', response.context)
        self.assertIn('mediums', response.context)

    # ID: VTCH-22
    # Descripcion: Revisamos que si se accede a t_saveresult con un metodo distinto a POST (como GET),
    # el sistema devuelve un mensaje dcieindo que el metodo no esta permitido.
    # Metodo a Probar: t_saveresult (GET)
    # Datos de la Prueba: {teacher_user}
    # Resultado Esperado: Respuesta HTTP 200 con el texto “Method not Allowed..!”
    def test_t_saveresult_get_not_allowed(self):
        self.client.force_login(self.teacher_user)

        response = self.client.get('/t_saveresult')  # acceso con metodo GET

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Method not Allowed..!")

    # ID: VTCH-23
    # Descripcion: Revisamos que un profesor pueda subir bien un resultado usando POST
    # Metodo a Probar: t_saveresult (POST)
    # Datos de la Prueba: {teacher_user, title='Examen Final', medium='English', std='10', archivo PDF}
    # Resultado Esperado: Se guarda un nuevo objeto Result y se redirige con mensaje de exito
    def test_t_saveresult_post_success(self):
        self.client.force_login(self.teacher_user)

        fake_file = SimpleUploadedFile("test.pdf", b"contenido del archivo", content_type="application/pdf") # archivo simulado

        post_data = {
            'title': 'Examen Final',
            'medium': 'English',
            'std': '10',
            'resultfile': fake_file
        }

        response = self.client.post('/t_saveresult', data=post_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/t_addresult')

        result = Result.objects.filter(title='Examen Final', created_by=self.teacher_user.username).first()
        self.assertIsNotNone(result)
        self.assertEqual(result.medium, 'English')
        self.assertEqual(result.std, '10')

    # ID: VTCH-24
    # Descripcion: Revisamos que si pasa un error al intentar subir el resultado (como falla al crear el objeto),
    # el sistema muestre un mensaje de error y redirija bien a /t_addresult
    # Metodo a Probar: t_saveresult (POST)
    # Datos de la Prueba: {teacher_user, titulo, medium, std, archivo PDF, mock de excepcion}
    # Resultado Esperado: No se guarda el resultado, se muestra mensaje de error, y redirige a /t_addresult
    def test_t_saveresult_post_exception_path(self):
        self.client.force_login(self.teacher_user)

        with patch('Main_App.v_teacher.Result.objects.create', side_effect=Exception("Error interno")): # simulamos un fallo al crear el objeto Result
            fake_file = SimpleUploadedFile("fallo.pdf", b"contenido", content_type="application/pdf") # archivo simulado

            post_data = {
                'title': 'Fallido',
                'medium': 'Español',
                'std': '9',
                'resultfile': fake_file
            }

            response = self.client.post('/t_saveresult', data=post_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/t_addresult')

        storage = list(messages.get_messages(response.wsgi_request))
        self.assertTrue(any("Failed to upload result" in m.message for m in storage))

    # ID: VTCH-25
    # Descripcion: Revisamos que un usuario con rol de profesor puede acceder a la vista t_viewresult y
    # que se renderiza bien la plantilla junto con la lista de resultados disponibles
    # Metodo a Probar: t_viewresult (GET)
    # Datos de la Prueba: {teacher_user}
    # Resultado Esperado: HTTP 200, uso de plantilla 'teacher/t_viewresult.html' y contexto tiene 'results'
    def test_t_viewresult_renders_correctly(self):
        self.client.force_login(self.teacher_user)

        Result.objects.create(title="Res 1", file="file1.pdf", std="10", medium="English", created_by="profe") # simulamos resultados
        Result.objects.create(title="Res 2", file="file2.pdf", std="9", medium="Spanish", created_by="profe")

        response = self.client.get('/t_viewresult/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'teacher/t_viewresult.html')
        self.assertIn('results', response.context)
        self.assertEqual(len(response.context['results']), 2)

    # ID: VTCH-26
    # Descripción: Verificamos que un profesor puede resetear la contraseña de un estudiante exitosamente
    # Método a Probar: t_resetspass (GET)
    # Datos de la Prueba: {teacher_user, student_user}
    # Resultado Esperado: Redirección a /t_viewstudent, contraseña del estudiante cambia y aparece mensaje de éxito
    def test_t_resetspass_success(self):
        self.client.force_login(self.teacher_user)
        
        student = MyUser.objects.create_user(username='student1', password='original123')

        response = self.client.get(reverse('t_resetspass', args=[student.id]))

        self.assertRedirects(response, reverse('t_viewstudent'))
        
        student.refresh_from_db()
        self.assertTrue(student.check_password('Student@100'))

    # ID: VTCH-27
    # Descripción: Verifica que un profesor autenticado puede acceder a la vista t_deleteresult y que se muestran los resultados creados por él.
    # Método a Probar: t_deleteresult (GET)
    # Datos de la Prueba: {teacher_user, resultados creados por el usuario}
    # Resultado Esperado: HTTP 200, uso de plantilla 'teacher/t_deleteresult.html', contexto contiene resultados creados por el profesor

    def test_t_deleteresult_renders_results_correctly(self):
        self.client.force_login(self.teacher_user)

        Result.objects.create(title="Res A", file="fileA.pdf", std="10", medium="English", created_by=self.teacher_user.username)
        Result.objects.create(title="Res B", file="fileB.pdf", std="9", medium="Spanish", created_by="Andres_Viquez")

        response = self.client.get(reverse('t_deleteresult'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'teacher/t_deleteresult.html')
        self.assertIn('results', response.context)
        self.assertEqual(len(response.context['results']), 1)
        self.assertEqual(response.context['results'][0].created_by, self.teacher_user.username)


    # ID: VTCH-28
    # Descripción: Verifica que un profesor puede eliminar un resultado correctamente a través de la vista t_removeresult
    # Método a Probar: t_removeresult (GET)
    # Datos de la Prueba: {teacher_user, resultado creado}
    # Resultado Esperado: redirección a '/t_deleteresult', mensaje de éxito, y el resultado eliminado de la base de datos

    def test_t_removeresult_deletes_result(self):
        self.client.force_login(self.teacher_user)

        result = Result.objects.create(title="Res C", file="fileC.pdf", std="11", medium="English", created_by=self.teacher_user.username)

        response = self.client.get(reverse('t_removeresult', args=[result.id]))

        self.assertRedirects(response, reverse('t_deleteresult'))
        self.assertFalse(Result.objects.filter(id=result.id).exists())

    
    # ID: VTCH-29
    # Descripción: Verifica la ocurrencia de un error a la hora de intentar eliminar un resultado a traver de t_removeresult
    # Método a Probar: excepcion en t_removeresult (GET) 
    # Datos de la Prueba: {teacher_user, resultado creado}
    # Resultado Esperado: redirección a '/t_deleteresult' y mensaje de fallo
    def test_t_removeresult_deletes_result_error(self):
        self.client.force_login(self.teacher_user)

        result = Result.objects.create(
            title="Test Result",
            file="dummy.pdf",
            std="10",
            medium="CBSE",
            created_by=self.teacher_user.username
        )

        with patch.object(Result, 'delete', side_effect=Exception("Error simulado")):
            response = self.client.get(reverse('t_removeresult', args=[result.id]))

        self.assertRedirects(response, reverse('t_deleteresult'))

        messages = list(response.wsgi_request._messages)
        self.assertTrue(
            any("Failed to delete result" in str(m.message) for m in messages)
        )
    
    # ID: VTCH-30
    # Descripción: Verificamos que un usuario con rol de profesor pueda acceder a la vista t_addnotes
    # Método a Probar: t_addnotes (GET)
    # Datos de la Prueba: {self.client}
    # Resultado Esperado: HTTP 200, uso de plantilla 'teacher/t_addnotes.html' y contexto contiene 'notes'
    def test_t_addnotes_view(self):
        self.client.force_login(self.teacher_user)

        response = self.client.get('/t_addnotes/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'teacher/t_addnotes.html')
        self.assertIn('stds', response.context)
        self.assertIn('mediums', response.context)


    # ID: VTCH-31
    # Descripción: Verificamos que un usuario con rol de profesor pueda guardar un registro de notass
    # Método a Probar: t_savenotes (GET)
    # Datos de la Prueba: {post_data}
    # Resultado Esperado: El registro de notas existe, y se puede acceder a su informacion
    def test_t_savenotes_post_success(self):
        self.client.force_login(self.teacher_user)

        fake_notes = SimpleUploadedFile("testNotes.pdf", b"contenido del archivo", content_type="application/pdf")

        post_data = {
            'title': 'Notas Examen Final',
            'medium': 'English',
            'std': '10',
            'notes': fake_notes  
        }

        response = self.client.post('/t_savenotes', data=post_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/t_addnotes')

        note = Notes.objects.filter(title='Notas Examen Final', created_by=self.teacher_user.username).first()
        self.assertIsNotNone(note)
        self.assertEqual(note.medium, 'English')
        self.assertEqual(note.std, '10')

    # ID: VTCH-32
    # Descripción: Verificar la ocurrencia de un error al intentar guardar un registro de notas desde t_savenotes
    # Método a Probar: excepcion en t_savenotes (GET)
    # Datos de la Prueba: {post_data}
    # Resultado Esperado: codigo de erspuesta 302, y un mensaje de error
    def test_t_savenotes_exception(self):
        self.client.force_login(self.teacher_user)

        fake_notes = SimpleUploadedFile("testNotes.pdf", b"contenido", content_type="application/pdf")

        post_data = {
            'title': 'Notas Error',
            'medium': 'English',
            'std': '10',
            'notes': fake_notes
        }

        with patch('Main_App.models.Notes.objects.create', side_effect=Exception("Simulated error")):
            response = self.client.post(reverse('t_savenotes'), data=post_data)

        self.assertEqual(response.status_code, 302)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any("Failed to upload Notes" in str(m.message) for m in messages))

    
    # ID: VTCH-33
    # Descripción: Verificamos que un usuario con rol de profesor pueda acceder a la vista t_deletenotes,
    # y que la plantilla se renderice correctamente con las notas creadas por ese usuario.
    # Método a Probar: t_deletenotes (GET)
    # Datos de la Prueba: {teacher_user}
    # Resultado Esperado: HTTP 200, uso de plantilla 'teacher/t_deletenotes.html' y contexto contiene 'notes'
    def test_t_deletenotes_succes(self):
        self.client.force_login(self.teacher_user)

        Notes.objects.create(
            title="Nota 1",
            file=SimpleUploadedFile("nota1.pdf", b"contenido", content_type="application/pdf"),
            std="10",
            medium="CBSE",
            created_by=self.teacher_user.username  # coincide con la vista
        )

        Notes.objects.create(
            title="Nota 2",
            file=SimpleUploadedFile("nota2.pdf", b"contenido", content_type="application/pdf"),
            std="9",
            medium="CBSE",
            created_by=self.teacher_user.username
        )

        response = self.client.get('/t_deletenotes/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'teacher/t_deletenotes.html')
        self.assertIn('notes', response.context)
        self.assertEqual(len(response.context['notes']), 2)

    # ID: VTCH-34
    # Descripción: Verificar una excepcion a la hora de accedera la vista t_deletenotes
    # Método a Probar: excepcion en t_deletenotes (GET)
    # Datos de la Prueba: {teacher_user}
    # Resultado Esperado: HTTP 200, uso de plantilla 'teacher/t_deletenotes.html' pero un pantalla sin mostrar ningun registro de notas
    def test_t_deletenotes_exception(self):
        self.client.force_login(self.teacher_user)

        with patch('Main_App.models.Notes.objects.filter', side_effect=Exception("Simulated error")):
            response = self.client.get(reverse('t_deletenotes'))

        self.assertTemplateUsed(response, 'teacher/t_deletenotes.html')
        self.assertEqual(response.status_code, 200)

    # ID: VTCH-35
    # Descripción: Verificar la eliminacion de un registro de notas por parte de un profesor
    # Método a Probar: t_removenotes (POST)
    # Datos de la Prueba: {notesr}
    # Resultado Esperado: Redireccionamiento a l pagina 't_deletenotes' y verificar que las notas ya no existen
    def test_t_removenotes_succes(self):
        self.client.force_login(self.teacher_user)
        notes =Notes.objects.create(
            title="Nota 1",
            file=SimpleUploadedFile("nota1.pdf", b"contenido", content_type="application/pdf"),
            std="10",
            medium="CBSE",
            created_by=self.teacher_user.username  # coincide con la vista
        )

        response = self.client.get(reverse('t_removenotes', args=[notes.id]))

        self.assertRedirects(response, reverse('t_deletenotes'))
        self.assertFalse(Notes.objects.filter(id=notes.id).exists())


    # ID: VTCH-36
    # Descripción: Verificamos que un usuario con rol de profesor pueda acceder a la vista t_viewnotes
    # y que la plantilla 'teacher/t_viewnotes.html' se renderice correctamente con las notas disponibles
    # Método a Probar: t_viewnotes (GET)
    # Datos de la Prueba: {teacher_user}
    # Resultado Esperado: HTTP 200, uso de plantilla 'teacher/t_viewnotes.html' y contexto contiene 'notes'

    def test_t_viewnotes_renders_correctly(self):
        self.client.force_login(self.teacher_user)

        Notes.objects.create(
            title="Nota 1",
            file=SimpleUploadedFile("nota1.pdf", b"contenido 1", content_type="application/pdf"),
            std="10",
            medium="CBSE",
            created_by=self.teacher_user.username
        )
        Notes.objects.create(
            title="Nota 2",
            file=SimpleUploadedFile("nota2.pdf", b"contenido 2", content_type="application/pdf"),
            std="9",
            medium="Marathi",
            created_by=self.teacher_user.username
        )

        response = self.client.get('/t_viewnotes/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'teacher/t_viewnotes.html')
        self.assertIn('notes', response.context)
        self.assertEqual(len(response.context['notes']), 2)

