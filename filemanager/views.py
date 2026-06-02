import csv
import io
import logging
from datetime import timedelta
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

from .models import VaultFile, IncidentTicket, Ticket, TicketAttachment, Category, AuditLog, KnowledgeBaseArticle
from .forms import (
    VaultFileForm,
    IncidentTicketForm,
    IncidentTicketUpdateForm,
    TicketBulkCloseForm,
    CustomUserCreationForm,
    TicketForm,
    TicketAttachmentForm,
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

    def get_queryset(self):
        if self.request.user.is_staff:
            return IncidentTicket.objects.all()
        return IncidentTicket.objects.filter(reporter=self.request.user)

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
        logger.info('Web ticket submission by %s', self.request.user.username)
        return super().form_valid(form)

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
        return queryset

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
            ctx['open_tickets'] = IncidentTicket.objects.filter(is_resolved=False).count()
            ctx['resolved_tickets'] = IncidentTicket.objects.filter(is_resolved=True).count()
            ctx['recent_tickets'] = IncidentTicket.objects.filter(created_at__gte=timezone.now() - timedelta(days=1)).count()
            ctx['security_incidents'] = IncidentTicket.objects.filter(is_security_incident=True).count()
            ctx['stale_tickets'] = IncidentTicket.objects.filter(is_resolved=False, updated_at__lt=timezone.now() - timedelta(hours=72)).count()
            resolved = IncidentTicket.objects.filter(is_resolved=True)
            total = 0
            count = 0
            for t in resolved:
                if t.updated_at and t.created_at:
                    total += (t.updated_at - t.created_at).total_seconds()
                    count += 1
            ctx['avg_resolution_hours'] = (total / count / 3600) if count else None
            ctx['live_tickets'] = IncidentTicket.objects.filter(is_resolved=False).order_by('-created_at')[:10]
            ctx['status_counts'] = IncidentTicket.objects.values('status').annotate(count=models.Count('id')).order_by('-count')
            ctx['source_counts'] = IncidentTicket.objects.values('source').annotate(count=models.Count('id')).order_by('-count')[:10]
            ctx['top_categories'] = [
                (Category.objects.filter(name=item['category__name']).first(), item['count'])
                for item in IncidentTicket.objects.values('category__name').annotate(count=models.Count('id')).order_by('-count')[:10]
                if item['category__name']
            ]
            ctx['status_choices'] = IncidentTicket.STATUS_CHOICES
            ctx['staff_users'] = get_user_model().objects.filter(is_staff=True, is_active=True).order_by('username')
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
    def post(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return self.handle_no_permission()

        ticket = get_object_or_404(IncidentTicket, pk=kwargs.get('pk'))
        status_value = request.POST.get('status')
        assignee_id = request.POST.get('assignee')
        resolved_value = request.POST.get('is_resolved')

        valid_statuses = {choice[0] for choice in IncidentTicket.STATUS_CHOICES}
        if status_value in valid_statuses:
            ticket.status = status_value

        if assignee_id:
            user = get_user_model().objects.filter(pk=assignee_id, is_active=True).first()
            ticket.assignee = user
        else:
            ticket.assignee = None

        ticket.is_resolved = bool(resolved_value)
        ticket.last_updated_by = request.user
        ticket.save()

        return HttpResponseRedirect(reverse('admin-dashboard'))
