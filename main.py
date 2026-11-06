import os
import time
import json
import glob
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# 1. Google Drive Config
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
    print(f"Sucesso! File ID: {uploaded.get('id')}")

# 2. Configurar Chrome
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
wait = WebDriverWait(driver, 15)

try:
    print("Conectando ao Bluesoft ERP...")
    driver.get("https://erp.bluesoft.com.br/roldao/seguranca/login/login?redirectTo=/app/#/menu")
    
    # Login
    user_elem = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@name='username' or @id='username' or @type='text']")))
    user_elem.clear()
    user_elem.send_keys(os.environ['WMS_USER'])
    
    pass_elem = driver.find_element(By.XPATH, "//input[@name='password' or @id='password' or @type='password']")
    pass_elem.clear()
    pass_elem.send_keys(os.environ['WMS_PASS'])
    
    driver.find_element(By.XPATH, "//button[@type='submit'] | //input[@type='submit']").click()
    time.sleep(5)
    print("Login efetuado!")

    for item in REPORTS_CONFIG:
        menu_code = item["menu"]
        folder_id = item["folder_id"]
        print(f"\n--- Abrindo Menu {menu_code} ---")
        
        # Tenta acionar a barra de pesquisa rápida do menu Bluesoft se disponível, ou via URL direta com refresh
        try:
            driver.get(f"https://erp.bluesoft.com.br/roldao/app/#/menu/{menu_code}")
            time.sleep(5)
            
            # Tirar foto da página para debug se não encontrar botões
            driver.save_screenshot(f"screenshot_menu_{menu_code}.png")
            print(f"Screenshot da tela salva como screenshot_menu_{menu_code}.png")
            
            # Muda para iframe se o Bluesoft carregar a tela dentro de um iframe legacy
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            if len(iframes) > 0:
                print(f"Encontrado {len(iframes)} iframe(s). Alternando...")
                driver.switch_to.frame(0)
            
            # Buscar botão Consultar / Pesquisar
            buttons = driver.find_elements(By.XPATH, "//button | //a | //input[@type='button' or @type='submit']")
            print(f"Elementos clicáveis encontrados na tela: {len(buttons)}")
            
            # Procura por elementos com texto Excel, Exportar ou Gerar
            export_target = None
            for btn in buttons:
                txt = btn.text.lower()
                title = (btn.get_attribute("title") or "").lower()
                val = (btn.get_attribute("value") or "").lower()
                if "excel" in txt or "excel" in title or "excel" in val or "exportar" in txt or "exportar" in title:
                    export_target = btn
                    break
            
            if export_target:
                export_target.click()
                print(f"Botão de exportação clicado no menu {menu_code}!")
                time.sleep(8)
            else:
                print(f"Nenhum botão de Excel/Exportar identificado visivelmente no menu {menu_code}.")

            driver.switch_to.default_content()

        except Exception as e:
            print(f"Erro ao processar menu {menu_code}: {e}")
            driver.switch_to.default_content()
            continue

        # Upload
        downloaded = glob.glob(os.path.join(download_dir, "*"))
        if downloaded:
            latest = max(downloaded, key=os.path.getmtime)
            if os.path.isfile(latest) and not latest.endswith(".crdownload"):
                upload_to_drive(latest, folder_id)
                os.remove(latest)

except Exception as e:
    print(f"Falha na execução: {e}")
    raise e

finally:
    driver.quit()
