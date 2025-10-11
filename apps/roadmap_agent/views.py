from rest_framework.views import APIView
from rest_framework.response import Response

from careermate.middleware import verify_internal_request


class TestView(APIView):
    @verify_internal_request
    def get(self, request):
        return Response({
            "message": "Request accepted from Spring Boot",
            "method": request.method,
        })
