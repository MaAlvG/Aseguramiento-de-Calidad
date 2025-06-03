from django.test import TestCase, Client
from django.urls import reverse
from Main_App.models import MyUser
from Main_App.models import Teacher
from Main_App.models import Student
from unittest.mock import patch # para simular el comportamiento de los mensajes
from django.contrib import messages # para inspeccionar los mensajes
from Main_App.models import Notification # para pruebas de notificaciones

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

    # ID: VTCH-9  -->>hay que hacer un reporte de error para esta prueba
    # Descripcion: Revisar que un profesor puede resetear la contrasena de un estudiante bien.
    # Metodo a Probar: t_resetspass (GET)
    # Datos de la Prueba: {teacher_user, student_user}
    # Resultado Esperado: La contrasena del estudiante se actualiza a "Student@100" y se redirecciona bien
    def test_t_resetspass_resets_password(self):
        student_user = MyUser.objects.create_user(
            username='est_reset', password='contraAntigua03', user_type=3
        )
        # actualizar datos del estudiante creado por la señal post_save 
        student_user.student.address = 'Heredia'
        student_user.student.gender = 'Male'
        student_user.student.save()

        self.client.force_login(self.teacher_user)
        response = self.client.get(f'/t_resetspass/{student_user.id}')

        self.assertEqual(response.status_code, 302)
        student_user.refresh_from_db()
        self.assertTrue(student_user.check_password("Student@100"))
    
    # ID: VTCH-10
    # Descripcion: Un usuario con rol Teacher accede a t_addnotification.
    # Metodo a Probar: t_addnotification (GET)
    # Datos de la Prueba: {teacher_user}
    # Resultado Esperado: HTTP 200 y se renderiza 'teacher/t_addnotification.html'
    def test_t_addnotification_teacher_access(self):
        self.client.force_login(self.teacher_user)
        response = self.client.get('/t_addnotification/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'teacher/t_addnotification.html')

    # ID: VTCH-11
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

    # ID: VTCH-12
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

    # ID: VTCH-13
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

        notif = Notification.objects.filter(heading='Examen',
                                            message='El examen sera el lunes',
                                            created_by=self.teacher_user.username).first()
        self.assertIsNotNone(notif)

        storage = list(messages.get_messages(response.wsgi_request))
        self.assertTrue(any(m.message == "Notification added successfully" for m in storage))

    # ID: VTCH-14
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

    # ID: VTCH-15
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
