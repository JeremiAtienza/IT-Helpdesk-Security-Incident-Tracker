from django.core.management.base import BaseCommand
from filemanager.models import Category

class Command(BaseCommand):
    help = 'Seed default ticket categories and assignment mapping.'

    def handle(self, *args, **options):
        defaults = [
            {'name': 'Password Compromise', 'slug': 'password-compromise', 'is_security': False, 'default_assignee_group': 'Account Support Team'},
            {'name': 'Malware', 'slug': 'malware', 'is_security': True, 'default_assignee_group': 'Security Team'},
            {'name': 'Phishing', 'slug': 'phishing', 'is_security': True, 'default_assignee_group': 'Security Team'},
            {'name': 'Unauthorized Access', 'slug': 'unauthorized-access', 'is_security': True, 'default_assignee_group': 'Admin'},
            {'name': 'Network Attack', 'slug': 'network-attack', 'is_security': True, 'default_assignee_group': 'Network Administrator'},
            {'name': 'Data Breach', 'slug': 'data-breach', 'is_security': True, 'default_assignee_group': 'Security Team'},
        ]

        for data in defaults:
            category, created = Category.objects.get_or_create(slug=data['slug'], defaults=data)
            verb = 'Created' if created else 'Exists'
            self.stdout.write(self.style.SUCCESS(f"{verb} category: {category.name}"))
