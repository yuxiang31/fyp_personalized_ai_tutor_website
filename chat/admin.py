from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import StudyMaterials, StudyMaterialFiles, ConversationRecord, Checkpoints

User = get_user_model()


class StudyMaterialFilesInline(admin.TabularInline):
    """
    Inline admin for Study Material Files
    """
    model = StudyMaterialFiles
    extra = 1
    fields = ('file_path',)


@admin.register(StudyMaterials)
class StudyMaterialsAdmin(admin.ModelAdmin):
    """
    Admin for Study Materials
    """
    list_display = ('id', 'study_plan_preview', 'file_count')
    search_fields = ('study_plan',)  # Required for autocomplete
    readonly_fields = ('id',)
    inlines = [StudyMaterialFilesInline]
    
    def study_plan_preview(self, obj):
        """Show first 50 characters of study plan"""
        return obj.study_plan[:50] + "..." if len(obj.study_plan) > 50 else obj.study_plan
    study_plan_preview.short_description = 'Study Plan Preview'
    
    def file_count(self, obj):
        """Show number of files associated with this study material"""
        return obj.files.count()
    file_count.short_description = 'Files Count'


@admin.register(StudyMaterialFiles)
class StudyMaterialFilesAdmin(admin.ModelAdmin):
    """
    Admin for Study Material Files
    """
    list_display = ('id', 'study_material', 'file_path')
    list_filter = ('study_material',)
    search_fields = ('file_path', 'study_material__study_plan')
    raw_id_fields = ('study_material',)  # Alternative to autocomplete


@admin.register(ConversationRecord)
class ConversationRecordAdmin(admin.ModelAdmin):
    """
    Admin for Conversation Records
    """
    list_display = ('conversation_title', 'user', 'thread_id', 'study_material', 'checkpoints_count', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at', 'study_material')
    search_fields = ('conversation_title', 'user__email', 'user__first_name', 'user__last_name', 'thread_id')
    readonly_fields = ('id', 'thread_id', 'created_at', 'updated_at', 'checkpoints_count')
    # Remove autocomplete_fields temporarily or make sure User admin has search_fields
    raw_id_fields = ('user', 'study_material')  # Alternative to autocomplete
    date_hierarchy = 'created_at'
    
    def checkpoints_count(self, obj):
        """Show number of checkpoints for this conversation"""
        return obj.get_checkpoints().count()
    checkpoints_count.short_description = 'Checkpoints Count'
    
    fieldsets = (
        (None, {
            'fields': ('conversation_title', 'user', 'study_material')
        }),
        ('System Fields', {
            'fields': ('id', 'thread_id'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Checkpoints)
class CheckpointsAdmin(admin.ModelAdmin):
    """
    Admin for Checkpoints (Read-only since managed by LangGraph)
    """
    list_display = ('checkpoint_id', 'thread_id', 'get_conversation_title', 'parent_checkpoint_id', 'type')
    list_filter = ('type',)
    search_fields = ('thread_id', 'checkpoint_id', 'parent_checkpoint_id')
    readonly_fields = ('id', 'thread_id', 'checkpoint_id', 'parent_checkpoint_id', 'type', 'checkpoint', 'metadata', 'get_conversation_title')
    
    def get_conversation_title(self, obj):
        """Show the conversation title for this checkpoint"""
        conv = obj.conversation_record
        return conv.conversation_title if conv else "No conversation found"
    get_conversation_title.short_description = 'Conversation'
    
    # Make all fields read-only since this is managed by LangGraph
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    fieldsets = (
        ('Checkpoint Information', {
            'fields': ('id', 'thread_id', 'checkpoint_id', 'parent_checkpoint_id', 'type', 'get_conversation_title')
        }),
        ('Checkpoint Data', {
            'fields': ('checkpoint', 'metadata'),
            'classes': ('collapse',)
        }),
    )

