from django import forms
from .models import AccountingEntry

class AccountingEntryForm(forms.ModelForm):
    class Meta:
        model = AccountingEntry
        fields = ['description', 'amount', 'entry_type', 'date']
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'form-input', 
                'placeholder': 'e.g., Office Rent, Salary, Offline Sale'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-input', 
                'placeholder': '0.00'
            }),
            'entry_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'date': forms.DateTimeInput(attrs={
                'class': 'form-input', 
                'type': 'datetime-local',
                'step': '1'  # Allow seconds to prevent HTML5 validation errors
            }),
        }
