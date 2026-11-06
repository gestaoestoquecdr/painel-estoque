import os
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# 1. Autenticação na API do Google Drive via Conta de Serviço
SCOPES = ['https://www.googleapis.com/auth/drive']
service_account_info = json.loads(os.environ['GCP_SERVICE_ACCOUNT_JSON'])
creds = ServiceAccountCredentials.from_service_account_info(service_account_info, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=creds)

# 2. Configurar o Selenium Chrome em modo Headless
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")

download_dir = os.path.join(os.getcwd(), "downloads")
os.makedirs(download_dir, exist_ok=True)

prefs = {
    "download.default_directory": download_dir,
    "download.prompt_for_download": False,
    "directory_upgrade": True
}
chrome_options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 15)

try:
    print("Iniciando acesso ao WMS Bluesoft...")
    driver.get("https://erp.bluesoft.com.br/roldao/seguranca/login/login?redirectTo=/app/#/menu")
    
    # Aguardar até 15 segundos para o campo de utilizador carregar no ecrã
    username_input = wait.until(
        EC.presence_of_element_located((
            By.XPATH, 
            "//input[@name='username' or @id='username' or @name='usuario' or @id='usuario' or @type='text']"
        ))
    )
    username_input.clear()
    username_input.send_keys(os.environ['WMS_USER'])
    
    # Localizar campo de palavra-passe
    password_input = driver.find_element(
        By.XPATH, 
        "//input[@name='password' or @id='password' or @name='senha' or @id='senha' or @type='password']"
    )
    password_input.clear()
    password_input.send_keys(os.environ['WMS_PASS'])
    
    # Localizar e clicar no botão de submissão
    submit_button = driver.find_element(
        By.XPATH, 
        "//button[@type='submit'] | //input[@type='submit'] | //button[contains(text(), 'Entrar')]"
    )
    submit_button.click()
    
    time.sleep(5)
    print("Login efetuado com sucesso no Bluesoft Roldão!")

except Exception as e:
    print(f"Erro durante a execução: {str(e)}")
    raise e

finally:
    driver.quit()
