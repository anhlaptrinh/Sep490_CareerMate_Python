from django.db import models
from .jd_skill import JDSkill
from .job_posting import JobPostings



class JobDescription(models.Model):
    id = models.AutoField(primary_key=True)
    jd_skill = models.ForeignKey(JDSkill, on_delete=models.DO_NOTHING, db_column='skill_id')
    job_posting = models.ForeignKey(JobPostings, on_delete=models.DO_NOTHING, db_column='job_posting_id')
    must_have = models.BooleanField(default=False, db_column='must_to_have')
    experience_year = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'job_description'
        managed = False

    def __str__(self):
        return f"{self.job_posting.title} - {self.jd_skill.name}"