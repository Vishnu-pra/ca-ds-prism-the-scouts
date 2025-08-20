from llm_utils import llm_proxy_api
import os 
import json
import time
from llm_utils.llm_prompts import *



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

def process_rfp_folder(folder_path):
    """Process all documents in the RFP folder"""
    all_text = ""
    
    # Walk through the folder
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_ext = os.path.splitext(file)[1].lower()
            
            # Extract text based on file type
            if file_ext == '.pdf':
                text = extract_text_from_pdf(file_path)
            elif file_ext in ['.doc', '.docx']:
                text = extract_text_from_docx(file_path)
            elif file_ext in ['.xls', '.xlsx']:
                text = extract_text_from_excel(file_path)
            else:
                continue
                
            if text:
                all_text += f"\n\n=== Content from {file} ===\n{text}"
    
    return all_text


class GetTechnicalSummary():


    def __init__(self):
        # System instruction for RFP analysis
        self.system_instruction = """You are a specialized AI expert tasked with analyzing RFP (Request for Proposal) documents. 
        Extract and categorize information into three main categories:

        1. Company Capability Requirements
        2. Technical Capacity/Strength Requirements
        3. Product Capacity/Strength Requirements

    Format the output as a JSON with these three categories as main keys. Under each category, 
    list the specific requirements or expectations mentioned in the RFP.

    Example format:
    {
        "company_capability": [
            "Requirement 1",
            "Requirement 2"
        ],
        "technical_capacity": [
            "Requirement 1",
            "Requirement 2"
        ],
        "product_capacity": [
            "Requirement 1",
            "Requirement 2"
        ]
    }

    Only output the JSON, no additional text or explanations."""


    

    def create_knowledge_base(self, folder_path, output_path, use_llm_proxy=False):
        """Create a knowledge base from RFP folder"""
        # Process all documents
        print(f"Processing documents in {folder_path}...")
        all_text = process_rfp_folder(folder_path)
        
        if not all_text:
            print("No text could be extracted from the documents.")
            return False
        
        analysis_text = analyze_text_with_llm_proxy(all_text)

        if not analysis_text:
            print("Failed to analyze content with LLM proxy ....")
            print("Analyzing content with Gemini...")
            analysis_text = analyze_text_with_gemini(all_text)
            if not analysis_text:
                print("Failed to analyze content with Gemini ....") 
                return False
        
        try:
            # Parse the JSON response
            analysis = json.loads(analysis_text)
            
            # Format requirements lists
            company_reqs = '\n'.join([f'• {req}' for req in analysis.get('company_capability', [])])
            technical_reqs = '\n'.join([f'• {req}' for req in analysis.get('technical_capacity', [])])
            product_reqs = '\n'.join([f'• {req}' for req in analysis.get('product_capacity', [])])
            
            # Create knowledge base content
            bank_name = os.path.basename(folder_path)
            output_content = f"""##############################################################
            # {bank_name} RFP KNOWLEDGE BASE
            # Created: {pd.Timestamp.now().strftime('%Y-%m-%d')}
            ##############################################################

            This document contains information extracted from the {bank_name} RFP documents.

            ===============================================================
            1. COMPANY CAPABILITY
            ===============================================================
            {company_reqs}

            ===============================================================
            2. TECHNICAL CAPACITY/STRENGTH
            ===============================================================
            {technical_reqs}

            ===============================================================
            3. PRODUCT CAPACITY/STRENGTH
            ===============================================================
            {product_reqs}

            ##############################################################
            # End of Knowledge Base
            ##############################################################"""

            # Save to file
            with open(output_path, 'w') as f:
                f.write(output_content)
            
            print(f"Knowledge base created successfully: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error creating knowledge base: {str(e)}")
            return False

    
        
