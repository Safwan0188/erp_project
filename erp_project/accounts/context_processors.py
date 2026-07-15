from .models import AppUser


def current_user(request):
    """
    Injects `current_user` into every template.

    THIS IS THE ONE PLACE that will change when the external site's API
    is wired in: instead of reading `app_user_id` from the Django
    session, it will validate a token/cookie against that API (or a
    locally cached copy of the user it returns) and return that user
    instead. Every view/template that reads `current_user` stays the
    same — only the lookup inside this function changes.
    """
    app_user_id = request.session.get('app_user_id')
    if not app_user_id:
        return {'current_user': None}

    try:
        user = AppUser.objects.get(pk=app_user_id, is_active=True)
    except AppUser.DoesNotExist:
        user = None

    return {'current_user': user}