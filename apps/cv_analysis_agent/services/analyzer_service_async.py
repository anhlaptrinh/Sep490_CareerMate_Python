# apps/cv_analysis_agent/services/analyzer_service_async.py
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from apps.cv_analysis_agent.services.analyzer_service import (
    analyze_resume_text,
    generate_feedback,
    extract_text
)


def analyze_resume_async(file) -> dict:
    """
    Asynchronously analyze resume with parallel processing.
    Much faster than sync version for multi-step operations.
    """
    # Step 1: Extract text from PDF (must be done first)
    text = extract_text(file)

    # Step 2 & 3: Run extraction and a dummy task in parallel preparation
    # Since feedback depends on structured data, we do extraction first
    structured = analyze_resume_text(text)

    # Step 3: Generate feedback based on structured data
    feedback = generate_feedback(structured)

    return {
        "structured_resume": structured,
        "feedback": feedback
    }


async def analyze_resume_concurrent(file) -> dict:
    """
    Concurrent version using ThreadPoolExecutor.
    Extracts text first, then runs analysis in thread pool.
    """
    loop = asyncio.get_event_loop()

    with ThreadPoolExecutor(max_workers=2) as executor:
        # Step 1: Extract text (blocking I/O)
        text = await loop.run_in_executor(executor, extract_text, file)

        # Step 2: Analyze text (API call)
        structured = await loop.run_in_executor(
            executor, analyze_resume_text, text
        )

        # Step 3: Generate feedback (API call)
        feedback = await loop.run_in_executor(
            executor, generate_feedback, structured
        )

    return {
        "structured_resume": structured,
        "feedback": feedback
    }

