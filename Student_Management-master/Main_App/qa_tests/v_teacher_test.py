from django.test import TestCase, Client
from django.urls import reverse
from Main_App.models import MyUser
from Main_App.models import Teacher
from Main_App.models import Student

class TeacherViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher_user = MyUser.objects.create_user(
            username='profe', password='clave123', user_type=2
        )
        # evitar conflicto si ya existe una instancia Teacher con ese admin
        if not Teacher.objects.filter(admin=self.teacher_user).exists():
            Teacher.objects.create(admin=self.teacher_user, address='San José', gender='Female')


    # ID: VTCH-1
    # Descripcion: Revisar que un usuario con rol de profesor puede acceder a la vista t_home.
    # Metodo a Probar: t_home (GET)
    # Datos de la Prueba: {teacher_user}
    # Resultado Esperado: El sistema permite el acceso a la vista, devuelve HTTP 200, 
    # entonces sabemos que la vista es accesible para el rol de profesor
    def test_t_home_status_code(self):
        self.client.force_login(self.teacher_user)
        response = self.client.get(reverse('t_home'))
        self.assertEqual(response.status_code, 200)

    # ID: VTCH-2
    # Descripcion: Revisar que un usuario con rol de profesor puede acceder a la vista t_profile.
    # Metodo a Probar: t_profile (GET)
    # Datos de la Prueba: {teacher_user}
    # Resultado Esperado: Se devuelve un 200 y se renderiza la info del perfil, 
    # resvisando que el usuario tiene un objeto Teacher relacionado y permisos suficientes
    def test_t_profile_view(self):
        self.client.force_login(self.teacher_user)
        response = self.client.get(reverse('t_profile'))
        self.assertEqual(response.status_code, 200)

    # ID: VTCH-3
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

    # ID: VTCH-4
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

    # ID: VTCH-5
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

    # ID: VTCH-6
    # Descripcion: Revisar que un usuario con rol de profesor puede acceder a la vista t_viewstudent.
    # Metodo a Probar: t_viewstudent (GET)
    # Datos de la Prueba: {teacher_user}
    # Resultado Esperado: El sistema permite el acceso a la vista, 
    # devuelve HTTP 200 y renderiza bien la lista de estudiantes
    def test_t_viewstudent_status_code(self):
        self.client.force_login(self.teacher_user)
        response = self.client.get('/t_viewstudent/')
        self.assertEqual(response.status_code, 200)

    # ID: VTCH-7
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









