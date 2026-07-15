from django.shortcuts import redirect

# Paths that don't require a "logged in" AppUser. Keep this list small and
# explicit rather than trying to guess.
EXEMPT_PATH_PREFIXES = (
    '/accounts/login-as/',
    '/admin/',
    '/media/',
    '/static/',
)


class RequireAppUserMiddleware:
    """
    Temporary stand-in for real auth enforcement. Redirects to the
    login-as picker if no AppUser is set in the session.

    Once the external site's API is wired in, this will check for a
    valid token/cookie from that system instead of the session flag —
    the redirect-if-missing behavior itself stays the same.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if not path.startswith(EXEMPT_PATH_PREFIXES) and not request.session.get('app_user_id'):
            return redirect('login_as')
        return self.get_response(request)