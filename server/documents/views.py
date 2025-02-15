from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings
from .models import Document
from chat.models import ChatSession
import PyPDF2
import os

class DocumentUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request, *args, **kwargs):
        # Get or create chat session
        session_id = request.data.get('session_id')
        try:
            if session_id:
                session = ChatSession.objects.get(id=session_id)
            else:
                session = ChatSession.objects.create()
        except ChatSession.DoesNotExist:
            session = ChatSession.objects.create()
        
        # Get file from request
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if it's a PDF
        if not file_obj.name.endswith('.pdf'):
            return Response(
                {'error': 'Only PDF files are supported'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create document
        document = Document.objects.create(
            session=session,
            title=file_obj.name,
            file=file_obj
        )
        
        # Extract text from PDF
        try:
            # Get the file path
            file_path = os.path.join(settings.MEDIA_ROOT, str(document.file))
            
            # Extract text
            text_content = ""
            with open(file_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text_content += page.extract_text() + "\n\n"
            
            # Update document with extracted text
            document.content = text_content
            document.save()
            
        except Exception as e:
            return Response(
                {'error': f'Error processing PDF: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'message': 'Document uploaded successfully',
            'document_id': document.id,
            'session_id': session.id,
            'title': document.title
        }, status=status.HTTP_201_CREATED)