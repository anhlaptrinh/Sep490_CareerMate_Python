import os

from celery.result import AsyncResult
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from careermate import celery_app
from .services.analyzer_service import analyze_resume_sync
from .serializers import ResumeUploadSerializer
from .task import process_resume_task

TMP_DIR = "/tmp/uploads"
os.makedirs(TMP_DIR, exist_ok=True)

class CVAnalyzeView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = ResumeUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file = serializer.validated_data['file']
        give_feedback = serializer.validated_data['give_feedback']

        temp_path = os.path.join(TMP_DIR, file.name)
        with open(temp_path, "wb+") as dest:
            for chunk in file.chunks():
                dest.write(chunk)

        task = process_resume_task.delay(temp_path,give_feedback)
        return Response({
            "task_id": task.id,
            "status": "processing"
        }, status=status.HTTP_202_ACCEPTED)

class CVTaskStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, task_id):
        result = AsyncResult(task_id, app=celery_app)
        if result.state == "SUCCESS":
            # Return the actual CV analysis result
            return Response({
                "status": "completed",
                "data": result.result  # This contains the structured_resume data
            }, status=status.HTTP_200_OK)
        elif result.state == "PENDING":
            return Response({"status": "pending"}, status=status.HTTP_202_ACCEPTED)
        elif result.state == "STARTED":
            return Response({"status": "in_progress"}, status=status.HTTP_202_ACCEPTED)
        elif result.state == "FAILURE":
            return Response({
                "status": "failed",
                "error": str(result.result)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"status": result.state}, status=status.HTTP_200_OK)

class CVAnalyzeSyncView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        # Use serializer for validation
        serializer = ResumeUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file = serializer.validated_data['file']

        try:
            result = analyze_resume_sync(file,True)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        serializer = ResumeUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        file = serializer.validated_data['file']
        try:
            result = analyze_resume_sync(file,False)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


