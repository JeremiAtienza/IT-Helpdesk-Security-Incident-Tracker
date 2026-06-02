from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from filemanager.models import Ticket, KnowledgeBaseArticle

class Command(BaseCommand):
    help = 'Initialize default RBAC groups and permissions for the ticketing system.'

    def handle(self, *args, **options):
        groups = {
            'Employee': {
                'ticket_perms': ['add_ticket', 'view_ticket'],
                'kb_perms': ['view_knowledgebasearticle'],
            },
            'IT Staff': {
                'ticket_perms': ['change_ticket', 'view_ticket'],
                'kb_perms': ['view_knowledgebasearticle', 'add_knowledgebasearticle'],
            },
            'Security Analyst': {
                'ticket_perms': ['change_ticket', 'view_ticket', 'delete_ticket'],
                'kb_perms': ['view_knowledgebasearticle', 'add_knowledgebasearticle'],
            },
            'Account Support Team': {
                'ticket_perms': ['change_ticket', 'view_ticket'],
                'kb_perms': ['view_knowledgebasearticle'],
            },
            'Security Team': {
                'ticket_perms': ['change_ticket', 'view_ticket'],
                'kb_perms': ['view_knowledgebasearticle'],
            },
            'Network Administrator': {
                'ticket_perms': ['change_ticket', 'view_ticket'],
                'kb_perms': ['view_knowledgebasearticle'],
            },
            'Admin': {
                'ticket_perms': ['add_ticket', 'change_ticket', 'delete_ticket', 'view_ticket'],
                'kb_perms': ['add_knowledgebasearticle', 'change_knowledgebasearticle', 'delete_knowledgebasearticle', 'view_knowledgebasearticle'],
            },
        }

        ticket_ct = ContentType.objects.get_for_model(Ticket)
        kb_ct = ContentType.objects.get_for_model(KnowledgeBaseArticle)

        for name, perms in groups.items():
            grp, created = Group.objects.get_or_create(name=name)
            self.stdout.write(self.style.SUCCESS(f"Group {'created' if created else 'exists'}: {name}"))
            # Ticket perms
            for codename in perms.get('ticket_perms', []):
                try:
                    perm = Permission.objects.get(content_type=ticket_ct, codename=codename)
                    grp.permissions.add(perm)
                except Permission.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Permission not found: {codename}"))
            # KB perms
            for codename in perms.get('kb_perms', []):
                try:
                    perm = Permission.objects.get(content_type=kb_ct, codename=codename)
                    grp.permissions.add(perm)
                except Permission.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Permission not found: {codename}"))

        self.stdout.write(self.style.SUCCESS('RBAC initialization complete.'))
