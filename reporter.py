# reporter.py

import os
import smtplib # SMTP library for email sending
import ssl # Library for secure connection (SSL)
from typing import List # List for type hinting
from pathlib import Path # Path for path handling
from email.mime.multipart import MIMEMultipart # Object to combine email body/attachments
from email.mime.base import MIMEBase # Base object for handling attachments
from email.mime.text import MIMEText # Object for handling email body (text)
from email.utils import formatdate # For formatting email date
from email import encoders # For encoding attachments to Base64

from markdown_pdf import MarkdownPdf, Section # Markdown to PDF converter (specified in requirements.txt)
from state import AgentState # State blueprint

# [Important] Get project root path (folder containing reporter.py)
# Without this, files will be saved in wrong location when run via cron
BASE_DIR = Path(__file__).parent.absolute()
REPORTS_DIR = BASE_DIR / "reports"

def _generate_pdf_report(target_stock: str, report_sections: list[str]) -> str:
    """
    Helper function that generates a single PDF file from 16 report sections.
    """
    print("--- [Reporter] Starting PDF report generation ---")

    try:
        # [Modified] Create reports folder if it does not exist (use absolute path)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        # 1. Combine markdown
        final_markdown = "\n\n".join(report_sections)
        title = f"# {target_stock} Stock Comprehensive Analysis Report\n\n"
        final_markdown = title + final_markdown

        # 3. Create PDF converter object
        pdf = MarkdownPdf()
        section = Section(text=final_markdown, toc=False)

        # 5. Table styling
        table_css = """
table {
    border-collapse: collapse;
    width: 100%;
    margin: 10px 0;
    border: 1px solid #000;
}
th, td {
    border-right: 1px solid #000;
    border-bottom: 1px solid #000;
    padding: 8px;
    text-align: left;
}
th:last-child, td:last-child {
    border-right: none;
}
tr:last-child td {
    border-bottom: none;
}
th {
    font-weight: bold;
}
"""
        pdf.add_section(section, user_css=table_css)

        # 6. Set save path (absolute path + filename)
        pdf_filename = f"[{target_stock}]Comprehensive_Analysis_Report.pdf"
        output_path = REPORTS_DIR / pdf_filename

        # 7. Save PDF
        pdf.save(str(output_path))

        print(f"--- [Reporter] PDF generation complete: {output_path} ---")

        return str(output_path)

    except Exception as e:
        print(f"--- [Reporter] PDF generation failed: {e} ---")
        return None

def _generate_bilingual_pdfs(target_stock: str, english_sections: list[str], korean_sections: list[str] = None) -> dict:
    """
    Helper function that generates bilingual PDF files (English + Korean).
    """
    print("--- [Reporter] Starting bilingual PDF generation ---")

    result = {}

    # [Modified] Create reports folder if it does not exist (use absolute path)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Common table CSS
    table_css = """
table {
    border-collapse: collapse;
    width: 100%;
    margin: 10px 0;
    border: 1px solid #000;
}
th, td {
    border-right: 1px solid #000;
    border-bottom: 1px solid #000;
    padding: 8px;
    text-align: left;
}
th:last-child, td:last-child {
    border-right: none;
}
tr:last-child td {
    border-bottom: none;
}
th {
    font-weight: bold;
}
"""

    # Generate English PDF
    try:
        english_markdown = "\n\n".join(english_sections)
        english_title = f"# {target_stock} Stock Comprehensive Analysis Report\n\n"
        english_markdown = english_title + english_markdown

        pdf = MarkdownPdf()
        section = Section(text=english_markdown, toc=False)
        pdf.add_section(section, user_css=table_css)

        # [Modified] Use absolute path
        english_filename = f"ENG_[{target_stock}]Comprehensive_Analysis_Report.pdf"
        output_path_en = REPORTS_DIR / english_filename
        
        pdf.save(str(output_path_en))

        print(f"--- [Reporter] English PDF generation complete: {output_path_en} ---")
        result["english"] = str(output_path_en)

    except Exception as e:
        print(f"--- [Reporter] English PDF generation failed: {e} ---")
        import traceback
        traceback.print_exc()

    # Generate Korean PDF (if available)
    if korean_sections and len(korean_sections) > 0:
        try:
            korean_markdown = "\n\n".join(korean_sections)
            korean_title = f"# {target_stock} Stock Comprehensive Analysis Report\n\n"
            korean_markdown = korean_title + korean_markdown

            pdf = MarkdownPdf()
            section = Section(text=korean_markdown, toc=False)
            pdf.add_section(section, user_css=table_css)

            # [Modified] Use absolute path
            korean_filename = f"KOR_[{target_stock}]Comprehensive_Analysis_Report.pdf"
            output_path_ko = REPORTS_DIR / korean_filename
            
            pdf.save(str(output_path_ko))

            print(f"--- [Reporter] Korean PDF generation complete: {output_path_ko} ---")
            result["korean"] = str(output_path_ko)

        except Exception as e:
            print(f"--- [Reporter] Korean PDF generation failed: {e} ---")
            print("--- [Reporter] Will proceed with English PDF only ---")
            import traceback
            traceback.print_exc()
    else:
        print("--- [Reporter] No Korean sections available, skipping Korean PDF ---")

    return result

def _send_email_with_attachments(recipient_emails: List[str], subject: str, body: str, pdf_files: dict):
    """
    Helper function that sends an email with multiple PDF attachments.
    """
    print(f"--- [Reporter] Starting email sending with {len(pdf_files)} PDF(s) (To: {', '.join(recipient_emails)}) ---")

    sender_email = os.getenv("GMAIL_USER")
    sender_password = os.getenv("GMAIL_APP_PASSWORD")

    if not sender_email or not sender_password:
        print("--- [Reporter] GMAIL_USER or GMAIL_APP_PASSWORD not found in .env.")
        print("---              Skipping email sending.")
        return

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ", ".join(recipient_emails)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach(MIMEText(body))

    # Attach all PDF files
    for lang, pdf_path in pdf_files.items():
        try:
            # Read file
            with open(pdf_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())

            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(pdf_path)}",
            )

            msg.attach(part)
            print(f"--- [Reporter] PDF attachment ({lang}) processing complete: {pdf_path} ---")

        except FileNotFoundError:
            print(f"--- [Reporter] PDF file not found ({lang}): {pdf_path}")
        except Exception as e:
            print(f"--- [Reporter] PDF attachment ({lang}) failed: {e} ---")

    # Send email
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_emails, msg.as_string())

        print(f"--- [Reporter] Email sent successfully with {len(pdf_files)} PDF(s): {', '.join(recipient_emails)} ---")

    except Exception as e:
        print(f"--- [Reporter] Email sending failed: {e} ---")

def generate_and_send_report(state: AgentState) -> dict:
    """
    [Final Node] Generates bilingual PDFs and sends email.
    """
    target_stock = state['target_stock']
    recipient_emails = state['recipient_emails']

    unified_report = state.get('unified_report', [])
    report_sections = state.get('report_sections', [])
    english_sections = unified_report if unified_report else report_sections
    korean_sections = state.get('korean_report', [])

    if unified_report:
        print("--- [Reporter] Using unified report for English PDF ---")
    else:
        print("--- [Reporter] Using original report for English PDF ---")

    if korean_sections:
        print(f"--- [Reporter] Korean translation available: {len(korean_sections)} sections ---")
    else:
        print("--- [Reporter] No Korean translation available, generating English PDF only ---")

    retried_succeeded = state.get('failed_groups', [])
    permanently_failed = state.get('permanently_failed_groups', [])

    # Generate PDF (always created in reports folder)
    pdf_files = _generate_bilingual_pdfs(target_stock, english_sections, korean_sections)

    if pdf_files:
        is_incomplete = len(permanently_failed) > 0
        has_retries = len(retried_succeeded) > 0
        
        subject = f"JooKkoomi AI Individual Stock Analysis Report: {target_stock}"
        if is_incomplete:
            subject = f"[Incomplete] {subject}"

        body_parts = [f"{target_stock} stock analysis completed.\n"]

        if has_retries:
            retried_names = [g.replace(" (retry successful)", "") for g in retried_succeeded]
            body_parts.append(f"ℹ️  Groups completed after retry: {', '.join(retried_names)}\n")

        if is_incomplete:
            body_parts.append(f"⚠️ Warning: Incomplete analysis: {', '.join(permanently_failed)}\n")

        if "korean" in pdf_files:
            body_parts.append("📎 Attachments: English (ENG) and Korean (KOR) PDF")
        else:
            body_parts.append("📎 Attachments: English PDF only")

        body_parts.append("\nPlease check the attached PDF file.")
        
        _send_email_with_attachments(recipient_emails, subject, "\n".join(body_parts), pdf_files)
    else:
        print("--- [Reporter] Cannot send email because no PDF files were generated.")

    return {}