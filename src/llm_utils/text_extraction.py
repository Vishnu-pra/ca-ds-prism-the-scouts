import fitz  # PyMuPDF
import pandas as pd
import docx
import os

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF file"""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        print(f"Error extracting PDF text from {pdf_path}: {str(e)}")
        return None

def extract_text_from_docx(docx_path):
    """Extract text from DOCX file"""
    try:
        doc = docx.Document(docx_path)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    except Exception as e:
        print(f"Error extracting DOCX text from {docx_path}: {str(e)}")
        return None

def extract_text_from_excel(excel_path):
    """Extract text from Excel file"""
    try:
        df = pd.read_excel(excel_path)
        text = df.to_string()
        return text
    except Exception as e:
        print(f"Error extracting Excel text from {excel_path}: {str(e)}")
        return None


def text_extraction(file_path:str) -> str:

    if not os.path.exists(file_path):
        print("File does not exist for text recognition in file : ", file_path)
        return ""

    file_ext = os.path.splitext(file_path)[1].lower()
    
    # Extract text based on file type
    if file_ext == '.pdf':
        return extract_text_from_pdf(file_path)
    elif file_ext in ['.doc', '.docx']:
        return extract_text_from_docx(file_path)
    elif file_ext in ['.xls', '.xlsx']:
        return extract_text_from_excel(file_path)
    else:
        print(" Unknown file format in text extraction : ", file_path)
        return ""
    
