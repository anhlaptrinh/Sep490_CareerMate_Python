# agent_core/schemas/resume_schemas.py
"""
JSON schemas for enforcing structured output from Gemini models.
This drastically improves speed and eliminates JSON parsing errors.
"""

# Schema for resume extraction
RESUME_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "email": {"type": "string"},
        "phone": {"type": "string"},
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "degree": {"type": "string"},
                    "school": {"type": "string"},
                    "year": {"type": "string"}
                }
            }
        },
        "experience": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "company": {"type": "string"},
                    "duration": {"type": "string"}
                }
            }
        },
        "projects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "tech": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            }
        },
        "skills": {
            "type": "array",
            "items": {"type": "string"}
        },
        "certificates": {
            "type": "array",
            "items": {"type": "string"}
        },
        "languages": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["name", "email", "phone", "education", "experience", "projects", "skills", "certificates", "languages"]
}

# Schema for feedback generation
FEEDBACK_SCHEMA = {
    "type": "object",
    "properties": {
        "strength": {
            "type": "string",
            "description": "2-3 key strengths in the resume"
        },
        "weakness": {
            "type": "string",
            "description": "2-3 areas to improve"
        },
        "suggest": {
            "type": "string",
            "description": "Top 3 actionable suggestions"
        },
        "overall_score": {
            "type": "integer",
            "description": "Score from 0-100 based on experience (30%), skills (25%), projects (20%), education (15%), completeness (10%)",
            "minimum": 0,
            "maximum": 100
        }
    },
    "required": ["strength", "weakness", "suggest", "overall_score"]
}


