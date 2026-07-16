from .utils import get_current_app_user


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
    user = get_current_app_user(request)
    return {'current_user': user, 'current_role': user.role if user else None}