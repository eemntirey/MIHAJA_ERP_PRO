import qrcode


def generate_qr_code(data, filename):
    img = qrcode.make(data)
    img.save(filename)
    return filename
