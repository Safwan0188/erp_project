"""
Single source of truth for role -> permission checks.

Keep every "can this user do X" question funneled through here, rather
than checking `current_user.role == 'admin'` directly in views/templates.
That way, when Developer/QA (or more) roles are added later, only this
file changes — views and templates that already call these functions
don't need to be touched again.
"""

ADMIN_ROLE     = 'admin'
DEVELOPER_ROLE = 'developer'
QA_ROLE        = 'qa'


def has_permission(app_user, action=None):
    """
    Returns True if app_user is allowed to perform `action`.

    Admin remains a wildcard. Developer/QA-specific rules live in the
    dedicated functions below rather than here, since they need more
    than a yes/no (e.g. which issue, which fields) — has_permission()
    stays for simple role-wide checks.
    """
    if app_user is None or not app_user.is_active:
        return False
    if app_user.role == ADMIN_ROLE:
        return True
    return False


def can_view_create_issue_page(app_user):
    """Developers and QA cannot see or use the Create Issue page."""
    if app_user is None or not app_user.is_active:
        return False
    return app_user.role not in (DEVELOPER_ROLE, QA_ROLE)


def can_view_settings_page(app_user):
    """Developers and QA cannot see or use the Settings page."""
    if app_user is None or not app_user.is_active:
        return False
    return app_user.role not in (DEVELOPER_ROLE, QA_ROLE)


def get_linked_developer(app_user):
    """
    Returns the Developer record linked to this AppUser, or None.
    Local import avoids a circular import between accounts and issues.
    """
    if app_user is None:
        return None
    from issues.models import Developer
    try:
        return Developer.objects.get(linked_user=app_user)
    except Developer.DoesNotExist:
        return None


def get_linked_qamember(app_user):
    """
    Returns the QAMember record linked to this AppUser, or None.
    Local import avoids a circular import between accounts and issues.
    """
    if app_user is None:
        return None
    from issues.models import QAMember
    try:
        return QAMember.objects.get(linked_user=app_user)
    except QAMember.DoesNotExist:
        return None


def can_edit_issue(app_user, issue):
    """
    Whether app_user can open the edit form for this issue at all.
    Admin: always. Developer: only if the issue is currently assigned
    to their linked Developer record. QA: if the issue is still
    unclaimed (qa_by empty — they can open it to self-claim), or if
    it's already claimed by their own linked QAMember record. Anyone
    else: no.
    """
    if app_user is None or not app_user.is_active:
        return False
    if app_user.role == ADMIN_ROLE:
        return True
    if app_user.role == DEVELOPER_ROLE:
        dev = get_linked_developer(app_user)
        return dev is not None and issue.assigned_to_id == dev.id
    if app_user.role == QA_ROLE:
        qa = get_linked_qamember(app_user)
        if qa is None:
            return False
        return issue.qa_by_id is None or issue.qa_by_id == qa.id
    return False


def can_delete_issue(app_user):
    """Only Admin can delete issues."""
    return app_user is not None and app_user.is_active and app_user.role == ADMIN_ROLE


# Fields a Developer may change on an issue assigned to them. Everything
# else on Issue stays read-only for that role, even on their own issues.
DEVELOPER_EDITABLE_FIELDS = ['allocated_time', 'approx_delivery', 'status', 'developer_comments']

# Fields a QA member may change. qa_by is included so they can self-claim
# an unassigned issue, but the form layer locks it once it's set — see
# QAIssueEditForm.
QA_EDITABLE_FIELDS = ['qa_by', 'qa_status', 'qa_comments']