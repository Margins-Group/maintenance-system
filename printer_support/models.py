from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import ugettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from multiselectfield import MultiSelectField
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User


# from django_celery_beat.models import PeriodicTask


class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(_('email address'), unique=True)
    middle_name = models.CharField(max_length=20, blank=True)
    phone_number = PhoneNumberField()
    is_pro = models.BooleanField(default=False)  # procurement officer
    is_accountant = models.BooleanField(default=False)  # accountant
    is_head = models.BooleanField(default=False)
    is_supervisor = models.BooleanField(default=False)
    is_client = models.BooleanField(null=True, default=False)
    image = models.ImageField(upload_to='profiles', null=True, blank=True)
    password = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return f'{self.first_name} {self.middle_name} {self.last_name}'


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email_confirmed = models.BooleanField(default=False)

    def __str__(self):
        return '{} {}'.format(self.user.first_name, self.user.last_name)


@receiver(post_save, sender=User)
def update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()


class Client(models.Model):
    client_name = models.CharField(max_length=30, unique=True)
    address = models.CharField(max_length=50)
    requested_by = models.CharField(max_length=60, null=True, blank=True)
    approved_by = models.CharField(max_length=60, null=True, blank=True)
    action_status = models.CharField(max_length=20, default='Approved')
    rep = models.CharField(max_length=60)
    rep_tel = PhoneNumberField(blank=True, null=True)
    rep_email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.client_name


# purchased printers
class Procurement(models.Model):
    printer_brands = [('Datacard', 'Datacard'),
                      ('IDP', 'IDP'),
                      ('Zebra', 'Zebra'),
                      ('Fargo', 'Fargo'),
                      ('Magicard', 'Magicard'),
                      ('ScreenCheck', 'ScreenCheck'),
                      ('Evolis', 'Evolis'),
                      ('Nisca', 'Nisca')]
    printer_models = [('CD 800', 'CD 800'),
                      ('IDP', 'IDP'),
                      ('Smart 5', 'Smart 5')]

    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    client = models.ForeignKey(Client, null=True, on_delete=models.SET_NULL)
    printer_number = models.CharField(max_length=6, primary_key=True)
    box_number = models.CharField(max_length=20, blank=True, null=True)
    brand = models.CharField(choices=printer_brands, null=True, blank=True, max_length=30)
    model = models.CharField(choices=printer_models, null=True, blank=True, max_length=30)
    warranty_years = models.IntegerField(null=True, blank=True, )
    warranty_start_date = models.DateField(null=True, blank=True, )
    date_purchased = models.DateField(null=True, blank=True)
    warranty_status = models.CharField(null=True, blank=True, max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.printer_number


class MRW(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    client = models.ForeignKey(Client, null=True, on_delete=models.SET_NULL)
    mrw_number = models.CharField(max_length=8, primary_key=True)
    date_purchased = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.mrw_number


class Laminator(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    client = models.ForeignKey(Client, null=True, on_delete=models.SET_NULL)
    laminator_number = models.CharField(max_length=7, primary_key=True)
    box_number = models.CharField(max_length=20, blank=True, null=True)
    date_purchased = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.laminator_number


class ISS(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    client = models.ForeignKey(Client, null=True, on_delete=models.SET_NULL)
    iss_number = models.CharField(max_length=9, primary_key=True)
    date_purchased = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.iss_number


class PrinterRMA(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    printer = models.ForeignKey(Procurement, on_delete=models.CASCADE)
    part_name = models.CharField(max_length=30)
    faulty_part_barcode = models.CharField(max_length=20)
    replaced_part_barcode = models.CharField(max_length=20, null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.printer


class Schedule(models.Model):
    rstatus = [('Pending', 'Pending'), ('Fixed', 'Fixed')]

    dstatus = [('Pending', 'Pending'), ('Delivered', 'Delivered')]

    dcategory = [('No parts available', 'No parts available'),
                 ('Internal issues', 'Internal issues'),
                 ('Car delay', 'Car delay')]

    pparts = [('n', 'No Part Available'),
              ('k', 'Key'),
              ('a', 'Adapter'),
              ('u', 'USB'),
              ('r', 'Sleeve'),
              ('c', 'Cartridge Holder'),
              ('ohf', 'OHF'),
              ('rt', 'Reject Tray'),
              ('es', 'Encoder Spring'),
              ]

    issues = [('c', 'CNP'),
              ('cs', 'CNP from start'),
              ('h', 'Broken Head'),
              ('b', 'Board'),
              ('pu', 'Printer Unlock'),
              ('rb', 'Ribbon Issues'),
              ('r', 'Roller Issues'),
              ('fm', 'Flipper Motor'),
              # ('pm', 'Picker Motor'),
              ('fb', 'Flipper Board'),
              ('s', 'Sensor Issues'),
              ('mp', 'Cartridge'),
              ('i', 'IHF'),
              ('o', 'OHF'),
              ('p', 'RJ11 Port'),
              ('l', 'LCD'),
              ('sa', 'Swing Arm'),
              ('e', 'Encoder')]

    rparts = [('h', 'Print Head'),
              ('b', 'Board'),
              ('s', 'Sensor'),
              ('i', 'IHF'),
              ('o', 'OHF'),
              ('m', 'Motor'),
              ('r', 'Roller'),
              ('eb', 'Encoder Board'),
              ('l', 'LCD')]

    technicians = []
    queryset = User.objects.filter(is_active=True).order_by('first_name')
    for name in queryset:
        if not (name.is_staff or name.is_pro or name.is_accountant):
            technicians.append((name.id, name))

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, null=True, on_delete=models.SET_NULL)
    printer_number = models.CharField(max_length=6)
    box_number = models.CharField(max_length=20, null=True, blank=True)
    pickup_parts = MultiSelectField(choices=pparts)
    pickup_date = models.DateField(help_text="format : YYYY-MM-DDY")
    assigned_technicians = MultiSelectField(choices=technicians, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancelled = models.BooleanField(default=False)
    cancellation_reason = models.TextField(null=True, blank=True)
    date_cancelled = models.DateField(null=True, blank=True)
    repair_status = models.CharField(choices=rstatus, default='Pending', max_length=10)
    delay_maintenance_reason = models.CharField(choices=dcategory, max_length=20, null=True, blank=True)
    delay_maintenance_date = models.DateField(null=True, blank=True)
    date_repaired = models.DateField(null=True, blank=True, help_text="format : YYYY-MM-DD")
    fixed_by = MultiSelectField(choices=technicians, null=True, blank=True)
    requested_by = models.CharField(max_length=60, null=True, blank=True)
    approved_by = models.CharField(max_length=60, null=True, blank=True)
    action_status = models.CharField(max_length=20, default='Approved')
    problem = MultiSelectField(choices=issues, null=True, blank=True)
    parts_replaced = MultiSelectField(choices=rparts, null=True, blank=True)
    old_head_barcode = models.CharField(max_length=9, null=True, blank=True)
    new_head_barcode = models.CharField(max_length=9, null=True, blank=True)
    old_board = models.CharField(max_length=16, null=True, blank=True)
    new_board = models.CharField(max_length=16, null=True, blank=True)
    delivery_status = models.CharField(choices=dstatus, default='Pending', max_length=10)
    date_delivered = models.DateField(null=True, blank=True, help_text="format : YYYY-MM-DD")

    def __str__(self):
        return self.printer_number


class ISSSchedule(models.Model):
    pparts = [('l', 'Laptop'),
              ('la', 'Laptop Adapter'),
              ('fs', 'Fingerprint Scanner'),
              ('bs', 'Barcode Scanner'),
              ('cr', 'Card Reader'),
              ('uh', 'USB Hub'),
              ('pb', 'Power Bank'),
              ('c', 'Power Bank to Laptop Cable'),
              ('pa', 'Power Bank Adapter')]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, null=True, on_delete=models.SET_NULL)
    iss_number = models.CharField(max_length=9)
    pickup_parts = MultiSelectField(choices=pparts)
    pickup_date = models.DateField(help_text="format : YYYY-MM-DDY")
    problem = models.TextField()
    assigned_technicians = MultiSelectField(choices=Schedule.technicians, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancelled = models.BooleanField(default=False)
    cancellation_reason = models.TextField(null=True, blank=True)
    date_cancelled = models.DateField(null=True, blank=True)
    repair_status = models.CharField(choices=Schedule.rstatus, default='Pending', max_length=10)
    date_repaired = models.DateField(null=True, blank=True, help_text="format : YYYY-MM-DD")
    re_qualified_iss_number = models.CharField(max_length=9, null=True, blank=True)
    fixed_by = models.IntegerField(null=True, blank=True)
    requested_by = models.IntegerField(null=True, blank=True)
    approved_by = models.IntegerField(null=True, blank=True)
    action_status = models.CharField(max_length=20, default='Approved')
    parts_replaced = MultiSelectField(choices=pparts, null=True, blank=True)
    # delivery_status = models.CharField(choices=Schedule.dstatus, default='Pending', max_length=10)
    # date_delivered = models.DateField(null=True, blank=True, help_text="format : YYYY-MM-DD")

    def __str__(self):
        return self.iss_number


class LaminatorSchedule(models.Model):
    pparts = [('pa', 'Power Adapter'),
              ('ch1', 'L1 Cartridge Holder'),
              ('ch2', 'L1 Cartridge Holder')]

    issues = [('l1', 'Broken Cartridge - L1'),
              ('l2', 'Broken Cartridge - L2'),
              ('c', 'RJ11 Cable'),
              ('p', 'RJ11 Port'),
              ('d', 'Broken Debow')]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, null=True, on_delete=models.SET_NULL)
    laminator_number = models.CharField(max_length=7)
    box_number = models.CharField(max_length=20, null=True, blank=True)
    pickup_parts = MultiSelectField(choices=pparts)
    pickup_date = models.DateField(help_text="format : YYYY-MM-DDY")
    problem = MultiSelectField(choices=issues, null=True, blank=True)
    other_problem = models.TextField(null=True, blank=True)
    assigned_technicians = MultiSelectField(choices=Schedule.technicians, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancelled = models.BooleanField(default=False)
    cancellation_reason = models.TextField(null=True, blank=True)
    date_cancelled = models.DateField(null=True, blank=True)
    repair_status = models.CharField(choices=Schedule.rstatus, default='Pending', max_length=10)
    date_repaired = models.DateField(null=True, blank=True, help_text="format : YYYY-MM-DD")
    fixed_by = models.IntegerField(null=True, blank=True)
    requested_by = models.IntegerField(null=True, blank=True)
    approved_by = models.IntegerField(null=True, blank=True)
    action_status = models.CharField(max_length=20, default='Approved')
    parts_replaced = MultiSelectField(choices=pparts, null=True, blank=True)
    # delivery_status = models.CharField(choices=Schedule.dstatus, default='Pending', max_length=10)
    # date_delivered = models.DateField(null=True, blank=True, help_text="format : YYYY-MM-DD")

    def __str__(self):
        return self.laminator_number


class MRWSchedule(models.Model):
    pparts = [('l', 'Laptop'),
              ('la', 'Laptop Adapter'),
              ('s', 'IRIS Scanner'),
              ('sc', 'IRIS Scanner Cable'),
              ('ds', 'Document Scanner'),
              ('sd', 'SD Card'),
              ('rp', 'Receipt Printer'),
              ('rpc', 'Receipt Printer Cable'),
              ('rpa', 'Receipt Printer Adapter'),
              ('fs', 'Fingerprint Scanner'),
              ('sp', 'Signature PAD'),
              ('bs', 'Barcode Scanner'),
              ('cr', 'Card Reader'),
              ('w', 'Webcam'),
              ('uha', 'USB Hub-A'),
              ('uhc', 'USB Hub-C'),
              ('pb', 'Power Bank'),
              ('c', 'Power Bank to Laptop Cable'),
              ('pa', 'Power Bank Adapter'),
              ('led', 'LED'),
              ('b', 'Batteries'),
              ('bc', 'Battery Charger')]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, null=True, on_delete=models.SET_NULL)
    mrw_number = models.CharField(max_length=8)
    pickup_parts = MultiSelectField(choices=pparts)
    pickup_date = models.DateField(help_text="format : YYYY-MM-DDY")
    problem = models.TextField()
    assigned_technicians = MultiSelectField(choices=Schedule.technicians, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancelled = models.BooleanField(default=False)
    cancellation_reason = models.TextField(null=True, blank=True)
    date_cancelled = models.DateField(null=True, blank=True)
    repair_status = models.CharField(choices=Schedule.rstatus, default='Pending', max_length=10)
    date_repaired = models.DateField(null=True, blank=True, help_text="format : YYYY-MM-DD")
    re_qualified_mrw_number = models.CharField(max_length=8, null=True, blank=True)
    fixed_by = models.IntegerField(null=True, blank=True)
    requested_by = models.IntegerField(null=True, blank=True)
    approved_by = models.IntegerField(null=True, blank=True)
    action_status = models.CharField(max_length=20, default='Approved')
    parts_replaced = MultiSelectField(choices=pparts, null=True, blank=True)
    # delivery_status = models.CharField(choices=Schedule.dstatus, default='Pending', max_length=10)
    # date_delivered = models.DateField(null=True, blank=True, help_text="format : YYYY-MM-DD")

    def __str__(self):
        return self.mrw_number


class Event(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user


class Part(models.Model):
    pnames = [('None', 'Name not included?'),
              ('Print head', 'Print Head'),
              ('Board', 'Board'),
              ('Input hopper frame', 'Input Hopper Frame'),
              ('Output hopper frame', 'Output Hopper Frame'),
              ('Encoder board', 'Encoder Board'),
              ('LCD', 'LCD'),
              ('Sensor', 'Sensor')]

    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=30, unique=True)
    requested_by = models.CharField(max_length=60, null=True, blank=True)
    approved_by = models.CharField(max_length=60, null=True, blank=True)
    action_status = models.CharField(max_length=20, default='Approved')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class PartStock(models.Model):
    name = models.ForeignKey(Part, null=True, on_delete=models.SET_NULL)
    user = models.CharField(max_length=60)
    request = models.IntegerField(default=0)
    topup = models.IntegerField(default=0)
    action_status = models.CharField(max_length=20, default='Approved')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class PartEvent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=60)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.first_name}'


class Waybill(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    client = models.CharField(max_length=50)
    filename = models.CharField(max_length=10, unique=True)
    type = models.CharField(max_length=20)
    file = models.FileField(blank=True, null=True, upload_to='waybills')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.filename


# trainings
class Training(models.Model):
    ttype = [('Loyalty solution', 'Loyalty Solution'),
             ('CCTV surveillance system', 'CCTV Surveillance System'),
             ('Time and Attendance solution', 'Time and Attendance Solution'),
             ('ART', 'ART'),
             ('STEM', 'STEM'),
             ('Printer Troubleshooting', 'Printer Troubleshooting'),
             ('Printer Repairs', 'Printer Repairs'),
             ('Printer Cleaning', 'Printer Cleaning')
             ]
    users = []  # Technicians
    queryset = User.objects.filter(is_active=True).order_by('first_name')
    for name in queryset:
        if not (name.is_staff or name.is_pro or name.is_accountant):
            users.append((name.id, name))
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, null=True, on_delete=models.CASCADE)
    raters_email = models.TextField()
    trainers = MultiSelectField(choices=users)
    training_category = models.CharField(choices=ttype, default='troubleshooting', max_length=30)
    start_date = models.DateField()
    end_date = models.DateField()
    description = models.TextField()
    training_comment = models.TextField(null=True, blank=True)
    status = models.CharField(blank=True, null=True, max_length=15)
    link_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Maintenance(models.Model):
    ttype = [('Printer Troubleshooting', 'Printer Troubleshooting'),
             ('Printer Repairs', 'Printer Repairs'),
             ('Printer Cleaning', 'Printer Cleaning'),
             ('Software Installation', 'Software Installation'),
             ('Laminator Troubleshooting', 'Laminator Troubleshooting'),
             ('Laminator Repairs', 'Laminator Repairs'),
             ('Laminator Cleaning', 'Laminator Cleaning'),
             ('MRW Troubleshooting', 'MRW Troubleshooting'),
             ('MRW Repairs', 'MRW Repairs'),
             ('MRW Cleaning', 'MRW Cleaning')
             ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    # training_category = models.CharField(choices=ttype, default='troubleshooting', max_length=30)
    description = models.TextField()
    assigned_technicians = MultiSelectField(choices=Schedule.technicians, null=True, blank=True)
    status = models.CharField(blank=True, null=True, max_length=20)
    link_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


# ratings and assessments
class UserRating(models.Model):
    options = [('None', 'Choose an option!'),
               ('Strongly Agree', 'Strongly Agree'),
               ('Agree', 'Agree'),
               ('Uncertain', 'Uncertain'),
               ('Disagree', 'Disagree'),
               ('Strongly Disagree', 'Strongly Disagree')]
    rating_type = models.CharField(max_length=10)
    training = models.ForeignKey(Training, null=True, on_delete=models.SET_NULL)
    maintenance = models.ForeignKey(Maintenance, null=True, on_delete=models.SET_NULL)
    user = models.IntegerField()
    rater = models.IntegerField(null=True, blank=True)
    rating = models.IntegerField(default=0)
    comment = models.CharField(max_length=100, null=True, blank=True)
    date = models.DateField()
    topics = models.CharField(max_length=20, choices=options, null=True, blank=True)
    slides = models.CharField(max_length=20, choices=options, null=True, blank=True)
    duration = models.CharField(max_length=20, choices=options, null=True, blank=True)
    solution = models.CharField(max_length=20, choices=options, null=True, blank=True)
    style = models.CharField(max_length=20, choices=options, null=True, blank=True)
    q_response = models.CharField(max_length=20, choices=options, null=True, blank=True)
    location = models.CharField(max_length=20, choices=options, null=True, blank=True)
    config_install = models.CharField(max_length=20, choices=options, null=True, blank=True)
    training_benefit = models.CharField(max_length=20, choices=options, null=True, blank=True)
    recommend = models.CharField(max_length=20, choices=options, null=True, blank=True)
    # stem = models.CharField(max_length=20, choices=options, null=True, blank=True)
    # art = models.CharField(max_length=20, choices=options, null=True, blank=True)
    # time = models.CharField(max_length=20, choices=options, null=True, blank=True)
    # cctv = models.CharField(max_length=20, choices=options, null=True, blank=True)
    # loyalty = models.CharField(max_length=20, choices=options, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


# class MaintenanceAgreement(models.Model):
#     month_of_year = [('0', 'January'),
#                      ('1', 'February'),
#                      ('2', 'March'),
#                      ('3', 'April'),
#                      ('4', 'May'),
#                      ('5', 'June'),
#                      ('6', 'July'),
#                      ('7', 'August'),
#                      ('8', 'September'),
#                      ('9', 'October'),
#                      ('10', 'November'),
#                      ('11', 'December'),
#                      ('*', 'Every Month')
#                      ]
#
#     user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
#     schedule = models.ForeignKey(PeriodicTask, on_delete=models.CASCADE)
#     # cancelled = models.BooleanField(default=False)
#     client = models.CharField(max_length=50)
#     agreement = models.TextField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#
#     def __str__(self):
#         return f'{self.schedule.name}'


class HelpDesk(models.Model):
    fstatus = [('Pending', 'Pending'), ('Fixed', 'Fixed')]

    category = [('access denial', 'Access Denial'),
                ('h', 'Account Issue'),
                ('k', 'Notification'),
                ('s', 'Helpdesk'),
                ('security', 'Security'),
                ('pending approval', 'Pending Approval')]

    reporter = models.ForeignKey(User, on_delete=models.CASCADE)
    issue = models.CharField(max_length=30)
    description = models.TextField()
    fix_status = models.CharField(choices=fstatus, default='Pending', max_length=10)
    fixed_by = models.IntegerField(null=True, blank=True)
    date_fixed = models.DateField(null=True)
    fix_confirmation = models.CharField(default='Pending', max_length=10)
    ready_rate = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    position = models.TextField(null=True)

    def __str__(self):
        return f'{self.reporter.first_name}'
