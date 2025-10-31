from django.db import models

# Create your models here.

class Contest(models.Model):
    id = models.BigAutoField(primary_key=True)
    slug = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    visibility = models.CharField(max_length=50, choices=[("public", "Public"), ("private", "Private")], default="private")
    penalty_time = models.IntegerField(default=20, help_text="Penalty time in minutes for each wrong submission")
    penalty_mode = models.CharField(max_length=50, choices=[("none", "No Penalty"), ("standard", "Standard Penalty")], default="standard")
    freeze_rankings_at = models.DateTimeField(null=True, blank=True, help_text="Time when the rankings will be frozen")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name="created_contests")
    updated_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name="updated_contests")
   
    class Meta:
        db_table = "contests"
        ordering = ["-start_at"]

class ContestProblem(models.Model):
    id = models.BigAutoField(primary_key=True)
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name="contest_problems")
    problem = models.ForeignKey('problems.Problem', on_delete=models.CASCADE, related_name="contest_problems")
    sequence = models.IntegerField(default=0, help_text="Order of the problem in the contest")
    alias = models.CharField(max_length=10, help_text="Short alias for the problem in the contest context")

    class Meta:
        db_table = "contest_problems"
        unique_together = ("contest", "problem")
        ordering = ["sequence"]