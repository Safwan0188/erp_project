from django.db import models


class Category(models.Model):
    name       = models.CharField(max_length=100, unique=True)
    is_default = models.BooleanField(default=False)
    created_by = models.ForeignKey('accounts.AppUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    def __str__(self):
        return self.name


class IssueType(models.Model):
    name       = models.CharField(max_length=100, unique=True)
    is_default = models.BooleanField(default=False)
    created_by = models.ForeignKey('accounts.AppUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    def __str__(self):
        return self.name


class Status(models.Model):
    name       = models.CharField(max_length=100, unique=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class QAStatus(models.Model):
    name       = models.CharField(max_length=100, unique=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class DeliveryStatus(models.Model):
    name       = models.CharField(max_length=100, unique=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Developer(models.Model):
    name         = models.CharField(max_length=100, unique=True)
    is_default   = models.BooleanField(default=False)
    linked_user  = models.OneToOneField('accounts.AppUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='developer_profile')
    is_active    = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class QAMember(models.Model):
    name         = models.CharField(max_length=100, unique=True)
    is_default   = models.BooleanField(default=False)
    linked_user  = models.OneToOneField('accounts.AppUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='qa_profile')
    is_active    = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Issue(models.Model):

    issue_id             = models.AutoField(primary_key=True)
    project              = models.CharField(max_length=200)
    category             = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    type                 = models.ForeignKey(IssueType, on_delete=models.SET_NULL, null=True, blank=True)
    module               = models.CharField(max_length=200, blank=True, null=True)
    task_name            = models.CharField(max_length=300)
    description          = models.TextField(blank=True, null=True)
    attachments          = models.FileField(upload_to='attachments/', blank=True, null=True)
    created_by           = models.ForeignKey('accounts.AppUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='reported_issues')
    reported_date        = models.DateField()
    assigned_to          = models.ForeignKey(Developer, on_delete=models.SET_NULL, null=True, blank=True)
    allocated_time       = models.CharField(max_length=100, blank=True, null=True)
    approx_delivery      = models.DateField(blank=True, null=True)
    status               = models.ForeignKey(Status, on_delete=models.SET_NULL, null=True, blank=True)
    developer_comments   = models.TextField(blank=True, null=True)
    completion_date      = models.DateField(blank=True, null=True)
    qa_by                = models.ForeignKey('QAMember', on_delete=models.SET_NULL, null=True, blank=True, related_name='issues')
    qa_status            = models.ForeignKey(QAStatus, on_delete=models.SET_NULL, null=True, blank=True)
    qa_comments          = models.TextField(blank=True, null=True)
    delivery_status      = models.ForeignKey(DeliveryStatus, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"[{self.issue_id}] {self.task_name}"


class IssueAssignmentHistory(models.Model):
    """
    Tracks each assignment window of a developer on an issue, so that
    per-developer notification filtering ("only from when I was assigned")
    has a real timestamp to filter from. Populated automatically via signals
    whenever Issue.assigned_to changes — never edited directly.
    """
    issue          = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='assignment_history')
    developer      = models.ForeignKey(Developer, on_delete=models.CASCADE, related_name='assignment_history')
    assigned_at    = models.DateTimeField(auto_now_add=True)
    unassigned_at  = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-assigned_at']

    def __str__(self):
        status = "active" if not self.unassigned_at else "ended"
        return f"Issue #{self.issue_id} — {self.developer.name} ({status})"

class QAAssignmentHistory(models.Model):
    """
    Tracks each assignment window of a QA member on an issue, mirroring
    IssueAssignmentHistory for developers. Populated automatically via
    signals whenever Issue.qa_by changes — never edited directly.
    """
    issue          = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='qa_assignment_history')
    qa_member      = models.ForeignKey(QAMember, on_delete=models.CASCADE, related_name='assignment_history')
    assigned_at    = models.DateTimeField(auto_now_add=True)
    unassigned_at  = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-assigned_at']

    def __str__(self):
        status = "active" if not self.unassigned_at else "ended"
        return f"Issue #{self.issue_id} — {self.qa_member.name} ({status})"

class Notification(models.Model):
    TYPE_CHOICES = [
        ('new_assignment',    'New Assignment'),
        ('reassignment',      'Reassignment'),
        ('upcoming_delivery', 'Upcoming Delivery'),
        ('overdue',           'Overdue'),
        ('qa_rejection',      'QA Rejection'),
        ('qa_approval',       'QA Approval'),
        ('completed',           'Issue Completed'),
        ('reopened',          'Issue Reopened'),
        ('dev_comment',       'Developer Comment'),
        ('qa_comment',        'QA Comment'),
        ('delivered',         'Issue Delivered'),
    ]

    issue      = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='notifications')
    type       = models.CharField(max_length=50, choices=TYPE_CHOICES)
    message    = models.TextField()
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.type} - Issue #{self.issue.issue_id}"
    
    