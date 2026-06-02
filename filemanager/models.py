import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, User
from django.contrib.auth.signals import user_login_failed, user_logged_in, user_logged_out
from django.utils import timezone
import cloudinary.uploader
from cloudinary_storage.storage import RawMediaCloudinaryStorage

incident_logger = logging.getLogger('incident_chain')

class VaultFile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255, help_text="Give your file a descriptive name")
    document = models.FileField(upload_to='vault/', storage=RawMediaCloudinaryStorage())
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title

    # Override the default delete method
    def delete(self, *args, **kwargs):
        if self.document:
            try:
                # self.document.name contains the Cloudinary public_id
                # resource_type='raw' is required because we used RawMediaCloudinaryStorage
                cloudinary.uploader.destroy(self.document.name, resource_type='raw')
            except Exception as e:
                # Print the error to your server logs if the Cloudinary API fails
                print(f"Error deleting file from Cloudinary: {e}")
                
        # Call the parent class's delete method to remove the database record
        super().delete(*args, **kwargs)


class IncidentTicket(models.Model):
    NIST_STAGE_PREPARATION = 'PREPARATION'
    NIST_STAGE_DETECTION = 'DETECTION'
    NIST_STAGE_CONTAINMENT = 'CONTAINMENT'
    NIST_STAGE_RECOVERY = 'RECOVERY'

    STATUS_CHOICES = [
        (NIST_STAGE_PREPARATION, 'Preparation'),
        (NIST_STAGE_DETECTION, 'Detection'),
        (NIST_STAGE_CONTAINMENT, 'Containment'),
        (NIST_STAGE_RECOVERY, 'Recovery'),
    ]

    reporter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reported_tickets')
    assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_incidents')
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey('filemanager.Category', on_delete=models.SET_NULL, null=True, blank=True)
    PRIORITY_LOW = 'LOW'
    PRIORITY_MEDIUM = 'MEDIUM'
    PRIORITY_HIGH = 'HIGH'
    PRIORITY_CRITICAL = 'CRITICAL'

    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Low'),
        (PRIORITY_MEDIUM, 'Medium'),
        (PRIORITY_HIGH, 'High'),
        (PRIORITY_CRITICAL, 'Critical'),
    ]

    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)
    # New fields for advanced incident handling
    severity_score = models.PositiveSmallIntegerField(default=0)
    IMPACT_LOW = 'LOW'
    IMPACT_MEDIUM = 'MEDIUM'
    IMPACT_HIGH = 'HIGH'
    IMPACT_CRITICAL = 'CRITICAL'

    IMPACT_CHOICES = [
        (IMPACT_LOW, 'Low'),
        (IMPACT_MEDIUM, 'Medium'),
        (IMPACT_HIGH, 'High'),
        (IMPACT_CRITICAL, 'Critical'),
    ]

    impact_level = models.CharField(max_length=10, choices=IMPACT_CHOICES, default=IMPACT_MEDIUM)
    # List of affected assets (hosts, IPs, services). Use JSON when available.
    try:
        from django.db.models import JSONField as _JSONField
    except Exception:
        from django.db.models import TextField as _JSONField

    affected_assets = _JSONField(blank=True, null=True, default=list)
    iocs = models.TextField(blank=True, default='')
    evidence_summary = models.TextField(blank=True, default='')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=NIST_STAGE_DETECTION)
    is_resolved = models.BooleanField(default=False)
    source = models.CharField(max_length=64, default='web')
    chain_of_custody = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_tickets')
    # SLA / escalation
    sla_due = models.DateTimeField(null=True, blank=True)
    escalation_level = models.PositiveSmallIntegerField(default=0)
    escalated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.status})"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        previous = None
        if not is_new:
            previous = IncidentTicket.objects.filter(pk=self.pk).first()

        actor = self.last_updated_by or self.reporter
        actor_name = actor.username if actor else 'system'
        changes = []

        if is_new:
            changes.append('created')
        elif previous is not None:
            if previous.status != self.status:
                changes.append(f"status:{previous.status}->{self.status}")
            if previous.is_resolved != self.is_resolved:
                changes.append(f"resolved:{previous.is_resolved}->{self.is_resolved}")
            if previous.description != self.description:
                changes.append('description:updated')

        entry = f"{timezone.now().isoformat()} user={actor_name} changes={'|'.join(changes) if changes else 'no_change'}"
        self.chain_of_custody = f"{self.chain_of_custody}{entry}\n"
        super().save(*args, **kwargs)
        incident_logger.info(entry)

    def compute_severity(self):
        mapping = {
            self.PRIORITY_LOW: 10,
            self.PRIORITY_MEDIUM: 30,
            self.PRIORITY_HIGH: 70,
            self.PRIORITY_CRITICAL: 95,
        }
        score = mapping.get(self.priority, 0)
        if self.category and getattr(self.category, 'is_security', False):
            score = max(score, 60)
        self.severity_score = score

    def compute_sla_due(self):
        now = self.created_at or timezone.now()
        sla_mapping = {
            self.PRIORITY_LOW: timedelta(days=3),
            self.PRIORITY_MEDIUM: timedelta(days=2),
            self.PRIORITY_HIGH: timedelta(hours=24),
            self.PRIORITY_CRITICAL: timedelta(hours=4),
        }
        delta = sla_mapping.get(self.priority, timedelta(days=3))
        self.sla_due = now + delta

    def assign_based_on_category(self):
        if self.assignee or not self.category:
            return
        assigned = False
        team_name = getattr(self.category, 'default_assignee_group', '')
        if team_name:
            grp = Group.objects.filter(name__iexact=team_name).first()
            if grp:
                user = grp.user_set.first()
                if user:
                    self.assignee = user
                    assigned = True
        if not assigned:
            name = self.category.name.lower() if self.category else ''
            if 'password' in name or 'account' in name:
                grp = Group.objects.filter(name__icontains='account').first()
            elif 'malware' in name or 'virus' in name or 'security' in name or (self.category and getattr(self.category, 'is_security', False)):
                grp = Group.objects.filter(name__icontains='security').first()
            elif 'network' in name:
                grp = Group.objects.filter(name__icontains='network').first()
            else:
                grp = Group.objects.filter(name__icontains='it').first()
            if grp:
                user = grp.user_set.first()
                if user:
                    self.assignee = user

    def escalate_if_overdue(self):
        if not self.sla_due:
            return
        if timezone.now() > self.sla_due and self.escalation_level < 3:
            self.escalation_level += 1
            self.escalated_at = timezone.now()
            incident_logger.info('Ticket escalated id=%s level=%s', self.pk, self.escalation_level)


# --- Ticketing and incident models (expanded) ---
from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import Group
from datetime import timedelta


class Category(models.Model):
    name = models.CharField(max_length=128, unique=True)
    slug = models.SlugField(max_length=128, unique=True)
    is_security = models.BooleanField(default=False)
    default_assignee_group = models.CharField(max_length=128, blank=True, help_text='Group name to auto-assign')

    def __str__(self):
        return self.name


class Ticket(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_RESOLVED = 'RESOLVED'
    STATUS_CLOSED = 'CLOSED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_RESOLVED, 'Resolved'),
        (STATUS_CLOSED, 'Closed'),
    ]

    PRIORITY_LOW = 'LOW'
    PRIORITY_MEDIUM = 'MEDIUM'
    PRIORITY_HIGH = 'HIGH'
    PRIORITY_CRITICAL = 'CRITICAL'

    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Low'),
        (PRIORITY_MEDIUM, 'Medium'),
        (PRIORITY_HIGH, 'High'),
        (PRIORITY_CRITICAL, 'Critical'),
    ]

    SOURCE_WEB = 'WEB'
    SOURCE_EMAIL = 'EMAIL'
    SOURCE_API = 'API'
    SOURCE_QR = 'QR'

    SOURCE_CHOICES = [
        (SOURCE_WEB, 'Web Portal'),
        (SOURCE_EMAIL, 'Email'),
        (SOURCE_API, 'API'),
        (SOURCE_QR, 'QR Code'),
    ]

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets_reported')
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    source = models.CharField(max_length=16, choices=SOURCE_CHOICES, default=SOURCE_WEB)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets_assigned')
    last_updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets_last_updated')
    is_security_incident = models.BooleanField(default=False)
    severity_score = models.PositiveSmallIntegerField(default=0)
    sla_due = models.DateTimeField(null=True, blank=True)
    escalation_level = models.PositiveSmallIntegerField(default=0)
    escalated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} [{self.get_priority_display()}]"

    def compute_severity(self):
        mapping = {
            self.PRIORITY_LOW: 1,
            self.PRIORITY_MEDIUM: 3,
            self.PRIORITY_HIGH: 7,
            self.PRIORITY_CRITICAL: 10,
        }
        score = mapping.get(self.priority, 0)
        if self.category and self.category.is_security:
            score = max(score, 6)
        self.severity_score = score

    def compute_sla_due(self):
        now = self.created_at or timezone.now()
        sla_mapping = {
            self.PRIORITY_LOW: timedelta(days=3),
            self.PRIORITY_MEDIUM: timedelta(days=2),
            self.PRIORITY_HIGH: timedelta(hours=24),
            self.PRIORITY_CRITICAL: timedelta(hours=4),
        }
        delta = sla_mapping.get(self.priority, timedelta(days=3))
        self.sla_due = now + delta

    @property
    def is_overdue(self):
        return bool(self.sla_due and timezone.now() > self.sla_due and self.status != self.STATUS_RESOLVED)

    def auto_categorize(self):
        if self.category:
            return
        text = f"{self.title} {self.description}".lower()
        rules = [
            (['password', 'account', 'login'], 'Password Compromise'),
            (['malware', 'virus', 'ransomware', 'infection', 'pop-up'], 'Malware'),
            (['phishing', 'spoof', 'suspicious email', 'scam'], 'Phishing'),
            (['network', 'wifi', 'internet', 'connection'], 'Network Attack'),
            (['unauthoriz', 'unauthorized', 'data breach', 'breach'], 'Unauthorized Access'),
        ]
        for keywords, category_name in rules:
            if any(term in text for term in keywords):
                self.category = Category.objects.filter(name__iexact=category_name).first()
                if self.category:
                    self.is_security_incident = self.category.is_security
                    break

    def assign_based_on_category(self):
        if self.assignee or not self.category:
            return
        assigned = False
        team_name = self.category.default_assignee_group
        if team_name:
            grp = Group.objects.filter(name__iexact=team_name).first()
            if grp:
                user = grp.user_set.first()
                if user:
                    self.assignee = user
                    assigned = True
        if not assigned:
            name = self.category.name.lower()
            if 'password' in name or 'account' in name:
                grp = Group.objects.filter(name__icontains='account').first()
            elif 'malware' in name or 'virus' in name or 'security' in name or self.category.is_security:
                grp = Group.objects.filter(name__icontains='security').first()
            elif 'network' in name:
                grp = Group.objects.filter(name__icontains='network').first()
            else:
                grp = Group.objects.filter(name__icontains='it').first()
            if grp:
                user = grp.user_set.first()
                if user:
                    self.assignee = user

    def get_suggestion(self):
        similar = Ticket.objects.filter(category=self.category).exclude(pk=self.pk).order_by('-created_at').first()
        if similar:
            return f"Similar issue found: {similar.title}. Consider checking prior notes or similar resolution paths."
        if self.category:
            return {
                'Malware': 'Try isolating the affected device and running a malware scan immediately.',
                'Phishing': 'Do not reply to the suspicious email; forward it to security and change your password.',
                'Unauthorized Access': 'Ensure account credentials are reset and review login history.',
                'Network Attack': 'Check firewall logs and reset the network gateway if needed.',
                'Password Compromise': 'Reset the password and verify MFA if available.',
            }.get(self.category.name, 'Review the issue details and assign to the appropriate team.')
        return 'Review the details, then route to the correct support team.'

    def send_sms_alert(self, message):
        if not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM_NUMBER):
            return
        try:
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            recipients = getattr(settings, 'TWILIO_SMS_RECIPIENTS', [])
            for recipient in recipients:
                if recipient:
                    client.messages.create(
                        body=message,
                        from_=settings.TWILIO_FROM_NUMBER,
                        to=recipient,
                    )
        except Exception as exc:
            incident_logger.error('SMS alert failed: %s', exc)

    def send_alert(self, message):
        User = get_user_model()
        recipients = [user.email for user in User.objects.filter(is_staff=True, is_active=True) if user.email]
        if recipients:
            try:
                send_mail(
                    subject=f"Critical ticket alert: {self.title}",
                    message=message,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
                    recipient_list=recipients,
                    fail_silently=True,
                )
            except Exception as exc:
                incident_logger.error('Alert email failed: %s', exc)
        self.send_sms_alert(message)

    def escalate(self):
        if self.escalation_level >= 2:
            return
        self.escalation_level += 1
        self.escalated_at = timezone.now()
        admins = Group.objects.filter(name__iexact='Admin').first()
        if admins:
            user = admins.user_set.first()
            if user:
                self.assignee = user
        incident_logger.info('Ticket escalated id=%s level=%s', self.pk, self.escalation_level)


class TicketAttachment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    file = models.FileField(upload_to='ticket_attachments/', storage=RawMediaCloudinaryStorage())
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment for {self.ticket_id} by {self.uploaded_by}"


class TicketComment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author or 'Unknown'} on ticket {self.ticket_id}"


class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=128)
    object_type = models.CharField(max_length=64)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    detail = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        actor = self.actor.username if self.actor else 'system'
        return f"{self.timestamp.isoformat()} {actor} {self.action} {self.object_type}:{self.object_id}"

class IncidentEvent(models.Model):
    """Timeline events attached to an IncidentTicket for forensic/history purposes."""
    ticket = models.ForeignKey(IncidentTicket, on_delete=models.CASCADE, related_name='events')
    timestamp = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=64, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        who = self.actor.username if self.actor else 'system'
        return f"{self.timestamp.isoformat()} [{who}] {self.action or 'note'}"


class IncidentAttachment(models.Model):
    ticket = models.ForeignKey(IncidentTicket, on_delete=models.CASCADE, related_name='incident_attachments')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    file = models.FileField(upload_to='incident_attachments/', storage=RawMediaCloudinaryStorage())
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"IncidentAttachment for {self.ticket.pk} by {self.uploaded_by or 'Unknown'}"

class KnowledgeBaseArticle(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    content = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


@receiver(post_save, sender=Ticket)
def ticket_post_save(sender, instance: Ticket, created, **kwargs):
    if created:
        instance.auto_categorize()
        instance.compute_severity()
        instance.compute_sla_due()
        instance.assign_based_on_category()
        if instance.is_security_incident or instance.priority in {instance.PRIORITY_HIGH, instance.PRIORITY_CRITICAL}:
            instance.send_alert(
                f"Ticket {instance.title} created with priority {instance.get_priority_display()} and category {getattr(instance.category, 'name', 'None')}"
            )
        instance.save(update_fields=[
            'category', 'is_security_incident', 'severity_score', 'sla_due', 'assignee',
            'escalation_level', 'escalated_at', 'source',
        ])

    if not created and instance.is_overdue and instance.escalation_level == 0:
        instance.escalate()
        instance.save(update_fields=['assignee', 'escalation_level', 'escalated_at'])
        instance.send_alert(f"Ticket {instance.title} has been escalated due to SLA breach.")

    actor = getattr(instance, 'last_updated_by', None) or instance.reporter
    AuditLog.objects.create(
        actor=actor,
        action='ticket_created' if created else 'ticket_updated',
        object_type='Ticket',
        object_id=instance.pk,
        detail=f"status={instance.status} priority={instance.priority} assignee={getattr(instance.assignee, 'username', None)} sla_due={instance.sla_due}",
    )


@receiver(post_delete, sender=Ticket)
def ticket_post_delete(sender, instance, **kwargs):
    AuditLog.objects.create(
        actor=None,
        action='ticket_deleted',
        object_type='Ticket',
        object_id=instance.pk,
        detail=f"deleted {instance.title}",
    )


@receiver(post_save, sender=TicketAttachment)
def attachment_post_save(sender, instance, created, **kwargs):
    if created:
        AuditLog.objects.create(
            actor=instance.uploaded_by,
            action='attachment_added',
            object_type='TicketAttachment',
            object_id=instance.pk,
            detail=f"ticket={instance.ticket.pk} file={instance.file.name}",
        )


@receiver(post_delete, sender=TicketAttachment)
def attachment_post_delete(sender, instance, **kwargs):
    AuditLog.objects.create(
        actor=instance.uploaded_by,
        action='attachment_deleted',
        object_type='TicketAttachment',
        object_id=instance.pk,
        detail=f"ticket={instance.ticket.pk} file={instance.file.name}",
    )


@receiver(post_save, sender=TicketComment)
def comment_post_save(sender, instance, created, **kwargs):
    if created:
        AuditLog.objects.create(
            actor=instance.author,
            action='comment_added',
            object_type='TicketComment',
            object_id=instance.pk,
            detail=f"ticket={instance.ticket.pk} comment={instance.content[:80]}",
        )


@receiver(post_save, sender=KnowledgeBaseArticle)
def kb_post_save(sender, instance, created, **kwargs):
    AuditLog.objects.create(
        actor=instance.created_by,
        action='kb_article_created' if created else 'kb_article_updated',
        object_type='KnowledgeBaseArticle',
        object_id=instance.pk,
        detail=f"title={instance.title}",
    )


@receiver(post_delete, sender=KnowledgeBaseArticle)
def kb_post_delete(sender, instance, **kwargs):
    AuditLog.objects.create(
        actor=instance.created_by,
        action='kb_article_deleted',
        object_type='KnowledgeBaseArticle',
        object_id=instance.pk,
        detail=f"title={instance.title}",
    )


@receiver(post_save, sender=IncidentTicket)
def incident_ticket_post_save(sender, instance: IncidentTicket, created, **kwargs):
    # On create: auto-calc severity, SLA, and assign based on category
    if created:
        instance.compute_severity()
        instance.compute_sla_due()
        instance.assign_based_on_category()
        # create an initial timeline event
        IncidentEvent.objects.create(ticket=instance, actor=instance.reporter, action='created', note='Incident created')
        instance.save(update_fields=['severity_score', 'sla_due', 'assignee'])

    # On update: check SLA breach and escalate
    else:
        if instance.sla_due and timezone.now() > instance.sla_due and instance.escalation_level == 0:
            instance.escalate_if_overdue()
            instance.save(update_fields=['escalation_level', 'assignee', 'escalated_at'])
            instance.send_alert(f"Incident {instance.title} escalated due to SLA breach.")

    actor = getattr(instance, 'last_updated_by', None) or instance.reporter
    AuditLog.objects.create(
        actor=actor,
        action='incident_created' if created else 'incident_updated',
        object_type='IncidentTicket',
        object_id=instance.pk,
        detail=f"status={instance.status} priority={instance.priority} assignee={getattr(instance.assignee, 'username', None)} sla_due={instance.sla_due}",
    )

    # Add a timeline event for updates
    if not created:
        IncidentEvent.objects.create(ticket=instance, actor=actor, action='updated', note='Incident updated')


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    AuditLog.objects.create(
        actor=user,
        action='user_login',
        object_type='User',
        object_id=user.pk,
        detail=f"login successful from {request.META.get('REMOTE_ADDR')}",
    )


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    AuditLog.objects.create(
        actor=None,
        action='user_login_failed',
        object_type='User',
        object_id=None,
        detail=f"login failed for {credentials.get('username')} from {request.META.get('REMOTE_ADDR')}",
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    AuditLog.objects.create(
        actor=user,
        action='user_logout',
        object_type='User',
        object_id=user.pk,
        detail=f"logout from {request.META.get('REMOTE_ADDR')}",
    )
