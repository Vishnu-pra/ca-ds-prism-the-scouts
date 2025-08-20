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
    
    response_schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "RFPDetailExtractionSchema",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "rfp_id": {
                        "type": "string",
                        "description": "The unique identifier for the RFP."
                    },
                    "events": {
                        "type": "array",
                        "description": "A list of key events with due dates.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "event": {
                                    "type": "string",
                                    "description": "The name of the event."
                                },
                                "due_date": {
                                    "type": "string",
                                    "description": "The due date in YYYY-MM-DD format."
                                },
                                "due_time": {
                                    "type": "string",
                                    "description": "The due time in HH:MM:SS format."
                                }
                            },
                            "required": ["event", "due_date", "due_time"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["rfp_id", "events"],
                "additionalProperties": False
            }
        }
    }

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


<DOCUMENT_TEXT>
{rfp_text}
</DOCUMENT_TEXT>
"""

    llm_output = llm_proxy_api(
        llm_system_prompt=system_prompt,
        llm_user_prompt=user_prompt,
        temperature=0.3,
        top_p=0.9,
    )

    if llm_output:
        try:
            extracted_details = json.loads(llm_output)
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

