import sys
import os
import json
from llm_utils.llm_proxy import llm_proxy_api
def extract_multiple_rfp_details(rfp_text: str) -> dict:
    """
    Uses an LLM to extract all key events and their details from RFP text.
    Post-processes the results to remove events with no due date.

    Args:
        rfp_text (str): The full text content of the RFP document.

    Returns:
        dict: A dictionary containing the RFP ID and a list of event dictionaries.
    """
    
    system_prompt = (
        "You are an expert procurement analyst specializing in document review. "
        "Your task is to analyze a business document and extract all key events, "
        "their corresponding due dates, and times. "
        "Your final output MUST be a single JSON object and nothing else. Do not include "
        "any explanatory text, comments, or markdown formatting outside of the JSON block."
    )

    user_prompt = f"""
# Task: Extract All RFP Events and Due Dates

Please extract the following information from the text provided below.

**RFP ID:** The unique identifier for the Request for Proposal.
**Events:** A list of all key milestones or events from the document that have a corresponding due date. For each event, extract its exact name as it appears in the document, along with its due date, and due time.

**Formatting Instructions:**
1.  **Date Format:** Convert all dates to the standard YYYY-MM-DD format.
2.  **Time Format:** Convert all times to the standard 24-hour HH:MM:SS format (e.g., 03:00:00 for 3:00 PM).
3.  **Missing Time:** If the document specifies a due date but not a specific due time, you MUST default the time to 23:59:00.

Ensure your output is a single JSON object. If a detail is not found, use a null value.

<DOCUMENT_TEXT>
{rfp_text}
</DOCUMENT_TEXT>

**JSON Output Example:**
{{
  "rfp_id": "12345",
  "events": [
    {{
      "event": "Bid Submission",
      "due_date": "2025-09-30",
      "due_time": "17:00:00"
    }},
    {{
      "event": "Queries/Clarification Submission",
      "due_date": "2025-09-15",
      "due_time": "11:00:00"
    }}
  ]
}}
"""

    llm_output = llm_proxy_api(
        llm_system_prompt=system_prompt,
        llm_user_prompt=user_prompt,
        temperature=0.3,
        top_p=0.9,
        response_format={"type": "json_object"}
    )

    if llm_output:
        try:
            # Clean and parse the JSON response from the LLM
            cleaned_output = llm_output.strip().removeprefix("```json").removesuffix("```").strip()
            extracted_details = json.loads(cleaned_output)

            # === POST-PROCESSING LOGIC ===
            # Filter out events with a null due_date
            if "events" in extracted_details and isinstance(extracted_details["events"], list):
                filtered_events = []
                for event in extracted_details["events"]:
                    # Check if the due_date is present and not null
                    if event.get("due_date") is not None:
                        filtered_events.append(event)
                extracted_details["events"] = filtered_events
                
            return extracted_details
        except json.JSONDecodeError as e:
            print(f"Error: Could not parse LLM response as JSON. Response: {llm_output}. Error: {e}")
            return None
    
    print("Error: LLM returned an empty response.")
    return None

