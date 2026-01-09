from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib import colors

# --- Define Brand Colors ---
THEME_COLOR = colors.HexColor("#1f6aa5")  # Professional Blue
LIGHT_BG = colors.HexColor("#f0f8ff")     # Light Alice Blue for rows
TEXT_DARK = colors.HexColor("#2c3e50")    # Dark Slate Grey for text

def generate_bill_pdf(bill_data):
    if not bill_data: return False
    
    h = bill_data['header']
    items = bill_data['items']
    
    file_name = f"BILL-{h['bill_no']}-{h['party_name']}.pdf".upper()
    
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
    elements.append(Paragraph(f"<b><font size=14 color='{THEME_COLOR.hexval()}'>KESAR INDUSTRIES - PURCHASE BILL</font></b>", style_title))
    elements.append(Spacer(1, 0.1*inch))
    
    # --- 3. HEADER INFO ---
    address = str(h.get('address') or 'N/A').upper()
    gst = str(h.get('gst_no') or 'N/A').upper()
    mobile = str(h.get('mobile_no') or 'N/A').upper()
    lorry = str(h.get('lorry_no') or 'N/A').upper()

    party_txt = f"""
    <font color='#1f6aa5'><b>PARTY DETAILS:</b></font><br/>
    <b>NAME:</b> {h['party_name'].upper()}<br/>
    <b>ADDRESS:</b> {address}<br/>
    <b>GST NO:</b> {gst}<br/>
    <b>MOBILE:</b> {mobile}
    """
    
    bill_txt = f"""
    <font color='#1f6aa5'><b>INVOICE DETAILS:</b></font><br/>
    <b>BILL NO:</b> {h['bill_no']}<br/>
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
    elements.append(Spacer(1, 0.15*inch))
    
    # --- 4. WEIGHTS SECTION ---
    w1 = float(h.get('truck_weight1_kg') or 0.0)
    w2 = float(h.get('truck_weight2_kg') or 0.0)
    w3 = float(h.get('truck_weight3_kg') or 0.0)
    final_w = float(h.get('final_truck_weight_kg') or 0.0)

    def fmt_wt(label, val):
        is_selected = (abs(val - final_w) < 0.01) and (val > 0)
        val_str = f"{val:.2f} QTL"
        text = f"{label}<br/>{val_str}"
        if is_selected:
            return Paragraph(f"<b><font size=10 color='black'>{text}</font></b>", style_center)
        else:
            color = "gray" if val == 0 else "black"
            return Paragraph(f"<font color='{color}'>{text}</font>", style_center)

    weight_row = [fmt_wt("WEIGHT 1", w1), "", fmt_wt("WEIGHT 2", w2), "", fmt_wt("WEIGHT 3", w3)]
    
    w_table = Table([weight_row], colWidths=[2.2*inch, 0.2*inch, 2.2*inch, 0.2*inch, 2.2*inch])
    w_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOX', (0,0), (0,0), 1, colors.lightgrey),
        ('BOX', (2,0), (2,0), 1, colors.lightgrey),
        ('BOX', (4,0), (4,0), 1, colors.lightgrey),
        ('BACKGROUND', (0,0), (0,0), LIGHT_BG),
        ('BACKGROUND', (2,0), (2,0), LIGHT_BG),
        ('BACKGROUND', (4,0), (4,0), LIGHT_BG),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(w_table)
    
    elements.append(Spacer(1, 0.05*inch))
    final_txt = f"FINAL BILLING WEIGHT: {final_w:.2f} QTL"
    elements.append(Paragraph(f"<b><font size=11 color='{THEME_COLOR.hexval()}'>{final_txt}</font></b>", style_center))
    elements.append(Spacer(1, 0.1*inch))

    # --- 5. ITEMS TABLE (Rounded Item Amount) ---
    items_header = ['ITEM', 'BAGS', 'MOIST', 'RATE', 'FINAL RT', 'WT(QTL)', 'AMOUNT']
    table_data = [items_header]

    for item in items:
        row = [
            item['paddy_type'].upper(),
            str(item['bags']),
            f"{item['moisture']:.1f}%",
            f"{item['base_rate']:,.2f}",
            f"{item['calculated_rate']:,.2f}",
            f"{item['calculated_weight_kg']:.2f}",
            f"{item['item_amount']:,.0f}"  # <--- CHANGED TO .0f (No Decimals)
        ]
        table_data.append(row)
    
    # Total Row
    total_bags = str(h.get('total_bags') or 0)
    total_row = ['TOTAL', total_bags, '', '', '', f"{final_w:.2f}", '']
    table_data.append(total_row)
        
    t = Table(table_data, colWidths=[1.4*inch, 0.6*inch, 0.7*inch, 0.9*inch, 0.9*inch, 1.0*inch, 1.2*inch])
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
    elements.append(Spacer(1, 0.1*inch))

    # --- 6. FINANCIAL TOTALS (Rounded) ---
    gross = float(h.get('total_gross_amount') or 0)
    disc_percent = float(h.get('discount_percent') or 0)
    disc_val = (gross * disc_percent) / 100
    
    # ROUNDING ALL MONEY VALUES
    totals_data = [
        ['GROSS AMOUNT:', f"{gross:,.0f}"], # No decimals
        [f"DISCOUNT ({disc_percent}%):", f"- {disc_val:,.0f}"], # No decimals
        ['BROKERAGE:', f"{float(h.get('brokerage') or 0):,.0f}"], # No decimals
        ['HAMALI:', f"{float(h.get('hamali') or 0):,.0f}"], # No decimals
        [f"OTHERS ({str(h.get('others_desc') or '').upper()}):", f"{float(h.get('others_amount') or 0):,.0f}"],
        ['', ''],
        ['NET PAYABLE:', f"Rs. {float(h.get('net_payable') or 0):,.0f}"] # No decimals
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
        print(f"PDF Generated: {file_name}")
        return True
    except Exception as e:
        print(f"PDF Error: {e}")
        return False