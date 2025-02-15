from django.contrib import admin
from .models import Document

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'session', 'uploaded_at', 'has_content')
    list_filter = ('uploaded_at',)
    search_fields = ('title', 'content')
    
    @admin.display(boolean=True, description='Has extracted content')
    def has_content(self, obj):
        return bool(obj.content)