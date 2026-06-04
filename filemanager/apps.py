from django.apps import AppConfig


class FilemanagerConfig(AppConfig):
    name = 'filemanager'
    def ready(self):
        # Restrict access to the Django admin site to superusers only.
        try:
            from django.contrib import admin

            def _admin_has_permission(request):
                user = getattr(request, 'user', None)
                return bool(user and user.is_active and user.is_superuser)

            admin.site.has_permission = _admin_has_permission
        except Exception:
            # avoid breaking startup if admin isn't installed/available in some contexts
            pass
