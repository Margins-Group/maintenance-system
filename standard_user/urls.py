from django.urls import path
from . import views

urlpatterns = [
    path('helpdesk', views.helpdesk_options, name='helpdesk_u'),
    path('helpdesk/form', views.helpdesk_form, name='helpdesk_form'),
    path('helpdesk/tickets', views.tickets, name="tickets_u"),
    path('contact', views.contact, name="contact"),
    path('schedule/request/delay/maintenance', views.delay_maintenance, name="delay_maintenance_form"),
    path('managements/', views.user_management, name="user_management_u"),
    path('history/', views.event, name="user_event"),
    path('client/add', views.add_client, name="add_client_u"),
    path('report/client/printers', views.client_report, name="client_report_u"),
    path('report/options', views.reports, name="reports_u"),
    path('report/maintenance', views.maintenance, name="maintenance_u"),
    path('reports/fixed/printers', views.fixed_printers, name="fixed_printers_u"),
    path('reports/fixed/not_delivered', views.fixed_undelivered_printers, name="fixed_undelivered_printers_u"),
    path('cancelled_schedules', views.cancelled_schedules, name="cancelled_schedules_u"),
    path('report/printer/options', views.printer_options, name="printer_options_u"),
    path('waybill/options', views.waybill_options, name="waybill_options_u"),
    path('schedule/cancel', views.cancel_schedule, name="cancel_schedule_u"),
    path('stock/repairshop/parts/management', views.part_management_options, name="part_options_u"),
    path('stock/parts/options', views.stock_options, name="stock_options"),
    path('report/stock/repairshop/parts', views.parts, name="parts_u"),
    path('stock/part/add', views.add_part, name="add_part_u"),
    path('rate_admin/<uid>/<tid>', views.rate_admin, name="rate_admin"),
    path('trainings', views.user_trainings, name="user_trainings"),
    path('profile/image/update', views.update_profile, name="update_image"),
    path('profile/update', views.update_user_profile, name="update_profile"),
    path('profile/repairs', views.repair_profile, name="repair_profile"),
    path('profile/trainings', views.training_profile, name="training_profile"),
    path('client/maintenances', views.client_maintenance, name='client_maintenance_u'),

    # laminator urls
    path('laminator/options', views.laminator_options, name="laminator_options_u"),
    path('schedule/new/laminator', views.schedule_laminator, name="schedule_laminator_u"),
    path('cancel/laminator/schedule', views.cancel_laminator_schedule, name="cancel_laminator_u"),
    path('report/pending/laminators', views.pending_laminators, name="pending_laminators_u"),
    path('reports/fixed/laminators', views.fixed_laminators, name="fixed_laminators_u"),

    # mrw urls
    path('mrw/options', views.mrw_options, name="mrw_options_u"),
    path('schedule/new/mrw', views.schedule_mrw, name="schedule_mrw_u"),
    path('cancel/mrw/schedule', views.cancel_mrw_schedule, name="cancel_mrw_u"),
    path('report/pending/mrws', views.pending_mrws, name="pending_mrws_u"),
    path('reports/fixed/mrws', views.fixed_mrws, name="fixed_mrws_u"),

    # iss urls
    path('iss/options', views.iss_options, name="iss_options_u"),
    path('schedule/new/iss', views.schedule_iss, name="schedule_iss_u"),
    path('cancel/iss/schedule', views.cancel_iss_schedule, name="cancel_iss_u"),
    path('report/pending/iss', views.pending_iss, name="pending_iss_u"),
    path('reports/fixed/iss', views.fixed_iss, name="fixed_iss_u"),
]
