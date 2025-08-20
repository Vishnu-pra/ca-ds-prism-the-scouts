from llm_utils import llm_proxy_api
import os 
import json
import time
from llm_utils.llm_prompts import *


def summarise_text_with_gemini(text):
    """Analyze text using Gemini API"""

    try:

        response = llm_proxy_api(
            llm_system_prompt = SUMMARISATION_LLM_SYSTEM_PROMPT,
            llm_user_prompt = SUMMARISATION_LLM_USER_PROMPT,
            llm_context = text,
            model_id = "gemini-2.5-flash-(US)",
            temperature = 0.7,
            top_p = 1,
            response_format = SUMMARISATION_LLM_OUTPUT_FORMAT
        )
        
        
        # Clean and parse the response
        print("\nRaw Gemini Response:")
        print(response)
        
        # Remove any markdown code block indicators
        clean_text = response.replace('```json\n', '').replace('```', '').strip()
        print("\nCleaned Response:")
        print(clean_text)
        
        # Parse JSON
        try:
            analysis = json.loads(clean_text)
        except json.JSONDecodeError as e:
            print(f"Error parsing llm response JSON while summarising: {str(e)}")
            analysis = {}
        
        # Convert to proper format
        formatted_response = {
            'company_capability': analysis.get('company_capability', []),
            'technical_capacity': analysis.get('technical_capacity', []),
            'product_capacity': analysis.get('product_capacity', [])
        }
        
        return json.dumps(formatted_response)
        
    except Exception as e:
        print(f"Error analyzing text: {str(e)}")
        return None


def summarise_rfp_file(file_path):
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
        print(" Unknown file format in summariosation : ", file_path)
        return ""
    
    if text:
        print("Summarising file : ", file_path)
        summarisation_start_time = time.time()
        summarised_text = summarise_text_with_gemini(text)
        summarisation_end_time = time.time()
        print("Summarisation time : ", summarisation_end_time - summarisation_start_time)
        return summarised_text
    else:
        print("No actionable text found in file for summarisation : ", file_path)
        return ""
        