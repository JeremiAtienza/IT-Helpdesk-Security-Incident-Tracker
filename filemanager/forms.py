from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django import forms
from .models import Category, VaultFile, IncidentTicket, Ticket, TicketAttachment, TicketComment, KnowledgeBaseArticle, IncidentAttachment

class VaultFileForm(forms.ModelForm):
    class Meta:
        model = VaultFile
        fields = ['title', 'document']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Q3 Financial Report'}),
            'document': forms.FileInput(attrs={'class': 'form-control'}),
        }

class IncidentTicketForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=True,
        empty_label='-- Select a category --',
        widget=forms.Select(attrs={'class': 'form-select', 'style': 'appearance: auto; background-color: #ffffff; color: #112d4e;'})
    )

    class Meta:
        model = IncidentTicket
        fields = ['title', 'description', 'category', 'priority', 'status', 'impact_level', 'affected_assets', 'iocs', 'evidence_summary']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Incident summary'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Describe the issue or security incident'}),
            'category': forms.Select(attrs={'class': 'form-select', 'style': 'appearance: auto; background-color: #ffffff; color: #112d4e;'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'impact_level': forms.Select(attrs={'class': 'form-select'}),
            'affected_assets': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'List affected hosts/IPs/services (JSON or comma-separated)'}),
            'iocs': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Indicators of compromise (hashes, domains, IPs)'}),
            'evidence_summary': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Short evidence summary'}),
        }
        labels = {
            'category': 'Incident Category',
            'priority': 'Priority',
            'is_resolved': 'Mark as resolved',
        }


class IncidentTicketUpdateForm(forms.ModelForm):
    """Form for admin to update incident status, category, priority, and assign personnel"""
    class Meta:
        model = IncidentTicket
        fields = ['status', 'category', 'priority', 'impact_level', 'assignee', 'escalation_level']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select', 'style': 'appearance: auto; background-color: #ffffff; color: #112d4e;'}),
            'category': forms.Select(attrs={'class': 'form-select', 'style': 'appearance: auto; background-color: #ffffff; color: #112d4e;'}),
            'priority': forms.Select(attrs={'class': 'form-select', 'style': 'appearance: auto; background-color: #ffffff; color: #112d4e;'}),
            'impact_level': forms.Select(attrs={'class': 'form-select', 'style': 'appearance: auto; background-color: #ffffff; color: #112d4e;'}),
            'assignee': forms.Select(attrs={'class': 'form-select', 'style': 'appearance: auto; background-color: #ffffff; color: #112d4e;'}),
            'escalation_level': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
        }
        labels = {
            'category': 'Incident Category',
            'priority': 'Priority',
            'impact_level': 'Impact Level',
            'assignee': 'Assign To',
            'escalation_level': 'Escalation Level',
        }

class TicketBulkCloseForm(forms.Form):
    ticket_ids = forms.ModelMultipleChoiceField(
        queryset=IncidentTicket.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Select resolved tickets to bulk close',
    )

    def __init__(self, *args, **kwargs):
        queryset = kwargs.pop('queryset', IncidentTicket.objects.none())
        super().__init__(*args, **kwargs)
        self.fields['ticket_ids'].queryset = queryset

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        # By default, this asks for Username and Password. 
        fields = UserCreationForm.Meta.fields 

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Automatically add Bootstrap classes to all fields
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

class CustomAuthForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply Bootstrap classes to the username and password fields
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control form-control-lg'})


class TicketForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=True,
        empty_label='-- Select a category --',
        widget=forms.Select(attrs={'class': 'form-select', 'style': 'appearance: auto; background-color: #ffffff; color: #112d4e;'})
    )

    class Meta:
        model = Ticket
        fields = ['title', 'description', 'category', 'priority']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'category': forms.Select(attrs={'class': 'form-select', 'style': 'appearance: auto; background-color: #ffffff; color: #112d4e;'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
        }


class TicketAttachmentForm(forms.ModelForm):
    class Meta:
        model = TicketAttachment
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }


class IncidentAttachmentForm(forms.ModelForm):
    class Meta:
        model = IncidentAttachment
        # set model dynamically below
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }


class TicketCommentForm(forms.ModelForm):
    class Meta:
        model = TicketComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Add a comment or note...'}),
        }
        labels = {
            'content': 'Comment',
        }


class TicketSearchForm(forms.Form):
    query = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search tickets...'}))
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + Ticket.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    priority = forms.ChoiceField(
        required=False,
        choices=[('', 'All Priorities')] + Ticket.PRIORITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    category = forms.ModelChoiceField(
        required=False,
        queryset=Category.objects.all(),
        empty_label='All Categories',
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class KnowledgeBaseSearchForm(forms.Form):
    query = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search help articles'}))