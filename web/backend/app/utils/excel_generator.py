from openpyxl import Workbook


def generate_excel_report(filename, rows):
    wb = Workbook()
    ws = wb.active
    for row_index, row in enumerate(rows, start=1):
        for col_index, value in enumerate(row, start=1):
            ws.cell(row=row_index, column=col_index, value=value)
    wb.save(filename)
