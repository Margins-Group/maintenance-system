from django import forms
from django.contrib.auth.forms import UserCreationForm
from phonenumber_field.formfields import PhoneNumberField
from django.contrib.auth import get_user_model
from django.forms.widgets import NumberInput
from .models import Client, Schedule, Part, PrinterRMA, Maintenance, Training, Procurement, LaminatorSchedule, \
    ISSSchedule, MRWSchedule, Laminator, ISS, MRW

User = get_user_model()


class LoginForm(forms.ModelForm):
    email = forms.EmailField(initial='you@example.com')
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['email', 'password']


class RegisterForm(UserCreationForm):
    email = forms.EmailField(max_length=254, required=True)
    first_name = forms.CharField(max_length=20, required=True)
    middle_name = forms.CharField(max_length=20, required=False, help_text='Optional')
    last_name = forms.CharField(max_length=20, required=True)
    phone_number = PhoneNumberField(required=True, max_length=13, help_text='Include country code')

    class Meta:
        model = User
        fields = ('email', 'first_name', 'middle_name', 'last_name', 'phone_number', 'password1', 'password2')


class UpdateProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'middle_name', 'last_name', 'email', 'phone_number']

    # def clean_phone_number(self):
    #     return '+233' + self.cleaned_data['phone_number'][-9:]


class AddClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            'client_name',
            'address',
            'rep',
            'rep_email',
            'rep_tel'
        ]


class UpdateClientForm(forms.ModelForm):
    class Meta:
        model = Client
        exclude = ['requested_by', 'approved_by', 'action_status', 'updated_at', 'created_at']


class AddPrinterForm(forms.Form):
    client = forms.ModelChoiceField(queryset=Client.objects.all().exclude(action_status='Pending'))
    box_number = forms.CharField(max_length=20, min_length=6, required=True)
    printer_number = forms.CharField(max_length=6, min_length=6, required=True)
    brand = forms.ChoiceField(choices=Procurement.printer_brands)
    model = forms.ChoiceField(choices=Procurement.printer_models, initial='Select from the list below')
    warranty = forms.IntegerField(label='Enter the warranty years', required=True)
    w_date = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}), label='Warranty Start Date')
    p_date = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}), label='Date Purchased')

    def clean_printer_number(self):
        return self.cleaned_data['printer_number'].upper()

    def clean_box_number(self):
        return self.cleaned_data['box_number'].upper()

    def clean_warranty(self):
        return abs(self.cleaned_data['warranty'])


class ClientPrintersForm(forms.Form):
    client = forms.ModelChoiceField(queryset=Client.objects.all().exclude(action_status='Pending'))


class UpdatePrinterForm(forms.ModelForm):
    class Meta:
        model = Procurement
        exclude = ['created_at', 'updated_at', 'warranty_status']


class AddPrinterRMAForm(forms.Form):
    printer_number = forms.CharField(max_length=6, min_length=6, required=True)
    part_name = forms.ModelChoiceField(queryset=Part.objects.all().exclude(action_status='Pending'))
    faulty_part_barcode = forms.CharField(max_length=20, label='Enter the part serial number you are making RMA request for')

    def clean_printer_number(self):
        return self.cleaned_data['printer_number'].upper()


class UpdateRMAForm(forms.ModelForm):
    class Meta:
        model = PrinterRMA
        exclude = ['created_at', 'updated_at', 'user']

    def clean_printer_number(self):
        return self.cleaned_data['printer_number'].upper()


class ScheduleForm(forms.Form):
    box_number = forms.CharField(max_length=20, min_length=4, required=True)
    printer_number = forms.CharField(max_length=6, min_length=6, required=True)
    pickup_parts = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=Schedule.pparts)
    client = forms.ModelChoiceField(queryset=Client.objects.all().exclude(action_status='Pending'))
    pickup_date = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}))
    problem = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple, choices=Schedule.issues,
                                        help_text='Ignore the "problem" field if not certain')
    assigned_technicians = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=Schedule.technicians,
                                                     required=False, help_text='Ignore this field if not certain')

    def clean_box_number(self):
        return self.cleaned_data['box_number'].upper()


class UpdateScheduleForm(forms.ModelForm):
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


class BothUpdateScheduleForm(forms.Form):
    printer_number = forms.CharField(min_length=6, max_length=6, required=True)
    date_repaired = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}))
    problem = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=Schedule.issues)
    parts_replaced = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=Schedule.rparts,
                                               required=False)
    # fixed_by = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=Schedule.technicians)
    date_delivered = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}))
    old_head_barcode = forms.CharField(min_length=5, max_length=5, required=False, label='Print Head Old Serial Number',
                                       help_text='Only required if you replaced a head, ONLY the 5 ENDING VALUES are required!')
    new_head_barcode = forms.CharField(min_length=5, max_length=5, required=False, label='Print Head New Serial Number',
                                       help_text='Only required if you replaced a head, ONLY the 5 ENDING VALUES are required!')
    old_board = forms.CharField(min_length=16, max_length=16, required=False, label='Board Old Serial Number',
                                help_text='Only required if you replaced a board!')
    new_board = forms.CharField(min_length=16, max_length=16, required=False, label='Board New Serial Number',
                                help_text='Only required if you replaced a board!')

    def clean_old_head_barcode(self):
        if not self.cleaned_data['old_head_barcode']:
            return self.cleaned_data['old_head_barcode']
        return 'CQUH' + self.cleaned_data['old_head_barcode']

    def clean_new_head_barcode(self):
        if not self.cleaned_data['new_head_barcode']:
            return self.cleaned_data['new_head_barcode']
        return 'CQUH' + self.cleaned_data['new_head_barcode']


class ScheduleUpdateForm(forms.Form):
    box_number = forms.CharField(max_length=20, min_length=4, required=True)
    printer_number = forms.CharField(max_length=6, min_length=6, required=True)
    pickup_parts = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=Schedule.pparts)
    client = forms.ModelChoiceField(queryset=Client.objects.all().exclude(action_status='Pending'))
    pickup_date = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}))
    problem = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=Schedule.issues)
    date_repaired = forms.DateField(widget=NumberInput(attrs={'type': 'date'}))
    parts_replaced = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=Schedule.rparts,
                                               required=False)
    date_delivered = forms.DateField(widget=NumberInput(attrs={'type': 'date'}))
    old_head = forms.CharField(min_length=5, max_length=5, required=False, label='Print Head Old Serial Number',
                               help_text='Only required if you replaced a head, ONLY the 5 ENDING VALUES are required!')
    new_head = forms.CharField(min_length=5, max_length=5, required=False, label='Print Head New Serial Number',
                                       help_text='Only required if you replaced a head, ONLY the 5 ENDING VALUES are required!')
    old_board = forms.CharField(min_length=16, max_length=16, required=False, label='Board Old Serial Number',
                                help_text='Only required if you replaced a board!')
    new_board = forms.CharField(min_length=16, max_length=16, required=False, label='Board New Serial Number',
                                help_text='Only required if you replaced a board!')

    def clean_box_number(self):
        return self.cleaned_data['box_number'].upper()

    def clean_old_head(self):
        if not self.cleaned_data['old_head']:
            return self.cleaned_data['old_head']
        return 'CQUH' + self.cleaned_data['old_head']

    def clean_new_head(self):
        if not self.cleaned_data['new_head']:
            return self.cleaned_data['new_head']
        return 'CQUH' + self.cleaned_data['new_head']



class FixedUpdateScheduleForm(forms.Form):
    printer_number = forms.CharField(min_length=6, max_length=6, required=True)
    date_repaired = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}))
    problem = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=Schedule.issues)
    parts_replaced = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=Schedule.rparts,
                                               required=False)
    # fixed_by = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=Schedule.technicians)

    old_head_barcode = forms.CharField(min_length=5, max_length=5, required=False, label='Print Head Old Serial Number',
                                       help_text='Only required if you replaced a head, ONLY the 5 ENDING VALUES are required!')
    new_head_barcode = forms.CharField(min_length=5, max_length=5, required=False, label='Print Head New Serial Number',
                                       help_text='Only required if you replaced a head, ONLY the 5 ENDING VALUES are required!')
    old_board = forms.CharField(min_length=16, max_length=16, required=False, label='Board Old Serial Number',
                                help_text='Only required if you replaced a board!')
    new_board = forms.CharField(min_length=16, max_length=16, required=False, label='Board New Serial Number',
                                help_text='Only required if you replaced a board!')

    def clean_old_head_barcode(self):
        if not self.cleaned_data['old_head_barcode']:
            return self.cleaned_data['old_head_barcode']
        return 'CQUH' + self.cleaned_data['old_head_barcode']

    def clean_new_head_barcode(self):
        if not self.cleaned_data['new_head_barcode']:
            return self.cleaned_data['new_head_barcode']
        return 'CQUH' + self.cleaned_data['new_head_barcode']


class DeliveryUpdateScheduleForm(forms.Form):
    printer_number = forms.CharField(min_length=6, max_length=6, required=True)
    date_delivered = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}))


class CancelScheduleForm(forms.Form):
    printer_number = forms.CharField(min_length=6, max_length=6, required=True)
    cancellation_reason = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))


class DelayMaintenanceForm(forms.Form):
    printer_number = forms.CharField(min_length=6, max_length=6, required=True)
    reason = forms.ChoiceField(choices=Schedule.dcategory, label='Reason for seeking delay maintenance')


class WaybillForm(forms.Form):
    client = forms.ModelChoiceField(queryset=Client.objects.all().exclude(action_status='Pending'))
    start_date_for_when_fixed = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}))
    end_date_for_when_fixed = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}))


class WaybillPickupForm(forms.Form):
    client = forms.ModelChoiceField(queryset=Client.objects.all().exclude(action_status='Pending'))
    start_date_for_when_picked_up = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}))
    end_date_for_when_picked_up = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}))


class UploadWaybill(forms.Form):
    client = forms.ModelChoiceField(queryset=Client.objects.all().exclude(action_status='Pending'))
    start_date_for_when_fixed = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}))
    end_date_for_when_fixed = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}))


class AddPartForm(forms.Form):
    part_name = forms.ChoiceField(choices=Part.pnames)
    part_name_not_included = forms.CharField(required=False, min_length=3, max_length=30,
                                             help_text='Only fill this if the part name is not included in the above PART LIST',
                                             label='Enter the part name not included')
    topup = forms.IntegerField(required=True, label='Enter the quantity if any', initial=0)

    def clean_part_name_not_included(self):
        return self.cleaned_data['part_name_not_included'].capitalize()

    def clean_topup(self):
        return abs(self.cleaned_data['topup'])


class UpdatePartForm(forms.ModelForm):
    class Meta:
        model = Part
        exclude = ["number_requested"]
        # fields = '__all__'

    def clean_available_number(self):
        return abs(self.cleaned_data['available_number'])


class UpdateStockForm(forms.Form):
    part_name = forms.ModelChoiceField(queryset=Part.objects.filter(action_status='Approved'))
    topup = forms.IntegerField(required=True, label='Enter the quantity to update')

    def clean_topup(self):
        return abs(self.cleaned_data['topup'])


class RequestPartForm(forms.Form):
    part_name = forms.ModelChoiceField(queryset=Part.objects.filter(action_status='Approved'))
    request = forms.IntegerField(required=True, label='Enter the number of part to request')

    def clean_request(self):
        return abs(self.cleaned_data['request'])


class RateUserForm(forms.Form):
    user = forms.ModelChoiceField(queryset=User.objects.all().exclude(is_staff=True),
                                  label='Select technician to be rated on repairs')
    comment = forms.CharField(max_length=100, required=False)


class ImageProfileForm(forms.Form):
    image = forms.ImageField()


# celery
# class ScheduleMaintenanceForm(forms.Form):
#     name = forms.CharField(min_length=3, max_length=30, required=True, help_text='Short Description For This Task')
#     client = forms.ModelChoiceField(queryset=Client.objects.all().exclude(action_status='Pending'))
#     agreement = forms.CharField(help_text='Detailed description of the agreement about this Periodic maintenance '
#                                           'with the client', widget=forms.Textarea(attrs={'rows': 5}))
#     moy = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=MaintenanceAgreement.month_of_year,
#                                     label='Select your preferred Month(s) Of The Year to run')
#     dom = forms.CharField(help_text='Example: "1" for only 1st of the selected month(s), "1,15" for both 1st and 15th '
#                                     'of the selected month(s)', label='Day(s) Of The Month', initial=1)
#     hour = forms.CharField(label='Hour(s):', initial=5, help_text="It's 24h format. Example: '16' to be run at 4PM "
#                                                                   "of the selected day(s), '4,16' to be run at 4AM "
#                                                                   "and 4PM of the selected day(s)")
#     min = forms.CharField(help_text="0 - 59 range. Example: '30' to be run at :30 of the selected hour(s)",
#                           label='Minute(s):', initial=0)


class MaintenanceForm(forms.Form):
    client = forms.ModelChoiceField(queryset=Client.objects.all().exclude(action_status='Pending'))
    start_date = forms.DateField(label='Start Date', required=True, widget=NumberInput(attrs={'type': 'date'}))
    end_date = forms.DateField(label='End Date', required=True, widget=NumberInput(attrs={'type': 'date'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}), label='Description of the maintenance')
    assigned_technicians = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=Schedule.technicians)


class UpdateMaintenanceForm(forms.ModelForm):
    class Meta:
        model = Maintenance
        exclude = ['status', 'user', 'created_at', 'updated_at', 'link_sent']


class TrainingForm(forms.Form):
    client = forms.ModelChoiceField(queryset=Client.objects.all().exclude(action_status='Pending'))
    training_category = forms.ChoiceField(choices=Training.ttype, help_text='What the training is about')
    trainers = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=Training.users)
    start_date = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}))
    end_date = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}), label='Description of the training')


class UpdateTrainingForm(forms.ModelForm):
    class Meta:
        model = Training
        exclude = ['user', 'client', 'status', 'link_sent', 'created_at', 'updated_at', 'training_comment']


class ScheduleLaminatorForm(forms.Form):
    box_number = forms.CharField(max_length=20, min_length=4, required=True)
    laminator_number = forms.CharField(max_length=7, min_length=7, required=True)
    pickup_parts = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=LaminatorSchedule.pparts)
    client = forms.ModelChoiceField(queryset=Client.objects.all().exclude(action_status='Pending'))
    pickup_date = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}))
    problem = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=LaminatorSchedule.issues,
                                        help_text='Ignore the "problem" field if not certain')
    other_problem = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}), required=False)
    assigned_technicians = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=Schedule.technicians)

    def clean_box_number(self):
        return self.cleaned_data['box_number'].upper()


class LaminatorUpdateForm(forms.Form):
    laminator_number = forms.CharField(min_length=7, max_length=7, required=True)
    # date_repaired = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}))
    problem = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=LaminatorSchedule.issues)
    other_problem = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}), required=False)
    parts_replaced = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=LaminatorSchedule.pparts,
                                               required=False)
    # re_qualified = forms.CharField(min_length=7, max_length=7, required=False)
    old_head = forms.CharField(min_length=5, max_length=5, required=False, label='Print Head Old Serial Number',
                                       help_text='Only required if you replaced a head, ONLY the 5 ENDING VALUES are required!')
    new_head = forms.CharField(min_length=5, max_length=5, required=False, label='Print Head New Serial Number',
                                       help_text='Only required if you replaced a head, ONLY the 5 ENDING VALUES are required!')
    old_board = forms.CharField(min_length=16, max_length=16, required=False, label='Board Old Serial Number',
                                help_text='Only required if you replaced a board!')
    new_board = forms.CharField(min_length=16, max_length=16, required=False, label='Board New Serial Number',
                                help_text='Only required if you replaced a board!')

    def clean_old_head(self):
        if not self.cleaned_data['old_head']:
            return self.cleaned_data['old_head']
        return 'CQUH' + self.cleaned_data['old_head']

    def clean_new_head(self):
        if not self.cleaned_data['new_head']:
            return self.cleaned_data['new_head']
        return 'CQUH' + self.cleaned_data['new_head']


class CancelLaminatorScheduleForm(forms.Form):
    laminator_number = forms.CharField(min_length=7, max_length=7, required=True)
    cancellation_reason = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))


class LaminatorScheduleUpdateForm(forms.Form):
    box_number = forms.CharField(max_length=20, min_length=4, required=True)
    laminator_number = forms.CharField(max_length=7, min_length=7, required=True)
    pickup_parts = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=LaminatorSchedule.pparts)
    client = forms.ModelChoiceField(queryset=Client.objects.all().exclude(action_status='Pending'))
    pickup_date = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}))
    problem = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=LaminatorSchedule.issues)
    other_problem = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}), required=False)
    # date_repaired = forms.DateField(widget=NumberInput(attrs={'type': 'date'}))
    parts_replaced = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=LaminatorSchedule.pparts,
                                               required=False)
    # re_qualified = forms.CharField(min_length=7, max_length=7, required=False)
    old_head = forms.CharField(min_length=5, max_length=5, required=False, label='Print Head Old Serial Number',
                                       help_text='Only required if you replaced a head, ONLY the 5 ENDING VALUES are required!')
    new_head = forms.CharField(min_length=5, max_length=5, required=False, label='Print Head New Serial Number',
                                       help_text='Only required if you replaced a head, ONLY the 5 ENDING VALUES are required!')
    old_board = forms.CharField(min_length=16, max_length=16, required=False, label='Board Old Serial Number',
                                help_text='Only required if you replaced a board!')
    new_board = forms.CharField(min_length=16, max_length=16, required=False, label='Board New Serial Number',
                                help_text='Only required if you replaced a board!')

    def clean_box_number(self):
        return self.cleaned_data['box_number'].upper()

    def clean_old_head(self):
        if not self.cleaned_data['old_head']:
            return self.cleaned_data['old_head']
        return 'CQUH' + self.cleaned_data['old_head']

    def clean_new_head(self):
        if not self.cleaned_data['new_head']:
            return self.cleaned_data['new_head']
        return 'CQUH' + self.cleaned_data['new_head']


class UpdatePendingForm(forms.ModelForm):

    class Meta:
        model = LaminatorSchedule
        exclude = ['cancellation_reason', 'cancelled', 'user', 'date_cancelled', 'updated_at', 'created_at', 'fixed_by',
                   'approved_by', 'requested_by', 'action_status']

    def clean_laminator_number(self):
        return self.cleaned_data['laminator_number'].upper()

    def clean_box_number(self):
        return self.cleaned_data['box_number'].upper()


class ScheduleMRWForm(forms.Form):
    mrw_number = forms.CharField(max_length=8, min_length=7, required=True, label='MRW Number')
    pickup_parts = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=MRWSchedule.pparts)
    client = forms.ModelChoiceField(queryset=Client.objects.all().exclude(action_status='Pending'))
    pickup_date = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}))
    # problem = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=MRWSchedule.issues,
                                        # help_text='Ignore the "problem" field if not certain')
    problem = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))
    assigned_technicians = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=Schedule.technicians)


class MRWUpdateForm(forms.Form):
    mrw_number = forms.CharField(min_length=7, max_length=8, required=True, label='MRW Number')
    problem = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))
    parts_replaced = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=MRWSchedule.pparts)
    re_qualified = forms.CharField(min_length=7, max_length=8, required=False, label='Re-Qualified MRW Number',
                                   help_text='Only required if there is re-qualification!')


class CancelMRWScheduleForm(forms.Form):
    mrw_number = forms.CharField(min_length=7, max_length=8, required=True, label='MRW Number')
    cancellation_reason = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))


class MRWScheduleUpdateForm(forms.Form):
    mrw_number = forms.CharField(max_length=8, min_length=7, required=True, label='MRW Number')
    pickup_parts = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=MRWSchedule.pparts)
    client = forms.ModelChoiceField(queryset=Client.objects.all().exclude(action_status='Pending'))
    pickup_date = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}))
    problem = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))
    parts_replaced = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=MRWSchedule.pparts)
    re_qualified = forms.CharField(min_length=7, max_length=8, required=False, label='Re-Qualified MRW Number',
                                   help_text='Only required if there is re-qualification!')


class UpdatePendingMRWForm(forms.ModelForm):

    class Meta:
        model = MRWSchedule
        exclude = ['cancellation_reason', 'cancelled', 'user', 'date_cancelled', 'updated_at', 'created_at', 'fixed_by',
                   'approved_by', 'requested_by', 'action_status']

    def clean_mrw_number(self):
        return self.cleaned_data['mrw_number'].upper()


class ScheduleISSForm(forms.Form):
    iss_number = forms.CharField(max_length=9, min_length=7, required=True, label='ISS Number')
    pickup_parts = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=ISSSchedule.pparts)
    client = forms.ModelChoiceField(queryset=Client.objects.all().exclude(action_status='Pending'))
    pickup_date = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}))
    problem = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))
    assigned_technicians = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=Schedule.technicians)


class ISSUpdateForm(forms.Form):
    iss_number = forms.CharField(max_length=9, min_length=7, required=True, label='ISS Number')
    problem = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))
    parts_replaced = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=ISSSchedule.pparts)
    re_qualified = forms.CharField(min_length=7, max_length=9, required=False, label='Re-Qualified ISS Number',
                                   help_text='Only required if there is re-qualification!')


class CancelISSScheduleForm(forms.Form):
    iss_number = forms.CharField(max_length=9, min_length=7, required=True, label='ISS Number')
    cancellation_reason = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))


class ISSScheduleUpdateForm(forms.Form):
    iss_number = forms.CharField(max_length=9, min_length=7, required=True, label='ISS Number')
    pickup_parts = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=ISSSchedule.pparts)
    client = forms.ModelChoiceField(queryset=Client.objects.all().exclude(action_status='Pending'))
    pickup_date = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}))
    problem = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))
    parts_replaced = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=ISSSchedule.pparts)
    re_qualified = forms.CharField(min_length=7, max_length=9, required=False, label='Re-Qualified ISS Number',
                                   help_text='Only required if there is re-qualification!')


class UpdatePendingISSForm(forms.ModelForm):

    class Meta:
        model = ISSSchedule
        exclude = ['cancellation_reason', 'cancelled', 'user', 'date_cancelled', 'updated_at', 'created_at', 'fixed_by',
                   'approved_by', 'requested_by', 'action_status']

    def clean_iss_number(self):
        return self.cleaned_data['iss_number'].upper()


class AddLaminatorForm(forms.Form):
    client = forms.ModelChoiceField(queryset=Client.objects.all().exclude(action_status='Pending'))
    box_number = forms.CharField(max_length=20, min_length=6, required=True)
    laminator_number = forms.CharField(max_length=7, min_length=7, required=True)
    p_date = forms.DateField(required=True, widget=NumberInput(attrs={'type': 'date'}), label='Date Purchased')

    def clean_laminator_number(self):
        return self.cleaned_data['laminator_number'].upper()

    def clean_box_number(self):
        return self.cleaned_data['box_number'].upper()


class UpdateLaminatorForm(forms.ModelForm):
    class Meta:
        model = Laminator
        exclude = ['created_at', 'updated_at']


class UpdateMRWForm(forms.ModelForm):
    class Meta:
        model = MRW
        exclude = ['created_at', 'updated_at']


class UpdateISSForm(forms.ModelForm):
    class Meta:
        model = ISS
        exclude = ['created_at', 'updated_at']

