from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import Issue, Notification


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


@receiver(post_save, sender=Issue)
def create_notifications(sender, instance, created, **kwargs):

    # New Issue Created
    if created:
        if instance.assigned_to:
            Notification.objects.create(
                issue   = instance,
                type    = 'new_assignment',
                message = f"New issue #{instance.issue_id} '{instance.summary}' has been created and assigned to {instance.assigned_to.name}."
            )
        else:
            Notification.objects.create(
                issue   = instance,
                type    = 'new_assignment',
                message = f"New issue #{instance.issue_id} '{instance.summary}' has been created."
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
                message = f"Issue #{instance.issue_id} '{instance.summary}' has been assigned to {instance.assigned_to.name}."
            )

        # Reassignment
        elif (instance.assigned_to and old_assigned and
                instance.assigned_to != old_assigned):
            Notification.objects.create(
                issue   = instance,
                type    = 'reassignment',
                message = f"Issue #{instance.issue_id} '{instance.summary}' has been reassigned from {old_assigned.name} to {instance.assigned_to.name}."
            )

        # QA Rejection
        if (instance.qa_status and old_qa and
                instance.qa_status != old_qa and
                instance.qa_status.name == 'Failed'):
            Notification.objects.create(
                issue   = instance,
                type    = 'qa_rejection',
                message = f"Issue #{instance.issue_id} '{instance.summary}' has failed QA verification."
            )

        # Issue Closure
        if (instance.status and old_status and
                instance.status != old_status and
                instance.status.name == 'Closed'):
            Notification.objects.create(
                issue   = instance,
                type    = 'closure',
                message = f"Issue #{instance.issue_id} '{instance.summary}' has been closed."
            )