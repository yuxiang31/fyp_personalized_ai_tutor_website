from django.db import models
from django.conf import settings
import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver


class StudyMaterials(models.Model):
    """
    Model to store study plan information
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # uuid.uuid4 - used to generate a random UUID (random ID number e.g. c303282d-f2e6-46ca-a04a-35d3d873712d)
    # editable=False - this field won't appear in forms by default
    study_plan = models.TextField()
    
    class Meta:
        db_table = 'study_materials' # actual table name in database
        verbose_name = 'Study Material'
        verbose_name_plural = 'Study Materials'
    
    def __str__(self): 
        # make model instance more readable
        return f"Study Material {self.id}"


class StudyMaterialFiles(models.Model):
    """
    Model to store files related to study materials
    """
    id = models.AutoField(primary_key=True)
    study_material = models.ForeignKey(
        StudyMaterials, # links each file to one StudyMaterials instance
        on_delete=models.CASCADE, # if a studyMaterials record is deleted, its related files will also be deleted
        related_name='files' # allows reverse access from StudyMaterials
    )
    file_path = models.CharField(max_length=500)
    
    class Meta:
        db_table = 'study_material_files'
        verbose_name = 'Study Material File'
        verbose_name_plural = 'Study Material Files'
    
    def __str__(self):
        return f"File: {self.file_path}"


class ConversationRecord(models.Model):
    """
    Model to store conversation records
    """
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, # links the conversation to a user
        on_delete=models.CASCADE, # if a user is deleted, their conversations are also deleted
        related_name='conversations'
    )
    thread_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False) # unique=True - to guarantee no two conversations have the same thread ID
    conversation_title = models.CharField(max_length=255)
    study_material = models.ForeignKey(
        StudyMaterials,
        on_delete=models.SET_NULL,
        null=True, # makes the field optional
        blank=True,
        related_name='conversations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'conversation_record'
        verbose_name = 'Conversation Record'
        verbose_name_plural = 'Conversation Records'
        ordering = ['-updated_at'] # default ordering is by updated_at in descending order - newest conversations show up first
    
    def __str__(self):
        return f"{self.conversation_title} - {self.user}"
    
    def get_checkpoints(self):
        """
        Get all checkpoints for this conversation using thread_id
        """
        return Checkpoints.objects.filter(thread_id=self.thread_id)


class Checkpoints(models.Model):
    """
    LangChain predefined checkpoints table - DO NOT MODIFY
    This table structure is managed by LangChain.
    
    Note: In LangChain, thread_id is not unique as there can be multiple 
    checkpoints per thread. The actual primary key would likely be a 
    combination of thread_id + checkpoint_id, but since this is managed 
    by LangChain, we define it as they expect.
    """
    # LangChain typically uses a composite key or auto-generated ID
    # For Django compatibility, we'll assume there's an auto ID field
    id = models.AutoField(primary_key=True)
    thread_id = models.CharField(max_length=255, db_index=True)
    # checkpoint_ns = models.CharField(max_length=255) # <-- Implemented by 21/8, haven't migrate
    checkpoint_id = models.CharField(max_length=255)
    parent_checkpoint_id = models.CharField(
        max_length=255, 
        null=True, 
        blank=True
    )
    type = models.CharField(max_length=50)
    checkpoint = models.TextField()  # LangChain checkpoint data
    metadata = models.TextField()  # LangChain metadata
    
    class Meta:
        db_table = 'checkpoints'
        managed = False  # Tell Django not to manage this table
        verbose_name = 'Checkpoint'
        verbose_name_plural = 'Checkpoints'
        # Add composite unique constraint if needed
        # unique_together = [['thread_id', 'checkpoint_id']]
    
    def __str__(self):
        return f"Checkpoint {self.checkpoint_id} for thread {self.thread_id}"
    
    @property
    def conversation_record(self):
        """
        Get the related conversation record by matching thread_id
        """
        try:
            return ConversationRecord.objects.get(thread_id=self.thread_id)
        except ConversationRecord.DoesNotExist:
            return None


# --- Signals ---
@receiver(post_save, sender=StudyMaterials)
def attach_material_to_conversation(sender, instance: StudyMaterials, created: bool, **kwargs):
    """When a StudyMaterials is created, auto-attach it to the most relevant
    ConversationRecord by:
    1) Trying to use the latest Checkpoints.thread_id to find a matching conversation.
    2) Falling back to the most recently created/updated conversation if no checkpoint found.

    This runs best-effort and should never raise to avoid breaking the request.
    """
    if not created:
        return

    try:
        # Prefer linking by the most recent LangGraph checkpoint's thread
        latest_cp = None
        try:
            latest_cp = Checkpoints.objects.order_by('-id').first()
        except Exception:
            # Table may not exist or be empty; ignore
            latest_cp = None

        conversation = None
        if latest_cp and latest_cp.thread_id:
            try:
                conversation = ConversationRecord.objects.filter(thread_id=latest_cp.thread_id).first()
            except Exception:
                conversation = None

        # Fallback: pick the most recently updated conversation
        if conversation is None:
            try:
                conversation = ConversationRecord.objects.order_by('-updated_at').first()
            except Exception:
                conversation = None

        if conversation is not None:
            # Only update if it's different or empty
            if conversation.study_material_id != instance.id:
                conversation.study_material = instance
                # Also bump updated_at to reflect linkage
                conversation.save(update_fields=['study_material', 'updated_at'])
    except Exception:
        # Best-effort: never block creation if anything goes wrong
        pass