from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Prefetch
import asyncio
from .models import JobPostings, JobDescription, Account, Candidate, Resume, Skill
from .serializers import (
    JobPostingSerializer,
    AccountSerializer,
    CandidateSerializer,
    JobRecommendationRequestSerializer,
    JobRecommendationResponseSerializer
)
from .services.recommendation_system import get_hybrid_job_recommendations, query_all_jobs


@extend_schema(
    tags=['Job Recommendations'],
    request=JobRecommendationRequestSerializer,
    responses={
        200: JobRecommendationResponseSerializer,
        400: {'description': 'Bad Request - Missing candidate_id'},
        500: {'description': 'Internal Server Error'}
    },
    description="Get hybrid job recommendations for a candidate based on collaborative filtering and content-based filtering",
    summary="Get Job Recommendations"
)
class JobPostingView(APIView):
    """
    API endpoint to get hybrid job recommendations for a candidate
    POST /job-recommendations/ - Get personalized job recommendations
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # 1️⃣ Validate and extract data from request
            serializer = JobRecommendationRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    "error": "Invalid request data",
                    "details": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            validated_data = serializer.validated_data
            candidate_id = validated_data.get("candidate_id")
            top_n = validated_data.get("top_n", 5)

            # 2️⃣ Validate candidate exists in database
            if not Candidate.objects.filter(candidate_id=candidate_id).exists():
                return Response({
                    "ok": False,
                    "error": f"Candidate with ID {candidate_id} does not exist in database",
                    "candidate_id": candidate_id
                }, status=status.HTTP_404_NOT_FOUND)

            # 3️⃣ Build query_item from request data (skills, title, description)
            query_item = {}

            # Add skills if provided
            if "skills" in validated_data and validated_data.get("skills"):
                query_item["skills"] = validated_data["skills"]

            # Add title if provided
            if "title" in validated_data and validated_data.get("title"):
                query_item["title"] = validated_data["title"]

            # Add description if provided
            if "description" in validated_data and validated_data.get("description"):
                query_item["description"] = validated_data["description"]

            # If no query parameters provided, try to fetch from candidate's profile
            if not query_item:
                # Fetch candidate data from database
                candidate = Candidate.objects.select_related('account').prefetch_related(
                    Prefetch('resumes', queryset=Resume.objects.prefetch_related('skills'))
                ).filter(candidate_id=candidate_id).first()

                # Build query_item from candidate's resume
                if candidate.title:
                    query_item["title"] = candidate.title

                # Get skills from latest resume
                resumes = list(candidate.resumes.all())
                if resumes:
                    latest_resume = resumes[0]
                    skills = [skill.skill_name for skill in latest_resume.skills.all()]
                    if skills:
                        query_item["skills"] = skills
                    if latest_resume.about_me:
                        query_item["description"] = latest_resume.about_me

                # If still no query_item data, return error
                if not query_item:
                    return Response({
                        "ok": False,
                        "error": "No query parameters provided and candidate has no resume data",
                        "candidate_id": candidate_id
                    }, status=status.HTTP_400_BAD_REQUEST)

            # 4️⃣ Lấy danh sách job từ DB hoặc Weaviate
            job_ids = [j["job_id"] for j in query_all_jobs()]

            # 5️⃣ Gọi service hybrid with proper async handling
            recs = asyncio.run(get_hybrid_job_recommendations(
                candidate_id=candidate_id,
                query_item=query_item,
                job_ids=job_ids,
                top_n=top_n
            ))

            # 6️⃣ Trả về response JSON
            return Response({
                "ok": True,
                "results": recs
            }, status=status.HTTP_200_OK)

        except Exception as e:
            import traceback
            return Response({
                "ok": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)






@extend_schema(tags=['Candidates'])
class CandidateView(APIView):
    """
    API endpoint to get all candidates with their skills
    GET /candidates/ - List all candidates joined with resume and skills
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Get list of candidates with their skills by joining candidate, resume, and skill tables
        Query params:
        - candidate_id: Filter by specific candidate ID
        - limit: Number of results to return (default: 20)
        - offset: Offset for pagination (default: 0)
        """
        try:
            # Get query parameters
            candidate_id = request.GET.get('candidate_id', None)
            limit = int(request.GET.get('limit', 20))
            offset = int(request.GET.get('offset', 0))

            # Build query with prefetch to optimize joins
            queryset = Candidate.objects.select_related('account').prefetch_related(
                Prefetch('resumes', queryset=Resume.objects.prefetch_related('skills'))
            )

            # Apply filters
            if candidate_id:
                queryset = queryset.filter(candidate_id=candidate_id)

            # Get total count
            total_count = queryset.count()

            # Apply pagination
            candidates = queryset[offset:offset + limit]

            # Serialize data
            candidate_data = []
            for candidate in candidates:
                # Collect all skills from all resumes
                skills = []
                for resume in candidate.resumes.all():
                    for skill in resume.skills.all():
                        skills.append({
                            'skill_name': skill.skill_name,
                            'skill_type': skill.skill_type or '',
                            'yearOfExperience': skill.yearOfExperience or 0
                        })

                candidate_data.append({
                    'candidate_id': candidate.candidate_id,
                    'title': candidate.title or '',
                    'fullname': candidate.fullname or '',
                    'email': candidate.account.email,
                    'skills': skills
                })

            serializer = CandidateSerializer(candidate_data, many=True)

            return Response({
                'success': True,
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
