from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.conf import settings
from .models import ConversationRecord, Checkpoints, StudyMaterials, StudyMaterialFiles
import logging
import json
import os

logger = logging.getLogger(__name__)

# Configure logger to show more detailed information
logging.basicConfig(level=logging.INFO)

@login_required
def index(request):
    """
    Main chat interface view - checks for existing conversations or creates a new one if none exist
    """
    # Get user's conversations, ordered by most recent first
    conversations = ConversationRecord.objects.filter(user=request.user).order_by('-updated_at')
    
    # Create a new conversation only if no conversations exist
    if not conversations.exists():
        conversation = create_new_Conversation_Object(request)
        # Refresh the conversations queryset
        conversations = ConversationRecord.objects.filter(user=request.user).order_by('-updated_at')
    else:
        # Get the latest conversation
        conversation = conversations.first()
    
    # History will be fetched client-side via /chat/conversation/<thread_id>
    logger.info(f"Current Conversation & Thread_ID from views.py: {conversation.thread_id}")
    context = {
        'user': request.user,
        'conversations': conversations,
        'current_conversation': conversation,
    }
    return render(request, 'chat/index.html', context)

@login_required
def create_conversation(request):
    """
    Create a new conversation and return its details
    """
    if request.method == 'POST':
        try:
            # Create new conversation
            conversation = create_new_Conversation_Object(request)
            
            return JsonResponse({
                'success': True,
                'thread_id': str(conversation.thread_id),
                'conversation_title': conversation.conversation_title,
                'created_at': conversation.created_at.isoformat()
            })

        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to create conversation'
            }, status=500)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def get_conversation_history(request, thread_id):
    """
    Fetch conversation history for a specific thread
    """
    if request.method == 'GET':
        try:
            # Verify the conversation belongs to the user
            conversation = ConversationRecord.objects.get(thread_id=thread_id, user=request.user)
            
            # Get checkpoints for this conversation
            checkpoints = Checkpoints.objects.filter(thread_id=str(thread_id)).last()
            logger.info(f"Checkpoints: {checkpoints}")
            
            # Get messages for this conversation (you'll need to implement this based on your Message model)
            messages = []  # Replace with actual message fetching logic
            
            return JsonResponse({
                'success': True,
                'conversation': {
                    'thread_id': str(conversation.thread_id),
                    'title': conversation.conversation_title,
                    'checkpoints': process_raw_checkpoints(checkpoints),
                }
            })

        except ConversationRecord.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Conversation not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error fetching conversation history: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to fetch conversation history'
            }, status=500)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def delete_conversation(request, thread_id):
    """
    Delete a conversation (related checkpoints, and study materials) owned by the current user.
    Accepts POST only and returns JSON.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        conversation = ConversationRecord.objects.get(thread_id=thread_id, user=request.user)

        # Cache related study material before we delete the conversation
        study_material = conversation.study_material

        # Delete checkpoints for this thread if they exist (thread_id stored as str)
        try:
            Checkpoints.objects.filter(thread_id=str(thread_id)).delete()
        except Exception as e:
            # Log but continue with conversation delete to avoid orphan entries
            logger.warning(f"Failed deleting checkpoints for thread {thread_id}: {e}")

        # If there's a study material linked and it's not used by other conversations,
        # delete it (related StudyMaterialFiles rows will cascade). Also try to remove files from disk.
        if study_material is not None:
            try:
                is_shared = study_material.conversations.exclude(pk=conversation.pk).exists()
            except Exception:
                # If anything odd happens, assume it's not shared and proceed
                is_shared = False

            if is_shared:
                logger.info(
                    f"Study material {study_material.id} is linked to other conversations; skipping delete."
                )
            else:
                # Attempt to delete files from disk first (best-effort)
                try:
                    for f in study_material.files.all():
                        file_path = f.file_path or ""
                        if not file_path:
                            continue
                        # Build absolute path if needed
                        abs_path = file_path if os.path.isabs(file_path) else os.path.join(
                            settings.BASE_DIR, file_path.lstrip('/\\')
                        )
                        try:
                            if os.path.exists(abs_path):
                                os.remove(abs_path)
                        except Exception as fe:
                            logger.warning(
                                f"Failed to remove study material file '{abs_path}': {fe}"
                            )
                except Exception as e:
                    logger.warning(
                        f"Failed while iterating/removing files for study material {study_material.id}: {e}"
                    )

                # Delete the StudyMaterials row (will cascade delete StudyMaterialFiles rows)
                try:
                    study_material.delete()
                except Exception as e:
                    logger.warning(
                        f"Failed deleting study material {study_material.id} for thread {thread_id}: {e}"
                    )

        conversation.delete()

        return JsonResponse({'success': True})
    except ConversationRecord.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Conversation not found'}, status=404)
    except Exception as e:
        logger.error(f"Error deleting conversation {thread_id}: {e}")
        return JsonResponse({'success': False, 'error': 'Failed to delete conversation'}, status=500)

def logout_view(request):
    logout(request)
    return redirect("/")

# ALTER TABLE checkpoints
# ADD COLUMN IF NOT EXISTS id SERIAL;

def process_raw_checkpoints(checkpoints):
    """
    Process checkpoints from langgraph to usable format
    """
    normalized_checkpoints = []
    # for checkpoint in checkpoints:
    #     json_format_metadata = json.loads(checkpoint.metadata) # -> convert string json format to dictonary (json format)
    #     messages = json_format_metadata["writes"]
    #     if messages == None:
    #         pass
    #     else:
    #         # logger.info(f"messages start access: {messages['__start__']}")
    #         if "__start__" in messages:
    #             messages_start = messages["__start__"]
    #             message_kwargs = messages_start["messages"][0]["kwargs"]
    #         elif "supervisor" in messages:
    #             messages_start = messages["supervisor"]
    #             message_kwargs = messages_start["messages"][0]["kwargs"]
    #         else:
    #             messages_agent = messages["agent"]
    #             message_kwargs = messages_agent["messages"][0]["kwargs"]

    #         normalized_checkpoints.append({
    #             "type": message_kwargs["type"],
    #             "old_message": message_kwargs["content"],
    #         })
    if checkpoints == None:
        return normalized_checkpoints
    else:
        json_format_metadata = json.loads(checkpoints.metadata)
        messages_writes_section = json_format_metadata["writes"]
        # messages_retreive = None
        if messages_writes_section == None:
            pass
        else:
            list_of_messages = messages_writes_section["supervisor"]["messages"]
            for message in list_of_messages:
                message_kwargs = message["kwargs"]
                if len(message_kwargs["content"]) != 0 :
                    if message_kwargs["type"] == "human" or message_kwargs["name"] == "supervisor":
                        normalized_checkpoints.append({
                            "type": message_kwargs["type"],
                            "old_message": message_kwargs["content"],
                        })
    
        # if "__start__" in messages:
        #     messages_retreive = messages["__start__"]
        # elif "agent" in messages:
        #     messages_retreive = messages["agent"]

        # list_of_messages = messages_retreive["messages"]
        # logger.info(f"list_of_messages: {list_of_messages}")
        # for message in list_of_messages:
        #     message_kwargs = message["kwargs"]
        #     if message_kwargs["name"] == "supervisor" or message_kwargs["type"] == "human":
        #         normalized_checkpoints.append({
        #             "type": message_kwargs["type"],
        #             "old_message": message_kwargs["content"],
        #         })
                    
    return normalized_checkpoints

def create_new_Conversation_Object(request):
    """
    Used to create a new conversation object by passing request information
    """
    conversation = ConversationRecord.objects.create(
                user=request.user,
                conversation_title="New Chat",
            )
    return conversation