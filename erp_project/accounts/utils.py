from .models import AppUser


def get_current_app_user(request):
    """
    Returns the currently 'logged in' AppUser for this request, or None.

    This is the single place (alongside context_processors.current_user,
    which delegates to this same lookup) that will change when the
    external site's API is wired in — everything else that calls this
    function stays the same.
    """
    app_user_id = request.session.get('app_user_id')
    if not app_user_id:
        return None
    try:
        return AppUser.objects.get(pk=app_user_id, is_active=True)
    except AppUser.DoesNotExist:
        return None