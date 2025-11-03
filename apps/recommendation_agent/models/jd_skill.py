from django.db import models


class JDSkill(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)

    class Meta:
        db_table = 'jd_skill'
        managed = False

    def __str__(self):
        return self.name
