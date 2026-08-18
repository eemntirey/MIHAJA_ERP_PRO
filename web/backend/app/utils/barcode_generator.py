import barcode
from barcode.writer import ImageWriter


def generate_barcode(data, filename):
    code_class = barcode.get('code128', data, writer=ImageWriter())
    code_class.save(filename)
    return filename
