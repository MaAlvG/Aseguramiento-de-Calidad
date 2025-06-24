import unittest
import time
import subprocess
import requests
import signal
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from .helpers.reset_datos_prueba_sarah import *

class DjangoSeleniumTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print(f"\n=== Configurando {cls.__name__} ===")
        cls.chrome_options = Options()
        # cls.chrome_options.add_argument('--headless')
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

        cls.live_server_url = 'http://127.0.0.1:8000'
        cls.server_process = None
        cls.server_started_by_us = False

        try:
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
        print(f"\n=== Limpiando {cls.__name__} ===")
        if hasattr(cls, 'server_started_by_us') and cls.server_started_by_us:
            if hasattr(cls, 'server_process') and cls.server_process:
                cls.stop_django_server()

    def setUp(self):
        print(f"  -> Iniciando: {self._testMethodName}")
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=self.chrome_options)
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)
        except WebDriverException as e:
            self.skipTest(f"No se pudo inicializar Chrome WebDriver: {e}")
        except Exception as e:
            self.skipTest(f"Error inesperado al configurar WebDriver: {e}")

    def tearDown(self):
        print(f"  <- Finalizando: {self._testMethodName}")
        if hasattr(self, 'driver'):
            try:
                self.driver.quit()
            except Exception as e:
                print(f"    Error al cerrar el driver: {e}")

    @classmethod
    def is_server_running(cls):
        try:
            response = requests.get(cls.live_server_url, timeout=5)
            return response.status_code < 500
        except:
            return False

    @classmethod
    def start_django_server(cls):
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
        if hasattr(cls, 'server_process') and cls.server_process:
            try:
                print("    Deteniendo servidor Django...")
                if hasattr(os, 'killpg'):
                    os.killpg(os.getpgid(cls.server_process.pid), signal.SIGTERM)
                else:
                    cls.server_process.terminate()
                cls.server_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                print("    Forzando cierre del servidor...")
                if hasattr(os, 'killpg'):
                    os.killpg(os.getpgid(cls.server_process.pid), signal.SIGKILL)
                else:
                    cls.server_process.kill()
                cls.server_process.wait()
            except Exception as e:
                print(f"    Error al detener el servidor: {e}")

    @classmethod
    def wait_for_server(cls, timeout=30):
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
            time.sleep(2)
        raise Exception(f"El servidor Django no estuvo disponible después de {timeout} segundos")

# SM-01
class access_teacher_table(DjangoSeleniumTestCase):
    """
    SM-01

    Verifica que al ingresar a "Manage -> Teacher" se despliega correctamente la tabla con los profesores.

    Datos:
        - Usuario: admin@pruebas.com / pruebas

    Resultado esperado:
        - Se muestra la tabla con columnas: ID, First Name, Last Name, Teacher Code, Email, Gender, Address, Created At, Updated At.
    """
    def test_access_teacher_table(self):
        driver = self.driver
        driver.get(self.live_server_url)

        # login como administrador
        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        # esperamos carga del dashboard
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3'))
        )

        # vamos a la vista de gestionar profesores
        driver.get(self.live_server_url + "/manageteacher/")

        # esperar los encabezados de la tabla
        headers = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, '//table//thead//tr//th'))
        )

        expected = [
            "ID", "First Name", "Last Name", "Teacher Code",
            "Email", "Gender", "Address", "Created At", "Updated At"
        ]
        actual = [h.text.strip() for h in headers]

        for col in expected:
            self.assertIn(col, actual, f"Falta la columna '{col}' en la tabla.")

# SM-02
class filter_teacher_by_name(DjangoSeleniumTestCase): # tiene que fallar, error encontrado
    """
    SM-02

    Verifica que el campo de búsqueda filtre bien a los profesores por nombre.

    Datos:
        - Usuario: admin@pruebas.com / pruebas
        - Valor de búsqueda: "Roberto"

    Resultado esperado:
        - Se muestra en la tabla solo el profesor cuyo nombre contiene "Roberto"
    """
    def test_filter_teacher_by_name(self):
        driver = self.driver
        driver.get(self.live_server_url)

        # login
        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        # esperar dashboard
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3'))
        )

        reset_roberto(driver, self.live_server_url)  # funcion auxiliar para resetear el profesor Roberto a su estado original

        # vamos a la vista de profesores
        driver.get(self.live_server_url + "/manageteacher/")

        # esperar el campo de busqueda 
        search_box = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '//input[@placeholder="Search…"]'))
        )
        search_box.clear()
        search_box.send_keys("Roberto")
        search_box.send_keys(Keys.ENTER)

        # esperar que la tabla se actualice (si es que se actualiza)
        time.sleep(1.5)

        # buscar filas visibles en la tabla
        rows = driver.find_elements(By.XPATH, '//table//tbody/tr')
        visible_rows = [row for row in rows if row.is_displayed()]

        # validacion basica
        self.assertGreater(len(visible_rows), 0, "No se encontraron resultados tras la búsqueda.")

        for row in visible_rows:
            row_text = row.text.lower()
            self.assertIn("roberto", row_text, "La fila visible no contiene 'Roberto'")

# SM-03
class edit_teacher_address(DjangoSeleniumTestCase):
    """
    SM-03

    Verifica que al editar un profesor y cambiar su dirección, el cambio se guarda correctamente.

    Datos:
        - Usuario: admin@pruebas.com / pruebas
        - Profesor existente: Roberto Gomez
        - Nueva dirección: San José, Curridabat

    Resultado esperado:
        - El nuevo valor aparece en la tabla después de guardar los cambios.
    """
    def test_edit_teacher_address(self):
        driver = self.driver
        driver.get(self.live_server_url)

        # login
        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3'))
        )

        reset_roberto(driver, self.live_server_url)  # funcion auxiliar para resetear el profesor Roberto a su estado original

        # ir a lista de profesores
        driver.get(self.live_server_url + "/manageteacher/")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//table'))
        )

        # buscar fila con "Roberto"
        target_row = None
        rows = driver.find_elements(By.XPATH, '//table//tbody/tr')
        for row in rows:
            if row.is_displayed() and "roberto" in row.text.lower():
                target_row = row
                break

        self.assertIsNotNone(target_row, "No se encontró un profesor con nombre 'Roberto'.")

        # clic en boton de editar
        edit_btn = target_row.find_element(By.XPATH, './/td[last()-1]/a')
        edit_btn.click()

        # esperar que se cargue el formulario
        address_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '//input[@name="address"]'))
        )

        # cambiar direccion
        address_input.clear()
        address_input.send_keys("San José, Curridabat")

        # clic en boton de "Update"
        submit_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@type="submit" and contains(text(), "Update")]'))
        )
        driver.execute_script("arguments[0].click();", submit_btn)

        # revisar cambio en la tabla
        driver.get(self.live_server_url + "/manageteacher/")
        time.sleep(1.5)

        updated = False
        rows = driver.find_elements(By.XPATH, '//table//tbody/tr')
        for row in rows:
            if row.is_displayed() and "roberto" in row.text.lower() and "curridabat" in row.text.lower():
                updated = True
                break

        self.assertTrue(updated, "La dirección no se actualizó correctamente en la tabla.")

# SM-04
class edit_teacher_empty_email(DjangoSeleniumTestCase): # tambien falla, error encontrado
    """
    SM-04

    Validar que el sistema impide actualizar los datos de un profesor si el campo de email se deja vacío.

    Datos:
        - Usuario: admin@pruebas.com / pruebas
        - Profesor objetivo: Roberto Gomez
        - Acción: borrar el email y tratar de guardar

    Resultado esperado:
        - No se permite enviar el formulario
        - No aparece mensaje de éxito
    """
    def test_edit_teacher_empty_email(self):
        driver = self.driver
        driver.get(self.live_server_url)

        # iniciar sesion como administrador
        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3'))
        )

        reset_roberto(driver, self.live_server_url)  # funcion auxiliar para resetear el profesor Roberto a su estado original

        # ir al listado de profesores
        driver.get(self.live_server_url + "/manageteacher/")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//table')))

        # buscar fila de "Gomez"
        target_row = None
        for row in driver.find_elements(By.XPATH, '//table//tbody/tr'):
            if row.is_displayed() and "roberto" in row.text.lower():
                target_row = row
                break

        self.assertIsNotNone(target_row, "No se encontró un profesor con nombre 'Roberto'.")
        edit_btn = target_row.find_element(By.XPATH, './/td[last()-1]/a')
        edit_btn.click()

        # borrar campo de email
        email_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '//input[@name="email"]'))
        )
        email_input.clear()

        # clic en "Update"
        submit_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@type="submit" and contains(text(), "Update")]'))
        )
        driver.execute_script("arguments[0].click();", submit_btn)

        time.sleep(1)  # esperar que se procese el submit

        # revisar que NO se muestre mensaje de éxito
        try:
            success_msg = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[contains(text(), "Teacher Updated successfully")]')
                )
            )
            self.fail("Se mostró mensaje de éxito a pesar de dejar el email vacío.")
        except TimeoutException:
            pass

# SM-05
class delete_teacher_by_name(DjangoSeleniumTestCase):
    """
    SM-05

    Validar que el botón eliminar remueve un profesor correctamente

    Datos:
        - Usuario: admin@pruebas.com / pruebas
        - Profesor objetivo: Nombre contiene "Borrador"

    Resultado esperado:
        - El profesor desaparece de la tabla y no vuelve a aparecer al refrescar
    """
    def test_delete_teacher_by_name(self):
        driver = self.driver
        driver.get(self.live_server_url)

        # iniciar sesion como administrador
        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3'))
        )

        reset_borrador_teacher(driver, self.live_server_url)  # funcion auxiliar para resetear el profesor Borrador a su estado original

        # ir al listado de profesores
        driver.get(self.live_server_url + "/manageteacher/")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//table')))

        # buscar fila que contenga "Borrador"
        target_row = None
        for row in driver.find_elements(By.XPATH, '//table/tbody/tr'):
            if row.is_displayed() and "borrador" in row.text.lower():
                target_row = row
                break

        self.assertIsNotNone(target_row, "No se encontró ningún profesor con nombre 'Borrador'.")

        # clic en el boton de eliminar
        delete_btn = target_row.find_element(By.XPATH, './/td[last()]/a')
        delete_btn.click()

        # esperar y volver a cargar tabla
        time.sleep(1)
        driver.get(self.live_server_url + "/manageteacher/")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//table')))

        # revisar que el nombre ya no aparece en la tabla
        rows = driver.find_elements(By.XPATH, '//table/tbody/tr')
        found = False
        for row in rows:
            if row.is_displayed() and "borrador" in row.text.lower():
                found = True
                break

        self.assertFalse(found, "El profesor con nombre 'Borrador' aún aparece en la tabla después de eliminarlo.")


# SM-07
class edit_teacher_invalid_email(DjangoSeleniumTestCase):
    """
    SM-07

    Validar que el sistema rechace correos con formato inválido al editar profesor.

    Datos de prueba:
        - "robertogmailcom"
        - "1234"
        - "$"

    Resultado esperado:
        - El sistema no permite guardar y no se muestra mensaje de éxito.
    """
    def test_edit_teacher_invalid_email(self):
        driver = self.driver
        driver.get(self.live_server_url)

        # login como administrador
        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        # esperar carga de dashboard
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3'))
        )

        reset_roberto(driver, self.live_server_url)  # funcion auxiliar para resetear el profesor Roberto a su estado original

        # ir directamente a la vista de profesores
        driver.get(self.live_server_url + "/manageteacher/")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//table')))

        # buscar al profesor "Roberto"
        target_row = None
        for row in driver.find_elements(By.XPATH, '//table/tbody/tr'):
            if "roberto" in row.text.lower():
                target_row = row
                break

        self.assertIsNotNone(target_row, "No se encontró un profesor con nombre 'Roberto'.")

        # ir al boton de editar
        edit_btn = target_row.find_element(By.XPATH, './/td[last()-1]/a')
        edit_btn.click()

        # esperar formulario de edicion
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//input[@name="email"]'))
        )

        # probar cada email invalido
        invalid_emails = ["robertogmailcom", "1234", "$"]
        for invalid in invalid_emails:
            # reabrir formulario para cada intento
            driver.get(self.live_server_url + "/manageteacher/")
            for row in driver.find_elements(By.XPATH, '//table/tbody/tr'):
                if "roberto" in row.text.lower():
                    row.find_element(By.XPATH, './/td[last()-1]/a').click()
                    break

            email_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//input[@name="email"]'))
            )

            email_input.clear()
            email_input.send_keys(invalid)

            # clic en Update
            update_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//button[text()="Update"]'))
            )
            driver.execute_script("arguments[0].click();", update_btn)

            time.sleep(1)

            # revisar que NO se muestra el mensaje de exito
            try:
                success_msg = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, '//div[contains(text(), "successfully")]'))
                )
                self.fail(f"El sistema permitió guardar con email inválido: '{invalid}'")
            except TimeoutException:
                print(f"Email inválido correctamente rechazado: {invalid}")

# SM-08
class edit_teacher_empty_firstname(DjangoSeleniumTestCase): # tambien falla, error encontrado
    """
    SM-08

    Validar que el sistema impide actualizar los datos de un profesor si el campo de nombre (First Name) se deja vacío.

    Datos de prueba:
        - Usuario: admin@pruebas.com / pruebas
        - Profesor objetivo: Roberto Gomez
        - Acción: borrar el first name y tratar de guardar

    Resultado esperado:
        - No se permite enviar el formulario
        - No aparece mensaje de éxito
    """
    def test_edit_teacher_empty_firstname(self):
        driver = self.driver
        driver.get(self.live_server_url)

        # login como administrador
        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3'))
        )

        reset_roberto(driver, self.live_server_url)  # funcion auxiliar para resetear el profesor Roberto a su estado original

        # ir al listado de profesores
        driver.get(self.live_server_url + "/manageteacher/")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//table')))

        # buscar fila del profesor Roberto
        target_row = None
        for row in driver.find_elements(By.XPATH, '//table/tbody/tr'):
            if row.is_displayed() and "roberto" in row.text.lower():
                target_row = row
                break

        self.assertIsNotNone(target_row, "No se encontró un profesor con nombre 'Roberto'.")
        edit_btn = target_row.find_element(By.XPATH, './/td[last()-1]/a')
        edit_btn.click()

        # esperar campo first name
        first_name_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '//input[@name="firstname"]'))
        )
        first_name_input.clear()

        # clic en "Update"
        submit_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@type="submit" and contains(text(), "Update")]'))
        )
        driver.execute_script("arguments[0].click();", submit_btn)

        time.sleep(1)

        # revisar que NO se muestra mensaje de exito
        try:
            success_msg = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[contains(text(), "Teacher Updated successfully")]')
                )
            )
            self.fail("Se mostró mensaje de éxito a pesar de dejar el nombre vacío.")
        except TimeoutException:
            pass

# SM-11
class edit_student_partial_update(DjangoSeleniumTestCase):
    """
    SM-11

    Validar que al editar un estudiante solo se modifique el campo actualizado.

    Datos de prueba:
        - Usuario: admin@pruebas.com / pruebas
        - Estudiante objetivo: Kristel
        - Campo a modificar: clase (de "8" a "2")

    Resultado esperado:
        - Solo el campo clase se actualiza.
        - Los demás campos se mantienen intactos.
    """
    def test_edit_student_partial_update(self):
        driver = self.driver
        driver.get(self.live_server_url)

        # login como administrador
        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3'))
        )

        reset_kristel(driver, self.live_server_url)  # funcion auxiliar para resetear el estudiante Kristel a su estado original

        # ir al listado de estudiantes
        driver.get(self.live_server_url + "/managestudent/")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//table'))
        )

        # buscar al estudiante "Kristel"
        target_row = None
        for row in driver.find_elements(By.XPATH, '//table/tbody/tr'):
            if row.is_displayed() and "kristel" in row.text.lower():
                target_row = row
                break

        self.assertIsNotNone(target_row, "No se encontró un estudiante con nombre 'Kristel'.")
        original_row_text = target_row.text

        # ir a editar 
        edit_btn = target_row.find_element(By.XPATH, './/td[last()-1]/a')
        edit_btn.click()

        # esperar el campo de clase
        class_select = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "std"))
        )

        # cambiar la clase a 2
        select = Select(class_select)
        WebDriverWait(driver, 10).until(
            lambda d: any(o.text.strip() == "2" for o in Select(class_select).options)
        )
        select.select_by_visible_text("2")

        submit_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//button[@type="submit" and contains(text(), "Submit")]')))
        driver.execute_script("arguments[0].click();", submit_btn)

        # reconsultar la tabla despues de guardar
        driver.get(self.live_server_url + "/managestudent/")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//table')))

        # buscar nuevamente la fila de Kristel
        updated_row = None
        for row in driver.find_elements(By.XPATH, '//table/tbody/tr'):
            if "kristel" in row.text.lower():
                updated_row = row
                break

        self.assertIsNotNone(updated_row, "No se encontró el estudiante 'Kristel' luego de la edición.")
        updated_text = updated_row.text.lower()

        # revisar que clase sea 2 y los otros campos se conserven
        self.assertIn("2", updated_text, "La clase no se actualizó correctamente a 2.")
        preserved_fields = ["kristel", "campos", "@gmail.com", "female", "foundation", "grecia"]
        for field in preserved_fields:
            self.assertIn(field, updated_text, f"El campo '{field}' no se conservó tras la edición.")

# SM-12
class delete_student_by_name(DjangoSeleniumTestCase):
    """
    SM-12

    Verificar que tras eliminar un estudiante, este no vuelva a aparecer al recargar.

    Datos:
        - Usuario: admin@pruebas.com / pruebas
        - Estudiante objetivo: Nombre contiene "Borrador"

    Resultado esperado:
        - El estudiante desaparece de la tabla después de eliminarlo
        - No vuelve a aparecer al refrescar la página
    """
    def test_delete_student_by_name(self):
        driver = self.driver
        driver.get(self.live_server_url)

        # login como administrador
        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3')
            )
        )

        reset_borrador_student(driver, self.live_server_url)  # funcion auxiliar para resetear el estudiante Borrador a su estado original

        # ir al listado de estudiantes
        driver.get(self.live_server_url + "/managestudent/")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//table'))
        )

        # buscar fila con nombre "Borrador"
        target_row = None
        for row in driver.find_elements(By.XPATH, '//table/tbody/tr'):
            if row.is_displayed() and "borrador" in row.text.lower():
                target_row = row
                break

        self.assertIsNotNone(target_row, "No se encontró ningún estudiante con nombre 'Borrador'.")

        # clic en el botón de eliminar
        delete_btn = target_row.find_element(By.XPATH, './/td[last()]/a')
        delete_btn.click()

        # esperar y volver a cargar la tabla
        time.sleep(1)
        driver.get(self.live_server_url + "/managestudent/")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//table'))
        )

        # revisar que el nombre ya no aparece
        still_exists = False
        for row in driver.find_elements(By.XPATH, '//table/tbody/tr'):
            if row.is_displayed() and "borrador" in row.text.lower():
                still_exists = True
                break

        self.assertFalse(still_exists, "El estudiante con nombre 'Borrador' aún aparece en la tabla después de eliminarlo.")

# SM-13
class cancel_edit_teacher_discard_changes(DjangoSeleniumTestCase):
    """
    SM-13

    Validar que al cancelar la edición de un profesor no se guarden los cambios.

    Datos de prueba:
        - Usuario: admin@pruebas.com / pruebas
        - Profesor objetivo: Roberto
        - Campo editado: first name → Bernardo (sin guardar)

    Resultado esperado:
        - El nombre anterior se conserva después de salir de la vista sin guardar.
    """
    def test_cancel_edit_teacher_discard_changes(self):
        driver = self.driver
        driver.get(self.live_server_url)

        # Iniciar sesión como admin
        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3')
            )
        )

        reset_roberto(driver, self.live_server_url)  # funcion auxiliar para resetear el profesor Roberto a su estado original

        # ir a vista de profesores
        driver.get(self.live_server_url + "/manageteacher/")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//table')))

        # buscar profesor "Roberto"
        target_row = None
        for row in driver.find_elements(By.XPATH, '//table/tbody/tr'):
            if row.is_displayed() and "roberto" in row.text.lower():
                target_row = row
                break

        self.assertIsNotNone(target_row, "No se encontró al profesor 'Roberto'.")
        original_text = target_row.text.lower()

        # entrar al formulario de edicion
        edit_btn = target_row.find_element(By.XPATH, './/td[last()-1]/a')
        edit_btn.click()

        # esperar campo de nombre
        name_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.NAME, "firstname"))
        )

        # cambiar el nombre por "Bernardo"
        name_input.clear()
        name_input.send_keys("Bernardo")

        # simular "cancelar" usando el boton de atras del navegador
        driver.back()

        # volver a la pagina de profesores
        driver.get(self.live_server_url + "/manageteacher/")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//table')))

        # revisar que el nombre aun sea "Roberto"
        name_still_rob = False
        for row in driver.find_elements(By.XPATH, '//table/tbody/tr'):
            if row.is_displayed() and "roberto" in row.text.lower():
                name_still_rob = True
                break

        self.assertTrue(name_still_rob, "El cambio de nombre fue guardado a pesar de cancelar la edición.")

# SM-16
class edit_teacher_updated_at_change(DjangoSeleniumTestCase):
    """
    SM-16

    Validar que se actualice el campo “Updated At” tras una edición en profesores.

    Datos de prueba:
        - Usuario: admin@pruebas.com / pruebas
        - Profesor objetivo: Roberto Gomez
        - Campo editado: Last Name → Arias

    Resultado esperado:
        - El valor de la columna “Updated At” cambia tras guardar la edición.
    """
    def test_edit_teacher_updated_at_change(self):
        import re

        driver = self.driver
        driver.get(self.live_server_url)

        # login como admin
        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3'))
        )

        reset_roberto(driver, self.live_server_url)  # funcion auxiliar para resetear el profesor Roberto a su estado original

        # ir a vista de profesores
        driver.get(self.live_server_url + "/manageteacher/")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//table')))

        # buscar profesor "Roberto"
        target_row = None
        for row in driver.find_elements(By.XPATH, '//table/tbody/tr'):
            if row.is_displayed() and "roberto" in row.text.lower():
                target_row = row
                break

        self.assertIsNotNone(target_row, "No se encontró al profesor 'Roberto'.")

        # extraer Updated At usando regex
        row_text = target_row.text
        timestamp_pattern = r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}, \d{1,2}:\d{2} (?:a|p)\.m\."
        matches = re.findall(timestamp_pattern, row_text)

        print("Texto original de la fila:", row_text)
        print("Timestamps encontrados:", matches)

        self.assertGreaterEqual(len(matches), 2, "No se encontraron suficientes timestamps para validar 'Updated At'.")
        original_updated_at = matches[1]

        print("Esperando 60 segundos para asegurar cambio de timestamp... (porque quise automatizar los datos de prueba jiji)")
        time.sleep(60)

        # ir a editar
        edit_btn = target_row.find_element(By.XPATH, './/td[last()-1]/a')
        edit_btn.click()

        # editar last name
        last_name_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.NAME, "lastname"))
        )
        last_name_input.clear()
        last_name_input.send_keys("Arias")

        # clic en Update
        update_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@type="submit" and contains(text(), "Update")]'))
        )
        driver.execute_script("arguments[0].click();", update_btn)

        # volver a lista de profesores
        driver.get(self.live_server_url + "/manageteacher/")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//table')))

        # volver a buscar a Roberto
        updated_row = None
        for row in driver.find_elements(By.XPATH, '//table/tbody/tr'):
            if row.is_displayed() and "roberto" in row.text.lower():
                updated_row = row
                break

        self.assertIsNotNone(updated_row, "No se encontró al profesor 'Roberto' tras la edición.")

        updated_text = updated_row.text
        updated_matches = re.findall(timestamp_pattern, updated_text)

        print("Texto actualizado de la fila:", updated_text)
        print("Timestamps después de editar:", updated_matches)

        self.assertGreaterEqual(len(updated_matches), 2, "No se encontraron timestamps tras la edición.")
        new_updated_at = updated_matches[1]

        self.assertNotEqual(
            original_updated_at,
            new_updated_at,
            f"El campo 'Updated At' no se actualizó. Antes: {original_updated_at}, Ahora: {new_updated_at}")
        
# SM-17
class edit_student_medium_update(DjangoSeleniumTestCase):
    """
    SM-17

    Validar que al cambiar la opción “Medium” se actualice correctamente en la lista.

    Datos de prueba:
        - Usuario: admin@pruebas.com / pruebas
        - Estudiante objetivo: Kristel
        - Campo a modificar: Medium -> SemiEng

    Resultado esperado:
        - El campo “Medium” se actualiza correctamente.
        - El valor actualizado aparece reflejado en la tabla.
    """
    def test_edit_student_medium_update(self):
        driver = self.driver
        driver.get(self.live_server_url)

        # login como administrador
        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3'))
        )

        reset_kristel(driver, self.live_server_url)  # funcion auxiliar para resetear el estudiante Kristel a su estado original

        # ir al listado de estudiantes
        driver.get(self.live_server_url + "/managestudent/")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//table')))

        # buscar estudiante Kristel
        target_row = None
        for row in driver.find_elements(By.XPATH, '//table/tbody/tr'):
            if row.is_displayed() and "kristel" in row.text.lower():
                target_row = row
                break

        self.assertIsNotNone(target_row, "No se encontró al estudiante 'Kristel'.")

        # editar estudiante
        edit_btn = target_row.find_element(By.XPATH, './/td[last()-1]/a')
        edit_btn.click()

        # esperar campo Medium
        medium_select = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "medium"))
        )
        from selenium.webdriver.support.ui import Select
        Select(medium_select).select_by_visible_text("SemiEng")

        # enviar cambios
        submit_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@type="submit" and contains(text(), "Submit")]'))
        )
        driver.execute_script("arguments[0].click();", submit_btn)

        # recargar y revisar el cambio en la tabla
        driver.get(self.live_server_url + "/managestudent/")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//table')))

        updated = False
        for row in driver.find_elements(By.XPATH, '//table/tbody/tr'):
            if row.is_displayed() and "kristel" in row.text.lower() and "semieng" in row.text.lower():
                updated = True
                break

        self.assertTrue(updated, "El campo 'Medium' no se actualizó correctamente a 'SemiEng'.")

# SM-20
class edit_student_empty_firstname(DjangoSeleniumTestCase):
    """
    SM-20

    Validar que el sistema impide actualizar los datos de un estudiante si el campo de nombre (First Name) se deja vacío.

    Datos de prueba:
        - Usuario: admin@pruebas.com / pruebas
        - Estudiante objetivo: Kristel
        - Acción: borrar el first name y tratar de guardar

    Resultado esperado:
        - No se permite enviar el formulario
        - No aparece mensaje de éxito
    """
    def test_edit_student_empty_firstname(self): # tambien falla, error encontrado
        driver = self.driver
        driver.get(self.live_server_url)

        # login como admin
        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3'))
        )

        reset_kristel(driver, self.live_server_url)  # funcion auxiliar para resetear el estudiante Kristel a su estado original

        # ir al listado de estudiantes
        driver.get(self.live_server_url + "/managestudent/")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//table')))

        # buscar a Kristel
        target_row = None
        for row in driver.find_elements(By.XPATH, '//table/tbody/tr'):
            if row.is_displayed() and "kristel" in row.text.lower():
                target_row = row
                break

        self.assertIsNotNone(target_row, "No se encontró un estudiante con nombre 'Kristel'.")
        edit_btn = target_row.find_element(By.XPATH, './/td[last()-1]/a')
        edit_btn.click()

        # borrar campo de First Name
        first_name_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.NAME, 'firstname'))
        )
        first_name_input.clear()

        # clic en Submit
        submit_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@type="submit" and contains(text(), "Submit")]'))
        )
        driver.execute_script("arguments[0].click();", submit_btn)

        time.sleep(1)

        # revisar que NO se muestre mensaje de exito
        try:
            success_msg = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[contains(text(), "Student upadated successfully")]') # tiene un typo en la notif para estudiante, asi es
                )
            )
            self.fail("Se mostró mensaje de éxito a pesar de dejar el nombre vacío.")
        except TimeoutException:
            pass

# SM-21
class edit_student_empty_email(DjangoSeleniumTestCase): # tambien falla, error encontrado
    """
    SM-21

    Validar que el sistema impide actualizar los datos de un estudiante si el campo de email se deja vacío.

    Datos de prueba:
        - Usuario: admin@pruebas.com / pruebas
        - Estudiante objetivo: Kristel
        - Acción: borrar el email y tratar de guardar

    Resultado esperado:
        - No se permite enviar el formulario
        - No aparece mensaje de éxito
    """

    def test_edit_student_empty_email(self):
        driver = self.driver
        driver.get(self.live_server_url)

        # login como administrador
        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3'))
        )

        reset_kristel(driver, self.live_server_url) # funcion auxiliar para resetear la estudiante Kristel a su estado original

        # ir al listado de estudiantes
        driver.get(self.live_server_url + "/managestudent/")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//table')))

        # buscar fila del estudiante Kristel
        target_row = None
        for row in driver.find_elements(By.XPATH, '//table/tbody/tr'):
            if row.is_displayed() and "kristel" in row.text.lower():
                target_row = row
                break

        self.assertIsNotNone(target_row, "No se encontró un estudiante con nombre 'Kristel'.")
        edit_btn = target_row.find_element(By.XPATH, './/td[last()-1]/a')
        edit_btn.click()

        # borrar campo de email
        email_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '//input[@name="email"]'))
        )
        email_input.clear()

        # clic en "Submit"
        submit_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@type="submit" and contains(text(), "Submit")]'))
        )
        driver.execute_script("arguments[0].click();", submit_btn)

        time.sleep(1)  # dar tiempo a que se procese el intento de guardar

        # revisar que NO se muestre mensaje de exito
        try:
            success_msg = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[contains(text(), "Student upadated successfully")]')  # tiene un typo en la notif para estudiante, asi es)
                )
            )
            self.fail("Se mostró mensaje de éxito a pesar de dejar el email vacío.")
        except TimeoutException:
            print("El sistema rechazó correctamente el email vacío.")

# SM-22
class edit_teacher_address_special_characters(DjangoSeleniumTestCase):
    """
    SM-22

    Validar que al escribir caracteres especiales en el campo “Address” de profesores no se presenten errores ni comportamientos inesperados.

    Datos de prueba:
        - "Calle 5"
        - "#123-Apt°"
        - "‘Barrio Sur"

    Resultado esperado:
        - El valor se guarda y muestra correctamente en la tabla, sin errores visuales o lógicos.
    """
    def test_edit_teacher_address_special_characters(self):
        driver = self.driver
        driver.get(self.live_server_url)

        # login como admin
        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys('admin@pruebas.com')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[3]').send_keys('pruebas')
        driver.find_element(By.XPATH, '/html/body/div/div/form/input[4]').click()

        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div/div/main/div/div[1]/div/h3'))
        )

        reset_roberto(driver, self.live_server_url) # funcion auxiliar para resetear el profesor Roberto a su estado original

        # redireccionar a la pagina de profesores
        driver.get(self.live_server_url + "/manageteacher/")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'table')))

        # lista de direcciones con caracteres especiales
        special_addresses = ["Calle 5", "#123-Apt°", "‘Barrio Sur"]

        for address in special_addresses:
            # ir a vista de profesores
            driver.get(self.live_server_url + "/manageteacher/")
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//table')))

            # buscar profesor "Roberto"
            target_row = None
            for row in driver.find_elements(By.XPATH, '//table/tbody/tr'):
                if row.is_displayed() and "roberto" in row.text.lower():
                    target_row = row
                    break

            self.assertIsNotNone(target_row, "No se encontró un profesor con nombre 'Roberto'.")

            # ir al formulario de edicion
            edit_btn = target_row.find_element(By.XPATH, './/td[last()-1]/a')
            edit_btn.click()

            # esperar campo Address y cambiar
            address_input = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.NAME, "address"))
            )
            address_input.clear()
            address_input.send_keys(address)

            # guardar cambios
            submit_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//button[@type="submit" and contains(text(), "Update")]'))
            )
            driver.execute_script("arguments[0].click();", submit_btn)

            # volver a la tabla y revisar que se guardo bien
            driver.get(self.live_server_url + "/manageteacher/")
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//table')))

            updated = False
            for row in driver.find_elements(By.XPATH, '//table/tbody/tr'):
                if row.is_displayed() and "roberto" in row.text.lower() and address.lower() in row.text.lower():
                    updated = True
                    break

            self.assertTrue(
                updated,
                f"La dirección '{address}' no se guardó o mostró correctamente en la tabla.")

if __name__ == '__main__':
    unittest.main(verbosity=2)
