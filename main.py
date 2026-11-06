import os
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# 1. Autenticação na API do Google Drive via Conta de Serviço
SCOPES = ['https://www.googleapis.com/auth/drive']
service_account_info = json.loads(os.environ['GCP_SERVICE_ACCOUNT_JSON'])
creds = ServiceAccountCredentials.from_service_account_info(service_account_info, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=creds)

# Mapeamento dos Relatórios para as respetivas pastas no Drive
# (Certifique-se de validar se estes IDs correspondem às suas pastas)
REPORTS = [
    {"menu": "1666", "folder_id": "14Dgaf..."}, # Substiua pelo ID real da pasta 1666 se necessário
    {"menu": "1926", "folder_id": "..."},
    {"menu": "1672", "folder_id": "..."},
    {"menu": "1682", "folder_id": "..."}
]

def upload_to_drive(file_path, folder_id):
    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_path, resumable=True)
    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    print(f"Ficheiro {os.path.basename(file_path)} enviado com sucesso! ID: {uploaded_file.get('id')}")

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

try:
    # Fazer Login no WMS Bluesoft
    driver.get("https://erp.bluesoft.com.br/roldao/seguranca/login/login?redirectTo=/app/#/menu") # Coloque a URL do seu WMS
    time.sleep(2)
    
    driver.find_element(By.ID, "username").send_keys(os.environ['WMS_USER']) # Ajuste o ID do input se necessário
    driver.find_element(By.ID, "password").send_keys(os.environ['WMS_PASS']) # Ajuste o ID do input se necessário
    driver.find_element(By.ID, "btn-login").click()
    time.sleep(5)
    
    # Executar a extração dos relatórios
    print("Login efetuado com sucesso!")
    # Adicione a lógica de navegação/download dos relatórios aqui
    
finally:
    driver.quit()
