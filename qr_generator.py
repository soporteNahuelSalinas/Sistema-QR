import json
import requests
from requests.auth import HTTPBasicAuth
import qrcode
import os
import xml.etree.ElementTree as ET
import re

# Configuraciones de la API
api_url = 'https://tienda.anywayinsumos.com.ar/api/products/'
api_key = '7FBXGUHYR2PXIGBS7GC3AAQ7BHEQX57E'
tinyurl_api_url = 'http://tinyurl.com/api-create.php?url='
output_dir = 'qrcodes-manuales'

# Limpieza de nombres
def clean_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', '_', name)
    return name.strip()[:100]  # Limita el nombre a 100 caracteres

# Normalizar precios con impuestos
def normalize_price(price, tax_type):
    try:
        price = float(price)
        if tax_type == "1":
            price *= 1.21  # Aplicar IVA 21%
        elif tax_type == "2":
            price *= 1.105  # Aplicar IVA 10.5%
        return str(int(price))  # Convertir a entero sin decimales
    except ValueError:
        return "0"

# Obtener datos del producto
def fetch_product_data(product_id):
    url = f"{api_url}{product_id}"
    try:
        response = requests.get(url, auth=HTTPBasicAuth(api_key, ''), timeout=10)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        product_name = root.find('.//name/language').text
        link_rewrite = root.find('.//link_rewrite/language').text
        reference = root.find('.//reference').text
        price = root.find('.//price').text  # Obtener precio base
        tax_type = root.find('.//id_tax_rules_group').text  # Obtener ID de reglas de impuestos
        final_price = normalize_price(price, tax_type)  # Aplicar impuestos según el ID

        return {
            "id": product_id,
            "name": product_name,
            "link_rewrite": link_rewrite,
            "reference": reference,
            "price": final_price,
            "tax_type": tax_type
        }
    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud para el producto {product_id}: {e}")
    except ET.ParseError:
        print(f"Error al parsear XML para el producto {product_id}.")
    return None

# Generar código QR
def generate_qr(product_data):
    os.makedirs(output_dir, exist_ok=True)
    product_url = f"https://tienda.anywayinsumos.com.ar/{product_data['link_rewrite']}/{product_data['id']}-{product_data['link_rewrite']}.html"
    
    try:
        # Acortar la URL con TinyURL
        response = requests.get(tinyurl_api_url + product_url, timeout=10)
        response.raise_for_status()
        short_url = response.text

        # Generar código QR a partir de la URL acortada
        qr_img = qrcode.make(short_url)
        cleaned_name = clean_filename(product_data["name"])
        qr_filename = os.path.join(output_dir, f"{cleaned_name}_{product_data['reference']}_Precio ${product_data['price']}.png")

        if os.path.exists(qr_filename):
            print(f"El archivo {qr_filename} ya existe. Saltando...")
            return

        qr_img.save(qr_filename)
        print(f"Código QR generado: {qr_filename}")
    except requests.exceptions.RequestException as e:
        print(f"Error al acortar URL para el producto {product_data['id']}: {e}")
    except Exception as e:
        print(f"Error al generar el código QR: {e}")

# Generar códigos QR para una lista de IDs
def generate_qr_codes(product_ids):
    for product_id in product_ids:
        product_data = fetch_product_data(product_id)
        if product_data:
            generate_qr(product_data)

# Ejecución principal
if __name__ == "__main__":
    product_ids = [1, 2, 3, 4, 5]  # Reemplazar con IDs reales
    generate_qr_codes(product_ids)