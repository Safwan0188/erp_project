"""
Single source of truth for role -> permission checks.

Keep every "can this user do X" question funneled through here, rather
than checking `current_user.role == 'admin'` directly in views/templates.
That way, when Developer/QA (or more) roles are added later, only this
file changes — views and templates that already call has_permission()
don't need to be touched again.
"""

ADMIN_ROLE = 'admin'


def has_permission(app_user, action=None):
    if app_user is None or not app_user.is_active:
        return False
    if app_user.role == ADMIN_ROLE:
        return True
    return False