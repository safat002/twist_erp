from django.contrib import admin
from .models import AIConfiguration, AITrainingExample

@admin.register(AIConfiguration)
class AIConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'ai_assistant_enabled')

@admin.register(AITrainingExample)
class AITrainingExampleAdmin(admin.ModelAdmin):
    list_display = ('prompt', 'status')
    list_filter = ('status',)
    search_fields = ('prompt',)