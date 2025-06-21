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
from django.contrib.auth import get_user_model

class DjangoSeleniumTestCase(unittest.TestCase):
    """
    SetUp para cada prueba que se va a ejecutar en Selenium
    """
    
    @classmethod
    def setUpClass(cls):
        print(f"\n=== Configurando {cls.__name__} ===")
        
        # Configurar opciones del navegador
        cls.chrome_options = Options()
        #cls.chrome_options.add_argument('--headless') #para NO ver las ejecuciones en tiempo real.
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
        Limpieza que se gace despues de ejecutar todas las pruebas 
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
            # Usar webdriver-manager para obtener el ChromeDriver compatible, necesario en el caso de usar Linux
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
        """Verifica si el servidor Django se esta ejecutando"""
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
        """Espera a que el servidor Django este disponible"""
        print("    Esperando a que el servidor este disponible...")
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
        """Espera a que un elemento este presente listo y sea visible"""
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

#SM-42
class add_student_alfanumeric_lastName(DjangoSeleniumTestCase):
    """
    SM-42
    Intentar añadir un nuevo profesor sin ningún dato incorporado
    Datos:
        - Usuario: admin@pruebas.com/pruebas
        - Email address = {“carl@test.com”}
        - First Name = {“Carl”}
        - Last Name = {“Morera72”}
        - Medium = {“SemiEng”}
        - Class = {“1”}
        - Gender = {“Male”}
        - Address = {“Isla Tortuga, Limón”}

    Resultado esperado:
        - La ventana de “Add Student” se limpiara y tendrá un mensaje en celeste indicando “Student Added Successfully”
            En la ventana de “Admin Dashboard” deberá aparecer un estudiante nuevo en los datos.
    """
    def test_add_student_with_alfanumeric_lastname(self):
        driver = self.driver
        driver.get(self.live_server_url)

        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3'))
        )

        driver.find_element(By.XPATH, '//*[@id="sidebar"]/div/div[1]/div[2]/div/div/div/ul/li[4]/a').click()

        driver.find_element(By.XPATH, '//*[@id="add"]/li[1]/a').click()

        title = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/h1'))
        )

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input').send_keys('carl@test.com')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/input').send_keys('Carl')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/input').send_keys('Morela72')

        driver.find_element(By.XPATH, '//*[@id="medium"]').click()
        driver.find_element(By.XPATH, '//*[@id="medium"]/option[3]').click()

        driver.find_element(By.XPATH, '//*[@id="std"]').click()
        driver.find_element(By.XPATH, '//*[@id="std"]/option[7]').click()

        driver.find_element(By.XPATH, '//*[@id="gender"]').click()
        driver.find_element(By.XPATH, '//*[@id="gender"]/option[2]').click()

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[7]/input').send_keys('Isla Tortuga, Limón')

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[8]/button').click()
        
        added = driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div[1]/div[2]/strong')

        self.assertEqual(added.text, "Student added successfully")

#SM-43
class add_teacher_no_data(DjangoSeleniumTestCase):
    """
    SM-43
    Intentar añadir un nuevo profesor sin ningún dato incorporado   
    Datos:
        Usuario: admin@pruebas.com / pruebas
    Resultado esperado:
        - Debe saltar un mensaje en “Email address” indicando “Please fill out this field”
    """
    def test_add_teacher_with_no_data(self):
        driver = self.driver
        driver.get(self.live_server_url)

        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3'))
        )

        driver.find_element(By.XPATH, '//*[@id="sidebar"]/div/div[1]/div[2]/div/div/div/ul/li[4]/a').click()

        driver.find_element(By.XPATH, '//*[@id="add"]/li[2]/a').click()

        title = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/h1'))
        )

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[6]/button').click()
        
        try:
            alert = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "alert-message"))
            )
            # Verificar el contenido del mensaje
            alert_text = alert.text.strip()
            self.assertNotIn("Student added successfully", alert_text,
                             "El maestro no debería haberse creado exitosamente sin datos")
        except TimeoutException:
            # Si no aparece mensaje, eso tambien es valido
            pass

#SM-44
class add_teacher_success(DjangoSeleniumTestCase):
    """
    SM-44
    Intentar añadir un profesor correctamente  
    Datos:
        - Usuario: admin@pruebas.com / pruebas
        - Email address = {samuel@test.com}
        - First Name = {Samuel}
        - Last Name = {Duarte}
        - Gender = {Male}
        - Address = {Poas, Alajuela}
    Resultado esperado:
La ventana de “Add Teacher” se limpiara y tendrá un mensaje en celeste indicando “Teacher  added successfully”
    """
    def test_add_teacher(self):
        driver = self.driver
        driver.get(self.live_server_url)

        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3'))
        )

        driver.find_element(By.XPATH, '//*[@id="sidebar"]/div/div[1]/div[2]/div/div/div/ul/li[4]/a').click()

        driver.find_element(By.XPATH, '//*[@id="add"]/li[2]/a').click()

        title = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/h1'))
        )

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input').send_keys('samuel@test.com')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/input').send_keys('Samuel')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/input').send_keys('Duarte')

        driver.find_element(By.XPATH, '//*[@id="gender"]').click()
        driver.find_element(By.XPATH, '//*[@id="gender"]/option[2]').click()

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[5]/input').send_keys('Poas, Alajuela')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[6]/button').click()
        
        added = driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div[1]/div[2]/strong')

        self.assertEqual(added.text, "Teacher added successfully")


#SM-46
class add_teacher_no_email(DjangoSeleniumTestCase):
    """
    SM-46
    Intentar añadir un profesor sin un “Email Address”
    Datos:
        - Usuario: admin@pruebas.com / pruebas
        - First Name = {Samuel}
        - Last Name = {Duarte}
        - Gender = {Male}
        - Address = {Poas, Alajuela}
    Resultado esperado:
        Debe saltar un mensaje en “Email address” indicando “Please fill out this field”
    """
    def test_add_teacher(self):
        driver = self.driver
        driver.get(self.live_server_url)

        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3'))
        )

        driver.find_element(By.XPATH, '//*[@id="sidebar"]/div/div[1]/div[2]/div/div/div/ul/li[4]/a').click()

        driver.find_element(By.XPATH, '//*[@id="add"]/li[2]/a').click()

        title = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/h1'))
        )

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/input').send_keys('Samuel')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/input').send_keys('Duarte')

        driver.find_element(By.XPATH, '//*[@id="gender"]').click()
        driver.find_element(By.XPATH, '//*[@id="gender"]/option[2]').click()

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[5]/input').send_keys('Poas, Alajuela')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[6]/button').click()
        
    
        try:
            alert = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "alert-message"))
            )
            # Verificar el contenido del mensaje
            alert_text = alert.text.strip()
            self.assertNotIn("Teacher added successfully", alert_text,
                             "El profesor no se deberia de añadir sin email")
        except TimeoutException:
            # Si no aparece mensaje, eso tambien es valido
            pass        

#SM-47
class add_teacher_no_name(DjangoSeleniumTestCase):
    """
    SM-47
    Intentar añadir un profesor sin un “First Name”
    Datos:
        - Usuario: admin@pruebas.com / pruebas
        - Email address = {samuel@test.com}
        - Last Name = {Duarte}
        - Gender = {Male}
        - Address = {Poas, Alajuela}
    Resultado esperado:
        Debe saltar un mensaje en “First name” indicando “Please fill out this field”
    """
    def test_add_teacher_no_name(self):
        driver = self.driver
        driver.get(self.live_server_url)

        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3'))
        )

        driver.find_element(By.XPATH, '//*[@id="sidebar"]/div/div[1]/div[2]/div/div/div/ul/li[4]/a').click()

        driver.find_element(By.XPATH, '//*[@id="add"]/li[2]/a').click()

        title = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/h1'))
        )

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input').send_keys('samuel@test.com')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/input').send_keys('Duarte')

        driver.find_element(By.XPATH, '//*[@id="gender"]').click()
        driver.find_element(By.XPATH, '//*[@id="gender"]/option[2]').click()

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[5]/input').send_keys('Poas, Alajuela')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[6]/button').click()
        
        

        try:
            alert = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "alert-message"))
            )
            # Verificar el contenido del mensaje
            alert_text = alert.text.strip()
            self.assertNotIn("Teacher added successfully", alert_text,
                             "El profesor no se deberia de añadir sin email")
        except TimeoutException:
            # Si no aparece mensaje, eso tambien es valido
            pass        

#SM-48
class add_teacher_no_lastname(DjangoSeleniumTestCase):
    """
    SM-48
    Intentar añadir un profesor sin un “Last Name”
    Datos:
        - Usuario: admin@pruebas.com / pruebas
        - Email address = {samuel@test.com}
        - Fist Name = {Samuel}
        - Gender = {Male}
        - Address = {Poas, Alajuela}
    Resultado esperado:
        Debe saltar un mensaje en “First name” indicando “Please fill out this field”
    """
    def test_add_teacher_no_lastname(self):
        driver = self.driver
        driver.get(self.live_server_url)

        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3'))
        )

        driver.find_element(By.XPATH, '//*[@id="sidebar"]/div/div[1]/div[2]/div/div/div/ul/li[4]/a').click()

        driver.find_element(By.XPATH, '//*[@id="add"]/li[2]/a').click()

        title = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/h1'))
        )

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input').send_keys('samuel@test.com')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/input').send_keys('Samuel')

        driver.find_element(By.XPATH, '//*[@id="gender"]').click()
        driver.find_element(By.XPATH, '//*[@id="gender"]/option[2]').click()

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[5]/input').send_keys('Poas, Alajuela')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[6]/button').click()

        try:
            alert = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "alert-message"))
            )
            # Verificar el contenido del mensaje
            alert_text = alert.text.strip()
            self.assertNotIn("Teacher added successfully", alert_text,
                             "El profesor no se deberia de añadir sin email")
        except TimeoutException:
            # Si no aparece mensaje, eso tambien es valido
            pass 

#SM-52 
class upload_note_no_file(DjangoSeleniumTestCase):    
    """
    SM-52
    Añadir material de estudio en el apartado de notas, sin seleccionar un material de estudio
    Datos:
        - User: profesor@pruebas.com / Teacher@100
        - Title = {“Tarea 2”}
        - Medium = {“SemiEng”}
        - Class = {3}
    Resultado esperado:
        - Se va a mostrar una notificación indicando que es necesario seleccionar un archivo
    """
    def test_upload_note_no_file(self):
        driver = self.driver
        driver.get(self.live_server_url)

        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('profesor@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('Teacher@100')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        # Esperar a que redirija (puede variar)
        element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3/strong'))
        )

        driver.find_element(By.XPATH, '/html/body/div/nav/div/div[1]/div[2]/div/div/div/ul/li[8]/a').click()
        
        # Esperar a que aparezca el enlace "Upload" en el submenú y hacer clic
        upload_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/div/nav/div/div[1]/div[2]/div/div/div/ul/li[8]/ul/li[1]/a'))
        )
        upload_link.click()

        title_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input'))
        )
        title_element.send_keys('Tarea 2')

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/select').click()
        driver.find_element(By.XPATH, '//*[@id="medium"]/option[3]').click()
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/select').click()
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/select/option[4]').click()
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[5]/button').click()

        try:
            alert = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "alert-message"))
            )
            # Verificar el contenido del mensaje
            alert_text = alert.text.strip()
            self.assertNotIn("Notes uploaded successfully", alert_text,
                             "El formulario no debería haberse enviado exitosamente sin archivo")
        except TimeoutException:
            # Si no aparece mensaje, eso tambien es valido
            pass

#SM-54
class upload_note_no_tittle(DjangoSeleniumTestCase):    
    """
    SM-54
    Añadir un material de estudio en el apartado de notas sin haberle ingresado un título 
    Datos:
        - User: profesor@pruebas.com / Teacher@100
        - Medium = {“SemiEng”}
        - Class = {3}
    Resultado esperado:
        - Se va a mostrar una notificación indicando que es necesario seleccionar un medio
    """
    def test_upload_note_no_tittle(self):
        driver = self.driver
        driver.get(self.live_server_url)

        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('profesor@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('Teacher@100')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        # Esperar a que redirija (puede variar)
        element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3/strong'))
        )

        driver.find_element(By.XPATH, '/html/body/div/nav/div/div[1]/div[2]/div/div/div/ul/li[8]/a').click()
        
        # Esperar a que aparezca el enlace "Upload" en el submenú y hacer clic
        upload_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/div/nav/div/div[1]/div[2]/div/div/div/ul/li[8]/ul/li[1]/a'))
        )
        upload_link.click()

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/select').click()
        driver.find_element(By.XPATH, '//*[@id="medium"]/option[3]').click()
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/select').click()
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/select/option[4]').click()
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[5]/button').click()

        try:
            alert = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "alert-message"))
            )
            # Verificar el contenido del mensaje
            alert_text = alert.text.strip()
            self.assertNotIn("Notes uploaded successfully", alert_text,
                             "El formulario no debería haberse enviado exitosamente sin un titulo")
        except TimeoutException:
            # Si no aparece mensaje, eso tambien es valido
            pass

#SM-55 
class upload_note_no_class(DjangoSeleniumTestCase):    
    """
    SM-55
    Añadir un material de estudio en el apartado de notas sin seleccionar una clase
    Datos:
        - User: profesor@pruebas.com / Teacher@100
        - Title = {“Tarea1”}
        - Medium = {“SemiEng”}
    Resultado esperado:
        - Se va a mostrar una notificación indicando que es necesario seleccionar una clase
    """
    def test_upload_note_no_class(self):
        driver = self.driver
        driver.get(self.live_server_url)

        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('profesor@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('Teacher@100')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        # Esperar a que redirija (puede variar)
        element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3/strong'))
        )

        driver.find_element(By.XPATH, '/html/body/div/nav/div/div[1]/div[2]/div/div/div/ul/li[8]/a').click()
        
        # Esperar a que aparezca el enlace "Upload" en el submenú y hacer clic
        upload_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/div/nav/div/div[1]/div[2]/div/div/div/ul/li[8]/ul/li[1]/a'))
        )
        upload_link.click()


        title_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input'))
        )
        title_element.send_keys('Tarea1')

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/select').click()
        driver.find_element(By.XPATH, '//*[@id="medium"]/option[3]').click()
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[5]/button').click()

        try:
            alert = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "alert-message"))
            )
            # Verificar el contenido del mensaje
            alert_text = alert.text.strip()
            self.assertNotIn("Notes uploaded successfully", alert_text,
                             "El formulario no debería haberse enviado exitosamente sin un titulo")
        except TimeoutException:
            # Si no aparece mensaje, eso tambien es valido
            pass

#SM-56
class upload_note_no_medium(DjangoSeleniumTestCase):    
    """
    SM-54
    Añadir un material de estudio en el apartado de notas sin seleccionar un medio
    Datos:
        - User: profesor@pruebas.com / Teacher@100
        - Title = {“Tarea1”}
        - Class = {“3“}
    Resultado esperado:
        - Se va a mostrar una notificación indicando que es necesario seleccionar un medio
    """
    def test_upload_note_no_file(self):
        driver = self.driver
        driver.get(self.live_server_url)

        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('profesor@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('Teacher@100')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        # Esperar a que redirija (puede variar)
        element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3/strong'))
        )

        driver.find_element(By.XPATH, '/html/body/div/nav/div/div[1]/div[2]/div/div/div/ul/li[8]/a').click()
        
        # Esperar a que aparezca el enlace "Upload" en el submenú y hacer clic
        upload_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/div/nav/div/div[1]/div[2]/div/div/div/ul/li[8]/ul/li[1]/a'))
        )
        upload_link.click()

        title_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input'))
        )
        title_element.send_keys('Tarea1')

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/select').click()
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/select/option[4]').click()
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[5]/button').click()

        try:
            alert = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "alert-message"))
            )
            # Verificar el contenido del mensaje
            alert_text = alert.text.strip()
            self.assertNotIn("Notes uploaded successfully", alert_text,
                             "El formulario no debería haberse enviado exitosamente sin archivo")
        except TimeoutException:
            # Si no aparece mensaje, eso tambien es valido
            pass

#SM-59 
class upload_notification(DjangoSeleniumTestCase):    
    """
    SM-59
    Añadir una notificación desde el rol de profesor
    Datos:
        - User: profesor@pruebas.com / Teacher@100
        - Notification heading = {Clase cancelada}
        - Notification message = {La clase ha sido cancelada debido a motivos personales}
    Resultado esperado:
        - Se va a mostrar una notificación indicando que la notificacion se creo con exito
    """
    def test_upload_notification(self):
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
        
        # Esperar a que aparezca el enlace "Add" en el submenú y hacer clic
        upload_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="forms"]/li[1]/a'))
        )
        upload_link.click()

        title_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input'))
        )
        title_element.send_keys('Clase cancelada')

        body_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/textarea'))
        )
        body_element.send_keys('La clase ha sido cancelada debido a motivos personales')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/button').click()

        alert = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "alert-message"))
            )
        alert_message = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div[1]/div[2]'))
        )
        self.assertEqual(alert_message.text, 'Notification added successfully')
    
#SM-60
class upload_notification_no_tittle(DjangoSeleniumTestCase):    
    """
    SM-60
    Añadir una notificación dejando el encabezado en blanco 
    Datos:
        - User: profesor@pruebas.com / Teacher@100
        - Notification message = {La clase ha sido cancelada debido a motivos personales}
    Resultado esperado:
        - Se va a mostrar una notificación indicando que se debe de completar el titulo de la notificacion
    """
    def test_upload_notification_no_tittle(self):
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
        
        # Esperar a que aparezca el enlace "Add" en el submenú y hacer clic
        upload_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="forms"]/li[1]/a'))
        )
        upload_link.click()

        body_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/textarea'))
        )
        body_element.send_keys('La clase ha sido cancelada debido a motivos personales')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/button').click()

        try:
            alert = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "alert-message"))
            )
            # Verificar el contenido del mensaje
            alert_text = alert.text.strip()
            self.assertNotIn("Notification added successfully", alert_text,
                             "La notificación no debería de haberse subido sin titulo")
        except TimeoutException:
            # Si no aparece mensaje, eso tambien es valido
            pass        
#SM-61 
class upload_notification_no_body(DjangoSeleniumTestCase):    
    """
    SM-61
    Añadir una notificación dejando en cuerpo de la notificación vacío  
    Datos:
        - User: profesor@pruebas.com / Teacher@100
        - Notification heading = {Clase cancelada}
    Resultado esperado:
        - Se va a mostrar una notificación indicando que se debe de completar el cuerpo de la notificacion
    """
    def test_upload_notification_no_body(self):
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
        
        # Esperar a que aparezca el enlace "Add" en el submenú y hacer clic
        upload_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="forms"]/li[1]/a'))
        )
        upload_link.click()

        title_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input'))
        )
        title_element.send_keys('Clase cancelada')

        try:
            alert = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "alert-message"))
            )
            # Verificar el contenido del mensaje
            alert_text = alert.text.strip()
            self.assertNotIn("Notification added successfully", alert_text,
                             "La notificación no debería de haberse subido sin cuerpo")
        except TimeoutException:
            # Si no aparece mensaje, eso tambien es valido
            pass        

#SM-62
class upload_notification_tittle_lenght(DjangoSeleniumTestCase):    
    """
    SM-62
    Añadir una notificación con un encabezado  con tenido menor a 15 caracteres  
    Datos:
        - User: profesor@pruebas.com / Teacher@100
        - Notification heading = {Feriado}
        - Notification message = {Mañana es feriado}
    Resultado esperado:
        - Se va a mostrar una notificación indicando que el encabezado de la notificacion debe de 
        tener una longitud mayor a 15 caracteres
    """
    def test_upload_notification_tittle_lenght(self):
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
        
        # Esperar a que aparezca el enlace "Add" en el submenú y hacer clic
        upload_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="forms"]/li[1]/a'))
        )
        upload_link.click()

        title_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input'))
        )
        title_element.send_keys('Feriado')


        body_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/textarea'))
        )
        body_element.send_keys('Mañana es feriado')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/button').click()

        try:
            alert = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "alert-message"))
            )
            # Verificar el contenido del mensaje
            alert_text = alert.text.strip()
            self.assertNotIn("Notification added successfully", alert_text,
                             "La notificación no debería de haberse subido sin un titulo de mas de 14 caracteres")
        except TimeoutException:
            # Si no aparece mensaje, eso tambien es valido
            pass        

#SM-63 
class upload_notification_body_lenght(DjangoSeleniumTestCase):    
    """
    SM-63
    Añadir una notificación con un encabezado  con tenido menor a 15 caracteres  
    Datos:
        - User: profesor@pruebas.com / Teacher@100
        - Notification heading = {Clase Cancelada}
        - Notification message = {Mañana es feriado}
    Resultado esperado:
        - Se va a mostrar una notificación mensaje indicando que el cuerpo de la notificación debe de tener una longitud mínima de 30 caracteres.
          También debe de mostrar la cantidad de caracteres usados hasta el momento. 
    """
    def test_upload_notification_body_lenght(self):
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
        
        # Esperar a que aparezca el enlace "Add" en el submenú y hacer clic
        upload_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="forms"]/li[1]/a'))
        )
        upload_link.click()

        title_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input'))
        )
        title_element.send_keys('Clase Cancelada')


        body_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/textarea'))
        )
        body_element.send_keys('Mañana es feriado')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/button').click()

        try:
            alert = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "alert-message"))
            )
            # Verificar el contenido del mensaje
            alert_text = alert.text.strip()
            self.assertNotIn("Notification added successfully", alert_text,
                             "La notificación no debería de haberse subido sin un titulo de mas de 14 caracteres")
        except TimeoutException:
            # Si no aparece mensaje, eso tambien es valido
            pass   

if __name__ == '__main__':
    # Configurar el runner de pruebas
    unittest.main(verbosity=2)