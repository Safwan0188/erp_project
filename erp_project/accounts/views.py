from django.shortcuts import render, redirect
from django.contrib import messages
from .models import AppUser
from .utils import get_current_app_user
from . import permissions as perms


def user_management(request):
    """
    Admin-only page for assigning or removing another user's role.
    Does not delete the AppUser record itself — see the model's
    sync_developer_from_appuser / sync_qamember_from_appuser signals
    for what happens automatically when a role changes away from
    Developer/QA (the linked Developer/QAMember record is deactivated
    or removed there, not here).
    """
    current_user = get_current_app_user(request)
    if not perms.can_manage_users(current_user):
        return redirect('dashboard')

    if request.method == 'POST':
        user_id  = request.POST.get('app_user_id')
        new_role = request.POST.get('role', '')
        target = AppUser.objects.filter(pk=user_id).first()
        if target is None:
            messages.error(request, 'User not found.')
        elif new_role and new_role not in dict(AppUser.ROLE_CHOICES):
            messages.error(request, 'Invalid role.')
        else:
            target.role = new_role
            target.save()
            if new_role:
                messages.success(request, f"{target.name}'s role set to {target.get_role_display()}.")
            else:
                messages.success(request, f"{target.name}'s role has been removed.")
        return redirect('user_management')

    return render(request, 'accounts/user_management.html', {
        'app_users'    : AppUser.objects.order_by('name'),
        'role_choices' : AppUser.ROLE_CHOICES,
    })


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