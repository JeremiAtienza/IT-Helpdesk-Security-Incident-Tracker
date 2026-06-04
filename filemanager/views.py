import csv
import io
import logging
from collections import Counter
from datetime import timedelta
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
    FormView,
    DetailView,
    TemplateView,
    View,
)
from django.views.generic.edit import FormMixin
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.db import models
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.db.models import Q

from ratelimit.decorators import ratelimit
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import VaultFile, IncidentTicket, Ticket, TicketAttachment, IncidentAttachment, Category, AuditLog, KnowledgeBaseArticle
from .forms import (
    VaultFileForm,
    IncidentTicketForm,
    IncidentTicketUpdateForm,
    TicketBulkCloseForm,
    CustomUserCreationForm,
    StaffCreationForm,
    TicketForm,
    TicketAttachmentForm,
    IncidentAttachmentForm,
    TicketCommentForm,
    TicketSearchForm,
    KnowledgeBaseSearchForm,
)

logger = logging.getLogger(__name__)

class FileListView(LoginRequiredMixin, ListView):
    model = VaultFile
    template_name = 'filemanager/file_list.html'
    context_object_name = 'files'

    def get_queryset(self):
        return VaultFile.objects.filter(user=self.request.user)

class FileUploadView(LoginRequiredMixin, CreateView):
    model = VaultFile
    form_class = VaultFileForm
    template_name = 'filemanager/file_upload.html'
    success_url = reverse_lazy('file-list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'registration/signup.html'
    success_url = reverse_lazy('login')

class StaffCreateView(LoginRequiredMixin, CreateView):
    """View to create staff accounts with role assignment (Admin only)"""
    model = get_user_model()
    form_class = StaffCreationForm
    template_name = 'filemanager/staff_create.html'
    success_url = reverse_lazy('admin-dashboard')

    def dispatch(self, request, *args, **kwargs):
        # Only admins can create staff accounts
        if not request.user.is_superuser and not (request.user.is_staff and request.user.groups.filter(name='Admin').exists()):
            raise PermissionDenied('Only administrators can create staff accounts')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.instance
        
        # Assign to the selected role group
        role = form.cleaned_data.get('role')
        if role:
            group = Group.objects.filter(name=role).first()
            if group:
                user.groups.add(group)
                logger.info('Staff account created: %s assigned to group: %s by %s', user.username, role, self.request.user.username)
            else:
                logger.warning('Group not found: %s', role)
        
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Staff Account'
        context['groups'] = Group.objects.filter(name__in=['IT Staff', 'Security Analyst', 'Account Support Team', 'Security Team', 'Network Administrator']).count()
        return context

class FileUpdateView(LoginRequiredMixin, UpdateView):
    model = VaultFile
    form_class = VaultFileForm
    template_name = 'filemanager/file_upload.html'
    success_url = reverse_lazy('file-list')

    def get_queryset(self):
        return VaultFile.objects.filter(user=self.request.user)

class FileDeleteView(LoginRequiredMixin, DeleteView):
    model = VaultFile
    template_name = 'filemanager/file_confirm_delete.html'
    success_url = reverse_lazy('file-list')

    def get_queryset(self):
        return VaultFile.objects.filter(user=self.request.user)

class IncidentTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentTicket
        fields = ['title', 'description', 'status', 'is_resolved']

class IncidentTicketCreateAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = IncidentTicketSerializer(data=request.data)
        if serializer.is_valid():
            ticket = serializer.save(
                reporter=request.user,
                last_updated_by=request.user,
                source='api',
            )
            logger.info('API ticket created id=%s by=%s', ticket.pk, request.user.username)
            return Response({'id': ticket.pk, 'status': 'created'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TicketListView(LoginRequiredMixin, ListView):
    model = IncidentTicket
    template_name = 'filemanager/ticket_list.html'
    context_object_name = 'tickets'
    paginate_by = 10

    def get_queryset(self):
        if self.request.user.is_staff:
            return IncidentTicket.objects.all().order_by('-created_at')
        return IncidentTicket.objects.filter(reporter=self.request.user).order_by('-created_at')


class StaffDashboardAssignedView(LoginRequiredMixin, ListView):
    """View for staff to see tickets assigned to them"""
    model = IncidentTicket
    template_name = 'filemanager/staff_assigned.html'
    context_object_name = 'assigned_tickets'
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        # Only staff can access this view
        if not request.user.is_staff:
            raise PermissionDenied('Only staff members can access assigned tickets')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # Show tickets assigned to current staff member
        return IncidentTicket.objects.filter(assignee=self.request.user).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get statistics for the dashboard
        all_assigned = IncidentTicket.objects.filter(assignee=self.request.user)
        context['total_assigned'] = all_assigned.count()
        context['open_assigned'] = all_assigned.exclude(is_resolved=True).count()
        context['resolved_assigned'] = all_assigned.filter(is_resolved=True).count()
        context['critical_assigned'] = all_assigned.filter(priority=IncidentTicket.PRIORITY_CRITICAL).count()
        return context


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'filemanager/profile.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        profile = getattr(user, 'profile', None)
        ctx['user_obj'] = user
        ctx['profile'] = profile
        return ctx


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    template_name = 'filemanager/profile_edit.html'
    form_class = None

    def get_form_class(self):
        from .forms import UserProfileForm
        return UserProfileForm

    def get_object(self, queryset=None):
        # Ensure a profile exists
        profile = getattr(self.request.user, 'profile', None)
        if not profile:
            from .models import UserProfile
            profile = UserProfile.objects.create(user=self.request.user)
        return profile

    def get_success_url(self):
        from django.urls import reverse
        return reverse('profile')

class TicketCreateView(LoginRequiredMixin, CreateView):
    model = IncidentTicket
    form_class = IncidentTicketForm
    template_name = 'filemanager/ticket_form.html'
    success_url = reverse_lazy('ticket-list')

    @method_decorator(ratelimit(key='ip', rate='10/m', block=True))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.reporter = self.request.user
        form.instance.last_updated_by = self.request.user
        form.instance.source = 'web'
        # Ensure new tickets always start in DETECTION status
        form.instance.status = IncidentTicket.NIST_STAGE_DETECTION
        logger.info('Web ticket submission by %s', self.request.user.username)
        return super().form_valid(form)

    def get_success_url(self):
        # Redirect staff/admin to dashboard to see the new ticket
        if self.request.user.is_staff:
            return reverse_lazy('admin-dashboard')
        return reverse_lazy('ticket-list')

class TicketUpdateView(LoginRequiredMixin, UpdateView):
    model = IncidentTicket
    template_name = 'filemanager/ticket_form.html'
    success_url = reverse_lazy('ticket-list')

    def get_form_class(self):
        """Use enhanced form for admins with assignee field"""
        if self.request.user.is_staff:
            return IncidentTicketUpdateForm
        return IncidentTicketForm

    def get_queryset(self):
        if self.request.user.is_staff:
            return IncidentTicket.objects.all()
        return IncidentTicket.objects.filter(reporter=self.request.user)

    def form_valid(self, form):
        form.instance.last_updated_by = self.request.user
        logger.info('Ticket updated id=%s by %s', form.instance.pk, self.request.user.username)
        return super().form_valid(form)

class TicketBulkCloseView(LoginRequiredMixin, FormView):
    template_name = 'filemanager/ticket_bulk_close.html'
    form_class = TicketBulkCloseForm
    success_url = reverse_lazy('ticket-list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied('Only IT managers may close resolved tickets')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['queryset'] = IncidentTicket.objects.filter(is_resolved=True).exclude(status=IncidentTicket.NIST_STAGE_RECOVERY)
        return kwargs

    def form_valid(self, form):
        tickets = form.cleaned_data.get('ticket_ids', [])
        for ticket in tickets:
            ticket.status = IncidentTicket.NIST_STAGE_RECOVERY
            ticket.is_resolved = True
            ticket.last_updated_by = self.request.user
            ticket.save()
            logger.info('Ticket bulk-closed id=%s by %s', ticket.pk, self.request.user.username)
        return super().form_valid(form)


class HelpTicketListView(LoginRequiredMixin, ListView):
    model = Ticket
    template_name = 'filemanager/help_ticket_list.html'
    context_object_name = 'tickets'
    paginate_by = 10

    def get_queryset(self):
        queryset = Ticket.objects.all() if self.request.user.is_staff else Ticket.objects.filter(reporter=self.request.user)
        query = self.request.GET.get('query', '').strip()
        status = self.request.GET.get('status', '')
        priority = self.request.GET.get('priority', '')
        category_id = self.request.GET.get('category', '')

        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(category__name__icontains=query)
            )
        if status:
            queryset = queryset.filter(status=status)
        if priority:
            queryset = queryset.filter(priority=priority)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_form'] = TicketSearchForm(initial={
            'query': self.request.GET.get('query', ''),
            'status': self.request.GET.get('status', ''),
            'priority': self.request.GET.get('priority', ''),
            'category': self.request.GET.get('category', ''),
        })
        ctx['categories'] = Category.objects.all()
        return ctx


class HelpTicketCreateView(LoginRequiredMixin, CreateView):
    model = Ticket
    form_class = TicketForm
    template_name = 'filemanager/help_ticket_form.html'
    success_url = reverse_lazy('help-ticket-list')

    def form_valid(self, form):
        form.instance.reporter = self.request.user
        form.instance.source = Ticket.SOURCE_WEB
        form.instance.last_updated_by = self.request.user
        form.instance.is_security_incident = bool(form.instance.category and form.instance.category.is_security)
        return super().form_valid(form)


class HelpTicketDetailView(LoginRequiredMixin, FormMixin, DetailView):
    model = Ticket
    template_name = 'filemanager/help_ticket_detail.html'
    context_object_name = 'ticket'
    form_class = TicketCommentForm

    def get_queryset(self):
        if self.request.user.is_staff:
            return Ticket.objects.all()
        return Ticket.objects.filter(reporter=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ticket = self.get_object()
        ctx['suggestion'] = ticket.get_suggestion()
        ctx['overdue'] = ticket.is_overdue
        ctx['comments'] = ticket.comments.all()
        ctx['form'] = self.get_form()
        ctx['audit_logs'] = AuditLog.objects.filter(
            Q(object_type='Ticket', object_id=ticket.pk) |
            Q(detail__icontains=f'ticket={ticket.pk}')
        ).order_by('-timestamp')[:20]
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        comment = form.save(commit=False)
        comment.ticket = self.get_object()
        comment.author = self.request.user
        comment.save()
        return HttpResponseRedirect(self.request.path_info)


class TicketExportCSVView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        queryset = Ticket.objects.all() if request.user.is_staff else Ticket.objects.filter(reporter=request.user)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="help_tickets.csv"'
        writer = csv.writer(response)
        writer.writerow(['ID', 'Title', 'Reporter', 'Assignee', 'Priority', 'Status', 'Category', 'SLA Due', 'Escalation Level', 'Created At', 'Updated At'])
        for ticket in queryset:
            writer.writerow([
                ticket.pk,
                ticket.title,
                ticket.reporter.username if ticket.reporter else '',
                ticket.assignee.username if ticket.assignee else '',
                ticket.get_priority_display(),
                ticket.get_status_display(),
                ticket.category.name if ticket.category else '',
                ticket.sla_due.isoformat() if ticket.sla_due else '',
                ticket.escalation_level,
                ticket.created_at.isoformat(),
                ticket.updated_at.isoformat(),
            ])
        return response


class TicketExportPDFView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
        except ImportError:
            return HttpResponse(
                'PDF export is unavailable because the reportlab package is not installed.',
                content_type='text/plain',
                status=503,
            )

        queryset = Ticket.objects.all() if request.user.is_staff else Ticket.objects.filter(reporter=request.user)
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        y = height - 72
        p.setFont('Helvetica-Bold', 14)
        p.drawString(72, y, 'Help Ticket Export')
        y -= 36
        p.setFont('Helvetica', 10)
        for ticket in queryset[:30]:
            p.drawString(72, y, f"#{ticket.pk} {ticket.title} ({ticket.get_status_display()})")
            y -= 14
            p.drawString(90, y, f"Priority: {ticket.get_priority_display()} | Assignee: {ticket.assignee.username if ticket.assignee else 'Unassigned'}")
            y -= 14
            p.drawString(90, y, f"Category: {ticket.category.name if ticket.category else 'None'} | SLA Due: {ticket.sla_due:%Y-%m-%d %H:%M}" if ticket.sla_due else "Category: None")
            y -= 28
            if y < 72:
                p.showPage()
                y = height - 72
        p.save()
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="help_tickets.pdf"'
        return response


class KnowledgeBaseListView(LoginRequiredMixin, ListView):
    model = KnowledgeBaseArticle
    template_name = 'filemanager/knowledgebase_list.html'
    context_object_name = 'articles'

    def get_queryset(self):
        queryset = KnowledgeBaseArticle.objects.all()
        query = self.request.GET.get('query')
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(content__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_form'] = KnowledgeBaseSearchForm(initial={'query': self.request.GET.get('query', '')})
        return ctx


class KnowledgeBaseDetailView(LoginRequiredMixin, DetailView):
    model = KnowledgeBaseArticle
    template_name = 'filemanager/knowledgebase_detail.html'
    context_object_name = 'article'

    def get_queryset(self):
        return KnowledgeBaseArticle.objects.all()


class AttachmentUploadView(LoginRequiredMixin, CreateView):
    model = TicketAttachment
    form_class = TicketAttachmentForm
    template_name = 'filemanager/attachment_upload.html'

    def form_valid(self, form):
        ticket_id = self.kwargs.get('pk')
        ticket = get_object_or_404(Ticket, pk=ticket_id)
        form.instance.ticket = ticket
        form.instance.uploaded_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('help-ticket-detail', args=[self.object.ticket.pk])


class IncidentAttachmentUploadView(LoginRequiredMixin, CreateView):
    model = IncidentAttachment
    form_class = IncidentAttachmentForm
    template_name = 'filemanager/attachment_upload.html'

    def form_valid(self, form):
        incident_id = self.kwargs.get('pk')
        incident = get_object_or_404(IncidentTicket, pk=incident_id)
        form.instance.ticket = incident
        form.instance.uploaded_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('incident-detail', args=[self.object.ticket.pk])


class IncidentDetailView(LoginRequiredMixin, DetailView):
    model = IncidentTicket
    template_name = 'filemanager/incident_detail.html'
    context_object_name = 'incident'

    def get_queryset(self):
        if self.request.user.is_staff:
            return IncidentTicket.objects.all()
        return IncidentTicket.objects.filter(reporter=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        incident = self.get_object()
        ctx['events'] = incident.events.all()
        ctx['attachments'] = incident.incident_attachments.all()
        return ctx


class AdminDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'filemanager/admin_dashboard.html'

    def get(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return self.handle_no_permission()

        try:
            return super().get(request, *args, **kwargs)
        except Exception:
            logger.exception('Admin dashboard rendering error')
            import traceback
            tb = traceback.format_exc()
            logger.error('ADMIN_DASHBOARD_TRACEBACK:\n%s', tb)
            try:
                print('ADMIN_DASHBOARD_TRACEBACK:\n' + tb, flush=True)
            except Exception:
                pass

            context = self.get_context_data(error='Unable to load dashboard data. Please verify Render logs and database settings.')
            return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            open_statuses = [IncidentTicket.NIST_STAGE_DETECTION, IncidentTicket.NIST_STAGE_CONTAINMENT]
            resolved_statuses = [IncidentTicket.NIST_STAGE_RECOVERY]
            tickets = IncidentTicket.objects.all()
            help_open_statuses = [Ticket.STATUS_PENDING, Ticket.STATUS_IN_PROGRESS]
            help_resolved_statuses = [Ticket.STATUS_RESOLVED, Ticket.STATUS_CLOSED]
            help_tickets = Ticket.objects.all()

            open_count = tickets.filter(status__in=open_statuses).count() + help_tickets.filter(status__in=help_open_statuses).count()
            resolved_count = tickets.filter(status__in=resolved_statuses).count() + help_tickets.filter(status__in=help_resolved_statuses).count()
            recent_count = tickets.filter(created_at__gte=timezone.now() - timedelta(days=1)).count() + help_tickets.filter(created_at__gte=timezone.now() - timedelta(days=1)).count()
            security_count = tickets.filter(is_security_incident=True).count() + help_tickets.filter(is_security_incident=True).count()
            stale_count = tickets.filter(status__in=open_statuses, updated_at__lt=timezone.now() - timedelta(hours=72)).count() + help_tickets.filter(status__in=help_open_statuses, updated_at__lt=timezone.now() - timedelta(hours=72)).count()

            ctx['open_tickets'] = open_count
            ctx['resolved_tickets'] = resolved_count
            ctx['recent_tickets'] = recent_count
            ctx['security_incidents'] = security_count
            ctx['stale_tickets'] = stale_count

            resolved = tickets.filter(status__in=resolved_statuses)
            help_resolved = help_tickets.filter(status__in=help_resolved_statuses)
            total = 0
            count = 0
            for t in list(resolved) + list(help_resolved):
                if t.updated_at and t.created_at:
                    total += (t.updated_at - t.created_at).total_seconds()
                    count += 1
            ctx['avg_resolution_hours'] = (total / count / 3600) if count else None

            incident_live = list(tickets.filter(status__in=open_statuses).order_by('-created_at')[:10])
            help_live = list(help_tickets.filter(status__in=help_open_statuses).order_by('-created_at')[:10])
            combined_live = sorted(incident_live + help_live, key=lambda ticket: ticket.created_at, reverse=True)[:10]
            ctx['live_tickets'] = combined_live

            status_counter = Counter()
            for item in tickets.values('status').annotate(count=models.Count('id')):
                status_counter[item['status']] += item['count']
            for item in help_tickets.values('status').annotate(count=models.Count('id')):
                status_counter[item['status']] += item['count']
            ctx['status_counts'] = [{'status': status, 'count': count} for status, count in status_counter.most_common()]

            source_counter = Counter()
            for item in tickets.values('source').annotate(count=models.Count('id')):
                source_counter[item['source']] += item['count']
            for item in help_tickets.values('source').annotate(count=models.Count('id')):
                source_counter[item['source']] += item['count']
            ctx['source_counts'] = [{'source': source, 'count': count} for source, count in source_counter.most_common()][:10]

            category_counter = Counter()
            for item in tickets.values('category__name').annotate(count=models.Count('id')):
                if item['category__name']:
                    category_counter[item['category__name']] += item['count']
            for item in help_tickets.values('category__name').annotate(count=models.Count('id')):
                if item['category__name']:
                    category_counter[item['category__name']] += item['count']
            ctx['top_categories'] = [
                (Category.objects.filter(name=name).first(), count)
                for name, count in category_counter.most_common(10)
            ]
            ctx['status_choices'] = IncidentTicket.STATUS_CHOICES
            ctx['staff_users'] = get_user_model().objects.filter(is_staff=True, is_active=True).order_by('username')
            
            # Staff workload summary
            staff_workload = []
            for user in ctx['staff_users']:
                total_assigned = IncidentTicket.objects.filter(assignee=user).count()
                unresolved_assigned = IncidentTicket.objects.filter(assignee=user, is_resolved=False).count()
                if total_assigned > 0:
                    staff_workload.append((user, total_assigned, unresolved_assigned))
            ctx['staff_workload'] = staff_workload
            
            ctx['recent_audit_events'] = AuditLog.objects.order_by('-timestamp')[:20]
        except Exception:
            logger.exception('Admin dashboard context error')
            import traceback
            tb = traceback.format_exc()
            logger.error('ADMIN_DASHBOARD_TRACEBACK:\n%s', tb)
            try:
                print('ADMIN_DASHBOARD_TRACEBACK:\n' + tb, flush=True)
            except Exception:
                pass

            ctx['error'] = 'Unable to load dashboard data at this time. Check Render environment variables and database configuration.'
            if self.request.user.is_staff:
                ctx['error_details'] = tb
            else:
                ctx['error_details'] = None
            # provide safe empty defaults so template renders
            ctx['open_tickets'] = 0
            ctx['resolved_tickets'] = 0
            ctx['recent_tickets'] = 0
            ctx['security_incidents'] = 0
            ctx['stale_tickets'] = 0
            ctx['avg_resolution_hours'] = None
            ctx['live_tickets'] = []
            ctx['status_counts'] = []
            ctx['source_counts'] = []
            ctx['top_categories'] = []
            ctx['recent_audit_events'] = []
        return ctx


class AdminTicketActionView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        """Redirect GET requests back to the admin dashboard"""
        if not request.user.is_staff:
            return self.handle_no_permission()
        return HttpResponseRedirect(reverse('admin-dashboard'))

    def post(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return self.handle_no_permission()

        ticket_type = request.POST.get('ticket_type')
        if ticket_type == 'ticket':
            ticket = get_object_or_404(Ticket, pk=kwargs.get('pk'))
            valid_statuses = {choice[0] for choice in Ticket.STATUS_CHOICES}
        else:
            ticket = get_object_or_404(IncidentTicket, pk=kwargs.get('pk'))
            valid_statuses = {choice[0] for choice in IncidentTicket.STATUS_CHOICES}

        status_value = request.POST.get('status')
        assignee_id = request.POST.get('assignee')

        if status_value in valid_statuses:
            ticket.status = status_value

        previous_assignee = ticket.assignee

        if assignee_id:
            user = get_user_model().objects.filter(pk=assignee_id, is_active=True).first()
            ticket.assignee = user
        else:
            ticket.assignee = None

        ticket.last_updated_by = request.user
        ticket.save()

        # If assignee changed, create an audit entry is handled by post_save signal.
        # Additionally, notify the newly assigned user by email (if available).
        new_assignee = ticket.assignee
        if new_assignee and (not previous_assignee or previous_assignee.pk != new_assignee.pk):
            try:
                from django.core.mail import send_mail
                subject = f"You have been assigned ticket #{ticket.pk}: {ticket.title}"
                message = f"Hello {new_assignee.get_full_name() or new_assignee.username},\n\nYou have been assigned to the ticket:\n\nTitle: {ticket.title}\nPriority: {ticket.get_priority_display()}\nStatus: {ticket.get_status_display()}\n\nPlease review it in the dashboard: {request.build_absolute_uri(reverse('ticket-edit', args=[ticket.pk]))}\n\nThanks."
                if new_assignee.email:
                    send_mail(subject, message, getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'), [new_assignee.email], fail_silently=True)
            except Exception:
                logger.exception('Failed to notify new assignee via email for ticket id=%s', ticket.pk)

        return HttpResponseRedirect(reverse('admin-dashboard'))
