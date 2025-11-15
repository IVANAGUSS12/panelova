from django import forms
from .models import Patient, Attachment

class QRPatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            'full_name', 'dni', 'phone', 'email',
            'coverage', 'doctor', 'service', 'planned_date',
            'external_observations',
        ]
        widgets = {
            'planned_date': forms.DateInput(attrs={'type': 'date'}),
            'external_observations': forms.Textarea(attrs={'rows': 3}),
        }

class AttachmentForm(forms.ModelForm):
    class Meta:
        model = Attachment
        fields = ['type', 'file']

class PatientFilterForm(forms.Form):
    q = forms.CharField(required=False, label='Buscar')
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos')] + Patient.STATUS_CHOICES,
        label='Estado'
    )
    coverage = forms.CharField(required=False, label='Cobertura')
    doctor = forms.CharField(required=False, label='Médico')
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

class ReprogramForm(forms.ModelForm):
    reprogram_reason = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={'rows': 3}),
        label='Motivo de reprogramación'
    )

    class Meta:
        model = Patient
        fields = ['planned_date']
        widgets = {
            'planned_date': forms.DateInput(attrs={'type': 'date'}),
        }
