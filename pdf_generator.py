import json

from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

avenir = "Avenir"
font_path = "/System/Library/Fonts/Avenir Next.ttc"  # Replace with the actual path
pdfmetrics.registerFont(TTFont(avenir, font_path))


work_sans = "work_sans"
font_path = "/Users/mehulpadwal/Library/Fonts/WorkSans-Regular.ttf"  # Replace with the actual path
pdfmetrics.registerFont(TTFont(work_sans, font_path))

work_sans_bold = "work_sans_bold"
font_path = "/Users/mehulpadwal/Library/Fonts/WorkSans-Bold.ttf"  # Replace with the actual path
pdfmetrics.registerFont(TTFont(work_sans_bold, font_path))

work_sans_italic = "work_sans_italic"
font_path = "/Users/mehulpadwal/Library/Fonts/WorkSans-Italic.ttf"  # Replace with the actual path
pdfmetrics.registerFont(TTFont(work_sans_italic, font_path))

def generate_reduced_top_margin_resume(buffer, resume, output_path):
    # Load JSON data

    resume_data = resume

    # Define styles
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Heading1'],
        fontName=avenir,
        fontSize=25,
        textColor=colors.black
    )

    sub_header_style = ParagraphStyle(
        'SubHeaderStyle',
        parent=styles['Heading2'],
        fontName=avenir,
        fontSize=13,
        textColor=colors.black,
        padding = 0
    )

    content_style = ParagraphStyle(
        'BodyText',
        fontSize=11,
        fontName=work_sans
    )

    right_align_content_style = ParagraphStyle(
        'BodyText',
        fontSize=11,
        fontName=work_sans,
        alignment= TA_RIGHT
    )

    company_name_style = ParagraphStyle(
        'BodyText',
        fontSize=11,
        fontName=work_sans_bold
    )

    italic_style = ParagraphStyle(
        'BodyText',
        fontSize=11,
        fontName=work_sans_italic
    )

    work_style = ParagraphStyle(
        'BodyText',
        fontSize=11,
        fontName=work_sans,
        leftIndent=6, # This adds a 20-unit indentation
    )

    centered_style = ParagraphStyle(name='CenteredStyle', parent=styles['Normal'], alignment=1)

    # Define line separator
    line_separator = Table([[""]], colWidths=[8*72], rowHeights=[0.1*12])
    line_separator.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.gray),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))

    # Create PDF document with reduced margins
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=12, leftMargin=12, topMargin=0.2*72, bottomMargin = 0.1*72)  # 30% of 1 inch
    content_elements = []

    # Add name and basic info
    basic_info_line = f"{resume_data['basics']['location']['address']} | {resume_data['basics']['email']} | {resume_data['basics']['phone']}"
    content_elements.append(Paragraph(resume_data["basics"]["name"], header_style))
    content_elements[-1].style = centered_style
    content_elements.append(Spacer(1, 15))
    content_elements.append(Paragraph(basic_info_line, content_style))
    content_elements[-1].style = centered_style
    content_elements.append(Spacer(1, 6))  # Reduced gap

    # Education section
    content_elements.append(Paragraph("Education", sub_header_style))
    content_elements.append(line_separator)
    for edu in resume_data["education"]:
        edu_table_data = [
            [Paragraph(edu["institution"], company_name_style),
             Paragraph(f"{edu['startDate']} - {edu['endDate']}", right_align_content_style)],
            [Paragraph(f"{edu['studyType']} {edu['area']} GPA: {edu['gpa']}", italic_style),
             Paragraph(f"{edu['location']}", right_align_content_style)]
        ]
        edu_table = Table(edu_table_data, colWidths=[6*72, 2*72], hAlign='CENTER')
        edu_table.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
        ]))
        content_elements.append(edu_table)
        content_elements.append(Spacer(1, 2))  # Reduced gap

    # Skills section
    content_elements.append(Paragraph("Skills", sub_header_style))
    content_elements.append(line_separator)
    for skill in resume_data["skills"]:
        skill_table_data = [
            [Paragraph(f"{skill['name']}:", company_name_style),
             Paragraph(f"{', '.join(skill['keywords'])}", italic_style)]
        ]

        skill_table = Table(skill_table_data, colWidths=[2 * 72, 6 * 72], hAlign='CENTER')

        skill_table.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT')  # Ensure left alignment
        ]))
        content_elements.append(skill_table)


        # content_elements.append(Paragraph(f"{skill['name']}",italic_style))
        # content_elements.append(Paragraph(f"{' '.join(skill['keywords'])}", work_style))

    content_elements.append(Spacer(1, 6))  # Reduced gap

    # Experience section
    content_elements.append(Paragraph("Experience", sub_header_style))
    content_elements.append(line_separator)
    for work in resume_data["work"]:
        work_table_data = [
            [Paragraph(work["company"], company_name_style),
             Paragraph(f"{work.get('location', '')}", right_align_content_style)],
            [Paragraph(work["position"], italic_style), Paragraph(f"{work['startDate']} - {work['endDate']}", right_align_content_style)]
        ]
        work_table = Table(work_table_data, colWidths=[6*72, 2*72], hAlign='CENTER')
        work_table.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT')  # Ensure left alignment
        ]))
        content_elements.append(work_table)
        content_elements.append(Spacer(1, 6))  # Reduced gap
        if work.get("highlights"):
            for highlight in work["highlights"]:
                if highlight:
                    content_elements.append(Paragraph(f"• {highlight}", work_style))
                    content_elements.append(Spacer(1, 2))
            content_elements.append(Spacer(1, 6))  # Reduced gap


    # Build the PDF with the content
    doc.build(content_elements)


if __name__ == "__main__":
    generate_reduced_top_margin_resume('resumemake.json', 'resume.pdf')

# Usage example:
# generate_resume('resumemake.json', 'generated_resume.pdf')
"""

# Saving the script to a file
script_filename = "/mnt/data/generate_resume_script.py"
with open(script_filename, "w") as file:
    file.write(script_content)

script_filename
"""