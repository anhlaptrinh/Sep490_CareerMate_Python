# apps/cv_analysis_agent/services/performance_utils.py
import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)


def timing_decorator(func):
    """Decorator to measure function execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed = end_time - start_time
        logger.info(f"{func.__name__} took {elapsed:.2f}s")
        return result
    return wrapper


def measure_performance(file) -> dict:
    """
    Measure performance of each step in resume analysis.
    Returns timing breakdown for optimization insights.
    """
    from .extract_text import extract_text
    from .analyzer_service import analyze_resume_text, generate_feedback

    timings = {}

    # Step 1: Text extraction
    start = time.time()
    text = extract_text(file)
    timings['text_extraction'] = time.time() - start

    # Step 2: Resume analysis
    start = time.time()
    structured = analyze_resume_text(text)
    timings['resume_analysis'] = time.time() - start

    # Step 3: Feedback generation
    start = time.time()
    feedback = generate_feedback(structured)
    timings['feedback_generation'] = time.time() - start

    timings['total'] = sum(timings.values())

    return {
        "structured_resume": structured,
        "feedback": feedback,
        "performance": {
            "timings_seconds": timings,
            "breakdown_percentage": {
                key: f"{(val/timings['total']*100):.1f}%"
                for key, val in timings.items() if key != 'total'
            }
        }
    }

