
SUMMARISATION_LLM_SYSTEM_PROMPT = """You are a specialized AI expert tasked with analyzing RFP (Request for Proposal) documents. 
Extract and categorize information into three main categories:

1. Company Capability
2. Technical Capacity/Strength
3. Product Capacity/Strength

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

SUMMARISATION_LLM_USER_PROMPT = "Analyze this RFP and categorize requirements:"

SUMMARISATION_LLM_OUTPUT_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "SummarisationOutputFormat",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "company_capability": {"type": "array", "items": {"type": "string"}},
                "technical_capacity": {"type": "array", "items": {"type": "string"}},
                "product_capacity": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["company_capability", "technical_capacity", "product_capacity"],
            "additionalProperties": False
        }
    }
}