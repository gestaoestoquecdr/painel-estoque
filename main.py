import os
import time
import json
import glob
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- CONFIGURAÇÃO DE LOGS ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# --- 1. AUTENTICAÇÃO E CONFIGURAÇÃO DA API DO GOOGLE DRIVE ---
SCOPES = ['https://www.googleapis.com/auth/drive']
service_account_info = json.loads(os.environ['GCP_SERVICE_ACCOUNT_JSON'])
creds = ServiceAccountCredentials.from_service_account_info(service_account_info, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=creds)

# Mapeamento dos Menus com os IDs Reais das Pastas do Google Drive
PASTAS_DRIVE = {
    "1666": "15mzmHiAGRKR5rhDWgzHwIy6OptEgZ2j0",
    "1926": "1M5eEwCHSEGMYpzFzL6WtisF2YdeF36hl",
    "1672": "12PbQkZSp40kRmJClQfOYk8-inPekHfi7",
    "1682": "1fyqjJ9Y5NPJ1kjFR38lluDYdLfhCji4K"
}

def enviar_para_google_drive(caminho_arquivo_local, menu_code, prefixo_nome):
    """Envia o relatório baixado localmente direto para a pasta correta no Google Drive."""
    folder_id = PASTAS_DRIVE.get(menu_code)
    if not folder_id:
        print(f"❌ ID da pasta para o menu {menu_code} não localizado.")
        return

    extensao = os.path.splitext(caminho_arquivo_local)[1]
    data_hora = datetime.now().strftime("%Y-%m-%d_%H-%M")
    novo_nome = f"{prefixo_nome}_{data_hora}{extensao}"

    print(f"⏳ Enviando '{novo_nome}' para a pasta do Google Drive (ID: {folder_id})...")

    file_metadata = {
        'name': novo_nome,
        'parents': [folder_id]
    }
    media = MediaFileUpload(caminho_arquivo_local, resumable=True)
    uploaded = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    
    print(f"✅ SUCESSO: Arquivo {novo_nome} enviado para o Drive com ID: {uploaded.get('id')}\n")

def processar_download_e_upload(pasta_downloads, prefixo_nome, tempo_clique, menu_code):
    """Aguarda o término do download e realiza o upload para a nuvem."""
    caminho_arquivo_baixado = None

    for _ in range(30):
        time.sleep(1)
        arquivos = glob.glob(os.path.join(pasta_downloads, "*.xlsx")) + glob.glob(os.path.join(pasta_downloads, "*.csv"))
        if arquivos:
            ultimo = max(arquivos, key=os.path.getmtime)
            if os.path.getmtime(ultimo) >= tempo_clique - 2:
                if not glob.glob(os.path.join(pasta_downloads, "*.crdownload")):
                    caminho_arquivo_baixado = ultimo
                    break

    if not caminho_arquivo_baixado:
        msg_erro = f"❌ ERRO: O download de {prefixo_nome} não foi concluído a tempo!"
        print(msg_erro)
        logging.error(msg_erro)
        return

    # Envia para o Drive e deleta o arquivo temporário
    enviar_para_google_drive(caminho_arquivo_baixado, menu_code, prefixo_nome)
    os.remove(caminho_arquivo_baixado)

def rodar_automacao():
    print("🚀 Iniciando automação dos relatórios Bluesoft ERP no GitHub Actions...")

    # Configuração do Chrome Headless e Pasta de Downloads no Linux do GitHub
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

    navegador = None

    try:
        navegador = webdriver.Chrome(options=chrome_options)
        url = "https://erp.bluesoft.com.br/roldao/seguranca/login/login.action"
        navegador.get(url)

        time.sleep(3)

        # --- LOGIN COM SECRETS DO GITHUB ---
        campo_usuario = WebDriverWait(navegador, 10).until(
            EC.visibility_of_element_located((By.ID, "j_username"))
        )
        campo_usuario.send_keys(os.environ['WMS_USER'])

        campo_senha = WebDriverWait(navegador, 10).until(
            EC.visibility_of_element_located((By.ID, "j_password"))
        )
        campo_senha.send_keys(os.environ['WMS_PASS'])

        botao_entrar = WebDriverWait(navegador, 15).until(
            EC.element_to_be_clickable((By.ID, "btnSubmit"))
        )
        botao_entrar.click()

        print("Login efetuado com sucesso!")
        time.sleep(5)

        # ==========================================
        # 1º RELATÓRIO (MENU 1666 - Padrão Grid)
        # ==========================================
        print("\n--- 1/4: Processando Menu 1666 ---")
        navegador.get("https://erp.bluesoft.com.br/roldao/menu/1666")
        time.sleep(4)

        botao_buscar_1 = WebDriverWait(navegador, 15).until(
            EC.presence_of_element_located((By.XPATH, "//button[@descricao='Buscar' or contains(., 'Buscar')]"))
        )
        navegador.execute_script("arguments[0].click();", botao_buscar_1)
        time.sleep(3)

        menu_grid_1 = WebDriverWait(navegador, 15).until(
            EC.presence_of_element_located((By.XPATH, "//i[contains(@class, 'ui-grid-icon-menu')]"))
        )
        navegador.execute_script("arguments[0].click();", menu_grid_1)
        time.sleep(2)

        botao_exportar_excel_1 = WebDriverWait(navegador, 15).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Exportar todos os dados como excel')]"))
        )

        tempo_clique_1 = time.time()
        navegador.execute_script("arguments[0].click();", botao_exportar_excel_1)
        print("Download do Menu 1666 iniciado...")
        processar_download_e_upload(download_dir, "Relatorio_1666", tempo_clique_1, "1666")

        # ==========================================
        # 2º RELATÓRIO (MENU 1926 - Dropdown Verde)
        # ==========================================
        print("\n--- 2/4: Processando Menu 1926 ---")
        navegador.get("https://erp.bluesoft.com.br/roldao/menu/1926")
        time.sleep(3)

        botao_buscar_2 = WebDriverWait(navegador, 15).until(
            EC.presence_of_element_located((By.ID, "btnSubmit"))
        )
        navegador.execute_script("arguments[0].click();", botao_buscar_2)
        time.sleep(3)

        dropdown_exportar_2 = WebDriverWait(navegador, 15).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(@class, 'btn-success') and contains(@class, 'dropdown-toggle')]"))
        )
        navegador.execute_script("arguments[0].click();", dropdown_exportar_2)
        time.sleep(2)

        opcao_excel_2 = WebDriverWait(navegador, 15).until(
            EC.presence_of_element_located((By.XPATH, "//a[@data-format='xlsx' or contains(., 'Exportar Excel')]"))
        )

        tempo_clique_2 = time.time()
        navegador.execute_script("arguments[0].click();", opcao_excel_2)
        print("Download do Menu 1926 iniciado...")
        processar_download_e_upload(download_dir, "Relatorio_1926", tempo_clique_2, "1926")

        # ==========================================
        # 3º RELATÓRIO (MENU 1682 - Padrão Grid)
        # ==========================================
        print("\n--- 3/4: Processando Menu 1682 ---")
        navegador.get("https://erp.bluesoft.com.br/roldao/menu/1682")
        time.sleep(4)

        botao_buscar_3 = WebDriverWait(navegador, 15).until(
            EC.presence_of_element_located((By.XPATH, "//button[@descricao='Buscar' or contains(., 'Buscar')]"))
        )
        navegador.execute_script("arguments[0].click();", botao_buscar_3)
        time.sleep(3)

        menu_grid_3 = WebDriverWait(navegador, 15).until(
            EC.presence_of_element_located((By.XPATH, "//i[contains(@class, 'ui-grid-icon-menu')]"))
        )
        navegador.execute_script("arguments[0].click();", menu_grid_3)
        time.sleep(2)

        botao_exportar_excel_3 = WebDriverWait(navegador, 15).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Exportar todos os dados como excel')]"))
        )

        tempo_clique_3 = time.time()
        navegador.execute_script("arguments[0].click();", botao_exportar_excel_3)
        print("Download do Menu 1682 iniciado...")
        processar_download_e_upload(download_dir, "Relatorio_1682", tempo_clique_3, "1682")

        # ==========================================
        # 4º RELATÓRIO (MENU 1672 - Dropdown Verde)
        # ==========================================
        print("\n--- 4/4: Processando Menu 1672 ---")
        navegador.get("https://erp.bluesoft.com.br/roldao/menu/1672")
        time.sleep(3)

        botao_buscar_4 = WebDriverWait(navegador, 15).until(
            EC.presence_of_element_located((By.ID, "btnSubmit"))
        )
        navegador.execute_script("arguments[0].click();", botao_buscar_4)
        time.sleep(3)

        dropdown_exportar_4 = WebDriverWait(navegador, 15).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(@class, 'btn-success') and contains(@class, 'dropdown-toggle')]"))
        )
        navegador.execute_script("arguments[0].click();", dropdown_exportar_4)
        time.sleep(2)

        opcao_excel_4 = WebDriverWait(navegador, 15).until(
            EC.presence_of_element_located((By.XPATH, "//a[@data-format='xlsx' or contains(., 'Exportar Excel')]"))
        )

        tempo_clique_4 = time.time()
        navegador.execute_script("arguments[0].click();", opcao_excel_4)
        print("Download do Menu 1672 iniciado...")
        processar_download_e_upload(download_dir, "Relatorio_1672", tempo_clique_4, "1672")

        print("🎉 Processo concluído com sucesso! Os 4 relatórios foram salvos nas pastas do Google Drive.")

    except Exception as erro:
        print(f"❌ Erro durante a execução da automação: {erro}")
        raise erro

    finally:
        if navegador:
            navegador.quit()

if __name__ == "__main__":
    rodar_automacao()
