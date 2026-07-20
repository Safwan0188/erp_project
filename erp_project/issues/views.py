from django.utils import timezone
from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from .forms import IssueForm, DeveloperIssueEditForm, QAIssueEditForm, CategoryForm, IssueTypeForm, StatusForm, QAStatusForm, DeliveryStatusForm
from .models import Issue, Category, IssueType, Status, QAStatus, DeliveryStatus, Developer, QAMember, Notification, IssueAssignmentHistory, QAAssignmentHistory
from accounts.utils import get_current_app_user
from accounts import permissions as perms

def issue_create(request):
    current_user = get_current_app_user(request)
    if not perms.can_view_create_issue_page(current_user):
        return redirect('issue_list')

    if request.method == 'POST':
        form = IssueForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('issue_list')
    else:
        form = IssueForm()
    return render(request, 'issues/issue_form.html', {'form': form})


def issue_list(request):
    current_user = get_current_app_user(request)
    all_issues = Issue.objects.all().order_by('-issue_id')

    query           = request.GET.get('q', '')
    status          = request.GET.get('status', '')
    category        = request.GET.get('category', '')
    type_           = request.GET.get('type', '')
    qa_status       = request.GET.get('qa_status', '')
    delivery_status = request.GET.get('delivery_status', '')
    date_from       = request.GET.get('date_from', '')
    date_to         = request.GET.get('date_to', '')

    if query:
        all_issues = all_issues.filter(
            Q(issue_id__icontains=query)          |
            Q(project__icontains=query)           |
            Q(module__icontains=query)            |
            Q(task_name__icontains=query)         |
            Q(reported_by__icontains=query)       |
            Q(assigned_to__name__icontains=query)
        )
    if status:
        all_issues = all_issues.filter(status__name=status)
    if category:
        all_issues = all_issues.filter(category__name=category)
    if type_:
        all_issues = all_issues.filter(type__name=type_)
    if qa_status:
        all_issues = all_issues.filter(qa_status__name=qa_status)
    if delivery_status:
        all_issues = all_issues.filter(delivery_status__name=delivery_status)
    if date_from:
        all_issues = all_issues.filter(approx_delivery__gte=date_from)
    if date_to:
        all_issues = all_issues.filter(approx_delivery__lte=date_to)

    pending_issues = all_issues.filter(
        Q(status__name__in=['Open', 'On Hold']) |
        Q(qa_status__name__in=['Open', 'On Hold'])
    ).distinct()

    inprogress_issues = all_issues.filter(
        Q(status__name='In Progress') |
        Q(qa_status__name='In Progress')
    ).distinct()

    completed_issues = all_issues.filter(
        Q(status__name='Completed') |
        Q(qa_status__name__in=['Approved', 'Rejected'])
    ).distinct()

    delivered_issues = all_issues.filter(
        delivery_status__name='Delivered'
    ).order_by('-issue_id')

    # Developers get their own sub-lists based purely on Development
    # Status (not mixed with QA Status like the general/admin view),
    # since a Developer's worklist should reflect their own status only.
    if current_user and current_user.role == 'developer':
        dev = perms.get_linked_developer(current_user)
        if dev:
            dev_issues = all_issues.filter(assigned_to=dev)
            pending_issues    = dev_issues.filter(status__name__in=['Open', 'On Hold'])
            inprogress_issues = dev_issues.filter(status__name='In Progress')
            completed_issues  = dev_issues.filter(status__name='Completed')
            delivered_issues  = dev_issues.filter(delivery_status__name='Delivered').order_by('-issue_id')
        else:
            pending_issues    = pending_issues.none()
            inprogress_issues = inprogress_issues.none()
            completed_issues  = completed_issues.none()
            delivered_issues  = delivered_issues.none()

    # QA gets a hybrid: the Pending sub-list is a shared pool of every
    # unclaimed issue (qa_by empty) still Open/On Hold, visible to every
    # QA member, plus their own claimed issues that are still Open/On
    # Hold. Once an issue is claimed (qa_by set), it moves into that QA
    # member's personal sub-lists the same way Developer's do — driven
    # purely by QA Status.
    if current_user and current_user.role == 'qa':
        qa = perms.get_linked_qamember(current_user)
        if qa:
            unclaimed = all_issues.filter(qa_by__isnull=True)
            own       = all_issues.filter(qa_by=qa)
            pending_issues    = (unclaimed | own).filter(qa_status__name__in=['Open', 'On Hold']).distinct()
            inprogress_issues = own.filter(qa_status__name='In Progress')
            completed_issues  = own.filter(qa_status__name__in=['Approved', 'Rejected'])
            delivered_issues  = own.filter(delivery_status__name='Delivered').order_by('-issue_id')
        else:
            pending_issues    = pending_issues.none()
            inprogress_issues = inprogress_issues.none()
            completed_issues  = completed_issues.none()
            delivered_issues  = delivered_issues.none()

    return render(request, 'issues/issue_list.html', {
        'issues'               : all_issues,
        'query'                : query,
        'status'               : status,
        'category'             : category,
        'type'                 : type_,
        'qa_status'            : qa_status,
        'delivery_status'      : delivery_status,
        'date_from'            : date_from,
        'date_to'              : date_to,
        'all_statuses'         : Status.objects.all(),
        'all_categories'       : Category.objects.all(),
        'all_types'            : IssueType.objects.all(),
        'all_qa_statuses'      : QAStatus.objects.all(),
        'all_delivery_statuses': DeliveryStatus.objects.all(),
        'pending_issues'       : pending_issues,
        'inprogress_issues'    : inprogress_issues,
        'completed_issues'     : completed_issues,
        'delivered_issues'     : delivered_issues,
    })


def issue_edit(request, pk):
    issue = get_object_or_404(Issue, pk=pk)
    current_user = get_current_app_user(request)

    if not perms.can_edit_issue(current_user, issue):
        # Not allowed to edit this issue at all (e.g. a Developer viewing
        # an issue not assigned to them) — send them to the read-only view.
        return redirect('issue_detail', pk=pk)

    if current_user.role == 'developer':
        if request.method == 'POST':
            form = DeveloperIssueEditForm(request.POST, instance=issue)
            if form.is_valid():
                form.save()
                return redirect('issue_detail', pk=pk)
        else:
            form = DeveloperIssueEditForm(instance=issue)
        return render(request, 'issues/issue_form_developer.html', {'form': form, 'issue': issue})

    if current_user.role == 'qa':
        qa = perms.get_linked_qamember(current_user)
        if request.method == 'POST':
            form = QAIssueEditForm(request.POST, instance=issue, qa_member=qa)
            if form.is_valid():
                form.save()
                return redirect('issue_detail', pk=pk)
        else:
            form = QAIssueEditForm(instance=issue, qa_member=qa)
        return render(request, 'issues/issue_form_qa.html', {'form': form, 'issue': issue})

    if request.method == 'POST':
        form = IssueForm(request.POST, request.FILES, instance=issue)
        if form.is_valid():
            form.save()
            return redirect('issue_list')
    else:
        form = IssueForm(instance=issue)
    return render(request, 'issues/issue_form.html', {'form': form, 'edit': True})


def issue_delete(request, pk):
    issue = get_object_or_404(Issue, pk=pk)
    current_user = get_current_app_user(request)
    if not perms.can_delete_issue(current_user):
        return redirect('issue_detail', pk=pk)
    if request.method == 'POST':
        issue.delete()
        return redirect('issue_list')
    return render(request, 'issues/issue_confirm_delete.html', {'issue': issue})


def issue_detail(request, pk):
    issue = get_object_or_404(Issue, pk=pk)
    current_user = get_current_app_user(request)
    return render(request, 'issues/issue_detail.html', {
        'issue'      : issue,
        'can_edit'   : perms.can_edit_issue(current_user, issue),
        'can_delete' : perms.can_delete_issue(current_user),
    })


def dashboard(request):
    today  = timezone.now().date()
    
    # All issues for delivery summary
    all_issues = Issue.objects.all()
    
    # Active issues — exclude delivered and undelivered
    issues = Issue.objects.exclude(
        delivery_status__name__in=['Delivered', 'Undelivered']
    )

    # 11.1 Issue Summary by Category
    total    = issues.count()
    critical = issues.filter(category__name='Critical').count()
    high     = issues.filter(category__name='High').count()
    medium   = issues.filter(category__name='Medium').count()
    regular  = issues.filter(category__name='Regular').count()

    # 11.2 Development Status Summary
    open_count  = issues.filter(status__name='Open').count()
    in_progress = issues.filter(status__name='In Progress').count()
    on_hold     = issues.filter(status__name='On Hold').count()
    completed   = issues.filter(status__name='Completed').count()
    reopened    = issues.filter(status__name='Reopened').count()

    # 11.3 Delivery Summary
    delivered   = all_issues.filter(delivery_status__name='Delivered').count()
    undelivered = all_issues.filter(delivery_status__name='Undelivered').count()
    on_track    = all_issues.exclude(
        delivery_status__name__in=['Delivered', 'Undelivered']
    ).filter(approx_delivery__gte=today).count()
    delayed     = all_issues.exclude(
        delivery_status__name__in=['Delivered', 'Undelivered']
    ).filter(approx_delivery__lt=today).count()

    # 11.4 Developer Performance — uses all issues
    developers = all_issues.exclude(assigned_to__isnull=True).values('assigned_to__name').annotate(
        total_assigned = Count('issue_id'),
        completed      = Count('issue_id', filter=Q(status__name='Completed')),
        in_progress    = Count('issue_id', filter=Q(status__name='In Progress')),
        delayed        = Count('issue_id', filter=Q(approx_delivery__lt=today) & ~Q(status__name='Completed')),
    ).order_by('assigned_to__name')

    for dev in developers:
        total_dev = dev['total_assigned']
        dev['resolution_rate'] = round((dev['completed'] / total_dev) * 100) if total_dev > 0 else 0

    return render(request, 'issues/dashboard.html', {
        'total'       : total,
        'critical'    : critical,
        'high'        : high,
        'medium'      : medium,
        'regular'     : regular,
        'open_count'  : open_count,
        'in_progress' : in_progress,
        'on_hold'     : on_hold,
        'completed'   : completed,
        'reopened'    : reopened,
        'total_tasks' : all_issues.count(),
        'delivered'   : delivered,
        'undelivered' : undelivered,
        'on_track'    : on_track,
        'delayed'     : delayed,
        'developers'  : developers,
    })


def settings_page(request):
    current_user = get_current_app_user(request)
    if not perms.can_view_settings_page(current_user):
        return redirect('issue_list')
    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'category':
            form = CategoryForm(request.POST)
            if form.is_valid():
                form.save()

        elif form_type == 'issue_type':
            form = IssueTypeForm(request.POST)
            if form.is_valid():
                form.save()

        elif form_type == 'status':
            form = StatusForm(request.POST)
            if form.is_valid():
                form.save()

        elif form_type == 'qa_status':
            form = QAStatusForm(request.POST)
            if form.is_valid():
                form.save()

        elif form_type == 'delivery_status':
            form = DeliveryStatusForm(request.POST)
            if form.is_valid():
                form.save()

        elif form_type == 'category_time':
            category_id = request.POST.get('category_id')
            category    = get_object_or_404(Category, pk=category_id)
            value       = request.POST.get('default_time_value') or None
            unit        = request.POST.get('default_time_unit') or None
            category.default_time_value = value
            category.default_time_unit  = unit
            category.save()

        elif form_type == 'delete':
            model_name = request.POST.get('model_name')
            obj_id     = request.POST.get('obj_id')

            model_map = {
                'category'        : Category,
                'issue_type'      : IssueType,
                'status'          : Status,
                'qa_status'       : QAStatus,
                'delivery_status' : DeliveryStatus,
                'qa_member'       : QAMember,
                'developer'       : Developer,
            }

            if model_name in model_map:
                obj = get_object_or_404(model_map[model_name], pk=obj_id)
                if model_name == 'developer' and obj.linked_user_id:
                    # Role-driven Developer — must be managed by revoking
                    # the Developer role in Accounts, not deleted here.
                    pass
                elif model_name == 'qa_member' and obj.linked_user_id:
                    # Role-driven QA member — must be managed by revoking
                    # the QA role in Accounts, not deleted here.
                    pass
                elif not obj.is_default:
                    obj.delete()

        return redirect('settings_page')

    context = {
        'categories'           : Category.objects.all(),
        'issue_types'          : IssueType.objects.all(),
        'statuses'             : Status.objects.all(),
        'qa_statuses'          : QAStatus.objects.all(),
        'delivery_statuses'    : DeliveryStatus.objects.all(),
        'qa_members'           : QAMember.objects.all(),
        'developers'           : Developer.objects.all(),
        'category_form'        : CategoryForm(),
        'type_form'            : IssueTypeForm(),
        'status_form'          : StatusForm(),
        'qa_status_form'       : QAStatusForm(),
        'delivery_status_form' : DeliveryStatusForm(),
    }
    return render(request, 'issues/settings.html', context)


def notification_list(request):
    current_user = get_current_app_user(request)
    notifications = Notification.objects.all().order_by('-created_at')

    if current_user and current_user.role == 'developer':
        dev = perms.get_linked_developer(current_user)
        if dev:
            # Only notifications on issues currently assigned to this
            # developer, and only from their current assignment window
            # onward (not from before they were assigned).
            active_windows = IssueAssignmentHistory.objects.filter(
                developer=dev, unassigned_at__isnull=True
            )
            visible_q = Q(pk__in=[])
            for window in active_windows:
                visible_q |= Q(issue_id=window.issue_id, created_at__gte=window.assigned_at)
            notifications = notifications.filter(visible_q) if active_windows else notifications.none()
        else:
            notifications = notifications.none()

    if current_user and current_user.role == 'qa':
        qa = perms.get_linked_qamember(current_user)
        if qa:
            active_windows = QAAssignmentHistory.objects.filter(
                qa_member=qa, unassigned_at__isnull=True
            )
            visible_q = Q(pk__in=[])
            for window in active_windows:
                visible_q |= Q(issue_id=window.issue_id, created_at__gte=window.assigned_at)
            notifications = notifications.filter(visible_q) if active_windows else notifications.none()
        else:
            notifications = notifications.none()

    unread_count = notifications.filter(is_read=False).count()
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'issues/notifications.html', {
        'notifications' : notifications,
        'unread_count'  : unread_count,
    })


def get_unread_count(request):
    current_user = get_current_app_user(request)
    notifications = Notification.objects.filter(is_read=False)

    if current_user and current_user.role == 'developer':
        dev = perms.get_linked_developer(current_user)
        if dev:
            active_windows = IssueAssignmentHistory.objects.filter(
                developer=dev, unassigned_at__isnull=True
            )
            visible_q = Q(pk__in=[])
            for window in active_windows:
                visible_q |= Q(issue_id=window.issue_id, created_at__gte=window.assigned_at)
            notifications = notifications.filter(visible_q) if active_windows else notifications.none()
        else:
            notifications = notifications.none()

    if current_user and current_user.role == 'qa':
        qa = perms.get_linked_qamember(current_user)
        if qa:
            active_windows = QAAssignmentHistory.objects.filter(
                qa_member=qa, unassigned_at__isnull=True
            )
            visible_q = Q(pk__in=[])
            for window in active_windows:
                visible_q |= Q(issue_id=window.issue_id, created_at__gte=window.assigned_at)
            notifications = notifications.filter(visible_q) if active_windows else notifications.none()
        else:
            notifications = notifications.none()

    return {'unread_count': notifications.count()}