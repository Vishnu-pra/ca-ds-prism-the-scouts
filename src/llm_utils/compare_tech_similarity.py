import os
import json
import torch
from sentence_transformers import SentenceTransformer, util
from src.llm_utils.utils import get_rfp_link_from_gcs, list_files_in_gcs_folder

def load_text_content(file_path):
    """Load text content from a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        print(f"Error loading file {file_path}: {str(e)}")
        return None

def extract_sections(content):
    """Extract sections from content - simplified to handle any text format"""
    sections = {
        'company_capability': '',
        'technical_capacity': '',
        'product_capacity': ''
    }
    
    current_section = None
    current_content = []
    
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        # Check for section headers
        if any(x in line.upper() for x in ['COMPANY CAPABILITY', '1. COMPANY', 'COMPANY CAP']):
            if current_section:
                sections[current_section] = '\n'.join(current_content)
            current_section = 'company_capability'
            current_content = []
        elif any(x in line.upper() for x in ['TECHNICAL CAPACITY', 'TECHNICAL STRENGTH', '2. TECHNICAL', 'TECH CAP']):
            if current_section:
                sections[current_section] = '\n'.join(current_content)
            current_section = 'technical_capacity'
            current_content = []
        elif any(x in line.upper() for x in ['PRODUCT CAPACITY', 'PRODUCT STRENGTH', '3. PRODUCT', 'PROD CAP']):
            if current_section:
                sections[current_section] = '\n'.join(current_content)
            current_section = 'product_capacity'
            current_content = []
        elif current_section and not any(x in line for x in ['=', '-', '#']):
            current_content.append(line)
    
    # Add the last section
    if current_section:
        sections[current_section] = '\n'.join(current_content)
    
    # If no sections found, treat entire content as technical capacity
    if not any(sections.values()):
        sections['technical_capacity'] = content
    
    return sections

def calculate_text_similarity(input_text, kb_text):
    """Calculate similarity between input text and knowledge base text"""
    model_path = "./artifacts/all-MiniLM-L6-v2"
    model = SentenceTransformer(model_path)
    
    try:
        # Split texts into sentences for better comparison
        input_sentences = [s.strip() for s in input_text.split('.') if s.strip()]
        kb_sentences = [s.strip() for s in kb_text.split('.') if s.strip()]
        
        if not input_sentences or not kb_sentences:
            return 0.0
        
        # Get embeddings
        input_embeddings = model.encode(input_sentences, convert_to_tensor=True)
        kb_embeddings = model.encode(kb_sentences, convert_to_tensor=True)
        
        # Calculate cosine similarities
        similarities = util.cos_sim(input_embeddings, kb_embeddings)
        
        # Get max similarity for each input sentence
        max_similarities = torch.max(similarities, dim=1).values
        
        # Average the similarities
        avg_similarity = torch.mean(max_similarities).item()
        return round(avg_similarity * 100, 2)
        
    except Exception as e:
        print(f"Error calculating similarity: {str(e)}")
        return 0.0

def calculate_category_similarities(input_sections, kb_sections):
    """Calculate similarity scores for each category"""
    scores = {}
    
    for category in ['company_capability', 'technical_capacity', 'product_capacity']:
        input_text = input_sections.get(category, '')
        kb_text = kb_sections.get(category, '')
        print(" The similarity calculated for tech category : ", category)
        if input_text and kb_text:
            scores[category] = calculate_text_similarity(input_text, kb_text)
        else:
            scores[category] = 0.0
    
    return scores

def compare_text_with_knowledge_base(input_text, summary_kb_dir):
    """
    Compare input text with all files in summary_kb directory
    
    Args:
        input_text (str): The text summary to compare
        summary_kb_dir (str): Path to the summary_kb directory
        
    Returns:
        dict: JSON-formatted comparison results
    """
    
    # Get all .txt files from summary_kb directory
    try:
        kb_files = [f for f in os.listdir(summary_kb_dir) if f.endswith('.txt')]
    except Exception as e:
        return {"error": f"Cannot access directory {summary_kb_dir}: {str(e)}"}
    
    if not kb_files:
        return {"error": "No .txt files found in summary_kb directory"}
    
    # Extract sections from input text
    input_sections = extract_sections(input_text)
    
    # Compare with each knowledge base file
    all_comparisons = []
    best_overall_score = 0
    best_match = None
    
    for kb_file in kb_files:
        kb_path = os.path.join(summary_kb_dir, kb_file)
        print(" Checking smiliarities for file : ", kb_file)
        kb_content = load_text_content(kb_path)
        
        if not kb_content:
            continue
        
        # Extract sections from knowledge base
        kb_sections = extract_sections(kb_content)
        
        # Calculate category similarities
        category_scores = calculate_category_similarities(input_sections, kb_sections)
        
        # Calculate overall score
        overall_score = sum(category_scores.values()) / len(category_scores) if category_scores else 0
        
        # Get RFP link from GCS
        rfp_name = kb_file.replace('_Knowledge_Base.txt', '').replace('.txt', '')
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
    summary_kb_dir = "/Users/viswanaath.krishnamoorthy/Documents/GitHub/ca-ds-prism-the-scouts/src/artifacts/summary_kb"
    
    # Example input text (replace with actual input)
    sample_input = """
    RFP SUMMARY REPORT
==================================================

Analysis of RFP: e9956863c32b40ef8e4eefce46b067b7.pdf


Company Capability:
------------------
• Must be one of the pre-empaneled vendors listed in the RFQ.
• Must furnish an Earnest Money Deposit (EMD) of Rs. 1,50,000.
• The selected bidder must submit a Performance Bank Guarantee for 5% of the total contract value.
• Must have implementation experience of the specified APIs in other Schedule Commercial Banks or listed companies.
• Must demonstrate experience based on the number of APIs implemented in other banks.
• Complete integration of all required APIs within 30 days from the purchase order acceptance.
• Must sign a formal contract agreement within 21 days of accepting the purchase order.
• Prices quoted must be fixed for the next two years.
• Must provide a structured and detailed Exit Management plan, including knowledge transfer and transition support to a new vendor.
• Must not subcontract any work without prior written consent from the Bank.
• Must provide a contingent of well-trained personnel who have passed third-party background checks.
• Must adhere to a strict non-disclosure agreement to maintain confidentiality of bank and customer data.
• Must agree to the contract being extendable for one additional year at the same terms and cost, based on performance.
• Must be able to provide presentations and product demonstrations as part of the evaluation process.


Technical Capacity:
------------------
• Must guarantee 24x7x365 availability of all services.
• Must maintain a minimum monthly uptime of 98% for all services.
• The platform must demonstrate experience in handling high transaction volumes (>=700 TPS for maximum evaluation score).
• Must have prior integration experience with lending platforms.
• API outputs must be supported in multiple formats, including JSON, XML, and SOAP.
• Vendor's APIs must be compatible with new platforms to ensure hassle-free migration in the future.
• Must allow the Bank, RBI, or other regulatory authorities the right to conduct annual audits of security, risk management, and governance systems.
• Must have a robust Business Continuity and Disaster Recovery (BCP/DR) plan and conduct periodic testing.
• Must comply with the Bank's Information Security and Cyber Security policies.
• Must adhere to all RBI guidelines, including regulations for the storage of data within India.
• Must ensure compliance with the Digital Personal Data Protection Act (DPDPA) 2023.
• Must immediately report any security incidents, including data breaches or service unavailability, to the Bank.
• Must have processes in place for the secure removal, disposal, or destruction of data.


Product Capacity:
----------------
• Must provide an API for UDYAM registration details verification (both OTP-based with consent and non-OTP based).
• Must provide an API to fetch GST details, including 2-year turnover and filing details from a PAN/GST number.
• Must provide an API for Bank Statement Analysis from digital PDFs or Account Aggregator outputs.
• Must provide an API for Financial Statement Analysis from both digital (PDF/XML/JSON) and scanned documents.
• Must provide an API to fetch company details from the Ministry of Corporate Affairs (MCA), including basic details and detailed data with 3-year financials.
• Must provide an API for Income Tax Return (ITR) verification, including filing status for the past 3 years and document analysis.
• Must provide APIs for various other verifications: Shop & Establishment Certificate, Vehicle RC, Export-Import License, CERSAI, other OVDs (Passport, Driving License, Voter ID), and Litigation Checks.
• Must be able to provide a Proof of Concept (PoC) and a live demo of the proposed services during evaluation.
• Must provide any additional services required to enable the end-to-end digital lending journey.
• Must rectify or replace any defective services or fix bugs at no extra cost to the bank.
• Payments will be based on the actual number of successful API hits on a quarterly basis.

    """
    
    # Perform comparison
    result = compare_text_with_knowledge_base(sample_input, summary_kb_dir)
    
    # Print result as JSON
    print(json.dumps(result, indent=2))
    
    # Save to file
    output_file = "comparison_result.json"
    if save_comparison_result(result, output_file):
        print(f"\nResults saved to {output_file}")
    else:
        print(f"\nFailed to save results to {output_file}")

