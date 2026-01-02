from fpdf import FPDF
from fpdf.fonts import FontFace
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any


class RiskAssessmentPDF(FPDF):
    def __init__(self, assessment_data: Dict[str, Any]):
        super().__init__()
        self.assessment_data = assessment_data
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()

    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 7)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

    def section_header(self, title: str):
        self.set_font('helvetica', 'B', 9)
        self.set_fill_color(192, 0, 0)  # Dark Red
        self.set_text_color(255, 255, 255)  # White
        self.cell(0, 5, title, fill=True, ln=True)
        self.set_text_color(0, 0, 0)  # Reset to black
        self.set_fill_color(255, 255, 255)  # Reset fill to white
        self.ln(1)

    def get_color_for_rating(self, rating: str):
        if not rating:
            return (255, 255, 255)  # White
        r = rating.upper()
        if "HIGH" in r or "RED" in r:
            return (255, 100, 100)  # Red
        if "MEDIUM" in r or "YELLOW" in r:
            return (255, 255, 200)  # Yellow
        if "LOW" in r or "GREEN" in r:
            return (200, 255, 200)  # Green
        return (255, 255, 255)

    def generate_report(self):
        data = self.assessment_data
        model = data.get('model', {})

        # Title
        self.set_font('helvetica', 'B', 14)
        self.set_text_color(192, 0, 0)
        self.cell(0, 8, 'Model Risk Ranking', ln=True)
        self.set_text_color(0, 0, 0)

        self.set_font('helvetica', 'I', 8)
        self.cell(
            0, 5, f"Assessment Date: {data.get('assessment_date', '')}", ln=True)
        self.ln(2)

        # Set default font for tables
        self.set_font('helvetica', '', 8)

        # Section 1: Model Information
        self.section_header("Section 1: Model Information")
        self.set_font('helvetica', '', 8)

        with self.table(col_widths=(40, 150), borders_layout="INTERNAL", line_height=5) as table:
            info_fields = [
                ("Model Name", model.get('name', '')),
                ("Model ID", str(model.get('id', ''))),
                ("Project ID", model.get('project_id', '')),
                ("Product", model.get('product', '')),
                ("Region", data.get('region', 'Global')),
                ("Model Category", model.get('category', '')),
                ("Model Subcategory", model.get('subcategory', '')),
            ]
            for label, value in info_fields:
                row = table.row()
                row.cell(label, style=FontFace(
                    emphasis="B", fill_color=(245, 245, 245)))
                row.cell(str(value), style=FontFace(
                    fill_color=(230, 240, 255)))
        self.ln(2)

        # Section 2: Inherent Model Risk
        self.section_header("Section 2: Inherent Model Risk")
        self.set_font('helvetica', '', 8)

        with self.table(col_widths=(80, 30, 80), line_height=5) as table:
            # Header
            row = table.row()
            row.cell("Schema", style=FontFace(
                emphasis="B", fill_color=(240, 240, 240)))
            row.cell("Assessment", style=FontFace(
                emphasis="B", fill_color=(240, 240, 240)))
            row.cell("Comments", style=FontFace(
                emphasis="B", fill_color=(240, 240, 240)))

            # 2.0 Inherent Model Risk
            row = table.row()
            row.cell("2.0 Inherent Model Risk",
                     style=FontFace(emphasis="B", fill_color=(240, 240, 240)))
            rating = data.get('inherent_risk_tier', '')
            row.cell(rating, style=FontFace(
                fill_color=self.get_color_for_rating(rating), emphasis="B"))
            row.cell("")

            # 2.1 Derived
            row = table.row()
            row.cell("    2.1 Inherent Model Risk - Derived",
                     style=FontFace(emphasis="I", fill_color=(255, 255, 255)))
            rating = data.get('inherent_risk_derived', '')
            row.cell(rating, style=FontFace(
                fill_color=self.get_color_for_rating(rating)))
            row.cell(data.get('inherent_risk_derived_comment', ''),
                     style=FontFace(size_pt=7))

            # 2.1.1 Quantitative
            row = table.row()
            row.cell("        2.1.1 Quantitative Factor",
                     style=FontFace(fill_color=(255, 255, 255)))
            rating = data.get('quantitative_rating', '')
            row.cell(rating, style=FontFace(
                fill_color=self.get_color_for_rating(rating)))
            row.cell(data.get('quantitative_comment', ''),
                     style=FontFace(size_pt=7))

            # 2.1.2 Quantitative Override
            row = table.row()
            row.cell("        2.1.2 Quantitative Factor - Override",
                     style=FontFace(fill_color=(255, 255, 255)))
            rating = data.get('quantitative_override', '')
            row.cell(rating, style=FontFace(
                fill_color=self.get_color_for_rating(rating)))
            row.cell(data.get('quantitative_override_comment', ''),
                     style=FontFace(size_pt=7))

            # 2.1.3 Qualitative
            row = table.row()
            row.cell("        2.1.3 Qualitative Factor",
                     style=FontFace(fill_color=(250, 250, 250)))
            rating = data.get('qualitative_rating', '')
            row.cell(rating, style=FontFace(
                fill_color=self.get_color_for_rating(rating)))
            row.cell("")

            # Qualitative Factors
            factors = data.get('qualitative_factors', [])
            for i, factor in enumerate(factors, 1):
                row = table.row()
                row.cell(f"            2.1.3.{i} {factor.get('name', '')}", style=FontFace(
                    fill_color=(255, 255, 255)))
                rating = factor.get('rating', '')
                row.cell(rating, style=FontFace(
                    fill_color=self.get_color_for_rating(rating)))
                row.cell(factor.get('comment', ''), style=FontFace(size_pt=7))

            # 2.1.4 Qualitative Override
            row = table.row()
            row.cell("        2.1.4 Qualitative Factor - Override",
                     style=FontFace(fill_color=(255, 255, 255)))
            rating = data.get('qualitative_override', '')
            row.cell(rating, style=FontFace(
                fill_color=self.get_color_for_rating(rating)))
            row.cell(data.get('qualitative_override_comment', ''),
                     style=FontFace(size_pt=7))

            # 2.2 Inherent Override
            row = table.row()
            row.cell("    2.2 Inherent Model Risk - Override",
                     style=FontFace(fill_color=(255, 255, 255)))
            rating = data.get('inherent_risk_override', '')
            row.cell(rating, style=FontFace(
                fill_color=self.get_color_for_rating(rating)))
            row.cell(data.get('inherent_risk_override_comment', ''),
                     style=FontFace(size_pt=7))

        self.ln(2)

        # Section 3: Validation Assessment (Scorecard)
        self.section_header("Section 3: Validation Assessment (Scorecard)")
        self.set_font('helvetica', '', 8)

        with self.table(col_widths=(80, 30, 80), line_height=5) as table:
            # Header
            row = table.row()
            row.cell("Schema", style=FontFace(
                emphasis="B", fill_color=(240, 240, 240)))
            row.cell("Assessment", style=FontFace(
                emphasis="B", fill_color=(240, 240, 240)))
            row.cell("Comments", style=FontFace(
                emphasis="B", fill_color=(240, 240, 240)))

            # 3.0 Validation Assessment
            row = table.row()
            row.cell("3.0 Validation Assessment",
                     style=FontFace(emphasis="B", fill_color=(240, 240, 240)))
            rating = data.get('validation_rating', '')
            row.cell(rating, style=FontFace(
                fill_color=self.get_color_for_rating(rating), emphasis="B"))
            row.cell(data.get('validation_comment', ''),
                     style=FontFace(size_pt=7))

            # Scorecard Sections
            scorecard_sections = data.get('scorecard_sections', [])
            for i, section in enumerate(scorecard_sections, 1):
                row = table.row()
                row.cell(f"    3.{i} {section.get('name', '')}",
                         style=FontFace(fill_color=(255, 255, 255)))
                rating = section.get('rating', '')
                row.cell(rating, style=FontFace(
                    fill_color=self.get_color_for_rating(rating)))
                row.cell(section.get('comment', ''), style=FontFace(size_pt=7))

        self.ln(2)

        # Section 4: Model Risk Rating (Residual)
        self.section_header("Section 4: Model Risk Rating (Residual)")
        self.set_font('helvetica', '', 8)

        with self.table(col_widths=(80, 30, 80), line_height=5) as table:
            # Header
            row = table.row()
            row.cell("Schema", style=FontFace(
                emphasis="B", fill_color=(240, 240, 240)))
            row.cell("Assessment", style=FontFace(
                emphasis="B", fill_color=(240, 240, 240)))
            row.cell("Comments", style=FontFace(
                emphasis="B", fill_color=(240, 240, 240)))

            # 4.0 Residual Risk
            row = table.row()
            row.cell("4.0 Model Risk Ranking (Residual)",
                     style=FontFace(emphasis="B", fill_color=(240, 240, 240)))
            rating = data.get('residual_risk', '')
            row.cell(rating, style=FontFace(
                fill_color=self.get_color_for_rating(rating), emphasis="B"))
            row.cell("")

            # 4.1 Derived
            row = table.row()
            row.cell("    4.1 Derived", style=FontFace(
                fill_color=(255, 255, 255)))
            rating = data.get('residual_risk_derived', '')
            row.cell(rating, style=FontFace(
                fill_color=self.get_color_for_rating(rating)))
            row.cell(data.get('residual_risk_derived_comment', ''),
                     style=FontFace(size_pt=7))

            # 4.2 Override
            row = table.row()
            row.cell("    4.2 Override", style=FontFace(
                fill_color=(255, 255, 255)))
            rating = data.get('residual_risk_override', '')
            row.cell(rating, style=FontFace(
                fill_color=self.get_color_for_rating(rating)))
            row.cell(data.get('residual_risk_override_comment', ''),
                     style=FontFace(size_pt=7))
