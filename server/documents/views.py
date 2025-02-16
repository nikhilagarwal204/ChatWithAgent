import PyPDF2
from chat.models import ChatSession
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Document


class DocumentUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        # Validate file
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response(
                {"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not file_obj.name.endswith(".pdf"):
            return Response(
                {"error": "Only PDF files are supported"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get or create session
        session_id = request.data.get("session_id")
        session = ChatSession.objects.get_or_create(id=session_id)[0]

        try:
            document = Document.objects.create(
                session=session, title=file_obj.name, file=file_obj
            )

            # Extract text content
            text_content = self._extract_pdf_text(document.file.path)
            document.content = text_content
            document.save()

            return Response(
                {
                    "message": "Document uploaded successfully",
                    "document_id": document.id,
                    "title": document.title,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response(
                {"error": f"Error processing PDF: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _extract_pdf_text(self, file_path):
        text_content = ""
        with open(file_path, "rb") as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            for page in reader.pages:
                text_content += page.extract_text() + "\n\n"
        return text_content
