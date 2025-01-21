from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, redirect, url_for
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import requests
import re

app = Flask(__name__)

# Configuração do Selenium com ChromeDriver
def get_driver():
    chrome_options = Options()
    #chrome_options.add_argument("--headless")  # Executa sem abrir o navegador
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_service = ChromeService(executable_path='chromedriver.exe')
    return webdriver.Chrome(service=chrome_service, options=chrome_options)

# Função para carregar e processar a página
def scrape_with_Catalog(keyword):
    link = f'https://store.usp.org/product/{keyword}'
    driver = get_driver()
    try:
        # Acessar a página
        driver.get(link)

        # Esperar que um elemento carregue (ajuste o seletor de acordo com a página)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'attr-value'))
        )

        # Pegar o HTML carregado
        page_source = driver.page_source

        # Usar BeautifulSoup para tratar os dados
        soup = BeautifulSoup(page_source, 'html.parser')
        get = soup.find_all('div',attrs={"class":"usp-certificates"})
        lot_data = []
        for element in get:
            tbody = element.find('tbody')  # Encontre o tbody dentro do elemento
            if tbody:  # Verifique se o tbody existe
                for row in tbody.find_all('tr'):
                    lot_number = row.find_all('td')[0].text.strip()
                    valid_date = row.find_all('td')[2].text.strip()

                    # Limpar o lote, removendo '(Current)' ou similares
                    lot_number_cleaned = re.sub(r'\s*\(.*?\)', '', lot_number)

                    lot_data.append((lot_number_cleaned, valid_date))

        # Exibir os resultados
        return lot_data

    finally:
        driver.quit()
    
def download_certificate(keyword, lote):
    url = f'https://static.usp.org/pdf/EN/referenceStandards/certificates/{keyword}-{lote}.pdf'
    response = requests.get(url)
    if response.status_code == 200:
        file_path = os.path.join('certificates', f'{keyword}-{lote}.pdf')
        os.makedirs('certificates', exist_ok=True)
        with open(file_path, 'wb') as file:
            file.write(response.content)
        return file_path
    else:
        return None

# Rota para servir certificados
@app.route('/certificates/<filename>')
def serve_certificate(filename):
    return send_from_directory('certificates', filename, mimetype='application/pdf')

# Rota principal
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        keywords = request.form.get('keywords')
        keywords_list = [k.strip() for k in keywords.split(',')]
        results = {}
        for keyword in keywords_list:
            try:
                lot_data = scrape_with_Catalog(keyword)
                results[keyword] = lot_data
            except Exception as e:
                results[keyword] = []
        return render_template('index.html', results=results)
    return render_template('index.html', results={})

# Rota para download de certificado
@app.route('/download', methods=['POST'])
def download():
    keyword = request.form.get('keyword') 
    lote = request.form.get('lote')

    if not keyword or not lote:
        return jsonify({'success': False, 'error': 'Dados insuficientes fornecidos.'}), 400

    file_path = download_certificate(keyword, lote)
    if file_path:
        # Extrair apenas o nome do arquivo (sem o diretório)
        filename = os.path.basename(file_path)
        # Redirecionar para a rota que serve o arquivo
        return redirect(url_for('serve_certificate', filename=filename))
    
    return jsonify({'success': False, 'error': 'Erro ao baixar o certificado.'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
    # app.run(host='0.0.0.0', port=10000, debug=False, allow_unsafe_werkzeug=True)