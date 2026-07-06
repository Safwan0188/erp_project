from django.core.management.base import BaseCommand
from issues.models import Category, IssueType, Status, QAStatus, DeliveryStatus


class Command(BaseCommand):
    help = 'Load default options'

    def handle(self, *args, **kwargs):

        categories = ['Critical', 'High', 'Medium', 'Regular']
        for name in categories:
            Category.objects.get_or_create(name=name, defaults={'is_default': True})

        types = ['Issue', 'Requirement', 'Modification', 'Module Development']
        for name in types:
            IssueType.objects.get_or_create(name=name, defaults={'is_default': True})

        statuses = ['Open', 'In Progress', 'On Hold', 'Completed', 'Reopened']
        for name in statuses:
            Status.objects.get_or_create(name=name, defaults={'is_default': True})

        qa_statuses = ['Open', 'In Progress', 'On Hold', 'Approved', 'Rejected']
        for name in qa_statuses:
            QAStatus.objects.get_or_create(name=name, defaults={'is_default': True})

        delivery_statuses = ['Delivered', 'Undelivered']
        for name in delivery_statuses:
            DeliveryStatus.objects.get_or_create(name=name, defaults={'is_default': True})

        self.stdout.write(self.style.SUCCESS('Default options loaded successfully!'))