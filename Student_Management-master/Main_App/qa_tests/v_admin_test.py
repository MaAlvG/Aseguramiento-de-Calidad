from django.test import TestCase, Client
from django.urls import reverse
from Main_App.models import MyUser, Teacher
from django.contrib.messages import get_messages
from django.contrib import messages
from Main_App.models import Result
from Main_App.models import Notification
from django.core.files.uploadedfile import SimpleUploadedFile
from Main_App.models import Notes
from Main_App.models import Student

class AdminViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = MyUser.objects.create_user(
            username='admin', password='admin123', user_type=1
        )
        self.teacher_user = MyUser.objects.create_user(
            username='Viquez', password='clave123', user_type=2
        )
        if not Teacher.objects.filter(admin=self.teacher_user).exists(): 
            Teacher.objects.create(admin=self.teacher_user, address='Alajuela', gender='Male')

        self.student_user = MyUser.objects.create_user(
            username='student', password='stud123', user_type=3
        )
        if not Student.objects.filter(admin=self.student_user).exists():
            Student.objects.create(
                admin=self.student_user,
                address='Old Address',
                gender='Male',
                medium='English',
                std='10'
            )


    # ID: VADM-1
    # Descripci0n: Verificar que un usuario con rol de administrador puede acceder a la vista a_home.
    # Metodo a Probar: a_home (GET)
    # Datos de la Prueba: {admin_user}
    # Resultado Esperado: El sistema permite el acceso a la vista, devuelve HTTP 200.
    def test_a_home_status_code_and_context(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('adminhome')) 

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/a_home.html')
        self.assertIn('male_count', response.context)
        self.assertIn('marathi_count', response.context)
        self.assertIn('count_1', response.context)

    # ID: VADM-2
    # Descripcion: Verificar que un usuario con rol de administrador puede acceder a la vista adminprofile
    # Metodo a Probar: adminprofile (GET)
    # Datos de la Prueba: {admin_user}
    # Resultado Esperado: Se devuelve un 200 y se va la vista correspondiente
    def test_admin_profile_view(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('adminprofile'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/a_profile.html')


    # ID: VADM-3
    # Descripcion: Verificar que un usuario con rol de administrador pueda añadir un profesor addteacher
    # Metodo a Probar: addteacher (GET)
    # Datos de la Prueba: {admin_user}
    # Resultado Esperado: Se devuelve un 200 y se dirige a la vista correspondiente con la variable 'genders' en el contexto
    def test_addteacher_view_get(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('addteacher')) 

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/a_addteacher.html')
        self.assertIn('genders', response.context)

    # ID: VADM-4
    # Descripcion: Verificar que un usuario con rol de administrador puede enviar una solicitud POST para crear un nuevo Teacher
    # Metodo a Probar: saveteacher (POST)
    # Datos de la Prueba: {firstname, lastname, email, address, gender}
    # Resultado Esperado: Se crea un nuevo usuario y un objeto Teacher, se muestra un mensaje de exito y se redirige a /addteacher

    def test_saveteacher_post_success(self):
        self.client.force_login(self.admin_user)

        post_data = {
            'firstname': 'Andres',
            'lastname': 'Viquez',
            'email': 'viquez@estudiantec.com',
            'address': 'Alajuela',
            'gender': 'Male',
        }

        response = self.client.post(reverse('saveteacher'), data=post_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/addteacher')

        # Verificar el mensaje
        messages_list = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Teacher added successfully" in str(m.message) for m in messages_list))

        new_user = MyUser.objects.filter(email='viquez@estudiantec.com', user_type=2).first()
        self.assertIsNotNone(new_user)
        self.assertIsNotNone(new_user.teacher)
        self.assertEqual(new_user.teacher.address, 'Alajuela')
        self.assertEqual(new_user.teacher.gender, 'Male')

    # ID: VADM-5
    # Descripcion: Verificar que un usuario con rol de administrador puede eliminar un profe existente mediante la vista deleteteacher.
    # Metodo a Probar: deleteteacher (GET)
    # Datos de la Prueba: {teacher_user.id}
    # Resultado Esperado: El usuario y su perfil Teacher son eliminados, se redirige a /manageteacher con un mensaje de exito.

    def test_deleteteacher_success(self):
        self.client.force_login(self.admin_user)

        teacher_id = self.teacher_user.id
        self.assertTrue(MyUser.objects.filter(id=teacher_id).exists())
        response = self.client.get(reverse('deleteteacher', args=[teacher_id]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/manageteacher')

        self.assertFalse(MyUser.objects.filter(id=teacher_id).exists())

        messages_list = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Teacher deleted successfully" in str(m.message) for m in messages_list))


    # ID: VADM-6
    # Descripcion: Verificar que un usuario con rol de administrador puede restablecer la contraseña de un profesor mediante la vista resetteacherpass.
    # Metodo a Probar: resetteacherpass (GET)
    # Datos de la Prueba: {teacher_user.id}
    # Resultado Esperado: La contraseña del usuario se actualiza a "Teacher@100", se redirige a /manageteacher con un mensaje de exito.

    def test_resetteacherpass_success(self):
        self.client.force_login(self.admin_user)

        teacher_id = self.teacher_user.id
        response = self.client.get(reverse('resetteacherpass', args=[teacher_id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/manageteacher')

        # Recarga el objeto desde la BD
        self.teacher_user.refresh_from_db()

        self.assertTrue(self.teacher_user.check_password('Teacher@100'))
        messages_list = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Password reset successfully to Teacher@100" in str(m.message) for m in messages_list))

    # ID: VADM-7
    # Descripcion: Verificar que un usuario con rol de administrador puede acceder a la vista editteacher.
    # Metodo a Probar: editteacher (GET)
    # Datos de la Prueba: {teacher_user.id}
    # Resultado Esperado: Se devuelve un 200 y se dirige a a_editteacher.html con el objeto Teacher en el contexto.

    def test_editteacher_view_success(self):
        self.client.force_login(self.admin_user)

        teacher_id = self.teacher_user.id
        response = self.client.get(reverse('editteacher', args=[teacher_id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/a_editteacher.html')
        self.assertIn('teacher', response.context)
        self.assertEqual(response.context['teacher'].admin.id, teacher_id)
    

    # ID: VADM-8
    # Descripcion: Verificar que un usuario con rol de administrador puede actualizar correctamente un profesor 
    # Metodo a Probar: saveeditteacher (POST)
    # Datos de la Prueba: Datos modificados de un teacher existente
    # Resultado Esperado: Se actualiza el profesor, se redirige a /editteacher/<id> y se muestra un mensaje de exito

    def test_saveeditteacher_success(self):
        self.client.force_login(self.admin_user)

        teacher_id = str(self.teacher_user.id)
        post_data = {
            'teacher_id': teacher_id,
            'firstname': 'Maria',
            'lastname': 'Mora',
            'email': 'mmora@gmail.com',
            'address': 'San Jose',
            'gender': 'Other',
        }

        response = self.client.post(reverse('saveeditteacher'), post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f'/editteacher/{teacher_id}')

        # Recarga los objetos desde la BD
        self.teacher_user.refresh_from_db()
        teacher = Teacher.objects.get(admin=self.teacher_user)
        self.assertEqual(self.teacher_user.first_name, 'Maria')
        self.assertEqual(self.teacher_user.last_name, 'Mora')
        self.assertEqual(self.teacher_user.email, 'mmora@gmail.com')
        self.assertEqual(teacher.address, 'San Jose')
        self.assertEqual(teacher.gender, 'Other')
        messages_list = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Teacher Updated successfully" in str(m.message) for m in messages_list))

    # ID: VADM-9
    # Descripcion: Verificar que un usuario con rol de administrador puede eliminar un estudiante 
    # Método a Probar: deletestudent (GET o POST según implementación)
    # Datos de la Prueba: ID de un estudiante existente
    # Resultado Esperado: El estudiante se elimina, se redirige a /managestudent y se muestra mensaje de exito

    def test_deletestudent_success(self):
        self.client.force_login(self.admin_user)

        student_user = MyUser.objects.create_user(
            username='pkvist',
            password='124',
            user_type=3,
            first_name='Paula',
            last_name='Kvist',
            email='pkvist@gmail.com'
        )
        
        response = self.client.get(reverse('deletestudent', args=[student_user.id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/managestudent')

        user_exists = MyUser.objects.filter(id=student_user.id).exists()
        self.assertFalse(user_exists)
        messages_list = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Student deleted successfully" in str(m.message) for m in messages_list))
    
    # ID: VADM-10
    # Descripcion: Verificar que un usuario con rol de administrador puede resetear la contraseña de un estudiante
    # Método a Probar: resetstudentpass 
    # Datos de la Prueba: ID de un estudiante existente
    # Resultado Esperado: La contraseña se resetea a "Student@100", se redirige a /managestudent y se muestra mensaje de exito

    def test_resetstudentpass_success(self):
        self.client.force_login(self.admin_user)

        student_user = MyUser.objects.create_user(
            username='  Ion',
            password='123',
            user_type=3,
            first_name='Ion',
            last_name='Ion',
            email='Ion@gmail.com'
        )

        response = self.client.get(reverse('resetstudentpass', args=[student_user.id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/managestudent')
        student_user.refresh_from_db()
        self.assertTrue(student_user.check_password('Student@100'))
        messages_list = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Password reset successfully to Student@100" in str(m.message) for m in messages_list))


    # ID: VADM-11
    # Descripcion: Verificar que un usuario con rol de administrador puede acceder a la vista a_addnotification
    # Metodo a Probar: a_addnotification (GET)
    # Datos de la Prueba: {admin_user}
    # Resultado Esperado: El sistema permite el acceso a la vista, devuelve HTTP 200

    def test_a_addnotification_view_get(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('a_addnotification'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/a_addnotification.html')

    # ID: VADM-12
    # Descripcion: Verificar que un usuario con rol de administrador puede crear una notificacion 
    # Metodo a Probar: a_savenotification (POST)
    # Datos de la Prueba: {admin_user, heading="Hola", message="Hola mundo"}
    # Resultado Esperado: Se crea una nueva instancia de Notification, se guarda correctamente y se muestra un mensaje de exito
    def test_a_savenotification_post_success(self):
            self.client.force_login(self.admin_user)

            post_data = {
                'heading': 'Hola',
                'message': 'Hola Mundo'
            }

            response = self.client.post('/a_savenotification', data=post_data)

            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, '/a_addnotification')

            notif = Notification.objects.filter(
                heading='Hola',
                message='Hola Mundo',
                created_by=self.admin_user.username
            ).first()
            self.assertIsNotNone(notif)
            storage = list(messages.get_messages(response.wsgi_request))
            self.assertTrue(any(m.message == "Notification added successfully" for m in storage))

    # ID: VADM-13
    # Descripcion: Verificar que no se permite el acceso por medio del GET a  a_savenotification
    # Metodo a probar: a_savenotification (GET)
    # Datos de prueba: Solicitud GET autenticada por un usuario administrador
    # Resultado esperado: Codigo  html 200 y el  mensaje "Method not Allowed..!" 
    def test_a_savenotification_get_not_allowed(self):
        self.client.force_login(self.admin_user)
        response = self.client.get('/a_savenotification')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Method not Allowed..!")

    # ID: VADM-14
    # Descripcion: Verifica que un administrador pueda eliminar una notificacion
    # Metodo a probar: a_deletenotification (GET)
    # Datos de prueba: Notificación creada previamente
    # Resultado esperado: La notificacion es eliminada y se redirige a /managenotification (HTTP 302)

    def test_a_deletenotification_success(self):
        self.client.force_login(self.admin_user)

        notification = Notification.objects.create(
            heading='Hola',
            message='Hola Mundo',
            created_by=self.admin_user.username
        )

        response = self.client.get(f'/a_deletenotification/{notification.id}')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/managenotification')

        self.assertFalse(Notification.objects.filter(id=notification.id).exists())
        storage = list(messages.get_messages(response.wsgi_request))
        self.assertTrue(any(m.message == "Notification deleted successfully" for m in storage))

    # ID: VADM-15
    # Descripcion: Verificar que un administrador pueda acceder a la vista para agregar resultados
    # Metodo a probar: a_addresult (GET)
    # Resultado esperado: Se carga el template con los datos de std_choices y medium_choices (HTTP 200)

    def test_a_addresult_get_success(self):
        self.client.force_login(self.admin_user)

        response = self.client.get('/a_addresult/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/a_addresult.html')
        self.assertIn('stds', response.context)
        self.assertIn('mediums', response.context)

        # Asegurarse de que los contextos contengan las elecciones definidas
        self.assertEqual(response.context['stds'], Result.std_choices)
        self.assertEqual(response.context['mediums'], Result.medium_choices)


    # ID: VADM-16
    # Descripcion: Verificar que un administrador pueda subir un resultado
    # Metodo a Probar: a_saveresult (POST)
    # Datos de la Prueba: {admin_user, title='Examen Final', medium='English', std='10th', resultfile=archivo_pdf}
    # Resultado Esperado: Se crea un registro en Result y  se añade el mensaje de exito
    def test_a_saveresult_post_success(self):
        self.client.force_login(self.admin_user)

        # Simula un archivo subido
        test_file = SimpleUploadedFile("test_result.pdf", b"file_content", content_type="application/pdf")
        post_data = {
            'title': 'Examen Final',
            'medium': 'English', 
            'std': '10th',      
            'resultfile': test_file,
        }
        response = self.client.post('/a_saveresult', data=post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/a_addresult')


        result = Result.objects.filter(title='Examen Final', created_by=self.admin_user.username).first()
        self.assertIsNotNone(result)
        self.assertEqual(result.medium, 'English')
        self.assertEqual(result.std, '10th')

        storage = list(messages.get_messages(response.wsgi_request))
        self.assertTrue(any(m.message == "Result uploaded successfully" for m in storage))

    # ID: VADM-17
    # Descripcion: Revisar que un usuario con rol de administrador puede acceder a a_viewresult 
    # Metodo a Probar: a_viewresult (GET)
    # Datos de la Prueba: {admin_user}
    # Resultado Esperado: HTTP 200
    def test_a_viewresult_renders_correctly(self):
        self.client.force_login(self.admin_user)

        Result.objects.create(title="Res 1", file="file1.pdf", std="10", medium="English", created_by="admin")
        Result.objects.create(title="Res 2", file="file2.pdf", std="9", medium="Spanish", created_by="admin")

        response = self.client.get('/a_viewresult/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/a_viewresult.html')
        self.assertIn('results', response.context)
        self.assertEqual(len(response.context['results']), 2)

    # ID: VADM-18
    # Descripcion: Verificar que un administrador pueda acceder correctamente a la vista de agregar notas
    # Metodo a Probar: a_addnotes (GET)
    # Datos de la Prueba: {admin_user}
    # Resultado Esperado: Codigo HTTP 200 
    def test_a_addnotes_get_success(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse('a_addnotes'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/a_addnotes.html')
        self.assertIn('stds', response.context)
        self.assertIn('mediums', response.context)
        self.assertTrue(len(response.context['stds']) > 0)
        self.assertTrue(len(response.context['mediums']) > 0)

    # ID: VADM-19
    # Descripcion: Verificar que un administrador pueda subir correctamente las notas
    # Metodo a Probar: a_savenotes (POST)
    # Datos de la Prueba: {admin_user, archivo válido}
    # Resultado Esperado: Redirección a /a_addnotes/, y creacion del objeto Notes con los datos enviados.
    def test_a_savenotes_post_success(self):
        self.client.force_login(self.admin_user)

        fake_notes = SimpleUploadedFile("testNotes.pdf", b"contenido del archivo", content_type="application/pdf")

        post_data = {
            'title': 'Notas Examen Final Admin',
            'medium': 'English',
            'std': '10',
            'notesfile': fake_notes
        }

        url = reverse('a_savenotes')
        response = self.client.post(url, data=post_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('a_addnotes'))

        note = Notes.objects.filter(title='Notas Examen Final Admin', created_by=self.admin_user.username).first()
        self.assertIsNotNone(note)
        self.assertEqual(note.medium, 'English')
        self.assertEqual(note.std, '10')

    # ID: VADM-20
    # Descripcion: Verificar que un usuario con rol de administrador puede acceder a la vista manageteacher
    # Metodo a Probar: manageteacher (GET)
    # Datos de la Prueba: {admin_user}
    # Resultado Esperado: El sistema permite el acceso a la vista y devuelve HTTP 200
    def test_manageteacher_access(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('manageteacher')) 

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/a_manageteacher.html')
        self.assertIn('teachers', response.context)

    # ID: VADM-21
    # Descripcion: Verificar que un usuario con rol de administrador puede acceder a la vista addstudent
    # Metodo a Probar: addstudent (GET)
    # Datos de la Prueba: {admin_user}
    # Resultado Esperado: El sistema permite el acceso a la vista y devuelve HTTP 200
    def test_addstudent_access(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('addstudent')) 

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/a_addstudent.html')
        self.assertIn('genders', response.context)
        self.assertIn('stds', response.context)
        self.assertIn('mediums', response.context)

    # ID: VADM-22
    # Descripcion: Verificar que un usuario con rol de administrador puede acceder a la vista managestudent
    # Metodo a Probar: managestudent (GET)
    # Datos de la Prueba: {admin_user}
    # Resultado Esperado: El sistema permite el acceso a la vista y  devuelve HTTP 200
    def test_managestudent_access(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('managestudent'))  
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/a_managestudent.html')
        self.assertIn('students', response.context)

    # ID:VADM-23
    # Descripcion: Verificar que un usuario con rol de administrador puede acceder a la vista managenotification
    # Metodo a Probar: managenotification (GET)
    # Datos de la Prueba: {admin_user}
    # Resultado Esperado: El sistema permite el acceso a la vista y devuelve HTTP 200
    def test_managenotification_access(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('managenotification')) 
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/a_managenotification.html')
        self.assertIn('notifications', response.context)

    # ID: VADM-24
    # Descripcion: Verificar que un usuario con rol de administrador puede acceder a la vista a_viewnotes
    # Metodo a Probar: a_viewnotes (GET)
    # Datos de la Prueba: {admin_user autenticado}
    # Resultado Esperado: El sistema devuelve HTTP 200
    def test_a_viewnotes_access(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('a_viewnotes')) 
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/a_viewnotes.html')
        self.assertIn('notes', response.context)

    # ID: VADM-25
    # Descripci0n: Verificar que un usuario con rol de administrador puede actualizar correctamente un estudiante
    # Metodo a Probar: saveeditstudent (POST)
    # Datos de la Prueba: Datos modificados de un estudiante existente.
    # Resultado Esperado: Se actualiza el estudiante y manda un mensaje de exito.

    def test_saveeditstudent_success(self):
        self.client.force_login(self.admin_user)
        student_id = str(self.student_user.id)
        post_data = {
            'student_id': student_id,
            'firstname': 'Paula',
            'lastname': 'Kvist',
            'email': 'paulita@gmail.com',
            'address': 'Atenas',
            'gender': 'Female',
            'medium': 'Spanish',
            'std': '11',
        }

        response = self.client.post(reverse('saveeditstudent'), post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f'/editstudent/{student_id}')
        # Recarga los objetos desde la BD
        self.student_user.refresh_from_db()
        student = Student.objects.get(admin=self.student_user)

        self.assertEqual(self.student_user.first_name, 'Paula')
        self.assertEqual(self.student_user.last_name, 'Kvist')
        self.assertEqual(self.student_user.email, 'paulita@gmail.com')
        self.assertEqual(student.address, 'Atenas')
        self.assertEqual(student.gender, 'Female')
        self.assertEqual(student.medium, 'Spanish')
        self.assertEqual(student.std, '11')
        messages_list = list(get_messages(response.wsgi_request))
        self.assertTrue(any("upadated successfully" in str(m.message) for m in messages_list))
