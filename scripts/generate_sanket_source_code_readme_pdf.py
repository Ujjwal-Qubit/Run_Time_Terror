"""
SANKET v1.0 — Source Code README PDF Generator.
Conforms to SIH 2026 Problem Statement 26169 (Department of Space / ISRO).
Generates an executive, formal Source Code Reproduction Guide PDF using ReportLab Platypus
with NumberedCanvas for 'Page X of Y' headers and footers.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable, Image, Preformatted
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(colors.HexColor("#4A5568"))

        header_text_left = "SANKET v1.0 — SOURCE CODE DISTRIBUTION & REPRODUCTION GUIDE"
        header_text_right = "SIH 2026 PS 26169 | ISRO / Department of Space"
        self.drawString(40, 11 * inch - 30, header_text_left)
        self.drawRightString(8.5 * inch - 40, 11 * inch - 30, header_text_right)

        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(40, 11 * inch - 34, 8.5 * inch - 40, 11 * inch - 34)

        footer_text_left = "DELIVERABLE 02 — SOURCE CODE REPRODUCTION INSTRUCTIONS"
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawString(40, 26, footer_text_left)
        self.drawRightString(8.5 * inch - 40, 26, page_str)

        self.line(40, 36, 8.5 * inch - 40, 36)
        self.restoreState()


def build_source_readme_pdf(filename: str):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=46,
        bottomMargin=46,
    )

    styles = getSampleStyleSheet()

    c_primary = colors.HexColor("#1A365D")     # Deep Navy
    c_secondary = colors.HexColor("#C53030")   # Crimson Accent
    c_accent = colors.HexColor("#2B6CB0")      # Slate Blue
    c_dark = colors.HexColor("#2D3748")        # Charcoal Body
    c_bg_light = colors.HexColor("#F7FAFC")    # Table alt row
    c_bg_head = colors.HexColor("#EDF2F7")     # Table header
    c_border = colors.HexColor("#CBD5E0")

    title_style = ParagraphStyle(
        'CoverTitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=18, leading=22,
        textColor=c_primary, spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'CoverSubtitle', parent=styles['Normal'],
        fontName='Helvetica', fontSize=10, leading=14,
        textColor=colors.HexColor("#4A5568"), spaceAfter=12
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=11, leading=15,
        textColor=c_primary, spaceBefore=9, spaceAfter=4, keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8, leading=11.5,
        textColor=c_dark, spaceAfter=4
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom', parent=body_style,
        leftIndent=12, firstLineIndent=-8, spaceAfter=2.5
    )

    table_cell = ParagraphStyle(
        'TableCell', parent=styles['Normal'],
        fontName='Helvetica', fontSize=7.5, leading=9.5,
        textColor=c_dark
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=7.5, leading=9.5,
        textColor=c_primary
    )

    code_pre = ParagraphStyle(
        'CodePre', parent=styles['Normal'],
        fontName='Courier', fontSize=7, leading=8.5,
        textColor=colors.HexColor("#1A202C")
    )

    story = []

    story.append(Paragraph("SANKET v1.0 — Source Code Reproduction Guide", title_style))
    story.append(Paragraph("Complete Technical Instructions for Building, Testing, and Packaging SANKET from Source", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=c_primary, spaceAfter=8, spaceBefore=0))

    meta_table_data = [
        [Paragraph("<b>System Name:</b>", table_cell_bold), Paragraph("SANKET (AI-Assisted FSOC Workstation)", table_cell), Paragraph("<b>Target Organization:</b>", table_cell_bold), Paragraph("Department of Space / ISRO", table_cell)],
        [Paragraph("<b>Problem Statement:</b>", table_cell_bold), Paragraph("SIH 2026 PS 26169 (PS-4)", table_cell), Paragraph("<b>Clean Archive:</b>", table_cell_bold), Paragraph("<code>SANKET_Source.zip</code> (30.36 MB, 281 files)", table_cell)],
        [Paragraph("<b>Backend Stack:</b>", table_cell_bold), Paragraph("Python 3.11.9, OpenCV 4.10, PySide6", table_cell), Paragraph("<b>Frontend Stack:</b>", table_cell_bold), Paragraph("React 19, TypeScript, Three.js, Vite", table_cell)],
    ]
    t_meta = Table(meta_table_data, colWidths=[1.5*inch, 2.2*inch, 1.5*inch, 2.0*inch])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_bg_light),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 6))

    story.append(Paragraph("1. System Architecture & Module Organization", h1_style))
    tree_text = """SANKET/
|-- src/
|   |-- aiml/           # Calibrated Logistic Regression classifier & feature extraction
|   |-- app/            # AppController & QtWebEngine host window
|   |-- control/        # PTZ dual-axis PID controller with rate limiting (<= 10 deg/s)
|   |-- evaluation/     # BenchmarkManager (19-scenario matrix & MP4 video evaluator)
|   |-- frame/          # SimulationFrameProvider and MP4FrameProvider
|   |-- metrics/        # Real-time MetricsEngine and LoggingEngine
|   |-- simulation/     # 2000x2000 World Canvas, FPA Camera Model, DisturbanceEngine
|   |-- tests/          # 599 automated unit, integration, and contract tests
|   `-- tracker/        # DetectionEngine, Sub-pixel CoG Centroid, Kalman State Machine
|-- frontend/           # Embedded React 19 / TypeScript / Tailwind / Three.js UI
|-- scenarios/          # 19 standardized ISRO PS-26169 scenario JSON definitions
|-- scripts/            # Screenshot capture, PDF compilers, and packaging scripts
`-- sanket.spec         # PyInstaller standalone executable specification"""
    story.append(Preformatted(tree_text, code_pre))
    story.append(Spacer(1, 6))

    story.append(Paragraph("2. Reproduction & Build Commands", h1_style))
    story.append(Paragraph("<b>Step 1: Environment Setup & Python Dependencies</b>", body_style))
    step1_cmd = """python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt"""
    story.append(Preformatted(step1_cmd, code_pre))
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>Step 2: Frontend Bundle Compilation</b>", body_style))
    step2_cmd = """cd frontend
npm install
npm run build
cd .."""
    story.append(Preformatted(step2_cmd, code_pre))
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>Step 3: Verification via Automated Test Suite (599 Tests)</b>", body_style))
    step3_cmd = "pytest"
    story.append(Preformatted(step3_cmd, code_pre))
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>Step 4: Launching SANKET</b>", body_style))
    step4_cmd = """# Graphical Interactive Workstation:
python -m src.main

# Headless Batch Execution:
python -m src.main --headless --scenario scenario_2_circular --duration 30"""
    story.append(Preformatted(step4_cmd, code_pre))
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>Step 5: Standalone Binary Compilation (PyInstaller)</b>", body_style))
    step5_cmd = "pyinstaller sanket.spec --noconfirm --clean"
    story.append(Preformatted(step5_cmd, code_pre))

    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E0"), spaceAfter=8, spaceBefore=0))
    story.append(Paragraph("<b>End of Source Code Reproduction Guide — SANKET v1.0 Production Release</b>", ParagraphStyle('SignOff', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor("#718096"), alignment=1)))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Source Code README PDF successfully generated: '{filename}'")


if __name__ == "__main__":
    import shutil
    project_root = Path(__file__).resolve().parents[1]
    deliv_pdf = project_root / "deliverables" / "02_Source_Code" / "SOURCE_CODE_README.pdf"
    deliv_pdf.parent.mkdir(parents=True, exist_ok=True)
    build_source_readme_pdf(str(deliv_pdf))
    print(f"Generated deliverable Source Code README PDF: {deliv_pdf} ({deliv_pdf.stat().st_size:,} bytes)")
    
    docs_pdf = project_root / "docs" / "SANKET_v1.0_Source_Code_README.pdf"
    docs_pdf.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(deliv_pdf, docs_pdf)
    print(f"Mirrored docs Source Code README PDF: {docs_pdf}")
