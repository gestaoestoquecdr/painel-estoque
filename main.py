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

REPORTS_CONFIG = [
    {"menu": "1666", "folder_id": "15mzmHiAGRKR5rhDWgzHwIy6OptEgZ2j0"},
    {"menu": "1926", "folder_id": "1M5eEwCHSEGMYpzFzL6WtisF2YdeF36hl"},
    {"menu": "1672", "folder_id": "12PbQkZSp40kRmJClQfOYk8-inPekHfi7"},
    {"menu": "1682", "folder_id": "1fyqjJ9Y5NPJ1kjFR38lluDYdLfhCji4K"}
]

def upload_to_drive(file_path, folder_id):
    file_name = os.path.basename(file_path)
    print(f"A enviar '{file_name}' para o Google Drive...")
    file_metadata = {'name': file_name, 'parents': [folder_id]}
    media = MediaFileUpload(file_path, resumable=True)
    uploaded = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f"Sucesso! Ficheiro enviado com ID: {uploaded.get('id')}")

# ---------------------------------------------------------
# 2. Configurar o Selenium Chrome em modo Headless
# ---------------------------------------------------------
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")

download_dir = os.path.join(os.getcwd(), "downloads")
os.makedirs(download_dir, exist_ok=True)
chrome_options.add_experimental_option("prefs", {
    "download.default_directory": download_dir,
    "download.prompt_for_download": False,
    "directory_upgrade": True,
    "safebrowsing.enabled": True
})

driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 20)

try:
    print("Conectando ao Bluesoft ERP...")
    driver.get("https://erp.bluesoft.com.br/roldao/seguranca/login/login?redirectTo=/app/#/menu")
    
    # Preenchimento de Login
    user_elem = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@name='username' or @id='username' or @type='text']")))
    user_elem.clear()
    user_elem.send_keys(os.environ['WMS_USER'])
    
    pass_elem = driver.find_element(By.XPATH, "//input[@name='password' or @id='password' or @type='password']")
    pass_elem.clear()
    pass_elem.send_keys(os.environ['WMS_PASS'])
    
    driver.find_element(By.XPATH, "//button[@type='submit'] | //input[@type='submit']").click()
    time.sleep(5)
    print("Login efetuado com sucesso!")

    for item in REPORTS_CONFIG:
        menu_code = item["menu"]
        folder_id = item["folder_id"]
        print(f"\n--- Processando Menu {menu_code} ---")
        
        driver.get(f"https://erp.bluesoft.com.br/roldao/app/#/menu/{menu_code}")
        time.sleep(6)
        
        # Verificar se a tela carrega dentro de um iframe
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if len(iframes) > 0:
            driver.switch_to.frame(0)

        # 1. Clicar no botão BUSCAR para carregar a tabela com os dados
        try:
            buscar_btn = wait.until(
                EC.element_to_be_clickable((
                    By.XPATH, 
                    "//button[contains(text(), 'BUSCAR') or contains(text(), 'Buscar') or contains(text(), 'Consultar') or contains(@class, 'btn-primary')]"
                ))
            )
            buscar_btn.click()
            print(f"Botão BUSCAR clicado no menu {menu_code}. Aguardando dados...")
            time.sleep(8)
        except Exception as e:
            print(f"Aviso: Não foi necessário/possível clicar em BUSCAR: {e}")

        # 2. Clicar no botão do Menu da Tabela UI-Grid (Ícone de Opções/Grelha)
        try:
            grid_menu_btn = wait.until(
                EC.element_to_be_clickable((
                    By.XPATH, 
                    "//div[contains(@class, 'ui-grid-menu-button')] | //button[contains(@class, 'ui-grid-menu-button')]"
                ))
            )
            grid_menu_btn.click()
            time.sleep(2)
            
            # 3. Clicar na opção 'Exportar todos os dados como excel'
            export_excel_btn = wait.until(
                EC.element_to_be_clickable((
                    By.XPATH, 
                    "//button[contains(text(), 'Exportar todos os dados como excel') or contains(text(), 'como excel')]"
                ))
            )
            export_excel_btn.click()
            print(f"Exportação para Excel disparada no menu {menu_code}!")
            time.sleep(10)  # Aguarda tempo do download terminar
            
        except Exception as err:
            print(f"Erro ao tentar exportar a grelha no menu {menu_code}: {err}")
            driver.switch_to.default_content()
            continue

        driver.switch_to.default_content()

        # 4. Verificar download e enviar para o Google Drive
        downloaded = glob.glob(os.path.join(download_dir, "*"))
        if downloaded:
            latest = max(downloaded, key=os.path.getmtime)
            if os.path.isfile(latest) and not latest.endswith(".crdownload"):
                upload_to_drive(latest, folder_id)
                os.remove(latest)
            else:
                print(f"O ficheiro ainda está em transferência ou é inválido: {latest}")
        else:
            print(f"Nenhum ficheiro descarregado para o menu {menu_code}.")

except Exception as e:
    print(f"Falha na execução: {e}")
    raise e

finally:
    driver.quit()
    print("\nProcessamento concluído.")
