from flask import Flask, request, render_template, redirect, url_for
from flask_socketio import SocketIO, emit
import fitz
import io
from PIL import Image
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
socketio = SocketIO(app)

def calculate_ink_usage(img):
    """
    Calculate the percentage of black and color ink used on the given image.
    """
    img = img.convert("RGB")
    width, height = img.size
    total_pixels = width * height
    black_pixels = 0
    color_pixels = 0

    for x in range(width):
        for y in range(height):
            r, g, b = img.getpixel((x, y))
            if r == g == b:
                if r != 255:  # Ignore white pixels
                    black_pixels += 1
            else:
                color_pixels += 1

    black_ink_usage = (black_pixels / total_pixels) * 100
    color_ink_usage = (color_pixels / total_pixels) * 100
    return black_ink_usage, color_ink_usage

def calculate_price(black_ink, color_ink):
    """
    Calculate the printing price based on ink usage.
    """
    if black_ink > 0:
        if black_ink < 75:
            black_price = 3
        elif black_ink < 50:
            black_price = 2
        else:
            black_price = 1
    else:
        black_price = 0

    if color_ink > 0:
        if color_ink < 75:
            color_price = 25
        elif color_ink < 50:
            color_price = 4
        else:
            color_price = 3
    else:
        color_price = 0

    return black_price + color_price

def analyze_pdf(pdf_path):
    """
    Analyze each page in the PDF to check if it is grayscale or contains color.
    Calculate the ink usage and determine the printing price for each page.
    """
    doc = fitz.open(pdf_path)
    results = {}
    total_pages = len(doc)

    for page_num in range(total_pages):
        page = doc.load_page(page_num)
        pix = page.get_pixmap()
        img = Image.open(io.BytesIO(pix.tobytes()))

        black_ink, color_ink = calculate_ink_usage(img)
        price = calculate_price(black_ink, color_ink)

        results[page_num + 1] = {
            "black_ink": black_ink,
            "color_ink": color_ink,
            "price": price
        }

        # Emit progress update
        socketio.emit('progress', {'progress': int(((page_num + 1) / total_pages) * 100)})

    return results

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            analysis_results = analyze_pdf(file_path)
            os.remove(file_path)
            return render_template('result.html', results=analysis_results)
    return render_template('upload.html')

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    socketio.run(app, debug=True)
