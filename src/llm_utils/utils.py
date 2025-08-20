import os
import json
import requests
from typing import Optional, Dict, Any
from text_extraction import text_extraction

# LLM Configurations
LLM_PROXY_URL = "https://llmproxy-gcp.go-yubi.in/chat/completions"
LLM_PROXY_KEY = "sk-NNj65lMBTN6rTd7XMNOVMA"
MAX_RETRIES = 3

# Initialize Gemini client (if needed)
try:
    from google import genai
    from google.genai import types
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/viswanaath.krishnamoorthy/Downloads/dataengg-poc-194f121bf3d8.json"
    client = genai.Client(
        vertexai=True,
        project="dataengg-poc",
        location="global",
    )
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

def setup_gemini_config(system_instruction: str):
    """Setup Gemini configuration with custom system instruction"""
    return types.GenerateContentConfig(
        temperature=0.7,
        top_p=1,
        seed=0,
        max_output_tokens=65535,
        system_instruction=[types.Part.from_text(text=system_instruction)],
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF")
        ]
    )



def process_folder_documents(folder_path: str) -> str:
    """Process all documents in a folder and combine their text"""
    all_text = ""
    
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            text = text_extraction(file_path)
            
            if text:
                all_text += f"\n\n=== Content from {file} ===\n{text}"
    
    return all_text

def analyze_with_llm_proxy(text: str, system_instruction: str, model: str = "gpt-4.1-(US)") -> Optional[Dict[str, Any]]:
    """Analyze text using LLM proxy with retries"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLM_PROXY_KEY}"
    }
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": [{"type": "text", "text": system_instruction}]
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": f"Analyze this RFP:\n{text}"}]
            }
        ],
        "temperature": 0.2,
        "top_p": 0.98
    }
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(LLM_PROXY_URL, json=payload, headers=headers, timeout=300)
            
            if response.status_code == 200:
                response_data = response.json()
                response_text = response_data['choices'][0]['message']['content']
                
                print(f"\nRaw LLM Response (Attempt {attempt}):")
                print(response_text)
                
                # Clean and parse the response
                clean_text = response_text.replace('```json\n', '').replace('```', '').strip()
                print("\nCleaned Response:")
                print(clean_text)
                
                # Parse JSON
                try:
                    json_start = clean_text.find('{')
                    json_end = clean_text.rfind('}')
                    if json_start >= 0 and json_end >= 0:
                        json_str = clean_text[json_start:json_end + 1]
                        return json.loads(json_str)
                    return json.loads(clean_text)
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON: {str(e)}")
                    if attempt < MAX_RETRIES:
                        print(f"Retrying ({attempt}/{MAX_RETRIES})...")
                        continue
                    return None
            
            if attempt < MAX_RETRIES:
                print(f"LLM proxy failed with status {response.status_code}, retrying ({attempt}/{MAX_RETRIES})...")
                continue
            
            print(f"LLM proxy failed after {MAX_RETRIES} attempts with status {response.status_code}")
            return None
            
        except requests.RequestException as e:
            if attempt < MAX_RETRIES:
                print(f"LLM proxy request failed: {e}, retrying ({attempt}/{MAX_RETRIES})...")
                continue
            
            print(f"LLM proxy request failed after {MAX_RETRIES} attempts: {e}")
            return None

def analyze_with_gemini(text: str, system_instruction: str, model: str = "gemini-2.5-pro") -> Optional[Dict[str, Any]]:
    """Analyze text using Gemini API"""
    if not GEMINI_AVAILABLE:
        print("Gemini API not available. Please install google-cloud-aiplatform package.")
        return None

    try:
        config = setup_gemini_config(system_instruction)
        
        msg_text = types.Part.from_text(text="Analyze this RFP:")
        msg_content = types.Part.from_text(text=text)
        
        contents = [
            types.Content(
                role="user",
                parts=[msg_text, msg_content]
            )
        ]
        
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config
        )
        
        # Clean and parse the response
        response_text = response.text
        print("\nRaw Gemini Response:")
        print(response_text)
        
        # Remove any markdown code block indicators
        clean_text = response_text.replace('```json\n', '').replace('```', '').strip()
        print("\nCleaned Response:")
        print(clean_text)
        
        # Parse JSON
        try:
            json_start = clean_text.find('{')
            json_end = clean_text.rfind('}')
            if json_start >= 0 and json_end >= 0:
                json_str = clean_text[json_start:json_end + 1]
                return json.loads(json_str)
            return json.loads(clean_text)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {str(e)}")
            return None
        
    except Exception as e:
        print(f"Error analyzing with Gemini: {str(e)}")
        return None

def analyze_text(text: str, system_instruction: str) -> Optional[Dict[str, Any]]:
    """Analyze text with fallback from LLM proxy to Gemini"""
    print("Analyzing content with LLM proxy...")
    result = analyze_with_llm_proxy(text, system_instruction)
    
    if not result:
        print("Failed to analyze content with LLM proxy...")
        print("Analyzing content with Gemini...")
        result = analyze_with_gemini(text, system_instruction)
        if not result:
            print("Failed to analyze content with Gemini...")
            return None
    
    return result

def save_output(content: str, output_path: str) -> bool:
    """Save content to file"""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(content)
        print(f"Output saved to: {output_path}")
        return True
    except Exception as e:
        print(f"Error saving output: {str(e)}")
        return False
