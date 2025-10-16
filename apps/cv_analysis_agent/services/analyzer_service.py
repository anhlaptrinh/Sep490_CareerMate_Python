# apps/cv_creation_agent/services/analyzer_service.py
import json
import re
from functools import lru_cache
from agent_core.llm import get_model
from agent_core.prompts import extract_resume_prompts, feedback_prompts
from apps.cv_analysis_agent.services.extract_text import extract_text


# Cache model instances to avoid recreation overhead
@lru_cache(maxsize=2)
def get_cached_model(temperature: float, json_output: bool = True):
    """Cache model instances for reuse"""
    return get_model(temperature=temperature)


def extract_json_from_response(response: str) -> str:
    """Extract JSON from a response that may contain markdown or extra text."""
    if not response or not response.strip():
        raise ValueError("Model returned empty response")

    response = response.strip()

    # Fast path: check if it's already valid JSON
    if response.startswith('{') and response.endswith('}'):
        try:
            json.loads(response)
            return response
        except json.JSONDecodeError:
            pass

    # Try to find JSON in markdown code blocks (non-greedy, more efficient)
    json_match = re.search(r'```(?:json)?\s*(\{[\s\S]+?\})\s*```', response)
    if json_match:
        return json_match.group(1).strip()

    # Try to find JSON object directly (first occurrence)
    json_match = re.search(r'\{[\s\S]+\}', response)
    if json_match:
        return json_match.group(0).strip()

    raise ValueError(f"No valid JSON found in response: {response[:200]}")


def analyze_resume_text(text: str) -> dict:
    """Extract structured data from resume text"""
    # Validate input text
    if not text or not text.strip():
        raise ValueError("Cannot analyze empty resume text. PDF extraction may have failed.")

    text = text.strip()
    if len(text) < 50:
        raise ValueError(f"Resume text too short ({len(text)} chars). May not contain valid resume content.")

    # Use cached model for better performance
    model = get_cached_model(temperature=0.2, json_output=True)

    # Streamlined prompt - system instruction + user content
    full_prompt = f"""{extract_resume_prompts.SYSTEM_PROMPT}

Extract fields from this resume:

{text}

Return ONLY valid JSON, no markdown."""

    response = model.invoke(full_prompt)

    # LangChain returns AIMessage object, get the content
    response_text = response.content if hasattr(response, 'content') else str(response)

    # Debug: Check if response is empty
    if not response_text:
        raise ValueError("Model returned None or empty string. Check API key and model configuration.")

    try:
        json_str = extract_json_from_response(response_text)
        parsed = json.loads(json_str)
        return parsed
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON response from model. Response preview: {response_text[:500]}") from e


def generate_feedback(resume_json: dict) -> dict:
    """Generate feedback based on structured resume data"""
    if not resume_json:
        raise ValueError("Cannot generate feedback for empty resume data")

    # Use cached model with higher temperature for creative feedback
    model = get_cached_model(temperature=0.7, json_output=True)

    # Create concise prompt
    full_prompt = f"""{feedback_prompts.SYSTEM_PROMPT}

Analyze this resume and provide feedback:

{json.dumps(resume_json, indent=2)}

Return ONLY valid JSON with strength, weakness, suggest, and overall_score (0-10)."""

    response = model.invoke(full_prompt)

    # Extract response content
    response_text = response.content if hasattr(response, 'content') else str(response)

    if not response_text:
        raise ValueError("Model returned empty feedback response")

    try:
        json_str = extract_json_from_response(response_text)
        feedback_data = json.loads(json_str)

        # Ensure overall_score is present and valid
        if 'overall_score' not in feedback_data:
            feedback_data['overall_score'] = 70  # Default score

        return feedback_data
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in feedback response: {response_text[:500]}") from e


def analyze_resume_sync(file) -> dict:
    """
    Synchronously analyze a resume file.
    Returns structured data and feedback.
    """
    # Step 1: Extract text from PDF
    text = extract_text(file)

    # Step 2: Extract structured information
    structured = analyze_resume_text(text)

    # Step 3: Generate feedback
    feedback = generate_feedback(structured)

    return {
        "structured_resume": structured,
        "feedback": feedback
    }
