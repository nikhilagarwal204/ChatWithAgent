from rest_framework import serializers
from .models import Feedback, Message

class FeedbackSerializer(serializers.ModelSerializer):
    message_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = Feedback
        fields = ['message_id', 'rating', 'comments']
        
    def create(self, validated_data):
        message_id = validated_data.pop('message_id')
        try:
            message = Message.objects.get(id=message_id)
            feedback = Feedback.objects.create(
                message=message,
                session=message.session,
                **validated_data
            )
            return feedback
        except Message.DoesNotExist:
            raise serializers.ValidationError("Message not found")