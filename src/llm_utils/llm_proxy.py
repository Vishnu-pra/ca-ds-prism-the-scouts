""" File to track all LLM Proxy Code """
from settings import * 
import requests
import json
import io
from PIL import Image
from pdf2image import convert_from_path
import base64

def llm_proxy_api(
        input_images:list = [], 
        llm_system_prompt:str = "You are a helpful assistant and an expert in RFPS", 
        llm_user_prompt:str = "", 
        llm_context:str = "", 
        model_id:str = "gemini-2.5-flash-(US)", 
        temperature:float = 0.2, 
        response_format:dict = {},
        top_p:float = 0.9) -> str:
    """
    Send text through the configured LLM proxy API and return the response with retry support.
    """
    headers = {"Content-Type": "application/json"}

    if LLM_PROXY_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_PROXY_API_KEY}"
    else: 
        print("LLM_PROXY_API_KEY not found")
        return ""
    
    payload = {
        "model": model_id,
        "messages": [
            {
                "role": "system", 
                "content":  llm_system_prompt
            },
            {
                "role": "user",
                "content": [
                {
                    "type": "text",
                    "text": llm_user_prompt
                }, {
                    "type": "text",
                    "text": llm_context
                }
            ]
            }
        ],
        "temperature": temperature,
        "top_p": top_p
    }

    if input_images:
        payload["messages"][1]["content"].append(
            {
                "type": "image_url",
                "image_url": {
                    "url": "data:image/jpeg;base64," + input_image
                }
            }
        )
    
    if response_format:
        payload["response_format"] = response_format

    max_retries = MAX_RETRIES
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(LLM_PROXY_URL, json=payload, headers=headers, timeout=300)

            if resp.status_code == 200:
                body = resp.json()
                # assume OpenAI-style chat response
                content = body.get("choices", [])[0].get("message", {}).get("content")
                if content:
                    return content
                return json.dumps(body)

            if attempt < max_retries:
                print(f"llm_proxy_api failed with status {resp.status_code}, retrying ({attempt}/{max_retries})...")
                continue

            return ""

        except requests.RequestException as e:

            if attempt < max_retries:
                print(f"llm_proxy_api exception: {e}, retrying ({attempt}/{max_retries})...")
                continue

            return ""

def extract_images(pdf_path:str, start_page:int, end_page:int):

    image_list =  convert_from_path(pdf_path, dpi = 200)

    required_image_list = image_list[start_page:end_page]

    for image in required_image_list:
        # compress image 
        max_size=5242880
        min_side=600
        quality = 95
        orig_width, orig_height = image.size
        width, height = orig_width, orig_height

        while True:
            buffer = io.BytesIO()
            image = image.convert('RGB')  # Ensures compatibility
            image.save(buffer, format='JPEG', quality=quality, optimize=True)
            data = buffer.getvalue()
            if len(data) <= max_size:
                return data
            # Lower quality if possible
            if quality > 20:
                quality -= 10   
                continue
            # If quality can't be lowered further, reduce size
            width = int(width * 0.9)
            height = int(height * 0.9)
            if width < min_side or height < min_side:
                # Stop shrinking if already very small; return as-is
                return data
            image = image.resize((width, height), Image.LANCZOS)
            # Reset quality for smaller image
            quality = 95

            base64.b64encode(image_bytes).decode('utf-8')