from celery import shared_task
from .services.extract_text import extract_text
from .services.analyzer_service import analyze_resume_text, generate_feedback

@shared_task(bind=True, max_retries=2)
def process_resume_task(self, file_path: str):
    try:
        with open(file_path, "rb") as f:
            text = extract_text(f)
        structured = analyze_resume_text(text)
        feedback = generate_feedback(structured)
        return {
            "structured_resume": structured,
            "feedback": feedback
        }
    except Exception as e:
        raise self.retry(exc=e, countdown=10)
