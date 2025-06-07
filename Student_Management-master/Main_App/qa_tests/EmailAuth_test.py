from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend, UserModel

from Main_App.EmailAuthentication import EmailAuth

class EmailAuth_test(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='securepassword123',
            user_type=1
        )

    # ID: EA-01
    # Descripción: Verificar que un usuario existe y se ingreso la contraseña correcta
    # Método a Probar: authenticate (GET)
    # Datos de la Prueba: {user}
    # Resultado Esperado: el usuario se puede autenticar, y se puede obtener informacion del usuario ya autenticado

    def test_authenticate_with_valid_email_and_password(self):
        backend = EmailAuth()
        authenticated_user = backend.authenticate(username='testuser@example.com', password='securepassword123')
        self.assertIsNotNone(authenticated_user)
        self.assertEqual(authenticated_user, self.user)

    # ID: EA-02
    # Descripción: Verificar que un usuario no existe pero se ingreso una contraseña correcta
    # Método a Probar: authenticate (GET)
    # Datos de la Prueba: {user}
    # Resultado Esperado: No se puede obtener informacion del usuario solicitado
    def test_authenticate_with_invalid_email(self):
        backend = EmailAuth()
        user = backend.authenticate(username='wrong@example.com', password='securepassword123')
        self.assertIsNone(user)

    # ID: EA-03
    # Descripción: Verificar que un usuario existe pero se ingreso una contraseña incorrecta
    # Método a Probar: authenticate (GET)
    # Datos de la Prueba: {user}
    # Resultado Esperado: No se puede obtener informacion del usuario solicitado
    def test_authenticate_with_invalid_password(self):
        backend = EmailAuth()
        user = backend.authenticate(username='testuser@example.com', password='wrongpassword')
        self.assertIsNone(user)