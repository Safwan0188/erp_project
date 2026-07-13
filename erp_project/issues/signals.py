from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import Issue, Notification, Status, QAStatus, DeliveryStatus


@receiver(pre_save, sender=Issue)
def track_issue_changes(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_assigned_to        = None
        instance._old_status             = None
        instance._old_qa_status          = None
        instance._old_delivery_status    = None
        instance._old_developer_comments = None
        instance._old_qa_comments        = None
        return

    try:
        old = Issue.objects.get(pk=instance.pk)
        instance._old_assigned_to        = old.assigned_to
        instance._old_status             = old.status
        instance._old_qa_status          = old.qa_status
        instance._old_delivery_status    = old.delivery_status
        instance._old_developer_comments = old.developer_comments
        instance._old_qa_comments        = old.qa_comments
    except Issue.DoesNotExist:
        instance._old_assigned_to        = None
        instance._old_status             = None
        instance._old_qa_status          = None
        instance._old_delivery_status    = None
        instance._old_developer_comments = None
        instance._old_qa_comments        = None


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

    # 1. New assignment or reassignment → Dev Status = Open
    if instance.assigned_to and (
        not old_assigned or instance.assigned_to != old_assigned
    ):
        if status_open:
            instance.status = status_open

    # 2. Dev Status = Completed → QA Status = Open
    if (instance.status and
            instance.status.name == 'Completed' and
            (old_status is None or old_status.name != 'Completed')):
        if qa_open:
            instance.qa_status = qa_open

    # 3. QA Status = Rejected → Dev Status = Reopened
    if (instance.qa_status and
            instance.qa_status.name == 'Rejected' and
            (old_qa is None or old_qa.name != 'Rejected')):
        if status_reopened:
            instance.status = status_reopened

    # 4. Dev Status changed from Reopened to In Progress or On Hold → QA Status = blank
    if (instance.status and old_status and
            old_status.name == 'Reopened' and
            instance.status.name in ['In Progress', 'On Hold']):
        instance.qa_status = None

    # 5. Dev = Completed AND QA = Approved → Delivery = Undelivered (if blank)
    if (instance.status and instance.qa_status and
            instance.status.name == 'Completed' and
            instance.qa_status.name == 'Approved' and
            not instance.delivery_status):
        if delivery_undelivered:
            instance.delivery_status = delivery_undelivered

    # 6. Conditions not met → clear Delivery Status
    if not (instance.status and instance.status.name == 'Completed' and
            instance.qa_status and instance.qa_status.name == 'Approved'):
        instance.delivery_status = None


@receiver(post_save, sender=Issue)
def create_notifications(sender, instance, created, **kwargs):

    old_assigned     = getattr(instance, '_old_assigned_to', None)
    old_status       = getattr(instance, '_old_status', None)
    old_qa           = getattr(instance, '_old_qa_status', None)
    old_delivery     = getattr(instance, '_old_delivery_status', None)
    old_dev_comments = getattr(instance, '_old_developer_comments', None)
    old_qa_comments  = getattr(instance, '_old_qa_comments', None)

    # 1. New Issue Created
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
        return

    # 2. New Assignment (was unassigned before)
    if instance.assigned_to and not old_assigned:
        Notification.objects.create(
            issue   = instance,
            type    = 'new_assignment',
            message = f"Issue #{instance.issue_id} '{instance.task_name}' has been assigned to {instance.assigned_to.name}."
        )

    # 3. Reassignment
    elif (instance.assigned_to and old_assigned and
            instance.assigned_to != old_assigned):
        Notification.objects.create(
            issue   = instance,
            type    = 'reassignment',
            message = f"Issue #{instance.issue_id} '{instance.task_name}' has been reassigned from {old_assigned.name} to {instance.assigned_to.name}."
        )

    # 4. Issue Completed
    if (instance.status and old_status and
            instance.status != old_status and
            instance.status.name == 'Completed'):
        Notification.objects.create(
            issue   = instance,
            type    = 'completed',
            message = f"Issue #{instance.issue_id} '{instance.task_name}' has been completed by {instance.assigned_to.name if instance.assigned_to else 'developer'}."
        )

    # 5. Issue Reopened
    if (instance.status and old_status and
            instance.status != old_status and
            instance.status.name == 'Reopened'):
        Notification.objects.create(
            issue   = instance,
            type    = 'reopened',
            message = f"Issue #{instance.issue_id} '{instance.task_name}' has been reopened due to QA rejection."
        )

    # 6. QA Approved
    if (instance.qa_status and old_qa and
            instance.qa_status != old_qa and
            instance.qa_status.name == 'Approved'):
        Notification.objects.create(
            issue   = instance,
            type    = 'qa_approval',
            message = f"Issue #{instance.issue_id} '{instance.task_name}' has been approved by QA."
        )

    # 7. QA Rejected
    if (instance.qa_status and old_qa and
            instance.qa_status != old_qa and
            instance.qa_status.name == 'Rejected'):
        Notification.objects.create(
            issue   = instance,
            type    = 'qa_rejection',
            message = f"Issue #{instance.issue_id} '{instance.task_name}' has been rejected by QA."
        )

    # 8. Developer Comments added or updated
    if (instance.developer_comments and
            instance.developer_comments != old_dev_comments):
        Notification.objects.create(
            issue   = instance,
            type    = 'dev_comment',
            message = f"Issue #{instance.issue_id} '{instance.task_name}' has new developer comments."
        )

    # 9. QA Comments added or updated
    if (instance.qa_comments and
            instance.qa_comments != old_qa_comments):
        Notification.objects.create(
            issue   = instance,
            type    = 'qa_comment',
            message = f"Issue #{instance.issue_id} '{instance.task_name}' has new QA comments."
        )

    # 10. Issue Delivered
    if (instance.delivery_status and old_delivery and
            instance.delivery_status != old_delivery and
            instance.delivery_status.name == 'Delivered'):
        Notification.objects.create(
            issue   = instance,
            type    = 'delivered',
            message = f"Issue #{instance.issue_id} '{instance.task_name}' has been delivered."
        )