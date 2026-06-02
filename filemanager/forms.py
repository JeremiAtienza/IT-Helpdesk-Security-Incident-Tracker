from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django import forms
from .models import VaultFile, IncidentTicket, Ticket, TicketAttachment, KnowledgeBaseArticle

class VaultFileForm(forms.ModelForm):
    class Meta:
        model = VaultFile
        fields = ['title', 'document']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Q3 Financial Report'}),
            'document': forms.FileInput(attrs={'class': 'form-control'}),
        }

class IncidentTicketForm(forms.ModelForm):
    class Meta:
        model = IncidentTicket
        fields = ['title', 'description', 'status', 'is_resolved']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Incident summary'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Describe the issue or security incident'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'is_resolved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'is_resolved': 'Mark as resolved',
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
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'category', 'priority']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
        }


class TicketAttachmentForm(forms.ModelForm):
    class Meta:
        model = TicketAttachment
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }


class KnowledgeBaseSearchForm(forms.Form):
    query = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search help articles'}))