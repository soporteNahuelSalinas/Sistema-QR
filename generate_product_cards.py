import os
import re
import math
from PIL import Image, ImageDraw, ImageFont
import textwrap
from PyPDF2 import PdfMerger

# Configuración general
dpi = 300
a4_width, a4_height = int(8.27 * dpi), int(11.69 * dpi)
card_width, card_height = 780, 340
output_folder = "output_pdfs"
qr_folder = "qrcodes-manuales"
page_color = "#D4C3C3"
qr_max_height = card_height - int(0.1 * dpi + 2)
background_color = "#FFFF"
font_color = "black"
margin = int(0.01 * dpi)
spacing = int(0.02 * dpi)
columns = 3
max_rows_per_page = 10

# Ruta relativa a la fuente en tu proyecto
font_path = os.path.join("assets", "fonts", "Poppins-Regular.ttf")
if not os.path.exists(font_path):
    raise FileNotFoundError(f"No se encontró la fuente en la ubicación especificada: {font_path}")

# Crear la fuente
font_size = 30
font = ImageFont.truetype(font_path, font_size)
font_large = ImageFont.truetype(font_path, font_size * 2)  # Doble tamaño para el precio

def format_price(price):
    """ Formatea el precio redondeando hacia arriba a la siguiente decena. """
    rounded_price = math.ceil(int(price) / 10) * 10  # Redondea siempre hacia arriba
    return f"AR ${rounded_price:,}".replace(",", ".")

def clean_product_name(filename):
    name = os.path.splitext(filename)[0]
    name = re.sub(r"[_-]", " ", name)
    
    price_match = re.search(r"Precio \$(\d+)", name)
    price = format_price(price_match.group(1)) if price_match else ""

    ref_match = re.search(r"(\d+)\s+Precio", name)
    reference = ref_match.group(1) if ref_match else ""

    clean_name = re.sub(r"\d+\s+Precio.*$", "", name).strip()

    return clean_name, reference, price

def generate_cards():
    os.makedirs(output_folder, exist_ok=True)
    if not os.path.exists(qr_folder):
        raise FileNotFoundError(f"No se encontró el directorio de QR: {qr_folder}")

    product_data = []
    for file in os.listdir(qr_folder):
        if file.endswith(".png"): 
            product_name, reference, price = clean_product_name(file)
            product_data.append({"name": product_name, "reference": reference, "price": price, "qr_path": os.path.join(qr_folder, file)})

    page_count = 1
    x_offset, y_offset = margin, margin
    current_row = 0
    page = Image.new("RGB", (a4_width, a4_height), page_color)
    pdf_files = []

    for i, product in enumerate(product_data):
        card = Image.new("RGB", (card_width, card_height), background_color)
        card_draw = ImageDraw.Draw(card)

        qr = Image.open(product["qr_path"])
        qr_width = int(qr.width * (qr_max_height / qr.height))
        qr = qr.resize((qr_width, qr_max_height))
        qr_x = card_width - qr.width - margin
        qr_y = (card_height - qr.height) // 2
        card.paste(qr, (qr_x, qr_y))

        # Texto CTA debajo del QR
        cta_text = "Ver más info"
        cta_font = ImageFont.truetype(font_path, 22)
        cta_bbox = card_draw.textbbox((0, 0), cta_text, font=cta_font)
        cta_width = cta_bbox[2] - cta_bbox[0]
        cta_x = qr_x + (qr.width - cta_width) // 2
        cta_y = qr_y + qr.height - 25
        card_draw.text((cta_x, cta_y), cta_text, font=cta_font, fill=font_color)

        text_max_width = card_width - qr_width - margin * 3
        text_x_center_area = (card_width - qr_width - text_max_width) // 2 + 15
        text_y = margin

        wrapped_text = product["name"]
        if len(wrapped_text) > 100:
            wrapped_text = textwrap.shorten(wrapped_text, width=100, placeholder="...")

        if product["reference"]:
            wrapped_text += f" (Ref: {product['reference']})"
        
        wrapped_text = textwrap.fill(wrapped_text, width=25)

        text_bbox = card_draw.textbbox((0, 0), wrapped_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        text_x = text_x_center_area + (text_max_width - text_width) // 2
        text_y = (card_height - text_height) // 2 + 20

        if product["price"]:
            price_text = product["price"]
            price_bbox = card_draw.textbbox((0, 0), price_text, font=font_large)
            price_width = price_bbox[2] - price_bbox[0]
            price_x = (card_width - price_width) // 2 - 130
            price_y = margin + 30
            card_draw.text((price_x, price_y), price_text, font=font_large, fill=font_color)

        final_text = "\n".join([wrapped_text])
        card_draw.multiline_text((text_x, text_y), final_text, font=font, fill=font_color, align="center")

        page.paste(card, (x_offset, y_offset))
        x_offset += card_width + spacing

        if (i + 1) % columns == 0:
            x_offset = margin
            y_offset += card_height + spacing
            current_row += 1

        if current_row >= max_rows_per_page:
            output_file = os.path.join(output_folder, f"tarjetas_qr_pagina_{page_count}.pdf")
            page.save(output_file, resolution=dpi)
            pdf_files.append(output_file)
            page_count += 1
            page = Image.new("RGB", (a4_width, a4_height), page_color)
            x_offset, y_offset = margin, margin 
            current_row = 0 

    if x_offset != margin or y_offset != margin:
        output_file = os.path.join(output_folder, f"tarjetas_qr_pagina_{page_count}.pdf")
        page.save(output_file, resolution=dpi)
        pdf_files.append(output_file)

    merged_pdf_path = os.path.join(output_folder, "tarjetas_productos_completo.pdf")
    merger = PdfMerger()
    for pdf in pdf_files:
        merger.append(pdf)
    merger.write(merged_pdf_path)
    merger.close()

    print("Generación completa. Archivo combinado en:", merged_pdf_path)
    return merged_pdf_path

if __name__ == "__main__":
    generate_cards()