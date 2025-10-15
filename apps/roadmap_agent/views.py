from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.roadmap_agent.serializers import TestSerializer


class TestView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TestSerializer

    def get(self, request):
        serializer = self.serializer_class({"message": "Token valid", "user": str(request.user)})
        return Response(serializer.data)
