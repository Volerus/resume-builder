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

def generate_reduced_top_margin_resume(buffer, resume):
    # Load JSON data
    resume_data = resume

    # Define colors
    dark_blue = colors.HexColor('#2C3E50')
    dark_gray = colors.HexColor('#555555')
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Header Styles
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Heading1'],
        fontName=avenir,
        fontSize=24,
        textColor=dark_blue,
        alignment=1, # Center
        spaceAfter=10
    )

    contact_style = ParagraphStyle(
        'ContactStyle',
        parent=styles['Normal'],
        fontName=work_sans,
        fontSize=10,
        textColor=dark_gray,
        alignment=1, # Center
        spaceAfter=20
    )

    # Section Header Style
    section_header_style = ParagraphStyle(
        'SectionHeaderStyle',
        parent=styles['Heading2'],
        fontName=avenir,
        fontSize=14,
        textColor=dark_blue,
        textTransform='uppercase',
        spaceBefore=20,
        spaceAfter=5,
        borderPadding=5,
        borderWidth=0,
        borderColor=dark_blue
    )

    # Content Styles
    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontSize=11,
        fontName=work_sans,
        leading=14,
        spaceAfter=2
    )
    
    company_style = ParagraphStyle(
        'CompanyStyle',
        parent=body_style,
        fontName=work_sans_bold,
        fontSize=12,
        textColor=colors.black
    )
    
    position_style = ParagraphStyle(
        'PositionStyle',
        parent=body_style,
        fontName=work_sans_italic,
        fontSize=11,
        textColor=colors.black
    )
    
    date_location_style = ParagraphStyle(
        'DateLocationStyle',
        parent=body_style,
        fontName=work_sans,
        fontSize=11,
        textColor=colors.black,
        alignment=TA_RIGHT
    )
    
    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=body_style,
        fontName=work_sans,
        fontSize=11,
        leftIndent=15,
        firstLineIndent=0,
        spaceAfter=3,
        bulletIndent=5
    )

    skill_category_style = ParagraphStyle(
        'SkillCategory',
        parent=body_style,
        fontName=work_sans_bold,
        fontSize=11
    )
    
    skill_keywords_style = ParagraphStyle(
        'SkillKeywords',
        parent=body_style,
        fontName=work_sans,
        fontSize=11
    )

    # Define line separator for headers
    line_separator = Table([[""]], colWidths=[7.5*72], rowHeights=[1])
    line_separator.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), dark_blue),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    # Create PDF document with improved margins
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter, 
        rightMargin=0.75*72, 
        leftMargin=0.75*72, 
        topMargin=0.5*72, 
        bottomMargin=0.5*72
    )
    content_elements = []

    # --- Header Section ---
    content_elements.append(Paragraph(resume_data["basics"]["name"], header_style))
    
    # Construct contact info line
    contact_parts = []
    if resume_data['basics'].get('location', {}).get('address'):
        contact_parts.append(resume_data['basics']['location']['address'])
    if resume_data['basics'].get('email'):
        contact_parts.append(resume_data['basics']['email'])
    if resume_data['basics'].get('phone'):
        contact_parts.append(resume_data['basics']['phone'])
    if resume_data['basics'].get('url'): # Assuming website/portfolio might be in basics
         contact_parts.append(resume_data['basics']['url'])

    contact_line = " | ".join(contact_parts)
    content_elements.append(Paragraph(contact_line, contact_style))
    
    # Horizontal line below header
    header_line = Table([[""]], colWidths=[7.5*72], rowHeights=[0.5])
    header_line.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey),
    ]))
    content_elements.append(header_line)
    content_elements.append(Spacer(1, 10))

    # --- Professional Summary ---
    if "professional_summary" in resume_data and resume_data["professional_summary"]:
        content_elements.append(Paragraph("Professional Summary", section_header_style))
        content_elements.append(line_separator)
        content_elements.append(Spacer(1, 8))
        content_elements.append(Paragraph(resume_data["professional_summary"], body_style))

    # --- Skills Section ---
    if "skills" in resume_data and resume_data["skills"]:
        content_elements.append(Paragraph("Skills", section_header_style))
        content_elements.append(line_separator)
        content_elements.append(Spacer(1, 8))
        
        for skill in resume_data["skills"]:
            # Use a table for better alignment of category vs keywords
            # Check if keywords is a list or string
            keywords = skill.get('keywords', [])
            if isinstance(keywords, list):
                keywords_str = ", ".join(keywords)
            else:
                keywords_str = str(keywords)

            skill_data = [
                [Paragraph(f"{skill.get('name', '')}:", skill_category_style),
                 Paragraph(keywords_str, skill_keywords_style)]
            ]
            
            skill_table = Table(skill_data, colWidths=[1.8*72, 5.2*72])
            skill_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            content_elements.append(skill_table)

    # --- Experience Section ---
    if "work" in resume_data and resume_data["work"]:
        content_elements.append(Paragraph("Experience", section_header_style))
        content_elements.append(line_separator)
        content_elements.append(Spacer(1, 8))

        for work in resume_data["work"]:
            # Company and Location line
            company_name = work.get("company", "")
            location = work.get("location", "")
            
            # Position and Dates line
            position = work.get("position", "")
            dates = f"{work.get('startDate', '')} - {work.get('endDate', '')}"

            # Create a table for the header of each job entry to handle alignment
            job_header_data = [
                [Paragraph(company_name, company_style), Paragraph(location, date_location_style)],
                [Paragraph(position, position_style), Paragraph(dates, date_location_style)]
            ]
            
            job_header_table = Table(job_header_data, colWidths=[5*72, 2*72])
            job_header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            content_elements.append(job_header_table)
            content_elements.append(Spacer(1, 4))

            # Highlights
            if work.get("highlights"):
                for highlight in work["highlights"]:
                    if highlight:
                        # Use a bullet character
                        content_elements.append(Paragraph(f"• {highlight}", bullet_style))
            
            content_elements.append(Spacer(1, 12)) # Space between jobs

    # --- Education Section ---
    if "education" in resume_data and resume_data["education"]:
        content_elements.append(Paragraph("Education", section_header_style))
        content_elements.append(line_separator)
        content_elements.append(Spacer(1, 8))
        
        for edu in resume_data["education"]:
            institution = edu.get("institution", "")
            location = edu.get("location", "")
            dates = f"{edu.get('startDate', '')} - {edu.get('endDate', '')}"
            degree_info = f"{edu.get('studyType', '')} {edu.get('area', '')}"
            if edu.get('gpa'):
                degree_info += f" | GPA: {edu['gpa']}"

            edu_data = [
                [Paragraph(institution, company_style), Paragraph(dates, date_location_style)],
                [Paragraph(degree_info, position_style), Paragraph(location, date_location_style)]
            ]
            
            edu_table = Table(edu_data, colWidths=[5.5*72, 1.5*72])
            edu_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            content_elements.append(edu_table)
            content_elements.append(Spacer(1, 6))

    # Build the PDF
    doc.build(content_elements)


if __name__ == "__main__":
    with open('resumemake.json', 'r') as f:
        resume_data = json.load(f)
    with open('info.json', 'r') as f:
        info_data = json.load(f)
    
    full_resume = {**resume_data, **info_data}
    generate_reduced_top_margin_resume('resume.pdf', full_resume)

# Usage example:
# generate_resume('resumemake.json', 'generated_resume.pdf')
"""

# Saving the script to a file
script_filename = "/mnt/data/generate_resume_script.py"
with open(script_filename, "w") as file:
    file.write(script_content)

script_filename
"""