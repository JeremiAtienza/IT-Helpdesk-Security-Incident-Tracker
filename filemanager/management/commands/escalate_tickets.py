from django.core.management.base import BaseCommand
from django.utils import timezone
from filemanager.models import Ticket

class Command(BaseCommand):
    help = 'Escalate overdue tickets automatically and notify senior staff.'

    def handle(self, *args, **options):
        overdue_tickets = Ticket.objects.filter(
            status__in=[Ticket.STATUS_PENDING, Ticket.STATUS_IN_PROGRESS],
            sla_due__lt=timezone.now(),
        )

        for ticket in overdue_tickets:
            if ticket.escalation_level < 2:
                old_level = ticket.escalation_level
                ticket.escalate()
                ticket.save(update_fields=['assignee', 'escalation_level', 'escalated_at'])
                ticket.send_alert(
                    f"Ticket {ticket.title} has been escalated from level {old_level} to {ticket.escalation_level}."
                )
                self.stdout.write(self.style.SUCCESS(
                    f"Escalated ticket {ticket.pk} - {ticket.title} to level {ticket.escalation_level}"
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f"Ticket {ticket.pk} already at highest escalation level"
                ))
