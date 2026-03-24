import io
import pandas as pd
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

def df_to_excel(df: pd.DataFrame, sheet_name="Datos") -> bytes:
    """Convierte DataFrame a bytes de Excel."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        ws = writer.sheets[sheet_name]
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)
    return output.getvalue()

def df_to_pdf(df: pd.DataFrame, title="Reporte", subtitle="") -> bytes:
    """Convierte DataFrame a bytes de PDF con formato profesional."""
    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=1*cm, leftMargin=1*cm,
        topMargin=2*cm, bottomMargin=1*cm
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Title"], fontSize=16, textColor=colors.HexColor("#D4A017"), alignment=TA_CENTER)
    sub_style = ParagraphStyle("sub", parent=styles["Normal"], fontSize=10, textColor=colors.grey, alignment=TA_CENTER)

    elements = []
    elements.append(Paragraph("SISTEMA MINERO", title_style))
    elements.append(Paragraph(title, title_style))
    if subtitle:
        elements.append(Paragraph(subtitle, sub_style))
    elements.append(Spacer(1, 0.5*cm))

    # Tabla
    data = [list(df.columns)]
    for _, row in df.iterrows():
        data.append([str(v) if v is not None else "" for v in row])

    col_count = len(df.columns)
    available_width = landscape(A4)[0] - 2*cm
    col_width = available_width / col_count

    table = Table(data, colWidths=[col_width]*col_count, repeatRows=1)
    base_style = [
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#D4A017")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 9),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONTSIZE", (0,1), (-1,-1), 8),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F5F5F5")]),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("ROWHEIGHT", (0,0), (-1,-1), 18),
    ]

    # Colores por estado específico
    for row_num, (orig_idx, row) in enumerate(df.iterrows()):
        row_vals = {str(k).lower(): str(v).lower() for k, v in row.items()}
        
        # Primero evaluamos celdas individuales para colorearlas
        for col_idx, (k, v) in enumerate(row.items()):
            val_lower = str(v).lower().strip()
            
            if val_lower in ["presente", "sí", "si"]:
                base_style.append(("TEXTCOLOR", (col_idx, row_num + 1), (col_idx, row_num + 1), colors.HexColor("#059669"))) # Verde
                base_style.append(("FONTNAME", (col_idx, row_num + 1), (col_idx, row_num + 1), "Helvetica-Bold"))
            elif val_lower in ["falta", "no", "ausente", "no_laborable", "no laborable"]:
                base_style.append(("TEXTCOLOR", (col_idx, row_num + 1), (col_idx, row_num + 1), colors.HexColor("#DC2626"))) # Rojo
                base_style.append(("FONTNAME", (col_idx, row_num + 1), (col_idx, row_num + 1), "Helvetica-Bold"))
            elif val_lower in ["permiso"]:
                base_style.append(("TEXTCOLOR", (col_idx, row_num + 1), (col_idx, row_num + 1), colors.HexColor("#D97706"))) # Naranja
                base_style.append(("FONTNAME", (col_idx, row_num + 1), (col_idx, row_num + 1), "Helvetica-Bold"))
            elif val_lower in ["pendiente"]:
                base_style.append(("TEXTCOLOR", (col_idx, row_num + 1), (col_idx, row_num + 1), colors.HexColor("#6B7280"))) # Gris

        # Evaluar la fila completa si es un domingo estructurado como fila inactiva
        es_no_laborable = False
        tipo_dia = row_vals.get("tipo dia", "")
        fecha_txt = row_vals.get("fecha", "")

        if "no laborable" in tipo_dia:
            es_no_laborable = True
        elif "domingo" in fecha_txt and "presente" not in row_vals.values():
            es_no_laborable = True

        if es_no_laborable:
            base_style.append(("TEXTCOLOR", (0, row_num + 1), (-1, row_num + 1), colors.HexColor("#DC2626")))
            base_style.append(("FONTNAME", (0, row_num + 1), (-1, row_num + 1), "Helvetica-Bold"))

    table.setStyle(TableStyle(base_style))
    elements.append(table)
    doc.build(elements)
    return output.getvalue()


def sections_to_pdf(sections: list, title="Reporte", subtitle="") -> bytes:
    """Convierte una lista de secciones a un PDF con tablas separadas.

    sections: [(nombre_seccion, dataframe), ...]
    """
    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=1 * cm,
        leftMargin=1 * cm,
        topMargin=2 * cm,
        bottomMargin=1 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title",
        parent=styles["Title"],
        fontSize=16,
        textColor=colors.HexColor("#D4A017"),
        alignment=TA_CENTER,
    )
    sub_style = ParagraphStyle(
        "sub",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.grey,
        alignment=TA_CENTER,
    )
    section_style = ParagraphStyle(
        "section",
        parent=styles["Heading3"],
        fontSize=11,
        textColor=colors.HexColor("#1A1D27"),
        alignment=TA_LEFT,
    )

    elements = [Paragraph("SISTEMA MINERO", title_style), Paragraph(title, title_style)]
    if subtitle:
        elements.append(Paragraph(subtitle, sub_style))
    elements.append(Spacer(1, 0.5 * cm))

    available_width = landscape(A4)[0] - 2 * cm

    for section_name, df in sections:
        if df is None or df.empty:
            df = pd.DataFrame({"Info": ["Sin datos"]})

        elements.append(Paragraph(str(section_name), section_style))
        elements.append(Spacer(1, 0.2 * cm))

        data = [list(df.columns)]
        for _, row in df.iterrows():
            data.append([str(v) if v is not None else "" for v in row])

        col_count = len(df.columns) if len(df.columns) > 0 else 1
        col_width = available_width / col_count
        table = Table(data, colWidths=[col_width] * col_count, repeatRows=1)
        
        base_style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D4A017")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWHEIGHT", (0, 0), (-1, -1), 18),
        ]

        # Aplicar colores por estado (SÍ, NO, PRESENTE, FALTA, etc.)
        for row_num, (orig_idx, row) in enumerate(df.iterrows()):
            # Evaluamos celdas individuales para colorearlas
            for col_idx, (k, v) in enumerate(row.items()):
                val_lower = str(v).lower().strip()
                if val_lower in ["presente", "sí", "si"]:
                    base_style.append(("TEXTCOLOR", (col_idx, row_num + 1), (col_idx, row_num + 1), colors.HexColor("#059669"))) # Verde
                    base_style.append(("FONTNAME", (col_idx, row_num + 1), (col_idx, row_num + 1), "Helvetica-Bold"))
                elif val_lower in ["falta", "no", "ausente", "no_laborable", "no laborable"]:
                    base_style.append(("TEXTCOLOR", (col_idx, row_num + 1), (col_idx, row_num + 1), colors.HexColor("#DC2626"))) # Rojo
                    base_style.append(("FONTNAME", (col_idx, row_num + 1), (col_idx, row_num + 1), "Helvetica-Bold"))
                elif val_lower in ["permiso"]:
                    base_style.append(("TEXTCOLOR", (col_idx, row_num + 1), (col_idx, row_num + 1), colors.HexColor("#D97706"))) # Naranja
                    base_style.append(("FONTNAME", (col_idx, row_num + 1), (col_idx, row_num + 1), "Helvetica-Bold"))
                elif val_lower in ["pendiente"]:
                    base_style.append(("TEXTCOLOR", (col_idx, row_num + 1), (col_idx, row_num + 1), colors.HexColor("#6B7280"))) # Gris

        table.setStyle(TableStyle(base_style))
        elements.append(table)
        elements.append(Spacer(1, 0.35 * cm))

    doc.build(elements)
    return output.getvalue()

def multiple_sheets_excel(sheets: dict) -> bytes:
    """Crea Excel con múltiples hojas. sheets = {nombre: DataFrame}"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
    return output.getvalue()
