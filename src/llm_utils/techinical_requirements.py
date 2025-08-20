import os
import json
from typing import Optional, Dict, Any
from utils import analyze_text, extract_pdf_text, process_folder_documents, save_output

class GetTechnicalRequirement:
    """Class for analyzing RFP technical requirements and capabilities"""
    
    SYSTEM_INSTRUCTION = """You are a specialized AI expert tasked with analyzing RFP (Request for Proposal) documents. 
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

    def __init__(self):
        self.system_instruction = self.SYSTEM_INSTRUCTION

    def analyze_single_rfp(self, rfp_path: str) -> Optional[Dict[str, Any]]:
        """Analyze a single RFP document for technical requirements"""
        print(f"Extracting text from {rfp_path}...")
        rfp_text = extract_pdf_text(rfp_path)
        
        if not rfp_text:
            print("Failed to extract text from RFP.")
            return None
        
        return analyze_text(rfp_text, self.system_instruction)

    def analyze_rfp_folder(self, folder_path: str) -> Optional[Dict[str, Any]]:
        """Analyze all documents in a folder for technical requirements"""
        print(f"Processing documents in {folder_path}...")
        all_text = process_folder_documents(folder_path)
        
        if not all_text:
            print("No text could be extracted from the documents.")
            return None
        
        return analyze_text(all_text, self.system_instruction)

    def generate_summary_report(self, analysis_results: Dict[str, Any], source_path: str) -> str:
        """Generate a summary report of the RFP analysis"""
        if not analysis_results:
            return "Analysis failed. Please check the errors above."
        
        summary = []
        
        # Header
        summary.append("RFP SUMMARY REPORT")
        summary.append("=" * 50)
        summary.append(f"\nAnalysis of RFP: {os.path.basename(source_path)}\n")
        
        # Requirements by Category
        for category in ['company_capability', 'technical_capacity', 'product_capacity']:
            title = category.replace('_', ' ').title()
            summary.append(f"\n{title}:")
            summary.append("-" * len(title))
            
            requirements = analysis_results.get(category, [])
            for req in requirements:
                summary.append(f"• {req}")
            summary.append("")
        
        return "\n".join(summary)

    def generate_knowledge_base(self, analysis_results: Dict[str, Any], source_path: str) -> str:
        """Generate a knowledge base from analysis results"""
        if not analysis_results:
            return "Analysis failed. Please check the errors above."
        
        # Format requirements lists
        company_reqs = '\n'.join([f'• {req}' for req in analysis_results.get('company_capability', [])])
        technical_reqs = '\n'.join([f'• {req}' for req in analysis_results.get('technical_capacity', [])])
        product_reqs = '\n'.join([f'• {req}' for req in analysis_results.get('product_capacity', [])])
        
        # Create knowledge base content
        source_name = os.path.basename(source_path)
        output_content = f"""##############################################################
# {source_name} RFP KNOWLEDGE BASE
# Created: {os.path.basename(source_path).replace('.pdf', '')}
##############################################################

This document contains information extracted from the {source_name} RFP documents.

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
        
        return output_content

    def summarize_rfp(self, rfp_path: str, output_path: str) -> bool:
        """Summarize a single RFP document"""
        analysis_results = self.analyze_single_rfp(rfp_path)
        
        if not analysis_results:
            return False
        
        print("Generating summary report...")
        summary = self.generate_summary_report(analysis_results, rfp_path)
        
        return save_output(summary, output_path)

    def create_knowledge_base(self, folder_path: str, output_path: str) -> bool:
        """Create a knowledge base from RFP folder"""
        analysis_results = self.analyze_rfp_folder(folder_path)
        
        if not analysis_results:
            return False
        
        print("Generating knowledge base...")
        knowledge_base = self.generate_knowledge_base(analysis_results, folder_path)
        
        return save_output(knowledge_base, output_path)
