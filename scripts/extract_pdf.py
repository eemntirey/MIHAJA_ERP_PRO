# -*- coding: utf-8 -*-
import sys
from pypdf import PdfReader

reader = PdfReader(r"c:\Users\eemntirey\Downloads\Boky Andrea.pdf")

with open(r"c:\Users\eemntirey\Desktop\ERP_MM\MIHAJA_ERP_PRO\scripts\pdf_content.txt", "w", encoding="utf-8") as f:
    f.write(f"TOTAL PAGES: {len(reader.pages)}\n")
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        f.write(f"\n===== PAGE {i+1} =====\n")
        f.write(text)
        f.write("\n")
print("OK")
