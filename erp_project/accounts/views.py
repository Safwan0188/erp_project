from django.shortcuts import render, redirect
from django.contrib import messages
from .models import AppUser


def login_as(request):
    """
    TEMPORARY stand-in for real authentication. No password — just pick
    an existing AppUser and "become" them for this browser session.
    """
    if request.method == 'POST':
        user_id = request.POST.get('app_user_id')
        try:
            app_user = AppUser.objects.get(pk=user_id, is_active=True)
            request.session['app_user_id'] = app_user.pk
            return redirect('dashboard')
        except AppUser.DoesNotExist:
            messages.error(request, 'Selected user not found.')

    return render(request, 'accounts/login_as.html', {
        'app_users': AppUser.objects.filter(is_active=True).order_by('name'),
    })


def logout_view(request):
    request.session.pop('app_user_id', None)
    return redirect('login_as')