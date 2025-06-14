from django.test import TestCase, Client
from django.urls import reverse
from Main_App.models import MyUser
from Main_App.models import Student
from Main_App.models import Result

class StudentViewsTestCase(TestCase):
    # Configuracion de Pruebas
    # Consideraciones: Se usara force_login, para efectuar los test sin
    # pasar por la parte de restrictions.
    def setUp(self):
        self.client = Client()
        
        self.s_username = 'Pepito'
        self.t_username = 'teacher'
        self.a_username = 'admin'
        self.s_password = '1234'
        self.t_password = 'profe123'
        self.a_password = 'admin123'

        self.student_user = MyUser.objects.create_user(
            username=self.s_username, 
            password=self.s_password , 
            user_type=3
        )
        self.admin_user = MyUser.objects.create_user(
            username=self.a_username,
            email='admin@test.com',
            password=self.a_password,
            user_type=1
        )
        self.teacher_user = MyUser.objects.create_user(
            username=self.t_username,
            email='teacher@test.com',
            password=self.t_password,
            user_type=2
        )
        if not Student.objects.filter(admin=self.student_user).exists():
            Student.objects.create(admin=self.student_user, address='Limon', gender='Male')



    # ID: VST-1
    # Descripcion: Revisar que un MyUser con rol de Student puede acceder a la vista s_home.
    # Metodo a Probar: s_home (GET)
    # Datos de la Prueba: {student_user}
    # Resultado Esperado: El sistema permite el acceso a la vista, devuelve HTTP 200, 
    # entonces sabemos que la vista es accesible para el rol de Student
    def test_s_home_status_code(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('s_home'))
        self.assertEqual(response.status_code, 200)

    # ID: VST-2
    # Descripcion: Revisar que una cuenta sin autenticar no tenga acceso a vista s_home.
    # Metodo a Probar: s_home (GET)
    # Datos de la Prueba: N/A
    # Resultado Esperado: El sistema no permite el acceso a la vista, devuelve HTTP 302, 
    # entonces sabemos que la vista es inaccesible. Ademas redirige a /loginpage.
    def test_s_home_unauthenticated_user(self):
        response = self.client.get(reverse('s_home'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/loginpage')
        
    # ID: VST-3
    # Descripcion: Revisar que una cuenta que no sea Student no tenga acceso a vista s_home.
    # Metodo a Probar: s_home (GET)
    # Datos de la Prueba: 
    #                   username: {t_username, a_username}
    #                   password: {t_password, a_password}
    # Resultado Esperado: El sistema no permite el acceso a la vista, devuelve HTTP 302, 
    # entonces sabemos que la vista es inaccesible. Ademas redirige a /loginpage.
    def test_s_home_not_student_user(self):
        self.client.login(username=self.t_username, 
                          password=self.t_password)
        response = self.client.get(reverse('s_home'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/loginpage')

    # ID: VST-4
    # Descripcion: Revisar que un MyUser con rol de Student puede acceder a la vista s_profile.
    # Metodo a Probar: s_profile (GET)
    # Datos de la Prueba: {student_user}
    # Resultado Esperado: Se devuelve un 200 y se renderiza la info del perfil, 
    # resvisando que el usuario tiene un objeto Student relacionado y permisos suficientes
    def test_s_profile_view(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('s_profile'))
        self.assertEqual(response.status_code, 200)

    # ID: VST-5
    # Descripcion: Revisar que una cuenta sin autenticar no tenga acceso a vista s_profile.
    # Metodo a Probar: s_profile (GET)
    # Datos de la Prueba: N/A
    # Resultado Esperado: El sistema no permite el acceso a la vista, devuelve HTTP 302, 
    # entonces sabemos que la vista es inaccesible. Ademas redirige a /loginpage.
    def test_unauthorized_s_profile_view(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('s_profile'))
        self.assertEqual(response.status_code, 200)

    # ID: VST-6
    # Descripcion: Revisar que una cuenta sin autenticar no tenga acceso a vista s_profile.
    # Metodo a Probar: s_profile (GET)
    # Datos de la Prueba: 
    #                   username: {t_username, a_username}
    #                   password: {t_password, a_password}
    # Resultado Esperado: El sistema no permite el acceso a la vista, devuelve HTTP 302, 
    # entonces sabemos que la vista es inaccesible. Ademas redirige a /loginpage.
    def test_not_student_s_profile_view(self):
        self.client.login(username=self.t_username, 
                          password=self.t_password)
        response = self.client.get(reverse('s_profile'))
        self.assertEqual(response.status_code, 302)

    # ID: VST-7
    # Descripcion: Revisar que un Student puede actualizar exitosamente los campos editables de su perfil.
    # Metodo a Probar: s_saveprofile (POST)
    # Datos de la Prueba: 
    #                   login = self.student_user
    #                   student_id = self.student_user.id
    #                   name = 'Laura'
    #                   lastname = 'Lorenz'
    #                   email = 'laura@test.com'
    #                   address = 'Alajuela'
    #                   gender = 'Female'
    # Resultado Esperado: Se actualiza el perfil del estudiante con los nuevos datos, 
    # el sistema redirige a login dada la actualizacion.
    def test_s_saveprofile_post_success(self):
        self.client.force_login(self.student_user)
        name = 'Laura'
        lastname = 'Lorenz'
        email = 'laura@test.com'
        address = 'Alajuela'
        gender = 'Female'
        post_data = {
            'student_id': self.student_user.id,
            'firstname': name,
            'lastname': lastname,
            'email': email,
            'address': address,
            'gender': gender,
            'password': ''
        }
        response = self.client.post('/s_saveprofile', data=post_data)
        self.assertEqual(response.status_code, 302)  # redireccion despues de guardar
        self.assertEqual(response.url, '/studentprofile')

        updated_student = MyUser.objects.get(id=self.student_user.id)
        self.assertEqual(updated_student.first_name, name)
        self.assertEqual(updated_student.last_name, lastname)
        self.assertEqual(updated_student.email, email)

        student_profile = Student.objects.get(admin=updated_student)
        self.assertEqual(student_profile.address, address)
        self.assertEqual(student_profile.gender, gender)

    # ID: VST-8
    # Descripcion: Revisar que una cuenta sin autenticar no tenga capacidad de sobreescribir
    #              un perfil de Student.
    # Metodo a Probar: s_saveprofile (POST)
    # Datos de la Prueba:
    #                   student_id = self.student_user.id
    #                   name = 'Laura'
    #                   lastname = 'Lorenz'
    #                   email = 'laura@test.com'
    #                   address = 'Alajuela'
    #                   gender = 'Female'
    # Resultado Esperado: El sistema no permite el acceso a la funcion, devuelve HTTP 302, 
    # entonces sabemos que la funcion es inaccesible. Ademas redirige a /loginpage.
    def test_unathorized_s_saveprofile_post_success(self):
        name = 'Laura'
        lastname = 'Lorenz'
        email = 'laura@test.com'
        address = 'Alajuela'
        gender = 'Female'
        post_data = {
            'student_id': self.student_user.id,
            'firstname': name,
            'lastname': lastname,
            'email': email,
            'address': address,
            'gender': gender,
            'password': ''
        }
        response = self.client.post('/s_saveprofile', data=post_data)
        self.assertEqual(response.status_code, 302)  # redireccion despues de guardar
        self.assertEqual(response.url, '/loginpage')

        updated_student = MyUser.objects.get(id=self.student_user.id)
        self.assertNotEqual(updated_student.first_name, name)
        self.assertNotEqual(updated_student.last_name, lastname)
        self.assertNotEqual(updated_student.email, email)

        student_profile = Student.objects.get(admin=updated_student)
        self.assertNotEqual(student_profile.address, address)
        self.assertNotEqual(student_profile.gender, gender)

    # ID: VST-9
    # Descripcion: Revisar que una cuenta distinta a tipo Student no tenga capacidad 
    #              de sobreescribir un perfil de Student.
    # Metodo a Probar: s_saveprofile (POST)
    # Datos de la Prueba: 
    #                   username: {t_username, a_username}
    #                   password: {t_password, a_password}
    #                   student_id = self.student_user.id
    #                   name = 'Laura'
    #                   lastname = 'Lorenz'
    #                   email = 'laura@test.com'
    #                   address = 'Alajuela'
    #                   gender = 'Female'            
    # Resultado Esperado: El sistema no permite el acceso a la funcion, devuelve HTTP 302, 
    # entonces sabemos que la funcion es inaccesible. Ademas redirige a /loginpage.
    def test_not_student_s_saveprofile_post_success(self):
        self.client.login(username=self.a_username, 
                          password=self.a_password)
        name = 'Laura'
        lastname = 'Lorenz'
        email = 'laura@test.com'
        address = 'Alajuela'
        gender = 'Female'
        post_data = {
            'student_id': self.student_user.id,
            'firstname': name,
            'lastname': lastname,
            'email': email,
            'address': address,
            'gender': gender,
            'password': ''
        }
        response = self.client.post('/s_saveprofile', data=post_data)
        self.assertEqual(response.status_code, 302)  # redireccion despues de guardar
        self.assertEqual(response.url, '/loginpage')

        updated_student = MyUser.objects.get(id=self.student_user.id)
        self.assertNotEqual(updated_student.first_name, name)
        self.assertNotEqual(updated_student.last_name, lastname)
        self.assertNotEqual(updated_student.email, email)

        student_profile = Student.objects.get(admin=updated_student)
        self.assertNotEqual(student_profile.address, address)
        self.assertNotEqual(student_profile.gender, gender)

    # ID: VST-9
    # Descripcion: Revisar que no sea posible emplear una request distinta a POST
    # Metodo a Probar: s_saveprofile (GET/UPDATE/DELETE)
    # Datos de la Prueba: self.student_user
    # Resultado Esperado: El sistema no permite el acceso a la funcion, devuelve HTTP 302, 
    # entonces sabemos que la funcion es inaccesible. Ademas redirige a /loginpage.
    def test_not_post_s_saveprofile_post_success(self):
        self.client.force_login(self.student_user)
        response = self.client.get('/s_saveprofile')
        self.assertEqual(response.content.decode(), "Method not Allowed..!")  
        
    # ID: VST-10
    # Descripcion: Revisar que un MyUser con rol de Student puede acceder a la vista s_viewresult.
    # Metodo a Probar: s_viewresult (GET)
    # Datos de la Prueba: {student_user}
    # Resultado Esperado: El sistema permite el acceso a la vista, devuelve HTTP 200, 
    # entonces sabemos que la vista es accesible para el rol de Student
    def test_s_viewresult_status_code(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('s_viewresult'))
        self.assertEqual(response.status_code, 200)

    # ID: VST-11
    # Descripcion: Revisar que una cuenta sin autenticar no tenga acceso a vista s_viewresult.
    # Metodo a Probar: s_viewresult (GET)
    # Datos de la Prueba: N/A
    # Resultado Esperado: El sistema no permite el acceso a la vista, devuelve HTTP 302, 
    # entonces sabemos que la vista es inaccesible. Ademas redirige a /loginpage.
    def test_s_viewresult_unauthenticated_user(self):
        response = self.client.get(reverse('s_viewresult'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/loginpage')

    # ID: VST-12
    # Descripcion: Revisar que una cuenta que no sea Student no tenga acceso a vista s_viewresult.
    # Metodo a Probar: s_viewresult (GET)
    # Datos de la Prueba: 
    #                   username: {t_username, a_username}
    #                   password: {t_password, a_password}
    # Resultado Esperado: El sistema no permite el acceso a la vista, devuelve HTTP 302, 
    # entonces sabemos que la vista es inaccesible. Ademas redirige a /loginpage.
    def test_s_viewresult_not_student_user(self):
        self.client.login(username=self.t_username, 
                          password=self.t_password)
        response = self.client.get(reverse('s_viewresult'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/loginpage')