import os
import time
import json
import glob
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ---------------------------------------------------------
# 1. Autenticação na API do Google Drive via Conta de Serviço
# ---------------------------------------------------------
SCOPES = ['https://www.googleapis.com/auth/drive']
service_account_info = json.loads(os.environ['GCP_SERVICE_ACCOUNT_JSON'])
creds = ServiceAccountCredentials.from_service_account_info(service_account_info, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=creds)

# Mapeamento dos Menus do WMS com as Pastas do Google Drive
REPORTS_CONFIG = [
    {"menu": "1666", "folder_id": "15mzmHiAGRKR5rhDWgzHwIy6OptEgZ2j0"},
    {"menu": "1926", "folder_id": "1M5eEwCHSEGMYpzFzL6WtisF2YdeF36hl"},
    {"menu": "1672", "folder_id": "12PbQkZSp40kRmJClQfOYk8-inPekHfi7"},
    {"menu": "1682", "folder_id": "1fyqjJ9Y5NPJ1kjFR38lluDYdLfhCji4K"}
]

def upload_to_drive(file_path, folder_id):
    """Envia um ficheiro local para a pasta específica do Google Drive."""
    file_name = os.path.basename(file_path)
    print(f"A enviar '{file_name}' para o Google Drive (Pasta ID: {folder_id})...")
    
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_path, resumable=True)
    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    
    print(f"Ficheiro '{file_name}' enviado com sucesso! ID: {uploaded_file.get('id')}")

# ---------------------------------------------------------
# 2. Configuração do Selenium Chrome em modo Headless
# ---------------------------------------------------------
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
    "directory_upgrade": True,
    "safebrowsing.enabled": True
}
chrome_options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 20)

try:
    print("Iniciando acesso ao WMS Bluesoft...")
    driver.get("https://erp.bluesoft.com.br/roldao/seguranca/login/login?redirectTo=/app/#/menu")
    
    # Preenchimento das credenciais de acesso
    username_input = wait.until(
        EC.presence_of_element_located((
            By.XPATH, 
            "//input[@name='username' or @id='username' or @name='usuario' or @id='usuario' or @type='text']"
        ))
    )
    username_input.clear()
    username_input.send_keys(os.environ['WMS_USER'])
    
    password_input = driver.find_element(
        By.XPATH, 
        "//input[@name='password' or @id='password' or @name='senha' or @id='senha' or @type='password']"
    )
    password_input.clear()
    password_input.send_keys(os.environ['WMS_PASS'])
    
    submit_button = driver.find_element(
        By.XPATH, 
        "//button[@type='submit'] | //input[@type='submit'] | //button[contains(text(), 'Entrar')]"
    )
    submit_button.click()
    
    time.sleep(5)
    print("Login efetuado com sucesso!")

    # ---------------------------------------------------------
    # 3. Processamento e Extração de cada Relatório
    # ---------------------------------------------------------
    for item in REPORTS_CONFIG:
        menu_code = item["menu"]
        folder_id = item["folder_id"]
        
        print(f"\n--- Processando Relatório Menu {menu_code} ---")
        
        # Aceder diretamente à URL do menu
        driver.get(f"https://erp.bluesoft.com.br/roldao/app/#/menu/{menu_code}")
        time.sleep(4)
        
        # Tentar acionar o botão de consulta/execução do relatório
        try:
            consult_btn = driver.find_element(
                By.XPATH, 
                "//button[contains(text(), 'Consultar') or contains(text(), 'Pesquisar') or contains(text(), 'Gerar')]"
            )
            consult_btn.click()
            time.sleep(5)
        except Exception:
            print(f"Aviso: Botão de consulta padrão não localizado no menu {menu_code} ou carregamento automático.")

        # Tentar clicar no botão de exportação (Excel / CSV / Download)
        try:
            export_btn = wait.until(
                EC.element_to_be_clickable((
                    By.XPATH, 
                    "//button[contains(@title, 'Excel') or contains(text(), 'Excel') or contains(@class, 'export') or contains(text(), 'Exportar')]"
                ))
            )
            export_btn.click()
            print(f"Download iniciado para o menu {menu_code}...")
            time.sleep(7)
        except Exception as err:
            print(f"Não foi possível exportar o menu {menu_code} automaticamente: {err}")
            continue

        # Identificar o ficheiro descarregado e enviar para o Google Drive
        downloaded_files = glob.glob(os.path.join(download_dir, "*"))
        if downloaded_files:
            latest_file = max(downloaded_files, key=os.path.getmtime)
            
            if os.path.isfile(latest_file) and not latest_file.endswith(".crdownload"):
                upload_to_drive(latest_file, folder_id)
                os.remove(latest_file)
            else:
                print(f"O ficheiro ainda está em transferência ou é inválido: {latest_file}")
        else:
            print(f"Nenhum ficheiro encontrado na pasta de transferências para o menu {menu_code}.")

except Exception as e:
    print(f"Erro durante o fluxo de execução: {str(e)}")
    raise e

finally:
    driver.quit()
    print("\nExecução concluída.")
