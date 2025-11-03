from django.db import models
from .candidate import Candidate
from .job_posting import JobPostings


# =====================================================
#  JOB FEEDBACK
# =====================================================

class JobFeedback(models.Model):
    class FeedbackType(models.TextChoices):
        APPLY = 'apply', 'Apply'
        LIKE = 'like', 'Like'

    feedback_type = models.CharField(max_length=10, choices=FeedbackType.choices, default=FeedbackType.APPLY)
    score = models.FloatField(null=True, blank=True)
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name='job_feedbacks',   # 1 candidate có nhiều feedback
        db_column='candidate_id'
    )

    job = models.ForeignKey(
        JobPostings,
        on_delete=models.CASCADE,
        related_name='feedbacks',# 1 job có nhiều feedback
        db_column='job_id'
    )

    class Meta:
        db_table = 'job_feedback'
        managed = False  # Database table already exists
        unique_together = ('candidate', 'job', 'feedback_type')
        indexes = [
            models.Index(fields=['candidate']),
            models.Index(fields=['job']),
            models.Index(fields=['feedback_type']),
        ]

    def __str__(self):
        return f"Feedback #{self.id} - Candidate {self.candidate_id} → Job {self.job_id}"
