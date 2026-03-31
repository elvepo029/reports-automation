from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
import io
import os


def html_to_pdf(html_string, base_url=None):
    """
    Convert HTML string to PDF using WeasyPrint.
    base_url: directory path or file URL for resolving relative links (e.g. images).
    Returns: BytesIO containing the PDF.
    """
    from weasyprint import HTML, CSS

    if base_url is None:
        base_url = os.path.dirname(os.path.abspath(__file__))
    if not base_url.startswith(("http://", "https://", "file://")):
        base_url = "file://" + os.path.abspath(base_url).replace(os.sep, "/")
    if not base_url.endswith("/"):
        base_url += "/"

    html = HTML(string=html_string, base_url=base_url)
    pdf_bytes = html.write_pdf()
    buffer = io.BytesIO(pdf_bytes)
    buffer.seek(0)
    return buffer

def generate_pdf_from_json(data, template_path):
    """
    data: dict amb les dades del report
    template_path: path a la plantilla PNG
    retorna: BytesIO amb el PDF generat
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Fons (plantilla)
    c.drawImage(
        template_path,
        0, 0,
        width=width,
        height=height
    )

    DEFAULT_FONT = "Helvetica"
    DEFAULT_SIZE = 11
    DEFAULT_COLOR = colors.black
    DEFAULT_ALIGN = "center"

    # Mapa JSON -> coordenades
    fields = {
        "game": {
            "pos": (300, 765),
            "color": colors.white,
            "font": "Helvetica-Bold",
            "size": 12,
            "align": "center"
        },
        "date": (300, 744),
        "team_h": {
            "pos": (169, 705),
            "color": colors.white,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "team_a": {
            "pos": (425, 705),
            "color": colors.white,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "live_game_manager": {
            "pos": (480, 630),
            "color": colors.black,
            "font": "Helvetica",
            "size": 8,
            "align": "center"
        },
        "arrival_time": {
            "pos": (95, 552),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "checklist_on_time": {
            "pos": (195, 552),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "communication": {
            "pos": (295, 552),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "corrections_speed": {
            "pos": (395, 552),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "rescouted": {
            "pos": (495, 552),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "total_actions": {
            "pos": (125, 474),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "total_corrections": {
            "pos": (295, 474),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "%_corrections": {
            "pos": (465, 474),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "home_team": {
            "pos": (125, 416),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "away_team": {
            "pos": (295, 416),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "no_team": {
            "pos": (465, 416),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "quarter_1": {
            "pos": (95, 373),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "quarter_2": {
            "pos": (195, 373),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "quarter_3": {
            "pos": (295, 373),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "quarter_4": {
            "pos": (395, 373),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "et": {
            "pos": (495, 373),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "boxscore_corrections": {
            "pos": (169, 316),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "scoresheet_corrections": {
            "pos": (425, 316),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "result": {
            "pos": (90, 33),
            "color": colors.black,
            "font": "Helvetica-Bold",
            "size": 15,
            "align": "center"
        },
        "criteria_corrections": {
            "pos": (87, 275),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "misidentity_corrections": {
            "pos": (169, 275),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "missing_corrections": {
            "pos": (251, 275),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "not_happened_corrections": {
            "pos": (87, 232),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "misplaced_corrections": {
            "pos": (169, 232),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "timing_corrections": {
            "pos": (251, 232),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "jump_ball_corrections": {
            "pos": (336, 275),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "substitution_corrections": {
            "pos": (422, 275),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "irs_cc_corrections": {
            "pos": (508, 275),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "time_out_corrections": {
            "pos": (336, 232),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "fouls_corrections": {
            "pos": (422, 232),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
        "points_corrections": {
            "pos": (508, 232),
            "color": colors.black,
            "font": "Helvetica",
            "size": 11,
            "align": "center"
        },
    }

    draw_name_multiline(
        c,
        text=data["data_entry"],
        x=90,
        y=647,
        box_height=30,
        font="Helvetica",
        size=8
    )

    draw_name_multiline(
        c,
        text=data["caller_1"],
        x=172,
        y=647,
        box_height=30,
        font="Helvetica",
        size=8
    )

    draw_name_multiline(
        c,
        text=data["caller_2"],
        x=254,
        y=647,
        box_height=30,
        font="Helvetica",
        size=8
    )

    draw_name_multiline(
        c,
        text=data["timer"],
        x=338,
        y=647,
        box_height=30,
        font="Helvetica",
        size=8
    )

    draw_name_multiline(
        c,
        text=data["shot_clock"],
        x=422,
        y=647,
        box_height=30,
        font="Helvetica",
        size=8
    )

    draw_name_multiline(
        c,
        text=data["irs_operator"],
        x=506,
        y=647,
        box_height=30,
        font="Helvetica",
        size=8
    )

    draw_comments_justified(
        c,
        text=data["comments"],
        x=55,         
        y=135,
        box_width=480, 
        box_height=50, 
        font="Helvetica",
        size=8
    )


    # Escriure valors
    for key, cfg in fields.items():
        value = data.get(key, "")

        if value == "":
            continue

        # CAS SIMPLE → només coordenades
        if isinstance(cfg, tuple):
            x, y = cfg
            font = DEFAULT_FONT
            size = DEFAULT_SIZE
            color = DEFAULT_COLOR
            align = DEFAULT_ALIGN

        # CAS AVANÇAT → dict
        else:
            x, y = cfg["pos"]
            font = cfg.get("font", DEFAULT_FONT)
            size = cfg.get("size", DEFAULT_SIZE)
            color = cfg.get("color", DEFAULT_COLOR)
            align = cfg.get("align", DEFAULT_ALIGN)

        c.setFont(font, size)
        c.setFillColor(color)

        if align == "left":
            c.drawString(x, y, str(value))
        elif align == "center":
            c.drawCentredString(x, y, str(value))
        else:
            c.drawRightString(x, y, str(value))

    # Tancar PDF
    c.showPage()
    c.save()
    buffer.seek(0)

    return buffer

def draw_name_multiline(
    c,
    text,
    x,
    y,
    box_height,
    font="Helvetica",
    size=8,
    color=colors.black,
    max_lines=3,
    leading=None
):
    lines = split_name_keep_dash(text)
    if not lines:
        return

    lines = lines[:max_lines]

    if leading is None:
        leading = size + 2

    c.setFont(font, size)
    c.setFillColor(color)

    total_text_height = leading * len(lines)
    start_y = y + (box_height + total_text_height) / 2 - leading

    for i, line in enumerate(lines):
        c.drawCentredString(x, start_y - i * leading, line)

def split_name_keep_dash(text):
    """
    Separa per espais o guions,
    però conserva el guió al final de la paraula
    """
    if not text:
        return []

    # Espais → separació normal
    words = text.strip().split(" ")

    exceptions = {"DE", "LA", "BEN"}

    parts = []
    i = 0

    while i < len(words):
        if i + 1 < len(words) and words[i+1] in exceptions:
            parts.append(words[i] + " " + words[i+1])
            i += 2
        else:
            parts.append(words[i])
            i += 1

    result = []

    for part in parts:
        if "-" in part:
            subparts = part.split("-")
            for j, sp in enumerate(subparts):
                if j < len(subparts) - 1:
                    result.append(sp + "-")  # 👈 conserva guió
                else:
                    result.append(sp)
        else:
            result.append(part)

    return [r for r in result if r]

def draw_comments_justified(
    c,
    text,
    x,
    y,
    box_width,
    box_height,
    font="Helvetica",
    size=8,
    color=colors.black,
    leading=None
):
    if not text:
        return

    if leading is None:
        leading = size + 2

    style = ParagraphStyle(
        name="CommentsStyle",
        fontName=font,
        fontSize=size,
        leading=leading,
        textColor=color,
        alignment=TA_JUSTIFY,
    )

    p = Paragraph(text, style)

    # Mesura el text
    w, h = p.wrap(box_width, box_height)

    # IMPORTANT: Paragraph creix cap amunt,
    # així que el dibuixem des de baix del requadre
    draw_y = y + box_height - h

    p.drawOn(c, x, draw_y)