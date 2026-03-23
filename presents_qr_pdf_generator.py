import json
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
import io

from app.main import save_presents

PRESENTS_FILE = 'presents.json'
OUTPUT_PDF = 'qr_codes.pdf'
BASE_URL = ""
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
        BASE_URL = config['server_url'] + 'present'
except (FileNotFoundError, KeyError):
    print("Error: 'config.json' not found or 'server_url' key is missing.")
    exit()

# Dim
QR_SIZE = 30 * mm # 3 cm qr size
COLS_PER_ROW = 4
ROW_HEIGHT = 50 * mm
MARGIN_Y_TOP = 20 * mm

def generate_presents_pdf(specific_codes=None):
    try:
        with open(PRESENTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File {PRESENTS_FILE} not found.")
        return
    
    print(f'Total of {len(data)} presents loaded from {PRESENTS_FILE}.')
    
    keys_to_process = []
    data_modified = False

    if specific_codes:
        missing = set(specific_codes) - set(data.keys())
        if missing:
            print(f"These codes were not found and will be skipped: {missing}")

        for code in specific_codes:
            if code in data:
                keys_to_process.append(code)
                # Setting the parameter qr_printed to True if it wasnt
                if not data[code].get('qr_printed', False):
                    data[code]['qr_printed'] = True
                    data_modified = True
                else:
                    # already was True, but just to be sure
                    data[code]['qr_printed'] = True
    else:
        # Create QR codes for all presents that haven't been printed yet
        for code, details in data.items():
            # even if the parameter is missing, we consider it as False
            if not details.get('qr_printed', False):
                keys_to_process.append(code)
                # qr_printed True
                data[code]['qr_printed'] = True
                data_modified = True

    if not keys_to_process:
        print("No new items to print (all QR codes already created or list empty).")
        return

    c = canvas.Canvas(OUTPUT_PDF, pagesize=A4)
    page_width, page_height = A4
    
    col_width = page_width / COLS_PER_ROW
    
    current_col = 0
    current_row_y = page_height - MARGIN_Y_TOP - QR_SIZE

    count = 0
    
    for code in keys_to_process:
        final_url = f"{BASE_URL}?id={code}"
        
        qr = qrcode.QRCode(box_size=10, border=0)
        qr.add_data(final_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        reportlab_img = ImageReader(img_buffer)

        x_pos = (current_col * col_width) + (col_width - QR_SIZE) / 2
        
        # 1. QR
        c.drawImage(reportlab_img, x_pos, current_row_y, width=QR_SIZE, height=QR_SIZE)
        # 2. code
        c.setFont("Helvetica-Bold", 10)
        # 5mm under qr
        text_y = current_row_y - 5 * mm
        c.drawCentredString(x_pos + QR_SIZE/2, text_y, str(code))

        current_col += 1
        count += 1

        if current_col >= COLS_PER_ROW:
            current_col = 0
            current_row_y -= ROW_HEIGHT
            
            if current_row_y < 20 * mm:
                c.showPage()
                current_row_y = page_height - MARGIN_Y_TOP - QR_SIZE

    c.save()
    print(f"Created QR codes for {count} presents.")
    print(f"PDF generated: {OUTPUT_PDF}")

    # Saving to presents.json to update qr_printed status
    if data_modified:
        save_presents(data)

if __name__ == "__main__":
    
    # Print all
    #generate_presents_pdf()
    
    # Print specific
    #target_presents = ['test01', 'test02', 'test03'] 
    #generate_presents_pdf(target_presents)
    generate_presents_pdf()

