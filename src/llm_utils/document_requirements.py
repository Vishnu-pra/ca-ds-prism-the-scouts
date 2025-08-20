import os
import json
from typing import Optional, Dict, Any
# from utils import analyze_text, extract_pdf_text, process_folder_documents, save_output
# from utils import analyze_text, extract_pdf_text, process_folder_documents, save_output

class GetDocumentRequirement:
    """Class for analyzing RFP document submission requirements"""
    
    SYSTEM_INSTRUCTION = """You are a specialized AI expert tasked with analyzing RFP (Request for Proposal) documents.
Extract all required document submissions mentioned in the RFP. Categorize them into:

1. Company Documents:
   - Registration/incorporation certificates
   - Ownership/structure documents
   - Tax registrations

2. Financial Documents:
   - Balance sheets
   - P&L statements
   - Bank statements
   - Audit reports

3. Compliance Documents:
   - Industry certifications
   - Quality certifications
   - Regulatory approvals

4. Legal Documents:
   - Agreements/contracts
   - Declarations
   - Power of attorney

5. Technical Documents:
   - Solution architecture
   - Technical specifications
   - Implementation plans

6. Experience Documents:
   - Work orders
   - Client references
   - Completion certificates

Format the output as a JSON with these categories as keys and arrays of required documents as values.
Be very specific about each document requirement mentioned in the RFP."""

    def __init__(self):
        self.system_instruction = self.SYSTEM_INSTRUCTION

    # def analyze_single_rfp(self, rfp_path: str) -> Optional[Dict[str, Any]]:
    #     """Analyze a single RFP document for document requirements"""
    #     print(f"Extracting text from {rfp_path}...")
    #     rfp_text = extract_pdf_text(rfp_path)
        
    #     if not rfp_text:
    #         print("Failed to extract text from RFP.")
    #         return None
        
    #     return analyze_text(rfp_text, self.system_instruction)

    # def analyze_rfp_folder(self, folder_path: str) -> Optional[Dict[str, Any]]:
    #     """Analyze all documents in a folder for document requirements"""
    #     print(f"Processing documents in {folder_path}...")
    #     all_text = process_folder_documents(folder_path)
        
    #     if not all_text:
    #         print("No text could be extracted from the documents.")
    #         return None
        
    #     return analyze_text(all_text, self.system_instruction)

    def generate_analysis_report(self, analysis_results: Dict[str, Any], source_path: str) -> str:
        """Generate a document analysis report"""
        if not analysis_results:
            return "Analysis failed. Please check the errors above."
        
        output_content = []
        output_content.append("##############################################################")
        output_content.append(f"# {os.path.basename(source_path)} DOCUMENT REQUIREMENTS")
        output_content.append(f"# Analysis Report")
        output_content.append("##############################################################\n")
        
        # Add each category of documents
        for category, documents in analysis_results.items():
            title = category.replace('_', ' ').title()
            output_content.append(f"\n{title}:")
            output_content.append("-" * len(title))
            for doc in documents:
                output_content.append(f"• {doc}")
            output_content.append("")
        
        output_content.append("\n##############################################################")
        output_content.append("# End of Document Requirements")
        output_content.append("##############################################################")
        
        return '\n'.join(output_content)

    def generate_knowledge_base(self, analysis_results: Dict[str, Any], source_path: str) -> str:
        """Generate a document knowledge base from analysis results"""
        if not analysis_results:
            return "Analysis failed. Please check the errors above."
        
        output_content = []
        output_content.append("##############################################################")
        output_content.append(f"# {os.path.basename(source_path)} DOCUMENT REQUIREMENTS")
        output_content.append(f"# Knowledge Base")
        output_content.append("##############################################################\n")
        
        # Add each category of documents
        for category, documents in analysis_results.items():
            title = category.replace('_', ' ').title()
            output_content.append(f"\n{title}:")
            output_content.append("-" * len(title))
            for doc in documents:
                output_content.append(f"• {doc}")
            output_content.append("")
        
        output_content.append("\n##############################################################")
        output_content.append("# End of Document Requirements")
        output_content.append("##############################################################")
        
        return '\n'.join(output_content)

    # def analyze_document_requirements(self, rfp_path: str, output_path: str) -> bool:
    #     """Analyze document requirements in a single RFP"""
    #     analysis_results = self.analyze_single_rfp(rfp_path)
        
    #     if not analysis_results:
    #         return False
        
    #     print("Generating document analysis report...")
    #     report = self.generate_analysis_report(analysis_results, rfp_path)
        
    #     return save_output(report, output_path)

    # def create_document_knowledge_base(self, folder_path: str, output_path: str) -> bool:
    #     """Create a document knowledge base from RFP folder"""
    #     analysis_results = self.analyze_rfp_folder(folder_path)
        
    #     if not analysis_results:
    #         return False
        
    #     print("Generating document knowledge base...")
    #     knowledge_base = self.generate_knowledge_base(analysis_results, folder_path)
        
    #     return save_output(knowledge_base, output_path)