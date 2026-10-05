from django.urls import path

from employee import views

urlpatterns = [
    path("set-password/<uidb64>/<token>/",views.set_password,name="set-password"),
    # path("dashboard/",views.employee_dashboard,name="employee_dashboard"),
path(
        "set-password/<uidb64>/<token>/",
        views.set_password,
        name="set_password"
    ),
path("dashboard/",views.employee_dashboard,name="employee_dashboard"),
path("profile/",views.employee_profile,name="my_profile"),
path("apply_leave/",views.apply_leave,name="apply_leave"),
path("my_leaves/",views.my_leaves,name="my_leaves"),
path("my-payslips/",views.my_payslips,name="my_payslips"),
path("leave-calendar/",views.leave_calendar,name="leave_calendar"),
path(
    "settings/",
    views.employee_settings,
    name="employee_settings"
),

path(
    "settings/password/",
    views.employee_change_password,
    name="employee_change_password"
),
]