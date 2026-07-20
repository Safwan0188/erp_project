import re
from datetime import timedelta
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import Issue, Notification, Status, QAStatus, DeliveryStatus, Developer, IssueAssignmentHistory, QAAssignmentHistory, QAMember
from accounts.models import AppUser


def _compute_approx_delivery(allocated_time_str):
    """
    Parse a free-text allocated_time value (e.g. '3 - 12 Hours', '1 - 5 Days')
    and return today + the MAX value in that range as a date.
    Hour-based ranges resolve to tomorrow's date (since approx_delivery is date-only).
    Returns None if no number can be found in the text.
    """
    if not allocated_time_str:
        return None

    numbers = re.findall(r'\d+(?:\.\d+)?', allocated_time_str)
    if not numbers:
        return None

    max_value = max(float(n) for n in numbers)
    text_lower = allocated_time_str.lower()

    if 'hour' in text_lower or 'hr' in text_lower:
        return timezone.localdate() + timedelta(days=1)

    # Default to days for anything else (days, weeks worth of digits, etc.)
    return timezone.localdate() + timedelta(days=int(round(max_value)))


@receiver(pre_save, sender=Issue)
def track_issue_changes(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_assigned_to        = None
        instance._old_qa_by              = None
        instance._old_status             = None
        instance._old_qa_status          = None
        instance._old_delivery_status    = None
        instance._old_developer_comments = None
        instance._old_qa_comments        = None
        return

    try:
        old = Issue.objects.get(pk=instance.pk)
        instance._old_assigned_to        = old.assigned_to
        instance._old_qa_by              = old.qa_by
        instance._old_status             = old.status
        instance._old_qa_status          = old.qa_status
        instance._old_delivery_status    = old.delivery_status
        instance._old_developer_comments = old.developer_comments
        instance._old_qa_comments        = old.qa_comments
    except Issue.DoesNotExist:
        instance._old_assigned_to        = None
        instance._old_qa_by              = None
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

    # 2b. Dev Status = Completed → Completion Date = today (if not already set by this change)
    if (instance.status and
            instance.status.name == 'Completed' and
            (old_status is None or old_status.name != 'Completed')):
        instance.completion_date = timezone.localdate()

    # 2c. Dev Status changed away from Completed → Completion Date = blank
    if (old_status and old_status.name == 'Completed' and
            (not instance.status or instance.status.name != 'Completed')):
        instance.completion_date = None

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

    # 4b. Dev Status → In Progress (transition) on a DEFAULT category → auto-compute Approx Delivery
    if (instance.status and instance.status.name == 'In Progress' and
            (old_status is None or old_status.name != 'In Progress') and
            instance.category and instance.category.is_default and
            instance.allocated_time):
        computed_delivery = _compute_approx_delivery(instance.allocated_time)
        if computed_delivery:
            instance.approx_delivery = computed_delivery

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


@receiver(post_save, sender=Issue)
def track_assignment_history(sender, instance, created, **kwargs):
    """
    Maintains IssueAssignmentHistory so per-developer notification
    filtering has a real "assigned since" timestamp to work with.
    Runs on every save; only acts when assigned_to actually changed
    (or on creation with an assignee already set).
    """
    old_assigned = getattr(instance, '_old_assigned_to', None)
    new_assigned = instance.assigned_to

    if created:
        if new_assigned:
            IssueAssignmentHistory.objects.create(issue=instance, developer=new_assigned)
        return

    if new_assigned == old_assigned:
        return

    # Close out the previous developer's open assignment window, if any.
    if old_assigned:
        IssueAssignmentHistory.objects.filter(
            issue=instance, developer=old_assigned, unassigned_at__isnull=True
        ).update(unassigned_at=timezone.now())

    # Open a new window for the newly assigned developer.
    if new_assigned:
        IssueAssignmentHistory.objects.create(issue=instance, developer=new_assigned)


@receiver(post_save, sender=Issue)
def track_qa_assignment_history(sender, instance, created, **kwargs):
    """
    Maintains QAAssignmentHistory so per-QA-member notification filtering
    has a real "assigned since" timestamp to work with. Mirrors
    track_assignment_history for developers. Runs on every save; only
    acts when qa_by actually changed (or on creation with a QA member
    already set).
    """
    old_qa_by = getattr(instance, '_old_qa_by', None)
    new_qa_by = instance.qa_by

    if created:
        if new_qa_by:
            QAAssignmentHistory.objects.create(issue=instance, qa_member=new_qa_by)
        return

    if new_qa_by == old_qa_by:
        return

    # Close out the previous QA member's open assignment window, if any.
    if old_qa_by:
        QAAssignmentHistory.objects.filter(
            issue=instance, qa_member=old_qa_by, unassigned_at__isnull=True
        ).update(unassigned_at=timezone.now())

    # Open a new window for the newly assigned QA member.
    if new_qa_by:
        QAAssignmentHistory.objects.create(issue=instance, qa_member=new_qa_by)


@receiver(post_save, sender=AppUser)

def sync_developer_from_appuser(sender, instance, created, **kwargs):
    """
    Keeps the Developer lookup table in sync with users holding the
    Developer role. This is the role-driven replacement for manually
    adding/removing developers in Settings.

    - Role becomes/stays Developer (and user is_active) → ensure an
      active Developer record exists, linked to this AppUser. If one
      already exists (e.g. re-granted after revocation), reactivate it
      rather than creating a duplicate, so history is preserved.
    - Role changes away from Developer, or user is deactivated →
      deactivate the linked Developer (is_active=False) if they still
      have assigned issues, or delete it outright if they have none.
    """
    is_dev_now = instance.is_active and instance.role == 'developer'

    try:
        dev = Developer.objects.get(linked_user=instance)
    except Developer.DoesNotExist:
        dev = None

    if is_dev_now:
        if dev is None:
            # Reuse a pre-existing unlinked record with the same name if present
            # (covers the rare case where a Developer was created before linking existed).
            dev, _ = Developer.objects.get_or_create(
                linked_user=instance,
                defaults={'name': instance.name, 'is_default': True, 'is_active': True}
            )
        else:
            dev.name       = instance.name
            dev.is_default = True
            dev.is_active  = True
            dev.save()
    else:
        if dev is not None:
            has_assigned_issues = Issue.objects.filter(assigned_to=dev).exists()
            if has_assigned_issues:
                dev.is_active  = False
                dev.is_default = False
                dev.save()
            else:
                dev.delete()


@receiver(post_delete, sender=AppUser)
def deactivate_developer_on_appuser_delete(sender, instance, **kwargs):
    """
    If an AppUser is deleted outright (rather than deactivated) via Django
    Admin, apply the same zero-issues-delete / else-deactivate rule.
    linked_user will already be NULL on the Developer row by this point
    (SET_NULL), so we match on the AppUser's name as a best-effort fallback
    since this is a temporary, pre-API stand-in. This is one of the pieces
    intended to be revisited once real user records replace AppUser.
    """
    try:
        dev = Developer.objects.get(name=instance.name, linked_user__isnull=True)
    except (Developer.DoesNotExist, Developer.MultipleObjectsReturned):
        return

    has_assigned_issues = Issue.objects.filter(assigned_to=dev).exists()
    if has_assigned_issues:
        dev.is_active  = False
        dev.is_default = False
        dev.save()
    else:
        dev.delete()


@receiver(post_save, sender=AppUser)
def sync_qamember_from_appuser(sender, instance, created, **kwargs):
    """
    Keeps the QAMember lookup table in sync with users holding the QA
    role. Mirrors sync_developer_from_appuser exactly — see that
    function for the full rationale.
    """
    is_qa_now = instance.is_active and instance.role == 'qa'

    try:
        qa = QAMember.objects.get(linked_user=instance)
    except QAMember.DoesNotExist:
        qa = None

    if is_qa_now:
        if qa is None:
            qa, _ = QAMember.objects.get_or_create(
                linked_user=instance,
                defaults={'name': instance.name, 'is_default': True, 'is_active': True}
            )
        else:
            qa.name       = instance.name
            qa.is_default = True
            qa.is_active  = True
            qa.save()
    else:
        if qa is not None:
            has_assigned_issues = Issue.objects.filter(qa_by=qa).exists()
            if has_assigned_issues:
                qa.is_active  = False
                qa.is_default = False
                qa.save()
            else:
                qa.delete()


@receiver(post_delete, sender=AppUser)
def deactivate_qamember_on_appuser_delete(sender, instance, **kwargs):
    """
    QA equivalent of deactivate_developer_on_appuser_delete — see that
    function for the full rationale.
    """
    try:
        qa = QAMember.objects.get(name=instance.name, linked_user__isnull=True)
    except (QAMember.DoesNotExist, QAMember.MultipleObjectsReturned):
        return

    has_assigned_issues = Issue.objects.filter(qa_by=qa).exists()
    if has_assigned_issues:
        qa.is_active  = False
        qa.is_default = False
        qa.save()
    else:
        qa.delete()