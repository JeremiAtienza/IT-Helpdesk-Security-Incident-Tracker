from django.contrib import admin
from .models import VaultFile, IncidentTicket, Category, Ticket, TicketAttachment, AuditLog, KnowledgeBaseArticle


@admin.register(VaultFile)
class VaultFileAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'uploaded_at']
    search_fields = ['title', 'user__username']


@admin.register(IncidentTicket)
class IncidentTicketAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'reporter', 'created_at']
    search_fields = ['title', 'reporter__username']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_security', 'default_assignee_group']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['title', 'priority', 'status', 'category', 'assignee', 'created_at', 'is_security_incident']
    list_filter = ['priority', 'status', 'category', 'is_security_incident']
    search_fields = ['title', 'description', 'reporter__username', 'assignee__username']


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'uploaded_by', 'uploaded_at']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'actor', 'action', 'object_type', 'object_id']
    search_fields = ['actor__username', 'action', 'detail']
    readonly_fields = ['timestamp']


@admin.register(KnowledgeBaseArticle)
class KnowledgeBaseArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_by', 'created_at']
    search_fields = ['title', 'content']
    prepopulated_fields = {'slug': ('title',)}
