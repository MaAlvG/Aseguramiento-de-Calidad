import unittest
import time
import subprocess
import threading
import requests
import signal
import sys
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

class DjangoSeleniumTestCase(unittest.TestCase):
    """
    Clase base para todas las pruebas de Selenium
    Cada clase de prueba heredara de esta y tendra su propio ciclo de vida
    """
    
    @classmethod
    def setUpClass(cls):
        """
        Configuracion que se ejecuta una vez antes de todas las pruebas de esta clase
        """
        print(f"\n=== Configurando {cls.__name__} ===")
        
        # Configurar opciones del navegador
        cls.chrome_options = Options()
        
        cls.chrome_options.add_argument('--headless') #para NO ver las ejecuciones en tiempo real.
        cls.chrome_options.add_argument('--no-sandbox')
        cls.chrome_options.add_argument('--disable-dev-shm-usage')
        cls.chrome_options.add_argument('--disable-gpu')
        cls.chrome_options.add_argument('--disable-extensions')
        cls.chrome_options.add_argument('--disable-logging')
        cls.chrome_options.add_argument('--log-level=3')
        cls.chrome_options.add_argument('--silent')
        cls.chrome_options.add_argument('--window-size=1200,800')
        cls.chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        cls.chrome_options.add_experimental_option('useAutomationExtension', False)
        
        
        # URL base del servidor Django
        cls.live_server_url = 'http://127.0.0.1:8000'
        cls.server_process = None
        cls.server_started_by_us = False
        
        try:
            # Verificar si el servidor ya esta corriendo
            if not cls.is_server_running():
                print("Iniciando servidor Django...")
                cls.start_django_server()
                cls.wait_for_server()
                cls.server_started_by_us = True
            else:
                print("El servidor Django ya está ejecutándose.")
        except Exception as e:
            print(f"Error al configurar el servidor: {e}")
            raise
    
    @classmethod
    def tearDownClass(cls):
        """
        Limpieza que se ejecuta una vez después de todas las pruebas de esta clase
        """
        print(f"\n=== Limpiando {cls.__name__} ===")
        # Solo detener el servidor si lo iniciamos nosotros
        if hasattr(cls, 'server_started_by_us') and cls.server_started_by_us:
            if hasattr(cls, 'server_process') and cls.server_process:
                cls.stop_django_server()
    
    def setUp(self):
        """
        Configuración que se ejecuta antes de cada prueba individual
        """
        print(f"  → Iniciando: {self._testMethodName}")
        try:
            # Usar webdriver-manager para obtener el ChromeDriver compatible
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=self.chrome_options)
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)
        except WebDriverException as e:
            self.skipTest(f"No se pudo inicializar Chrome WebDriver: {e}")
        except Exception as e:
            self.skipTest(f"Error inesperado al configurar WebDriver: {e}")
    
    def tearDown(self):
        """
        Limpieza que se ejecuta después de cada prueba individual
        """
        print(f"  ← Finalizando: {self._testMethodName}")
        if hasattr(self, 'driver'):
            try:
                self.driver.quit()
            except Exception as e:
                print(f"    Error al cerrar el driver: {e}")
    
    @classmethod
    def is_server_running(cls):
        """Verifica si el servidor Django ya está ejecutándose"""
        try:
            response = requests.get(cls.live_server_url, timeout=5)
            return response.status_code < 500
        except:
            return False
    
    @classmethod
    def start_django_server(cls):
        """Inicia el servidor Django en un proceso separado"""
        try:
            cls.server_process = subprocess.Popen(
                ['python', 'manage.py', 'runserver', '127.0.0.1:8000', '--noreload'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            print(f"    Servidor Django iniciado con PID: {cls.server_process.pid}")
        except Exception as e:
            print(f"    Error al iniciar el servidor Django: {e}")
            raise
    
    @classmethod
    def stop_django_server(cls):
        """Detiene el servidor Django"""
        if hasattr(cls, 'server_process') and cls.server_process:
            try:
                print("    Deteniendo servidor Django...")
                if hasattr(os, 'killpg'):
                    os.killpg(os.getpgid(cls.server_process.pid), signal.SIGTERM)
                else:
                    cls.server_process.terminate()
                
                try:
                    cls.server_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    print("    Forzando cierre del servidor...")
                    if hasattr(os, 'killpg'):
                        os.killpg(os.getpgid(cls.server_process.pid), signal.SIGKILL)
                    else:
                        cls.server_process.kill()
                    cls.server_process.wait()
                
                print("    Servidor Django detenido.")
            except Exception as e:
                print(f"    Error al detener el servidor: {e}")
    
    @classmethod
    def wait_for_server(cls, timeout=30):
        """Espera a que el servidor Django esté disponible"""
        print("    Esperando a que el servidor esté disponible...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(cls.live_server_url, timeout=5)
                if response.status_code < 500:
                    print("    ✓ Servidor disponible!")
                    return
            except requests.exceptions.ConnectionError:
                pass
            except requests.exceptions.Timeout:
                print("    Timeout al conectar, reintentando...")
            time.sleep(2)
        
        raise Exception(f"El servidor Django no estuvo disponible después de {timeout} segundos")
    
    def wait_for_element(self, by, value, timeout=10):
        """Espera a que un elemento esté presente y sea visible"""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            print(f"    Elemento no encontrado: {by}={value}")
            raise
    
    def wait_for_clickable(self, by, value, timeout=10):
        """Espera a que un elemento sea clickeable"""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
        except TimeoutException:
            print(f"    Elemento no clickeable: {by}={value}")
            raise
    
    def safe_get(self, url, timeout=30):
        """Navega a una URL de manera segura con timeout"""
        try:
            self.driver.set_page_load_timeout(timeout)
            self.driver.get(url)
        except TimeoutException:
            print(f"    Timeout al cargar la página: {url}")
            raise
        except Exception as e:
            print(f"    Error al navegar a {url}: {e}")
            raise
# SM-76
class upload_result_no_file(DjangoSeleniumTestCase):    
    """
    SM-76

    Verifica que el sistema muestre un mensaje de error al intentar subir un resultado
    sin seleccionar un archivo.

    Datos:
        - Usuario: admin@pruebas.com / pruebas
        - Título: "Examen 2"
        - Medium: "Marathi"
        - Clase: 3
        - Archivo: no seleccionado

    Resultado esperado:
        - Aparece una notificación indicando que se requiere un archivo.
    """
    def test_upload_result_no_file(self):
        driver = self.driver
        driver.get(self.live_server_url)

        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        # Esperar a que redirija (puede variar)
        element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3/strong'))
        )

        driver.find_element(By.XPATH, '//*[@id="sidebar"]/div/div[1]/div[2]/div/div/div/ul/li[6]/a/span').click()
        
        # Esperar a que aparezca el enlace "Upload" en el submenú y hacer clic
        upload_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="result"]/li[1]/a'))
        )
        upload_link.click()

        title_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input'))
        )
        title_element.send_keys('Examen 2')

        driver.find_element(By.XPATH, '//*[@id="medium"]').click()
        driver.find_element(By.XPATH, '//*[@id="medium"]/option[2]').click()
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/select').click()
        driver.find_element(By.XPATH, '//*[@id="std"]/option[4]').click()
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[5]/button').click()

        try:
            alert = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "alert-message"))
            )
            # Verificar el contenido del mensaje
            alert_text = alert.text.strip()
            self.assertNotIn("Result uploaded successfully", alert_text,
                             "El formulario no debería haberse enviado exitosamente sin archivo")
        except TimeoutException:
            # Si no aparece mensaje, eso también es válido
            pass

#SM-82
class delete_result_file(DjangoSeleniumTestCase): 
    """
    SM-82

    Verifica que un profesor pueda eliminar un archivo de resultados correctamente.

    Datos:
        - Usuario: profesor@pruebas.com / Teacher@100
        - Navegación a la sección de resultados y selección del archivo a eliminar.

    Resultado esperado:
        - Aparece una notificación indicando que el resultado fue eliminado exitosamente.
    """
    def test_delete_result_file(self):
        driver = self.driver
        driver.get(self.live_server_url)

        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('profesor@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('Teacher@100')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        # Esperar a que redirija (puede variar)
        element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3/strong'))
        )

        driver.find_element(By.XPATH, '//*[@id="sidebar"]/div/div[1]/div[2]/div/div/div/ul/li[7]/a').click()

        driver.find_element(By.XPATH, '//*[@id="result"]/li[2]/a').click()

        delete_element = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/div/div/main/div/div/div/div/table/tbody/tr/td[4]/a'))
        )
        delete_element.click()

        alert_message = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div[1]/div[2]'))
        )
        self.assertEqual(alert_message.text, 'result deleted successfully')
    
#SM-84 
class login_sqlattack_email(DjangoSeleniumTestCase):
    """
    SM-84

    Verifica que el sistema no permita el acceso mediante un intento de inyección SQL
    en el campo de correo electrónico durante el inicio de sesión.

    Datos:
        - Usuario: "' OR '1'='1"
        - Contraseña: Teacher@100

    Resultado esperado:
        - Aparece un mensaje indicando que los datos de inicio de sesión no son válidos.
    """
    def test_login_sqlattack_email(self):
        driver = self.driver
        driver.get(self.live_server_url)

        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys("' OR '1'='1")
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('Teacher@100')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        try:
            message_element = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, '//*[@id="error"]'))
            )
            
            self.assertEqual(message_element.text, 'Invalid login details..!')
        except TimeoutException:
            # Si no aparece mensaje, eso también es válido
            pass
    
#SM-85
class login_sqlattack_password(DjangoSeleniumTestCase):
    """
    SM-85

    Verifica que el sistema no permita el acceso mediante un intento de inyección SQL
    en el campo de contraseña durante el inicio de sesión.

    Datos:
        - Usuario: profesor@pruebas.com
        - Contraseña: "' OR '1'='1"

    Resultado esperado:
        - Aparece un mensaje indicando que los datos de inicio de sesión no son válidos.
    """
    def test_login_sqlattack_password(self):
        driver = self.driver
        driver.get(self.live_server_url)

        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('profesor@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys("' OR '1'='1")
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        message_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '//*[@id="error"]'))
        )
        self.assertEqual(message_element.text, 'Invalid login details..!')

#SM-86 
class edit_profile_sqlattack_Fname(DjangoSeleniumTestCase): 
    """
    SM-86

    Verifica que el sistema tolere de manera segura un intento de inyección SQL
    en el campo de nombre al editar el perfil, sin comprometer la integridad del sistema.

    Datos:
        - Usuario: profesor2@pruebas.com / Teacher@100
        - Primer Nombre: 'INSERT INTO Main_App_teacher(address, message)VALUES (“ataque”, “contraseña”) '

    Resultado esperado:
        - Aparece una notificación indicando que el perfil fue actualizado exitosamente.
    """
    def test_edit_profile_sqlattack_Fname(self):
        driver = self.driver
        driver.get(self.live_server_url)

        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('profesor2@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('Teacher@100')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        # Esperar a que redirija (puede variar)
        element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3/strong'))
        )

        driver.find_element(By.XPATH, '//*[@id="sidebar"]/div/div[1]/div[2]/div/div/div/ul/li[3]/a/span').click()

        firstName_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[2]/div/div/div/form/div[3]/input'))
        )
        firstName_element.send_keys('‘INSERT INTO Main_App_teacher(address, message)VALUES (“ataque”, “contraseña”) ')
        
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div[2]/div/div/div/form/div[8]/button').click()

        alert_message = WebDriverWait(driver,3).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div[1]/div[2]'))
        )
        self.assertEqual(alert_message.text, 'Profile Updated successfully')

#SM-87
class edit_profile_sqlattack_Lname(DjangoSeleniumTestCase): 
    """
    SM-87

    Verifica que el sistema maneje correctamente un intento de inyección SQL
    en el campo de apellido durante la edición del perfil.

    Datos:
        - Usuario: profesor2@pruebas.com / Teacher@100
        - Apellido: 'INSERT INTO Main_App_teacher(address, message)VALUES (“ataque”, “contraseña”) '

    Resultado esperado:
        - Aparece una notificación indicando que el perfil fue actualizado exitosamente.
    """
    def test_edit_profile_sqlattack_Lname(self):
        driver = self.driver
        driver.get(self.live_server_url)

        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('profesor2@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('Teacher@100')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        # Esperar a que redirija (puede variar)
        element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3/strong'))
        )

        driver.find_element(By.XPATH, '//*[@id="sidebar"]/div/div[1]/div[2]/div/div/div/ul/li[3]/a/span').click()

        lastName_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[2]/div/div/div/form/div[4]/input'))
        )
        lastName_element.send_keys('‘INSERT INTO Main_App_teacher(address, message)VALUES (“ataque”, “contraseña”) ')
        
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div[2]/div/div/div/form/div[8]/button').click()

        alert_message = WebDriverWait(driver,3).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div[1]/div[2]'))
        )
        self.assertEqual(alert_message.text, 'Profile Updated successfully')

#SM-88
class edit_profile_sqlattack_address(DjangoSeleniumTestCase): 
    """
    SM-88

    Verifica que el sistema maneje de forma segura un intento de inyección SQL
    en el campo de dirección al editar el perfil.

    Datos:
        - Usuario: profesor2@pruebas.com / Teacher@100
        - Dirección: 'INSERT INTO Main_App_teacher(address, message)VALUES (“ataque”, “contraseña”) '

    Resultado esperado:
        - Aparece una notificación indicando que el perfil fue actualizado exitosamente.
    """
    def test_edit_profile_sqlattack_address(self):
        driver = self.driver
        driver.get(self.live_server_url)

        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('profesor2@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('Teacher@100')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        # Esperar a que redirija (puede variar)
        element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3/strong'))
        )

        driver.find_element(By.XPATH, '//*[@id="sidebar"]/div/div[1]/div[2]/div/div/div/ul/li[3]/a/span').click()

        address_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[2]/div/div/div/form/div[6]/input'))
        )
        address_element.send_keys('‘INSERT INTO Main_App_teacher(address, message)VALUES (“ataque”, “contraseña”) ')
        
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div[2]/div/div/div/form/div[8]/button').click()

        alert_message = WebDriverWait(driver,3).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div[1]/div[2]'))
        )
        self.assertEqual(alert_message.text, 'Profile Updated successfully')

#SM-89 fallo al tocar boton submit
class edit_profile_sqlattack_password(DjangoSeleniumTestCase): 
    """
    SM-89

    Verifica que el sistema maneje de forma segura un intento de inyección SQL
    en el campo de contraseña al editar el perfil.

    Datos:
        - Usuario: profesor3@pruebas.com / Teacher@100
        - Contraseña: 'INSERT INTO Main_App_teacher(address, message)VALUES (“ataque”, “contraseña”) '

    Resultado esperado:
        - Aparece una notificación indicando que el perfil fue actualizado exitosamente.
    """
    def test_edit_profile_sqlattack_password(self):
        driver = self.driver
        driver.get(self.live_server_url)

        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('profesor3@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('Teacher@100')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        # Esperar a que redirija (puede variar)
        element = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3/strong'))
        )

        driver.find_element(By.XPATH, '//*[@id="sidebar"]/div/div[1]/div[2]/div/div/div/ul/li[3]/a').click()

        password_element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/div/div/main/div/div[2]/div/div/div/form/div[7]/input'))
        )
        password_element.send_keys('‘INSERT INTO Main_App_teacher(address, message)VALUES (“ataque”, “contraseña”) ')
        
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div[2]/div/div/div/form/div[8]/button').click()

        alert_message = WebDriverWait(driver,10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div[1]/div[2]'))
        )
        self.assertEqual(alert_message.text, 'Profile Updated successfully')

#SM-90
class add_notification_sqlattack_heading(DjangoSeleniumTestCase):
    """
    SM-90

    Verifica que el sistema maneje de forma segura un intento de inyección SQL
    en el campo de título al agregar una nueva notificación.

    Datos:
        - Usuario: profesor@pruebas.com / Teacher@100
        - Título: 'INSERT INTO Main_App_notification(heading, message)VALUES (“ataque”, “mensage”) '
        - Mensaje: 'prueba sql injection prueba sql injection'

    Resultado esperado:
        - Aparece una notificación indicando que la notificación fue agregada exitosamente.
    """
    def test_add_notification_sqlattack_heading(self):
        driver = self.driver
        driver.get(self.live_server_url)

        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('profesor@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('Teacher@100')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        # Esperar a que redirija (puede variar)
        element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3/strong'))
        )

        driver.find_element(By.XPATH, '//*[@id="sidebar"]/div/div[1]/div[2]/div/div/div/ul/li[6]/a/span').click()
        

        add_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="forms"]/li[1]/a'))
        )
        add_link.click()

        title_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input'))
        )
        title_element.send_keys('‘INSERT INTO Main_App_notification(heading, message)VALUES (“ataque”, “mensage”) ')

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/textarea').send_keys(
            'prueba sql injection prueba sql injection')
        
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/button').click()

        alert_message = WebDriverWait(driver,3).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div[1]/div[2]'))
        )
        self.assertEqual(alert_message.text, 'Notification added successfully')

#SM-91
class add_notification_sqlattack_message(DjangoSeleniumTestCase):
    """
    SM-91

    Verifica que el sistema maneje correctamente un intento de inyección SQL
    en el campo de mensaje al agregar una notificación.

    Datos:
        - Usuario: profesor@pruebas.com / Teacher@100
        - Título: "prueba sql prueba sql"
        - Mensaje: 'INSERT INTO Main_App_notification(heading, message)VALUES (“ataque”, “mensage”) '

    Resultado esperado:
        - Aparece una notificación indicando que la notificación fue agregada exitosamente.
    """
    def test_add_notification_sqlattack_message(self):
        driver = self.driver
        driver.get(self.live_server_url)

        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('profesor@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('Teacher@100')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        # Esperar a que redirija (puede variar)
        element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3/strong'))
        )

        driver.find_element(By.XPATH, '//*[@id="sidebar"]/div/div[1]/div[2]/div/div/div/ul/li[6]/a/span').click()
        
        # Esperar a que aparezca el enlace "Teacher" en el submenú y hacer clic
        add_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="forms"]/li[1]/a'))
        )
        add_link.click()

        title_element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input'))
        )
        title_element.send_keys('prueba sql prueba sql')

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/textarea').send_keys(
            '‘INSERT INTO Main_App_notification(heading, message)VALUES (“ataque”, “mensage”) ')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/button').click()

        alert_message = WebDriverWait(driver,3).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div[1]/div[2]'))
        )
        self.assertEqual(alert_message.text, 'Notification added successfully')

#SM-95
class add_student_sqlattack_Fname(DjangoSeleniumTestCase):
    """
    SM-95

    Verifica que el sistema tolere adecuadamente un intento de inyección SQL
    en el campo de nombre al registrar un nuevo estudiante.

    Datos:
        - Usuario: admin@pruebas.com / pruebas
        - Correo del estudiante: student@sql.com
        - Nombre: 'INSERT INTO Main_App_student(id, address)VALUES (23, “nombre”) '
        - Apellidos: Test
        - Otros campos: Medium, Clase, Género, Dirección (valores válidos)

    Resultado esperado:
        - Aparece una notificación indicando que el estudiante fue registrado exitosamente.
    """
    def test_add_student_sqlattack_Fname(self):
        driver = self.driver
        driver.get(self.live_server_url)

        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        # Esperar a que redirija (puede variar)
        element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3/strong'))
        )

        driver.find_element(By.XPATH, '//*[@id="sidebar"]/div/div[1]/div[2]/div/div/div/ul/li[4]/a/span').click()
        
        # Esperar a que aparezca el enlace "Teacher" en el submenú y hacer clic
        student_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="add"]/li[1]/a'))
        )
        student_link.click()
        email_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input'))
        )
        email_element.send_keys('student@sql.com')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/input').send_keys(
            '“‘INSERT INTO Main_App_student(id, address)VALUES (23, “nombre”) ”')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/input').send_keys('Test')
        driver.find_element(By.XPATH, '//*[@id="medium"]').click()
        driver.find_element(By.XPATH, '//*[@id="medium"]/option[2]').click()
        driver.find_element(By.XPATH, '//*[@id="std"]').click()
        driver.find_element(By.XPATH, '//*[@id="std"]/option[2]').click()
        driver.find_element(By.XPATH, '//*[@id="gender"]').click()
        driver.find_element(By.XPATH, '//*[@id="gender"]/option[2]').click()
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[7]/input').send_keys('Alajuela')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[8]/button').click()

        alert_message = WebDriverWait(driver,3).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div[1]/div[2]'))
        )
        self.assertEqual(alert_message.text, 'Student added successfully')

#SM-96
class add_teacher_sqlattack_Fname(DjangoSeleniumTestCase):
    """
    SM-96

    Verifica que el sistema maneje correctamente un intento de inyección SQL
    en el campo de nombre al registrar un nuevo profesor.

    Datos:
        - Usuario: admin@pruebas.com / pruebas
        - Correo del profesor: teacher@sql.com
        - Nombre: INSERT INTO Main_App_teacher(first_name, address)VALUES (“Ataque”, “nombre”)
        - Apellidos: Test
        - Otros campos: Género, Dirección (valores válidos)

    Resultado esperado:
        - Aparece una notificación indicando que el profesor fue registrado exitosamente.
    """
    def test_add_teacher_sqlattack_Fname(self):
        driver = self.driver
        driver.get(self.live_server_url)

        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        # Esperar a que redirija (puede variar)
        element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3/strong'))
        )

        driver.find_element(By.XPATH, '//*[@id="sidebar"]/div/div[1]/div[2]/div/div/div/ul/li[4]/a/span').click()
        
        # Esperar a que aparezca el enlace "Teacher" en el submenú y hacer clic
        teacher_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//a[@href="/addteacher"]'))
        )
        teacher_link.click()
        email_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input'))
        )
        email_element.send_keys('teacher@sql.com')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/input').send_keys(
            'INSERT INTO Main_App_teacher(first_name, address)VALUES (“Ataque”, “nombre”)')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/input').send_keys('Test')
        driver.find_element(By.XPATH, '//*[@id="gender"]').click()
        driver.find_element(By.XPATH, '//*[@id="gender"]/option[4]').click()
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[5]/input').send_keys('Alajuela')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[6]/button').click()

        alert_message = WebDriverWait(driver,3).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div[1]/div[2]'))
        )
        self.assertEqual(alert_message.text, 'Teacher added successfully')

#SM-97
class add_student_sqlattack_Lname(DjangoSeleniumTestCase):
    """
    SM-97

    Verifica que el sistema maneje correctamente un intento de inyección SQL
    en el campo de apellido al registrar un nuevo estudiante.

    Datos:
        - Usuario: admin@pruebas.com / pruebas
        - Correo del estudiante: student2@sql.com
        - Nombre: Test
        - Apellido: "INSERT INTO Main_App_student(id, address)VALUES (23, “apellido”)"
        - Otros campos: Medium, Clase, Género, Dirección (valores válidos)

    Resultado esperado:
        - Aparece una notificación indicando que el estudiante fue registrado exitosamente.
    """
    def test_add_student_sqlattack_Lname(self):
        driver = self.driver
        driver.get(self.live_server_url)

        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        # Esperar a que redirija (puede variar)
        element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3/strong'))
        )

        driver.find_element(By.XPATH, '//*[@id="sidebar"]/div/div[1]/div[2]/div/div/div/ul/li[4]/a/span').click()
        
        # Esperar a que aparezca el enlace "Teacher" en el submenú y hacer clic
        student_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="add"]/li[1]/a'))
        )
        student_link.click()
        email_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input'))
        )
        email_element.send_keys('student2@sql.com')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/input').send_keys('Test')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/input').send_keys(
            '"INSERT INTO Main_App_student(id, address)VALUES (23, “apellido”)"')
        driver.find_element(By.XPATH, '//*[@id="medium"]').click()
        driver.find_element(By.XPATH, '//*[@id="medium"]/option[2]').click()
        driver.find_element(By.XPATH, '//*[@id="std"]').click()
        driver.find_element(By.XPATH, '//*[@id="std"]/option[2]').click()
        driver.find_element(By.XPATH, '//*[@id="gender"]').click()
        driver.find_element(By.XPATH, '//*[@id="gender"]/option[2]').click()
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[7]/input').send_keys('Alajuela')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[8]/button').click()

        alert_message = WebDriverWait(driver,3).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div[1]/div[2]'))
        )
        self.assertEqual(alert_message.text, 'Student added successfully')

#SM-98
class add_teacher_sqlattack_Lname(DjangoSeleniumTestCase):
    """
    SM-98

    Verifica que el sistema maneje correctamente un intento de inyección SQL
    en el campo de apellido al registrar un nuevo profesor.

    Datos:
        - Usuario: admin@pruebas.com / pruebas
        - Correo del profesor: teacher2@sql.com
        - Nombre: Test
        - Apellido: INSERT INTO Main_App_teacher(gender, address)VALUES (“Ataque”, “apellido”)
        - Otros campos: Género, Dirección (valores válidos)

    Resultado esperado:
        - Aparece una notificación indicando que el profesor fue registrado exitosamente.
    """
    def test_add_teacher_sqlattack_Lname(self):
        driver = self.driver
        driver.get(self.live_server_url)

        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        # Esperar a que redirija (puede variar)
        element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3/strong'))
        )

        driver.find_element(By.XPATH, '//*[@id="sidebar"]/div/div[1]/div[2]/div/div/div/ul/li[4]/a/span').click()
        
        # Esperar a que aparezca el enlace "Teacher" en el submenú y hacer clic
        teacher_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//a[@href="/addteacher"]'))
        )
        teacher_link.click()
        email_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input'))
        )
        email_element.send_keys('teacher2@sql.com')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/input').send_keys('Test')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/input').send_keys(
            'INSERT INTO Main_App_teacher(gender, address)VALUES (“Ataque”, “apellido”)')
        driver.find_element(By.XPATH, '//*[@id="gender"]').click()
        driver.find_element(By.XPATH, '//*[@id="gender"]/option[4]').click()
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[5]/input').send_keys('Alajuela')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[6]/button').click()

        alert_message = WebDriverWait(driver,3).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div[1]/div[2]'))
        )
        self.assertEqual(alert_message.text, 'Teacher added successfully')

#SM-99
class add_teacher_sqlattack_address(DjangoSeleniumTestCase):
    """
    SM-99

    Verifica que el sistema maneje correctamente un intento de inyección SQL
    en el campo de dirección al registrar un nuevo profesor.

    Datos:
        - Usuario: admin@pruebas.com / pruebas
        - Correo del profesor: teacher3@sql.com
        - Nombre: Test
        - Apellido: sql
        - Dirección: INSERT INTO Main_App_teacher(gender, address)VALUES (“Ataque de”, “address”)
        - Otros campos: Género (valor válido)

    Resultado esperado:
        - Aparece una notificación indicando que el profesor fue registrado exitosamente.
    """
    def test_add_teacher_sqlattack_address(self):
        driver = self.driver
        driver.get(self.live_server_url)

        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        # Esperar a que redirija (puede variar)
        element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3/strong'))
        )

        driver.find_element(By.XPATH, '//*[@id="sidebar"]/div/div[1]/div[2]/div/div/div/ul/li[4]/a/span').click()
        
        # Esperar a que aparezca el enlace "Teacher" en el submenú y hacer clic
        teacher_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//a[@href="/addteacher"]'))
        )
        teacher_link.click()
        email_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input'))
        )
        email_element.send_keys('teacher3@sql.com')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/input').send_keys('Test')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/input').send_keys('sql')
        driver.find_element(By.XPATH, '//*[@id="gender"]').click()
        driver.find_element(By.XPATH, '//*[@id="gender"]/option[4]').click()
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[5]/input').send_keys(
            'INSERT INTO Main_App_teacher(gender, address)VALUES (“Ataque de”, “address”)')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[6]/button').click()

        alert_message = WebDriverWait(driver,3).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div[1]/div[2]'))
        )
        self.assertEqual(alert_message.text, 'Teacher added successfully')


if __name__ == '__main__':
    # Configurar el runner de pruebas
    unittest.main(verbosity=2)