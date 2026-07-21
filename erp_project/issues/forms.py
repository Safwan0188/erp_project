import datetime
from django import forms
from .models import Issue, Category, IssueType, Status, QAStatus, DeliveryStatus, Developer, QAMember


class IssueForm(forms.ModelForm):
    class Meta:
        model = Issue
        # created_by is deliberately excluded - it's set server-side from
        # the logged-in AppUser (see issue_create in views.py), never
        # typed or edited by anyone, admin included.
        exclude = ['created_by']
        widgets = {
            'reported_date'      : forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'approx_delivery'    : forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'completion_date'    : forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'readonly': 'readonly'}),
            'description'        : forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'developer_comments' : forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'qa_comments'        : forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'project'            : forms.TextInput(attrs={'class': 'form-control'}),
            'module'             : forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Authentication'}),
            'task_name'          : forms.TextInput(attrs={'class': 'form-control', 'style': 'max-width:400px;'}),
            'attachments'        : forms.ClearableFileInput(attrs={'class': 'form-control', 'multiple': False}),
            'allocated_time'     : forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 3 - 5 hrs or 10 - 12 days'}),
            'category'           : forms.Select(attrs={'class': 'form-select'}),
            'type'               : forms.Select(attrs={'class': 'form-select'}),
            'status'             : forms.Select(attrs={'class': 'form-select'}),
            'qa_status'          : forms.Select(attrs={'class': 'form-select'}),
            'delivery_status'    : forms.Select(attrs={'class': 'form-select'}),
            'assigned_to'        : forms.Select(attrs={'class': 'form-select'}),
            'qa_by'              : forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = datetime.date.today().isoformat()
        self.fields['reported_date'].widget.attrs['min'] = today

        # Only offer active developers, but keep the currently-assigned
        # one selectable even if their role was since revoked, so an
        # existing assignment doesn't silently break the form.
        active_devs = Developer.objects.filter(is_active=True)
        if self.instance and self.instance.pk and self.instance.assigned_to_id and not self.instance.assigned_to.is_active:
            active_devs = active_devs | Developer.objects.filter(pk=self.instance.assigned_to_id)
        self.fields['assigned_to'].queryset = active_devs.order_by('name')

        # Same active/keep-currently-assigned pattern as assigned_to above.
        active_qa = QAMember.objects.filter(is_active=True)
        if self.instance and self.instance.pk and self.instance.qa_by_id and not self.instance.qa_by.is_active:
            active_qa = active_qa | QAMember.objects.filter(pk=self.instance.qa_by_id)
        self.fields['qa_by'].queryset = active_qa.order_by('name')

        if not self.instance.pk:
            self.fields['reported_date'].initial               = datetime.date.today()
            self.fields['approx_delivery'].widget.attrs['min'] = today
            self.fields['completion_date'].widget.attrs['min'] = today
        else:
            if self.instance.reported_date:
                reported = self.instance.reported_date.isoformat()
                self.fields['reported_date'].widget.attrs['min']   = reported
                self.fields['approx_delivery'].widget.attrs['min'] = reported
                self.fields['completion_date'].widget.attrs['min'] = reported
            else:
                self.fields['approx_delivery'].widget.attrs['min'] = today
                self.fields['completion_date'].widget.attrs['min'] = today

    def clean(self):
        cleaned_data    = super().clean()
        status          = cleaned_data.get('status')
        qa_status       = cleaned_data.get('qa_status')
        delivery_status = cleaned_data.get('delivery_status')
        assigned_to     = cleaned_data.get('assigned_to')

        # If assigned, status cannot be blank
        if assigned_to and not status:
            self.add_error('status', 'Development Status is required when issue is assigned.')

        # If Dev Status = Completed, QA Status cannot be blank
        if status and status.name == 'Completed' and not qa_status:
            self.add_error('qa_status', 'QA Status is required when Development Status is Completed.')

        # Delivery Status can only be set when Dev=Completed and QA=Approved
        if delivery_status:
            if not (status and status.name == 'Completed' and
                    qa_status and qa_status.name == 'Approved'):
                self.add_error('delivery_status', 'Delivery Status can only be set when Development Status is Completed and QA Status is Approved.')

        # If Dev=Completed and QA=Approved, Delivery Status cannot be blank
        if (status and status.name == 'Completed' and
                qa_status and qa_status.name == 'Approved' and
                not delivery_status):
            self.add_error('delivery_status', 'Delivery Status is required when Development Status is Completed and QA Status is Approved.')

        return cleaned_data


class DeveloperIssueEditForm(forms.ModelForm):
    """
    Restricted edit form for the Developer role — only the fields a
    Developer may change on an issue assigned to them. Everything else
    on the Issue stays whatever it already was. The model's signals
    still run exactly as they do for any other save (e.g. Completed ->
    QA Status auto-opens, Rejected -> Reopened, etc.) since that logic
    lives on Issue itself, not in this form.
    """
    class Meta:
        model = Issue
        fields = ['allocated_time', 'approx_delivery', 'status', 'developer_comments']
        widgets = {
            'allocated_time'     : forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 3 - 5 hrs or 10 - 12 days'}),
            'approx_delivery'    : forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'status'             : forms.Select(attrs={'class': 'form-select'}),
            'developer_comments' : forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.reported_date:
            self.fields['approx_delivery'].widget.attrs['min'] = self.instance.reported_date.isoformat()


class QAIssueEditForm(forms.ModelForm):
    """
    Restricted edit form for the QA role — only the fields a QA member
    may change on an issue. qa_by works as a self-claim: while an issue
    is unassigned, the dropdown offers only the current QA member's own
    name (they can't hand an issue to someone else). Once qa_by is set,
    it's locked (disabled) permanently — not even the assigned QA member
    can change it afterward, matching the same "once assigned" lock the
    Developer's assigned_to field already has implicitly. qa_status/
    qa_comments stay editable throughout, same as any other role's saves.
    """
    class Meta:
        model = Issue
        fields = ['qa_by', 'qa_status', 'qa_comments']
        widgets = {
            'qa_by'       : forms.Select(attrs={'class': 'form-select'}),
            'qa_status'   : forms.Select(attrs={'class': 'form-select'}),
            'qa_comments' : forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def __init__(self, *args, qa_member=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.qa_member = qa_member

        if self.instance and self.instance.pk and self.instance.qa_by_id:
            # Already claimed — lock qa_by, whoever claimed it.
            self.fields['qa_by'].disabled = True
        elif qa_member is not None:
            # Not yet claimed — the only valid choice is "assign it to me".
            self.fields['qa_by'].queryset = QAMember.objects.filter(pk=qa_member.pk)

class BAIssueForm(forms.ModelForm):
    """
    Restricted form for the Business Analyst role — used for both
    creating a new issue and (until it locks) editing one of their own.
    Only the fields a BA is allowed to touch; every other Issue field
    keeps whatever value it already has (blank on creation).

    assigned_to is included and optional — a BA may pick a Developer
    right away or leave it blank for an admin/dev to assign later.

    "Reported By" is deliberately NOT in this form - it's just a display
    of created_by, which is set server-side from the logged-in AppUser
    (see issue_create/issue_edit in views.py), never typed or edited.
    """
    class Meta:
        model = Issue
        fields = ['project', 'category', 'type', 'module', 'task_name', 'description', 'attachments', 'assigned_to']
        widgets = {
            'project'     : forms.TextInput(attrs={'class': 'form-control'}),
            'category'    : forms.Select(attrs={'class': 'form-select'}),
            'type'        : forms.Select(attrs={'class': 'form-select'}),
            'module'      : forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Authentication'}),
            'task_name'   : forms.TextInput(attrs={'class': 'form-control'}),
            'description' : forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'attachments' : forms.ClearableFileInput(attrs={'class': 'form-control', 'multiple': False}),
            'assigned_to' : forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_to'].required = False
        # Same active/keep-currently-assigned pattern as the admin IssueForm.
        active_devs = Developer.objects.filter(is_active=True)
        if self.instance and self.instance.pk and self.instance.assigned_to_id and not self.instance.assigned_to.is_active:
            active_devs = active_devs | Developer.objects.filter(pk=self.instance.assigned_to_id)
        self.fields['assigned_to'].queryset = active_devs.order_by('name')

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Critical'})}


class IssueTypeForm(forms.ModelForm):
    class Meta:
        model = IssueType
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Bug'})}


class StatusForm(forms.ModelForm):
    class Meta:
        model = Status
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. In Progress'})}


class QAStatusForm(forms.ModelForm):
    class Meta:
        model = QAStatus
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Approved'})}


class DeliveryStatusForm(forms.ModelForm):
    class Meta:
        model = DeliveryStatus
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Delivered'})}


class QAMemberForm(forms.ModelForm):
    class Meta:
        model = QAMember
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. John QA'})}


class DeveloperForm(forms.ModelForm):
    class Meta:
        model = Developer
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. John Doe'})}