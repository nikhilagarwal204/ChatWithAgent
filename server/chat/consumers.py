import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from langchain.prompts import PromptTemplate
from langchain.schema import AIMessage, HumanMessage
from langchain_ollama import OllamaLLM

from .models import ChatSession, Message

# Initialize Ollama model globally with optimized settings
llm = OllamaLLM(
    model="llama3.2",
    temperature=0.7,
    num_ctx=2048,
    num_thread=4,  # Optimize for multi-threading
    stop=["</s>", "Human:", "Assistant:"],  # Better conversation control
)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.chat_session = await self.get_or_create_chat_session()
        self.room_group_name = f"chat_{self.chat_session.id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

    async def chat_message(self, event):
        """
        Handler for chat_message type events.
        This method is called when a message is received through the channel layer.
        """
        message = event["message"]
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            "type": "message",
            "message": message
        }))

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get("type", "message")

        if message_type == "message":
            user_message = text_data_json["text"]

            # Send typing indicator
            await self.send(text_data=json.dumps({"type": "typing", "isTyping": True}))

            try:
                # Process message and get response
                response = await self.process_with_llama(
                    user_message, await self.get_context()
                )

                # Save messages after successful processing
                await self.save_message("user", user_message)
                await self.save_message("assistant", response)

                # Send response
                await self.channel_layer.group_send(
                    self.room_group_name, {"type": "chat_message", "message": response}
                )
            except Exception as e:
                # Handle errors gracefully
                error_msg = f"Error processing message: {str(e)}"
                await self.send(
                    text_data=json.dumps({"type": "error", "message": error_msg})
                )
            finally:
                # Always turn off typing indicator
                await self.send(
                    text_data=json.dumps({"type": "typing", "isTyping": False})
                )

    @database_sync_to_async
    def get_or_create_chat_session(self):
        session, created = ChatSession.objects.get_or_create(
            id=self.scope.get("session_id", None)
        )
        return session

    @database_sync_to_async
    def save_message(self, role, content):
        return Message.objects.create(
            session=self.chat_session, role=role, content=content
        )

    @database_sync_to_async
    def get_context(self):
        # Get chat history
        messages = Message.objects.filter(session=self.chat_session).order_by(
            "created_at"
        )
        history = []
        for msg in messages:
            if msg.role == "user":
                history.append(HumanMessage(content=msg.content))
            else:
                history.append(AIMessage(content=msg.content))

        # Get document content
        docs = self.chat_session.documents.all()
        doc_content = []
        for doc in docs:
            if doc.content:
                doc_content.append(f"Document: {doc.title}\n{doc.content}")

        return {"history": history, "documents": doc_content}

    async def process_with_llama(self, user_message, context):
        template = """
        <|im_start|>system
        You are a helpful AI assistant. Keep responses clear and concise.
        
        Context:
        {documents}
        
        Recent conversation:
        {history}
        <|im_end|>
        
        <|im_start|>user
        {question}
        <|im_end|>
        
        <|im_start|>assistant
        """

        # Limit history to last 5 messages for faster processing
        history_text = "\n".join(
            [
                f"{'Human' if isinstance(msg, HumanMessage) else 'Assistant'}: {msg.content}"
                for msg in context["history"][-5:]
            ]
        )

        docs_text = "\n".join(context["documents"][:3])  # Limit to 3 most relevant docs

        prompt = PromptTemplate(
            input_variables=["documents", "history", "question"], template=template
        )

        formatted_prompt = prompt.format(
            documents=docs_text if docs_text else "No context available.",
            history=history_text,
            question=user_message,
        )

        response = llm(formatted_prompt)
        return response.strip()
