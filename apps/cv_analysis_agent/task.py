from celery import shared_task
from .services.extract_text import extract_text
from .services.analyzer_service import analyze_resume_text

@shared_task(bind=True, max_retries=2)
def process_resume_task(self, file_path: str, give_feedback: bool) -> dict:
    try:
        with open(file_path, "rb") as f:
            text = extract_text(f)
        structured = analyze_resume_text(text,give_feedback)
        if give_feedback:
            result = "feedback"
        else:
            result = "structured_resume"

        return {
            result: structured
        }
    except Exception as e:
        raise self.retry(exc=e, countdown=10)
