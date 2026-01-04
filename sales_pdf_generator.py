from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib import colors

# --- Define Brand Colors ---
THEME_COLOR = colors.HexColor("#2cc985")  # Fresh Green for Sales
LIGHT_BG = colors.HexColor("#e8f8f0")     # Light Green for rows
TEXT_DARK = colors.HexColor("#2c3e50")    # Dark Slate Grey

def generate_sales_pdf(bill_data):
    if not bill_data: return False
    
    h = bill_data['header']
    items = bill_data['items']
    
    file_name = f"SALE-{h['bill_no']}-{h['party_name']}.pdf".upper()
    
    # 1. COMPACT MARGINS
    doc = SimpleDocTemplate(file_name, pagesize=A4, 
                            topMargin=0.2*inch, bottomMargin=0.2*inch,
                            leftMargin=0.4*inch, rightMargin=0.4*inch)
    
    styles = getSampleStyleSheet()
    style_center = ParagraphStyle(name='Center', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10, leading=12)
    style_title = ParagraphStyle(name='TitleCustom', parent=styles['Normal'], alignment=TA_CENTER, fontName='Helvetica-Bold', fontSize=14, leading=16)
    style_normal = ParagraphStyle(name='NormalCustom', parent=styles['Normal'], fontSize=9, leading=11)
    style_right = ParagraphStyle(name='Right', parent=styles['Normal'], alignment=TA_RIGHT, fontSize=9, leading=11)
    
    elements = []

    # --- 2. TITLE SECTION ---
    elements.append(Paragraph(f"<b><font color='{THEME_COLOR.hexval()}'>|| SHRI ||</font></b>", style_center))
    elements.append(Paragraph(f"<b><font size=14 color='{THEME_COLOR.hexval()}'>MAHESHWARI RICE MILL - SALES INVOICE</font></b>", style_title))
    elements.append(Spacer(1, 0.1*inch))
    
    # --- 3. HEADER INFO (Added Missing Details) ---
    address = str(h.get('address') or 'N/A').upper()
    gst = str(h.get('gst_no') or 'N/A').upper()
    mobile = str(h.get('mobile_no') or 'N/A').upper()
    lorry = str(h.get('lorry_no') or 'N/A').upper()

    party_txt = f"""
    <font color='#2cc985'><b>BUYER DETAILS:</b></font><br/>
    <b>NAME:</b> {h['party_name'].upper()}<br/>
    <b>ADDRESS:</b> {address}<br/>
    <b>GST NO:</b> {gst}<br/>
    <b>MOBILE:</b> {mobile}
    """
    
    bill_txt = f"""
    <font color='#2cc985'><b>INVOICE DETAILS:</b></font><br/>
    <b>SALE BILL NO:</b> {h['bill_no']}<br/>
    <b>DATE:</b> {h['bill_date']}<br/>
    <b>LORRY NO:</b> {lorry}
    """
    
    header_data = [[Paragraph(party_txt, style_normal), Paragraph(bill_txt, style_right)]]
    header_table = Table(header_data, colWidths=[4.5*inch, 3.0*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # --- 4. ITEMS TABLE ---
    items_header = ['ITEM VARIETY', 'BAGS', 'RATE', 'WEIGHT (QTL)', 'AMOUNT']
    table_data = [items_header]

    total_bags = 0
    final_wt = h.get('final_weight_kg', 0.0) # This is stored as QTL in DB, so display directly

    for item in items:
        # DB stores weight as QTL, so we display it directly
        row = [
            item['paddy_type'].upper(),
            str(item['bags']),
            f"{item['rate']:,.2f}",
            f"{item['weight_kg']:,.2f}", 
            f"{item['amount']:,.0f}"
        ]
        table_data.append(row)
        total_bags += item['bags']
    
    # Total Row
    total_row = ['TOTAL', str(total_bags), '', f"{final_wt:.2f}", '']
    table_data.append(total_row)
        
    t = Table(table_data, colWidths=[2.2*inch, 0.8*inch, 1.2*inch, 1.3*inch, 1.5*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), THEME_COLOR),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('FONTSIZE', (0,1), (-1,-1), 9),
        ('ALIGN', (0,1), (0,-1), 'LEFT'),
        ('ALIGN', (3,1), (-1,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, LIGHT_BG]),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
        ('LINEABOVE', (0,-1), (-1,-1), 1, colors.black),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.2*inch))

    # --- 5. FINANCIAL TOTALS ---
    gross = float(h.get('total_gross_amount') or 0)
    disc_percent = float(h.get('discount_percent') or 0)
    disc_val = (gross * disc_percent) / 100
    
    totals_data = [
        ['GROSS AMOUNT:', f"{gross:,.0f}"],
        [f"DISCOUNT ({disc_percent}%):", f"- {disc_val:,.0f}"],
        ['BROKERAGE:', f"{float(h.get('brokerage') or 0):,.0f}"],
        ['HAMALI:', f"{float(h.get('hamali') or 0):,.0f}"],
        [f"OTHERS ({str(h.get('others_desc') or '').upper()}):", f"{float(h.get('others_amount') or 0):,.0f}"],
        ['', ''],
        ['NET RECEIVABLE:', f"Rs. {float(h.get('net_payable') or 0):,.0f}"]
    ]
    
    totals_inner_table = Table(totals_data, colWidths=[1.5*inch, 1.2*inch])
    totals_inner_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,-1), (-1,-1), 9),
        ('FONTSIZE', (-1,-1), (-1,-1), 12),
        ('TEXTCOLOR', (-1,-1), (-1,-1), THEME_COLOR),
        ('LINEABOVE', (0,-1), (-1,-1), 1, colors.black),
        ('TOPPADDING', (0,-1), (1,-1), 4), 
        ('BOTTOMPADDING', (0,-1), (1,-1), 4),
    ]))

    master_row = [['', totals_inner_table]]
    master_table = Table(master_row, colWidths=[4*inch, 3.5*inch])
    master_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    
    elements.append(master_table)
    
    try:
        doc.build(elements)
        print(f"Sales PDF Generated: {file_name}")
        return True
    except Exception as e:
        print(f"PDF Error: {e}")
        return False