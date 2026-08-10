import json
import asyncio
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, AIMessage
from django.conf import settings
from chat.models import ConversationRecord, Checkpoints
import logging
from dotenv import load_dotenv
import os
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.prebuilt import create_react_agent

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from chat.agentService.multiAgent import run_supervised_agents
"""
Users must be authenticated to connect
Messages are sent between the user and AI
Typing indicators still work
Error handling remains intact
"""

"""
Console message (for monitor purpose)
Connection events:
When a user connects successfully (showing username first name and user ID)
When a connection is rejected due to no authentication
The channel name for each connection

Message handling:
When messages are received (showing username first and first 100 characters)
When AI responses are being generated
The length of AI responses generated

Disconnection events:
When users disconnect (showing username first and disconnect code)

Error cases:
Model initialization failures
Message processing errors
"""

load_dotenv()
logger = logging.getLogger(__name__)

# Configure logger to show more detailed information
logging.basicConfig(level=logging.INFO)

#################################################### INITIALIZE DATABASE (ALREADY EXECUTED) ####################################################
# Global flag to track if memory tables have been set up
# _memory_tables_initialized = False 

async def initialize_memory_tables():
    """
    One-time setup of memory tables for the whole system.
    Should be called only once when the application starts.
    """
    global _memory_tables_initialized
    if not _memory_tables_initialized:
        try:
            with ConnectionPool(
                conninfo=f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
                        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
                        f"?sslmode=disable",
                max_size=20,  
                kwargs={
                    "autocommit": True,
                    "prepare_threshold": 0,
                    "row_factory": dict_row,
                }
            )as pool, pool.connection() as conn:
                memory = PostgresSaver(conn)
                memory.setup()
                _memory_tables_initialized = True
                logger.info("Memory tables initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize memory tables: {e}")
            raise
#################################################### INITIALIZE DATABASE (ALREADY EXECUTED) ####################################################

class ChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Basic runtime state
        self.llm = None
        self.user = None
        self.memory = None
        self.conn_pool = None
        self.agent = None
        self.current_thread_id = None
        self._first_messages_cache = []  # cache first few messages for title generation (best-effort)
    
    #################################################### WEB SOCKET CONNECTION & SYSTEM INITIALIZATION ####################################################
    async def connect(self):
        """
        Handle WebSocket connection
        """
        # Get the user from the scope (provided by AuthMiddlewareStack)
        self.user = self.scope["user"]
        
        # Check if user is authenticated
        if not self.user.is_authenticated:
            logger.warning(f"Rejected WebSocket connection - User not authenticated")
            await self.close()
            return
        
        logger.info(f"New WebSocket connection - User: {self.user.first_name} (ID: {self.user.id})")
        logger.info(f"Connection details - Channel: {self.channel_name}")
            
        await self.accept()
        
        # Initialize components
        try:
            # ============================================ NOT USING ============================================ 
            # Ensure memory tables are initialized (will only run once for the whole system)
            # if not _memory_tables_initialized:
            #     await initialize_memory_tables()
            # ============================================ NOT USING ============================================ 
            
            # Initialize Gemini model
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                google_api_key=os.getenv("GEMINI_API_KEY"),
                temperature=1,
                max_tokens=None,
                timeout=None,
                max_retries=2,
            )
                
            await self.send(text_data=json.dumps({
                'type': 'connection_status',
                'message': 'Connected! AI is ready to chat.',
                'status': 'connected'
            }))
        except Exception as e:
            error_msg = f"Failed to initialize components: {e}"
            logger.error(f"{error_msg} - User: {self.user.first_name} (ID: {self.user.id})")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to initialize chat components. Please try again.',
                'status': 'error'
            }))
    #################################################### WEB SOCKET CONNECTION & SYSTEM INITIALIZATION ####################################################

    #################################################### WEB SOCKET DISCONNECT ####################################################
    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection
        """
        if hasattr(self, 'user') and self.user:
            logger.info(f"WebSocket disconnected - User: {self.user.first_name} (ID: {self.user.id})")
            logger.info(f"Disconnection code: {close_code}")
        
    #################################################### WEB SOCKET DISCONNECT ####################################################

    #################################################### RECEIVE MESSAGE ####################################################
    async def receive(self, text_data):
        """
        Handle incoming WebSocket messages
        """
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type', 'chat')
            
            if message_type == 'thread_update':
                # Handle thread ID updates
                thread_id = text_data_json.get('thread_id')
                if thread_id:
                    self.current_thread_id = thread_id
                    logger.info(f"Thread ID updated to: {thread_id} for user: {self.user.first_name}")
                
                # Send confirmation back to client
                await self.send(text_data=json.dumps({
                    'type': 'thread_update_confirmation',
                    'thread_id': thread_id,
                    'status': 'success'
                }))

            elif message_type == 'chat':
                user_message = text_data_json['message']
                thread_id = text_data_json.get('thread_id')  # Get thread_id from message
                if thread_id:
                    self.current_thread_id = thread_id
                
                logger.info(f"Received message from User: {self.user.first_name} (ID: {self.user.id})")
                logger.info(f"Message content: {user_message[:100]}...")  # Show first 100 chars of message
                logger.info(f"Using thread_id: {self.current_thread_id}")
                
                # Send user message back to confirm receipt
                await self.send(text_data=json.dumps({
                    'type': 'chat_message',
                    'message': user_message,
                    'sender': 'user',
                    'sender_name': self.user.first_name,
                    'timestamp': asyncio.get_event_loop().time()
                }))
                
                # Get AI response
                await self.get_ai_response(user_message)
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid message format',
                'status': 'error'
            }))
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Error processing your message',
                'status': 'error'
            }))
    #################################################### RECEIVE MESSAGE ####################################################

    #################################################### AI GENERATE RESPONSE ####################################################
    async def get_ai_response(self, user_message):
        """
        Get response from Gemini AI model
        """
        try:
            
            # Show typing indicator before generating response
            await self.send(text_data=json.dumps({
                'type': 'typing_indicator',
                'is_typing': True
            }))
            
            logger.info(f"Getting AI response for User: {self.user.first_name} (ID: {self.user.id})")
            
            # Get AI response using LangChain

            ############################################################### AI TUTOR AGENT SECTION (replaced) ###############################################################
            # implementing database connection pool and open
            DB_URI = (
                f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
                f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}?sslmode=disable"
            )

            async with AsyncConnectionPool(
                conninfo=DB_URI,
                max_size=20,
                kwargs={
                    "autocommit": True,
                    "prepare_threshold": 0,
                    "row_factory": dict_row,
                },
            ) as pool:
                ai_message = await run_supervised_agents(user_message, self.current_thread_id, pool)

            # logger.info(f"Memory Status Inside get_ai_response: {self.memory}")
            logger.info(f"AI response generated for User: {self.user.first_name} - Length: {len(ai_message)} characters")
            
            # Hide typing indicator
            await self.send(text_data=json.dumps({
                'type': 'typing_indicator',
                'is_typing': False
            }))
            
            # Send AI response directly to the WebSocket
            await self.send(text_data=json.dumps({
                'type': 'chat_message',
                'message': ai_message,
                'sender': 'ai',
                'sender_name': 'AI Assistant',
                'timestamp': asyncio.get_event_loop().time()
            }))

            # Try generating a conversation title once we have enough context
            try:
                await self._maybe_update_conversation_title()
            except Exception as e:
                logger.warning(f"Title generation skipped due to error: {e}")
            
        except Exception as e:
            logger.error(f"Error getting AI response: {e}")
            await self.send(text_data=json.dumps({
                'type': 'typing_indicator',
                'is_typing': False
            }))
            await self.send(text_data=json.dumps({
                'type': 'chat_message',
                'message': 'Sorry, I encountered an error while processing your request.',
                'sender': 'ai',
                'sender_name': 'AI Assistant',
                'timestamp': asyncio.get_event_loop().time()
            }))
    #################################################### AI GENERATE RESPONSE ####################################################

    #################################################### TITLE GENERATION ####################################################
    async def _maybe_update_conversation_title(self):
        """Generate and persist a concise conversation title based on the first five
        messages (user + AI) for the current thread. Emits a WS event to update UI.

        Runs once when conditions are met and title is still the default.
        """
        if not self.current_thread_id:
            return

        # Fetch the conversation and ensure title needs updating
        conversation = await database_sync_to_async(self._get_conversation_by_thread)(self.current_thread_id)
        if not conversation:
            return
        if conversation.conversation_title and conversation.conversation_title != "New Chat":
            return

        # Get the latest checkpoint for this thread and extract first messages
        checkpoint = await database_sync_to_async(self._get_latest_checkpoint_for_thread)(self.current_thread_id)
        if not checkpoint:
            return

        try:
            data = json.loads(checkpoint.metadata)
        except Exception:
            return

        writes = data.get("writes")
        if not writes:
            return

        # Prefer supervisor channel as used in views.process_raw_checkpoints
        messages = []
        try:
            sup = writes.get("supervisor")
            if sup and isinstance(sup.get("messages"), list):
                for m in sup["messages"]:
                    kwargs = m.get("kwargs", {})
                    content = kwargs.get("content", "")
                    if not content:
                        continue
                    mtype = kwargs.get("type")
                    name = kwargs.get("name")
                    # Consider human and supervisor (AI) only
                    if mtype == "human" or name == "supervisor":
                        role = "User" if mtype == "human" else "AI"
                        messages.append({"role": role, "content": content})
        except Exception:
            return

        if len(messages) < 5:
            return

        # Build prompt for title
        first_five = messages[:5]
        prompt = [
            "You are to create a short, neutral chat title based on the first five messages between a student and an AI tutor.",
            "Rules:",
            "- Max 8 words",
            "- Title Case",
            "- No punctuation at the end",
            "- No quotes",
            "- Be specific to the topic",
            "Messages:",
        ]
        for msg in first_five:
            prompt.append(f"{msg['role']}: {msg['content']}")
        prompt.append("\nRespond with title only.")
        prompt_text = "\n".join(prompt)

        # Default fallback: use trimmed first user message
        fallback_title = None
        for m in first_five:
            if m["role"] == "User":
                fallback_title = m["content"].strip().split("\n")[0][:60]
                break
        if not fallback_title:
            fallback_title = "New Chat"

        # Ask LLM for a concise title
        generated_title = None
        try:
            if not self.llm:
                raise RuntimeError("LLM not initialized")
            llm_resp = await self.llm.ainvoke([HumanMessage(content=prompt_text)])
            # Some models return list/parts; normalize to string
            if hasattr(llm_resp, "content"):
                if isinstance(llm_resp.content, list):
                    generated_title = " ".join([str(x) for x in llm_resp.content if isinstance(x, str)]).strip()
                else:
                    generated_title = str(llm_resp.content).strip()
        except Exception as e:
            logger.info(f"LLM title generation failed, using fallback. Error: {e}")

        title = (generated_title or fallback_title or "New Chat").strip()
        # Final sanitize: enforce max 8 words
        words = title.split()
        if len(words) > 8:
            title = " ".join(words[:8])

        # Persist if still necessary
        if title and title != conversation.conversation_title:
            await database_sync_to_async(self._update_conversation_title)(conversation.id, title)
            # Notify client to update UI
            await self.send(text_data=json.dumps({
                'type': 'title_update',
                'thread_id': str(self.current_thread_id),
                'conversation_title': title
            }))

    # ---- Sync helpers for ORM (wrapped with database_sync_to_async) ----
    def _get_conversation_by_thread(self, thread_id):
        try:
            return ConversationRecord.objects.get(thread_id=thread_id, user=self.user)
        except ConversationRecord.DoesNotExist:
            return None

    def _get_latest_checkpoint_for_thread(self, thread_id):
        try:
            return Checkpoints.objects.filter(thread_id=str(thread_id)).last()
        except Exception:
            return None

    def _update_conversation_title(self, conversation_id, title):
        try:
            ConversationRecord.objects.filter(id=conversation_id).update(conversation_title=title)
        except Exception as e:
            logger.error(f"Failed to update conversation title: {e}")
