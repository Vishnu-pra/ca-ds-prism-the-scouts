# from llm_utils import llm_proxy_api
# import os 
import json
# import time
from document_requirements import GetDocumentRequirement
from technical_requirements import GetTechnicalRequirement
from utils import analyze_text
from comapare_doc_similarity import compare_document_requirements_with_knowledge_base 
from compare_tech_similarity import compare_text_with_knowledge_base 

summary_kb_dir = "/Users/viswanaath.krishnamoorthy/Documents/GitHub/ca-ds-prism-the-scouts/src/artifacts/summary_kb"
document_kb_dir = "/Users/viswanaath.krishnamoorthy/Documents/GitHub/ca-ds-prism-the-scouts/src/artifacts/document_kb"

class Summariser():

    def __init__(self):
        self.doc_summariser = GetDocumentRequirement()
        self.tech_simmariser = GetTechnicalRequirement()

    
    def summariser_pipeline(self, pdf_text, pdf_name):
        try:
            tech_summary = analyze_text(pdf_text, self.tech_simmariser.system_instruction)

            if tech_summary:
                beautified_tech_summary =  self.tech_simmariser.generate_summary_report(tech_summary, pdf_name)

                tech_similarity = compare_text_with_knowledge_base(beautified_tech_summary, summary_kb_dir)

            document_summary = analyze_text(pdf_text, self.doc_summariser.system_instruction)
            if document_summary:
                beautified_document_summary = self.doc_summariser.generate_analysis_report(document_summary, pdf_name)
                doc_similarity = compare_document_requirements_with_knowledge_base(beautified_document_summary, document_kb_dir)
            
            return beautified_tech_summary, tech_similarity, beautified_document_summary, doc_similarity

        
        except:
            print("Summariser pipeline failed")

if __name__ == "__main__":
    summariser = Summariser()

    def load_text_content(file_path):
        """Load text content from a file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            print(f"Error loading file {file_path}: {str(e)}")
            return None
    
    pdf_path = '/Users/viswanaath.krishnamoorthy/Documents/GitHub/ca-ds-prism-the-scouts/sample_pdf_out.txt'
    pdf_text = load_text_content(pdf_path)

    output = summariser.summariser_pipeline(pdf_text, 'sample_pdf_out.txt')

    def save_comparison_result(result, output_path):
        """Save comparison result to JSON file"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving result to {output_path}: {str(e)}")
            return False
    
    with open('tech_summary.txt', 'w', encoding='utf-8') as f:
        f.write(output[0])

    # Save to file
    output_file = "comparison_result.json"
    if save_comparison_result(output[1], output_file):
        print(f"\nResults saved to {output_file}")
    else:
        print(f"\nFailed to save results to {output_file}")


    with open('document_summary.txt', 'w', encoding='utf-8') as f:
        f.write(output[0])

    # Save to file
    output_file = "document_comparison_result.json"
    if save_comparison_result(output[3], output_file):
        print(f"\nResults saved to {output_file}")
    else:
        print(f"\nFailed to save results to {output_file}")

    
