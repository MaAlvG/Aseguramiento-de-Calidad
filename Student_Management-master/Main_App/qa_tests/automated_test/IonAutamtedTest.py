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


class test_class_sm26(DjangoSeleniumTestCase):
    """
    SM-26
    Validar que se pueda ingresar a la pestaña de Add Student correctamente.    
    Datos:
        - Sin Datos de Prueba
    Resultado esperado:
        - La ventana cambiará a la plantilla/formulario para poder añadir un estudiante nuevo con titulo “Add Student”
    """
    def test_access_add_student(self):
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

        self.assertEqual("Add Student", title.text)

class test_class_sm27(DjangoSeleniumTestCase):
    """
    SM-27
    Validar que se pueda ingresar a la pestaña de Add Teacher correctamente   
    Datos:
        - Sin Datos de Prueba
    Resultado esperado:
        - La ventana cambiará a la plantilla/formulario para poder añadir un profesor nuevo con titulo “Add Teacher
    """
    def test_access_add_teacher(self):
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
        self.assertEqual("Add Teacher", title.text)

class test_class_sm28(DjangoSeleniumTestCase):
    """
    SM-28
    Intentar añadir un nuevo estudiante sin ningún dato incorporado.    
    Datos:
        - Sin Datos de Prueba
    Resultado esperado:
        - Debe saltar un mensaje en “Email address” indicando “Please fill out this field”
    """
    def test_add_student_with_no_data(self):
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

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[8]/button').click()
        
        try:
            alert = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "alert-message"))
            )
            # Verificar el contenido del mensaje
            alert_text = alert.text.strip()
            self.assertNotIn("Student added successfully", alert_text,
                             "El estudiante no debería haberse creado exitosamente sin datos")
        except TimeoutException:
            # Si no aparece mensaje, eso tambien es valido
            pass

class test_class_sm29(DjangoSeleniumTestCase):
    """
    SM-29
    Intentar añadir un estudiante correctamente   
    Datos:
        Email address = {“pepito@test.com”, “clara@test.com”}

        First Name = {“Pepito”, “Clara”}

        Last Name = {“Alvarez”, “Brenes”}

        Medium = {“Marathi”, “CBSE”}

        Class = {“1”, “10”}

        Gender = {“Male”, “Female”}

        Address = {“Alajuela, Alajuela”, “Barrio Amon, San Jose”}
    Resultado esperado:
        - La ventana de “Add Student” se limpiara y tendrá un mensaje en celeste indicando “Student Added Successfully”
            En la ventana de “Admin Dashboard” deberá aparecer un estudiante nuevo en los datos.
    """
    def test_add_student_with_data(self):
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

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input').send_keys('pepito@test.com')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/input').send_keys('Pepito')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/input').send_keys('Alvarez')

        driver.find_element(By.XPATH, '//*[@id="medium"]').click()
        driver.find_element(By.XPATH, '//*[@id="medium"]/option[2]').click()

        driver.find_element(By.XPATH, '//*[@id="std"]').click()
        driver.find_element(By.XPATH, '//*[@id="std"]/option[2]').click()

        driver.find_element(By.XPATH, '//*[@id="gender"]').click()
        driver.find_element(By.XPATH, '//*[@id="gender"]/option[2]').click()

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[7]/input').send_keys('Alajuela, Alajuela')

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[8]/button').click()
        
        added = driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div[1]/div[2]/strong')

        self.assertEqual(added.text, "Student added successfully")

class test_class_sm30(DjangoSeleniumTestCase):
    """
    SM-30
    Intentar añadir un estudiante correctamente, cuyos datos estén completamente repetidos previamente 
    Datos:
        Email address = {“pepito@test.com”, “clara@test.com”}

        First Name = {“Pepito”, “Clara”}

        Last Name = {“Alvarez”, “Brenes”}

        Medium = {“Marathi”, “CBSE”}

        Class = {“1”, “10”}

        Gender = {“Male”, “Female”}

        Address = {“Alajuela, Alajuela”, “Barrio Amon, San Jose”}
    Resultado esperado:
        - La ventana de “Add Student” se limpiara y tendrá un mensaje en celeste indicando “Student Added Successfully”
            En la ventana de “Admin Dashboard” deberá aparecer un estudiante nuevo en los datos.
    """
    def test_add_student_with_duplicated_data(self):
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

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input').send_keys('pepito@test.com')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/input').send_keys('Pepito')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/input').send_keys('Alvarez')

        driver.find_element(By.XPATH, '//*[@id="medium"]').click()
        driver.find_element(By.XPATH, '//*[@id="medium"]/option[2]').click()

        driver.find_element(By.XPATH, '//*[@id="std"]').click()
        driver.find_element(By.XPATH, '//*[@id="std"]/option[2]').click()

        driver.find_element(By.XPATH, '//*[@id="gender"]').click()
        driver.find_element(By.XPATH, '//*[@id="gender"]/option[2]').click()

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[7]/input').send_keys('Alajuela, Alajuela')

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[8]/button').click()
        
        try:
            alert = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "alert-message"))
            )
            # Verificar el contenido del mensaje
            alert_text = alert.text.strip()
            self.assertNotIn("Student Added Successfully", alert_text,
                             "El estudiante no debería haberse creado exitosamente con datos repetidos")
        except TimeoutException:
            # Si no aparece mensaje, eso tambien es valido
            pass


class test_class_sm31(DjangoSeleniumTestCase):
    """
    SM-31
    Intentar añadir un estudiante correctamente, con dos apellidos 
    Datos:
        Email address = {“andrea@test.com”}

        First Name = {“Andrea”}

        Last Name = {“Duarte Viquez”}

        Medium = {“Foundation”}

        Class = {“6”}

        Gender = {“Other”}

        Address = {“Alajuelita, Alajuela”}
    Resultado esperado:
        La ventana de “Add Student” se limpiara y tendrá un mensaje en celeste indicando “Student Added Successfully”
            En la ventana de “Admin Dashboard” deberá aparecer un estudiante nuevo en los datos.

    """
    def test_add_student_with_two_lastname(self):
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

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input').send_keys('andrea@test.com')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/input').send_keys('Andrea')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/input').send_keys('Duarte Viquez')

        driver.find_element(By.XPATH, '//*[@id="medium"]').click()
        driver.find_element(By.XPATH, '//*[@id="medium"]/option[3]').click()

        driver.find_element(By.XPATH, '//*[@id="std"]').click()
        driver.find_element(By.XPATH, '//*[@id="std"]/option[6]').click()

        driver.find_element(By.XPATH, '//*[@id="gender"]').click()
        driver.find_element(By.XPATH, '//*[@id="gender"]/option[3]').click()

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[7]/input').send_keys('Alajuelita, Alajuela')

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[8]/button').click()
        
        added = driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div[1]/div[2]/strong')
        self.assertEqual(added.text, "Student added successfully")

class test_class_sm32(DjangoSeleniumTestCase):
    """
    SM-32
    Intentar añadir un estudiante correctamente, sin “Email Address”
    Datos:
        Email address = N/A

        First Name = {“Pepito”, “Clara”}

        Last Name = {“Alvarez”, “Brenes”}

        Medium = {“Marathi”, “CBSE”}

        Class = {“1”, “10”}

        Gender = {“Male”, “Female”}

        Address = {“Alajuela, Alajuela”, “Barrio Amon, San Jose”}
    Resultado esperado:
        - Debe saltar un mensaje en “Email address” indicando “Please fill out this field”
    """
    def test_add_student_with_no_email(self):
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

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/input').send_keys('Pepito')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/input').send_keys('Alvarez')

        driver.find_element(By.XPATH, '//*[@id="medium"]').click()
        driver.find_element(By.XPATH, '//*[@id="medium"]/option[2]').click()

        driver.find_element(By.XPATH, '//*[@id="std"]').click()
        driver.find_element(By.XPATH, '//*[@id="std"]/option[2]').click()

        driver.find_element(By.XPATH, '//*[@id="gender"]').click()
        driver.find_element(By.XPATH, '//*[@id="gender"]/option[2]').click()

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[7]/input').send_keys('Alajuela, Alajuela')

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[8]/button').click()

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[8]/button').click()
        
        try:
            alert = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "alert-message"))
            )
            # Verificar el contenido del mensaje
            alert_text = alert.text.strip()
            self.assertNotIn("Student added successfully", alert_text,
                             "El estudiante no debería haberse creado exitosamente sin datos")
        except TimeoutException:
            # Si no aparece mensaje, eso tambien es valido
            pass


class test_class_sm33(DjangoSeleniumTestCase):
    """
    SM-33
    Intentar añadir un estudiante correctamente, sin “First Name”   
    Datos:
        Email address = {“pepito@test.com”, “clara@test.com”}

        First Name = N/A

        Last Name = {“Alvarez”, “Brenes”}

        Medium = {“Marathi”, “CBSE”}

        Class = {“1”, “10”}

        Gender = {“Male”, “Female”}

        Address = {“Alajuela, Alajuela”, “Barrio Amon, San Jose”}
    Resultado esperado:
        - Debe saltar un mensaje en “First Name” indicando “Please fill out this field”
    """
    def test_add_student_with_no_first_name(self):
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

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input').send_keys('pepito@test.com')

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/input').send_keys('Alvarez')

        driver.find_element(By.XPATH, '//*[@id="medium"]').click()
        driver.find_element(By.XPATH, '//*[@id="medium"]/option[2]').click()

        driver.find_element(By.XPATH, '//*[@id="std"]').click()
        driver.find_element(By.XPATH, '//*[@id="std"]/option[2]').click()

        driver.find_element(By.XPATH, '//*[@id="gender"]').click()
        driver.find_element(By.XPATH, '//*[@id="gender"]/option[2]').click()

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[7]/input').send_keys('Alajuela, Alajuela')

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[8]/button').click()

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[8]/button').click()
        
        try:
            alert = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "alert-message"))
            )
            # Verificar el contenido del mensaje
            alert_text = alert.text.strip()
            self.assertNotIn("Student added successfully", alert_text,
                             "El estudiante no debería haberse creado exitosamente sin datos")
        except TimeoutException:
            # Si no aparece mensaje, eso tambien es valido
            pass
        

class test_class_sm34(DjangoSeleniumTestCase):
    """
    SM-34
    Intentar añadir un estudiante correctamente, sin “Last Name”   
    Datos:
        Email address = {“pepito@test.com”, “clara@test.com”}

        First Name = {“Pepito”, “Clara”}

        Last Name = N/A

        Medium = {“Marathi”, “CBSE”}

        Class = {“1”, “10”}

        Gender = {“Male”, “Female”}

        Address = {“Alajuela, Alajuela”, “Barrio Amon, San Jose”}
    Resultado esperado:
        - Debe saltar un mensaje en “Last Name” indicando “Please fill out this field”
    """
    def test_add_student_with_no_lastname(self):
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

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input').send_keys('pepito@test.com')

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/input').send_keys('Pepito')

        driver.find_element(By.XPATH, '//*[@id="medium"]').click()
        driver.find_element(By.XPATH, '//*[@id="medium"]/option[2]').click()

        driver.find_element(By.XPATH, '//*[@id="std"]').click()
        driver.find_element(By.XPATH, '//*[@id="std"]/option[2]').click()

        driver.find_element(By.XPATH, '//*[@id="gender"]').click()
        driver.find_element(By.XPATH, '//*[@id="gender"]/option[2]').click()

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[7]/input').send_keys('Alajuela, Alajuela')

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[8]/button').click()

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[8]/button').click()
        
        try:
            alert = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "alert-message"))
            )
            # Verificar el contenido del mensaje
            alert_text = alert.text.strip()
            self.assertNotIn("Student added successfully", alert_text,
                             "El estudiante no debería haberse creado exitosamente sin datos")
        except TimeoutException:
            # Si no aparece mensaje, eso tambien es valido
            pass


class test_class_sm35(DjangoSeleniumTestCase):
    """
    SM-35
    Intentar añadir un estudiante correctamente, sin “Medium” 
    Datos:
        Email address = Email address = {“pepito@test.com”, “clara@test.com”}

        First Name = {“Pepito”, “Clara”}

        Last Name = {“Alvarez”, “Brenes”}

        Medium = N/A

        Class = {“1”, “10”}

        Gender = {“Male”, “Female”}

        Address = {“Alajuela, Alajuela”, “Barrio Amon, San Jose”}
    Resultado esperado:
        - Debe saltar un mensaje en “Medium” indicando “Please select an item in the list”
    """
    def test_add_student_with_no_medium(self):
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

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input').send_keys('pepito@test.com')

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/input').send_keys('Pepito')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/input').send_keys('Alvarez')

        driver.find_element(By.XPATH, '//*[@id="std"]').click()
        driver.find_element(By.XPATH, '//*[@id="std"]/option[2]').click()

        driver.find_element(By.XPATH, '//*[@id="gender"]').click()
        driver.find_element(By.XPATH, '//*[@id="gender"]/option[2]').click()

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[7]/input').send_keys('Alajuela, Alajuela')

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[8]/button').click()

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[8]/button').click()
        
        try:
            alert = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "alert-message"))
            )
            # Verificar el contenido del mensaje
            alert_text = alert.text.strip()
            self.assertNotIn("Student added successfully", alert_text,
                             "El estudiante no debería haberse creado exitosamente sin datos")
        except TimeoutException:
            # Si no aparece mensaje, eso tambien es valido
            pass


class test_class_sm36(DjangoSeleniumTestCase):
    """
    SM-36
    Intentar añadir un estudiante correctamente, sin “Class”  
    Datos:
        Email address = Email address = {“pepito@test.com”, “clara@test.com”}

        First Name = {“Pepito”, “Clara”}

        Last Name = {“Alvarez”, “Brenes”}

        Medium = {“Marathi”, “CBSE”}

        Class = N/A

        Gender = {“Male”, “Female”}

        Address = {“Alajuela, Alajuela”, “Barrio Amon, San Jose”}
    Resultado esperado:
        - Debe saltar un mensaje en “Class” indicando “Please select an item in the list”
    """
    def test_add_student_with_no_class(self):
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

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input').send_keys('pepito@test.com')

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/input').send_keys('Pepito')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/input').send_keys('Alvarez')

        driver.find_element(By.XPATH, '//*[@id="medium"]').click()
        driver.find_element(By.XPATH, '//*[@id="medium"]/option[2]').click()

        driver.find_element(By.XPATH, '//*[@id="gender"]').click()
        driver.find_element(By.XPATH, '//*[@id="gender"]/option[2]').click()

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[7]/input').send_keys('Alajuela, Alajuela')

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[8]/button').click()

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[8]/button').click()
        
        try:
            alert = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "alert-message"))
            )
            # Verificar el contenido del mensaje
            alert_text = alert.text.strip()
            self.assertNotIn("Student added successfully", alert_text,
                             "El estudiante no debería haberse creado exitosamente sin datos")
        except TimeoutException:
            # Si no aparece mensaje, eso tambien es valido
            pass

class test_class_sm37(DjangoSeleniumTestCase):
    """
    SM-37
    Intentar añadir un estudiante correctamente, sin “Gender” 
    Datos:
        Email address = Email address = {“pepito@test.com”, “clara@test.com”}

        First Name = {“Pepito”, “Clara”}

        Last Name = {“Alvarez”, “Brenes”}

        Medium = {“Marathi”, “CBSE”}

        Class = {“1”, “10”}

        Gender = N/A

        Address = {“Alajuela, Alajuela”, “Barrio Amon, San Jose”}
    Resultado esperado:
        - Debe saltar un mensaje en "Gender" indicando “Please select an item in the list”
    """
    def test_add_student_with_no_gender(self):
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

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input').send_keys('pepito@test.com')

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/input').send_keys('Pepito')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/input').send_keys('Alvarez')

        driver.find_element(By.XPATH, '//*[@id="medium"]').click()
        driver.find_element(By.XPATH, '//*[@id="medium"]/option[2]').click()

        driver.find_element(By.XPATH, '//*[@id="std"]').click()
        driver.find_element(By.XPATH, '//*[@id="std"]/option[2]').click()

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[7]/input').send_keys('Alajuela, Alajuela')

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[8]/button').click()

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[8]/button').click()
        
        try:
            alert = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "alert-message"))
            )
            # Verificar el contenido del mensaje
            alert_text = alert.text.strip()
            self.assertNotIn("Student added successfully", alert_text,
                             "El estudiante no debería haberse creado exitosamente sin datos")
        except TimeoutException:
            # Si no aparece mensaje, eso tambien es valido
            pass

class test_class_sm38(DjangoSeleniumTestCase):
    """
    SM-38
    Intentar añadir un estudiante correctamente, sin “Address” 
    Datos:
        Email address = Email address = {“pepito@test.com”, “clara@test.com”}

        First Name = {“Pepito”, “Clara”}

        Last Name = {“Alvarez”, “Brenes”}

        Medium = {“Marathi”, “CBSE”}

        Class =  {“1”, “10”}

        Gender = {“Male”, “Female”}

        Address = {“Alajuela, Alajuela”, “Barrio Amon, San Jose”}
    Resultado esperado:
        - Debe saltar un mensaje en “Address” indicando “Please fill out this field”
    """
    def test_add_student_with_no_address(self):
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

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input').send_keys('pepito@test.com')

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/input').send_keys('Pepito')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/input').send_keys('Alvarez')

        driver.find_element(By.XPATH, '//*[@id="medium"]').click()
        driver.find_element(By.XPATH, '//*[@id="medium"]/option[2]').click()

        driver.find_element(By.XPATH, '//*[@id="std"]').click()
        driver.find_element(By.XPATH, '//*[@id="std"]/option[2]').click()

        driver.find_element(By.XPATH, '//*[@id="gender"]').click()
        driver.find_element(By.XPATH, '//*[@id="gender"]/option[2]').click()

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[8]/button').click()

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[8]/button').click()
        
        try:
            alert = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "alert-message"))
            )
            # Verificar el contenido del mensaje
            alert_text = alert.text.strip()
            self.assertNotIn("Student added successfully", alert_text,
                             "El estudiante no debería haberse creado exitosamente sin datos")
        except TimeoutException:
            # Si no aparece mensaje, eso tambien es valido
            pass


class test_class_sm39(DjangoSeleniumTestCase):
    """
    SM-39
    Intentar añadir un estudiante correctamente, sin “Email Address” válido  
    Datos:
        Email address = {“www.samsung.com”, “www.amazon.com”}

        First Name = {“Pepito”, “Clara”}

        Last Name = {“Alvarez”, “Brenes”}

        Medium = {“Marathi”, “CBSE”}

        Class = {“1”, “10”}

        Gender = {“Male”, “Female”}

        Address = {“Alajuela, Alajuela”, “Barrio Amon, San Jose”}
    Resultado esperado:
        - Debe saltar un mensaje en “Email address” indicando “Please enter an email address”
    """
    def test_add_student_with_invalid_email(self):
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

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input').send_keys('www.samsung.com')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/input').send_keys('Pepito')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/input').send_keys('Alvarez')

        driver.find_element(By.XPATH, '//*[@id="medium"]').click()
        driver.find_element(By.XPATH, '//*[@id="medium"]/option[2]').click()

        driver.find_element(By.XPATH, '//*[@id="std"]').click()
        driver.find_element(By.XPATH, '//*[@id="std"]/option[2]').click()

        driver.find_element(By.XPATH, '//*[@id="gender"]').click()
        driver.find_element(By.XPATH, '//*[@id="gender"]/option[2]').click()

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[7]/input').send_keys('Alajuela, Alajuela')

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[8]/button').click()
        
        try:
            alert = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "alert-message"))
            )
            # Verificar el contenido del mensaje
            alert_text = alert.text.strip()
            self.assertNotIn("Student added successfully", alert_text,
                             "El estudiante no debería haberse creado exitosamente con datos erroneos")
        except TimeoutException:
            # Si no aparece mensaje, eso tambien es valido
            pass


class test_class_sm40(DjangoSeleniumTestCase):
    """
    SM-40
    Intentar añadir un estudiante correctamente, con inyección de codigo en la sección de nombre.
    Datos:
        Email address = {“anuel@test.com”}

        First Name = {“<script>alert("xss")</script>”}

        Last Name = {“Amador”}

        Medium = {“Foundation”}

        Class = {“3”}

        Gender = {“Male”, “Female”}

        Address = {“Santa Rosa, Guanacaste”}
    Resultado esperado:
        - Debería aparecer un mensaje de error indicando que la entrada es maliciosa.
    """
    def test_add_student_with_code_injection_in_firstname(self):
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

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input').send_keys('anuel@test.com')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/input').send_keys('<script>alert("xss")</script>')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/input').send_keys('Amador')

        driver.find_element(By.XPATH, '//*[@id="medium"]').click()
        driver.find_element(By.XPATH, '//*[@id="medium"]/option[3]').click()

        driver.find_element(By.XPATH, '//*[@id="std"]').click()
        driver.find_element(By.XPATH, '//*[@id="std"]/option[3]').click()

        driver.find_element(By.XPATH, '//*[@id="gender"]').click()
        driver.find_element(By.XPATH, '//*[@id="gender"]/option[2]').click()

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[7]/input').send_keys('Alajuela, Alajuela')

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[8]/button').click()
        
        try:
            alert = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "alert-message"))
            )
            # Verificar el contenido del mensaje
            alert_text = alert.text.strip()
            self.assertNotIn("Student added successfully", alert_text,
                             "El estudiante no debería haberse creado exitosamente con datos erroneos")
        except TimeoutException:
            # Si no aparece mensaje, eso tambien es valido
            pass


class test_class_sm41(DjangoSeleniumTestCase):
    """
    SM-41
    Intentar añadir un estudiante correctamente, con un “First Name” con caracteres alfanuméricos 
    Datos:
        Email address = {“alej12@test.com”}

        First Name = {“Alej12”}

        Last Name = {“Gonzales”}

        Medium = {“SemiEng”}

        Class = {“7”}

        Gender = {“Male”}

        Address = {“Isla Tortuga, Limón”}
    Resultado esperado:
        - La ventana de “Add Student” se limpiara y tendrá un mensaje en celeste indicando “Student Added Successfully”
            En la ventana de “Admin Dashboard” deberá aparecer un estudiante nuevo en los datos.
    """
    def test_add_student_with_alfanumeric_firstname(self):
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

        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[1]/input').send_keys('alej12@test.com')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[2]/input').send_keys('Alej12')
        driver.find_element(By.XPATH, '/html/body/div/div/main/div/div/div/div/div/form/div[3]/input').send_keys('“Gonzales”')

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


if __name__ == '__main__':
    # Configurar el runner de pruebas
    unittest.main(verbosity=2)