import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from filemanager.models import Category, KnowledgeBaseArticle
from django.contrib.auth.models import Group

print('=== SEED DATA VERIFICATION ===')
print(f'Categories: {Category.objects.count()}')
print(f'Groups: {Group.objects.count()}')
print(f'KB Articles: {KnowledgeBaseArticle.objects.count()}')

print('\n--- Categories ---')
for c in Category.objects.all():
    print(f'  • {c.name} (security={c.is_security}, group={c.default_assignee_group})')

print('\n--- Groups ---')
for g in Group.objects.all():
    print(f'  • {g.name}')

print('\n--- KB Articles ---')
for kb in KnowledgeBaseArticle.objects.all():
    print(f'  • {kb.title} (slug: {kb.slug})')
