import datetime
from django import forms
from .models import Issue, Category, IssueType, Status, QAStatus, DeliveryStatus, Developer, QAMember


class IssueForm(forms.ModelForm):
    class Meta:
        model = Issue
        fields = '__all__'
        widgets = {
            'reported_date'      : forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'approx_delivery'    : forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'completion_date'    : forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description'        : forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'developer_comments' : forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'qa_comments'        : forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'project'            : forms.TextInput(attrs={'class': 'form-control'}),
            'module'             : forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Authentication'}),
            'task_name'          : forms.TextInput(attrs={'class': 'form-control', 'style': 'max-width:400px;'}),
            'attachments'        : forms.ClearableFileInput(attrs={'class': 'form-control', 'multiple': False}),
            'reported_by'        : forms.TextInput(attrs={'class': 'form-control'}),
            'allocated_time'     : forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 3 - 5 hrs or 10 - 12 days'}),
            'category'           : forms.Select(attrs={'class': 'form-select'}),
            'type'               : forms.Select(attrs={'class': 'form-select'}),
            'status'             : forms.Select(attrs={'class': 'form-select'}),
            'qa_status'          : forms.Select(attrs={'class': 'form-select'}),
            'delivery_status'    : forms.Select(attrs={'class': 'form-select'}),
            'assigned_to'        : forms.Select(attrs={'class': 'form-select'}),
            'qa_by'              : forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = datetime.date.today().isoformat()
        self.fields['reported_date'].widget.attrs['min'] = today
        self.fields['qa_by'].queryset = QAMember.objects.all()
        if not self.instance.pk:
            self.fields['reported_date'].initial          = datetime.date.today()
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