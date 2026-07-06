from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import Issue, Notification, Status, QAStatus, DeliveryStatus


@receiver(pre_save, sender=Issue)
def track_issue_changes(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_assigned_to = None
        instance._old_status      = None
        instance._old_qa_status   = None
        return

    try:
        old = Issue.objects.get(pk=instance.pk)
        instance._old_assigned_to = old.assigned_to
        instance._old_status      = old.status
        instance._old_qa_status   = old.qa_status
    except Issue.DoesNotExist:
        instance._old_assigned_to = None
        instance._old_status      = None
        instance._old_qa_status   = None


@receiver(pre_save, sender=Issue)
def apply_auto_conditions(sender, instance, **kwargs):
    old_assigned = getattr(instance, '_old_assigned_to', None)
    old_status   = getattr(instance, '_old_status', None)
    old_qa       = getattr(instance, '_old_qa_status', None)

    try:
        status_open     = Status.objects.get(name='Open')
        status_reopened = Status.objects.get(name='Reopened')
    except Status.DoesNotExist:
        status_open     = None
        status_reopened = None

    try:
        qa_open = QAStatus.objects.get(name='Open')
    except QAStatus.DoesNotExist:
        qa_open = None

    try:
        delivery_undelivered = DeliveryStatus.objects.get(name='Undelivered')
    except DeliveryStatus.DoesNotExist:
        delivery_undelivered = None

    # 1. Issue assigned to developer → Development Status = Open
    if instance.assigned_to and not old_assigned:
        if status_open:
            instance.status = status_open

    # 2. Development Status = Completed → QA Status = Open
    if (instance.status and
            (old_status is None or instance.status != old_status) and
            instance.status.name == 'Completed'):
        if qa_open:
            instance.qa_status = qa_open

    # 3. QA Status = Approved → Delivery Status = Undelivered
    if (instance.qa_status and
            (old_qa is None or instance.qa_status != old_qa) and
            instance.qa_status.name == 'Approved'):
        if delivery_undelivered:
            instance.delivery_status = delivery_undelivered

    # 4. QA Status = Rejected → Development Status = Reopened
    if (instance.qa_status and
            (old_qa is None or instance.qa_status != old_qa) and
            instance.qa_status.name == 'Rejected'):
        if status_reopened:
            instance.status = status_reopened


@receiver(post_save, sender=Issue)
def create_notifications(sender, instance, created, **kwargs):

    # New Issue Created
    if created:
        if instance.assigned_to:
            Notification.objects.create(
                issue   = instance,
                type    = 'new_assignment',
                message = f"New issue #{instance.issue_id} '{instance.task_name}' has been created and assigned to {instance.assigned_to.name}."
            )
        else:
            Notification.objects.create(
                issue   = instance,
                type    = 'new_assignment',
                message = f"New issue #{instance.issue_id} '{instance.task_name}' has been created."
            )

    if not created:
        old_assigned = getattr(instance, '_old_assigned_to', None)
        old_status   = getattr(instance, '_old_status', None)
        old_qa       = getattr(instance, '_old_qa_status', None)

        # New Assignment (was unassigned before)
        if (instance.assigned_to and not old_assigned):
            Notification.objects.create(
                issue   = instance,
                type    = 'new_assignment',
                message = f"Issue #{instance.issue_id} '{instance.task_name}' has been assigned to {instance.assigned_to.name}."
            )

        # Reassignment
        elif (instance.assigned_to and old_assigned and
                instance.assigned_to != old_assigned):
            Notification.objects.create(
                issue   = instance,
                type    = 'reassignment',
                message = f"Issue #{instance.issue_id} '{instance.task_name}' has been reassigned from {old_assigned.name} to {instance.assigned_to.name}."
            )

        # QA Rejection
        if (instance.qa_status and old_qa and
                instance.qa_status != old_qa and
                instance.qa_status.name == 'Rejected'):
            Notification.objects.create(
                issue   = instance,
                type    = 'qa_rejection',
                message = f"Issue #{instance.issue_id} '{instance.task_name}' has failed QA verification."
            )

        # Issue Closure
        if (instance.status and old_status and
                instance.status != old_status and
                instance.status.name == 'Completed'):
            Notification.objects.create(
                issue   = instance,
                type    = 'closure',
                message = f"Issue #{instance.issue_id} '{instance.task_name}' has been completed."
            )