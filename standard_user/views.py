from django.shortcuts import render, redirect
from printer_support.forms import *
from .forms import *
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from printer_support.emails import send_pending_email
from printer_support.views import is_connected
from datetime import datetime, timedelta
from maintenance_portal.settings import EMAIL_HOST_USER
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_decode


# User managements
@login_required(login_url='login')
def user_management(request):
    return render(request, "standard_account/user_options.html")


# History
@login_required(login_url='login')
def event(request):
    history = Event.objects.filter(user=request.user).order_by('-created_at')
    title, start_date, end_date = '', '', ''
    if request.method == 'POST':
        start_date = request.POST['date']
        end_date = request.POST["date2"]
        title = f'From {start_date} to {end_date}'
        history = Event.objects.filter(user=request.user.pk, created_at__date__range=(start_date, end_date)).order_by('-created_at')
    return render(request, "standard_account/event.html",
                  {'events': history, 'title': title, 'date2': end_date, 'date': start_date})


# Request to add client
@login_required(login_url='login')
def add_client(request):
    if request.method == 'POST':
        form = AddClientForm(request.POST)
        if form.is_valid():
            current_user = request.user
            current_site = get_current_site(request)
            new_client = form.save(commit=False)
            name = form.cleaned_data.get('client_name')
            new_client.requested_by = str(current_user.email)
            new_client.action_status = 'Pending'

            try:
                existing_request = Client.objects.get(client_name=name)
            except (TypeError, ValueError, OverflowError, Client.DoesNotExist):
                existing_request = None
            if existing_request:
                if existing_request.action_status == 'Pending':
                    messages.info(request, 'Adding client request already sent and it awaits approval!'.format(name))
                    return redirect('maintenance_u')
            new_client.save()
            Event.objects.create(user_id=current_user.pk,
                                 action='Requested {} to be added as a new client'.format(name))
            if is_connected():
                send_pending_email(user=current_user, current_site=current_site.domain,
                                   subject_heading='ADDING CLIENT', reason='Attention needed')
                messages.success(request,
                                 'Request for {} to be added successfully sent to ADMIN for approval!'.format(name))
                return redirect('add_client_u')
            else:
                messages.success(request,
                                 'Request for {} to be added successfully sent to ADMIN for approval!'.format(name))
                messages.info(request, 'Email notification failed; You are not connected to internet!')
                return redirect('add_client_u')
    else:
        form = AddClientForm()
    return render(request, 'clients/add_client.html', {'form': form})


# Available reports
@login_required(login_url='login')
def reports(request):
    return render(request, "standard_account/report_options.html")


# Client report
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
    return render(request, "clients/user_client_report.html",
                  {'parts': plist, 'title': title, 'date2': end_date, 'date': start_date})


# User report breakdown
@login_required(login_url='login')
def client_report_details(request, pk, type, period, date, date2):
    user = Client.objects.get(pk=pk)
    pending = Schedule.objects.filter(repair_status='Pending', cancelled=False, client=pk)

    title = f'{user} {type} printers'

    date_object = datetime.strptime(date, '%Y-%m-%d')  # date object

    if type == 'scheduled' and period[0] == 'W':
        data = Schedule.objects.filter(client=pk, cancelled=False, pickup_date__gte=date,
                                       pickup_date__lte=date_object + timedelta(days=5))
    elif type == 'scheduled':
        data = Schedule.objects.filter(cancelled=False, client=pk, pickup_date__gte=date, pickup_date__lte=date2)
    elif type == 'fixed' and period[0] == 'W':
        data = Schedule.objects.filter(cancelled=False, repair_status='Fixed', client=pk, date_repaired__gte=date,
                                       date_repaired__lte=date_object + timedelta(days=5))
    elif type == 'fixed':
        data = Schedule.objects.filter(cancelled=False, repair_status='Fixed', client=pk, date_repaired__gte=date,
                                       date_repaired__lte=date2)
    elif type == 'cancelled' and period[0] == 'W':
        title = f'Approved {user} {type} printers'
        data = Schedule.objects.filter(cancelled=True, client=pk, date_cancelled__gte=date,
                                       date_cancelled__lte=date_object + timedelta(days=5))
    elif type == 'cancelled':
        title = f'Approved {user} {type} printers'
        data = Schedule.objects.filter(cancelled=True, client=pk, date_cancelled__gte=date,
                                       date_cancelled__lte=date2)
    else:
        data = pending
    json_data = {'schedules': data, 'period': period, 'pk': pk, 'type': type, 'title': title}

    return render(request, 'clients/user_client_report_details.html', json_data)


# delay maintenance form
@login_required(login_url='login')
def delay_maintenance(request):
    if request.method == 'POST':
        form = DelayMaintenanceForm(request.POST)
        current_site = get_current_site(request)
        if form.is_valid():
            current_user = request.user
            pname = form.cleaned_data.get('printer_number').capitalize()

            fixed_update_required = Schedule.objects.filter(printer_number=pname, cancelled=False,
                                                            repair_status='Pending')

            if not fixed_update_required:
                messages.warning(request, 'Sorry, Printer {} has not been scheduled for maintenance! '
                                          'Perhaps it has been updated as fixed'.format(pname))
                return redirect('delay_maintenance_form')

            else:
                for update in fixed_update_required:
                    update.delay_maintenance_reason = form.cleaned_data.get('reason')
                    update.delay_maintenance_date = datetime.today()
                    update.save()
                    Event.objects.create(user_id=current_user.pk, action='Requested a maintenance delay for printer {}'.
                                         format(pname))
                    # if is_connected():
                    #     send_pending_email(user=current_user, current_site=current_site.domain,
                    #                        subject_heading='DELAY MAINTENANCE REQUEST',
                    #                        reason=update.delay_maintenance_reason)
                    messages.success(request, 'Request sent successfully to ADMIN!')
                    return redirect('delay_maintenance_form')

    else:
        form = DelayMaintenanceForm()
    return render(request, 'schedule/delay_maintenance_form.html', {'form': form})


# View printers under maintenance
@login_required(login_url='login')
def maintenance(request):
    schedules = Schedule.objects.order_by('-updated_at').filter(cancelled=False, repair_status='Pending')
    return render(request, "standard_account/schedules/maintenance.html", {'schedules': schedules})


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
    return render(request, "standard_account/schedules/fixed_printers.html",
                  {'schedules': schedules, 'title': title, 'date2': end_date, 'date': start_date})


# View cancelled schedules
@login_required(login_url='login')
def cancelled_schedules(request):
    schedules = Schedule.objects.filter(cancelled=True).order_by('-updated_at')
    for i in schedules:
        i.requested_by = User.objects.get(email=i.requested_by)
    return render(request, "standard_account/schedules/cancelled_schedules.html", {'schedules': schedules})


# View fixed but undelivered printers
@login_required(login_url='login')
def fixed_undelivered_printers(request):
    schedules = Schedule.objects.filter(cancelled=False, repair_status='Fixed', delivery_status='Pending').order_by(
        '-updated_at')
    return render(request, "standard_account/schedules/fixed_undelivered_printers.html", {'schedules': schedules})


# Update from maintenance list
@login_required(login_url='login')
def update_maintenance(request, pk):
    item = Schedule.objects.get(id=pk)
    form = UpdateScheduleFormU(instance=item)
    current_user = request.user

    if request.method == 'POST':
        form = UpdateScheduleFormU(request.POST, instance=item)
        if form.is_valid():
            form.save()
            Event.objects.create(user_id=current_user.pk, action='Updated printer {} maintenance schedule'.
                                 format(item.printer_number))
            messages.success(request,
                             'Printer {} maintenance schedule updated successfully!'.format(item.printer_number))
            return redirect('maintenance_u')
    return render(request, 'schedule/update_schedule.html', {'form': form})


# cancel from maintenance list
@login_required(login_url='login')
def cancel_maintenance(request, pk):
    item = Schedule.objects.get(id=pk)
    if request.method == 'POST':
        form = CancelMaintenanceForm(request.POST)
        if form.is_valid():
            current_user = request.user
            current_site = get_current_site(request)

            if item.action_status == 'Pending':
                messages.info(request,
                              'Cancellation request already sent and it awaits approval!'.format(item.printer_number))
                return redirect('maintenance_u')

            item.requested_by = str(current_user.email)
            item.action_status = 'Pending'
            item.date_cancelled = datetime.today()
            item.cancellation_reason = form.cleaned_data.get('cancellation_reason')
            item.save()
            Event.objects.create(user_id=current_user.pk,
                                 action='Requested printer {} maintenance schedule to be cancelled'.format(
                                     item.printer_number))
            if is_connected():
                send_pending_email(user=current_user, current_site=current_site.domain,
                                   subject_heading='CANCELLING SCHEDULE', reason=item.cancellation_reason)
                messages.success(request, 'Cancellation request sent successfully!'.format(item.printer_number))
                return redirect('maintenance_u')
            else:
                messages.success(request, 'Cancellation request sent successfully!'.format(item.printer_number))
                messages.info(request, 'Admin email notification failed; You are not connected to internet!')
                return redirect('maintenance_u')
    else:
        form = CancelMaintenanceForm()
    return render(request, 'standard_account/schedules/cancel_schedule.html', {'form': form})


# Available printer options
@login_required(login_url='login')
def printer_options(request):
    return render(request, "standard_account/printer_options.html")


# cancel with printer number
@login_required(login_url='login')
def cancel_schedule(request):
    if request.method == 'POST':
        form = CancelScheduleForm(request.POST)
        if form.is_valid():
            current_user = request.user
            current_site = get_current_site(request)
            pname = form.cleaned_data.get('printer_number').capitalize()

            fixed_update_required = Schedule.objects.filter(printer_number=pname, cancelled=False,
                                                            repair_status='Pending')
            existing_request = Schedule.objects.filter(cancelled=False, printer_number=pname, action_status='Pending')

            if not fixed_update_required:
                messages.warning(request, 'Sorry, Printer {} has not been scheduled for maintenance! '
                                          'Perhaps it has been updated as fixed'.format(pname))
                return redirect('cancel_schedule_u')
            elif existing_request:
                messages.info(request, 'Cancellation request already sent and it awaits approval!'.format(pname))
                return redirect('cancel_schedule_u')
            else:
                for update in fixed_update_required:
                    update.requested_by = str(current_user.email)
                    update.action_status = 'Pending'
                    update.date_cancelled = datetime.today()
                    update.cancellation_reason = form.cleaned_data.get('cancellation_reason')
                    update.save()
                    Event.objects.create(user_id=current_user.pk,
                                         action='Requested printer {} maintenance schedule to be cancelled'.format(
                                             update.printer_number))
                    if is_connected():
                        send_pending_email(user=current_user, current_site=current_site.domain,
                                           subject_heading='CANCELLING SCHEDULE', reason=update.cancellation_reason)
                        messages.success(request,
                                         'Cancellation request sent successfully!'.format(update.printer_number))
                        return redirect('cancel_schedule_u')
                    else:
                        messages.success(request, 'Cancellation request sent successfully!')
                        messages.info(request, 'Admin email notification failed; You are not connected to internet!')
                        return redirect('maintenance_u')
    else:
        form = CancelScheduleForm()
    return render(request, 'schedule/cancel_schedule.html', {'form': form})


# Waybill generation options
@login_required(login_url='login')
def waybill_options(request):
    return render(request, "waybill/user_waybill_options.html")


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
    return render(request, "standard_account/stock/parts.html", {'parts': plist, 'title': title})


# Add new part to our list of parts
@login_required(login_url='login')
def add_part(request):
    if request.method == 'POST':
        form = AddPartForm(request.POST)
        if form.is_valid():
            current_user = request.user
            current_site = get_current_site(request)
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
                    return redirect('add_part_u')
                elif existing_part:
                    if existing_part.action_status == 'Pending':
                        messages.warning(request, '{} request already sent, waiting for admins approval.'.format(
                            pname_not_added_value))
                        return redirect('add_part_u')
                    messages.warning(request, '{} already added and approved.'.format(pname_not_added_value))
                    return redirect('add_part_u')
                else:
                    Part.objects.create(user_id=current_user.pk, name=pname_not_added_value, action_status='Pending',
                                        requested_by=current_user.email)
                    PartStock.objects.create(name_id=Part.objects.get(name=pname_not_added_value).pk, topup=avn,
                                             action_status='Pending')
                    Event.objects.create(user_id=current_user.pk,
                                         action='Requested {} to be dded as a new part'.format(pname_not_added_value))
                    PartEvent.objects.create(user_id=current_user.pk,
                                             action='Requested {} to be dded as a new part'.format(
                                                 pname_not_added_value))
                    if is_connected():
                        send_pending_email(user=current_user, current_site=current_site.domain,
                                           subject_heading='ADDING PART', reason='Needs approval')
                        messages.success(request,
                                         'Request for {} to be added successfully sent to ADMIN for approval!'.format(
                                             pname_not_added_value))
                        return redirect('add_part_u')
                    else:
                        messages.success(request,
                                         'Request for {} to be added successfully sent to ADMIN for approval!'.format(
                                             pname_not_added_value))
                        messages.info(request, 'Admin email notification failed; You are not connected to internet!')
                        return redirect('add_part_u')
            else:
                try:
                    existing_name = Part.objects.get(name=pname)
                except (TypeError, ValueError, OverflowError, Part.DoesNotExist):
                    existing_name = None
                if existing_name:
                    if existing_name.action_status == 'Pending':
                        messages.warning(request, '{} request already sent, waiting for admins approval.'.format(pname))
                        return redirect('add_part_u')
                    messages.warning(request, '{} already added and approved.'.format(pname))
                    return redirect('add_part_u')
                else:
                    Part.objects.create(user_id=current_user.pk, name=pname, action_status='Pending',
                                        requested_by=current_user.email)
                    PartStock.objects.create(name_id=Part.objects.get(name=pname).pk, topup=avn,
                                             action_status='Pending')
                    Event.objects.create(user_id=current_user.pk,
                                         action='Requested {} to be dded as a new part'.format(pname))
                    PartEvent.objects.create(user_id=current_user.pk,
                                             action='Requested {} to be dded as a new part'.format(pname))
                    if is_connected():
                        send_pending_email(user=current_user, current_site=current_site.domain,
                                           subject_heading='ADDING PART', reason='Needs approval')
                        messages.success(request,
                                         'Request for {} to be added successfully sent to ADMIN for approval!'.format(
                                             pname))
                        return redirect('add_part_u')
                    else:
                        messages.success(request,
                                         'Request for {} to be added successfully sent to ADMIN for approval!'.format(
                                             pname))
                        messages.info(request, 'Admin email notification failed; You are not connected to internet!')
                        return redirect('add_part_u')
    else:
        form = AddPartForm()
    return render(request, 'stock/add_part.html', {'form': form})


# Part managements options for user
@login_required(login_url='login')
def part_management_options(request):
    return render(request, "standard_account/stock/part_management_options.html")


# Part managements options for procurement
@login_required(login_url='login')
def stock_options(request):
    return render(request, "finance/stock/stock_options.html")


# user profile
@login_required(login_url='login')
def user_ratings(request, type):
    def avg_rating(r, s):
        if r == 0:
            return 0
        else:
            avg = r / s
            avg1 = avg + 0.1
            dp = avg - int(avg)  # decimal points
            if dp < 0.55:
                return str(avg)[:3]
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
    qrst = UserRating.objects.filter(user=request.user.pk).order_by('-date')
    ratings = []
    if type == 'repair':
        for i in qrst:
            if i.rating_type == 'Repairs' or i.rating_type == 'Helpdesk':
                ratings.append(i)
    else:
        for i in qrst:
            if i.rating_type == 'Training':
                ratings.append(i)
    scores = len(ratings)
    total_ratings = 0
    for i in ratings:
        total_ratings += i.rating  # ratings
        i.rating = f'{i.rating}/5'
    star = float(avg_rating(r=total_ratings, s=scores))

    data = {'ratings': ratings,
            'user': request.user,
            'avg_rating': star,
            'remark': remark(star),
            'type': type
            }

    return render(request, "users/ratings/user_ratings.html", data)


# Update profile image
def update_profile(request):
    user = User.objects.get(id=request.user.pk)
    if request.method == 'POST':
        form = ImageProfileForm(request.POST, request.FILES)
        if form.is_valid():
            image = request.FILES['image']
            if user.image:
                user.image.delete()
                user.image.save(f'{image.name[:3]}-{user.first_name}-{user.pk}', image)
                Event.objects.create(user_id=request.user.pk, action='Updated profile picture')
            else:
                user.image.save(f'{user.first_name}-{user.pk}', image)
                Event.objects.create(user_id=request.user.pk, action='Updated profile picture')
            return redirect('repair_profile')
    else:
        form = ImageProfileForm()
    return render(request, 'users/ratings/update_profile.html', {'form': form})


# Update profile
def update_user_profile(request):
    current_user = request.user
    user = User.objects.get(id=current_user.pk)
    form = UpdateProfileForm(instance=user)

    if request.method == 'POST':
        form = UpdateProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            Event.objects.create(user_id=current_user.pk, action='Updated profile')
            # messages.success(request, 'Profile updated successfully!')
            return redirect('repair_profile')
    return render(request, 'users/update_profile.html', {'form': form})


def repair_profile(request):
    current_user = request.user

    def avg_rating(r, s):
        if r == 0:
            return 0
        else:
            avg = r / s
            avg1 = avg + 0.1
            dp = avg - int(avg)  # decimal points
            if dp < 0.55:
                return str(avg)[:3]
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

    qrst = UserRating.objects.filter(user=request.user.pk)
    ratings = []
    for i in qrst:
        if i.rating_type == 'Repairs' or i.rating_type == 'Helpdesk':
            ratings.append(i)
    scores = len(ratings)
    total_ratings = 0
    for i in ratings:
        total_ratings += i.rating  # ratings
        i.rating = f'{i.rating}/5'
    star = float(avg_rating(r=total_ratings, s=scores))

    data = {'ratings': ratings,
            'user': current_user,
            'avg_rating': star,
            'remark': remark(star),
            'no_of_rating': scores,
            'type': 'repair'
            }
    return render(request, 'users/ratings/repair_profile.html', data)


def training_profile(request):
    current_user = request.user

    def avg_rating(r, s):
        if r == 0:
            return 0
        else:
            avg = r / s
            avg1 = avg + 0.1
            dp = avg - int(avg)  # decimal points
            if dp < 0.55:
                return str(avg)[:3]
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

    qrst = UserRating.objects.filter(user=request.user.pk)
    ratings = []
    for i in qrst:
        if i.rating_type == 'Training':
            ratings.append(i)
    scores = len(ratings)
    total_ratings = 0
    for i in ratings:
        total_ratings += i.rating  # ratings
        i.rating = f'{i.rating}/5'
    star = float(avg_rating(r=total_ratings, s=scores))

    data = {'ratings': ratings,
            'user': current_user,
            'avg_rating': star,
            'remark': remark(star),
            'no_of_rating': scores,
            'type': 'training'
            }
    return render(request, 'users/ratings/training_profile.html', data)


# HelpDesk options
@login_required(login_url='login')
def helpdesk_options(request):
    return render(request, 'helpdesk/user_helpdesk_options.html')


# Fill HelpDesk form
@login_required(login_url='login')
def helpdesk_form(request):
    if request.method == 'POST':
        form = HelpDeskForm(request.POST)
        if form.is_valid():
            user = request.user
            issue = form.cleaned_data.get('issue_category')
            desc = form.cleaned_data.get('description')
            Event.objects.create(user_id=request.user.pk, action='Booked a new helpdesk ticket')
            HelpDesk.objects.create(reporter_id=user.pk, issue=issue, description=desc)
            current_site = get_current_site(request)
            subject = "MARGINS GROUP PRINTER SUPPORT TECHNICAL TEAM"
            message = render_to_string('helpdesk/helpdesk_ticket_email.html', {
                'user': user,
                'issue': issue,
                'current_user': request.user,
                'domain': current_site.domain,
            })
            recipient = []
            admins = User.objects.filter(is_staff=True)
            for i in admins:
                recipient.append(i.email)

            if is_connected():
                send_mail(subject, message, EMAIL_HOST_USER, recipient, fail_silently=False)
                messages.info(request, "You'll shortly be attended to.")
                return redirect('helpdesk_form')
            else:
                messages.warning(request,
                                 f"Failed to notify admin by mail due to no internet access "
                                 f"but you'll still be attended to shortly")
                return redirect('helpdesk_form')
    else:
        form = HelpDeskForm()
    return render(request, 'helpdesk/helpdesk_form.html', {'form': form})


# View helpdesk tickets
@login_required(login_url='login')
def tickets(request):
    tickets = HelpDesk.objects.filter(reporter_id=request.user.pk).order_by('-created_at')
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
    return render(request, "helpdesk/user_tickets.html", {'tickets': tickets})


# Confirm ticket as fixed
@login_required(login_url='login')
def confirm_ticket_status(request, pk):
    item = HelpDesk.objects.get(id=pk)
    current_user = request.user
    if request.method == 'POST':
        if item.fix_status == 'Pending':
            messages.warning(request, 'Ticket is still pending!')
            return redirect('tickets_u')
        elif item.fix_confirmation == 'Confirmed':
            messages.info(request, 'Ticket status already confirmed!')
            return redirect('tickets_u')
        elif not is_connected():
            messages.warning(request, 'No internet connection! Check and retry.')
            return redirect('tickets_u')
        item.fix_confirmation = 'Confirmed'
        item.save()
        current_site = get_current_site(request)
        subject = "RATINGS REQUEST - MARGINS ID SYSTEM"
        recipients = [current_user.email]
        message = render_to_string('users/ratings/admin_rating_request_email.html', {
            'training': item,
            'recipient': current_user,
            'user': User.objects.get(id=item.fixed_by),
            'domain': current_site.domain,
            'uid': urlsafe_base64_encode(force_bytes(item.fixed_by)),
            'tid': urlsafe_base64_encode(force_bytes(item.pk)),
        })
        send_mail(subject, message, EMAIL_HOST_USER, recipients, fail_silently=False)
        Event.objects.create(user_id=current_user.pk, action="Confirmed helpdesk ticket as fixed")
        messages.success(request, 'Ticket status confirmed as fixed successfully!')
        return redirect('tickets_u')
    return render(request, 'helpdesk/confirm_ticket_fixed-prompt.html', {'item': item, 'name': User.objects.get(id=item.fixed_by)})


# Rate admin
def rate_admin(request, uid, tid):
    invalid = False
    try:
        uid1 = force_text(urlsafe_base64_decode(uid))
        tid1 = force_text(urlsafe_base64_decode(tid))
        user = User.objects.get(pk=uid1)
        rate = HelpDesk.objects.get(pk=tid1)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist, HelpDesk.DoesNotExist):
        invalid = True

    if invalid:
        messages.warning(request, 'Invalid link')
        return redirect('login')

    elif request.method == 'POST':
        form = RateAdminForm(request.POST)
        if form.is_valid():
            r = request.POST['rating']
            com = form.cleaned_data.get('comment')

            ready = HelpDesk.objects.filter(fixed_by=uid1, ready_rate=True)
            if not ready:
                messages.warning(request, '{} has already been rated or has not fixed any ticket yet!'.format(user))
                return redirect('login')
            UserRating.objects.create(rating_type='Helpdesk', rating=r, rater=request.user.pk,
                                      date=datetime.today().date(), comment=com, user=uid1)
            # to prevent being rated on the same ticket more than once
            for i in ready:
                i.ready_rate = False
                i.save()
            messages.success(request, 'Thanks for rating {}.'.format(user))
            return redirect('login')
    else:
        form = RateAdminForm()
    return render(request, 'helpdesk/rate_admin.html',
                  {'form': form, 'uid': uid, 'tid': tid, 'user': user, 'rate': rate})


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid:
            pn = request.POST['phone']
            email = request.POST['email']
            name = request.POST['name']
            msg = request.POST['message']
            subject = "ENQUIRIES - MARGINS GROUP PRINTER SUPPORT"
            recipients = []
            admins = User.objects.filter(is_staff=True)
            for i in admins:
                recipients.append(i.email)

            message = render_to_string('contact_email.html', {
                'email': email,
                'phone': pn,
                'name': name,
                'message': msg,
            })

            if is_connected():
                send_mail(subject, message, EMAIL_HOST_USER, recipients, fail_silently=False)
                messages.success(request, "Message sent successfully! You'll be contacted shortly!")
                return redirect('contact')
            else:
                messages.warning(request, 'Sorry, failed to send message. '
                                          'Check your internet connection and retry.')
                return redirect('contact')
    else:
        form = ContactForm()
    return render(request, 'contact.html', {'form': form})


# Rate a user on training
def training_rate(request, uid, tid, rid):
    invalid = False
    try:
        uid1 = force_text(urlsafe_base64_decode(uid))
        tid1 = force_text(urlsafe_base64_decode(tid))
        rid1 = force_text(urlsafe_base64_decode(rid))
        user = User.objects.get(pk=uid1)
        rate = Training.objects.get(pk=tid1)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist, Training.DoesNotExist):
        invalid = True

    if invalid:
        messages.warning(request, 'Invalid link')
        return redirect('login')

    elif request.method == 'POST':
        form = RateTrainingForm(request.POST)
        if form.is_valid():
            r = request.POST['rating']
            com = form.cleaned_data.get('comment')
            topics = form.cleaned_data.get('topics')
            slides = form.cleaned_data.get('slides')
            duration = form.cleaned_data.get('duration')
            solution = form.cleaned_data.get('solution')
            style = form.cleaned_data.get('style')
            q_response = form.cleaned_data.get('q_response')
            location = form.cleaned_data.get('location')
            config_install = form.cleaned_data.get('config_install')
            training_benefit = form.cleaned_data.get('training_benefit')
            recommend = form.cleaned_data.get('recommend')
            # stem = form.cleaned_data.get('stem')
            # art = form.cleaned_data.get('art')
            # time = form.cleaned_data.get('time')
            # cctv = form.cleaned_data.get('cctv')
            # loyalty = form.cleaned_data.get('loyalty')
            existing_rate = UserRating.objects.filter(training=rate, user=uid1, rater=rid1)
            if existing_rate:
                messages.warning(request, '{} has already been rated!'.format(user))
                return redirect('login')
            UserRating.objects.create(training=rate, user=uid1, rater=rid1, rating_type='Training', rating=r,
                                      comment=com, date=datetime.today().date(), topics=topics, slides=slides,
                                      duration=duration, solution=solution, style=style, q_response=q_response,
                                      training_benefit=training_benefit, recommend=recommend, location=location,
                                      config_install=config_install)
            messages.warning(request, 'Thanks for rating {}.'.format(user))
            return redirect('login')
    else:
        form = RateTrainingForm()
    return render(request, 'training/rate_user_training.html',
                  {'form': form, 'uid': uid, 'tid': tid, 'rid': rid, 'user': user, 'rate': rate})


# Rate a user on maintenance
def maintenance_rate(request, uid, tid):
    invalid = False
    try:
        uid1 = force_text(urlsafe_base64_decode(uid))
        tid1 = force_text(urlsafe_base64_decode(tid))
        user = User.objects.get(pk=uid1)
        rate = Maintenance.objects.get(pk=tid1)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist, Training.DoesNotExist):
        invalid = True

    if invalid:
        messages.warning(request, 'Invalid link')
        return redirect('login')

    elif request.method == 'POST':
        form = RateAdminForm(request.POST)
        if form.is_valid():
            r = request.POST['rating']
            com = form.cleaned_data.get('comment')
            existing_rate = UserRating.objects.filter(maintenance=rate, user=uid1)
            if existing_rate:
                messages.warning(request, '{} has already been rated!'.format(user))
                return redirect('login')
            UserRating.objects.create(maintenance=rate, user=uid1, rating_type='Repairs', rating=r,
                                      comment=com, date=datetime.today().date())
            messages.warning(request, 'Thanks for rating {}.'.format(user))
            return redirect('login')
    else:
        form = RateAdminForm()
    return render(request, 'maintenance/rate_user_maintenance.html',
                  {'form': form, 'uid': uid, 'tid': tid, 'user': user, 'rate': rate})


# View user trainings
@login_required(login_url='login')
def user_trainings(request):
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
    return render(request, "training/user_trainings.html", {'trainings': qrt})


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
    return render(request, "maintenance/client_maintenance_user.html", {'maintenances': clist})


# Laminator options
@login_required(login_url='login')
def laminator_options(request):
    return render(request, "laminator/laminator_options_user.html")


@login_required(login_url='login')
def schedule_laminator(request):
    if request.method == 'POST':
        form = ScheduleLaminatorFormU(request.POST)
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
                if not purchased:
                    Laminator.objects.create(user=current_user, printer_number=pname, box_number=bname, client_id=cid)
                LaminatorSchedule.objects.create(user_id=uid, box_number=bname, client_id=cid, laminator_number=pname,
                                                 pickup_parts=pparts, pickup_date=pdate, problem=p, other_problem=p1)
                Event.objects.create(user_id=current_user.pk, action=f'Scheduled laminator {pname} for maintenance')
                messages.success(request, 'laminator {} scheduled for maintenance successfully!'.format(pname))
                return redirect('schedule_laminator_u')
    else:
        form = ScheduleLaminatorFormU()
    return render(request, 'laminator/schedule_laminator.html', {'form': form})


# cancel with laminator number
@login_required(login_url='login')
def cancel_laminator_schedule(request):
    if request.method == 'POST':
        form = CancelLaminatorScheduleForm(request.POST)
        if form.is_valid():
            current_user = request.user
            current_site = get_current_site(request)
            pname = form.cleaned_data.get('laminator_number').capitalize()

            fixed_update_required = LaminatorSchedule.objects.filter(laminator_number=pname, cancelled=False,
                                                                     repair_status='Pending')
            existing_request = LaminatorSchedule.objects.filter(cancelled=False, laminator_number=pname, action_status='Pending')

            if not fixed_update_required:
                messages.warning(request, 'Sorry, Laminator {} has not been scheduled for maintenance! '
                                          'Perhaps it has been updated as fixed'.format(pname))
                return redirect('cancel_laminator_u')
            elif existing_request:
                messages.info(request, 'Cancellation request already sent and it awaits approval!'.format(pname))
                return redirect('cancel_laminator_u')
            else:
                for update in fixed_update_required:
                    update.requested_by = current_user.pk
                    update.action_status = 'Pending'
                    update.date_cancelled = datetime.today().date()
                    update.cancellation_reason = form.cleaned_data.get('cancellation_reason')
                    update.save()
                    Event.objects.create(user_id=current_user.pk,
                                         action=f'Requested laminator {pname} maintenance schedule to be cancelled')
                    if is_connected():
                        send_pending_email(user=current_user, current_site=current_site.domain,
                                           subject_heading='CANCELLING SCHEDULE', reason=update.cancellation_reason)
                        messages.success(request,
                                         'Cancellation request sent successfully!'.format(update.laminator_number))
                        return redirect('cancel_laminator_u')
                    else:
                        messages.success(request, 'Cancellation request sent successfully!')
                        messages.info(request, 'Admin email notification failed; You are not connected to internet!')
                        return redirect('cancel_laminator_u')
    else:
        form = CancelLaminatorScheduleForm()
    return render(request, 'schedule/cancel_schedule.html', {'form': form})


# View laminators under maintenance
@login_required(login_url='login')
def pending_laminators(request):
    schedules = LaminatorSchedule.objects.order_by('-updated_at').filter(cancelled=False, repair_status='Pending')
    for i in schedules:
        i.problem = i.problem + ', ' + i.other_problem
    return render(request, "laminator/pending_laminators_user.html", {'schedules': schedules})


# Update from maintenance list
@login_required(login_url='login')
def update_pending_laminator(request, pk):
    item = LaminatorSchedule.objects.get(id=pk)
    form = UpdatePendingFormU(instance=item)
    current_user = request.user

    if request.method == 'POST':
        form = UpdatePendingFormU(request.POST, instance=item)
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
            current_site = get_current_site(request)

            if item.action_status == 'Pending':
                messages.info(request,
                              'Cancellation request already sent and it awaits approval!'.format(item.laminator_number))
                return redirect('pending_laminators_u')

            item.requested_by = current_user.pk
            item.action_status = 'Pending'
            item.date_cancelled = datetime.today().date()
            item.cancellation_reason = form.cleaned_data.get('cancellation_reason')
            item.save()
            Event.objects.create(user_id=current_user.pk,
                                 action='Requested laminator {} maintenance schedule to be cancelled'.format(
                                     item.laminator_number))
            if is_connected():
                send_pending_email(user=current_user, current_site=current_site.domain,
                                   subject_heading='CANCELLING SCHEDULE', reason=item.cancellation_reason)
                messages.success(request, 'Cancellation request sent successfully!'.format(item.laminator_number))
                return redirect('pending_laminators_u')
            else:
                messages.success(request, 'Cancellation request sent successfully!'.format(item.laminator_number))
                messages.info(request, 'Admin email notification failed; You are not connected to internet!')
                return redirect('pending_laminators_u')
    else:
        form = CancelMaintenanceForm()
    return render(request, 'standard_account/schedules/cancel_schedule.html', {'form': form})


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
        schedules = Schedule.objects.filter(cancelled=False, repair_status='Fixed', date_repaired__gte=start_date,
                                            date_repaired__lte=end_date)
        for i in schedules:
            i.fixed_by = User.objects.get(id=i.fixed_by)
            i.problem = i.problem + ', ' + i.other_problem
    return render(request, "laminator/fixed_laminators_user.html",
                  {'schedules': schedules, 'title': title, 'date2': end_date, 'date': start_date})


# mrw options
@login_required(login_url='login')
def mrw_options(request):
    return render(request, "mrw/mrw_options_user.html")


@login_required(login_url='login')
def schedule_mrw(request):
    if request.method == 'POST':
        form = ScheduleMRWFormU(request.POST)
        if form.is_valid():
            current_user = request.user
            pname = form.cleaned_data.get('mrw_number').upper()
            pparts = form.cleaned_data.get('pickup_parts')
            cname = (form.cleaned_data.get('client'))
            pdate = form.cleaned_data.get('pickup_date')
            p = form.cleaned_data.get('problem')
            cid = Client.objects.get(client_name=cname).pk
            uid = current_user.pk
            purchased = MRW.objects.filter(mrw_number=pname)

            try:
                # Query validations on schedule
                fixed_update_required = MRWSchedule.objects.filter(mrw_number=pname, cancelled=False, repair_status='Pending')

            except (TypeError, ValueError, OverflowError):
                existing_printer = None

            if fixed_update_required:
                # prompt user schedule already exist and redirect to update fixed status
                messages.warning(request, 'MRW {} schedule needs repair status update'.format(pname))
                return redirect('mrw_update')
            else:
                if not purchased:
                    MRW.objects.create(user=current_user, printer_number=pname, client_id=cid)
                MRWSchedule.objects.create(user_id=uid, client_id=cid, mrw_number=pname, pickup_parts=pparts,
                                           pickup_date=pdate, problem=p)
                Event.objects.create(user_id=current_user.pk, action=f'Scheduled MRW {pname} for maintenance')
                messages.success(request, 'MRW {} scheduled for maintenance successfully!'.format(pname))
                return redirect('schedule_mrw_u')
    else:
        form = ScheduleMRWFormU()
    return render(request, 'mrw/schedule_mrw.html', {'form': form})


# cancel with laminator number
@login_required(login_url='login')
def cancel_mrw_schedule(request):
    if request.method == 'POST':
        form = CancelMRWScheduleForm(request.POST)
        if form.is_valid():
            current_user = request.user
            current_site = get_current_site(request)
            pname = form.cleaned_data.get('mrw_number').capitalize()

            fixed_update_required = MRWSchedule.objects.filter(mrw_number=pname, cancelled=False, repair_status='Pending')
            existing_request = LaminatorSchedule.objects.filter(cancelled=False, mrw_number=pname, action_status='Pending')

            if not fixed_update_required:
                messages.warning(request, 'Sorry, MRW {} has not been scheduled for maintenance! '
                                          'Perhaps it has been updated as fixed'.format(pname))
                return redirect('cancel_mrw_u')
            elif existing_request:
                messages.info(request, 'Cancellation request already sent and it awaits approval!'.format(pname))
                return redirect('cancel_mrw_u')
            else:
                for update in fixed_update_required:
                    update.requested_by = current_user.pk
                    update.action_status = 'Pending'
                    update.date_cancelled = datetime.today().date()
                    update.cancellation_reason = form.cleaned_data.get('cancellation_reason')
                    update.save()
                    Event.objects.create(user_id=current_user.pk,
                                         action=f'Requested MRW {pname} maintenance schedule to be cancelled')
                    if is_connected():
                        send_pending_email(user=current_user, current_site=current_site.domain,
                                           subject_heading='CANCELLING SCHEDULE', reason=update.cancellation_reason)
                        messages.success(request,
                                         'Cancellation request sent successfully!'.format(update.mrw_number))
                        return redirect('cancel_mrw_u')
                    else:
                        messages.success(request, 'Cancellation request sent successfully!')
                        messages.info(request, 'Admin email notification failed; You are not connected to internet!')
                        return redirect('cancel_mrw_u')
    else:
        form = CancelMRWScheduleForm()
    return render(request, 'schedule/cancel_schedule.html', {'form': form})


# View mrws under maintenance
@login_required(login_url='login')
def pending_mrws(request):
    schedules = MRWSchedule.objects.order_by('-updated_at').filter(cancelled=False, repair_status='Pending')
    return render(request, "mrw/pending_mrws_user.html", {'schedules': schedules})


# Update from maintenance list
@login_required(login_url='login')
def update_pending_mrw(request, pk):
    item = MRWSchedule.objects.get(id=pk)
    form = UpdateMRWPendingFormU(instance=item)
    current_user = request.user

    if request.method == 'POST':
        form = UpdateMRWPendingFormU(request.POST, instance=item)
        if form.is_valid():
            form.save()
            Event.objects.create(user_id=current_user.pk, action='Updated MRW {} maintenance schedule'.
                                 format(item.mrw_number))
            messages.success(request,
                             'MRW {} maintenance schedule updated successfully!'.format(item.mrw_number))
            return redirect('pending_mrw_u')
    return render(request, 'schedule/update_schedule.html', {'form': form})


# cancel from maintenance list
@login_required(login_url='login')
def cancel_pending_mrw(request, pk):
    item = MRWSchedule.objects.get(id=pk)
    if request.method == 'POST':
        form = CancelMaintenanceForm(request.POST)
        if form.is_valid():
            current_user = request.user
            current_site = get_current_site(request)

            if item.action_status == 'Pending':
                messages.info(request,
                              'Cancellation request already sent and it awaits approval!'.format(item.mrw_number))
                return redirect('pending_mrws_u')

            item.requested_by = current_user.pk
            item.action_status = 'Pending'
            item.date_cancelled = datetime.today().date()
            item.cancellation_reason = form.cleaned_data.get('cancellation_reason')
            item.save()
            Event.objects.create(user_id=current_user.pk,
                                 action='Requested MRW {} maintenance schedule to be cancelled'.format(item.mrw_number))
            if is_connected():
                send_pending_email(user=current_user, current_site=current_site.domain,
                                   subject_heading='CANCELLING SCHEDULE', reason=item.cancellation_reason)
                messages.success(request, 'Cancellation request sent successfully!'.format(item.mrw_number))
                return redirect('pending_mrws_u')
            else:
                messages.success(request, 'Cancellation request sent successfully!'.format(item.mrw_number))
                messages.info(request, 'Admin email notification failed; You are not connected to internet!')
                return redirect('pending_mrws_u')
    else:
        form = CancelMaintenanceForm()
    return render(request, 'standard_account/schedules/cancel_schedule.html', {'form': form})


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
    return render(request, "mrw/fixed_mrws_user.html",
                  {'schedules': schedules, 'title': title, 'date2': end_date, 'date': start_date})


# iss options
@login_required(login_url='login')
def iss_options(request):
    return render(request, "iss/iss_options_user.html")


@login_required(login_url='login')
def schedule_iss(request):
    if request.method == 'POST':
        form = ScheduleISSFormU(request.POST)
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
            cid = Client.objects.get(client_name=cname).pk
            uid = current_user.pk
            purchased = MRW.objects.filter(iss_number=pname)

            try:
                # Query validations on schedule
                fixed_update_required = ISSSchedule.objects.filter(iss_number=pname, cancelled=False, repair_status='Pending')

            except (TypeError, ValueError, OverflowError):
                existing_printer = None

            if fixed_update_required:
                # prompt user schedule already exist and redirect to update fixed status
                messages.warning(request, 'ISS {} schedule needs repair status update'.format(pname))
                return redirect('iss_update')
            else:
                if not purchased:
                    ISS.objects.create(user=current_user, iss_number=pname, client_id=cid)
                ISSSchedule.objects.create(user_id=uid, client_id=cid, iss_number=pname, pickup_parts=pparts,
                                           pickup_date=pdate, problem=p)
                Event.objects.create(user_id=current_user.pk, action=f'Scheduled ISS {pname} for maintenance')
                messages.success(request, 'ISS {} scheduled for maintenance successfully!'.format(pname))
                return redirect('schedule_iss_u')
    else:
        form = ScheduleISSFormU()
    return render(request, 'iss/schedule_iss.html', {'form': form})


# cancel with iss number
@login_required(login_url='login')
def cancel_iss_schedule(request):
    if request.method == 'POST':
        form = CancelISSScheduleForm(request.POST)
        if form.is_valid():
            current_user = request.user
            current_site = get_current_site(request)
            pname = form.cleaned_data.get('iss_number').capitalize()

            fixed_update_required = ISSSchedule.objects.filter(iss_number=pname, cancelled=False, repair_status='Pending')
            existing_request = LaminatorSchedule.objects.filter(cancelled=False, iss_number=pname, action_status='Pending')

            if not fixed_update_required:
                messages.warning(request, 'Sorry, ISS {} has not been scheduled for maintenance! '
                                          'Perhaps it has been updated as fixed'.format(pname))
                return redirect('cancel_iss_u')
            elif existing_request:
                messages.info(request, 'Cancellation request already sent and it awaits approval!'.format(pname))
                return redirect('cancel_iss_u')
            else:
                for update in fixed_update_required:
                    update.requested_by = current_user.pk
                    update.action_status = 'Pending'
                    update.date_cancelled = datetime.today().date()
                    update.cancellation_reason = form.cleaned_data.get('cancellation_reason')
                    update.save()
                    Event.objects.create(user_id=current_user.pk,
                                         action=f'Requested ISS {pname} maintenance schedule to be cancelled')
                    if is_connected():
                        send_pending_email(user=current_user, current_site=current_site.domain,
                                           subject_heading='CANCELLING SCHEDULE', reason=update.cancellation_reason)
                        messages.success(request,
                                         'Cancellation request sent successfully!'.format(update.iss_number))
                        return redirect('cancel_iss_u')
                    else:
                        messages.success(request, 'Cancellation request sent successfully!')
                        messages.info(request, 'Admin email notification failed; You are not connected to internet!')
                        return redirect('cancel_iss_u')
    else:
        form = CancelISSScheduleForm()
    return render(request, 'schedule/cancel_schedule.html', {'form': form})


# View iss under maintenance
@login_required(login_url='login')
def pending_iss(request):
    schedules = ISSSchedule.objects.order_by('-updated_at').filter(cancelled=False, repair_status='Pending')
    return render(request, "iss/pending_iss_user.html", {'schedules': schedules})


# Update from maintenance list
@login_required(login_url='login')
def update_pending_iss(request, pk):
    item = ISSSchedule.objects.get(id=pk)
    form = UpdateISSPendingFormU(instance=item)
    current_user = request.user

    if request.method == 'POST':
        form = UpdateISSPendingFormU(request.POST, instance=item)
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
            current_site = get_current_site(request)

            if item.action_status == 'Pending':
                messages.info(request,
                              'Cancellation request already sent and it awaits approval!'.format(item.iss_number))
                return redirect('pending_iss_u')

            item.requested_by = current_user.pk
            item.action_status = 'Pending'
            item.date_cancelled = datetime.today().date()
            item.cancellation_reason = form.cleaned_data.get('cancellation_reason')
            item.save()
            Event.objects.create(user_id=current_user.pk,
                                 action='Requested ISS {} maintenance schedule to be cancelled'.format(item.iss_number))
            if is_connected():
                send_pending_email(user=current_user, current_site=current_site.domain,
                                   subject_heading='CANCELLING SCHEDULE', reason=item.cancellation_reason)
                messages.success(request, 'Cancellation request sent successfully!'.format(item.iss_number))
                return redirect('pending_iss_u')
            else:
                messages.success(request, 'Cancellation request sent successfully!'.format(item.iss_number))
                messages.info(request, 'Admin email notification failed; You are not connected to internet!')
                return redirect('pending_iss_u')
    else:
        form = CancelMaintenanceForm()
    return render(request, 'standard_account/schedules/cancel_schedule.html', {'form': form})


# View fixed iss
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
    return render(request, "iss/fixed_iss_user.html",
                  {'schedules': schedules, 'title': title, 'date2': end_date, 'date': start_date})
