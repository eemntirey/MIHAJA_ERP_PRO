import qrcode
import base64
from io import BytesIO


def generate_qr_code(data, filename=None):
    img = qrcode.make(data)
    if filename:
        img.save(filename)
        return filename
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()


def generate_qr_code_base64(data):
    """Generate QR code and return base64 encoded PNG"""
    img = qrcode.make(data)
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"
