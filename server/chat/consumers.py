import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from documents.models import Document
from langchain.schema import AIMessage, HumanMessage
from langchain_ollama import OllamaLLM

from .agents.producer import ProducerAgent
from .agents.reviewer import ReviewerAgent
from .models import ChatSession, Message

# Initialize Ollama model globally with optimized settings
llm = OllamaLLM(
    model="llama3.2",
    temperature=0.3,
    num_ctx=4096,  # Increased context window for improved answer accuracy
    num_thread=4,  # Optimize for multi-threading
    stop=["</s>", "Human:", "Assistant:"],  # Better conversation control
)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            # Parse query string more safely
            query_string = self.scope["query_string"].decode()
            query_params = {}
            if query_string:
                for param in query_string.split("&"):
                    if "=" in param:
                        key, value = param.split("=", 1)
                        query_params[key.strip()] = value.strip()

            # Extract clean session_id & Remove any trailing query params
            session_id = query_params.get("session_id", "").split("?")[0]
            self.scope["session_id"] = session_id
            print(f"Connecting with session ID: {session_id}")

            # Initialize room_group_name before potential errors
            self.room_group_name = None

            if not session_id:
                print("No session ID provided")
                await self.close()
                return

            await self.accept()
            self.chat_session = await self.get_or_create_chat_session()
            self.room_group_name = f"chat_{self.chat_session.id}"
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        except Exception as e:
            print(f"Connection error: {str(e)}")
            await self.close()

    async def disconnect(self, close_code):
        # Check if room_group_name exists before trying to access it
        if hasattr(self, "room_group_name") and self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

    async def chat_message(self, event):
        """
        Handler for chat_message type events.
        This method is called when a message is received through the channel layer.
        """
        message = event["message"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({"type": "message", "message": message}))

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get("type", "message")

        if message_type == "message":
            user_message = text_data_json["text"]

            # Only send typing indicator when actually processing a message
            await self.send(json.dumps({"type": "typing", "isTyping": True}))

            try:
                # Process message and get response
                response = await self.process_with_llama(
                    user_message, await self.get_context()
                )

                # Save messages after successful processing
                await self.save_message("user", user_message)
                await self.save_message("assistant", response)

                # Send response and stop typing indicator
                await self.send(json.dumps({"type": "message", "message": response}))

            except Exception as e:
                await self.send(
                    json.dumps({"type": "error", "message": f"Error: {str(e)}"})
                )
            finally:
                # Always ensure typing indicator is turned off
                await self.send(json.dumps({"type": "typing", "isTyping": False}))

    @database_sync_to_async
    def get_or_create_chat_session(self):
        # Add debug prints
        session_id = self.scope.get("session_id", None)
        print(f"Attempting to get/create session with ID: {session_id}")

        session, created = ChatSession.objects.get_or_create(id=session_id)
        print(f"Session found/created: {session.id}, Created new: {created}")
        return session

    @database_sync_to_async
    def save_message(self, role, content):
        return Message.objects.create(
            session=self.chat_session, role=role, content=content
        )

    @database_sync_to_async
    def get_context(self):
        """Get chat history and document context"""
        # Debug current session
        print(f"Current chat session ID: {self.chat_session.id}")

        # Get all documents for this session
        docs = Document.objects.filter(session=self.chat_session)

        # Verify document count
        doc_count = docs.count()
        print(f"Number of documents found: {doc_count}")

        # Rest of the function remains same
        doc_context = ""
        for doc in docs:
            if doc.content:
                doc_context += f"\nDocument '{doc.title}':\n{doc.content}\n---\n"
        print("doc_context", doc_context)

        # Get recent chat history
        messages = Message.objects.filter(session=self.chat_session).order_by(
            "-created_at"
        )[:5]
        print("messages", messages)
        history = []
        for msg in reversed(messages):
            if msg.role == "user":
                history.append(HumanMessage(content=msg.content))
            else:
                history.append(AIMessage(content=msg.content))
        print("history", history)

        return {"history": history, "documents": doc_context}

    async def process_with_llama(self, user_message, context):
        producer = ProducerAgent(llm)
        reviewer = ReviewerAgent(llm)
        max_retries = 3
        feedback = None
        final_response = None

        for attempt in range(max_retries):
            # Generate response with current context and feedback
            response = await producer.generate_response(
                context=context, question=user_message, feedback=feedback
            )

            # Review the generated response
            review = await reviewer.evaluate_response(
                response=response, context=context, question=user_message
            )

            if review["status"] == "approved":
                final_response = review["response"]
                break

            feedback = review.get("feedback", "General quality improvement needed")

        if not final_response:
            final_response = (
                "Unable to generate satisfactory response after multiple attempts"
            )

        return final_response
