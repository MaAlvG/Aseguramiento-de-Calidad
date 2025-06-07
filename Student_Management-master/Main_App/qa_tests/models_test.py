from django.test import TestCase
from Main_App.models import MyUser, Admin, Teacher, Student

class ModelsTests(TestCase):
    
    # ID: M-01
    # Descripción: Verificar la creacion de un usuario de tipo admin
    # Método a Probar: user_create
    # Datos de la Prueba: {user}
    # Resultado Esperado: el usuario creado existe   
    def test_create_admin_user_creates_admin_instance(self):
        user = MyUser.objects.create_user(username='admin@example.com', email='admin@example.com', password='adminpass', user_type=1)
        self.assertTrue(Admin.objects.filter(admin=user).exists())

    # ID: M-02
    # Descripción: Verificar la creacion de un usuario de tipo teacher
    # Método a Probar: user_create
    # Datos de la Prueba: {user}
    # Resultado Esperado: el usuario creado existe
    def test_create_teacher_user_creates_teacher_instance(self):
        user = MyUser.objects.create_user(username='teacher@example.com', email='teacher@example.com', password='teacherpass', user_type=2)
        self.assertTrue(Teacher.objects.filter(admin=user).exists())

    # ID: M-03
    # Descripción: Verificar la creacion de un usuario de tipo student
    # Método a Probar: user_create
    # Datos de la Prueba: {user}
    # Resultado Esperado: el usuario creado existe
    def test_create_student_user_creates_student_instance(self):
        user = MyUser.objects.create_user(username='student@example.com', email='student@example.com', password='studentpass', user_type=3)
        self.assertTrue(Student.objects.filter(admin=user).exists())

    # ID: M-04
    # Descripción: Verificar el guardado de un usuario de tipo admin
    # Método a Probar: user_create
    # Datos de la Prueba: {user}
    # Resultado Esperado: el usuario creado existe
    def test_user_save_triggers_related_model_save(self):
        user = MyUser.objects.create_user(username='admin2@example.com', email='admin2@example.com', password='adminpass', user_type=1)
        admin_instance = user.admin
        old_updated_at = admin_instance.updated_at

        # Modificar algo para que se note el efecto del save
        user.save()

        # Volver a cargar de DB
        admin_instance.refresh_from_db()
        self.assertNotEqual(admin_instance.updated_at, old_updated_at)
