from django.db import models
from chat.models import ChatSession

class Document(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/')
    content = models.TextField(blank=True)  # Extracted text content
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
