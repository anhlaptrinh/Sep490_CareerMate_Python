# apps/cv_creation_agent/urls.py
from django.urls import path
from .views import CVAnalyzeView, CVTaskStatusView, CVAnalyzeSyncView

urlpatterns = [
    path("analyze_cv/", CVAnalyzeView.as_view(), name="analyze_cv"),
    path("task-status/<str:task_id>/", CVTaskStatusView.as_view(), name="task_status"),
]
