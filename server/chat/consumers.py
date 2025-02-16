import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from langchain.prompts import PromptTemplate
from langchain.schema import AIMessage, HumanMessage
from langchain_ollama import OllamaLLM

from .models import ChatSession, Message
from documents.models import Document

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

            # Extract clean session_id
            session_id = query_params.get("session_id", "").split("?")[
                0
            ]  # Remove any trailing query params
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

            # Send typing indicator
            await self.send(json.dumps({"type": "typing", "isTyping": True}))

            try:
                # Process message and get response
                response = await self.process_with_llama(
                    user_message, await self.get_context()
                )

                # Save messages after successful processing
                await self.save_message("user", user_message)
                await self.save_message("assistant", response)

                # Send response back to WebSocket
                await self.send(json.dumps({"type": "message", "message": response}))
            except Exception as e:
                await self.send(
                    json.dumps({"type": "error", "message": f"Error: {str(e)}"})
                )
            finally:
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
        template = """
        <|im_start|>system
        You are a helpful AI assistant. Below is the content from uploaded documents and our conversation history.
        
        DOCUMENTS CONTENT:
        {documents}

        CONVERSATION HISTORY:
        {history}

        INSTRUCTIONS:
        1. If the question is about document content, provide answers based on the documents above
        2. If the question is about chat history, refer to the conversation history
        3. If information cannot be found in either documents or history, clearly state that
        4. Keep responses accurate, clear and concise
        5. Always maintain context from both documents and previous messages

        <|im_end|>
        
        <|im_start|>user
        {question}
        <|im_end|>
        
        <|im_start|>assistant
        """

        # Format context with better structure
        history_text = "\n".join(
            [
                f"{msg.__class__.__name__.replace('Message', '')}: {msg.content}"
                for msg in context["history"]
            ]
        )

        # Ensure document context is properly formatted
        doc_context = (
            context["documents"]
            if context["documents"]
            else "No documents uploaded yet."
        )

        formatted_prompt = PromptTemplate(
            input_variables=["documents", "history", "question"], template=template
        ).format(documents=doc_context, history=history_text, question=user_message)
        print("formatted_prompt", formatted_prompt)

        # Adjust LLM parameters for better responses
        llm.stop = [
            "User:",
            "Assistant:",
            "<|im_start|>",
            "<|im_end|>",
        ]  # Prevent template leakage

        # Get response from LLM
        response = await llm.agenerate([formatted_prompt])
        return response.generations[0][0].text.strip()
