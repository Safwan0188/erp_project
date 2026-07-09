from django.utils import timezone
from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from .forms import IssueForm, CategoryForm, IssueTypeForm, StatusForm, QAStatusForm, DeliveryStatusForm, QAMemberForm, DeveloperForm
from .models import Issue, Category, IssueType, Status, QAStatus, DeliveryStatus, Developer, QAMember, Notification


def issue_create(request):
    if request.method == 'POST':
        form = IssueForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('issue_list')
    else:
        form = IssueForm()
    return render(request, 'issues/issue_form.html', {'form': form})


def issue_list(request):
    issues = Issue.objects.all().order_by('-issue_id')

    query           = request.GET.get('q', '')
    status          = request.GET.get('status', '')
    category        = request.GET.get('category', '')
    type_           = request.GET.get('type', '')
    qa_status       = request.GET.get('qa_status', '')
    delivery_status = request.GET.get('delivery_status', '')
    date_from       = request.GET.get('date_from', '')
    date_to         = request.GET.get('date_to', '')

    if query:
        issues = issues.filter(
            Q(issue_id__icontains=query)          |
            Q(project__icontains=query)           |
            Q(assigned_to__name__icontains=query) |
            Q(reported_by__icontains=query)       |
            Q(task_name__icontains=query)         |
            Q(module__icontains=query)
        )

    if status:
        issues = issues.filter(status__name=status)
    if category:
        issues = issues.filter(category__name=category)
    if type_:
        issues = issues.filter(type__name=type_)
    if qa_status:
        issues = issues.filter(qa_status__name=qa_status)
    if delivery_status:
        issues = issues.filter(delivery_status__name=delivery_status)
    if date_from:
        issues = issues.filter(approx_delivery__gte=date_from)
    if date_to:
        issues = issues.filter(approx_delivery__lte=date_to)

    return render(request, 'issues/issue_list.html', {
    # existing context
    'issues'               : issues,
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
    # 4 tab sublists
    'pending_issues'   : Issue.objects.filter(
        Q(status__name__in=['Open', 'On Hold']) |
        Q(qa_status__name__in=['Open', 'On Hold'])
    ).distinct().order_by('-issue_id'),
    'inprogress_issues': Issue.objects.filter(
        Q(status__name='In Progress') |
        Q(qa_status__name='In Progress')
    ).distinct().order_by('-issue_id'),
    'completed_issues' : Issue.objects.filter(
         Q(status__name='Completed') |
        Q(qa_status__name__in=['Approved', 'Rejected'])
    ).distinct().order_by('-issue_id'),
})

def issue_edit(request, pk):
    issue = get_object_or_404(Issue, pk=pk)
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
    if request.method == 'POST':
        issue.delete()
        return redirect('issue_list')
    return render(request, 'issues/issue_confirm_delete.html', {'issue': issue})


def issue_detail(request, pk):
    issue = get_object_or_404(Issue, pk=pk)
    return render(request, 'issues/issue_detail.html', {'issue': issue})


def dashboard(request):
    today  = timezone.now().date()
    issues = Issue.objects.all()

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
    delivered   = issues.filter(delivery_status__name='Delivered').count()
    undelivered = issues.filter(delivery_status__name='Undelivered').count()
    on_track    = issues.exclude(delivery_status__name='Delivered').filter(approx_delivery__gte=today).count()
    delayed     = issues.exclude(delivery_status__name='Delivered').filter(approx_delivery__lt=today).count()

    # 11.4 Developer Performance
    developers = issues.exclude(assigned_to__isnull=True).values('assigned_to__name').annotate(
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
        'total_tasks' : total,
        'delivered'   : delivered,
        'undelivered' : undelivered,
        'on_track'    : on_track,
        'delayed'     : delayed,
        'developers'  : developers,
    })


def settings_page(request):
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

        elif form_type == 'qa_member':
            form = QAMemberForm(request.POST)
            if form.is_valid():
                form.save()

        elif form_type == 'developer':
            form = DeveloperForm(request.POST)
            if form.is_valid():
                form.save()

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
                if not obj.is_default:
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
        'qa_member_form'       : QAMemberForm(),
        'developer_form'       : DeveloperForm(),
    }
    return render(request, 'issues/settings.html', context)


def notification_list(request):
    notifications = Notification.objects.all().order_by('-created_at')
    unread_count  = notifications.filter(is_read=False).count()
    Notification.objects.filter(is_read=False).update(is_read=True)
    return render(request, 'issues/notifications.html', {
        'notifications' : notifications,
        'unread_count'  : unread_count,
    })


def get_unread_count(request):
    return {'unread_count': Notification.objects.filter(is_read=False).count()}