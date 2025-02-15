from django.contrib import admin
from .models import ChatSession, Message, Feedback


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "updated_at")
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "role", "short_content", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("content",)

    @admin.display(description="Content")
    def short_content(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("session", "message", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("comments",)

    @admin.display(description="Message")
    def message_content(self, obj):
        return (
            obj.message.content[:50] + "..."
            if len(obj.message.content) > 50
            else obj.message.content
        )
