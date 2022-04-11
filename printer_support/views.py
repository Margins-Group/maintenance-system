from django.shortcuts import render, redirect
from .models import *
from django.contrib.auth.models import User
from .forms import *
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, logout as logout_check, login as login_checks
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from .tokens import account_activation_token
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth import get_user_model
from maintenance_portal.settings import EMAIL_HOST_USER
from django.core.mail import send_mail
from django.template.loader import render_to_string
from printer_support.emails import send_pending_feedback_email
from django.contrib.auth.signals import user_logged_in, user_logged_out
import socket, os, random, string
from django.utils.encoding import force_text
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import BaseDocTemplate, PageTemplate, Table, TableStyle, Paragraph, Frame, Spacer, Image
from reportlab.lib.enums import TA_RIGHT, TA_JUSTIFY, TA_LEFT, TA_CENTER
from django.core.files.base import File
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from wsgiref.util import FileWrapper
from django.http import HttpResponse
from django.conf import settings
from django.db.models import Q
# from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
import math
import numpy as np

User = get_user_model()


def get_path():
    cdir = os.path.expanduser("~")
    path = os.path.join(cdir, "Downloads/")
    return path.replace(os.sep, '/')


internet_issues = (OSError, socket.gaierror)


def is_connected():
    try:
        socket.create_connection(("1.1.1.1", 53))
        return True
    except internet_issues:
        return False


def record_user_logged_in(sender, user, request, **kwargs):
    Event.objects.create(user_id=user.pk, action='Logged in to Printer Support')


def record_user_logged_out(sender, user, request, **kwargs):
    Event.objects.create(user_id=user.pk, action='Logged out from Printer Support')


# user_logged_in.connect(record_user_logged_in)
user_logged_out.connect(record_user_logged_out)


def home(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return render(request, 'admin_account/home.html')
        elif request.user.is_accountant:
            return render(request, 'finance/home.html')
        elif request.user.is_pro:
            return render(request, 'procurement/home.html')
        return render(request, 'standard_account/home.html')
    else:
        return render(request, 'users/login.html')


def about(request):
    return render(request, 'about.html')


@login_required(login_url='login')
def logout(request):
    u = request.user
    logout_check(request)
    messages.success(request, 'Logged out successfully {}! '
                              'Thanks for spending some quality time with the Web site today.'.format(u))
    return render(request, 'users/login.html')


def login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid:
            email = request.POST['email']
            password = request.POST['password']

            try:
                existing_user = User.objects.get(email=email)
                inactive_user = User.objects.filter(email=email, is_active=False)
            except (TypeError, ValueError, OverflowError, User.DoesNotExist):
                existing_user = None
            if existing_user is None:
                print(existing_user)
                messages.warning(request, 'Your account does not exist! Fill the below form to join the team.')
                return render(request, 'users/register.html')
            elif inactive_user:
                messages.warning(request, 'Your account is inactive! Wait for admin approval to login')
                return render(request, 'users/login.html')
            elif existing_user:
                user = authenticate(email=email, password=password)
                if user is not None:
                    if user.is_active and user.is_staff:
                        login_checks(request, user)
                        Event.objects.create(user_id=user.pk, action='Logged in as ADMIN')
                        return redirect('home')
                    elif user.is_active and user.is_accountant:
                        login_checks(request, user)
                        Event.objects.create(user_id=user.pk, action='Logged in as ACCOUNTANT')
                        return redirect('home')
                    elif user.is_active and user.is_pro:
                        login_checks(request, user)
                        Event.objects.create(user_id=user.pk, action='Logged in as PROCUREMENT OFFICER')
                        return redirect('home')
                    elif user.is_active:
                        login_checks(request, user)
                        Event.objects.create(user_id=user.pk, action='Logged in as TECHNICIAN')
                        return redirect('home')
                else:
                    messages.warning(request, 'Invalid credentials')
                    return render(request, 'users/login.html')
    else:
        form = LoginForm()
    return render(request, 'users/login.html', {'form': form})


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid:
            pn = request.POST['phone_number']
            p1 = request.POST['password1']
            p2 = request.POST['password2']
            email = request.POST['email']
            fn = request.POST['first_name']
            mn = request.POST['middle_name']
            ln = request.POST['last_name']
            inactive_user = User.objects.filter(email=email, is_active=False)
            phone_chosen = User.objects.filter(phone_number='+233' + pn[-9:])

            try:
                valid_phone = (len(pn) == 10) or (len(pn) == 13)
                valid_password = (p1 == p2)
                existing_user = User.objects.get(email=email, is_active=True)
            except (TypeError, ValueError, OverflowError, User.DoesNotExist):
                existing_user = None

            if (not valid_phone) and (not valid_password):
                messages.warning(request, 'Invalid Phone Number and Password mismatch!')
                return render(request, 'users/register.html')
            elif not valid_phone:
                messages.warning(request, 'Invalid Phone Number!')
                return render(request, 'users/register.html')
            elif not valid_password:
                messages.warning(request, 'Password mismatch!')
                return render(request, 'users/register.html')
            elif inactive_user:
                messages.warning(request, 'Your account already exist! Wait for admin approval to login')
                return render(request, 'users/login.html')
            elif existing_user:
                messages.warning(request, 'Your account already exist!')
                return render(request, 'users/login.html')
            elif phone_chosen:
                messages.warning(request, 'Phone number provided has already been chosen!')
                return render(request, 'users/register.html')
            else:
                phone = '+233' + pn[-9:]
                user = User.objects.create_user(email=email, first_name=fn, middle_name=mn, last_name=ln,
                                                phone_number=phone, password=p1)
                user.is_active = False
                user.save()
                Event.objects.create(user_id=user.pk, action='Created an account')
                current_site = get_current_site(request)
                subject = "USER ACCOUNT ACTIVATION REQUEST - MARGINS ID SYSTEM"
                recipients = []
                admins = User.objects.filter(is_staff=True)
                for i in admins:
                    recipients.append(i.email)
                message = render_to_string('users/account_activation_request_email.html', {
                    'user': user,
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': account_activation_token.make_token(user),
                })
                if is_connected():
                    send_mail(subject, message, EMAIL_HOST_USER, recipients, fail_silently=False)
                    messages.success(request, f'Your account has been created! Wait for admins approval for login')
                    return render(request, 'users/login.html')
                else:
                    messages.success(request, f'Your account has been created! Wait for admins approval for login')
                    return render(request, 'users/login.html')
    else:
        form = RegisterForm()
    return render(request, 'users/register.html', {'form': form})


# User accounts that require admin activation
@login_required(login_url='login')
def inactive_users(request):
    users = User.objects.filter(is_active=False).order_by('-created_at')
    return render(request, "users/inactive_users.html", {'users': users})


# User accounts that have been activated
@login_required(login_url='login')
def active_users(request):
    users = User.objects.filter(is_active=True).order_by('-created_at').exclude(is_superuser=True)
    for i in users:
        if i.is_staff:
            i.password = 'Admin'
        elif i.is_accountant:
            i.password = 'Accountant'
        elif i.is_pro:
            i.password = 'Procurement Officer'
        else:
            i.password = 'Technician'
    return render(request, "users/active_users.html", {'users': users})


# Give user privilege levels to a user or activate user's account
@login_required(login_url='login')
def activate_user(request, pk):
    current_user = request.user
    user = User.objects.get(id=pk)

    if request.method == 'POST':
        privilege = request.POST['privilege'].upper()

        current_site = get_current_site(request)
        subject = "MARGINS ID SYSTEM"
        message = render_to_string('users/account_activated_email.html', {
            'user': user,
            'privilege': privilege,
            'current_user': current_user,
            'domain': current_site.domain,
        })
        recipient = [user.email]

        if privilege == 'NONE':
            messages.warning(request,
                             "{}'s user account was not activated since no privilege level was selected!".format(user))
            return redirect('inactive_users')
        elif privilege == 'ADMIN':
            user.is_active = True
            user.is_staff = True
            user.profile.email_confirmed = True
            user.save()
            Event.objects.create(user_id=current_user.pk,
                                 action="Activated {}'s user account as {} user".format(user, privilege))
            if is_connected():
                send_mail(subject, message, EMAIL_HOST_USER, recipient, fail_silently=False)
                messages.success(request, "{}'s user account has been activated as {} successfully! {} will be "
                                          "notified by mail.".format(user, privilege, user))
                return redirect('inactive_users')
            else:
                messages.success(request,
                                 "{}'s user account has been activated as {} successfully!".format(user, privilege))
                messages.warning(request, f'Email notification failed; You are not connected to internet!')
                return redirect('inactive_users')

        elif privilege == 'TECHNICIAN':
            user.is_active = True
            user.profile.email_confirmed = True
            user.save()
            Event.objects.create(user_id=current_user.pk,
                                 action="Activated {}'s user account as {} user".format(user, privilege))
            if is_connected():
                send_mail(subject, message, EMAIL_HOST_USER, recipient, fail_silently=False)
                messages.success(request, "{}'s user account has been activated as {} successfully! {} will be "
                                          "notified by mail.".format(user, privilege, user))
                return redirect('inactive_users')
            else:
                messages.success(request,
                                 "{}'s user account has been activated as {} successfully!".format(user, privilege))
                messages.warning(request, f'Email notification failed; You are not connected to internet!')
                return redirect('inactive_users')
        elif privilege == 'ACCOUNTANT':
            user.is_active = True
            user.is_accountant = True
            user.profile.email_confirmed = True
            user.save()
            Event.objects.create(user_id=current_user.pk,
                                 action="Activated {}'s user account as {} user".format(user, privilege))
            if is_connected():
                send_mail(subject, message, EMAIL_HOST_USER, recipient, fail_silently=False)
                messages.success(request, "{}'s user account has been activated as {} successfully! {} will be "
                                          "notified by mail.".format(user, privilege, user))
                return redirect('inactive_users')
            else:
                messages.success(request,
                                 "{}'s user account has been activated as {} successfully!".format(user, privilege))
                messages.warning(request, f'Email notification failed; You are not connected to internet!')
                return redirect('inactive_users')

        else:
            user.is_active = True
            user.is_pro = True
            user.profile.email_confirmed = True
            user.save()
            Event.objects.create(user_id=current_user.pk,
                                 action="Activated {}'s user account as {} user".format(user, privilege))
            if is_connected():
                send_mail(subject, message, EMAIL_HOST_USER, recipient, fail_silently=False)
                messages.success(request, "{}'s user account has been activated as {} successfully! {} will be "
                                          "notified by mail.".format(user, privilege, user))
                return redirect('inactive_users')
            else:
                messages.success(request,
                                 "{}'s user account has been activated as {} successfully!".format(user, privilege))
                messages.warning(request, f'Email notification failed; You are not connected to internet!')
                return redirect('inactive_users')
    return render(request, 'users/activate_prompt.html', {'item': user})


# Remove admin access from a user
@login_required(login_url='login')
def deactivate_user(request, pk):
    current_user = request.user
    user = User.objects.get(id=pk)

    if request.method == 'POST':
        user.is_active = False
        user.is_staff = False
        user.is_accountant = False
        user.is_pro = False
        user.profile.email_confirmed = False
        user.save()
        Event.objects.create(user_id=current_user.pk, action="Deactivated {}'s user account".format(user))
        current_site = get_current_site(request)
        subject = "MARGINS ID SYSTEM"
        message = render_to_string('users/account_deactivated_email.html', {
            'user': user,
            'current_user': current_user,
            'domain': current_site.domain,
        })
        recipient = [user.email]

        if is_connected():
            send_mail(subject, message, EMAIL_HOST_USER, recipient, fail_silently=False)
            messages.success(request, '{} user account has been deactivated successfully! {} will be notified by mail.'
                             .format(user, user))
            return redirect('active_users')
        else:
            messages.success(request, "{}'s user account has been deactivated successfully!".format(user))
            messages.warning(request, f'Email notification failed; You are not connected to internet!')
            return redirect('active_users')

    return render(request, 'users/deactivate_prompt.html', {'item': user})


# User being activated via admin email
def admin_activate(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.profile.email_confirmed = True
        # user.save()
        current_site = get_current_site(request)
        subject = "MARGINS ID SYSTEM"
        message = render_to_string('users/account_activated_email.html', {
            'user': user,
            'current_user': request.user,
            'domain': current_site.domain,
        })
        recipient = [user.email]

        if is_connected():
            send_mail(subject, message, EMAIL_HOST_USER, recipient, fail_silently=False)
            messages.info(request, "{}'s Activation failed!; Link blocked by developer but {} will be notified by mail."
                          .format(user, user))
            return redirect('login')
        else:
            messages.warning(request, f'Failed to activate; Connect to internet and use the link to activate the user '
                                      f'or log in to the system and to activate the user!')
            return redirect('login')

    else:
        messages.warning(request, f'Sorry, Invalid token! The link has already been used by different Admin')
        return render(request, 'users/login.html')


# User report
@login_required(login_url='login')
def user_report(request):
    plist, title = [], 'All Technicians Report'
    qrst = User.objects.filter(is_active=True).order_by('first_name')
    for name in qrst:
        if not (name.is_pro or name.is_accountant):
            plist.append(name)

    for i in plist:
        r = 0
        schedules = Schedule.objects.filter(user=i.id, cancelled=False).all()
        cancel = Schedule.objects.filter(cancelled=True, requested_by=i.email).all()
        fixed = Schedule.objects.filter(cancelled=False, fixed_by__icontains=str(i.id)).all()
        part_reqs = PartStock.objects.filter(user=f'{i.first_name} {i.middle_name} {i.last_name}',
                                             action_status='Approved')
        for k in part_reqs:
            r += k.request
        i.username = len(schedules)  # total scheduled
        i.email = len(fixed)  # total fixed
        i.password = len(cancel)  # total cancelled
        i.is_active = r  # total parts requested
    start_date = 'All'
    end_date = 'All'
    if request.method == 'POST':
        start_date = request.POST['date']
        end_date = request.POST["date2"]
        title = f'Technicians Report from {start_date} to {end_date}'

        for i in plist:
            r = 0
            schedules = Schedule.objects.filter(cancelled=False, user=i.id, created_at__gte=start_date,
                                                created_at__lte=end_date)
            cancel = Schedule.objects.filter(date_cancelled__gte=start_date, date_cancelled__lte=end_date,
                                             cancelled=True, requested_by=i.email)
            fixed = Schedule.objects.filter(cancelled=False, date_repaired__gte=start_date,
                                            date_repaired__lte=end_date, fixed_by__icontains=str(i.id))
            part_reqs = PartStock.objects.filter(user=f'{i.first_name} {i.middle_name} {i.last_name}',
                                                 action_status='Approved', created_at__gte=start_date,
                                                 created_at__lte=end_date)
            for k in part_reqs:
                r += k.request
            i.username = len(schedules)  # total scheduled
            i.email = len(fixed)  # total fixed
            i.password = len(cancel)  # total cancelled
            i.is_active = r  # total parts requested
    return render(request, "users/user_report.html",
                  {'parts': plist, 'title': title, 'date2': end_date, 'date': start_date})


# User report breakdown
@login_required(login_url='login')
def user_report_details(request, pk, type, period, date, date2):
    user = User.objects.get(pk=pk)
    r = 0
    schedules = Schedule.objects.filter(user=pk, cancelled=False).all()
    cancel = Schedule.objects.filter(cancelled=True, requested_by=user.email).all()
    fixed = Schedule.objects.filter(cancelled=False, fixed_by__icontains=str(user.id)).all()
    part_reqs = PartStock.objects.filter(user=f'{user.first_name} {user.middle_name} {user.last_name}',
                                         action_status='Approved').exclude(request=0)
    title = f'Printers {type} by {user}'

    if type == 'scheduled' and period[0] == 'A':
        data = schedules
    elif type == 'scheduled':
        data = Schedule.objects.filter(cancelled=False, user=user.id, created_at__gte=date, created_at__lte=date2)
    elif type == 'fixed' and period[0] == 'A':
        data = fixed
    elif type == 'fixed':
        data = Schedule.objects.filter(cancelled=False, fixed_by__icontains=str(user.id), date_repaired__gte=date,
                                       date_repaired__lte=date2)
    elif type == 'cancelled' and period[0] == 'A':
        data = cancel
    elif type == 'cancelled':
        title = f'Approved {type} printers by {user}'
        data = Schedule.objects.filter(cancelled=True, requested_by=user.email, date_cancelled__gte=date,
                                       date_cancelled__lte=date2)
    else:
        title = f'Part requested by {user}'
        data = part_reqs
    json_data = {'schedules': data, 'period': period, 'pk': pk, 'type': type, 'title': title, 'date': date,
                 'date2': date2}
    return render(request, 'schedule/user_report_details.html', json_data)


# Part report breakdown
@login_required(login_url='login')
def user_part_report_details(request, pk, name, period, date, date2):
    user = User.objects.get(pk=pk)
    title = f'All {name} serial numbers used by {user}'
    schedules, board, ph, others = [], [], [], []
    if period[0] == 'A':
        fixed = Schedule.objects.filter(cancelled=False, repair_status='Fixed', fixed_by__icontains=str(pk)). \
            order_by('-date_repaired')
        for i in fixed:
            if name == 'Print head' and i.new_head_barcode:
                ph.append(i)
            elif name == 'Board' and i.new_board:
                board.append(i)
        if name == 'Board':
            schedules = board
        elif name == 'Print head':
            schedules = ph
        else:
            schedules = others
    else:
        title = f'{name} serial numbers used by {user} from {date} to {date2}'
        fixed = Schedule.objects.filter(cancelled=False, fixed_by__icontains=str(pk), date_repaired__gte=date,
                                        date_repaired__lte=date2)
        for i in fixed:
            if name == 'Print head' and i.new_head_barcode:
                ph.append(i)
            elif name == 'Board' and i.new_board:
                board.append(i)
        if name == 'Board':
            schedules = board
        elif name == 'Print head':
            schedules = ph
        else:
            schedules = others

    json_data = {'schedules': schedules, 'name': name, 'title': title}
    return render(request, 'schedule/user_part_report_details.html', json_data)


# Client managements options
@login_required(login_url='login')
def client_options(request):
    return render(request, "clients/client_options.html")


# Add a new client to our list of clients
@login_required(login_url='login')
def add_client(request):
    if request.method == 'POST':
        form = AddClientForm(request.POST)
        if form.is_valid():
            current_user = request.user
            new_client = form.save(commit=False)
            name = form.cleaned_data.get('client_name')
            new_client.requested_by = str(current_user)
            new_client.approved_by = str(current_user)
            new_client.save()
            Event.objects.create(user_id=current_user.pk, action='Added {} as a new client'.format(name))
            messages.success(request, 'Client {} added successfully!'.format(name))
            return redirect('add_client')
    else:
        form = AddClientForm()
    return render(request, 'clients/add_client.html', {'form': form})


# View clients
@login_required(login_url='login')
def clients(request):
    clist = Client.objects.all().exclude(action_status='Pending').order_by('-updated_at')
    return render(request, "clients/clients.html", {'clients': clist})


# Client report on printers
@login_required(login_url='login')
def client_report(request):
    st = str(datetime.today() - timedelta(days=5))[:10]
    td = str(datetime.today())[:10]
    title = f'Weekly Report for {st} to ' + td
    plist = Client.objects.filter(action_status='Approved').order_by('-created_at')
    start_date = td
    end_date = td

    for i in plist:
        schedules = Schedule.objects.filter(client=i.id, cancelled=False,
                                            pickup_date__gte=datetime.today() - timedelta(days=5),
                                            pickup_date__lte=datetime.today())
        cancel = Schedule.objects.filter(date_cancelled__gte=datetime.today() - timedelta(days=5),
                                         date_cancelled__lte=datetime.today(),
                                         cancelled=True, client=i.id)
        fixed = Schedule.objects.filter(date_repaired__gte=datetime.today() - timedelta(days=5),
                                        date_repaired__lte=datetime.today(),
                                        repair_status='Fixed', cancelled=False, client=i.id)
        pending = Schedule.objects.filter(repair_status='Pending', cancelled=False, client=i.id)
        i.requested_by = len(pending)  # total pending
        i.address = len(schedules)  # total scheduled
        i.rep = len(fixed)  # total fixed
        i.approved_by = len(cancel)  # total cancelled
    if request.method == 'POST':
        start_date = request.POST['date']
        end_date = request.POST["date2"]
        title = f'Client Report from {start_date} to {end_date}'
        for i in plist:
            schedules = Schedule.objects.filter(client=i.id, cancelled=False, pickup_date__gte=start_date,
                                                pickup_date__lte=end_date)
            cancel = Schedule.objects.filter(date_cancelled__gte=start_date, date_cancelled__lte=end_date,
                                             cancelled=True, client=i.id)
            fixed = Schedule.objects.filter(date_repaired__gte=start_date, date_repaired__lte=end_date,
                                            repair_status='Fixed', cancelled=False, client=i.id)
            pending = Schedule.objects.filter(repair_status='Pending', cancelled=False, client=i.id)
            i.requested_by = len(pending)  # total pending
            i.address = len(schedules)  # total scheduled
            i.rep = len(fixed)  # total fixed
            i.approved_by = len(cancel)  # total cancelled
    return render(request, "clients/client_report.html",
                  {'parts': plist, 'title': title, 'date2': end_date, 'date': start_date})


# client report breakdown
@login_required(login_url='login')
def client_report_details(request, pk, type, period, date, date2):
    user = Client.objects.get(pk=pk)
    pending = Schedule.objects.filter(repair_status='Pending', cancelled=False, client=pk)

    title = f'{user} {type} printers'

    date_object = datetime.strptime(date, '%Y-%m-%d')  # date object

    if type == 'scheduled' and period[0] == 'W':
        data = Schedule.objects.filter(client=pk, cancelled=False, pickup_date__gte=date_object - timedelta(days=5),
                                       pickup_date__lte=date)
    elif type == 'scheduled':
        data = Schedule.objects.filter(cancelled=False, client=pk, pickup_date__gte=date, pickup_date__lte=date2)
    elif type == 'fixed' and period[0] == 'W':
        data = Schedule.objects.filter(cancelled=False, repair_status='Fixed', client=pk,
                                       date_repaired__gte=date_object - timedelta(days=5),
                                       date_repaired__lte=date)
    # fixed = Schedule.objects.filter(date_repaired__gte=datetime.today() - timedelta(days=5),
    #                                 date_repaired__lte=datetime.today(),
    #                                 repair_status='Fixed', cancelled=False, client=i.id)

    elif type == 'fixed':
        data = Schedule.objects.filter(cancelled=False, repair_status='Fixed', client=pk, date_repaired__gte=date,
                                       date_repaired__lte=date2)
    elif type == 'cancelled' and period[0] == 'W':
        title = f'Approved {user} {type} printers'
        data = Schedule.objects.filter(cancelled=True, client=pk, date_cancelled__gte=date_object - timedelta(days=5),
                                       date_cancelled__lte=date)
    elif type == 'cancelled':
        title = f'Approved {user} {type} printers'
        data = Schedule.objects.filter(cancelled=True, client=pk, date_cancelled__gte=date,
                                       date_cancelled__lte=date2)
    else:
        data = pending
    json_data = {'schedules': data, 'period': period, 'pk': pk, 'type': type, 'title': title}

    return render(request, 'clients/client_report_details.html', json_data)


# Update from clients list
@login_required(login_url='login')
def update_client(request, pk):
    item = Client.objects.get(id=pk)
    form = UpdateClientForm(instance=item)
    current_user = request.user

    if request.method == 'POST':
        form = UpdateClientForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            Event.objects.create(user_id=current_user.pk, action='Updated client {}'.format(item))
            messages.success(request, 'Client {} updated successfully!'.format(item))
            return redirect('clients')
    return render(request, 'clients/update_client.html', {'form': form})


# Make a new RMA request
@login_required(login_url='login')
def add_rma(request):
    if request.method == 'POST':
        form = AddPrinterRMAForm(request.POST)
        if form.is_valid():
            current_user = request.user
            pname = form.cleaned_data.get('printer_number')
            pn = str(form.cleaned_data.get('part_name'))
            fbc = form.cleaned_data.get('faulty_part_barcode')
            existing_printer = Procurement.objects.filter(printer_number=pname)
            if not existing_printer:
                Procurement.objects.create(printer_number=pname)
                PrinterRMA.objects.create(user=current_user, printer_id=pname, part_name=pn,
                                          faulty_part_barcode=fbc)
                messages.success(request, 'Printer {} RMA requested successfully!'.format(pname))
                messages.warning(request, 'Printer {} procurement details not updated'.format(pname))
                return redirect('add_rma')
            PrinterRMA.objects.create(user=current_user, printer_id=pname, part_name=pn,
                                      faulty_part_barcode=fbc)
            Event.objects.create(user_id=current_user.pk, action='Request RMA for printer {}'.format(pname))
            messages.success(request, 'Printer {} RMA requested successfully!'.format(pname))
            return redirect('rma_requests')
    else:
        form = AddPrinterRMAForm()
    return render(request, 'printers/add_rma.html', {'form': form})


# RMA requests report
@login_required(login_url='login')
def rma_requests(request):
    plist = PrinterRMA.objects.all().order_by('-updated_at')
    today = datetime.today().date()
    for i in plist:
        printer = Procurement.objects.get(printer_number=i.printer_id)
        if not (printer.warranty_years and printer.warranty_start_date):
            printer.warranty_status = 'Pending'
            printer.save()
        else:
            difference = (today - printer.warranty_start_date).days / 365
            if difference > printer.warranty_years:
                printer.warranty_status = 'Declined'
            else:
                printer.warranty_status = 'Accepted'
            printer.save()
        i.updated_at = printer.warranty_status
    return render(request, "printers/rma_requests.html", {'printers': plist})


# Update from printers list
@login_required(login_url='login')
def update_rma(request, pk):
    item = PrinterRMA.objects.get(id=pk)
    form = UpdateRMAForm(instance=item)
    current_user = request.user

    if request.method == 'POST':
        form = UpdateRMAForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            Event.objects.create(user_id=current_user.pk, action='Updated printer {} RMA request'.format(item))
            messages.success(request, 'Printer {} RMA request updated successfully!'.format(item))
            return redirect('rma_requests')
    return render(request, 'printers/update_rma.html', {'form': form})


# View printers under maintenance
@login_required(login_url='login')
def maintenance(request):
    schedules = Schedule.objects.filter(cancelled=False, repair_status='Pending').order_by('-updated_at')
    return render(request, "schedule/maintenance.html", {'schedules': schedules})


# View delay maintenance
@login_required(login_url='login')
def delay_maintenances(request):
    title = 'no parts available'
    qrs = Schedule.objects.filter(cancelled=False, repair_status='Pending')
    schedules = []
    for i in qrs:
        if i.delay_maintenance_reason == 'No parts available':
            schedules.append(i)
    if request.method == 'POST':
        schedules = []
        key = request.POST["key"]
        if key == 'cd':
            title = 'car delay'
            for i in qrs:
                if i.delay_maintenance_reason == 'Car delay':
                    schedules.append(i)
        elif key == 'ii':
            title = 'internal issues'
            for i in qrs:
                if i.delay_maintenance_reason == 'Internal issues':
                    schedules.append(i)
        else:
            for i in qrs:
                if i.delay_maintenance_reason == 'No parts available':
                    schedules.append(i)
    return render(request, "schedule/delay_maintenances.html", {'schedules': schedules, 'title': title})


# View detailed maintenance occurrence
@login_required(login_url='login')
def maintenance_occurrence(request):
    title, title2 = '', ''
    index = 0
    schedules = Schedule.objects.filter(cancelled=False).order_by('-pickup_date')
    for i in schedules:
        if i.fixed_by:
            a = (str([i.fixed_by])[1:-1][1:-1]).replace("'", '').replace(',', " ").split()
            l = list(map(int, a))
            for k in l:
                pk = k
            i.fixed_by = User.objects.get(id=pk)
        index += 1
        i.action_status = index
        i.delivery_status = ''

    if request.method == 'POST':
        index = 0
        occurrence = abs(int(request.POST['occurrence']))
        start_date = request.POST['date']
        end_date = request.POST["date2"]
        schedules, num = [], []
        title2 = f'From {start_date} to {end_date}'
        qlist = Schedule.objects.filter(cancelled=False, pickup_date__gte=start_date, pickup_date__lte=end_date). \
            order_by('printer_number')

        def cal(val):
            if not num:
                num.append(val)
            else:
                # remove printer occurring more than ones
                check = any(val.printer_number in num for val.printer_number in qrst)
                if check is False:
                    num.append(val)

        for i in qlist:
            qrst = Schedule.objects.filter(printer_number=i.printer_number, cancelled=False,
                                           pickup_date__gte=start_date, pickup_date__lte=end_date)
            if len(qrst) >= occurrence:
                cal(i)
                if i.fixed_by:
                    a = (str([i.fixed_by])[1:-1][1:-1]).replace("'", '').replace(',', " ").split()
                    l = list(map(int, a))
                    for k in l:
                        pk = k
                    i.fixed_by = User.objects.get(id=pk)
                index += 1
                i.action_status = index
                i.delivery_status = len(qrst)
                schedules.append(i)

        title = f'{len(num)} Printers occurred minimum of {occurrence} times for maintenance'
    return render(request, "schedule/occurrence.html", {'schedules': schedules, 'title': title, 'title2': title2})


# View summarized maintenance occurrence
@login_required(login_url='login')
def summarized_maintenance_occurrence(request):
    data = request.session['list']
    index = 0
    list = Schedule.objects.filter(cancelled=False).order_by('-updated_at')
    schedules = []
    for i in list:
        # sort the printer occurrences from db of uncancelled schedules
        qrst = Schedule.objects.filter(printer_number=i.printer_number, cancelled=False)
        if len(qrst) >= data[0]:
            if not schedules:
                index += 1
                i.repair_status = index
                i.delivery_status = len(qrst)
                schedules.append(i)
            else:
                # remove printer occurring more than ones
                check = any(i.printer_number in schedules for i.printer_number in qrst)
                if check is False:
                    index += 1
                    i.repair_status = index
                    i.delivery_status = len(qrst)
                    schedules.append(i)
    return render(request, "schedule/summarized_occurrence.html", {'schedules': schedules})


# View fixed printers
@login_required(login_url='login')
def fixed_printers(request):
    title, start_date, end_date = '', '', ''
    schedules = Schedule.objects.filter(cancelled=False, repair_status='Fixed').order_by('-updated_at')
    for i in schedules:
        a = (str([i.fixed_by])[1:-1][1:-1]).replace("'", '').replace(',', " ").split()
        l = list(map(int, a))
        for k in l:
            pk = k
            i.fixed_by = User.objects.get(id=pk)
    if request.method == 'POST':
        start_date = request.POST['date']
        end_date = request.POST["date2"]
        title = f'From {start_date} to {end_date}'
        schedules = Schedule.objects.filter(cancelled=False, repair_status='Fixed', date_repaired__gte=start_date,
                                            date_repaired__lte=end_date)
        for i in schedules:
            a = (str([i.fixed_by])[1:-1][1:-1]).replace("'", '').replace(',', " ").split()
            l = list(map(int, a))
            for k in l:
                pk = k
            i.fixed_by = User.objects.get(id=pk)
    return render(request, "schedule/fixed_printers.html",
                  {'schedules': schedules, 'title': title, 'date2': end_date, 'date': start_date})


# View cancelled schedules
@login_required(login_url='login')
def cancelled_schedules(request):
    schedules = Schedule.objects.filter(cancelled=True).order_by('-updated_at')
    for i in schedules:
        i.requested_by = User.objects.get(email=i.requested_by)
    return render(request, "schedule/cancelled_schedules.html", {'schedules': schedules})


# View fixed but undelivered printers
@login_required(login_url='login')
def fixed_undelivered_printers(request):
    schedules = Schedule.objects.filter(cancelled=False, repair_status='Fixed', delivery_status='Pending').order_by(
        '-updated_at')
    return render(request, "schedule/fixed_undelivered_printers.html", {'schedules': schedules})


# Update from maintenance list
@login_required(login_url='login')
def update_maintenance(request, pk):
    item = Schedule.objects.get(id=pk)
    form = UpdateScheduleForm(instance=item)
    current_user = request.user

    if request.method == 'POST':
        form = UpdateScheduleForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            Event.objects.create(user_id=current_user.pk, action='Updated printer {} maintenance schedule'.
                                 format(item.printer_number))
            messages.success(request,
                             'Printer {} maintenance schedule updated successfully!'.format(item.printer_number))
            return redirect('maintenance')
    return render(request, 'schedule/update_schedule.html', {'form': form})


# cancel from maintenance list
@login_required(login_url='login')
def cancel_maintenance(request, pk):
    item = Schedule.objects.get(id=pk)
    if request.method == 'POST':
        form = CancelMaintenanceForm(request.POST)
        if form.is_valid():
            current_user = request.user
            item.cancelled = True
            item.date_cancelled = datetime.today()
            item.approved_by = str(current_user)
            item.requested_by = current_user.email
            item.cancellation_reason = form.cleaned_data.get('cancellation_reason')
            item.save()
            Event.objects.create(user_id=current_user.pk, action='Cancelled printer {} maintenance schedule'
                                 .format(item.printer_number))
            messages.success(request,
                             'Printer {} maintenance schedule cancelled successfully!'.format(item.printer_number))
            return redirect('maintenance')
    else:
        form = CancelMaintenanceForm()
    return render(request, 'schedule/cancel_schedule.html', {'form': form})


# cancel with printer number
@login_required(login_url='login')
def cancel_schedule(request):
    if request.method == 'POST':
        form = CancelScheduleForm(request.POST)
        if form.is_valid():
            current_user = request.user
            pname = form.cleaned_data.get('printer_number').capitalize()

            fixed_update_required = Schedule.objects.filter(printer_number=pname, cancelled=False,
                                                            repair_status='Pending')

            if not fixed_update_required:
                messages.warning(request, 'Sorry, Printer {} has not been scheduled for maintenance! '
                                          'Perhaps it has been updated as fixed'.format(pname))
                return redirect('cancel_schedule')

            else:
                for update in fixed_update_required:
                    update.cancelled = True
                    update.requested_by = current_user.email
                    update.approved_by = str(current_user)
                    update.date_cancelled = datetime.today()
                    update.cancellation_reason = form.cleaned_data.get('cancellation_reason')
                    update.save()
                    Event.objects.create(user_id=current_user.pk, action='Cancelled printer {} maintenance schedule'.
                                         format(pname))
                messages.success(request,
                                 'Printer {} maintenance schedule has successfully been cancelled!'.format(pname))
                return redirect('cancel_schedule')
    else:
        form = CancelScheduleForm()
    return render(request, 'schedule/cancel_schedule.html', {'form': form})


@login_required(login_url='login')
def schedule(request):
    if request.method == 'POST':
        form = ScheduleForm(request.POST)
        if form.is_valid():
            current_user = request.user
            bname = form.cleaned_data.get('box_number')
            pname = form.cleaned_data.get('printer_number').upper()
            pparts = form.cleaned_data.get('pickup_parts')
            cname = (form.cleaned_data.get('client'))
            pdate = form.cleaned_data.get('pickup_date')
            p = form.cleaned_data.get('problem')
            asstech = form.cleaned_data.get('assigned_technicians')
            cid = Client.objects.get(client_name=cname).pk
            uid = current_user.pk
            purchased = Procurement.objects.filter(printer_number=pname)

            try:
                # Query validations on schedule
                both_update_required = Schedule.objects.filter(printer_number=pname, cancelled=False,
                                                               repair_status='Pending', delivery_status='Pending')
                fixed_update_required = Schedule.objects.filter(printer_number=pname, cancelled=False,
                                                                repair_status='Pending')
                delivered_update_required = Schedule.objects.filter(printer_number=pname, cancelled=False,
                                                                    delivery_status='Pending')

            except (TypeError, ValueError, OverflowError):
                existing_printer = None

            if both_update_required:
                # prompt user schedule already exist and redirect to to update both fixed and delivery statuses
                messages.warning(request,
                                 'Printer {} schedule needs both repair and delivery status updates'.format(pname))
                return redirect('both_update_schedule')

            elif fixed_update_required:
                # prompt user schedule already exist and redirect to to update fixed status
                messages.warning(request, 'Printer {} schedule needs repair status update'.format(pname))
                return redirect('fixed_update_schedule')

            elif delivered_update_required:
                # prompt user schedule already exist and redirect to to update delivery status
                messages.warning(request, 'Printer {} schedule needs delivery status update!'.format(pname))
                return redirect('delivery_update_schedule')

            else:
                if not purchased:
                    Procurement.objects.create(user=current_user, printer_number=pname, box_number=bname, client_id=cid)
                Schedule.objects.create(user_id=uid, box_number=bname, client_id=cid, printer_number=pname,
                                        pickup_parts=pparts, pickup_date=pdate, problem=p, assigned_technicians=asstech)
                Event.objects.create(user_id=current_user.pk, action=f'Scheduled printer {pname} for maintenance')
                messages.success(request, 'Printer {} scheduled for maintenance successfully!'.format(pname))
                return redirect('schedule')
    else:
        form = ScheduleForm()
    return render(request, 'schedule/schedule.html', {'form': form})


# parts requests while repairs
def part_request(part):
    req = 1

    def check_available(name):
        qrs = PartStock.objects.filter(name=Part.objects.get(name=name).pk, action_status='Approved')
        r = 0
        t = 0
        for i in qrs:
            r += i.request
            t += i.topup
        return t - r

    available = check_available(part)
    if req > available:
        return [False, available]
    else:
        return [True, available]


# Direct update with printer number
@login_required(login_url='login')
def both_update_schedule(request):
    if request.method == 'POST':
        form = BothUpdateScheduleForm(request.POST)
        if form.is_valid():
            current_user = request.user
            pname = form.cleaned_data.get('printer_number').capitalize()

            both_update_required = Schedule.objects.filter(printer_number=pname, cancelled=False,
                                                           repair_status='Pending', delivery_status='Pending')

            if not both_update_required:
                messages.warning(request, 'Sorry, Printer {} has not been scheduled for maintenance! '
                                          'Perhaps it has been updated as repaired and delivered'.format(pname))
                return redirect('both_update_schedule')
            else:
                # check part requested
                nb = form.cleaned_data.get('new_board')
                nh = form.cleaned_data.get('new_head_barcode')
                if nh and nb:
                    h = part_request('Print head')
                    b = part_request('Board')
                    if (h[0] is True) and (b[0] is True):
                        PartStock.objects.create(name_id=Part.objects.get(name='Print head').pk, request=1,
                                                 user=str(current_user))
                        PartStock.objects.create(name_id=Part.objects.get(name='Board').pk, request=1,
                                                 user=str(current_user))
                        Event.objects.create(user_id=current_user.pk, action='Requested 1 Print Head')
                        Event.objects.create(user_id=current_user.pk, action='Requested 1 Board')
                        PartEvent.objects.create(user_id=current_user.pk, action='Requested 1 Board')
                        PartEvent.objects.create(user_id=current_user.pk, action='Requested 1 Print Head')
                    else:
                        messages.warning(request, 'Insufficient Print Heads/Boards available in stock!')
                        messages.info(request, '{} Print Heads and {} Boards available in stock!'.format(h[1], b[1]))
                        return redirect('both_update_schedule')
                elif nh:
                    h = part_request('Print head')
                    if h[0] is True:
                        PartStock.objects.create(name_id=Part.objects.get(name='Print head').pk, request=1,
                                                 user=str(current_user))
                        Event.objects.create(user_id=current_user.pk, action='Requested 1 Print Head')
                        PartEvent.objects.create(user_id=current_user.pk, action='Requested 1 Print Head')
                    else:
                        messages.warning(request, 'Insufficient Print Heads available in stock!')
                        messages.info(request, '{} Print Heads available in stock!'.format(h[1]))
                        return redirect('both_update_schedule')
                elif nb:
                    b = part_request('Board')
                    if b[0] is True:
                        PartStock.objects.create(name_id=Part.objects.get(name='Board').pk, request=1,
                                                 user=str(current_user))
                        Event.objects.create(user_id=current_user.pk, action='Requested 1 Board')
                        PartEvent.objects.create(user_id=current_user.pk, action='Requested 1 Board')
                    else:
                        messages.warning(request, 'Insufficient Boards available in stock!')
                        messages.info(request, '{} Boards available in stock!'.format(b[1]))
                        return redirect('both_update_schedule')
                for update in both_update_required:
                    update.repair_status = 'Fixed'
                    update.date_repaired = form.cleaned_data.get('date_repaired')
                    update.problem = form.cleaned_data.get('problem')
                    update.parts_replaced = form.cleaned_data.get('parts_replaced')
                    update.old_head_barcode = form.cleaned_data.get('old_head_barcode')
                    update.new_head_barcode = nh
                    update.old_board = form.cleaned_data.get('old_board')
                    update.new_board = nb
                    update.delivery_status = 'Delivered'
                    update.fixed_by = str(current_user.pk)
                    update.date_delivered = form.cleaned_data.get('date_delivered')
                    update.save()
                    Event.objects.create(user_id=current_user.pk, action='Updated both repair and delivery status of '
                                                                         'printer {} maintenance schedule'.format(
                        pname))
                    check_to_rate(user=current_user, current_site=get_current_site(request).domain,
                                  client=update.client)
                messages.success(request, 'Printer {} maintenance schedule '
                                          'has successfully been updated!'.format(pname))
                return redirect('both_update_schedule')
    else:
        form = BothUpdateScheduleForm()
    return render(request, 'schedule/both_update.html', {'form': form})


# both schedule and update printer
@login_required(login_url='login')
def schedule_update(request):
    if request.method == 'POST':
        form = ScheduleUpdateForm(request.POST)
        if form.is_valid():
            current_user = request.user
            bname = form.cleaned_data.get('box_number')
            pname = form.cleaned_data.get('printer_number').upper()
            pparts = form.cleaned_data.get('pickup_parts')
            cname = (form.cleaned_data.get('client'))
            pdate = form.cleaned_data.get('pickup_date')
            p = form.cleaned_data.get('problem')
            cid = Client.objects.get(client_name=cname).pk
            uid = current_user.pk
            dr = form.cleaned_data.get('date_repaired')
            pr = form.cleaned_data.get('parts_replaced')
            nb = form.cleaned_data.get('new_board')
            nh = form.cleaned_data.get('new_head')
            oh = form.cleaned_data.get('old_head')
            ob = form.cleaned_data.get('old_board')
            dd = form.cleaned_data.get('date_delivered')
            purchased = Procurement.objects.filter(printer_number=pname)

            try:
                # Query validations on schedule
                both_update_required = Schedule.objects.filter(printer_number=pname, cancelled=False,
                                                               repair_status='Pending', delivery_status='Pending')
                fixed_update_required = Schedule.objects.filter(printer_number=pname, cancelled=False,
                                                                repair_status='Pending')
                delivered_update_required = Schedule.objects.filter(printer_number=pname, cancelled=False,
                                                                    delivery_status='Pending')

            except (TypeError, ValueError, OverflowError):
                existing_printer = None

            if both_update_required:
                # prompt user schedule already exist and redirect to to update both fixed and delivery statuses
                messages.warning(request,
                                 'Printer {} schedule needs both repair and delivery status updates'.format(pname))
                return redirect('both_update_schedule')

            elif fixed_update_required:
                # prompt user schedule already exist and redirect to update fixed status
                messages.warning(request, 'Printer {} schedule needs repair status update'.format(pname))
                return redirect('fixed_update_schedule')

            elif delivered_update_required:
                # prompt user schedule already exist and redirect to to update delivery status
                messages.warning(request, 'Printer {} schedule needs delivery status update!'.format(pname))
                return redirect('delivery_update_schedule')

            else:
                # check part requested
                if nh and nb:
                    h = part_request('Print head')
                    b = part_request('Board')
                    if (h[0] is True) and (b[0] is True):
                        PartStock.objects.create(name_id=Part.objects.get(name='Print head').pk, request=1,
                                                 user=str(current_user))
                        PartStock.objects.create(name_id=Part.objects.get(name='Board').pk, request=1,
                                                 user=str(current_user))
                        Event.objects.create(user_id=current_user.pk, action='Requested 1 Print Head')
                        Event.objects.create(user_id=current_user.pk, action='Requested 1 Board')
                        PartEvent.objects.create(user_id=current_user.pk, action='Requested 1 Board')
                        PartEvent.objects.create(user_id=current_user.pk, action='Requested 1 Print Head')
                    else:
                        messages.warning(request, 'Insufficient Print Heads/Boards available in stock!')
                        messages.info(request, '{} Print Heads and {} Boards available in stock!'.format(h[1], b[1]))
                        return redirect('schedule_update')
                elif nh:
                    h = part_request('Print head')
                    if h[0] is True:
                        PartStock.objects.create(name_id=Part.objects.get(name='Print head').pk, request=1,
                                                 user=str(current_user))
                        Event.objects.create(user_id=current_user.pk, action='Requested 1 Print Head')
                        PartEvent.objects.create(user_id=current_user.pk, action='Requested 1 Print Head')
                    else:
                        messages.warning(request, 'Insufficient Print Heads available in stock!')
                        messages.info(request, '{} Print Heads available in stock!'.format(h[1]))
                        return redirect('schedule_update')
                elif nb:
                    b = part_request('Board')
                    if b[0] is True:
                        PartStock.objects.create(name_id=Part.objects.get(name='Board').pk, request=1,
                                                 user=str(current_user))
                        Event.objects.create(user_id=current_user.pk, action='Requested 1 Board')
                        PartEvent.objects.create(user_id=current_user.pk, action='Requested 1 Board')
                    else:
                        messages.warning(request, 'Insufficient Boards available in stock!')
                        messages.info(request, '{} Boards available in stock!'.format(b[1]))
                        return redirect('schedule_update')
                Schedule.objects.create(user_id=uid, box_number=bname, client_id=cid, printer_number=pname,
                                        repair_status='Fixed',
                                        pickup_parts=pparts, pickup_date=pdate, problem=p, date_repaired=dr,
                                        delivery_status='Delivered',
                                        date_delivered=dd, parts_replaced=pr, old_head_barcode=oh, new_head_barcode=nh,
                                        old_board=ob, new_board=nb, fixed_by=str(current_user.pk))
                if not purchased:
                    Procurement.objects.create(user=current_user, printer_number=pname, box_number=bname, client_id=cid)
                Event.objects.create(user_id=current_user.pk, action=f'Scheduled printer {pname} for maintenance')
                messages.success(request, 'Printer {} scheduled for maintenance successfully!'.format(pname))
                return redirect('schedule_update')
    else:
        form = ScheduleUpdateForm()
    return render(request, 'schedule/schedule_update.html', {'form': form})


# Direct update with printer number
@login_required(login_url='login')
def fixed_update_schedule(request):
    if request.method == 'POST':
        form = FixedUpdateScheduleForm(request.POST)
        if form.is_valid():
            current_user = request.user
            pname = form.cleaned_data.get('printer_number').capitalize()

            fixed_update_required = Schedule.objects.filter(printer_number=pname, cancelled=False,
                                                            repair_status='Pending')

            if fixed_update_required:
                # check part requested
                nb = form.cleaned_data.get('new_board')
                nh = form.cleaned_data.get('new_head_barcode')
                if nh and nb:
                    h = part_request('Print head')
                    b = part_request('Board')
                    if (h[0] is True) and (b[0] is True):
                        PartStock.objects.create(name_id=Part.objects.get(name='Print head').pk, request=1,
                                                 user=str(current_user))
                        PartStock.objects.create(name_id=Part.objects.get(name='Board').pk, request=1,
                                                 user=str(current_user))
                        Event.objects.create(user_id=current_user.pk, action='Requested 1 Print Head')
                        Event.objects.create(user_id=current_user.pk, action='Requested 1 Board')
                        PartEvent.objects.create(user_id=current_user.pk, action='Requested 1 Board')
                        PartEvent.objects.create(user_id=current_user.pk, action='Requested 1 Print Head')
                    else:
                        messages.warning(request, 'Insufficient Print Heads/Boards available in stock!')
                        messages.info(request, '{} Print Heads and {} Boards available in stock!'.format(h[1], b[1]))
                        return redirect('fixed_update_schedule')
                elif nh:
                    h = part_request('Print head')
                    if h[0] is True:
                        PartStock.objects.create(name_id=Part.objects.get(name='Print head').pk, request=1,
                                                 user=str(current_user))
                        Event.objects.create(user_id=current_user.pk, action='Requested 1 Print Head')
                        PartEvent.objects.create(user_id=current_user.pk, action='Requested 1 Print Head')
                    else:
                        messages.warning(request, 'Insufficient Print Heads available in stock!')
                        messages.info(request, '{} Print Heads available in stock!'.format(h[1]))
                        return redirect('fixed_update_schedule')
                elif nb:
                    b = part_request('Board')
                    if b[0] is True:
                        PartStock.objects.create(name_id=Part.objects.get(name='Board').pk, request=1,
                                                 user=str(current_user))
                        Event.objects.create(user_id=current_user.pk, action='Requested 1 Board')
                        PartEvent.objects.create(user_id=current_user.pk, action='Requested 1 Board')
                    else:
                        messages.warning(request, 'Insufficient Boards available in stock!')
                        messages.info(request, '{} Boards available in stock!'.format(b[1]))
                        return redirect('fixed_update_schedule')
                for update in fixed_update_required:
                    update.repair_status = 'Fixed'
                    update.date_repaired = form.cleaned_data.get('date_repaired')
                    update.problem = form.cleaned_data.get('problem')
                    update.parts_replaced = form.cleaned_data.get('parts_replaced')
                    update.old_head_barcode = form.cleaned_data.get('old_head_barcode')
                    update.new_head_barcode = nh
                    update.old_board = form.cleaned_data.get('old_board')
                    update.new_board = nb
                    update.fixed_by = str(current_user.pk)
                    update.save()
                    Event.objects.create(user_id=current_user.pk, action='Updated repair status of '
                                                                         'printer {} maintenance schedule'.format(
                        pname))
                    check_to_rate(user=current_user, current_site=get_current_site(request).domain,
                                  client=update.client)
                messages.success(request, 'Printer {} maintenance schedule has been updated successfully'
                                          'and its delivery status still remains pending!'.format(pname))
                return redirect('fixed_update_schedule')
            else:
                messages.warning(request, 'Sorry, Printer {} has not been scheduled for maintenance! '
                                          'Perhaps it has been updated as repaired'.format(pname))
                return redirect('fixed_update_schedule')
    else:
        form = FixedUpdateScheduleForm()
    return render(request, 'schedule/fixed_update.html', {'form': form})


# Direct update with printer number
@login_required(login_url='login')
def delivery_update_schedule(request):
    if request.method == 'POST':
        form = DeliveryUpdateScheduleForm(request.POST)
        if form.is_valid():
            current_user = request.user
            pname = form.cleaned_data.get('printer_number').capitalize()

            both_update_required = Schedule.objects.filter(printer_number=pname, cancelled=False,
                                                           repair_status='Pending', delivery_status='Pending')

            delivered_update_required = Schedule.objects.filter(printer_number=pname, cancelled=False,
                                                                delivery_status='Pending')

            if both_update_required:
                messages.error(request, 'Sorry, Printer {} scheduled for maintenance '
                                        'requires both fixed and delivery status update'.format(pname))
                return redirect('both_update_schedule')

            elif delivered_update_required:
                for update in delivered_update_required:
                    update.delivery_status = 'Delivered'
                    update.date_delivered = form.cleaned_data.get('date_delivered')
                    update.save()
                    Event.objects.create(user_id=current_user.pk, action='Updated delivery status of '
                                                                         'printer {} maintenance schedule'.format(
                        pname))
                messages.success(request, 'Printer {} maintenance schedule '
                                          'has successfully been updated!'.format(pname))
                return redirect('delivery_update_schedule')
            else:
                messages.warning(request, 'Sorry, Printer {} has not been scheduled for maintenance! '
                                          'Perhaps it has been updated as delivered'.format(pname))
                return redirect('delivery_update_schedule')
    else:
        form = DeliveryUpdateScheduleForm()
    return render(request, 'schedule/delivery_update.html', {'form': form})


# History
@login_required(login_url='login')
def event(request):
    history = Event.objects.all().order_by('-created_at')
    title, start_date, end_date = '', '', ''
    if request.method == 'POST':
        start_date = request.POST['date']
        end_date = request.POST["date2"]
        title = f'From {start_date} to {end_date}'
        history = Event.objects.filter(created_at__date__range=(start_date, end_date)).order_by('-created_at')
    return render(request, "admin_account/events.html",
                  {'events': history, 'title': title, 'date2': end_date, 'date': start_date})


# Available reports
@login_required(login_url='login')
def reports(request):
    return render(request, "admin_account/report_options.html")


# Available printer options
@login_required(login_url='login')
def printer_options(request):
    return render(request, "printers/printer_options.html")


# User managements
@login_required(login_url='login')
def user_management(request):
    return render(request, "users/user_managements.html")


# Waybill generation options
@login_required(login_url='login')
def waybill_options(request):
    return render(request, "waybill/waybill_options.html")


@login_required(login_url='login')
def waybill(request):
    if request.method == 'POST':
        form = WaybillForm(request.POST)
        if form.is_valid():
            client = Client.objects.get(client_name=form.cleaned_data.get('client'))
            client_addr = client.address
            client_name = client.rep
            start_date = form.cleaned_data.get('start_date_for_when_fixed')
            end_date = form.cleaned_data.get('end_date_for_when_fixed')
            data = [str(client), str(client_addr), str(start_date), str(end_date), str(client_name)]
            request.session['list'] = data  # json data
            return redirect('waybill_pdf')
    else:
        form = WaybillForm()
    return render(request, 'waybill/waybill_prompt.html', {'form': form})


@login_required(login_url='login')
def pickup(request):
    if request.method == 'POST':
        form = WaybillPickupForm(request.POST)
        if form.is_valid():
            client = Client.objects.get(client_name=form.cleaned_data.get('client'))
            client_addr = client.address
            client_name = client.rep
            start_date = form.cleaned_data.get('start_date_for_when_picked_up')
            end_date = form.cleaned_data.get('end_date_for_when_picked_up')
            data = [str(client), str(client_addr), str(start_date), str(end_date), str(client_name)]
            request.session['list'] = data  # json data
            return redirect('pickup_pdf')
    else:
        form = WaybillPickupForm()
    return render(request, 'waybill/pickup_prompt.html', {'form': form})


# generating random name
def get_filename(waybill_type):
    length = 7
    # chars = string.ascii_letters + string.digits
    chars = string.digits
    random.seed = (os.urandom(1024))
    name = ''.join(random.choice(chars) for i in range(length))
    return '%s%s' % (waybill_type, str(name))


def waybillpdf(request):
    data = request.session['list']
    client = data[0]
    client_address = data[1]
    client_name = data[4]
    cid = Client.objects.get(client_name=client).pk
    date = datetime.today().strftime('%d %b, %Y')  # ('%d-%m-%Y')
    ddate = datetime.strptime(data[2], '%Y-%m-%d').strftime('%d %b, %Y')
    # date1 = (datetime.today() - timedelta(days=1)).strftime('%d %b, %Y')
    d1 = datetime.today().strftime('%a %d %b, %Y %H:%M:%S')
    waybill_id = get_filename(waybill_type='W{}{}'.format(client[:1], client[-1:]))

    # Fetching printers for the waybill
    fixed = Schedule.objects.filter(cancelled=False, repair_status='Fixed', date_delivered__gte=data[2],
                                    date_delivered__lte=data[3], client_id=cid).order_by('-updated_at')
    data = [["No.", "Printer Number", "Problem Fixed", "Parts Replaced"]]
    index = 0

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{waybill_id}.pdf"'

    # Establish a document
    # template = PageTemplate('normal', [Frame(2.5*cm, 2.5*cm, 15*cm, 25*cm, id='F1')])
    template = PageTemplate('normal', [Frame(2.7 * cm, 4.5 * cm, 15 * cm, 25 * cm, id='F1')])
    doc = BaseDocTemplate(filename=response, pagesize=A4, pageTemplates=template)

    styles = getSampleStyleSheet()
    styleN = styles['Normal']
    styleR = ParagraphStyle(name='right', parent=styles['Normal'], fontName='Helvetica', fontSize=10,
                            alignment=TA_RIGHT)
    styleL = ParagraphStyle(name='left', parent=styles['Normal'], fontName='Helvetica', fontSize=10,
                            alignment=TA_LEFT)

    # Top content
    image = 'static/images/mid.PNG'
    num = [[Paragraph("No.: " + waybill_id, styleR)]]
    top_data = [
        [Paragraph("To: " + client, styleN), Paragraph("Order No.: N/A", styleR)],
        [Paragraph("Address: " + client_address, styleN), Paragraph("Invoice: N/A", styleR)],
        [Paragraph("Delivery Date: " + ddate, styleN)]
    ]

    # # Bottom content
    # bottom_data = [
    #     [Paragraph("Dispatched By: " + str(request.user), styleN),
    #      Paragraph("Received By: ______________________", styleR)],
    #     [Paragraph("Signature: _______________________", styleN),
    #      Paragraph("Signature: ________________________", styleR)],
    #     [Paragraph("Date: " + date, styleN), Paragraph("Date: ____________________________", styleR)]
    # ]

    # Bottom content
    bottom_data = [
        [Paragraph("Dispatched By: " + str(request.user), styleN),
         Paragraph("Received By: " + client_name, styleL)],
        [Paragraph("Signature: _________________________", styleN),
         Paragraph("Signature: ________________", styleL)],
        [Paragraph("Date: " + ddate, styleN), Paragraph("Date: " + ddate, styleL)]
    ]

    # Forming table
    try:
        for i in fixed:
            index += 1
            row = []
            no = str(index).encode('utf-8')
            pid = str(i.printer_number).encode('utf-8')
            pr = str(i.problem).encode('utf-8')
            prd = str(i.parts_replaced).encode('utf-8')
            row.append(no)
            row.append(pid)
            row.append(pr)
            row.append(prd)
            data.append(row)
    except:
        pass

    table = Table(
        data,
        repeatRows=1,
        # colWidths=[1.5 * cm, 3.5 * cm, 10.0 * cm],
        colWidths=[1.0 * cm, 3.0 * cm, 6.0 * cm, 5.0 * cm],
        style=TableStyle(
            [
                ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER')
            ]
        )
    )

    # Display the overall document
    pdf_template = [Image(image, 15 * cm, 5 * cm), Spacer(1, 20),
                    Table(num), Spacer(1, 20),
                    Table(top_data), Spacer(1, 20),
                    table, Spacer(1, 20),
                    Table(bottom_data)
                    ]

    doc.build(pdf_template)
    Waybill.objects.create(user_id=request.user.pk, filename=waybill_id, type=f'{client} waybill', client=client)
    Event.objects.create(user_id=request.user.pk, action='Prepared and downloaded {} waybill'.format(client))
    data = [str(waybill_id)]
    request.session['list'] = data  # json data
    return response


def save_waybill(request):
    try:
        pk = request.session['list']
    except KeyError:
        messages.warning(request, f'Sorry, Finish download before uploading!')
        return redirect('waybill_form')
    if not pk:
        messages.warning(request, 'Sorry, no waybill downloaded yet!')
        return redirect('waybill_form')
    else:
        path = get_path()

        try:
            waybill = Waybill.objects.get(filename=pk[0])
        except (OSError, Waybill.DoesNotExist):
            waybill = None

        if waybill:
            if waybill.file == '':
                try:
                    with open(f'{path}{waybill.filename}.pdf') as f:
                        waybill.file.save(f'{waybill.filename}.pdf', File(f))
                        messages.success(request, f'Waybill {waybill.filename}.pdf uploaded successfully!')
                        return redirect('waybill_form')
                except OSError:
                    messages.warning(request, f'Waybill {waybill.filename}.pdf was not found in your Downloads '
                                              f'directory! Verify if the file is in the same path as "{path}" and try again.')
                    return redirect('waybill_form')
            messages.warning(request, f'Sorry, Finish download before uploading!')
            return redirect('waybill_form')
        elif waybill is None:
            messages.warning(request, f'Sorry, no waybill downloaded yet!')
            return redirect('waybill_form')
        else:
            messages.warning(request, f'Waybill {waybill.filename}.pdf was not found in your Downloads directory! '
                                      f'Verify if the file is in the same path as "{path}"')
            return redirect('waybill_form')


def save_pickup_waybill(request):
    try:
        pk = request.session['list']
    except KeyError:
        messages.warning(request, f'Sorry, Finish download before uploading!')
        return redirect('pickup_form')
    if not pk:
        messages.warning(request, 'Sorry, no waybill downloaded yet!')
        return redirect('pickup_form')
    else:
        path = get_path()

        try:
            waybill = Waybill.objects.get(filename=pk[0])
        except Waybill.DoesNotExist:
            waybill = None

        if waybill:
            if waybill.file == '':
                try:
                    with open(f'{path}{waybill.filename}.pdf') as f:
                        waybill.file.save(f'{waybill.filename}.pdf', File(f))
                        messages.success(request, f'Waybill {waybill.filename}.pdf uploaded successfully!')
                        return redirect('pickup_form')
                except OSError:
                    messages.warning(request, f'Waybill {waybill.filename}.pdf was not found in your Downloads '
                                              f'directory! Verify if the file is in the same path as "{path}" and try again.')
                    return redirect('pickup_form')
            messages.warning(request, f'Sorry, Finish download before uploading!')
            return redirect('pickup_form')
        elif waybill is None:
            messages.warning(request, f'Sorry, no waybill downloaded yet!')
            return redirect('pickup_form')
        else:
            messages.warning(request, f'Waybill {waybill.filename}.pdf was not found in your Downloads directory! '
                                      f'Verify if the file is in the same path as "{path}"')
            return redirect('pickup_form')


def save_waybill_from_list(request, pk):
    waybill = Waybill.objects.get(id=pk)
    path = get_path()

    try:
        with open(f'{path}{waybill.filename}.pdf') as f:
            waybill.file.save(f'{waybill.filename}.pdf', File(f))
            messages.success(request, f'Waybill {waybill.filename}.pdf uploaded successfully!')
            return redirect('user_waybills')
    except OSError:
        messages.warning(request, f'Waybill {waybill.filename}.pdf was not found in your Downloads directory! '
                                  f'Verify if the file is in the same path as "{path}" and try again')
        return redirect('user_waybills')


def download_waybill(request, filename):
    try:
        file_path = settings.MEDIA_ROOT + '/waybills/' + f'{filename}.pdf'
        file_wrapper = FileWrapper(open(file_path, 'rb'))
        response = HttpResponse(file_wrapper, content_type='application/pdf')
        response['X-Sendfile'] = file_path
        response['Content-Length'] = os.stat(file_path).st_size
        response['Content-Disposition'] = f'attachment; filename = "{filename}.pdf"'
        return response
    except OSError:
        messages.warning(request, f'Waybill {filename}.pdf was not uploaded! '
                                  f'Contact Dispatcher to upload.')
        return redirect('waybills')


def view_waybill(request, filename):
    try:
        file_path = settings.MEDIA_ROOT + '/waybills/' + f'{filename}.pdf'
        file_wrapper = FileWrapper(open(file_path, 'rb'))
        response = HttpResponse(file_wrapper, content_type='application/pdf')
        response['X-Sendfile'] = file_path
        response['Content-Length'] = os.stat(file_path).st_size
        response['Content-Disposition'] = f'inline; filename = "{filename}.pdf"'
        return response
    except OSError:
        messages.warning(request, f'Waybill {filename}.pdf was not uploaded! '
                                  f'Contact Dispatcher to upload.')
        return redirect('waybills')


def pickup_pdf(request):
    data = request.session['list']
    client = data[0]
    client_address = data[1]
    client_name = data[4]
    cid = Client.objects.get(client_name=client).pk
    date = datetime.today().strftime('%d %b, %Y')  # ('%d-%m-%Y')
    d1 = datetime.today().strftime('%a %d %b, %Y %H:%M:%S')
    waybill_id = get_filename(waybill_type='P{}{}'.format(client[:1], client[-1:]).upper())

    # Fetching printers for the pickup waybill
    qryset = Schedule.objects.filter(cancelled=False, client_id=cid, pickup_date__gte=data[2],
                                     pickup_date__lte=data[3]).order_by('-created_at')

    data = [["No.", "Box Number", "Printer Number", "Pickup Parts"]]
    index = 0

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{waybill_id}.pdf"'

    # Establish a document
    template = PageTemplate('normal', [Frame(2.7 * cm, 4.5 * cm, 15 * cm, 25 * cm, id='F1')])
    doc = BaseDocTemplate(filename=response, pagesize=A4, pageTemplates=template)

    styles = getSampleStyleSheet()
    styleN = styles['Normal']
    styleR = ParagraphStyle(name='right', parent=styles['Normal'], fontName='Helvetica', fontSize=10,
                            alignment=TA_RIGHT)
    styleL = ParagraphStyle(name='left', parent=styles['Normal'], fontName='Helvetica', fontSize=10,
                            alignment=TA_LEFT)

    # Top content
    image = 'static/images/mid1.PNG'
    num = [[Paragraph("No.: " + waybill_id, styleR)]]
    top_data = [
        [Paragraph("From: " + client, styleN), Paragraph("Order No.: N/A", styleR)],
        [Paragraph("Address: " + client_address, styleN), Paragraph("Invoice: N/A", styleR)],
        [Paragraph("Pickup Date: " + date, styleN)]
    ]

    # Bottom content
    bottom_data = [
        [Paragraph("Dispatched By: " + client_name, styleN),
         Paragraph("Received By: " + str(request.user), styleL)],
        [Paragraph("Signature: _________________________", styleN),
         Paragraph("Signature: ________________", styleL)],
        [Paragraph("Date: " + date, styleN), Paragraph("Date: " + date, styleL)]
    ]

    # Forming table
    try:
        for i in qryset:
            index += 1
            row = []
            no = str(index).encode('utf-8')
            bid = str(i.box_number).encode('utf-8')
            pid = str(i.printer_number).encode('utf-8')
            pkt = str(i.pickup_parts).encode('utf-8')
            row.append(no)
            row.append(bid)
            row.append(pid)
            row.append(pkt)
            data.append(row)
    except:
        pass

    table = Table(
        data,
        repeatRows=1,
        # colWidths=[2 * cm, 5.2 * cm, 7.3 * cm],
        colWidths=[1.0 * cm, 3.2 * cm, 3.0 * cm, 8.0 * cm],
        style=TableStyle(
            [
                ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER')
            ]
        )
    )

    # Display the overall document
    pdf_template = [Image(image, 15 * cm, 5 * cm), Spacer(1, 20),
                    Table(num), Spacer(1, 20),
                    Table(top_data), Spacer(1, 20),
                    table, Spacer(1, 20),
                    Table(bottom_data)
                    ]

    doc.build(pdf_template)
    Waybill.objects.create(user_id=request.user.pk, filename=waybill_id, type=f'{client} pickup waybill', client=client)
    Event.objects.create(user_id=request.user.pk, action='Prepared and downloaded {} pickup waybill'.format(client))
    data = [str(waybill_id)]
    request.session['list'] = data  # json data
    return response


# Waybills not uploaded
@login_required(login_url='login')
def user_waybills(request):
    qrst = Waybill.objects.filter(user_id=request.user.pk, file='').order_by('-created_at')
    user = request.user
    return render(request, "waybill/update_user_waybills.html", {'schedules': qrst, 'user': user})


# Waybill references
@login_required(login_url='login')
def waybills(request):
    qrst = Waybill.objects.all().order_by('-created_at')
    for i in qrst:
        i.updated_at = Client.objects.get(client_name=i.client).rep
    return render(request, "waybill/waybills.html", {'schedules': qrst})


# Add new part to our list of parts
@login_required(login_url='login')
def add_part(request):
    if request.method == 'POST':
        form = AddPartForm(request.POST)
        if form.is_valid():
            current_user = request.user
            pname = form.cleaned_data.get('part_name')
            pname_not_added_value = form.cleaned_data.get('part_name_not_included')
            avn = form.cleaned_data.get('topup')

            name_not_included = (form.cleaned_data.get('part_name') == 'None')

            try:
                # Query validations on part not included
                existing_part = Part.objects.get(name=pname_not_added_value)

            except (TypeError, ValueError, OverflowError, Part.DoesNotExist):
                existing_part = None

            if name_not_included:
                if pname_not_added_value == '':
                    messages.warning(request, 'Provide a valid name for selecting "Part name was not included"!')
                    return redirect('add_part')
                elif existing_part:
                    if existing_part.action_status == 'Pending':
                        messages.warning(request, '{} request already sent, waiting for admins approval.'.format(
                            pname_not_added_value))
                        return redirect('add_part')
                    messages.warning(request, '{} already added and approved.'.format(pname_not_added_value))
                    return redirect('add_part')
                else:
                    Part.objects.create(user_id=current_user.pk, name=pname_not_added_value,
                                        requested_by=str(current_user), approved_by=str(current_user))
                    PartStock.objects.create(name_id=Part.objects.get(name=pname_not_added_value).pk, topup=avn, )
                    Event.objects.create(user_id=current_user.pk,
                                         action='Added {} as a new part'.format(pname_not_added_value))
                    PartEvent.objects.create(user_id=current_user.pk,
                                             action='Added {} as a new part'.format(pname_not_added_value))
                    messages.success(request, '{} added successfully!'.format(pname_not_added_value))
                    return redirect('add_part')
            else:
                try:
                    existing_name = Part.objects.get(name=pname)
                except (TypeError, ValueError, OverflowError, Part.DoesNotExist):
                    existing_name = None
                if existing_name:
                    if existing_name.action_status == 'Pending':
                        messages.warning(request, '{} request already sent, waiting for admins approval.'.format(pname))
                        return redirect('add_part')
                    messages.warning(request, '{} already added and approved.'.format(pname_not_added_value))
                    return redirect('add_part')
                else:
                    Part.objects.create(user_id=current_user.pk, name=pname, requested_by=str(current_user),
                                        approved_by=str(current_user))
                    PartStock.objects.create(name_id=Part.objects.get(name=pname).pk, topup=avn)
                    Event.objects.create(user_id=current_user.pk, action='Added {} as a new part'.format(pname))
                    PartEvent.objects.create(user_id=current_user.pk, action='Added {} as a new part'.format(pname))
                    messages.success(request, '{} added successfully!'.format(pname))
                    return redirect('add_part')
    else:
        form = AddPartForm()
    return render(request, 'stock/add_part.html', {'form': form})


# Update stock
@login_required(login_url='login')
def update_stock(request):
    if request.method == 'POST':
        form = UpdateStockForm(request.POST)
        if form.is_valid():
            current_user = request.user
            pname = form.cleaned_data.get('part_name')
            topup = form.cleaned_data.get('topup')

            PartStock.objects.create(name_id=Part.objects.get(name=pname).pk, topup=topup, user=str(current_user))
            Event.objects.create(user_id=current_user.pk, action='Added new {} {}s to Stock'.format(topup, pname))
            PartEvent.objects.create(user_id=current_user.pk, action='Added new {} {}s to Stock'.format(topup, pname))
            messages.success(request, '{} {}s added to stock successfully!'.format(topup, pname))
            return redirect('update_stock')
    else:
        form = UpdateStockForm()
    return render(request, 'stock/update_stock.html', {'form': form})


# View parts report
@login_required(login_url='login')
def parts(request):
    title = 'All Report'
    plist = Part.objects.filter(action_status='Approved').order_by('-updated_at')
    for i in plist:
        all_data = PartStock.objects.filter(name=i.id, action_status='Approved')
        r = 0  # clears buffer for next iteration
        t = 0
        for k in all_data:
            r += k.request
            t += k.topup
        i.requested_by = r  # total requested
        i.action_status = t - r  # total available
        i.updated_at = t  # total

    if request.method == 'POST':
        key = request.POST["key"]
        start_date = request.POST["date"]
        date = datetime.strptime(request.POST["date"], '%Y-%m-%d')  # date object
        year = date.strftime("%Y")
        month = date.strftime("%B")
        y = date.strftime("%Y")
        m = date.strftime("%m")
        d = date.strftime("%d")

        if key == 'all':
            for i in plist:
                all_data = PartStock.objects.filter(name=i.id, action_status='Approved')
                r = 0  # clears buffer for next iteration
                t = 0
                for k in all_data:
                    r += k.request
                    t += k.topup
                i.requested_by = r  # total requested
                i.action_status = t - r  # total available
                i.updated_at = t  # total
        elif key == 'daily':
            title = f'Daily Report for {start_date}'
            for i in plist:
                all_avai = PartStock.objects.filter(name=i.id, action_status='Approved')
                daily_data = PartStock.objects.filter(name=i.id, created_at__day=d, created_at__month=m,
                                                      created_at__year=y, action_status='Approved')
                r = 0
                for k in daily_data:
                    r += k.request
                i.requested_by = r
                t = 0
                for x in all_avai:
                    t += x.topup
                i.action_status = t - r  # total available
                i.updated_at = t  # total
        elif key == 'weekly':
            title = f'Weekly Report for {start_date} to ' + str(date + timedelta(days=5))[:10]
            for i in plist:
                all_avai = PartStock.objects.filter(name=i.id, action_status='Approved')
                weekly_data = PartStock.objects.filter(name=i.id, action_status='Approved', created_at__gte=date,
                                                       created_at__lte=date + timedelta(days=5))
                r = 0
                t = 0
                for k in weekly_data:
                    r += k.request
                    t += k.topup
                i.requested_by = r
                t = 0
                for x in all_avai:
                    t += x.topup
                i.action_status = t - r  # total available
                i.updated_at = t  # total
        elif key == 'monthly':
            title = f'Monthly Report for {month}, {y}'
            for i in plist:
                all_avai = PartStock.objects.filter(name=i.id, action_status='Approved')
                monthly_data = PartStock.objects.filter(name=i.id, action_status='Approved', created_at__month=m,
                                                        created_at__year=y)
                r = 0
                t = 0
                for k in monthly_data:
                    r += k.request
                    t += k.topup
                i.requested_by = r
                t = 0
                for x in all_avai:
                    t += x.topup
                i.action_status = t - r  # total available
                i.updated_at = t  # total
        elif key == 'quarter1':
            title = f'First Quarter Report(January, {year} - March, {year})'
            for i in plist:
                all_avai = PartStock.objects.filter(name=i.id, action_status='Approved')
                data = PartStock.objects.filter(name=i.id, action_status='Approved', created_at__gte=f'{y}-01-01',
                                                created_at__lte=f'{y}-03-31')
                r = 0
                t = 0
                for k in data:
                    r += k.request
                    t += k.topup
                i.requested_by = r
                t = 0
                for x in all_avai:
                    t += x.topup
                i.action_status = t - r  # total available
                i.updated_at = t  # total
        elif key == 'quarter2':
            title = f'Second Quarter Report(April, {year} - June, {year})'
            for i in plist:
                all_avai = PartStock.objects.filter(name=i.id, action_status='Approved')
                data = PartStock.objects.filter(name=i.id, action_status='Approved', created_at__gte=f'{y}-04-01',
                                                created_at__lte=f'{y}-06-30')
                r = 0
                t = 0
                for k in data:
                    r += k.request
                    t += k.topup
                i.requested_by = r
                t = 0
                for x in all_avai:
                    t += x.topup
                i.action_status = t - r  # total available
                i.updated_at = t  # total
        elif key == 'quarter3':
            title = f'Third Quarter Report(July, {year} - September, {year})'
            for i in plist:
                all_avai = PartStock.objects.filter(name=i.id, action_status='Approved')
                data = PartStock.objects.filter(name=i.id, action_status='Approved', created_at__gte=f'{y}-07-01',
                                                created_at__lte=f'{y}-09-30')
                r = 0
                t = 0
                for k in data:
                    r += k.request
                    t += k.topup
                i.requested_by = r
                t = 0
                for x in all_avai:
                    t += x.topup
                i.action_status = t - r  # total available
                i.updated_at = t  # total
        elif key == 'quarter4':
            title = f'Last Quarter Report(October, {year} - December, {year})'
            for i in plist:
                all_avai = PartStock.objects.filter(name=i.id, action_status='Approved')
                data = PartStock.objects.filter(name=i.id, action_status='Approved', created_at__gte=f'{y}-10-01',
                                                created_at__lte=f'{y}-12-31')
                r = 0
                t = 0
                for k in data:
                    r += k.request
                    t += k.topup
                i.requested_by = r
                t = 0
                for x in all_avai:
                    t += x.topup
                i.action_status = t - r  # total available
                i.updated_at = t  # total
        elif key == 'yearly':
            title = f'Yearly Report for {year}'
            for i in plist:
                all_avai = PartStock.objects.filter(name=i.id, action_status='Approved')
                data = PartStock.objects.filter(name=i.id, action_status='Approved', created_at__year=y)
                r = 0
                t = 0
                for k in data:
                    r += k.request
                    t += k.topup
                i.requested_by = r
                t = 0
                for x in all_avai:
                    t += x.topup
                i.action_status = t - r  # total available
                i.updated_at = t  # total
    return render(request, "stock/parts.html", {'parts': plist, 'title': title})


# Part report breakdown
@login_required(login_url='login')
def part_report_details(request, name):
    schedules, board, ph, others = [], [], [], []
    if request.method == 'POST':
        start_date = request.POST['date']
        end_date = request.POST["date2"]
        title = f'{name}s replaced serial numbers from {start_date} to {end_date}'
        fixed = Schedule.objects.filter(cancelled=False, repair_status='Fixed', date_repaired__gte=start_date,
                                        date_repaired__lte=end_date).order_by('-date_repaired')
        for i in fixed:
            if name == 'Print head' and i.new_head_barcode:
                ph.append(i)
            elif name == 'Board' and i.new_board:
                board.append(i)
        if name == 'Board':
            schedules = board
        elif name == 'Print head':
            schedules = ph
        else:
            schedules = others
    else:
        title = f'All {name}s replaced serial numbers'
        fixed = Schedule.objects.filter(cancelled=False, repair_status='Fixed').order_by('-date_repaired')
        for i in fixed:
            if name == 'Print head' and i.new_head_barcode:
                ph.append(i)
            elif name == 'Board' and i.new_board:
                board.append(i)
        if name == 'Board':
            schedules = board
        elif name == 'Print head':
            schedules = ph
        else:
            schedules = others

    json_data = {'schedules': schedules, 'name': name, 'title': title}
    return render(request, 'stock/part_report_details.html', json_data)


# Frequently used parts
@login_required(login_url='login')
def frequently_used_parts(request):
    plist = Part.objects.filter(action_status='Approved').order_by('name')
    json_plist = []
    for i in plist:
        all_data = PartStock.objects.filter(name=i.id, action_status='Approved', request__gt=0)
        i.action_status = len(all_data)  # request frequency
        json_slz = {k: getattr(i, k) for k in ['name', 'action_status', 'approved_by', 'created_at']}
        json_plist.append(json_slz)  # json serializable

    # sort json_plist in order of frequency
    json_plist.sort(key=lambda data: data['action_status'], reverse=True)
    return render(request, "stock/frequently_used_parts.html", {'parts': json_plist})


# Part managements options
@login_required(login_url='login')
def part_management_options(request):
    return render(request, "stock/part_management_options.html")


# Request part
@login_required(login_url='login')
def request_part(request):
    def check_available(name):
        qrs = PartStock.objects.filter(name=Part.objects.get(name=name).pk, action_status='Approved')
        r = 0
        t = 0
        for i in qrs:
            r += i.request
            t += i.topup
        return t - r

    if request.method == 'POST':
        form = RequestPartForm(request.POST)
        if form.is_valid():
            current_user = request.user
            pname = form.cleaned_data.get('part_name')
            req = form.cleaned_data.get('request')
            available = check_available(pname)
            remaining = available - req

            if req > available:
                messages.warning(request, 'Insufficient {}s available!'.format(pname))
                messages.info(request, '{} {}s available at the moment!'.format(available, pname))
                return redirect('request_part')
            else:
                PartStock.objects.create(name_id=Part.objects.get(name=pname).pk, request=req, user=str(current_user))
                Event.objects.create(user_id=current_user.pk, action='Requested {} {}s'.format(req, pname))
                PartEvent.objects.create(user_id=current_user.pk, action='Requested {} {}s'.format(req, pname))
                messages.success(request, 'Your request of {} {}s is successful!'.format(req, pname))
                messages.info(request, '{} {}s remaining in stock!'.format(remaining, pname))
                return redirect('request_part')
    else:
        form = RequestPartForm()
    return render(request, 'stock/request_part.html', {'form': form})


# Part usage history
@login_required(login_url='login')
def part_event(request):
    history = PartEvent.objects.all().order_by('-created_at')
    return render(request, "stock/part_events.html", {'events': history})


# Pending Approvals
@login_required(login_url='login')
def pending_approvals(request):
    return render(request, "pending_approvals/pending_approvals.html")


# Printer Pending cancellation requests
@login_required(login_url='login')
def cancellation_requests(request):
    schedules = Schedule.objects.filter(cancelled=False, action_status='Pending').order_by('-updated_at')
    for i in schedules:
        i.requested_by = User.objects.get(email=i.requested_by)
    return render(request, "pending_approvals/printer_cancelled_approvals.html", {'schedules': schedules})


# Pending cancellation requests
@login_required(login_url='login')
def added_client_requests(request):
    clients = Client.objects.filter(action_status='Pending').order_by('-updated_at')
    for i in clients:
        i.requested_by = User.objects.get(email=i.requested_by)
    return render(request, "pending_approvals/client_approvals.html", {'schedules': clients})


# Approve added client request
@login_required(login_url='login')
def approve_added_client_request(request, pk):
    item = Client.objects.get(id=pk)
    current_site = get_current_site(request)
    current_user = request.user
    if request.method == 'POST':
        item.approved_by = str(current_user)
        item.action_status = 'Approved'
        if is_connected():
            item.save()
            Event.objects.create(user_id=current_user.pk, action="Approved {}'s pending added client request".
                                 format(item.requested_by))
            send_pending_feedback_email(user=item.requested_by, admin=item.approved_by, action='approved',
                                        heading='Congratulations',
                                        current_site=current_site.domain,
                                        info='{} added as a new client'.format(item.client_name))
            messages.success(request,
                             'Client {} approved successfully! {} will be notified by mail.'.format(item.client_name,
                                                                                                    item.requested_by))
            return redirect('client_requests')
        else:
            messages.info(request, 'No connection. Check your internet connection and retry!')
            return redirect('client_requests')
    return render(request, 'pending_approvals/approve_client_prompt.html', {'item': item})


@login_required(login_url='login')
def reject_added_client_request(request, pk):
    item = Client.objects.get(id=pk)
    current_site = get_current_site(request)
    current_user = request.user
    ab = str(current_user)
    rb = item.requested_by
    name = item.client_name
    if request.method == 'POST':
        if is_connected():
            item.delete()
            Event.objects.create(user_id=current_user.pk, action="Rejected {}'s pending request as new client".
                                 format(rb))
            send_pending_feedback_email(user=rb, admin=ab, action='rejected',
                                        heading='Sorry', current_site=current_site.domain,
                                        info='{} pending request as a new client'.format(name))
            messages.success(request, 'Request of {} to be added has been rejected and deleted successfully! '
                                      '{} will be notified by mail.'.format(name, rb))
            return redirect('client_requests')
        else:
            messages.info(request, 'No connection. Check your internet connection and retry!')
            return redirect('client_requests')
    return render(request, 'pending_approvals/reject_clients_prompt.html', {'item': item})


# Approve cancellation request
@login_required(login_url='login')
def approve_cancellation_request(request, pk):
    item = Schedule.objects.get(id=pk)
    current_site = get_current_site(request)
    current_user = request.user
    if request.method == 'POST':
        item.cancelled = True
        item.approved_by = str(current_user)
        item.action_status = 'Approved'
        if is_connected():
            item.save()
            Event.objects.create(user_id=current_user.pk, action="Approved {}'s pending cancellation request".
                                 format(item.requested_by))
            send_pending_feedback_email(user=User.objects.get(email=item.requested_by), admin=item.approved_by,
                                        action='approved',
                                        heading='Congratulations',
                                        current_site=current_site.domain,
                                        info='{} schedule cancellation'.format(item.printer_number))
            messages.success(request,
                             f'Cancellation approved successfully! {User.objects.get(email=item.requested_by)} will be notified by mail.')
            return redirect('cancellation_requests')
        else:
            messages.info(request, 'No connection. Check your internet connection and retry!')
            return redirect('cancellation_requests')
    return render(request, 'pending_approvals/approve_cancellation_prompt.html', {'item': item})


@login_required(login_url='login')
def reject_cancellation_request(request, pk):
    item = Schedule.objects.get(id=pk)
    current_site = get_current_site(request)
    current_user = request.user
    if request.method == 'POST':
        item.approved_by = str(current_user)
        item.action_status = 'Approved'
        if is_connected():
            item.save()
            Event.objects.create(user_id=current_user.pk, action="Rejected {}'s pending cancellation request".
                                 format(item.requested_by))
            send_pending_feedback_email(user=item.requested_by, admin=item.approved_by, action='rejected',
                                        heading='sorry',
                                        current_site=current_site.domain,
                                        info='{} schedule cancellation'.format(item.printer_number))
            messages.success(request, 'Cancellation rejected successfully! {} will be notified by mail.'.format(
                item.requested_by))
            return redirect('cancellation_requests')
        else:
            messages.info(request, 'No connection. Check your internet connection and retry!')
            return redirect('cancellation_requests')
    return render(request, 'pending_approvals/reject_cancellation_prompt.html', {'item': item})


# Pending added part requests
@login_required(login_url='login')
def added_part_requests(request):
    parts = Part.objects.filter(action_status='Pending').order_by('-updated_at')
    for i in parts:
        val = PartStock.objects.filter(name=i.id, action_status='Pending')
        for k in val:
            t = k.topup
        i.requested_by = t
    return render(request, "pending_approvals/part_approvals.html", {'schedules': parts})


# Approve added part request
@login_required(login_url='login')
def approve_added_part_request(request, pk):
    item = Part.objects.get(id=pk)
    item_val = PartStock.objects.get(name=pk, action_status='Pending')
    current_site = get_current_site(request)
    current_user = request.user
    if request.method == 'POST':
        item.approved_by = str(current_user)
        item.action_status = 'Approved'
        if is_connected():
            item.save()
            item_val.action_status = 'Approved'
            item_val.save()
            Event.objects.create(user_id=current_user.pk,
                                 action=f"Approved {item.user}'s pending added part request")
            send_pending_feedback_email(user=User.objects.get(email=item.requested_by), admin=item.approved_by,
                                        action='approved',
                                        heading='Congratulations',
                                        current_site=current_site.domain,
                                        info='{} added as a new part'.format(item.client_name))
            messages.success(request, '{} approved successfully! {} will be notified by mail.'.format(item.name,
                                                                                                      item.requested_by))
            return redirect('part_requests')
        else:
            messages.info(request, 'No connection. Check your internet connection and retry!')
            return redirect('part_requests')
    return render(request, 'pending_approvals/approve_part_prompt.html', {'item': item})


@login_required(login_url='login')
def reject_added_part_request(request, pk):
    item = Part.objects.get(id=pk)
    current_site = get_current_site(request)
    current_user = request.user
    rb = item.requested_by
    name = item.name
    ab = str(current_user)
    if request.method == 'POST':
        if is_connected():
            item.delete()
            Event.objects.create(user_id=current_user.pk, action="Rejected {}'s pending request as new part".format(rb))
            send_pending_feedback_email(user=rb, admin=ab, action='rejected', heading='Sorry',
                                        current_site=current_site.domain,
                                        info='{} pending request as a new part'.format(name))
            messages.success(request, 'Request of {} to be added has been rejected and deleted successfully! '
                                      '{} will be notified by mail.'.format(item.name, item.requested_by))
            return redirect('part_requests')
        else:
            messages.info(request, 'No connection. Check your internet connection and retry!')
            return redirect('part_requests')
    return render(request, 'pending_approvals/reject_part_prompt.html', {'item': item})


# Rating options
@login_required(login_url='login')
def rating_options(request):
    return render(request, "users/ratings/rating_options.html")


# Rating summary
@login_required(login_url='login')
def rating_summary(request):
    def avg_rating(tr, s):
        if tr == 0:
            return 0
        else:
            avg = tr / s
            avg1 = avg + 0.1
            dp = avg - int(avg)  # decimal points
            if dp < 0.55:
                return str(avg)[:3]  # 1dp
            return str(avg1)[:3]

    def remark(num):
        if num == 0:
            return 'No Ratings yet!'
        elif 0 < num <= 1.00:
            return 'Terrible'
        elif 1.00 < num <= 2.00:
            return 'Fair'
        elif 2.00 < num <= 2.50:
            return 'Low Average'
        elif 2.50 < num <= 3.00:
            return 'Average'
        elif 3.00 < num <= 4.00:
            return 'Good'
        elif 4.00 < num <= 4.50:
            return 'Very Good'
        return 'Excellent'

    title = 'Average ratings on Trainings'
    user = User.objects.all().exclude(is_superuser=True).order_by('first_name')
    for i in user:
        r = 0
        ratings = UserRating.objects.filter(user=i.id, rating_type='Training')
        for x in ratings:
            r += x.rating
        star = float(avg_rating(tr=r, s=len(ratings)))
        i.username = len(ratings)
        i.email = r  # total ratings
        i.password = f'{star} Stars'  # average ratings
        i.is_active = remark(star)  # average remark

    if request.method == 'POST':
        ratings = []
        key = request.POST["key"]
        if key == 'repairs':
            title = 'Average ratings on Repairs/Helpdesk'
            for i in user:
                qrst = UserRating.objects.filter(user=i.id)
                for k in qrst:
                    if k.rating_type == 'Repairs' or k.rating_type == 'Helpdesk':
                        ratings.append(k)
                r = 0
                for x in ratings:
                    r += x.rating
                star = float(avg_rating(tr=r, s=len(ratings)))
                i.username = len(ratings)
                i.email = r  # total ratings
                i.password = f'{star} Stars'  # average ratings
                i.is_active = remark(star)  # average remark

    return render(request, "users/ratings/rating_summary.html", {'ratings': user, 'title': title})


# Rating report
@login_required(login_url='login')
def rating_report(request):
    ratings = UserRating.objects.all().order_by('-created_at')
    for i in ratings:
        i.rating = f'{i.rating}/5'
        user = User.objects.get(id=i.user)
        if user.is_staff:
            i.updated_at = 'Admin'
        else:
            i.updated_at = 'Technician'

    return render(request, "users/ratings/rating_report.html", {'ratings': ratings})


# Rate technician on repairs
def rate_user(request, uid, rid):
    invalid = False
    try:
        uid1 = force_text(urlsafe_base64_decode(uid))
        rid1 = force_text(urlsafe_base64_decode(rid))
        user = User.objects.get(pk=uid1)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        invalid = True

    if invalid:
        messages.warning(request, 'Invalid link')
        return redirect('login')

    elif request.method == 'POST':
        form = RateUserForm(request.POST)
        if form.is_valid():
            r = request.POST['rating']
            com = form.cleaned_data.get('comment')

            existing = UserRating.objects.filter(user=uid1, rater=rid1)
            if existing:
                messages.warning(request, '{} has already been rated by another admin'.format(user))
                return redirect('login')
            UserRating.objects.create(rating_type='Repairs', rater=rid1, rating=r, date=datetime.today().date(),
                                      comment=com, user=uid1)
            messages.success(request, 'Thanks for rating {}.'.format(user))
            return redirect('login')
    else:
        form = RateUserForm()
    return render(request, 'users/ratings/rate_user_repair.html', {'form': form, 'uid': uid, 'tid': rid, 'user': user})


# client maintenance schedule
@login_required(login_url='login')
def schedule_maintenance(request):
    current_user = request.user
    if request.method == 'POST':
        form = MaintenanceForm(request.POST)
        if form.is_valid():
            client = Client.objects.get(client_name=form.cleaned_data.get('client'))
            cid = client.pk
            sd = form.cleaned_data.get('start_date')
            ed = form.cleaned_data.get('end_date')
            desc = form.cleaned_data.get('description')
            asstech = form.cleaned_data.get('assigned_technicians')
            if not is_connected():
                messages.warning(request, f"No internet connection! Check your connectivity and retry.")
                return redirect('schedule_maintenance')
            else:
                a = (str([asstech])[1:-1][1:-1]).replace("'", '').replace(',', " ").split()
                map_object = map(int, a)
                trainers = list(map_object)  # list of technicians' id
                users = []  # list of technicians' names
                for i in trainers:
                    users.append(User.objects.get(id=i))
                Maintenance.objects.create(user=current_user, client_id=cid, start_date=sd, end_date=ed,
                                           description=desc)
                Event.objects.create(user_id=current_user.pk, action=f"Scheduled {client} maintenance for the period"
                                                                     f" of {sd} to {ed}")
                subject = "MAINTENANCE SCHEDULE - MARGINS ID SYSTEM"
                recipients = [client.rep_email]
                message = render_to_string('maintenance/maintenance_prompt_email.html', {
                    'sd': sd,
                    'ed': ed,
                    'user': current_user,
                    'users': users,
                })
                send_mail(subject, message, EMAIL_HOST_USER, recipients, fail_silently=False)
                messages.success(request, 'Maintenance scheduled successfully!')
                return redirect('schedule_maintenance')
    else:
        form = MaintenanceForm()
    return render(request, 'maintenance/schedule_maintenance.html', {'form': form})


# View client maintenance
@login_required(login_url='login')
def client_maintenance(request):
    clist = Maintenance.objects.all().order_by('-updated_at')
    today = datetime.today().date()
    for i in clist:
        if today < i.end_date:
            i.status = 'Yet to complete'
        elif today == i.end_date:
            i.status = 'Ongoing'
        else:
            i.status = 'Completed'
        i.save()
    return render(request, "maintenance/client_maintenance.html", {'maintenances': clist})


# Update from maintenance list
@login_required(login_url='login')
def update_client_maintenance(request, pk):
    item = Maintenance.objects.get(id=pk)
    ost, oed = item.start_date, item.end_date
    form = UpdateMaintenanceForm(instance=item)
    current_user = request.user
    current_site = get_current_site(request)
    if request.method == 'POST':
        form = UpdateMaintenanceForm(request.POST, instance=item)
        if form.is_valid():
            if not is_connected():
                messages.warning(request, f"No internet connection! Check your connectivity and retry.")
                return redirect('client_maintenance')
            else:
                form.save()
                if ost != item.start_date or oed != item.end_date:
                    Event.objects.create(user_id=current_user.pk,
                                         action=f"Updated {item.client} maintenance schedule from the period"
                                                f" of {ost} and {oed} to {item.start_date} and {item.end_date}")
                    subject = "MAINTENANCE POSTPONEMENT - MARGINS ID SYSTEM"
                    recipients = [item.client.rep_email]
                    message = render_to_string('maintenance/postpone_maintenance_prompt_email.html', {
                        'osd': ost,
                        'oed': oed,
                        'nsd': item.start_date,
                        'ned': item.end_date,
                        'date': item.created_at.date(),
                        'user': current_user,
                    })
                    send_mail(subject, message, EMAIL_HOST_USER, recipients, fail_silently=False)
                    messages.success(request, 'Maintenance schedule postponed successfully!')
                    return redirect('client_maintenance')
                elif (not item.link_sent) and (item.status == 'Completed' or item.status == 'Ongoing'):
                    a = (str([item.assigned_technicians])[1:-1][1:-1]).replace("'", '').replace(',', " ").split()
                    map_object = map(int, a)
                    trainers = list(map_object)  # list of trainers' id
                    users = []  # everyone's link
                    for i in trainers:
                        uid = urlsafe_base64_encode(force_bytes(i))
                        tid = urlsafe_base64_encode(force_bytes(pk))
                        jsonobj = {
                            'name': User.objects.get(id=i),
                            'link': f"http://{current_site.domain}/maintenance_rate/{uid}/{tid}"
                        }
                        users.append(jsonobj)
                    subject = "RATINGS REQUEST - MARGINS ID SYSTEM"
                    message = render_to_string('maintenance/maintenance_rating_request.html', {
                        'users': users,
                        'training': item,
                    })
                    send_mail(subject, message, EMAIL_HOST_USER, [item.client.rep_email], fail_silently=False)
                    item.link_sent = True
                    item.save()
                    messages.success(request, 'Maintenance has been updated successfully!')
                    return redirect('client_maintenance')
                else:
                    messages.success(request, 'Maintenance schedule updated successfully!')
                    return redirect('client_maintenance')
    return render(request, 'schedule/update_schedule.html', {'form': form})


# cancel client maintenance list
@login_required(login_url='login')
def cancel_client_maintenance(request, pk):
    item = Maintenance.objects.get(id=pk)
    data = item
    current_user = request.user
    if request.method == 'POST':
        if not is_connected():
            messages.warning(request, f"No internet connection! Check your connectivity and retry.")
            return redirect('client_maintenance')
        else:
            item.delete()
            Event.objects.create(action=f"Cancelled {data.client} maintenance scheduled on {data.created_at.date()}",
                                 user_id=current_user.pk)
            subject = "MAINTENANCE CANCELLED - MARGINS ID SYSTEM"
            recipients = [data.client.rep_email]
            message = render_to_string('maintenance/cancel_maintenance_email.html', {
                'data': data
            })
            send_mail(subject, message, EMAIL_HOST_USER, recipients, fail_silently=False)
            messages.success(request, 'Maintenance schedule cancelled successfully!')
            return redirect('client_maintenance')
    return render(request, 'maintenance/cancel_maintenance_prompt.html', {'item': item})


# # Maintenance options
# @login_required(login_url='login')
# def maintenance_options(request):
#     return render(request, "maintenance/maintenance_options.html")
#
#
# @login_required(login_url='login')
# def maintenance_agreement(request):
#     agreements = MaintenanceAgreement.objects.all().order_by('-created_at')
#     return render(request, "maintenance/maintenance_agreement.html", {'schedules': agreements})
#
#
# # schedule maintenance
# @login_required(login_url='login')
# def schedule_maintenance(request):
#     domain = get_current_site(request).domain
#     if request.method == 'POST':
#         form = ScheduleMaintenanceForm(request.POST)
#         if form.is_valid():
#             uid = request.user
#             name = form.cleaned_data.get('name')
#             client = form.cleaned_data.get('client')
#             agreement = form.cleaned_data.get('agreement')
#             moy = form.cleaned_data.get('moy')
#             dom = form.cleaned_data.get('dom')
#             hour = form.cleaned_data.get('hour')
#             m = form.cleaned_data.get('min')
#
#             existing_schedule = PeriodicTask.objects.filter(name=name)
#
#             # schedule, created = IntervalSchedule.objects.get_or_create(
#             #     every=10,
#             #     period=IntervalSchedule.SECONDS,
#             # )
#
#             if existing_schedule:
#                 messages.warning(request, 'Periodic Schedule with the same Name as {} already exists!'.format(client))
#                 return redirect('schedule_maintenance')
#
#             crontab_schedule, _ = CrontabSchedule.objects.get_or_create(
#                 minute=m,
#                 hour=hour,
#                 # day_of_week='1',  # first day of the week
#                 day_of_month=dom,
#                 month_of_year=moy,
#             )
#             sch = PeriodicTask.objects.create(
#                 crontab=crontab_schedule,
#                 name=name,
#                 task='printer_support.emails.maintenance_alert',
#                 description=agreement,
#                 args=json.dumps([str(client), domain])
#             )
#             # To disable or cancel
#             # periodic_task.enabled = False
#             # periodic_task.save()
#
#             MaintenanceAgreement.objects.create(user=uid, client=client, agreement=agreement, schedule_id=sch.id)
#             messages.success(request, '{} periodic maintenance scheduled successfully!'.format(client))
#             return redirect('schedule_maintenance')
#
#     else:
#         form = ScheduleMaintenanceForm()
#     return render(request, 'maintenance/schedule_maintenance.html', {'form': form})
#
#
# # Due Maintenance
# @login_required(login_url='login')
# def due_maintenance(request):
#     title = 'Maintenance schedules due in a month'
#     date = datetime.today()
#     due = PeriodicTask.objects.filter(start_time__gte=date, start_time__lt=date + relativedelta(months=+1)). \
#         order_by('start_time')
#     for i in due:
#         sch = MaintenanceAgreement.objects.filter(schedule_id=i.pk)
#         for k in sch:
#             i.clocked_id = k.user
#             i.interval_id = k.client
#             i.solar_id = k.created_at
#
#     if request.method == 'POST':
#         key = request.POST["key"]
#         year = date.strftime("%Y")
#         month = date.strftime("%B")
#         y = date.strftime("%Y")
#         m = date.strftime("%m")
#         d = date.strftime("%d")
#
#         if key == 'nm':
#             title = 'Maintenance schedules due in a month'
#             due = PeriodicTask.objects.filter(start_time__gte=date, start_time__lt=date + relativedelta(months=+1)). \
#                 order_by('start_time')
#             for i in due:
#                 sch = MaintenanceAgreement.objects.filter(schedule_id=i.pk)
#                 for k in sch:
#                     i.clocked_id = k.user
#                     i.interval_id = k.client
#                     i.solar_id = k.created_at
#         elif key == 'lm':
#             title = 'Maintenance schedules past one month'
#             due = PeriodicTask.objects.filter(start_time__gte=date + relativedelta(months=-1), start_time__lt=date). \
#                 order_by('-start_time')
#             for i in due:
#                 sch = MaintenanceAgreement.objects.filter(schedule_id=i.pk)
#                 for k in sch:
#                     i.clocked_id = k.user
#                     i.interval_id = k.client
#                     i.solar_id = k.created_at
#         elif key == 'lw':
#             title = 'Maintenance schedules past 7 days'
#             due = PeriodicTask.objects.filter(start_time__gte=date - timedelta(days=7), start_time__lt=date). \
#                 order_by('-start_time')
#             for i in due:
#                 sch = MaintenanceAgreement.objects.filter(schedule_id=i.pk)
#                 for k in sch:
#                     i.clocked_id = k.user
#                     i.interval_id = k.client
#                     i.solar_id = k.created_at
#         elif key == 'tm':
#             title = 'Maintenance schedules due in this month'
#             due = PeriodicTask.objects.filter(start_time__month=m, start_time__year=y).order_by('start_time')
#             for i in due:
#                 sch = MaintenanceAgreement.objects.filter(schedule_id=i.pk)
#                 for k in sch:
#                     i.clocked_id = k.user
#                     i.interval_id = k.client
#                     i.solar_id = k.created_at
#         elif key == 'n3m':
#             title = 'Maintenance schedules due in 3 months'
#             due = PeriodicTask.objects.filter(start_time__gte=date, start_time__lt=date + relativedelta(months=+3)). \
#                 order_by('start_time')
#             for i in due:
#                 sch = MaintenanceAgreement.objects.filter(schedule_id=i.pk)
#                 for k in sch:
#                     i.clocked_id = k.user
#                     i.interval_id = k.client
#                     i.solar_id = k.created_at
#         elif key == 'ty':
#             title = 'Maintenance schedules due in this year'
#             due = PeriodicTask.objects.filter(start_time__year=y).order_by('start_time')
#             for i in due:
#                 sch = MaintenanceAgreement.objects.filter(schedule_id=i.pk)
#                 for k in sch:
#                     i.clocked_id = k.user
#                     i.interval_id = k.client
#                     i.solar_id = k.created_at
#         else:
#             title = 'Available maintenance schedules'
#             due = PeriodicTask.objects.all().order_by('start_time')
#             for i in due:
#                 sch = MaintenanceAgreement.objects.filter(schedule_id=i.id)
#                 for k in sch:
#                     i.clocked_id = k.user
#                     i.interval_id = k.client
#                     i.solar_id = k.created_at
#     return render(request, "maintenance/due_maintenance.html", {'due': due, 'title': title})


# Rate user on printers repair
def check_to_rate(user, current_site, client):
    date = datetime.today()
    y = date.strftime("%Y")
    m = date.strftime("%m")
    d = date.strftime("%d")

    fixed_today = Schedule.objects.filter(date_repaired__day=d, date_repaired__month=m, date_repaired__year=y,
                                          repair_status='Fixed', cancelled=False, client=client.id)
    uf = Schedule.objects.filter(date_repaired__day=d, date_repaired__month=m, date_repaired__year=y, cancelled=False,
                                 repair_status='Fixed', client=client.id, fixed_by__icontains=str(user.id))

    pending = Schedule.objects.filter(repair_status='Pending', cancelled=False, client=client.id)
    today_pending = len(pending) + len(fixed_today)
    u_fixed = len(uf)
    if today_pending == 0:
        user_rate = 0
    user_rate = u_fixed / today_pending

    def send():
        if is_connected():
            subject = " RATING REQUEST - MARGINS ID SYSTEM"
            recipients = []
            admins = User.objects.filter(is_staff=True)
            for i in admins:
                recipients.append(i.email)
            message = render_to_string('users/ratings/request_to_rate_email.html', {
                'user': user,
                'domain': current_site,
                'client': client,
                'pending': pending,
                'user_fixed': u_fixed,
                'percentage': f'{user_rate * 100}%',
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'rid': urlsafe_base64_encode(force_bytes(datetime.today().minute + datetime.today().second)),
            })
            send_mail(subject, message, EMAIL_HOST_USER, recipients, fail_silently=False)
            return True
        else:
            return False

    if math.isclose(user_rate, 0.5, rel_tol=0.01):
        send()


# NHIA Account portal
@login_required(login_url='login')
def accounts_options(request):
    return render(request, "finance/account_options.html")


# View account portal
@login_required(login_url='login')
def nhia_sla(request):
    title = 'All available deductions'
    schedules = Schedule.objects.filter(cancelled=False, delivery_status='Delivered').order_by('date_delivered')
    index = 0

    # difference = (i.date_delivered - i.pickup_date).days - 3
    # holidays = pd.to_datetime("04/07/2019", format="%d/%m/%Y").date()
    # days = np.busday_count(start, end, holidays=[holidays])

    for i in schedules:
        difference = np.busday_count(i.pickup_date, i.date_delivered) - 3
        i.old_head_barcode = difference
        index += 1
        i.id = index
        i.new_head_barcode = (difference * 15) + 0.00

    # total deductions
    nhia = 0
    midsa = 0
    for i in schedules:
        if i.new_head_barcode > 0:
            nhia += i.new_head_barcode
        else:
            midsa += i.new_head_barcode
    midsa *= -1
    if midsa > nhia:
        gain = True
        profit = midsa - nhia
    else:
        gain = False
        profit = nhia - midsa

    if request.method == 'POST':
        key = request.POST["key"]
        date = datetime.strptime(request.POST["date"], '%Y-%m-%d')  # date object
        year = date.strftime("%Y")
        month = date.strftime("%B")
        y = date.strftime("%Y")
        m = date.strftime("%m")
        d = date.strftime("%d")

        if key == 'monthly':
            title = f'Monthly Deductions for {month}, {y}'
            schedules = Schedule.objects.filter(date_delivered__month=m, date_delivered__year=y, cancelled=False,
                                                delivery_status='Delivered').order_by('date_delivered')
            index = 0
            for i in schedules:
                difference = np.busday_count(i.pickup_date, i.date_delivered) - 3
                i.old_head_barcode = difference
                index += 1
                i.id = index
                i.new_head_barcode = (difference * 15) + 0.00

            # total deductions
            nhia = 0
            midsa = 0
            for i in schedules:
                if i.new_head_barcode > 0:
                    nhia += i.new_head_barcode
                else:
                    midsa += i.new_head_barcode
            midsa *= -1
            if midsa > nhia:
                gain = True
                profit = midsa - nhia
            else:
                gain = False
                profit = nhia - midsa

        elif key == 'quarter1':
            title = f'First Quarter Deductions(January, {year} - March, {year})'
            schedules = Schedule.objects.filter(date_delivered__gte=f'{y}-01-01', date_delivered__lte=f'{y}-03-31',
                                                cancelled=False, delivery_status='Delivered').order_by('date_delivered')
            index = 0
            for i in schedules:
                difference = np.busday_count(i.pickup_date, i.date_delivered) - 3
                i.old_head_barcode = difference
                index += 1
                i.id = index
                i.new_head_barcode = (difference * 15) + 0.00

            # total deductions
            nhia = 0
            midsa = 0
            for i in schedules:
                if i.new_head_barcode > 0:
                    nhia += i.new_head_barcode
                else:
                    midsa += i.new_head_barcode
            midsa *= -1
            if midsa > nhia:
                gain = True
                profit = midsa - nhia
            else:
                gain = False
                profit = nhia - midsa

        elif key == 'quarter2':
            title = f'Second Quarter Deductions(April, {year} - June, {year})'
            schedules = Schedule.objects.filter(date_delivered__gte=f'{y}-04-01', date_delivered__lte=f'{y}-06-30',
                                                cancelled=False, delivery_status='Delivered').order_by('date_delivered')
            index = 0
            for i in schedules:
                difference = np.busday_count(i.pickup_date, i.date_delivered) - 3
                i.old_head_barcode = difference
                index += 1
                i.id = index
                i.new_head_barcode = (difference * 15) + 0.00

            # total deductions
            nhia = 0
            midsa = 0
            for i in schedules:
                if i.new_head_barcode > 0:
                    nhia += i.new_head_barcode
                else:
                    midsa += i.new_head_barcode
            midsa *= -1
            if midsa > nhia:
                gain = True
                profit = midsa - nhia
            else:
                gain = False
                profit = nhia - midsa

        elif key == 'quarter3':
            title = f'Third Quarter Deductions(July, {year} - September, {year})'
            schedules = Schedule.objects.filter(date_delivered__gte=f'{y}-07-01', date_delivered__lte=f'{y}-09-30',
                                                cancelled=False, delivery_status='Delivered').order_by('date_delivered')
            index = 0
            for i in schedules:
                difference = np.busday_count(i.pickup_date, i.date_delivered) - 3
                i.old_head_barcode = difference
                index += 1
                i.id = index
                i.new_head_barcode = (difference * 15) + 0.00

            # total deductions
            nhia = 0
            midsa = 0
            for i in schedules:
                if i.new_head_barcode > 0:
                    nhia += i.new_head_barcode
                else:
                    midsa += i.new_head_barcode
            midsa *= -1
            if midsa > nhia:
                gain = True
                profit = midsa - nhia
            else:
                gain = False
                profit = nhia - midsa

        elif key == 'quarter4':
            title = f'Last Quarter Deductions(October, {year} - December, {year})'
            schedules = Schedule.objects.filter(date_delivered__gte=f'{y}-10-01', date_delivered__lte=f'{y}-12-31',
                                                cancelled=False, delivery_status='Delivered').order_by('date_delivered')
            index = 0
            for i in schedules:
                difference = np.busday_count(i.pickup_date, i.date_delivered) - 3
                i.old_head_barcode = difference
                index += 1
                i.id = index
                i.new_head_barcode = (difference * 15) + 0.00

            # total deductions
            nhia = 0
            midsa = 0
            for i in schedules:
                if i.new_head_barcode > 0:
                    nhia += i.new_head_barcode
                else:
                    midsa += i.new_head_barcode
            midsa *= -1
            if midsa > nhia:
                gain = True
                profit = midsa - nhia
            else:
                gain = False
                profit = nhia - midsa

        elif key == 'yearly':
            title = f'Yearly Deductions for {year}'
            schedules = Schedule.objects.filter(date_delivered__year=y, cancelled=False,
                                                delivery_status='Delivered').order_by('date_delivered')
            index = 0
            for i in schedules:
                difference = np.busday_count(i.pickup_date, i.date_delivered) - 3
                i.old_head_barcode = difference
                index += 1
                i.id = index
                i.new_head_barcode = (difference * 15) + 0.00

            # total deductions
            nhia = 0
            midsa = 0
            for i in schedules:
                if i.new_head_barcode > 0:
                    nhia += i.new_head_barcode
                else:
                    midsa += i.new_head_barcode
            midsa *= -1
            if midsa > nhia:
                gain = True
                profit = midsa - nhia
            else:
                gain = False
                profit = nhia - midsa

    data = {'schedules': schedules,
            'title': title,
            'nhia': nhia,
            'midsa': midsa,
            'd': '$',
            'profit': profit,
            'gain': gain
            }

    return render(request, "finance/account_portal.html", data)


# View account portal
@login_required(login_url='login')
def nhia_report(request):
    def parts_replaced(lt):
        ph, b = 0, 0
        for i in lt:
            if i.new_head_barcode and i.new_board:
                ph += 1
                b += 1
            elif i.new_board:
                b += 1
            elif i.new_head_barcode:
                ph += 1
        return [ph, b]

    title, status, start_date, end_date = '', '', '', ''
    schedules = Schedule.objects.filter(cancelled=False, client_id=1).order_by('-pickup_date')
    parts = parts_replaced(schedules)
    # print('Replaced Print Heads: ', parts[0], 'Replaced Boards: ', parts[1])
    if request.method == 'POST':
        key = request.POST["key"]
        start_date = request.POST['date']
        end_date = request.POST["date2"]
        title = f'From {start_date} to {end_date}'

        if key == 'pending':
            status = key.upper()
            schedules = Schedule.objects.filter(cancelled=False, client_id=1, repair_status=key.capitalize(),
                                                pickup_date__gte=start_date, pickup_date__lte=end_date)
            parts = parts_replaced(schedules)
        elif key == 'fixed':
            status = key.upper()
            schedules = Schedule.objects.filter(cancelled=False, client_id=1, repair_status=key.capitalize(),
                                                date_repaired__gte=start_date, date_repaired__lte=end_date)
            parts = parts_replaced(schedules)
        elif key == "delivered":
            status = key.upper()
            schedules = Schedule.objects.filter(cancelled=False, client_id=1, delivery_status=key.capitalize(),
                                                date_delivered__gte=start_date, date_delivered__lte=end_date)
            parts = parts_replaced(schedules)
    return render(request, "finance/nhia_printers_report.html",
                  {'schedules': schedules, 'title': title, 'date2': end_date, 'date': start_date,
                   'status': status, 'ph': parts[0], 'b': parts[1]})


# HelpDesk options
@login_required(login_url='login')
def helpdesk_options(request):
    return render(request, 'helpdesk/helpdesk_options.html')


# View helpdesk tickets
@login_required(login_url='login')
def tickets(request):
    tickets = HelpDesk.objects.all().order_by('-created_at')
    for i in tickets:
        i.fixed_by = User.objects.get(id=i.fixed_by)
        if i.reporter.is_staff:
            i.position = 'Admin'
        elif i.reporter.is_accountant:
            i.position = 'Accountant'
        elif i.reporter.is_pro:
            i.position = 'Procurement Officer'
        else:
            i.position = 'Technician'
    return render(request, "helpdesk/tickets.html", {'tickets': tickets})


# Update ticket fix status
@login_required(login_url='login')
def fix_ticket(request, pk):
    item = HelpDesk.objects.get(id=pk)
    current_site = get_current_site(request)
    current_user = request.user
    if request.method == 'POST':
        if item.fix_status == 'Fixed':
            messages.info(request, f'Ticket already resolved by {User.objects.get(id=item.fixed_by)}')
            return redirect('tickets')
        item.fixed_by = current_user.pk
        item.fix_status = 'Fixed'
        item.date_fixed = datetime.today().date()
        item.ready_rate = True
        if is_connected():
            item.save()
            Event.objects.create(user_id=current_user.pk, action="Updated helpdesk ticket as fixed")
            subject = "MARGINS ID SYSTEM"
            recipients = [item.reporter.email]
            message = render_to_string('helpdesk/ticket_fixed_feedback_email.html', {
                'user': item.reporter,
                'domain': current_site,
                'issue': item.issue,
                'admin': User.objects.get(id=item.fixed_by),
            })
            send_mail(subject, message, EMAIL_HOST_USER, recipients, fail_silently=False)
            messages.success(request,
                             'Ticket status updated successfully! {} will be notified by mail.'.format(item.reporter))
            return redirect('tickets')
        else:
            messages.info(request, 'No connection. Check your internet connection and retry!')
            return redirect('tickets')
    return render(request, 'helpdesk/ticket_fixed_prompt.html', {'item': item})


# Training and assessment options
@login_required(login_url='login')
def training_options(request):
    return render(request, "training/training_options.html")


# Training Form
@login_required(login_url='login')
def schedule_training(request):
    current_user = request.user
    if request.method == 'POST':
        form = TrainingForm(request.POST)
        if form.is_valid():
            client = Client.objects.get(client_name=form.cleaned_data.get('client'))
            trainers = form.cleaned_data.get('trainers')
            cid = client.pk
            tt = form.cleaned_data.get('training_category')
            sd = form.cleaned_data.get('start_date')
            ed = form.cleaned_data.get('end_date')
            desc = form.cleaned_data.get('description')
            if not is_connected():
                messages.warning(request, f"No internet connection! Check your connectivity and retry.")
                return redirect('schedule_training')
            else:
                Training.objects.create(trainers=trainers, raters_email=client.rep_email, end_date=ed, client_id=cid,
                                        description=desc, start_date=sd, training_category=tt, user=current_user)
                Event.objects.create(user_id=current_user.pk, action=f"Scheduled {client} training for the period"
                                                                     f" of {sd} to {ed}")
                subject = "TRAINING SCHEDULE - MARGINS ID SYSTEM"
                recipients = [client.rep_email]
                message = render_to_string('training/training_schedule_email.html', {
                    'sd': sd,
                    'ed': ed,
                    'user': current_user,
                })
                send_mail(subject, message, EMAIL_HOST_USER, recipients, fail_silently=False)
                messages.success(request, 'Training scheduled successfully!')
                return redirect('schedule_training')
    else:
        form = TrainingForm()
    return render(request, 'training/schedule_training.html', {'form': form})


# View user trainings
@login_required(login_url='login')
def trainings(request):
    qrt = Training.objects.all().order_by('-created_at')
    today = datetime.today().date()
    for i in qrt:
        if today < i.end_date:
            i.status = 'Yet to complete'
        elif today == i.end_date:
            i.status = 'Ongoing'
        else:
            i.status = 'Completed'
        i.save()
        i.created_at = i.created_at.date()
    return render(request, "training/trainings.html", {'trainings': qrt})


# Update from maintenance list
@login_required(login_url='login')
def update_training(request, pk):
    item = Training.objects.get(id=pk)
    ost, oed = item.start_date, item.end_date
    form = UpdateTrainingForm(instance=item)
    current_user = request.user
    current_site = get_current_site(request)
    if request.method == 'POST':
        form = UpdateTrainingForm(request.POST, instance=item)
        if form.is_valid():
            if not is_connected():
                messages.warning(request, f"No internet connection! Check your connectivity and retry.")
                return redirect('trainings')
            else:
                form.save()
                if ost != item.start_date or oed != item.end_date:
                    Event.objects.create(user_id=current_user.pk,
                                         action=f"Updated {item.client} training schedule from the period"
                                                f" of {ost} and {oed} to {item.start_date} and {item.end_date}")
                    subject = "TRAINING POSTPONEMENT - MARGINS ID SYSTEM"
                    recipients = [item.client.rep_email]
                    message = render_to_string('training/postpone_training_email.html', {
                        'osd': ost,
                        'oed': oed,
                        'nsd': item.start_date,
                        'ned': item.end_date,
                        'date': item.created_at.date(),
                        'user': current_user,
                    })
                    send_mail(subject, message, EMAIL_HOST_USER, recipients, fail_silently=False)
                    messages.success(request, 'Training schedule postponed successfully!')
                    return redirect('trainings')
                elif (not item.link_sent) and (item.status == 'Completed' or item.status == 'Ongoing'):
                    raters = item.raters_email.replace(',', " ").split()  # list of raters' email
                    a = (str([item.trainers])[1:-1][1:-1]).replace("'", '').replace(',', " ").split()
                    map_object = map(int, a)
                    trainers = list(map_object)  # list of trainers' id
                    users = []  # everyone's link
                    for i in trainers:
                        uid = urlsafe_base64_encode(force_bytes(i))
                        tid = urlsafe_base64_encode(force_bytes(pk))
                        jsonobj = {
                            'name': User.objects.get(id=i),
                            'link': f"http://{current_site.domain}/training_rate/{uid}/{tid}/"
                        }
                        users.append(jsonobj)
                    index = 0
                    for i in raters:
                        index += 1
                        subject = "RATINGS AND ASSESSMENT REQUEST - MARGINS ID SYSTEM"
                        message = render_to_string('training/training_ratings_request.html', {
                            'users': users,
                            'training': item,
                            'rid': urlsafe_base64_encode(force_bytes(index)),  # rater's id
                        })
                        send_mail(subject, message, EMAIL_HOST_USER, [i], fail_silently=False)
                    item.link_sent = True
                    item.save()
                    messages.success(request, 'Training has been updated successfully!')
                    return redirect('trainings')
                else:
                    messages.success(request, 'Training schedule updated successfully!')
                    return redirect('trainings')
    return render(request, 'schedule/update_schedule.html', {'form': form})


# cancel client training from list
@login_required(login_url='login')
def cancel_training(request, pk):
    item = Training.objects.get(id=pk)
    data = item
    current_user = request.user
    if request.method == 'POST':
        if not is_connected():
            messages.warning(request, f"No internet connection! Check your connectivity and retry.")
            return redirect('trainings')
        else:
            item.delete()
            Event.objects.create(action=f"Cancelled {data.client} training scheduled on {data.created_at.date()}",
                                 user_id=current_user.pk)
            subject = "TRAINING CANCELLED - MARGINS ID SYSTEM"
            recipients = [data.client.rep_email]
            message = render_to_string('training/cancel_training_email.html', {
                'data': data
            })
            send_mail(subject, message, EMAIL_HOST_USER, recipients, fail_silently=False)
            messages.success(request, 'Training schedule cancelled successfully!')
            return redirect('trainings')
    return render(request, 'training/cancel_training_prompt.html', {'item': item})


# Procurement options
@login_required(login_url='login')
def procurement_options(request):
    return render(request, "procurement/procurement_options.html")


# Add purchased printer
@login_required(login_url='login')
def add_purchased_printer(request):
    current_user = request.user
    if request.method == 'POST':
        form = AddPrinterForm(request.POST)
        if form.is_valid():
            cid = Client.objects.get(client_name=form.cleaned_data.get('client')).pk
            bname = form.cleaned_data.get('box_number')
            pname = form.cleaned_data.get('printer_number')
            b = form.cleaned_data.get('brand')
            m = form.cleaned_data.get('brand')
            w = form.cleaned_data.get('warranty')
            wsd = form.cleaned_data.get('w_date')
            pd = form.cleaned_data.get('p_date')
            Procurement.objects.create(user=current_user, printer_number=pname, box_number=bname, brand=b, model=m,
                                       warranty_years=w, warranty_start_date=wsd, date_purchased=pd, client_id=cid)
            Event.objects.create(user_id=current_user.pk, action='Added new purchased printer {}'.format(pname))
            messages.success(request, 'Printer {} added successfully!'.format(pname))
            return redirect('add_printer')
    else:
        form = AddPrinterForm()
    return render(request, 'procurement/add_printer.html', {'form': form})


@login_required(login_url='login')
def purchased_printers(request):
    qrt = Procurement.objects.all().order_by('-created_at')
    today = datetime.today().date()
    for i in qrt:
        if not (i.warranty_years and i.warranty_start_date):
            i.warranty_status = 'Pending'
            i.save()
        else:
            difference = (today - i.warranty_start_date).days / 365
            if difference > i.warranty_years:
                i.warranty_status = 'Declined'
            else:
                i.warranty_status = 'Accepted'
            i.save()
    return render(request, "procurement/purchased_printers.html", {'printers': qrt})


# View client printers
@login_required(login_url='login')
def client_printers(request):
    today = datetime.today().date()
    if request.method == 'POST':
        form = ClientPrintersForm(request.POST)
        if form.is_valid():
            client = Client.objects.get(client_name=form.cleaned_data.get('client'))
            cid = client.pk
            qrt = Procurement.objects.filter(client_id=cid).order_by('-created_at')
            for i in qrt:
                if not (i.warranty_years and i.warranty_start_date):
                    i.warranty_status = 'Pending'
                    i.save()
                else:
                    difference = (today - i.warranty_start_date).days / 365
                    if difference > i.warranty_years:
                        i.warranty_status = 'Declined'
                    else:
                        i.warranty_status = 'Accepted'
                    i.save()
            title = f'{client} Printers'
    else:
        form = ClientPrintersForm()
        title = 'All Printers'
        qrt = Procurement.objects.all().order_by('-created_at')
        for i in qrt:
            if not (i.warranty_years and i.warranty_start_date):
                i.warranty_status = 'Pending'
                i.save()
            else:
                difference = (today - i.warranty_start_date).days / 365
                if difference > i.warranty_years:
                    i.warranty_status = 'Declined'
                else:
                    i.warranty_status = 'Accepted'
                i.save()
    return render(request, "procurement/client_printers.html", {'form': form, 'printers': qrt, 'title': title})


# Update from printers list
@login_required(login_url='login')
def update_printer(request, pk):
    item = Procurement.objects.get(id=pk)
    form = UpdatePrinterForm(instance=item)
    current_user = request.user

    if request.method == 'POST':
        form = UpdatePrinterForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            item.user = current_user
            item.save()
            Event.objects.create(user_id=current_user.pk, action='Updated purchased printer {} details'.format(item))
            messages.success(request, 'Printer {} details updated successfully!'.format(item))
            return redirect('client_printers')
    return render(request, 'procurement/printer_update.html', {'form': form})


# View training assessments
@login_required(login_url='login')
def assessments(request):
    qrt = Training.objects.all().order_by('-created_at')
    today = datetime.today().date()
    for i in qrt:
        if today < i.end_date:
            i.status = 'Yet to complete'
        elif today == i.end_date:
            i.status = 'Ongoing'
        else:
            i.status = 'Completed'
        i.save()
    return render(request, "training/assessments.html", {'trainings': qrt})


def download_assessments(request, pk):
    training = Training.objects.get(id=pk)
    if training.status == 'Yet to complete':
        messages.warning(request, f"Training not completed!")
        return redirect('assessments')
    a = (str([training.trainers])[1:-1][1:-1]).replace("'", '').replace(',', " ").split()
    map_object = map(int, a)
    trainers = list(map_object)

    styles = getSampleStyleSheet()
    styleN = styles['Normal']
    styleR = ParagraphStyle(name='right', parent=styles['Normal'], fontName='Helvetica', fontSize=10,
                            alignment=TA_RIGHT)

    # Top content
    image = 'static/images/margin.jpg'

    period = [[Paragraph(f"Training Period: {training.start_date.strftime('%d %b, %Y')} to "
                         f"{training.end_date.strftime('%d %b, %Y')}", styleN)]
              ]

    heading = [
        [Paragraph(f"Technician Training Evaluations and Assessments on {training.training_category}", styleN)]
    ]

    response = HttpResponse(content_type='application/pdf')
    response[
        'Content-Disposition'] = f'attachment; filename="{training.client}_{training.training_category}_assessments.pdf"'

    # Establish a document
    template = PageTemplate('normal', [Frame(2.7 * cm, 4.5 * cm, 15 * cm, 25 * cm, id='F1')])
    doc = BaseDocTemplate(filename=response, pagesize=A4, pageTemplates=template)

    # Display the overall document
    pdf_template = [Image(image, 8 * cm, 4 * cm), Spacer(1, 20),
                    Table(heading), Spacer(1, 20),
                    Table(period), Spacer(1, 20),
                    ]

    # Fetching trainers' assessments
    for i in trainers:
        trainer_assessments = UserRating.objects.filter(training_id=pk, user=i)
        for k in trainer_assessments:
            assessment_heading = [
                [Paragraph(f"Technician: {User.objects.get(id=i)}", styleN),
                 Paragraph(f"Trainee Rating: {k.rating}/5", styleR)],
            ]
            pdf_template.append(Table(assessment_heading))
            pdf_template.append(Spacer(1, 10))

            # prepare table
            data = [["No.", "Program Contents", "Trainee's Feedback."],
                    ["1", "Topic(s) treated were relevant to my line of work.", k.topics],
                    ["2", "The training slides/sheets/Procedure and activities were helpful.", k.slides],
                    ["3", "The duration of the training was appropriate.", k.duration],
                    ["4", "The facilitator was technically inclined or vested on the solution.", k.solution],
                    ["5", "The facilitator’s style, delivery and instruction skills were", k.style],
                    [" ", "agreeable and well-suited to the content.", " "],
                    ["6", "The facilitator encouraged discussion and responded", k.q_response],
                    [" ", "to questions satisfactorily.", " "],
                    ["7", "The location and facilities (room layout, equipment,", k.location],
                    [" ", "personal comfort) were satisfactory.", " "],
                    ["8", "The installation and configuration training met my expectations", k.config_install],
                    ["9", "Overall, I found this training beneficial", k.training_benefit],
                    ["10", "I will recommend this training to a colleague", k.recommend]
                    ]
            table = Table(
                data,
                repeatRows=1,
                colWidths=[1.0 * cm, 10.2 * cm, 3.5 * cm],
                style=TableStyle(
                    [
                        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                        ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT')
                    ]
                )
            )
            pdf_template.append(table)
            pdf_template.append(Table([[Paragraph(f"Additional Comments: {k.comment}", styleN)]]))
            pdf_template.append(Table([[Paragraph(f"Date Evaluated: {k.date.strftime('%d %b, %Y')}", styleN)]]))
            pdf_template.append(Spacer(1, 20))

    doc.build(pdf_template)
    Event.objects.create(user_id=request.user.pk,
                         action=f"Downloaded technicians' training assessments on {training.training_category}")
    return response


# View Techncian printers report
@login_required(login_url='login')
def weekly_printers_report(request):
    start_date, end_date, schedules = '', '', []
    if request.method == 'POST':
        pickup = request.POST['date']
        delivery = request.POST["date2"]
        schedules = Schedule.objects.filter(Q(cancelled=False, pickup_date__exact=pickup) |
                                            Q(cancelled=False, date_delivered__exact=delivery))
        for i in schedules:
            i.old_head_barcode = f'{i.old_head_barcode} {i.old_board}'
            i.new_head_barcode = f'{i.new_head_barcode} {i.new_board}'
    return render(request, "weekly_report.html", {'schedules': schedules})


# Laminator options
@login_required(login_url='login')
def laminator_options(request):
    return render(request, "laminator/laminator_options.html")


@login_required(login_url='login')
def schedule_laminator(request):
    if request.method == 'POST':
        form = ScheduleLaminatorForm(request.POST)
        if form.is_valid():
            current_user = request.user
            bname = form.cleaned_data.get('box_number')
            pname = form.cleaned_data.get('laminator_number').upper()
            pparts = form.cleaned_data.get('pickup_parts')
            cname = (form.cleaned_data.get('client'))
            pdate = form.cleaned_data.get('pickup_date')
            p = form.cleaned_data.get('problem')
            p1 = form.cleaned_data.get('other_problem')
            asstech = form.cleaned_data.get('assigned_technicians')
            cid = Client.objects.get(client_name=cname).pk
            uid = current_user.pk
            purchased = Laminator.objects.filter(laminator_number=pname)

            try:
                # Query validations on schedule
                fixed_update_required = LaminatorSchedule.objects.filter(laminator_number=pname, cancelled=False,
                                                                         repair_status='Pending')

            except (TypeError, ValueError, OverflowError):
                existing_printer = None

            if fixed_update_required:
                # prompt user schedule already exist and redirect to to update fixed status
                messages.warning(request, 'Laminator {} schedule needs repair status update'.format(pname))
                return redirect('laminator_update')
            else:
                if not purchased:
                    Laminator.objects.create(user=current_user, printer_number=pname, box_number=bname, client_id=cid)
                LaminatorSchedule.objects.create(user_id=uid, box_number=bname, client_id=cid, laminator_number=pname,
                                                 pickup_parts=pparts, pickup_date=pdate, problem=p, other_problem=p1,
                                                 assigned_technicians=asstech)
                Event.objects.create(user_id=current_user.pk, action=f'Scheduled laminator {pname} for maintenance')
                messages.success(request, 'laminator {} scheduled for maintenance successfully!'.format(pname))
                return redirect('schedule_laminator')
    else:
        form = ScheduleLaminatorForm()
    return render(request, 'laminator/schedule_laminator.html', {'form': form})


# Direct update with laminator number
@login_required(login_url='login')
def laminator_update(request):
    if request.method == 'POST':
        form = LaminatorUpdateForm(request.POST)
        if form.is_valid():
            current_user = request.user
            pname = form.cleaned_data.get('laminator_number').capitalize()

            fixed_update_required = LaminatorSchedule.objects.filter(laminator_number=pname, cancelled=False,
                                                                     repair_status='Pending')

            if fixed_update_required:
                # check part requested
                nb = form.cleaned_data.get('new_board')
                nh = form.cleaned_data.get('new_head')
                if nh and nb:
                    h = part_request('Print head')
                    b = part_request('Board')
                    if (h[0] is True) and (b[0] is True):
                        PartStock.objects.create(name_id=Part.objects.get(name='Print head').pk, request=1,
                                                 user=str(current_user))
                        PartStock.objects.create(name_id=Part.objects.get(name='Board').pk, request=1,
                                                 user=str(current_user))
                        Event.objects.create(user_id=current_user.pk, action='Requested 1 Print Head')
                        Event.objects.create(user_id=current_user.pk, action='Requested 1 Board')
                        PartEvent.objects.create(user_id=current_user.pk, action='Requested 1 Board')
                        PartEvent.objects.create(user_id=current_user.pk, action='Requested 1 Print Head')
                    else:
                        messages.warning(request, 'Insufficient Print Heads/Boards available in stock!')
                        messages.info(request, '{} Print Heads and {} Boards available in stock!'.format(h[1], b[1]))
                        return redirect('laminator_update')
                elif nh:
                    h = part_request('Print head')
                    if h[0] is True:
                        PartStock.objects.create(name_id=Part.objects.get(name='Print head').pk, request=1,
                                                 user=str(current_user))
                        Event.objects.create(user_id=current_user.pk, action='Requested 1 Print Head')
                        PartEvent.objects.create(user_id=current_user.pk, action='Requested 1 Print Head')
                    else:
                        messages.warning(request, 'Insufficient Print Heads available in stock!')
                        messages.info(request, '{} Print Heads available in stock!'.format(h[1]))
                        return redirect('laminator_update')
                elif nb:
                    b = part_request('Board')
                    if b[0] is True:
                        PartStock.objects.create(name_id=Part.objects.get(name='Board').pk, request=1,
                                                 user=str(current_user))
                        Event.objects.create(user_id=current_user.pk, action='Requested 1 Board')
                        PartEvent.objects.create(user_id=current_user.pk, action='Requested 1 Board')
                    else:
                        messages.warning(request, 'Insufficient Boards available in stock!')
                        messages.info(request, '{} Boards available in stock!'.format(b[1]))
                        return redirect('laminator_update')
                for update in fixed_update_required:
                    update.repair_status = 'Fixed'
                    update.date_repaired = datetime.today().date()
                    update.problem = form.cleaned_data.get('problem')
                    update.other_problem = form.cleaned_data.get('other_problem')
                    update.parts_replaced = form.cleaned_data.get('parts_replaced')
                    update.old_head_barcode = form.cleaned_data.get('old_head')
                    update.new_head_barcode = nh
                    update.old_board = form.cleaned_data.get('old_board')
                    update.new_board = nb
                    update.fixed_by = str(current_user.pk)
                    update.save()
                    Event.objects.create(user_id=current_user.pk, action='Updated repair status of '
                                                                         'laminator {} maintenance schedule'.format(
                        pname))
                messages.success(request,
                                 'Laminator {} maintenance schedule has been updated successfully!'.format(pname))
                return redirect('laminator_update')
            else:
                messages.warning(request, 'Sorry, laminator {} has not been scheduled for maintenance! '
                                          'Perhaps it has been updated as repaired'.format(pname))
                return redirect('laminator_update')
    else:
        form = LaminatorUpdateForm()
    return render(request, 'laminator/laminator_update.html', {'form': form})


# cancel with laminator number
@login_required(login_url='login')
def cancel_laminator_schedule(request):
    if request.method == 'POST':
        form = CancelLaminatorScheduleForm(request.POST)
        if form.is_valid():
            current_user = request.user
            pname = form.cleaned_data.get('laminator_number').capitalize()

            fixed_update_required = LaminatorSchedule.objects.filter(laminator_number=pname, cancelled=False,
                                                                     repair_status='Pending')

            if not fixed_update_required:
                messages.warning(request, 'Sorry, Laminator {} has not been scheduled for maintenance! '
                                          'Perhaps it has been updated as fixed'.format(pname))
                return redirect('cancel_laminator_schedule')

            else:
                for update in fixed_update_required:
                    update.cancelled = True
                    update.requested_by = current_user.pk
                    update.approved_by = current_user.pk
                    update.action_status = 'Approved'
                    update.date_cancelled = datetime.today().date()
                    update.cancellation_reason = form.cleaned_data.get('cancellation_reason')
                    update.save()
                    Event.objects.create(user_id=current_user.pk, action='Cancelled laminator {} maintenance schedule'.
                                         format(pname))
                messages.success(request,
                                 'Laminator {} maintenance schedule has successfully been cancelled!'.format(pname))
                return redirect('cancel_laminator_schedule')
    else:
        form = CancelLaminatorScheduleForm()
    return render(request, 'schedule/cancel_schedule.html', {'form': form})


# both schedule and update printer
@login_required(login_url='login')
def laminator_schedule_update(request):
    if request.method == 'POST':
        form = LaminatorScheduleUpdateForm(request.POST)
        if form.is_valid():
            current_user = request.user
            bname = form.cleaned_data.get('box_number')
            pname = form.cleaned_data.get('laminator_number').upper()
            pparts = form.cleaned_data.get('pickup_parts')
            cname = (form.cleaned_data.get('client'))
            pdate = form.cleaned_data.get('pickup_date')
            p = form.cleaned_data.get('problem')
            p1 = form.cleaned_data.get('other_problem')
            cid = Client.objects.get(client_name=cname).pk
            uid = current_user.pk
            dr = datetime.today().date()
            pr = form.cleaned_data.get('parts_replaced')
            nb = form.cleaned_data.get('new_board')
            nh = form.cleaned_data.get('new_head')
            oh = form.cleaned_data.get('old_head')
            ob = form.cleaned_data.get('old_board')
            purchased = Laminator.objects.filter(laminator_number=pname)

            try:
                # Query validations on schedule
                fixed_update_required = LaminatorSchedule.objects.filter(laminator_number=pname, cancelled=False,
                                                                         repair_status='Pending')

            except (TypeError, ValueError, OverflowError):
                existing_printer = None

            if fixed_update_required:
                # prompt user schedule already exist and redirect to update fixed status
                messages.warning(request, 'Laminator {} schedule needs repair status update'.format(pname))
                return redirect('laminator_update')

            else:
                # check part requested
                if nh and nb:
                    h = part_request('Print head')
                    b = part_request('Board')
                    if (h[0] is True) and (b[0] is True):
                        PartStock.objects.create(name_id=Part.objects.get(name='Print head').pk, request=1,
                                                 user=str(current_user))
                        PartStock.objects.create(name_id=Part.objects.get(name='Board').pk, request=1,
                                                 user=str(current_user))
                        Event.objects.create(user_id=current_user.pk, action='Requested 1 Print Head')
                        Event.objects.create(user_id=current_user.pk, action='Requested 1 Board')
                        PartEvent.objects.create(user_id=current_user.pk, action='Requested 1 Board')
                        PartEvent.objects.create(user_id=current_user.pk, action='Requested 1 Print Head')
                    else:
                        messages.warning(request, 'Insufficient Print Heads/Boards available in stock!')
                        messages.info(request, '{} Print Heads and {} Boards available in stock!'.format(h[1], b[1]))
                        return redirect('laminator_schedule_update')
                elif nh:
                    h = part_request('Print head')
                    if h[0] is True:
                        PartStock.objects.create(name_id=Part.objects.get(name='Print head').pk, request=1,
                                                 user=str(current_user))
                        Event.objects.create(user_id=current_user.pk, action='Requested 1 Print Head')
                        PartEvent.objects.create(user_id=current_user.pk, action='Requested 1 Print Head')
                    else:
                        messages.warning(request, 'Insufficient Print Heads available in stock!')
                        messages.info(request, '{} Print Heads available in stock!'.format(h[1]))
                        return redirect('laminator_schedule_update')
                elif nb:
                    b = part_request('Board')
                    if b[0] is True:
                        PartStock.objects.create(name_id=Part.objects.get(name='Board').pk, request=1,
                                                 user=str(current_user))
                        Event.objects.create(user_id=current_user.pk, action='Requested 1 Board')
                        PartEvent.objects.create(user_id=current_user.pk, action='Requested 1 Board')
                    else:
                        messages.warning(request, 'Insufficient Boards available in stock!')
                        messages.info(request, '{} Boards available in stock!'.format(b[1]))
                        return redirect('laminator_schedule_update')
                LaminatorSchedule.objects.create(user_id=uid, box_number=bname, client_id=cid, laminator_number=pname,
                                                 repair_status='Fixed', assigned_technicians=str(uid),
                                                 pickup_parts=pparts,
                                                 pickup_date=pdate, problem=p, other_problem=p1, date_repaired=dr,
                                                 parts_replaced=pr, old_head_barcode=oh, new_head_barcode=nh,
                                                 old_board=ob, new_board=nb, fixed_by=str(current_user.pk))
                if not purchased:
                    Laminator.objects.create(user=current_user, laminator_number=pname, box_number=bname, client_id=cid)
                Event.objects.create(user_id=current_user.pk, action=f'Scheduled laminator {pname} for maintenance')
                messages.success(request, 'Laminator {} scheduled for maintenance successfully!'.format(pname))
                return redirect('laminator_schedule_update')
    else:
        form = LaminatorScheduleUpdateForm()
    return render(request, 'schedule/schedule_update.html', {'form': form})


# View cancelled schedules
@login_required(login_url='login')
def cancelled_laminator_schedules(request):
    schedules = LaminatorSchedule.objects.filter(cancelled=True).order_by('-updated_at')
    for i in schedules:
        i.requested_by = User.objects.get(pk=i.requested_by)
    return render(request, "laminator/cancelled_schedules.html", {'schedules': schedules})


# View laminators under maintenance
@login_required(login_url='login')
def pending_laminators(request):
    schedules = LaminatorSchedule.objects.order_by('-updated_at').filter(cancelled=False, repair_status='Pending')
    for i in schedules:
        i.problem = i.problem + ', ' + i.other_problem
    return render(request, "laminator/pending_laminators.html", {'schedules': schedules})


# Update from maintenance list
@login_required(login_url='login')
def update_pending_laminator(request, pk):
    item = LaminatorSchedule.objects.get(id=pk)
    form = UpdatePendingForm(instance=item)
    current_user = request.user

    if request.method == 'POST':
        form = UpdatePendingForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            Event.objects.create(user_id=current_user.pk, action='Updated laminator {} maintenance schedule'.
                                 format(item.laminator_number))
            messages.success(request,
                             'laminator {} maintenance schedule updated successfully!'.format(item.laminator_number))
            return redirect('pending_laminators_u')
    return render(request, 'schedule/update_schedule.html', {'form': form})


# cancel from maintenance list
@login_required(login_url='login')
def cancel_pending_laminator(request, pk):
    item = LaminatorSchedule.objects.get(id=pk)
    if request.method == 'POST':
        form = CancelMaintenanceForm(request.POST)
        if form.is_valid():
            current_user = request.user
            item.requested_by = current_user.pk
            item.action_status = 'Approved'
            item.approved_by = current_user.pk
            item.date_cancelled = datetime.today().date()
            item.cancellation_reason = form.cleaned_data.get('cancellation_reason')
            item.save()
            Event.objects.create(user_id=current_user.pk, action='Cancelled laminator {} maintenance schedule'.
                                 format(item.laminator_number))
            messages.success(request,
                             'Laminator {} maintenance schedule has successfully been cancelled!'.format(
                                 item.laminator_number))
            return redirect('pending_laminators')
    else:
        form = CancelMaintenanceForm()
    return render(request, 'standard_account/schedules/cancel_schedule.html', {'form': form})


# Laminator Pending cancellation requests
@login_required(login_url='login')
def laminator_cancellation_requests(request):
    schedules = LaminatorSchedule.objects.filter(cancelled=False, action_status='Pending').order_by('-updated_at')
    for i in schedules:
        i.requested_by = User.objects.get(pk=i.requested_by)
        i.approved_by = User.objects.get(pk=i.approved_by)
    return render(request, "pending_approvals/laminator_cancelled_approvals.html", {'schedules': schedules})


# Approve laminator cancellation request
@login_required(login_url='login')
def approve_laminator_cancellation_request(request, pk):
    item = LaminatorSchedule.objects.get(id=pk)
    current_site = get_current_site(request)
    current_user = request.user
    if request.method == 'POST':
        item.cancelled = True
        item.approved_by = current_user.pk
        item.action_status = 'Approved'
        if is_connected():
            item.save()
            Event.objects.create(user_id=current_user.pk, action="Approved {}'s pending cancellation request".
                                 format(User.objects.get(pk=item.requested_by)))
            send_pending_feedback_email(user=User.objects.get(pk=item.requested_by),
                                        admin=User.objects.get(pk=item.approved_by), action='approved',
                                        heading='Congratulations',
                                        current_site=current_site.domain,
                                        info='{} schedule cancellation'.format(item.laminator_number))
            messages.success(request,
                             f'Cancellation approved successfully! {User.objects.get(pk=item.requested_by)} will be notified by mail.')
            return redirect('laminator_cancellation_requests')
        else:
            messages.info(request, 'No connection. Check your internet connection and retry!')
            return redirect('laminator_cancellation_requests')
    return render(request, 'pending_approvals/approve_cancellation_prompt.html', {'item': item})


@login_required(login_url='login')
def reject_laminator_cancellation_request(request, pk):
    item = LaminatorSchedule.objects.get(id=pk)
    current_site = get_current_site(request)
    current_user = request.user
    if request.method == 'POST':
        item.approved_by = current_user.pk
        item.action_status = 'Approved'
        if is_connected():
            item.save()
            Event.objects.create(user_id=current_user.pk, action="Rejected {}'s pending cancellation request".
                                 format(User.objects.get(pk=item.requested_by)))
            send_pending_feedback_email(user=User.objects.get(pk=item.requested_by),
                                        admin=User.objects.get(pk=item.approved_by), action='rejected',
                                        heading='sorry',
                                        current_site=current_site.domain,
                                        info='{} schedule cancellation'.format(item.laminator_number))
            messages.success(request, 'Cancellation rejected successfully! {} will be notified by mail.'.
                             format(User.objects.get(pk=item.requested_by)))
            return redirect('laminator_cancellation_requests')
        else:
            messages.info(request, 'No connection. Check your internet connection and retry!')
            return redirect('laminator_cancellation_requests')
    return render(request, 'pending_approvals/reject_cancellation_prompt.html', {'item': item})


# View fixed laminators
@login_required(login_url='login')
def fixed_laminators(request):
    title, start_date, end_date = '', '', ''
    schedules = LaminatorSchedule.objects.filter(cancelled=False, repair_status='Fixed').order_by('-updated_at')
    for i in schedules:
        i.fixed_by = User.objects.get(id=i.fixed_by)
        i.problem = i.problem + ', ' + i.other_problem
    if request.method == 'POST':
        start_date = request.POST['date']
        end_date = request.POST["date2"]
        title = f'From {start_date} to {end_date}'
        schedules = LaminatorSchedule.objects.filter(cancelled=False, repair_status='Fixed',
                                                     date_repaired__gte=start_date,
                                                     date_repaired__lte=end_date)
        for i in schedules:
            i.fixed_by = User.objects.get(id=i.fixed_by)
            i.problem = i.problem + ', ' + i.other_problem
    return render(request, "laminator/fixed_laminators.html",
                  {'schedules': schedules, 'title': title, 'date2': end_date, 'date': start_date})


# Add purchased printer
@login_required(login_url='login')
def add_purchased_laminator(request):
    current_user = request.user
    if request.method == 'POST':
        form = AddLaminatorForm(request.POST)
        if form.is_valid():
            cid = Client.objects.get(client_name=form.cleaned_data.get('client')).pk
            bname = form.cleaned_data.get('box_number')
            pname = form.cleaned_data.get('laminator_number')
            pd = form.cleaned_data.get('p_date')
            Laminator.objects.create(user=current_user, laminator_number=pname, box_number=bname, date_purchased=pd,
                                     client_id=cid)
            Event.objects.create(user_id=current_user.pk, action='Added new purchased laminator {}'.format(pname))
            messages.success(request, 'Laminator {} added successfully!'.format(pname))
            return redirect('add_laminator')
    else:
        form = AddLaminatorForm()
    return render(request, 'procurement/add_laminator.html', {'form': form})


# View client laminators
@login_required(login_url='login')
def client_laminators(request):
    if request.method == 'POST':
        form = ClientPrintersForm(request.POST)
        if form.is_valid():
            client = Client.objects.get(client_name=form.cleaned_data.get('client'))
            cid = client.pk
            qrt = Laminator.objects.filter(client_id=cid).order_by('-created_at')
            title = f'{client} Laminators'
    else:
        form = ClientPrintersForm()
        title = 'All Laminators'
        qrt = Laminator.objects.all().order_by('-created_at')
    return render(request, "procurement/client_laminators.html", {'form': form, 'printers': qrt, 'title': title})


# Update from printers list
@login_required(login_url='login')
def update_laminator(request, pk):
    item = Laminator.objects.get(id=pk)
    form = UpdateLaminatorForm(instance=item)
    current_user = request.user

    if request.method == 'POST':
        form = UpdateLaminatorForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            item.user = current_user
            item.save()
            Event.objects.create(user_id=current_user.pk, action='Updated purchased lamiantor {} details'.format(item))
            messages.success(request, 'Laminator {} details updated successfully!'.format(item))
            return redirect('client_laminators')
    return render(request, 'procurement/printer_update.html', {'form': form})


# User report
@login_required(login_url='login')
def user_laminator_report(request):
    plist, title = [], 'All Technicians Report on laminators'
    qrst = User.objects.filter(is_active=True).order_by('first_name')
    for name in qrst:
        if not (name.is_pro or name.is_accountant):
            plist.append(name)

    for i in plist:
        r = 0
        schedules = LaminatorSchedule.objects.filter(user=i.id, cancelled=False).all()
        cancel = LaminatorSchedule.objects.filter(cancelled=True, requested_by=i.id).all()
        fixed = LaminatorSchedule.objects.filter(cancelled=False, fixed_by=i.id).all()
        part_reqs = PartStock.objects.filter(user=f'{i.first_name} {i.middle_name} {i.last_name}',
                                             action_status='Approved')
        for k in part_reqs:
            r += k.request
        i.username = len(schedules)  # total scheduled
        i.email = len(fixed)  # total fixed
        i.password = len(cancel)  # total cancelled
        i.is_active = r  # total parts requested
    start_date = 'All'
    end_date = 'All'
    if request.method == 'POST':
        start_date = request.POST['date']
        end_date = request.POST["date2"]
        title = f'Technicians Report from {start_date} to {end_date}'

        for i in plist:
            r = 0
            schedules = LaminatorSchedule.objects.filter(cancelled=False, user=i.id, created_at__gte=start_date,
                                                         created_at__lte=end_date)
            cancel = LaminatorSchedule.objects.filter(date_cancelled__gte=start_date, date_cancelled__lte=end_date,
                                                      cancelled=True, requested_by=i.id)
            fixed = LaminatorSchedule.objects.filter(cancelled=False, date_repaired__gte=start_date,
                                                     date_repaired__lte=end_date, fixed_by=i.id)
            part_reqs = PartStock.objects.filter(user=f'{i.first_name} {i.middle_name} {i.last_name}',
                                                 action_status='Approved', created_at__gte=start_date,
                                                 created_at__lte=end_date)
            for k in part_reqs:
                r += k.request
            i.username = len(schedules)  # total scheduled
            i.email = len(fixed)  # total fixed
            i.password = len(cancel)  # total cancelled
            i.is_active = r  # total parts requested
    return render(request, "users/user_laminator_report.html",
                  {'parts': plist, 'title': title, 'date2': end_date, 'date': start_date})


# User report breakdown
@login_required(login_url='login')
def user_report_laminator_details(request, pk, type, period, date, date2):
    user = User.objects.get(pk=pk)
    r = 0
    schedules = LaminatorSchedule.objects.filter(user=pk, cancelled=False).all()
    cancel = LaminatorSchedule.objects.filter(cancelled=True, requested_by=user.id).all()
    fixed = LaminatorSchedule.objects.filter(cancelled=False, fixed_by=user.id).all()
    part_reqs = PartStock.objects.filter(user=f'{user.first_name} {user.middle_name} {user.last_name}',
                                         action_status='Approved').exclude(request=0)
    title = f'Laminators {type} by {user}'

    if type == 'scheduled' and period[0] == 'A':
        data = schedules
    elif type == 'scheduled':
        data = LaminatorSchedule.objects.filter(cancelled=False, user=user.id, created_at__gte=date,
                                                created_at__lte=date2)
    elif type == 'fixed' and period[0] == 'A':
        data = fixed
    elif type == 'fixed':
        data = LaminatorSchedule.objects.filter(cancelled=False, fixed_by=user.id, date_repaired__gte=date,
                                                date_repaired__lte=date2)
    elif type == 'cancelled' and period[0] == 'A':
        data = cancel
    elif type == 'cancelled':
        title = f'Approved {type} printers by {user}'
        data = LaminatorSchedule.objects.filter(cancelled=True, requested_by=user.id, date_cancelled__gte=date,
                                                date_cancelled__lte=date2)
    else:
        title = f'Part requested by {user}'
        data = part_reqs
    json_data = {'schedules': data, 'period': period, 'pk': pk, 'type': type, 'title': title, 'date': date,
                 'date2': date2}
    return render(request, 'users/user_report_laminator_details.html', json_data)


# Client report
@login_required(login_url='login')
def client_laminator_report(request):
    st = str(datetime.today() - timedelta(days=5))[:10]
    td = str(datetime.today())[:10]
    title = f'Weekly Report for {st} to ' + td
    plist = Client.objects.filter(action_status='Approved').order_by('-created_at')
    start_date = td
    end_date = td

    for i in plist:
        schedules = LaminatorSchedule.objects.filter(client=i.id, cancelled=False,
                                                     pickup_date__gte=datetime.today() - timedelta(days=5),
                                                     pickup_date__lte=datetime.today())
        cancel = LaminatorSchedule.objects.filter(date_cancelled__gte=datetime.today() - timedelta(days=5),
                                                  date_cancelled__lte=datetime.today(),
                                                  cancelled=True, client=i.id)
        fixed = LaminatorSchedule.objects.filter(date_repaired__gte=datetime.today() - timedelta(days=5),
                                                 date_repaired__lte=datetime.today(),
                                                 repair_status='Fixed', cancelled=False, client=i.id)
        pending = LaminatorSchedule.objects.filter(repair_status='Pending', cancelled=False, client=i.id)
        i.requested_by = len(pending)  # total pending
        i.address = len(schedules)  # total scheduled
        i.rep = len(fixed)  # total fixed
        i.approved_by = len(cancel)  # total cancelled
    if request.method == 'POST':
        start_date = request.POST['date']
        end_date = request.POST["date2"]
        title = f'Client Report from {start_date} to {end_date}'
        for i in plist:
            schedules = LaminatorSchedule.objects.filter(client=i.id, cancelled=False, pickup_date__gte=start_date,
                                                         pickup_date__lte=end_date)
            cancel = LaminatorSchedule.objects.filter(date_cancelled__gte=start_date, date_cancelled__lte=end_date,
                                                      cancelled=True, client=i.id)
            fixed = LaminatorSchedule.objects.filter(date_repaired__gte=start_date, date_repaired__lte=end_date,
                                                     repair_status='Fixed', cancelled=False, client=i.id)
            pending = LaminatorSchedule.objects.filter(repair_status='Pending', cancelled=False, client=i.id)
            i.requested_by = len(pending)  # total pending
            i.address = len(schedules)  # total scheduled
            i.rep = len(fixed)  # total fixed
            i.approved_by = len(cancel)  # total cancelled
    return render(request, "clients/client_laminator_report.html",
                  {'parts': plist, 'title': title, 'date2': end_date, 'date': start_date})


# User report breakdown
@login_required(login_url='login')
def client_report_laminator_details(request, pk, type, period, date, date2):
    user = Client.objects.get(pk=pk)
    pending = LaminatorSchedule.objects.filter(repair_status='Pending', cancelled=False, client=pk)

    title = f'{user} {type} laminators'

    date_object = datetime.strptime(date, '%Y-%m-%d')  # date object

    if type == 'scheduled' and period[0] == 'W':
        data = LaminatorSchedule.objects.filter(client=pk, cancelled=False, pickup_date__gte=date_object - timedelta(days=5),
                                                pickup_date__lte=date)
    elif type == 'scheduled':
        data = LaminatorSchedule.objects.filter(cancelled=False, client=pk, pickup_date__gte=date,
                                                pickup_date__lte=date2)
    elif type == 'fixed' and period[0] == 'W':
        data = LaminatorSchedule.objects.filter(cancelled=False, repair_status='Fixed', client=pk,
                                                date_repaired__gte=date_object - timedelta(days=5),
                                                date_repaired__lte=date)

    elif type == 'fixed':
        data = LaminatorSchedule.objects.filter(cancelled=False, repair_status='Fixed', client=pk,
                                                date_repaired__gte=date,
                                                date_repaired__lte=date2)
    elif type == 'cancelled' and period[0] == 'W':
        title = f'Approved {user} {type} laminators'
        data = LaminatorSchedule.objects.filter(cancelled=True, client=pk, date_cancelled__gte=date_object - timedelta(days=5),
                                                date_cancelled__lte=date)
    elif type == 'cancelled':
        title = f'Approved {user} {type} laminators'
        data = LaminatorSchedule.objects.filter(cancelled=True, client=pk, date_cancelled__gte=date,
                                                date_cancelled__lte=date2)
    else:
        data = pending
    json_data = {'schedules': data, 'period': period, 'pk': pk, 'type': type, 'title': title}

    return render(request, 'clients/client_report_laminator_details.html', json_data)


# mrw options
@login_required(login_url='login')
def mrw_options(request):
    return render(request, "mrw/mrw_options.html")


@login_required(login_url='login')
def schedule_mrw(request):
    if request.method == 'POST':
        form = ScheduleMRWForm(request.POST)
        if form.is_valid():
            current_user = request.user
            pname = form.cleaned_data.get('mrw_number').upper()
            pparts = form.cleaned_data.get('pickup_parts')
            cname = (form.cleaned_data.get('client'))
            pdate = form.cleaned_data.get('pickup_date')
            p = form.cleaned_data.get('problem')
            asstech = form.cleaned_data.get('assigned_technicians')
            cid = Client.objects.get(client_name=cname).pk
            uid = current_user.pk
            purchased = MRW.objects.filter(mrw_number=pname)

            try:
                # Query validations on schedule
                fixed_update_required = MRWSchedule.objects.filter(mrw_number=pname, cancelled=False,
                                                                   repair_status='Pending')
            except (TypeError, ValueError, OverflowError):
                existing_printer = None

            if fixed_update_required:
                # prompt user schedule already exist and redirect to to update fixed status
                messages.warning(request, 'MRW {} schedule needs repair status update'.format(pname))
                return redirect('mrw_update')
            else:
                if not purchased:
                    MRW.objects.create(user=current_user, mrw_number=pname, client_id=cid)
                MRWSchedule.objects.create(user_id=uid, client_id=cid, mrw_number=pname, pickup_parts=pparts,
                                           pickup_date=pdate, problem=p, assigned_technicians=asstech)
                Event.objects.create(user_id=current_user.pk, action=f'Scheduled MRW {pname} for maintenance')
                messages.success(request, 'MRW {} scheduled for maintenance successfully!'.format(pname))
                return redirect('schedule_mrw')
    else:
        form = ScheduleMRWForm()
    return render(request, 'mrw/schedule_mrw.html', {'form': form})


# Direct update with mrw number
@login_required(login_url='login')
def mrw_update(request):
    if request.method == 'POST':
        form = MRWUpdateForm(request.POST)
        if form.is_valid():
            current_user = request.user
            pname = form.cleaned_data.get('mrw_number').capitalize()

            fixed_update_required = MRWSchedule.objects.filter(mrw_number=pname, cancelled=False,
                                                               repair_status='Pending')

            if fixed_update_required:
                for update in fixed_update_required:
                    update.repair_status = 'Fixed'
                    update.date_repaired = datetime.today().date()
                    update.problem = form.cleaned_data.get('problem')
                    update.parts_replaced = form.cleaned_data.get('parts_replaced')
                    update.fixed_by = current_user.pk
                    update.save()
                    Event.objects.create(user_id=current_user.pk, action='Updated repair status of '
                                                                         'MRW {} maintenance schedule'.format(pname))
                messages.success(request,
                                 'MRW {} maintenance schedule has been updated successfully!'.format(pname))
                return redirect('mrw_update')
            else:
                messages.warning(request, 'Sorry, MRW {} has not been scheduled for maintenance! '
                                          'Perhaps it has been updated as repaired'.format(pname))
                return redirect('mrw_update')
    else:
        form = MRWUpdateForm()
    return render(request, 'laminator/laminator_update.html', {'form': form})


# cancel with mrw number
@login_required(login_url='login')
def cancel_mrw_schedule(request):
    if request.method == 'POST':
        form = CancelMRWScheduleForm(request.POST)
        if form.is_valid():
            current_user = request.user
            pname = form.cleaned_data.get('mrw_number').capitalize()

            fixed_update_required = MRWSchedule.objects.filter(mrw_number=pname, cancelled=False,
                                                               repair_status='Pending')

            if not fixed_update_required:
                messages.warning(request, 'Sorry, MRW {} has not been scheduled for maintenance! '
                                          'Perhaps it has been updated as fixed'.format(pname))
                return redirect('cancel_mrw_schedule')

            else:
                for update in fixed_update_required:
                    update.cancelled = True
                    update.requested_by = current_user.pk
                    update.approved_by = current_user.pk
                    update.action_status = 'Approved'
                    update.date_cancelled = datetime.today().date()
                    update.cancellation_reason = form.cleaned_data.get('cancellation_reason')
                    update.save()
                    Event.objects.create(user_id=current_user.pk, action='Cancelled MRW {} maintenance schedule'.
                                         format(pname))
                messages.success(request, 'MRW {} maintenance schedule has successfully been cancelled!'.format(pname))
                return redirect('cancel_mrw_schedule')
    else:
        form = CancelMRWScheduleForm()
    return render(request, 'schedule/cancel_schedule.html', {'form': form})


# both schedule and update mrw
@login_required(login_url='login')
def mrw_schedule_update(request):
    if request.method == 'POST':
        form = MRWScheduleUpdateForm(request.POST)
        if form.is_valid():
            current_user = request.user
            pname = form.cleaned_data.get('mrw_number').upper()
            pparts = form.cleaned_data.get('pickup_parts')
            cname = (form.cleaned_data.get('client'))
            pdate = form.cleaned_data.get('pickup_date')
            p = form.cleaned_data.get('problem')
            cid = Client.objects.get(client_name=cname).pk
            uid = current_user.pk
            dr = datetime.today().date()
            pr = form.cleaned_data.get('parts_replaced')
            purchased = MRW.objects.filter(mrw_number=pname)

            try:
                # Query validations on schedule
                fixed_update_required = MRWSchedule.objects.filter(mrw_number=pname, cancelled=False,
                                                                   repair_status='Pending')

            except (TypeError, ValueError, OverflowError):
                existing_printer = None

            if fixed_update_required:
                # prompt user schedule already exist and redirect to update fixed status
                messages.warning(request, 'MRW {} schedule needs repair status update'.format(pname))
                return redirect('mrw_update')

            else:
                MRWSchedule.objects.create(user_id=uid, client_id=cid, mrw_number=pname, repair_status='Fixed',
                                           pickup_parts=pparts, pickup_date=pdate, problem=p, date_repaired=dr,
                                           parts_replaced=pr, fixed_by=current_user.pk)
                if not purchased:
                    MRW.objects.create(user=current_user, mrw_number=pname, client_id=cid)
                Event.objects.create(user_id=current_user.pk, action=f'Scheduled mrw {pname} for maintenance')
                messages.success(request, 'MRW {} scheduled for maintenance successfully!'.format(pname))
                return redirect('mrw_schedule_update')
    else:
        form = MRWScheduleUpdateForm()
    return render(request, 'schedule/schedule_update.html', {'form': form})


# View cancelled schedules
@login_required(login_url='login')
def cancelled_mrw_schedules(request):
    schedules = MRWSchedule.objects.filter(cancelled=True).order_by('-updated_at')
    for i in schedules:
        i.requested_by = User.objects.get(pk=i.requested_by)
    return render(request, "mrw/cancelled_schedules.html", {'schedules': schedules})


# View laminators under maintenance
@login_required(login_url='login')
def pending_mrws(request):
    schedules = MRWSchedule.objects.order_by('-updated_at').filter(cancelled=False, repair_status='Pending')
    return render(request, "mrw/pending_mrws.html", {'schedules': schedules})


# Update from maintenance list
@login_required(login_url='login')
def update_pending_mrw(request, pk):
    item = MRWSchedule.objects.get(id=pk)
    form = UpdatePendingMRWForm(instance=item)
    current_user = request.user

    if request.method == 'POST':
        form = UpdatePendingMRWForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            Event.objects.create(user_id=current_user.pk, action='Updated MRW {} maintenance schedule'.
                                 format(item.mrw_number))
            messages.success(request,
                             'MRW {} maintenance schedule updated successfully!'.format(item.mrw_number))
            return redirect('pending_mrws_u')
    return render(request, 'schedule/update_schedule.html', {'form': form})


# cancel from maintenance list
@login_required(login_url='login')
def cancel_pending_mrw(request, pk):
    item = MRWSchedule.objects.get(id=pk)
    if request.method == 'POST':
        form = CancelMaintenanceForm(request.POST)
        if form.is_valid():
            current_user = request.user
            item.requested_by = current_user.pk
            item.action_status = 'Approved'
            item.approved_by = current_user.pk
            item.date_cancelled = datetime.today().date()
            item.cancellation_reason = form.cleaned_data.get('cancellation_reason')
            item.save()
            Event.objects.create(user_id=current_user.pk, action='Cancelled MRW {} maintenance schedule'.
                                 format(item.mrw_number))
            messages.success(request,
                             'MRW {} maintenance schedule has successfully been cancelled!'.format(item.mrw_number))
            return redirect('pending_mrws')
    else:
        form = CancelMaintenanceForm()
    return render(request, 'standard_account/schedules/cancel_schedule.html', {'form': form})


# mrw Pending cancellation requests
@login_required(login_url='login')
def mrw_cancellation_requests(request):
    schedules = MRWSchedule.objects.filter(cancelled=False, action_status='Pending').order_by('-updated_at')
    for i in schedules:
        i.requested_by = User.objects.get(pk=i.requested_by)
        i.approved_by = User.objects.get(pk=i.approved_by)
    return render(request, "pending_approvals/mrw_cancelled_approvals.html", {'schedules': schedules})


# Approve laminator cancellation request
@login_required(login_url='login')
def approve_mrw_cancellation_request(request, pk):
    item = MRWSchedule.objects.get(id=pk)
    current_site = get_current_site(request)
    current_user = request.user
    if request.method == 'POST':
        item.cancelled = True
        item.approved_by = current_user.pk
        item.action_status = 'Approved'
        if is_connected():
            item.save()
            Event.objects.create(user_id=current_user.pk, action="Approved {}'s pending cancellation request".
                                 format(User.objects.get(pk=item.requested_by)))
            send_pending_feedback_email(user=User.objects.get(pk=item.requested_by),
                                        admin=User.objects.get(pk=item.approved_by), action='approved',
                                        heading='Congratulations',
                                        current_site=current_site.domain,
                                        info='{} schedule cancellation'.format(item.mrw_number))
            messages.success(request,
                             f'Cancellation approved successfully! {User.objects.get(pk=item.requested_by)} will be notified by mail.')
            return redirect('mrw_cancellation_requests')
        else:
            messages.info(request, 'No connection. Check your internet connection and retry!')
            return redirect('mrw_cancellation_requests')
    return render(request, 'pending_approvals/approve_cancellation_prompt.html', {'item': item})


@login_required(login_url='login')
def reject_mrw_cancellation_request(request, pk):
    item = MRWSchedule.objects.get(id=pk)
    current_site = get_current_site(request)
    current_user = request.user
    if request.method == 'POST':
        item.approved_by = current_user.pk
        item.action_status = 'Approved'
        if is_connected():
            item.save()
            Event.objects.create(user_id=current_user.pk, action="Rejected {}'s pending cancellation request".
                                 format(User.objects.get(pk=item.requested_by)))
            send_pending_feedback_email(user=User.objects.get(pk=item.requested_by),
                                        admin=User.objects.get(pk=item.approved_by), action='rejected',
                                        heading='sorry',
                                        current_site=current_site.domain,
                                        info='{} schedule cancellation'.format(item.mrw_number))
            messages.success(request, 'Cancellation rejected successfully! {} will be notified by mail.'.
                             format(User.objects.get(pk=item.requested_by)))
            return redirect('mrw_cancellation_requests')
        else:
            messages.info(request, 'No connection. Check your internet connection and retry!')
            return redirect('mrw_cancellation_requests')
    return render(request, 'pending_approvals/reject_cancellation_prompt.html', {'item': item})


# View fixed laminators
@login_required(login_url='login')
def fixed_mrws(request):
    title, start_date, end_date = '', '', ''
    schedules = MRWSchedule.objects.filter(cancelled=False, repair_status='Fixed').order_by('-updated_at')
    for i in schedules:
        i.fixed_by = User.objects.get(id=i.fixed_by)
    if request.method == 'POST':
        start_date = request.POST['date']
        end_date = request.POST["date2"]
        title = f'From {start_date} to {end_date}'
        schedules = MRWSchedule.objects.filter(cancelled=False, repair_status='Fixed', date_repaired__gte=start_date,
                                               date_repaired__lte=end_date)
        for i in schedules:
            i.fixed_by = User.objects.get(id=i.fixed_by)
    return render(request, "mrw/fixed_mrws.html",
                  {'schedules': schedules, 'title': title, 'date2': end_date, 'date': start_date})


# View client laminators
@login_required(login_url='login')
def client_mrws(request):
    if request.method == 'POST':
        form = ClientPrintersForm(request.POST)
        if form.is_valid():
            client = Client.objects.get(client_name=form.cleaned_data.get('client'))
            cid = client.pk
            qrt = MRW.objects.filter(client_id=cid).order_by('-created_at')
            title = f'{client} MRWs'
    else:
        form = ClientPrintersForm()
        title = 'ALL MRWs'
        qrt = MRW.objects.all().order_by('-created_at')
    return render(request, "procurement/client_mrws.html", {'form': form, 'printers': qrt, 'title': title})


# Update from printers list
@login_required(login_url='login')
def update_mrw(request, pk):
    item = MRW.objects.get(id=pk)
    form = UpdateMRWForm(instance=item)
    current_user = request.user

    if request.method == 'POST':
        form = UpdateMRWForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            item.user = current_user
            item.save()
            Event.objects.create(user_id=current_user.pk, action='Updated purchased MRW {} details'.format(item))
            messages.success(request, 'MRW {} details updated successfully!'.format(item))
            return redirect('client_mrws')
    return render(request, 'procurement/printer_update.html', {'form': form})


# User report
@login_required(login_url='login')
def user_mrw_report(request):
    plist, title = [], 'All Technicians Report on MRWs'
    qrst = User.objects.filter(is_active=True).order_by('first_name')
    for name in qrst:
        if not (name.is_pro or name.is_accountant):
            plist.append(name)

    for i in plist:
        r = 0
        schedules = MRWSchedule.objects.filter(user=i.id, cancelled=False).all()
        cancel = MRWSchedule.objects.filter(cancelled=True, requested_by=i.id).all()
        fixed = MRWSchedule.objects.filter(cancelled=False, fixed_by=i.id).all()
        part_reqs = PartStock.objects.filter(user=f'{i.first_name} {i.middle_name} {i.last_name}',
                                             action_status='Approved')
        for k in part_reqs:
            r += k.request
        i.username = len(schedules)  # total scheduled
        i.email = len(fixed)  # total fixed
        i.password = len(cancel)  # total cancelled
        i.is_active = r  # total parts requested
    start_date = 'All'
    end_date = 'All'
    if request.method == 'POST':
        start_date = request.POST['date']
        end_date = request.POST["date2"]
        title = f'Technicians Report from {start_date} to {end_date}'

        for i in plist:
            r = 0
            schedules = MRWSchedule.objects.filter(cancelled=False, user=i.id, created_at__gte=start_date,
                                                   created_at__lte=end_date)
            cancel = MRWSchedule.objects.filter(date_cancelled__gte=start_date, date_cancelled__lte=end_date,
                                                cancelled=True, requested_by=i.id)
            fixed = MRWSchedule.objects.filter(cancelled=False, date_repaired__gte=start_date,
                                               date_repaired__lte=end_date, fixed_by=i.id)
            part_reqs = PartStock.objects.filter(user=f'{i.first_name} {i.middle_name} {i.last_name}',
                                                 action_status='Approved', created_at__gte=start_date,
                                                 created_at__lte=end_date)
            for k in part_reqs:
                r += k.request
            i.username = len(schedules)  # total scheduled
            i.email = len(fixed)  # total fixed
            i.password = len(cancel)  # total cancelled
            i.is_active = r  # total parts requested
    return render(request, "users/user_mrw_report.html",
                  {'parts': plist, 'title': title, 'date2': end_date, 'date': start_date})


# User report breakdown
@login_required(login_url='login')
def user_report_mrw_details(request, pk, type, period, date, date2):
    user = User.objects.get(pk=pk)
    r = 0
    schedules = MRWSchedule.objects.filter(user=pk, cancelled=False).all()
    cancel = MRWSchedule.objects.filter(cancelled=True, requested_by=user.id).all()
    fixed = MRWSchedule.objects.filter(cancelled=False, fixed_by=user.id).all()
    part_reqs = PartStock.objects.filter(user=f'{user.first_name} {user.middle_name} {user.last_name}',
                                         action_status='Approved').exclude(request=0)
    title = f'MRWs {type} by {user}'

    if type == 'scheduled' and period[0] == 'A':
        data = schedules
    elif type == 'scheduled':
        data = MRWSchedule.objects.filter(cancelled=False, user=user.id, created_at__gte=date,
                                          created_at__lte=date2)
    elif type == 'fixed' and period[0] == 'A':
        data = fixed
    elif type == 'fixed':
        data = MRWSchedule.objects.filter(cancelled=False, fixed_by=user.id, date_repaired__gte=date,
                                          date_repaired__lte=date2)
    elif type == 'cancelled' and period[0] == 'A':
        data = cancel
    elif type == 'cancelled':
        title = f'Approved {type} printers by {user}'
        data = MRWSchedule.objects.filter(cancelled=True, requested_by=user.id, date_cancelled__gte=date,
                                          date_cancelled__lte=date2)
    else:
        title = f'Part requested by {user}'
        data = part_reqs
    json_data = {'schedules': data, 'period': period, 'pk': pk, 'type': type, 'title': title, 'date': date,
                 'date2': date2}
    return render(request, 'users/user_report_mrw_details.html', json_data)


# Client report
@login_required(login_url='login')
def client_mrw_report(request):
    st = str(datetime.today() - timedelta(days=5))[:10]
    td = str(datetime.today())[:10]
    title = f'Weekly Report for {st} to ' + td
    plist = Client.objects.filter(action_status='Approved').order_by('-created_at')
    start_date = td
    end_date = td

    for i in plist:
        schedules = MRWSchedule.objects.filter(client=i.id, cancelled=False,
                                               pickup_date__gte=datetime.today() - timedelta(days=5),
                                               pickup_date__lte=datetime.today())
        cancel = MRWSchedule.objects.filter(date_cancelled__gte=datetime.today() - timedelta(days=5),
                                            date_cancelled__lte=datetime.today(),
                                            cancelled=True, client=i.id)
        fixed = MRWSchedule.objects.filter(date_repaired__gte=datetime.today() - timedelta(days=5),
                                           date_repaired__lte=datetime.today(),
                                           repair_status='Fixed', cancelled=False, client=i.id)
        pending = MRWSchedule.objects.filter(repair_status='Pending', cancelled=False, client=i.id)
        i.requested_by = len(pending)  # total pending
        i.address = len(schedules)  # total scheduled
        i.rep = len(fixed)  # total fixed
        i.approved_by = len(cancel)  # total cancelled
    if request.method == 'POST':
        start_date = request.POST['date']
        end_date = request.POST["date2"]
        title = f'Client Report from {start_date} to {end_date}'
        for i in plist:
            schedules = MRWSchedule.objects.filter(client=i.id, cancelled=False, pickup_date__gte=start_date,
                                                   pickup_date__lte=end_date)
            cancel = MRWSchedule.objects.filter(date_cancelled__gte=start_date, date_cancelled__lte=end_date,
                                                cancelled=True, client=i.id)
            fixed = MRWSchedule.objects.filter(date_repaired__gte=start_date, date_repaired__lte=end_date,
                                               repair_status='Fixed', cancelled=False, client=i.id)
            pending = MRWSchedule.objects.filter(repair_status='Pending', cancelled=False, client=i.id)
            i.requested_by = len(pending)  # total pending
            i.address = len(schedules)  # total scheduled
            i.rep = len(fixed)  # total fixed
            i.approved_by = len(cancel)  # total cancelled
    return render(request, "clients/client_mrw_report.html",
                  {'parts': plist, 'title': title, 'date2': end_date, 'date': start_date})


# User report breakdown
@login_required(login_url='login')
def client_report_mrw_details(request, pk, type, period, date, date2):
    user = Client.objects.get(pk=pk)
    pending = MRWSchedule.objects.filter(repair_status='Pending', cancelled=False, client=pk)

    title = f'{user} {type} MRWs'

    date_object = datetime.strptime(date, '%Y-%m-%d')  # date object

    if type == 'scheduled' and period[0] == 'W':
        data = MRWSchedule.objects.filter(client=pk, cancelled=False, pickup_date__gte=date_object - timedelta(days=5),
                                          pickup_date__lte=date)
    elif type == 'scheduled':
        data = MRWSchedule.objects.filter(cancelled=False, client=pk, pickup_date__gte=date,
                                          pickup_date__lte=date2)
    elif type == 'fixed' and period[0] == 'W':
        data = MRWSchedule.objects.filter(cancelled=False, repair_status='Fixed', client=pk,
                                          date_repaired__gte=date_object - timedelta(days=5),
                                          date_repaired__lte=date)

    elif type == 'fixed':
        data = MRWSchedule.objects.filter(cancelled=False, repair_status='Fixed', client=pk,
                                          date_repaired__gte=date,
                                          date_repaired__lte=date2)
    elif type == 'cancelled' and period[0] == 'W':
        title = f'Approved {user} {type} MRWs'
        data = MRWSchedule.objects.filter(cancelled=True, client=pk, date_cancelled__gte=date_object - timedelta(days=5),
                                          date_cancelled__lte=date)
    elif type == 'cancelled':
        title = f'Approved {user} {type} MRWs'
        data = MRWSchedule.objects.filter(cancelled=True, client=pk, date_cancelled__gte=date,
                                          date_cancelled__lte=date2)
    else:
        data = pending
    json_data = {'schedules': data, 'period': period, 'pk': pk, 'type': type, 'title': title}

    return render(request, 'clients/client_report_mrw_details.html', json_data)


# iss options
@login_required(login_url='login')
def iss_options(request):
    return render(request, "iss/iss_options.html")


@login_required(login_url='login')
def schedule_iss(request):
    if request.method == 'POST':
        form = ScheduleISSForm(request.POST)
        if form.is_valid():
            current_user = request.user
            pname = form.cleaned_data.get('iss_number').upper()
            if len(pname) == 8:
                messages.warning(request, 'Invalid ISS Number!')
                return redirect('iss_update')
            pparts = form.cleaned_data.get('pickup_parts')
            cname = (form.cleaned_data.get('client'))
            pdate = form.cleaned_data.get('pickup_date')
            p = form.cleaned_data.get('problem')
            asstech = form.cleaned_data.get('assigned_technicians')
            cid = Client.objects.get(client_name=cname).pk
            uid = current_user.pk

            purchased = MRW.objects.filter(iss_number=pname)

            try:
                # Query validations on schedule
                fixed_update_required = ISSSchedule.objects.filter(iss_number=pname, cancelled=False,
                                                                   repair_status='Pending')
            except (TypeError, ValueError, OverflowError):
                existing_printer = None

            if fixed_update_required:
                # prompt user schedule already exist and redirect to to update fixed status
                messages.warning(request, 'ISS {} schedule needs repair status update'.format(pname))
                return redirect('iss_update')
            else:
                if not purchased:
                    ISS.objects.create(user=current_user, iss_number=pname, client_id=cid)
                ISSSchedule.objects.create(user_id=uid, client_id=cid, iss_number=pname, pickup_parts=pparts,
                                           pickup_date=pdate, problem=p, assigned_technicians=asstech)
                Event.objects.create(user_id=current_user.pk, action=f'Scheduled ISS {pname} for maintenance')
                messages.success(request, 'ISS {} scheduled for maintenance successfully!'.format(pname))
                return redirect('schedule_iss')
    else:
        form = ScheduleISSForm()
    return render(request, 'iss/schedule_iss.html', {'form': form})


# Direct update with iss number
@login_required(login_url='login')
def iss_update(request):
    if request.method == 'POST':
        form = ISSUpdateForm(request.POST)
        if form.is_valid():
            current_user = request.user
            pname = form.cleaned_data.get('iss_number').capitalize()

            fixed_update_required = ISSSchedule.objects.filter(iss_number=pname, cancelled=False,
                                                               repair_status='Pending')

            if fixed_update_required:
                for update in fixed_update_required:
                    update.repair_status = 'Fixed'
                    update.date_repaired = datetime.today().date()
                    update.problem = form.cleaned_data.get('problem')
                    update.parts_replaced = form.cleaned_data.get('parts_replaced')
                    update.fixed_by = current_user.pk
                    update.save()
                    Event.objects.create(user_id=current_user.pk, action='Updated repair status of '
                                                                         'ISS {} maintenance schedule'.format(pname))
                messages.success(request,
                                 'ISS{} maintenance schedule has been updated successfully!'.format(pname))
                return redirect('iss_update')
            else:
                messages.warning(request, 'Sorry, ISS {} has not been scheduled for maintenance! '
                                          'Perhaps it has been updated as repaired'.format(pname))
                return redirect('iss_update')
    else:
        form = ISSUpdateForm()
    return render(request, 'laminator/laminator_update.html', {'form': form})


# cancel with mrw number
@login_required(login_url='login')
def cancel_iss_schedule(request):
    if request.method == 'POST':
        form = CancelISSScheduleForm(request.POST)
        if form.is_valid():
            current_user = request.user
            pname = form.cleaned_data.get('iss_number').capitalize()

            fixed_update_required = ISSSchedule.objects.filter(iss_number=pname, cancelled=False,
                                                               repair_status='Pending')

            if not fixed_update_required:
                messages.warning(request, 'Sorry, ISS {} has not been scheduled for maintenance! '
                                          'Perhaps it has been updated as fixed'.format(pname))
                return redirect('cancel_iss_schedule')

            else:
                for update in fixed_update_required:
                    update.cancelled = True
                    update.requested_by = current_user.pk
                    update.approved_by = current_user.pk
                    update.action_status = 'Approved'
                    update.date_cancelled = datetime.today().date()
                    update.cancellation_reason = form.cleaned_data.get('cancellation_reason')
                    update.save()
                    Event.objects.create(user_id=current_user.pk, action='Cancelled ISS {} maintenance schedule'.
                                         format(pname))
                messages.success(request, 'ISS {} maintenance schedule has successfully been cancelled!'.format(pname))
                return redirect('cancel_iss_schedule')
    else:
        form = CancelISSScheduleForm()
    return render(request, 'schedule/cancel_schedule.html', {'form': form})


# both schedule and update mrw
@login_required(login_url='login')
def iss_schedule_update(request):
    if request.method == 'POST':
        form = ISSScheduleUpdateForm(request.POST)
        if form.is_valid():
            current_user = request.user
            pname = form.cleaned_data.get('iss_number').upper()
            if len(pname) == 8:
                messages.warning(request, 'Invalid ISS Number!')
                return redirect('iss_schedule_update')
            pparts = form.cleaned_data.get('pickup_parts')
            cname = (form.cleaned_data.get('client'))
            pdate = form.cleaned_data.get('pickup_date')
            p = form.cleaned_data.get('problem')
            cid = Client.objects.get(client_name=cname).pk
            uid = current_user.pk
            dr = datetime.today().date()
            pr = form.cleaned_data.get('parts_replaced')
            purchased = ISS.objects.filter(iss_number=pname)

            try:
                # Query validations on schedule
                fixed_update_required = ISSSchedule.objects.filter(iss_number=pname, cancelled=False,
                                                                   repair_status='Pending')

            except (TypeError, ValueError, OverflowError):
                existing_printer = None

            if fixed_update_required:
                # prompt user schedule already exist and redirect to update fixed status
                messages.warning(request, 'ISS {} schedule needs repair status update'.format(pname))
                return redirect('iss_update')

            else:
                ISSSchedule.objects.create(user_id=uid, client_id=cid, iss_number=pname, repair_status='Fixed',
                                           pickup_parts=pparts, pickup_date=pdate, problem=p, date_repaired=dr,
                                           parts_replaced=pr, fixed_by=current_user.pk)
                if not purchased:
                    ISS.objects.create(user=current_user, iss_number=pname, client_id=cid)
                Event.objects.create(user_id=current_user.pk, action=f'Scheduled ISS {pname} for maintenance')
                messages.success(request, 'ISS {} scheduled for maintenance successfully!'.format(pname))
                return redirect('iss_schedule_update')
    else:
        form = ISSScheduleUpdateForm()
    return render(request, 'schedule/schedule_update.html', {'form': form})


# View cancelled schedules
@login_required(login_url='login')
def cancelled_iss_schedules(request):
    schedules = ISSSchedule.objects.filter(cancelled=True).order_by('-updated_at')
    for i in schedules:
        i.requested_by = User.objects.get(pk=i.requested_by)
    return render(request, "iss/cancelled_schedules.html", {'schedules': schedules})


# View laminators under maintenance
@login_required(login_url='login')
def pending_iss(request):
    schedules = ISSSchedule.objects.order_by('-updated_at').filter(cancelled=False, repair_status='Pending')
    return render(request, "iss/pending_iss.html", {'schedules': schedules})


# Update from maintenance list
@login_required(login_url='login')
def update_pending_iss(request, pk):
    item = ISSSchedule.objects.get(id=pk)
    form = UpdatePendingISSForm(instance=item)
    current_user = request.user

    if request.method == 'POST':
        form = UpdatePendingISSForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            Event.objects.create(user_id=current_user.pk, action='Updated ISS {} maintenance schedule'.
                                 format(item.iss_number))
            messages.success(request,
                             'ISS {} maintenance schedule updated successfully!'.format(item.iss_number))
            return redirect('pending_iss_u')
    return render(request, 'schedule/update_schedule.html', {'form': form})


# cancel from maintenance list
@login_required(login_url='login')
def cancel_pending_iss(request, pk):
    item = ISSSchedule.objects.get(id=pk)
    if request.method == 'POST':
        form = CancelMaintenanceForm(request.POST)
        if form.is_valid():
            current_user = request.user
            item.requested_by = current_user.pk
            item.action_status = 'Approved'
            item.approved_by = current_user.pk
            item.date_cancelled = datetime.today().date()
            item.cancellation_reason = form.cleaned_data.get('cancellation_reason')
            item.save()
            Event.objects.create(user_id=current_user.pk, action='Cancelled ISS {} maintenance schedule'.
                                 format(item.iss_number))
            messages.success(request,
                             'ISS {} maintenance schedule has successfully been cancelled!'.format(item.iss_number))
            return redirect('pending_iss')
    else:
        form = CancelMaintenanceForm()
    return render(request, 'standard_account/schedules/cancel_schedule.html', {'form': form})


# mrw Pending cancellation requests
@login_required(login_url='login')
def iss_cancellation_requests(request):
    schedules = ISSSchedule.objects.filter(cancelled=False, action_status='Pending').order_by('-updated_at')
    for i in schedules:
        i.requested_by = User.objects.get(pk=i.requested_by)
        i.approved_by = User.objects.get(pk=i.approved_by)
    return render(request, "pending_approvals/iss_cancelled_approvals.html", {'schedules': schedules})


# Approve laminator cancellation request
@login_required(login_url='login')
def approve_iss_cancellation_request(request, pk):
    item = ISSSchedule.objects.get(id=pk)
    current_site = get_current_site(request)
    current_user = request.user
    if request.method == 'POST':
        item.cancelled = True
        item.approved_by = current_user.pk
        item.action_status = 'Approved'
        if is_connected():
            item.save()
            Event.objects.create(user_id=current_user.pk, action="Approved {}'s pending cancellation request".
                                 format(User.objects.get(pk=item.requested_by)))
            send_pending_feedback_email(user=User.objects.get(pk=item.requested_by),
                                        admin=User.objects.get(pk=item.approved_by), action='approved',
                                        heading='Congratulations',
                                        current_site=current_site.domain,
                                        info='{} schedule cancellation'.format(item.iss_number))
            messages.success(request,
                             f'Cancellation approved successfully! {User.objects.get(pk=item.requested_by)} will be notified by mail.')
            return redirect('iss_cancellation_requests')
        else:
            messages.info(request, 'No connection. Check your internet connection and retry!')
            return redirect('iss_cancellation_requests')
    return render(request, 'pending_approvals/approve_cancellation_prompt.html', {'item': item})


@login_required(login_url='login')
def reject_iss_cancellation_request(request, pk):
    item = ISSSchedule.objects.get(id=pk)
    current_site = get_current_site(request)
    current_user = request.user
    if request.method == 'POST':
        item.approved_by = current_user.pk
        item.action_status = 'Approved'
        if is_connected():
            item.save()
            Event.objects.create(user_id=current_user.pk, action="Rejected {}'s pending cancellation request".
                                 format(User.objects.get(pk=item.requested_by)))
            send_pending_feedback_email(user=User.objects.get(pk=item.requested_by),
                                        admin=User.objects.get(pk=item.approved_by), action='rejected',
                                        heading='sorry',
                                        current_site=current_site.domain,
                                        info='{} schedule cancellation'.format(item.iss_number))
            messages.success(request, 'Cancellation rejected successfully! {} will be notified by mail.'.
                             format(User.objects.get(pk=item.requested_by)))
            return redirect('iss_cancellation_requests')
        else:
            messages.info(request, 'No connection. Check your internet connection and retry!')
            return redirect('iss_cancellation_requests')
    return render(request, 'pending_approvals/reject_cancellation_prompt.html', {'item': item})


# View fixed laminators
@login_required(login_url='login')
def fixed_iss(request):
    title, start_date, end_date = '', '', ''
    schedules = ISSSchedule.objects.filter(cancelled=False, repair_status='Fixed').order_by('-updated_at')
    for i in schedules:
        i.fixed_by = User.objects.get(id=i.fixed_by)
    if request.method == 'POST':
        start_date = request.POST['date']
        end_date = request.POST["date2"]
        title = f'From {start_date} to {end_date}'
        schedules = ISSSchedule.objects.filter(cancelled=False, repair_status='Fixed', date_repaired__gte=start_date,
                                               date_repaired__lte=end_date)
        for i in schedules:
            i.fixed_by = User.objects.get(id=i.fixed_by)
    return render(request, "iss/fixed_iss.html",
                  {'schedules': schedules, 'title': title, 'date2': end_date, 'date': start_date})


# View client laminators
@login_required(login_url='login')
def client_iss(request):
    if request.method == 'POST':
        form = ClientPrintersForm(request.POST)
        if form.is_valid():
            client = Client.objects.get(client_name=form.cleaned_data.get('client'))
            cid = client.pk
            qrt = ISS.objects.filter(client_id=cid).order_by('-created_at')
            title = f'{client} ISSs'
    else:
        form = ClientPrintersForm()
        title = 'ALL ISSs'
        qrt = ISS.objects.all().order_by('-created_at')
    return render(request, "procurement/client_iss.html", {'form': form, 'printers': qrt, 'title': title})


# Update from printers list
@login_required(login_url='login')
def update_iss(request, pk):
    item = ISS.objects.get(id=pk)
    form = UpdateISSForm(instance=item)
    current_user = request.user

    if request.method == 'POST':
        form = UpdateISSForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            item.user = current_user
            item.save()
            Event.objects.create(user_id=current_user.pk, action='Updated purchased ISS {} details'.format(item))
            messages.success(request, 'ISS {} details updated successfully!'.format(item))
            return redirect('client_iss')
    return render(request, 'procurement/printer_update.html', {'form': form})


# User report
@login_required(login_url='login')
def user_iss_report(request):
    plist, title = [], 'All Technicians Report on ISSs'
    qrst = User.objects.filter(is_active=True).order_by('first_name')
    for name in qrst:
        if not (name.is_pro or name.is_accountant):
            plist.append(name)

    for i in plist:
        r = 0
        schedules = ISSSchedule.objects.filter(user=i.id, cancelled=False).all()
        cancel = ISSSchedule.objects.filter(cancelled=True, requested_by=i.id).all()
        fixed = ISSSchedule.objects.filter(cancelled=False, fixed_by=i.id).all()
        part_reqs = PartStock.objects.filter(user=f'{i.first_name} {i.middle_name} {i.last_name}',
                                             action_status='Approved')
        for k in part_reqs:
            r += k.request
        i.username = len(schedules)  # total scheduled
        i.email = len(fixed)  # total fixed
        i.password = len(cancel)  # total cancelled
        i.is_active = r  # total parts requested
    start_date = 'All'
    end_date = 'All'
    if request.method == 'POST':
        start_date = request.POST['date']
        end_date = request.POST["date2"]
        title = f'Technicians Report from {start_date} to {end_date}'

        for i in plist:
            r = 0
            schedules = ISSSchedule.objects.filter(cancelled=False, user=i.id, created_at__gte=start_date,
                                                   created_at__lte=end_date)
            cancel = ISSSchedule.objects.filter(date_cancelled__gte=start_date, date_cancelled__lte=end_date,
                                                cancelled=True, requested_by=i.id)
            fixed = ISSSchedule.objects.filter(cancelled=False, date_repaired__gte=start_date,
                                               date_repaired__lte=end_date, fixed_by=i.id)
            part_reqs = PartStock.objects.filter(user=f'{i.first_name} {i.middle_name} {i.last_name}',
                                                 action_status='Approved', created_at__gte=start_date,
                                                 created_at__lte=end_date)
            for k in part_reqs:
                r += k.request
            i.username = len(schedules)  # total scheduled
            i.email = len(fixed)  # total fixed
            i.password = len(cancel)  # total cancelled
            i.is_active = r  # total parts requested
    return render(request, "users/user_iss_report.html",
                  {'parts': plist, 'title': title, 'date2': end_date, 'date': start_date})


# User report breakdown
@login_required(login_url='login')
def user_report_iss_details(request, pk, type, period, date, date2):
    user = User.objects.get(pk=pk)
    r = 0
    schedules = ISSSchedule.objects.filter(user=pk, cancelled=False).all()
    cancel = ISSSchedule.objects.filter(cancelled=True, requested_by=user.id).all()
    fixed = ISSSchedule.objects.filter(cancelled=False, fixed_by=user.id).all()
    part_reqs = PartStock.objects.filter(user=f'{user.first_name} {user.middle_name} {user.last_name}',
                                         action_status='Approved').exclude(request=0)
    title = f'MRWs {type} by {user}'

    if type == 'scheduled' and period[0] == 'A':
        data = schedules
    elif type == 'scheduled':
        data = ISSSchedule.objects.filter(cancelled=False, user=user.id, created_at__gte=date,
                                          created_at__lte=date2)
    elif type == 'fixed' and period[0] == 'A':
        data = fixed
    elif type == 'fixed':
        data = ISSSchedule.objects.filter(cancelled=False, fixed_by=user.id, date_repaired__gte=date,
                                          date_repaired__lte=date2)
    elif type == 'cancelled' and period[0] == 'A':
        data = cancel
    elif type == 'cancelled':
        title = f'Approved {type} printers by {user}'
        data = ISSSchedule.objects.filter(cancelled=True, requested_by=user.id, date_cancelled__gte=date,
                                          date_cancelled__lte=date2)
    else:
        title = f'Part requested by {user}'
        data = part_reqs
    json_data = {'schedules': data, 'period': period, 'pk': pk, 'type': type, 'title': title, 'date': date,
                 'date2': date2}
    return render(request, 'users/user_report_iss_details.html', json_data)


# Client report
@login_required(login_url='login')
def client_iss_report(request):
    st = str(datetime.today() - timedelta(days=5))[:10]
    td = str(datetime.today())[:10]
    title = f'Weekly Report for {st} to ' + td
    plist = Client.objects.filter(action_status='Approved').order_by('-created_at')
    start_date = td
    end_date = td

    for i in plist:
        schedules = ISSSchedule.objects.filter(client=i.id, cancelled=False,
                                               pickup_date__gte=datetime.today() - timedelta(days=5),
                                               pickup_date__lte=datetime.today())
        cancel = ISSSchedule.objects.filter(date_cancelled__gte=datetime.today() - timedelta(days=5),
                                            date_cancelled__lte=datetime.today(),
                                            cancelled=True, client=i.id)
        fixed = ISSSchedule.objects.filter(date_repaired__gte=datetime.today() - timedelta(days=5),
                                           date_repaired__lte=datetime.today(),
                                           repair_status='Fixed', cancelled=False, client=i.id)
        pending = ISSSchedule.objects.filter(repair_status='Pending', cancelled=False, client=i.id)
        i.requested_by = len(pending)  # total pending
        i.address = len(schedules)  # total scheduled
        i.rep = len(fixed)  # total fixed
        i.approved_by = len(cancel)  # total cancelled
    if request.method == 'POST':
        start_date = request.POST['date']
        end_date = request.POST["date2"]
        title = f'Client Report from {start_date} to {end_date}'
        for i in plist:
            schedules = ISSSchedule.objects.filter(client=i.id, cancelled=False, pickup_date__gte=start_date,
                                                   pickup_date__lte=end_date)
            cancel = ISSSchedule.objects.filter(date_cancelled__gte=start_date, date_cancelled__lte=end_date,
                                                cancelled=True, client=i.id)
            fixed = ISSSchedule.objects.filter(date_repaired__gte=start_date, date_repaired__lte=end_date,
                                               repair_status='Fixed', cancelled=False, client=i.id)
            pending = ISSSchedule.objects.filter(repair_status='Pending', cancelled=False, client=i.id)
            i.requested_by = len(pending)  # total pending
            i.address = len(schedules)  # total scheduled
            i.rep = len(fixed)  # total fixed
            i.approved_by = len(cancel)  # total cancelled
    return render(request, "clients/client_iss_report.html",
                  {'parts': plist, 'title': title, 'date2': end_date, 'date': start_date})


# User report breakdown
@login_required(login_url='login')
def client_report_iss_details(request, pk, type, period, date, date2):
    user = Client.objects.get(pk=pk)
    pending = ISSSchedule.objects.filter(repair_status='Pending', cancelled=False, client=pk)

    title = f'{user} {type} ISSs'

    date_object = datetime.strptime(date, '%Y-%m-%d')  # date object

    if type == 'scheduled' and period[0] == 'W':
        data = ISSSchedule.objects.filter(client=pk, cancelled=False, pickup_date__gte=date_object - timedelta(days=5),
                                          pickup_date__lte=date)
    elif type == 'scheduled':
        data = ISSSchedule.objects.filter(cancelled=False, client=pk, pickup_date__gte=date,
                                          pickup_date__lte=date2)
    elif type == 'fixed' and period[0] == 'W':
        data = ISSSchedule.objects.filter(cancelled=False, repair_status='Fixed', client=pk,
                                          date_repaired__gte=date_object - timedelta(days=5),
                                          date_repaired__lte=date)

    elif type == 'fixed':
        data = ISSSchedule.objects.filter(cancelled=False, repair_status='Fixed', client=pk,
                                          date_repaired__gte=date,
                                          date_repaired__lte=date2)
    elif type == 'cancelled' and period[0] == 'W':
        title = f'Approved {user} {type} MRWs'
        data = ISSSchedule.objects.filter(cancelled=True, client=pk, date_cancelled__gte=date_object - timedelta(days=5),
                                          date_cancelled__lte=date)
    elif type == 'cancelled':
        title = f'Approved {user} {type} MRWs'
        data = ISSSchedule.objects.filter(cancelled=True, client=pk, date_cancelled__gte=date,
                                          date_cancelled__lte=date2)
    else:
        data = pending
    json_data = {'schedules': data, 'period': period, 'pk': pk, 'type': type, 'title': title}

    return render(request, 'clients/client_report_iss_details.html', json_data)
