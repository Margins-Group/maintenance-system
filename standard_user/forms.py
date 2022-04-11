from django import forms
from printer_support.models import *
from phonenumber_field.formfields import PhoneNumberField
from django.forms.widgets import NumberInput


class UpdateScheduleFormU(forms.ModelForm):

    class Meta:
        model = Schedule
        exclude = ['cancellation_reason', 'cancelled', 'delay_maintenance_reason', 'delay_maintenance_date',
                   'user', 'date_cancelled', 'updated_at', 'created_at', 'fixed_by', 'approved_by', 'requested_by',
                   'action_status']

    def clean_printer_number(self):
        return self.cleaned_data['printer_number'].upper()

    def clean_box_number(self):
        return self.cleaned_data['box_number'].upper()


class CancelMaintenanceForm(forms.Form):
    cancellation_reason = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))


class RateAdminForm(forms.Form):
    # admin = forms.ModelChoiceField(queryset=User.objects.filter(is_staff=True).exclude(is_superuser=True), label='Select technician to be rated')
    comment = forms.CharField(max_length=100, required=False)


class HelpDeskForm(forms.Form):
    issue_category = forms.ChoiceField(choices=HelpDesk.category, label='Select issue category')
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}),
                                  help_text='Description of the issue category selected')


class ContactForm(forms.Form):
    email = forms.EmailField(max_length=254, required=True)
    name = forms.CharField(max_length=60, required=True)
    phone = PhoneNumberField(required=True, max_length=13, initial='+233', help_text='Include country code')
    message = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))


class RateTrainingForm(forms.Form):
    topics = forms.ChoiceField(choices=UserRating.options, label='Topic(s) treated were relevant to my line of work')
    slides = forms.ChoiceField(choices=UserRating.options, label='The training slides/sheets/Procedure and activities were helpful')
    duration = forms.ChoiceField(choices=UserRating.options, label='The duration of the training was appropriate')
    solution = forms.ChoiceField(choices=UserRating.options, label='The facilitator was technically inclined or vested on the solution')
    style = forms.ChoiceField(choices=UserRating.options, label='The facilitator’s style, delivery and instruction skills were agreeable and well-suited to the content')
    q_response = forms.ChoiceField(choices=UserRating.options, label='The facilitator encouraged discussion and responded to questions satisfactorily')
    location = forms.ChoiceField(choices=UserRating.options, label='The location and facilities (room layout, equipment, personal comfort) were satisfactory')
    config_install = forms.ChoiceField(choices=UserRating.options, label='The installation and configuration training met my expectations')
    training_benefit = forms.ChoiceField(choices=UserRating.options, label='Overall, I found this training beneficial')
    recommend = forms.ChoiceField(choices=UserRating.options, label='I will recommend this training to a colleague')
    # stem = forms.ChoiceField(choices=UserRating.options, label='STEM')
    # art = forms.ChoiceField(choices=UserRating.options, label='ART')
    # time = forms.ChoiceField(choices=UserRating.options, label='Time and Attendance solution')
    # cctv = forms.ChoiceField(choices=UserRating.options, label='CCTV surveillance system')
    # loyalty = forms.ChoiceField(choices=UserRating.options, label='Loyalty solution')
    comment = forms.CharField(max_length=100, required=False, label='Additional Comments')


class ScheduleLaminatorFormU(forms.Form):
    box_number = forms.CharField(max_length=20, min_length=4, required=True)
    laminator_number = forms.CharField(max_length=7, min_length=7, required=True)
    pickup_parts = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=LaminatorSchedule.pparts)
    client = forms.ModelChoiceField(queryset=Client.objects.all().exclude(action_status='Pending'))
    pickup_date = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}))
    problem = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=LaminatorSchedule.issues,
                                        help_text='Ignore the "problem" field if not certain')
    other_problem = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}), required=False)

    def clean_box_number(self):
        return self.cleaned_data['box_number'].upper()


class UpdatePendingFormU(forms.ModelForm):

    class Meta:
        model = LaminatorSchedule
        exclude = ['cancellation_reason', 'cancelled', 'user', 'date_cancelled', 'updated_at', 'created_at', 'fixed_by',
                   'approved_by', 'requested_by', 'action_status', 'assigned_technicians']

    def clean_laminator_number(self):
        return self.cleaned_data['laminator_number'].upper()

    def clean_box_number(self):
        return self.cleaned_data['box_number'].upper()


class ScheduleMRWFormU(forms.Form):
    mrw_number = forms.CharField(max_length=8, min_length=7, required=True, label='MRW Number')
    pickup_parts = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=MRWSchedule.pparts)
    client = forms.ModelChoiceField(queryset=Client.objects.all().exclude(action_status='Pending'))
    pickup_date = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}))
    problem = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))


class UpdateMRWPendingFormU(forms.ModelForm):

    class Meta:
        model = MRWSchedule
        exclude = ['cancellation_reason', 'cancelled', 'user', 'date_cancelled', 'updated_at', 'created_at', 'fixed_by',
                   'approved_by', 'requested_by', 'action_status', 'assigned_technicians']

    def clean_mrw_number(self):
        return self.cleaned_data['mrw_number'].upper()


class ScheduleISSFormU(forms.Form):
    iss_number = forms.CharField(max_length=9, min_length=7, required=True, label='ISS Number')
    pickup_parts = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=ISSSchedule.pparts)
    client = forms.ModelChoiceField(queryset=Client.objects.all().exclude(action_status='Pending'))
    pickup_date = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}))
    problem = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))


class UpdateISSPendingFormU(forms.ModelForm):

    class Meta:
        model = ISSSchedule
        exclude = ['cancellation_reason', 'cancelled', 'user', 'date_cancelled', 'updated_at', 'created_at', 'fixed_by',
                   'approved_by', 'requested_by', 'action_status', 'assigned_technicians']

    def clean_iss_number(self):
        return self.cleaned_data['iss_number'].upper()
