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
BA_ROLE        = 'business_analyst'
MANAGEMENT_ROLE = 'management'


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


def can_manage_users(app_user):
    """Only Admin can view/change other users' roles."""
    if app_user is None or not app_user.is_active:
        return False
    return app_user.role == ADMIN_ROLE


def can_view_create_issue_page(app_user):
    """Developers, QA, Management (read-only), and users with no role cannot see or use the Create Issue page."""
    if app_user is None or not app_user.is_active or not app_user.role:
        return False
    return app_user.role not in (DEVELOPER_ROLE, QA_ROLE, MANAGEMENT_ROLE)


def can_view_settings_page(app_user):
    """Developers, QA, Management (read-only), and users with no role cannot see or use the Settings page."""
    if app_user is None or not app_user.is_active or not app_user.role:
        return False
    return app_user.role not in (DEVELOPER_ROLE, QA_ROLE, MANAGEMENT_ROLE)


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


def is_ba_locked(issue):
    """
    A Business Analyst loses edit/delete access to their own issue once
    its Development Status has moved to 'In Progress' — from that point
    on the issue is out of their hands and stays permanently locked to
    them, even if the status later changes again.
    """
    return issue.status_id is not None and issue.status.name == 'In Progress'


def can_edit_issue(app_user, issue):
    """
    Whether app_user can open the edit form for this issue at all.
    Admin: always. Developer: only if the issue is currently assigned
    to their linked Developer record. QA: if the issue is still
    unclaimed (qa_by empty — they can open it to self-claim), or if
    it's already claimed by their own linked QAMember record. Business
    Analyst: only on issues they personally created, and only until Dev
    Status reaches In Progress. Anyone else: no.
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
    if app_user.role == BA_ROLE:
        return issue.created_by_id == app_user.id and not is_ba_locked(issue)
    return False


def can_delete_issue(app_user, issue=None):
    """
    Admin can always delete. A Business Analyst can delete an issue
    they personally created, under the same lock rule as editing (only
    before Dev Status reaches In Progress). `issue` is optional so
    existing admin-only call sites that don't have one keep working.
    """
    if app_user is None or not app_user.is_active:
        return False
    if app_user.role == ADMIN_ROLE:
        return True
    if app_user.role == BA_ROLE and issue is not None:
        return issue.created_by_id == app_user.id and not is_ba_locked(issue)
    return False


# Fields a Developer may change on an issue assigned to them. Everything
# else on Issue stays read-only for that role, even on their own issues.
DEVELOPER_EDITABLE_FIELDS = ['allocated_time', 'approx_delivery', 'status', 'developer_comments']

# Fields a QA member may change. qa_by is included so they can self-claim
# an unassigned issue, but the form layer locks it once it's set — see
# QAIssueEditForm.
QA_EDITABLE_FIELDS = ['qa_by', 'qa_status', 'qa_comments']

# Fields a Business Analyst may set on creation and change afterward
# (until the issue locks). created_by (shown as "Reported By") is NOT
# here — it's forced from the logged-in user server-side, never
# something the BA (or anyone else) edits directly.
BA_EDITABLE_FIELDS = ['project', 'category', 'type', 'module', 'task_name', 'description', 'attachments', 'assigned_to']

def can_manage_option(app_user, obj=None, model_name=None):
    """
    Whether app_user can create/delete Category or Issue Type entries
    in Settings. Admin: any option type, any entry. Business Analyst:
    only Category and Issue Type (the option-lists behind their
    restricted Create Issue form), and only entries they personally
    created — `obj` is the specific Category/IssueType instance being
    deleted (omit `obj` when just checking create access, e.g. for
    model_name='category'/'issue_type').
    """
    if app_user is None or not app_user.is_active:
        return False
    if app_user.role == ADMIN_ROLE:
        return True
    if app_user.role == BA_ROLE and model_name in ('category', 'issue_type'):
        if obj is None:
            return True
        return obj.created_by_id == app_user.id
    return False




