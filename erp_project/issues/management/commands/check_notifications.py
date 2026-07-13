from django.core.management.base import BaseCommand
from django.utils import timezone
from issues.models import Issue, Notification


class Command(BaseCommand):
    help = 'Check for upcoming deliveries and overdue issues'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()

        # Upcoming delivery — 7, 3, 1 days
        for days in [7, 3, 1]:
            target_date = today + timezone.timedelta(days=days)
            upcoming = Issue.objects.filter(
                approx_delivery=target_date
            ).exclude(delivery_status__name='Delivered')

            for issue in upcoming:
                already_exists = Notification.objects.filter(
                    issue=issue,
                    type='upcoming_delivery',
                    message__icontains=f'{days} day'
                ).exists()

                if not already_exists:
                    Notification.objects.create(
                        issue   = issue,
                        type    = 'upcoming_delivery',
                        message = f"Issue #{issue.issue_id} '{issue.task_name}' is due in {days} day{'s' if days > 1 else ''}."
                    )

        # Overdue issues
        overdue = Issue.objects.filter(
            approx_delivery__lt=today
        ).exclude(delivery_status__name='Delivered')

        for issue in overdue:
            already_exists = Notification.objects.filter(
                issue=issue,
                type='overdue'
            ).filter(created_at__date=today).exists()

            if not already_exists:
                Notification.objects.create(
                    issue   = issue,
                    type    = 'overdue',
                    message = f"Issue #{issue.issue_id} '{issue.task_name}' is overdue! Delivery was {issue.approx_delivery}."
                )

        self.stdout.write(self.style.SUCCESS('Notifications checked successfully!'))