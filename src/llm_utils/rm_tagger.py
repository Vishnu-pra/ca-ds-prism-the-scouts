from llm_utils.llm_proxy import llm_proxy_api
import os
import json

def get_relevant_rms(rfa_analysis_report: str) -> list:
    """
    Analyzes an RFA report and returns a list of relevant RM IDs based on their descriptions.

    Args:
        rfa_analysis_report (str): The RFA analysis report as a string.

    Returns:
        list: A list of relevant RM IDs (strings).
    """

    # 1. Load the RM profiles from the local JSON file in the artifacts folder
    rm_file_path = "./artifacts/rm_profiles.json"
    if not os.path.exists(rm_file_path):
        print(f"Error: {rm_file_path} not found.")
        return []

    try:
        with open(rm_file_path, "r") as f:
            rm_profiles = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Could not decode {rm_file_path}.")
        return []

    # 1a. Load company descriptions from the local JSON file in the artifacts folder
    company_file_path = "./artifacts/company_description.json"
    if not os.path.exists(company_file_path):
        print(f"Error: {company_file_path} not found.")
        return []

    try:
        with open(company_file_path, "r") as f:
            company_descriptions = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Could not decode {company_file_path}.")
        return []

    # Create a set of all valid RM IDs for efficient lookup
    valid_rm_ids = {profile["rm_id"] for profile in rm_profiles}
    
    # 2. Prepare the strong, structured, and generic prompts
    system_prompt_rm_tagger = (
        "You are a Lead Business Analyst specializing in strategic resource allocation. "
        "Your task is to analyze a business report and recommend the most relevant personnel "
        "based on their professional descriptions. Your analysis must be thorough, "
        "and your output must strictly adhere to the specified JSON format."
        "Your final output MUST be a JSON object with two keys: 'relevant_ids' (a list of relevant RM IDs) "
        "and 'explanation' (a string explaining why each ID was chosen). "
        "For example: {'relevant_ids': ['rm_123', 'rm_456'], 'explanation': 'rm_123 was chosen because... rm_456 because...'}"
    )

    # Convert the RM profiles list to a readable string format
    rm_profiles_str = json.dumps(rm_profiles, indent=2)

    # Convert the company descriptions list to a readable string format
    company_descriptions_str = json.dumps(company_descriptions, indent=2)

    user_prompt_rm_tagger = f"""
# Task: Identify Relevant Resource Managers (RMs) for an RFP

**Objective:** Find the most relevant RMs for the following Request for Proposal (RFP) analysis report. Relevance is determined by the alignment between the report's critical requirements and the RM's professional description and their company's business domain.

---

# RFA Analysis Report

This document follows a standard format. Your analysis should focus on the content within its sections.

<RFA_REPORT>
{rfa_analysis_report}
</RFA_REPORT>

---

# Company Descriptions

First, identify which company's business domain is most relevant to the requirements of the RFA Report.

<COMPANY_DESCRIPTIONS>
{company_descriptions_str}
</COMPANY_DESCRIPTIONS>

---

# RM Profiles

After identifying the relevant company, evaluate each RM profile based on how well their description aligns with the requirements of the RFA Report and if they work for a relevant company.

<RM_PROFILES>
{rm_profiles_str}
</RM_PROFILES>

---

# Instructions

Follow these steps to generate your response:

1.  **ANALYZE THE RFA REPORT:** Read the RFA Report and determine the key skills, product needs, and expertise required. Pay special attention to the `Technical Capacity` and `Product Capacity` sections which mention APIs for `Bank Statement Analysis`, `Financial Statement Analysis`, `Income Tax Return (ITR)` verification, `GST details`, and `company details from the Ministry of Corporate Affairs (MCA)`.

2.  **IDENTIFY RELEVANT COMPANIES:** Analyze the `<COMPANY_DESCRIPTIONS>` and identify the company whose core business aligns best with the API requirements in the RFA report.

3.  **EVALUATE RM PROFILES:** For each RM, assess their professional description against the key skills and expertise identified in Step 1. Prioritize RMs who work for the company you identified in Step 2.

4.  **SELECT RELEVANT RMs:** Select only the RMs who demonstrate a **high degree of relevance** to the core needs of the RFA report, considering both their personal role and their company's domain.

5.  **GENERATE RESPONSE:** Provide your final response as a single JSON object. The JSON object must contain two keys:
    * `relevant_ids`: A JSON list of the `rm_id` strings for all selected RMs.
    * `explanation`: A single string that provides a clear, concise justification for why each selected RM is relevant. The explanation should reference the RM's description, the specific section of the RFA report they align with, and the company they work for.

**Your final output must be ONLY the JSON object, formatted as a single block of code.**
"""

    # 3. Call the LLM with the prepared prompt
    llm_output = None
    try:
        llm_output = llm_proxy_api(
                llm_system_prompt=system_prompt_rm_tagger, 
                llm_user_prompt=user_prompt_rm_tagger,
                model_id = "gemini-2.5-flash-(US)",
                temperature = 0.3,
                top_p = 0.9)
        
        if llm_output:
            # Remove Markdown code block syntax and parse the JSON
            cleaned_output = llm_output.strip().removeprefix("```json").removesuffix("```").strip()
            
            llm_response_obj = json.loads(cleaned_output)
            
            if "relevant_ids" not in llm_response_obj or not isinstance(llm_response_obj["relevant_ids"], list):
                print(f"Warning: LLM response did not contain a valid 'relevant_ids' list. Output was: {llm_output}")
                return []
            
            relevant_rm_ids = llm_response_obj["relevant_ids"]
            
            explanation = llm_response_obj.get("explanation", "No explanation provided.")
            print("\nLLM's Explanation:")
            print(explanation)
            print("-" * 20)
            
            # 4. Cross-check and filter the list to ensure all IDs are valid
            filtered_ids = [rm_id for rm_id in relevant_rm_ids if rm_id in valid_rm_ids]
            
            invalid_ids = [rm_id for rm_id in relevant_rm_ids if rm_id not in valid_rm_ids]
            if invalid_ids:
                print(f"Warning: The LLM generated the following invalid IDs that were filtered out: {invalid_ids}")
            
            return filtered_ids
        else:
            print("Error: LLM returned an empty response.")
            return []

    except json.JSONDecodeError:
        print(f"Error: Could not parse LLM response as JSON. Response: {llm_output}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []


rfa_analysis_report = """RFP SUMMARY REPORT
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

# print(get_relevant_rms(rfa_analysis_report))