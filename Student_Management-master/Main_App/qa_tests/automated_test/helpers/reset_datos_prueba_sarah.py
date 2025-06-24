from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
import time

def reset_roberto(driver, base_url):
    driver.get(base_url + "/manageteacher/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'table')))

    # eliminar si ya existe
    for row in driver.find_elements(By.XPATH, '//table/tbody/tr'):
        if "roberto" in row.text.lower():
            row.find_element(By.XPATH, './/td[last()]/a').click()
            time.sleep(1)
            break

    # agregar desde cero
    driver.get(base_url + "/addteacher/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "firstname")))

    driver.find_element(By.NAME, "firstname").send_keys("Roberto")
    driver.find_element(By.NAME, "lastname").send_keys("Gomez")
    driver.find_element(By.NAME, "email").send_keys("roberto.gomez9@gmail.com")
    Select(driver.find_element(By.NAME, "gender")).select_by_visible_text("Male")
    driver.find_element(By.NAME, "address").send_keys("San José, Curridabat")

    driver.find_element(By.XPATH, '//button[@type="submit"]').click()
    time.sleep(1)

def reset_kristel(driver, base_url):
    driver.get(base_url + "/managestudent/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'table')))

    for row in driver.find_elements(By.XPATH, '//table/tbody/tr'):
        if "kristel" in row.text.lower():
            row.find_element(By.XPATH, './/td[last()]/a').click()
            time.sleep(1)
            break

    driver.get(base_url + "/addstudent/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "firstname")))

    driver.find_element(By.NAME, "firstname").send_keys("Kristel")
    driver.find_element(By.NAME, "lastname").send_keys("Campos")
    driver.find_element(By.NAME, "email").send_keys("kristel.campos@gmail.com")
    Select(driver.find_element(By.NAME, "gender")).select_by_visible_text("Female")
    Select(driver.find_element(By.NAME, "std")).select_by_visible_text("8")
    Select(driver.find_element(By.NAME, "medium")).select_by_visible_text("Foundation")
    driver.find_element(By.NAME, "address").send_keys("Costa Rica, Alajuela, Grecia")

    driver.find_element(By.XPATH, '//button[@type="submit"]').click()
    time.sleep(1)

def reset_borrador_teacher(driver, base_url):
    driver.get(base_url + "/manageteacher/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'table')))

    for row in driver.find_elements(By.XPATH, '//table/tbody/tr'):
        if "borrador" in row.text.lower():
            row.find_element(By.XPATH, './/td[last()]/a').click()
            time.sleep(1)
            break

    driver.get(base_url + "/addteacher/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "firstname")))

    driver.find_element(By.NAME, "firstname").send_keys("Borrador")
    driver.find_element(By.NAME, "lastname").send_keys("Prueba")
    driver.find_element(By.NAME, "email").send_keys("borrador.prueba@gmail.com")
    Select(driver.find_element(By.NAME, "gender")).select_by_visible_text("Male")
    driver.find_element(By.NAME, "address").send_keys("Dirección temporal")

    driver.find_element(By.XPATH, '//button[@type="submit"]').click()
    time.sleep(1)

def reset_borrador_student(driver, base_url):
    driver.get(base_url + "/managestudent/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'table')))

    for row in driver.find_elements(By.XPATH, '//table/tbody/tr'):
        if "borrador" in row.text.lower():
            row.find_element(By.XPATH, './/td[last()]/a').click()
            time.sleep(1)
            break

    driver.get(base_url + "/addstudent/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "firstname")))

    driver.find_element(By.NAME, "firstname").send_keys("Borrador")
    driver.find_element(By.NAME, "lastname").send_keys("Prueba")
    driver.find_element(By.NAME, "email").send_keys("borrador.student@gmail.com")
    Select(driver.find_element(By.NAME, "gender")).select_by_visible_text("Male")
    Select(driver.find_element(By.NAME, "std")).select_by_visible_text("7")
    Select(driver.find_element(By.NAME, "medium")).select_by_visible_text("Foundation")
    driver.find_element(By.NAME, "address").send_keys("Zona de pruebas")

    driver.find_element(By.XPATH, '//button[@type="submit"]').click()
    time.sleep(1)
