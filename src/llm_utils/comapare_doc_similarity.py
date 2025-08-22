import os
import json
import torch
from sentence_transformers import SentenceTransformer, util
import requests
from src.llm_utils.utils import get_rfp_link_from_gcs, list_files_in_gcs_folder

def load_document_requirements(file_path):
    """Load document requirements from a file"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        return content
    except Exception as e:
        print(f"Error loading file {file_path}: {str(e)}")
        return None

def extract_document_sections(content):
    """Extract document sections and their requirements"""
    sections = {
        'Company Documents': [],
        'Financial Documents': [],
        'Compliance Documents': [],
        'Legal Documents': [],
        'Technical Documents': [],
        'Experience Documents': []
    }
    
    current_section = None
    for line in content.split('\n'):
        # Check for section headers
        for section in sections.keys():
            if section in line and ('-' * len(section)) in content.split('\n')[content.split('\n').index(line) + 1]:
                current_section = section
                break
        
        # Add requirements
        if line.startswith('• ') and current_section:
            sections[current_section].append(line[2:].strip())
    
    return sections

def calculate_document_similarity(doc1, doc2, model):
    """Calculate semantic similarity between two document names"""
    # Get embeddings
    emb1 = model.encode(doc1, convert_to_tensor=True)
    emb2 = model.encode(doc2, convert_to_tensor=True)
    
    # Calculate cosine similarity
    similarity = util.cos_sim(emb1, emb2)
    return similarity.item()

def calculate_similarity_scores(new_sections, existing_sections):
    """Calculate similarity scores between document requirement sections"""
    scores = {}
    for category in new_sections.keys():
        new_docs = new_sections[category]
        existing_docs = existing_sections[category]
        print("Checking similarity for category : ", category)
        
        if new_docs and existing_docs:
            score = calculate_section_similarity(new_docs, existing_docs)
            scores[category] = round(score * 100, 2)
        else:
            scores[category] = 0.0
    
    return scores

def calculate_section_similarity(new_docs, existing_docs):
    """Calculate similarity between two lists of documents"""
    model_path = "./artifacts/all-MiniLM-L6-v2"
    model = SentenceTransformer(model_path)
    
    similarities = []
    for new_doc in new_docs:
        best_match = None
        best_score = 0
        
        for existing_doc in existing_docs:
            score = calculate_document_similarity(new_doc, existing_doc, model)
            if score > best_score:
                best_score = score
                best_match = existing_doc
        
        similarities.append(best_score)
    
    return sum(similarities) / len(similarities)

def analyze_alignment(scores):
    """Analyze alignment levels and provide insights"""
    insights = []
    total_score = sum(scores.values())
    num_sections = len([s for s in scores.values() if s > 0])
    avg_score = total_score / num_sections if num_sections > 0 else 0
    
    insights.append(f"Overall Document Alignment: {avg_score:.2f}%")
    
    # Analyze each category
    for category, score in scores.items():
        if score > 0:
            level = "HIGH" if score > 70 else "MODERATE" if score > 40 else "LOW"
            insights.append(f"\n{category}:")
            insights.append(f"- Score: {score}%")
            insights.append(f"- Alignment: {level}")
    
    return insights

def generate_comparison_report(new_rfp_path, comparisons):
    """Generate a detailed comparison report"""
    report = []
    
    # Header
    report.append("DOCUMENT REQUIREMENTS COMPARISON REPORT")
    report.append("=" * 50)
    report.append(f"\nAnalyzing document requirements between:")
    report.append(f"New RFP: {os.path.basename(new_rfp_path)}")
    report.append("And existing RFPs:")
    
    # Track best match
    best_overall = 0
    best_rfp = None
    best_scores = None
    
    # Calculate best match
    for bank_name, scores in comparisons.items():
        total_score = sum(scores.values())
        num_sections = len([s for s in scores.values() if s > 0])
        overall_score = total_score / num_sections if num_sections > 0 else 0
        
        if overall_score > best_overall:
            best_overall = overall_score
            best_rfp = bank_name
            best_scores = scores
    
    # Add best match summary
    report.append("\nBEST MATCH SUMMARY")
    report.append("-" * len("BEST MATCH SUMMARY"))
    report.append(f"Best Matching RFP: {best_rfp}")
    report.append(f"Overall Alignment Score: {best_overall:.2f}%")
    
    if best_scores:
        report.append("\nCategory Scores:")
        for category, score in best_scores.items():
            if score > 0:
                alignment = "HIGH" if score > 70 else "MODERATE" if score > 40 else "LOW"
                report.append(f"• {category}: {score}% [{alignment}]")
    
    # Add detailed comparisons
    for bank_name, scores in comparisons.items():
        report.append(f"\n{bank_name} Comparison")
        report.append("-" * len(f"{bank_name} Comparison"))
        
        insights = analyze_alignment(scores)
        report.extend(insights)
        report.append("")
    
    return "\n".join(report)

def compare_document_requirements_with_knowledge_base(input_text, document_kb_dir):
    """
    Compare input document requirements with all files in document_kb directory
    
    Args:
        input_text (str): The document requirements text to compare
        document_kb_dir (str): Path to the document_kb directory
        
    Returns:
        dict: JSON-formatted comparison results
    """
    
    # Get all .txt files from document_kb directory
    try:
        kb_files = [f for f in os.listdir(document_kb_dir) if f.endswith('.txt')]
    except Exception as e:
        return {"error": f"Cannot access directory {document_kb_dir}: {str(e)}"}
    
    if not kb_files:
        return {"error": "No .txt files found in document_kb directory"}
    
    # Extract sections from input text
    input_sections = extract_document_sections(input_text)
    
    # Compare with each knowledge base file
    all_comparisons = []
    best_overall_score = 0
    best_match = None
    
    for kb_file in kb_files:
        kb_path = os.path.join(document_kb_dir, kb_file)
        print("checking for KB File : ", kb_file)
        kb_content = load_document_requirements(kb_path)
        
        if not kb_content:
            continue
        
        # Extract sections from knowledge base
        kb_sections = extract_document_sections(kb_content)
        
        # Calculate category similarities
        category_scores = calculate_similarity_scores(input_sections, kb_sections)
        
        # Calculate overall score
        total_score = sum(category_scores.values())
        num_sections = len([s for s in category_scores.values() if s > 0])
        overall_score = total_score / num_sections if num_sections > 0 else 0
        
        # Get RFP link from GCS
        rfp_name = kb_file.replace('_Document_Base.txt', '').replace('.txt', '')
        rfp_link = get_rfp_link_from_gcs(rfp_name)
        
        # Create comparison entry
        comparison = {
            "overall_score": round(overall_score, 2),
            "rfp_name": rfp_name,
            "rfp_link": rfp_link if rfp_link else "Link not found",
            "category_breakdown": category_scores
        }
        
        all_comparisons.append(comparison)
        
        # Update best match
        if overall_score > best_overall_score:
            best_overall_score = overall_score
            best_match = comparison
    
    # Sort comparisons by overall score (descending)
    all_comparisons.sort(key=lambda x: x["overall_score"], reverse=True)
    
    # Remove the best match from previous_rfp_matches to avoid duplication
    other_matches = [comp for comp in all_comparisons if comp != best_match]
    
    # Prepare final result
    result = {
        "best_overall_score": round(best_overall_score, 2),
        "best_matching_rfp": best_match["rfp_name"] if best_match else None,
        "best_matching_rfp_link": best_match["rfp_link"] if best_match else None,
        "best_matching_category_breakdown": best_match["category_breakdown"] if best_match else {},
        "previous_rfp_matches": other_matches
    }
    
    return result

def save_comparison_result(result, output_path):
    """Save comparison result to JSON file"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving result to {output_path}: {str(e)}")
        return False

if __name__ == "__main__":
    # List files from GCS first
    try:
        bucket_name = "prism-5x-scouts"
        folder_path = "Knowledge_base/Previous_RFP"

        print("Listing files in Knowledge_base/Previous_RFP folder:")
        files = list_files_in_gcs_folder(bucket_name, folder_path)
        
        if files:
            for file_info in files:
                print(f"- {file_info['name']}")
                print(f"  Size: {file_info['size']} bytes")
                print(f"  Created: {file_info['created']}")
                print(f"  Updated: {file_info['updated']}")
                print(f"  GCS Path: {file_info['gcs_path']}")
                print()
        else:
            print("No files found in the folder.")
            
    except Exception as e:
        print(f"Error listing files: {e}")
    
    # Example usage
    document_kb_dir = "/Users/viswanaath.krishnamoorthy/Documents/GitHub/ca-ds-prism-the-scouts/src/artifacts/document_kb"
    
    # Example input text (replace with actual input)
    sample_input = """
    ##############################################################
# FinTech Onboarding RFE FOR AI ML DRIVEN DOCUMENT VETTING_SV_21072025.pdf DOCUMENT REQUIREMENTS
# Analysis Report
##############################################################


Company Documents:
-----------------
• Certificate of Incorporation issued by Registrar of Companies (for Pvt Ltd/LLP/Partnership)
• Memorandum of Association (MoA)
• Articles of Association (AoA)
• Shareholding pattern document
• Partnership Deed registered by Registrar of Firms or other competent authority (for Partnership Firm)
• Certificate of Incorporation issued by Registrar in case of LLP
• PAN Certificate
• TAN Certificate
• GSTIN Certificate
• Any other tax-related document (if applicable)
• Bidder Details as per Appendix-D (including company profile, website, authorized signatory details, SPOC details, technology competence, external ratings, accreditations, promoters’ qualifications)
• Board resolution authorizing representative to sign and make commitments on behalf of the Bidder
• Power of Attorney (if applicable)
• Registration certificate issued by competent authority as per O.M. No. 6/18/2019-PPD (if applicable)
• Certificate of Recognition as Start-up from DPIIT (for Start-ups)
• Self-declaration on company’s letterhead regarding innovation, development, or improvement of products/services, or scalable business model
• Declaration of officials (names, roles, positions, dates of joining/resignation) who held positions in SBI in last 5 years (at empanelment and RFQ/award stage)
• Declaration regarding past/present litigations, disputes, bankruptcy, insolvency, debarment/blacklisting (on company letterhead)
• Declaration of compliance with restrictions on procurement from countries sharing land border with India (Appendix-A)
• Declaration of no pending Service Level Agreement with SBI for more than 6 months (Appendix-A)


Financial Documents:
-------------------
• Latest audited balance sheet (mandatory for FinTechs/DCPs, and as required for Start-ups)
• Profit and Loss account statement (as mentioned in Part-II)
• Certificate from Chartered Accountant with UDIN certifying turnover (for Start-ups, confirming turnover not exceeding Rs. 100 crore in any financial year since commencement)
• Document showing minimum net worth of Rs. 100 lakh (for FinTechs/DCPs, from latest audited balance sheet)
• Bank statements (if specifically requested in RFQ or as part of financial evaluation)
• Audit reports (if specifically requested in RFQ or as part of financial evaluation)


Compliance Documents:
--------------------
• Industry certifications relevant to the solution (e.g., ISO 9001:2015, ISO 14001:2015, ISO 45001:2018, ISO 27001:2013, CMMI, COPC OSP, ISAE 3402, SOC 1 & 2 Type II, HITRUST, EU GDPR Compliance, etc.)
• Quality certifications relevant to the solution
• Regulatory approvals as required for the solution (to be defined as per project requirement)
• Compliance with Bank’s Data Leakage Prevention measures/policies
• Compliance with product-specific latest guidelines of regulatory authorities
• Data Residency compliance (platform/data hosted in India)
• Security compliance (as per project requirement, including audit trails/logs, encryption at rest, etc.)
• Responsible AI principles compliance (fairness, transparency, non-discrimination, auditability, bias mitigation)
• Compliance with O.M. No. 6/18/2019-PPD, Public Procurement Orders


Legal Documents:
---------------
• Non-Disclosure Agreement (Appendix-E, to be stamped and signed)
• Bid covering letter/Bid form (Appendix-A, on company letterhead)
• Agreements/contracts relevant to the solution (if required at RFQ/award stage)
• Declaration regarding conflict of interest (Appendix-A)
• Declaration regarding compliance with Prevention of Corruption Act 1988 (Appendix-A)
• Declaration of not being debarred/blacklisted/disqualified/terminated for poor performance (Appendix-A)
• Declaration regarding no litigation affecting participation (Appendix-A and company letterhead)
• Power of Attorney (if applicable, with board resolution)
• Any other legal declaration required by SBI at RFQ/award stage


Technical Documents:
-------------------
• Specific response with supporting documents in respect of Eligibility Criteria and technical eligibility criteria (Appendix-C & Appendix-F)
• Solution architecture document (detailed description of product/services, integration/migration requirements, security requirements, scalability, performance, deployment models, etc.)
• Technical specifications of the proposed solution (including compliance with all mandatory requirements in Appendix-F(i))
• Implementation plan (project schedule, milestones, staffing plan, deliverables, training plan, integration/migration plan, help desk setup, MIS/reporting, backup/DR, review/testing/acceptance, etc.)
• Overview of Project Management approach
• Literature on the Solutions/services (segregated and kept together in one section)
• Proof of Concept (PoC) / Technical Evaluation demonstration readiness documentation
• API documentation for integration with SBI systems
• Data flow diagrams, security architecture, compliance mapping
• List of third-party components (if any) and their compliance/certification documents
• Training plan and documentation for SBI team


Experience Documents:
--------------------
• Work orders for completed projects (only contracts of >6 months, deployment in last 3 years, as per evaluation criteria)
• Completion certificates for implemented projects (in India and abroad, in banking/financial institutions and other sectors)
• Client references and contact details (Appendix-I, on letterhead, including client name, address, contact person, project details, start/end dates, status, value of work order)
• Self-certification of number of implementations (Appendix-B evaluation criteria)
• Evidence of experience and certification (Appendix-B, including number of years of operation, certifications, etc.)


##############################################################
# End of Document Requirements
##############################################################
    """
    
    # Perform comparison
    result = compare_document_requirements_with_knowledge_base(sample_input, document_kb_dir)
    
    # Print result as JSON
    print(json.dumps(result, indent=2))
    
    # Save to file
    output_file = "document_comparison_result.json"
    if save_comparison_result(result, output_file):
        print(f"\nResults saved to {output_file}")
    else:
        print(f"\nFailed to save results to {output_file}")
