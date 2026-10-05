
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.cache import never_cache
from django.http import HttpResponse, JsonResponse
from hr.models import Employee, Leave
from hr.models import Department, Designation, Payroll
from django.contrib import messages
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from decimal import Decimal
from django.db.models import Count, IntegerField
from django.db.models.functions import Cast

# =========================================================
# LOGIN
# =========================================================

def login_view(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)

            if Employee.objects.filter(user=user).exists():
                return redirect("employee_dashboard")

            return redirect("dashboard")

        return render(
            request,
            "login.html",
            {"error": "Invalid username or password"}
        )

    return render(request, "login.html")


# =========================================================
# DASHBOARD
# =========================================================

@login_required
@never_cache
def dashboard(request):

    return render(
        request,
        "dashboard.html"
    )


# =========================================================
# LOGOUT
# =========================================================

def logout_view(request):

    logout(request)

    return redirect("login")


# =========================================================
# EMPLOYEE LIST
@login_required
@never_cache
def employee_list(request):

    employees = (
        Employee.objects
        .select_related("department", "designation")
        .filter(status=True)
        .annotate(
            employee_id_number=Cast(
                "employee_id",
                IntegerField()
            )
        )
        .order_by("employee_id_number")
    )

    return render(
        request,
        "employee_list.html",
        {
            "employees": employees
        }
    )

# =========================================================
# CHECK EMPLOYEE ID
# =========================================================

@login_required
def check_employee_id(request):

    employee_id = request.GET.get("employee_id", "").strip()

    exists = False

    if employee_id:
        exists = Employee.objects.filter(
            employee_id=employee_id
        ).exists()

    return JsonResponse({
        "exists": exists
    })


# =========================================================
# CHECK EMPLOYEE EMAIL
# =========================================================

@login_required
def check_employee_email(request):

    email = request.GET.get("email", "").strip().lower()

    exists = False

    if email:
        exists = Employee.objects.filter(
            email__iexact=email
        ).exists()

    return JsonResponse({
        "exists": exists
    })


# =========================================================
# CHECK EMPLOYEE PHONE
# =========================================================

@login_required
def check_employee_phone(request):

    phone = request.GET.get("phone", "").strip()

    exists = False

    if phone:
        exists = Employee.objects.filter(
            phone=phone
        ).exists()

    return JsonResponse({
        "exists": exists
    })


# =========================================================
# CREATE EMPLOYEE
# =========================================================

@login_required
@never_cache
def employee_create(request):

    departments = Department.objects.all()
    designations = Designation.objects.all()

    if request.method == "POST":

        # -----------------------------------------
        # GET FORM DATA
        # -----------------------------------------

        employee_id = request.POST.get(
            "employee_id",
            ""
        ).strip()

        name = request.POST.get(
            "name",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip().lower()

        phone = request.POST.get(
            "phone",
            ""
        ).strip()

        department_id = request.POST.get(
            "department"
        )

        designation_id = request.POST.get(
            "designation"
        )

        joining_date = request.POST.get(
            "joining_date"
        )

        employment_type = request.POST.get(
            "employment_type"
        )

        salary = request.POST.get(
            "salary"
        )

        address = request.POST.get(
            "address"
        )

        status = request.POST.get(
            "status"
        ) == "on"


        # -----------------------------------------
        # CHECK PHONE NUMBER
        # -----------------------------------------

        if not phone.isdigit() or len(phone) != 10:

            messages.error(
                request,
                "Phone number must contain exactly 10 digits."
            )

            return redirect(
                "employee_create"
            )


        # -----------------------------------------
        # CHECK INDIAN MOBILE NUMBER
        # -----------------------------------------

        if phone[0] not in "6789":

            messages.error(
                request,
                "Phone number must start with 6, 7, 8, or 9."
            )

            return redirect(
                "employee_create"
            )


        # -----------------------------------------
        # CHECK PHONE DUPLICATE
        # -----------------------------------------

        if Employee.objects.filter(
            phone=phone
        ).exists():

            messages.error(
                request,
                "Employee with this mobile number already exists."
            )

            return redirect(
                "employee_create"
            )


        # -----------------------------------------
        # CHECK EMPLOYEE ID
        # -----------------------------------------

        if Employee.objects.filter(
            employee_id=employee_id
        ).exists():

            messages.error(
                request,
                "Employee ID already exists."
            )

            return redirect(
                "employee_create"
            )


        # -----------------------------------------
        # CHECK EMPLOYEE EMAIL
        # -----------------------------------------

        if Employee.objects.filter(
            email__iexact=email
        ).exists():

            messages.error(
                request,
                "Employee with this email already exists."
            )

            return redirect(
                "employee_create"
            )


        # -----------------------------------------
        # CHECK USER USERNAME
        # -----------------------------------------

        if User.objects.filter(
            username__iexact=email
        ).exists():

            messages.error(
                request,
                "An account with this email already exists."
            )

            return redirect(
                "employee_create"
            )


        # -----------------------------------------
        # CHECK USER EMAIL
        # -----------------------------------------

        if User.objects.filter(
            email__iexact=email
        ).exists():

            messages.error(
                request,
                "An account with this email already exists."
            )

            return redirect(
                "employee_create"
            )


        # -----------------------------------------
        # CREATE USER
        # -----------------------------------------

        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=name
        )

        # Employee will create password
        user.set_unusable_password()

        user.save()


        # -----------------------------------------
        # CREATE EMPLOYEE
        # -----------------------------------------

        employee = Employee.objects.create(

            user=user,

            employee_id=employee_id,

            name=name,

            email=email,

            phone=phone,

            department_id=department_id,

            designation_id=designation_id,

            joining_date=joining_date,

            employment_type=employment_type,

            salary=salary,

            address=address,

            status=status
        )


        # -----------------------------------------
        # CREATE PASSWORD SETUP LINK
        # -----------------------------------------

        uid = urlsafe_base64_encode(
            force_bytes(user.pk)
        )

        token = default_token_generator.make_token(
            user
        )

        setup_link = request.build_absolute_uri(
            reverse(
                "set_password",
                kwargs={
                    "uidb64": uid,
                    "token": token
                }
            )
        )


        # -----------------------------------------
        # SEND EMAIL
        # -----------------------------------------

        send_mail(

            subject="CrewConnect - Set Your Password",

            message=f"""
Hello {name},

Your CrewConnect employee account has been created.

Please click the link below to create your password:

{setup_link}

After setting your password, you can log in to CrewConnect.

Regards,
CrewConnect HR
""",

            from_email=settings.DEFAULT_FROM_EMAIL,

            recipient_list=[email],

            fail_silently=False
        )


        # -----------------------------------------
        # SUCCESS MESSAGE
        # -----------------------------------------

        messages.success(
            request,
            "Employee created successfully."
        )

        return redirect(
            "employee_list"
        )


    # -----------------------------------------
    # DISPLAY ADD EMPLOYEE FORM
    # -----------------------------------------

    return render(
        request,
        "employee_add_update.html",
        {
            "departments": departments,
            "designations": designations,
            "employment_types": Employee.EMPLOYMENT_TYPES,
            "is_update": False,
        }
    )


# =========================================================
# UPDATE EMPLOYEE
# =========================================================

@login_required
@never_cache
def employee_update(request, id):

    employee = get_object_or_404(
        Employee,
        id=id
    )

    departments = Department.objects.all()
    designations = Designation.objects.all()


    if request.method == "POST":

        employee.employee_id = request.POST.get(
            "employee_id"
        )

        employee.name = request.POST.get(
            "name"
        )

        employee.email = request.POST.get(
            "email",
            ""
        ).strip().lower()

        # -----------------------------------------
        # CHECK EMAIL DUPLICATE
        # -----------------------------------------

        if Employee.objects.filter(
            email__iexact=employee.email
        ).exclude(
            id=employee.id
        ).exists():

            messages.error(
                request,
                "Employee with this email already exists."
            )

            return redirect(
                "employee_update",
                id=id
            )

        if User.objects.filter(
            email__iexact=employee.email
        ).exclude(
            id=employee.user_id
        ).exists():

            messages.error(
                request,
                "An account with this email already exists."
            )

            return redirect(
                "employee_update",
                id=id
            )

        if User.objects.filter(
            username__iexact=employee.email
        ).exclude(
            id=employee.user_id
        ).exists():

            messages.error(
                request,
                "An account with this email already exists."
            )

            return redirect(
                "employee_update",
                id=id
            )

        employee.phone = request.POST.get(
            "phone",
            ""
        ).strip()


        # -----------------------------------------
        # CHECK PHONE NUMBER
        # -----------------------------------------

        if not employee.phone.isdigit() or len(employee.phone) != 10:

            messages.error(
                request,
                "Phone number must contain exactly 10 digits."
            )

            return redirect(
                "employee_update",
                id=id
            )


        # -----------------------------------------
        # CHECK INDIAN MOBILE NUMBER
        # -----------------------------------------

        if employee.phone[0] not in "6789":

            messages.error(
                request,
                "Phone number must start with 6, 7, 8, or 9."
            )

            return redirect(
                "employee_update",
                id=id
            )


        # -----------------------------------------
        # CHECK PHONE DUPLICATE
        # -----------------------------------------

        if Employee.objects.filter(
            phone=employee.phone
        ).exclude(
            id=employee.id
        ).exists():

            messages.error(
                request,
                "Employee with this mobile number already exists."
            )

            return redirect(
                "employee_update",
                id=id
            )


        employee.department_id = request.POST.get(
            "department"
        )

        employee.designation_id = request.POST.get(
            "designation"
        )

        employee.joining_date = request.POST.get(
            "joining_date"
        )

        employee.employment_type = request.POST.get(
            "employment_type"
        )

        employee.salary = request.POST.get(
            "salary"
        )

        employee.address = request.POST.get(
            "address"
        )

        employee.status = request.POST.get(
            "status"
        ) == "on"


        employee.save()

        return redirect(
            "employee_list"
        )


    return render(
        request,
        "employee_add_update.html",
        {
            "employee": employee,
            "departments": departments,
            "designations": designations,
            "employment_types": Employee.EMPLOYMENT_TYPES,
            "is_update": True,
        }
    )


# =========================================================
# DELETE / DEACTIVATE EMPLOYEE
# =========================================================

def employee_delete(request, id):

    employee = get_object_or_404(
        Employee,
        id=id
    )

    employee.status = not employee.status

    employee.save()

    return redirect(
        "employee_list"
    )


# =========================================================
# LEAVE APPROVAL
# =========================================================

@login_required
def leave_approve(request):

    if Employee.objects.filter(
        user=request.user
    ).exists():

        return redirect(
            "employee_dashboard"
        )


    leaves = Leave.objects.select_related(
        "employee",
        "employee__department",
        "employee__designation"
    ).order_by(
        "-applied_date"
    )


    return render(
        request,
        "leave_approval.html",
        {
            "leaves": leaves,
            "is_employee": False,
        }
    )


# =========================================================
# LEAVE ACTION
# =========================================================

@login_required
def leave_action(request, id):

    if Employee.objects.filter(
        user=request.user
    ).exists():

        return redirect(
            "employee_dashboard"
        )


    if request.method == "POST":

        leave = Leave.objects.get(
            id=id
        )

        action = request.POST.get(
            "action"
        )


        if action == "approve":

            leave.status = "Approved"

            leave.save()


        elif action == "reject":

            leave.status = "Rejected"

            leave.save()


    return redirect(
        "leave_approve"
    )


# =========================================================
# DEPARTMENT LIST
# =========================================================

@login_required
def department_list(request):

    departments = Department.objects.all()

    return render(
        request,
        "department_list.html",
        {
            "departments": departments
        }
    )


# =========================================================
# CREATE DEPARTMENT
# =========================================================

@login_required
def department_create(request):

    if request.method == "POST":

        name = request.POST.get(
            "name"
        )

        if name:

            Department.objects.create(
                name=name
            )

            return redirect(
                "department_list"
            )


    return render(
        request,
        "department_form.html"
    )


# =========================================================
# UPDATE DEPARTMENT
# =========================================================

@login_required
def department_update(request, id):

    department = get_object_or_404(
        Department,
        id=id
    )


    if request.method == "POST":

        name = request.POST.get(
            "name",
            ""
        ).strip()

        if name:

            department.name = name

            department.save()

            return redirect(
                "department_list"
            )


    return render(
        request,
        "department_form.html",
        {
            "department": department
        }
    )


# =========================================================
# DELETE DEPARTMENT
# =========================================================

@login_required
def department_delete(request, id):

    department = get_object_or_404(
        Department,
        id=id
    )


    if request.method == "POST":

        department.delete()

        return redirect(
            "department_list"
        )


    return render(
        request,
        "department_confirm_delete.html",
        {
            "department": department
        }
    )


# =========================================================
# DESIGNATION LIST
# =========================================================

@login_required
def designation_list(request):

    designations = (
        Designation.objects
        .all()
        .order_by("name")
    )

    return render(
        request,
        "designation_list.html",
        {
            "designations": designations
        }
    )


# =========================================================
# CREATE DESIGNATION
# =========================================================

@login_required
def designation_create(request):

    if request.method == "POST":

        name = request.POST.get(
            "name",
            ""
        ).strip()

        if name:

            Designation.objects.create(
                name=name
            )

            return redirect(
                "designation_list"
            )


    return render(
        request,
        "designation_form.html"
    )


# =========================================================
# UPDATE DESIGNATION
# =========================================================

@login_required
def designation_update(request, id):

    designation = get_object_or_404(
        Designation,
        id=id
    )


    if request.method == "POST":

        name = request.POST.get(
            "name",
            ""
        ).strip()

        if name:

            designation.name = name

            designation.save()

            return redirect(
                "designation_list"
            )


    return render(
        request,
        "designation_form.html",
        {
            "designation": designation
        }
    )


# =========================================================
# DELETE DESIGNATION
# =========================================================

@login_required
def designation_delete(request, id):

    designation = get_object_or_404(
        Designation,
        id=id
    )


    if request.method == "POST":

        designation.delete()

        return redirect(
            "designation_list"
        )


    return render(
        request,
        "designation_confirm_delete.html",
        {
            "designation": designation
        }
    )


# =========================================================
# REPORTS
# =========================================================

@login_required
def reports(request):

    total_employees = Employee.objects.count()

    total_departments = Department.objects.count()

    total_designations = Designation.objects.count()

    active_employees = Employee.objects.filter(
        status=True
    ).count()


    department_report = Department.objects.annotate(
        employee_count=Count("employee")
    ).order_by("name")


    designation_report = Designation.objects.annotate(
        employee_count=Count("employee")
    ).order_by("name")


    employment_report = Employee.objects.values(
        "employment_type"
    ).annotate(
        employee_count=Count("id")
    ).order_by("employment_type")


    context = {

        "total_employees": total_employees,

        "total_departments": total_departments,

        "total_designations": total_designations,

        "active_employees": active_employees,

        "department_report": department_report,

        "designation_report": designation_report,

        "employment_report": employment_report,
    }


    return render(
        request,
        "reports.html",
        context
    )


# =========================================================
# SETTINGS
# =========================================================

@login_required
def settings_view(request):

    return render(
        request,
        "settings.html"
    )


# =========================================================
# CHANGE PASSWORD
# =========================================================

@login_required
def change_password(request):

    if request.method == "POST":

        form = PasswordChangeForm(
            request.user,
            request.POST
        )


        if form.is_valid():

            user = form.save()

            update_session_auth_hash(
                request,
                user
            )

            messages.success(
                request,
                "Password changed successfully."
            )

            return redirect(
                "settings"
            )

    else:

        form = PasswordChangeForm(
            request.user
        )


    return render(
        request,
        "change_password.html",
        {
            "form": form
        }
    )


# =========================================================
# PAYROLL LIST
# =========================================================

def payroll_list(request):

    payrolls = (
        Payroll.objects
        .select_related("employee")
        .order_by(
            "-month",
            "employee__name"
        )
    )


    total_payroll = sum(
        payroll.net_salary
        for payroll in payrolls
    )


    paid_payroll = sum(
        payroll.net_salary
        for payroll in payrolls
        if payroll.status == "Paid"
    )


    pending_payroll = sum(
        payroll.net_salary
        for payroll in payrolls
        if payroll.status == "Pending"
    )


    context = {

        "payrolls": payrolls,

        "total_payroll": total_payroll,

        "paid_payroll": paid_payroll,

        "pending_payroll": pending_payroll,
    }


    return render(
        request,
        "payroll_list.html",
        context
    )


# =========================================================
# CREATE PAYROLL
# =========================================================

def payroll_create(request):

    employees = (
        Employee.objects
        .filter(status=True)
        .order_by("name")
    )


    if request.method == "POST":

        employee_id = request.POST.get(
            "employee"
        )

        month = request.POST.get(
            "month"
        )


        allowances = Decimal(
            request.POST.get(
                "allowances"
            ) or "0"
        )


        deductions = Decimal(
            request.POST.get(
                "deductions"
            ) or "0"
        )


        status = request.POST.get(
            "status"
        )


        employee = get_object_or_404(
            Employee,
            id=employee_id
        )


        Payroll.objects.create(

            employee=employee,

            month=month,

            basic_salary=employee.salary,

            allowances=allowances,

            deductions=deductions,

            status=status
        )


        messages.success(
            request,
            "Payroll created successfully."
        )

        return redirect(
            "payroll_list"
        )


    return render(
        request,
        "payroll_form.html",
        {
            "employees": employees
        }
    )


# =========================================================
# UPDATE PAYROLL
# =========================================================

def payroll_update(request, id):

    payroll = get_object_or_404(
        Payroll,
        id=id
    )


    employees = (
        Employee.objects
        .filter(status=True)
        .order_by("name")
    )


    if request.method == "POST":

        employee_id = request.POST.get(
            "employee"
        )

        month = request.POST.get(
            "month"
        )


        allowances = Decimal(
            request.POST.get(
                "allowances"
            ) or "0"
        )


        deductions = Decimal(
            request.POST.get(
                "deductions"
            ) or "0"
        )


        status = request.POST.get(
            "status"
        )


        employee = get_object_or_404(
            Employee,
            id=employee_id
        )


        payroll.employee = employee

        payroll.month = month

        payroll.basic_salary = employee.salary

        payroll.allowances = allowances

        payroll.deductions = deductions

        payroll.status = status

        payroll.save()


        messages.success(
            request,
            "Payroll updated successfully."
        )

        return redirect(
            "payroll_list"
        )


    return render(
        request,
        "payroll_form.html",
        {
            "payroll": payroll,
            "employees": employees
        }
    )


# =========================================================
# DELETE PAYROLL
# =========================================================

def payroll_delete(request, id):

    payroll = get_object_or_404(
        Payroll,
        id=id
    )


    if request.method == "POST":

        payroll.delete()

        messages.success(
            request,
            "Payroll deleted successfully."
        )

        return redirect(
            "payroll_list"
        )


    return render(
        request,
        "payroll_confirm_delete.html",
        {
            "payroll": payroll
        }
    )

