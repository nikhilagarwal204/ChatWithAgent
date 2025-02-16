from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import FeedbackSerializer

# Create your views here.


class FeedbackView(APIView):
    def post(self, request):
        serializer = FeedbackSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Feedback received successfully"},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
