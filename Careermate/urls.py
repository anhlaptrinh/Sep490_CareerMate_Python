from django.urls import path, include

from apps.roadmap_agent.views import TestView


urlpatterns = [
    path('api/docs/', include('apps.swagger.urls')),
    path('api/v1/', include('apps.cv_analysis_agent.urls')),
    path('api/test/', TestView.as_view(), name='test'),
]
