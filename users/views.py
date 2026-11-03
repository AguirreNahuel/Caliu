import io
import base64
import qrcode
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout, load_backend
from django.contrib.auth.decorators import login_required, user_passes_test
from django.conf import settings
from django.http import HttpResponse
from django.db.models import Q
from django.core.paginator import Paginator
from django_otp.plugins.otp_totp.models import TOTPDevice
from .models import User, Employee, normalize_text
from .forms import EmployeeForm, UserAccessForm



# ==========================================
# VISTAS DE AUTENTICACIÓN Y 2FA (HTMX)
# ==========================================

def login_view(request):
    """
    Maneja el flujo de autenticación de dos pasos con HTMX de forma segura:
    - Paso 1: Valida usuario/email y contraseña, regenerando la sesión.
    - Evalúa 2FA (Obligatorio para Staff/Superuser).
    """
    if request.method == 'GET':
        # Limpiamos cualquier rastro previo de 2FA al entrar a la vista de login
        if 'pre_2fa_user_id' in request.session:
            del request.session['pre_2fa_user_id']
        return render(request, 'users/login/login.html')

    # 1. EVALUACIÓN DE PASO 1: Credenciales
    if 'verify_credentials' in request.POST:
        identifier = request.POST.get('identifier', '').strip()
        password = request.POST.get('password', '')

        # Busco por username del usuario o por el email del empleado vinculado
        user_obj = User.objects.filter(
            Q(username__iexact=identifier) | Q(employee__email__iexact=identifier)
        ).first()

        auth_username = user_obj.username if user_obj else identifier
        user = authenticate(request, username=auth_username, password=password)

        if not user or not user.is_active:
            return render(request, 'users/login/partials/login_step1.html', {
                'error': 'Ocurrió un error al validar los datos. Verifique la información e intente nuevamente.'
            })

        # PREVENCIÓN DE FIJACIÓN DE SESIÓN:
        # Regeneramos la clave de sesión antes de iniciar cualquier flujo autenticado o semi-autenticado
        request.session.cycle_key()

        # Regla de Negocio: Si NO es staff ni superuser, salto el 2FA e inicio sesión directamente
        if not (user.is_staff or user.is_superuser):
            auth_login(request, user)
            response = HttpResponse()
            response['HX-Redirect'] = '/dashboard/'
            return response

        # Guardamos el ID de usuario de forma segura para la fase 2FA
        request.session['pre_2fa_user_id'] = user.id

        # Buscamos si ya tiene un dispositivo TOTP confirmado
        device = TOTPDevice.objects.filter(user=user, name='default', confirmed=True).first()

        # CASO A: Ya configuró 2FA previamente
        if device:
            return render(request, 'users/login/partials/login_step2_otp.html')

        # CASO B: Primera vez / No tiene dispositivo confirmado
        # Limpiamos dispositivos no confirmados previos para evitar basura o colisiones
        TOTPDevice.objects.filter(user=user, name='default', confirmed=False).delete()
        
        # Creamos uno nuevo limpio
        device = TOTPDevice.objects.create(user=user, name='default', confirmed=False)

        otp_uri = device.config_url
        img = qrcode.make(otp_uri)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return render(request, 'users/login/partials/login_step2_qr.html', {
            'qr_code': qr_base64,
            'secret_key': device.key
        })

    # 2. EVALUACIÓN DE PASO 2: Validación OTP
    if 'verify_otp' in request.POST:
        user_id = request.session.get('pre_2fa_user_id')
        if not user_id:
            return render(request, 'users/login/partials/login_step1.html', {
                'error': 'La sesión 2FA ha expirado o es inválida. Por favor, vuelva a iniciar sesión.'
            })

        try:
            user = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            if 'pre_2fa_user_id' in request.session:
                del request.session['pre_2fa_user_id']
            return render(request, 'users/login/partials/login_step1.html', {
                'error': 'Usuario no válido. Por favor, intente nuevamente.'
            })

        otp_code = request.POST.get('otp_code', '').strip()

        # Buscamos primero uno confirmado, o el último creado
        device = TOTPDevice.objects.filter(user=user, name='default', confirmed=True).first()
        if not device:
            device = TOTPDevice.objects.filter(user=user, name='default').order_by('-id').first()
        
        if device and device.verify_token(otp_code):
            if not device.confirmed:
                device.confirmed = True
                device.save()

            # Asignamos el backend activo al usuario (necesario por múltiples backends)
            for backend_path in settings.AUTHENTICATION_BACKENDS:
                backend = load_backend(backend_path)
                if hasattr(backend, 'get_user') and backend.get_user(user.pk):
                    user.backend = backend_path
                    break

            # Iniciamos sesión oficialmente en Django
            auth_login(request, user)
            
            # Limpiamos la variable temporal de 2FA de la sesión
            if 'pre_2fa_user_id' in request.session:
                del request.session['pre_2fa_user_id']

            response = HttpResponse()
            response['HX-Redirect'] = '/dashboard/'
            return response

        context = {'error': 'El código ingresado es incorrecto o ha expirado.'}
        
        # Si todavía no estaba confirmado, regeneramos el QR para que pueda reintentar
        if device and not device.confirmed:
            otp_uri = device.config_url
            img = qrcode.make(otp_uri)
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            context['qr_code'] = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return render(request, 'users/login/partials/login_step2_otp.html', context)

        return render(request, 'users/login/partials/login_step2_otp.html', context)

    return render(request, 'users/login/login.html')


@login_required
def logout_view(request):
    auth_logout(request)
    return redirect('login')


# ==========================================
# VISTAS DE GESTIÓN Y CRUD EMPLEADOS
# ==========================================

@login_required
def dashboard_view(request):
    total_employees = Employee.objects.count()
    total_products = 0

    context = {
        'total_employees': total_employees,
        'total_products': total_products,
    }

    # SI ES UNA PETICIÓN HTMX -> Devuelve ÚNICAMENTE el fragmento de tarjetas (sin sidebar)
    if request.headers.get('HX-Request'):
        return render(request, 'dashboard/partials/dashboard_home.html', context)

    # SI ES RECARGA (F5) O URL DIRECTA -> Devuelve el dashboard completo con su sidebar
    return render(request, 'dashboard/dashboard.html', context)

@login_required
def employee_list(request):
    search_query = request.GET.get('q', '').strip()
    # Asegúrate de excluir los eliminados si manejas borrado lógico (is_deleted)
    queryset = Employee.objects.filter(is_deleted=False) if hasattr(Employee, 'is_deleted') else Employee.objects.all()

    if search_query:
        normalized_q = normalize_text(search_query)
        queryset = queryset.filter(
            Q(normalized_full_name__icontains=normalized_q) |
            Q(cuit_dni__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # Configurar la paginación (por ejemplo, 10 empleados por página)
    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'employees': page_obj, # Ahora pasamos el objeto de página
        'page_obj': page_obj,
        'search_query': search_query, # Útil para mantener el buscador si cambias de página
    }

    # Si es una petición HTMX (ya sea escribiendo en el buscador o cambiando de página)
    if request.headers.get('HX-Request'):
        # Si la petición viene específicamente del input de búsqueda o de la paginación dentro de la tabla
        if 'q' in request.GET or 'page' in request.GET:
            return render(request, 'users/employees/partials/employee_table.html', context)
        return render(request, 'users/employees/employee_list.html', context)

    return render(request, 'users/employees/employee_list_page.html', context)


@login_required
def employee_create(request):
    error = None
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            form.save()
            response = HttpResponse()
            response['HX-Redirect'] = '/empleados/'
            return response
        else:
            error = 'No se pudo guardar la información. Por favor, verifique los datos ingresados.'
    else:
        form = EmployeeForm()

    context = {
        'form': form,
        'action_url': '/empleados/nuevo/',
        'title': 'Nuevo Empleado',
        'error': error
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'users/employees/partials/employee_form.html', context)
    return render(request, 'users/employees/employee_form_page.html', context)


@login_required
def employee_update(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    error = None
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            response = HttpResponse()
            response['HX-Redirect'] = '/empleados/'
            return response
        else:
            error = 'No se pudieron actualizar los cambios. Por favor, verifique los datos ingresados.'
    else:
        form = EmployeeForm(instance=employee)

    context = {
        'form': form,
        'action_url': f'/empleados/{pk}/editar/',
        'title': 'Editar Empleado',
        'error': error
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'users/employees/partials/employee_form.html', context)
    return render(request, 'users/employees/employee_form_page.html', context)


@login_required
def employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        employee.is_deleted = True # o employee.delete()
        employee.save()
        
        if request.headers.get('HX-Request'):
            # Replicar la consulta y paginación actual
            queryset = Employee.objects.filter(is_deleted=False) if hasattr(Employee, 'is_deleted') else Employee.objects.all()
            paginator = Paginator(queryset, 10)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            
            return render(request, 'users/employees/partials/employee_table.html', {'employees': page_obj, 'page_obj': page_obj})
            
        response = HttpResponse()
        response['HX-Redirect'] = '/empleados/'
        return response

    return render(request, 'users/employees/partials/employee_form_modal.html')


# ------------------------------------------
# VISTAS DE GESTIÓN Y CRUD ACCESOS (USUARIOS)
# ------------------------------------------

def is_superuser(user):
    return user.is_authenticated and user.is_superuser

@login_required
@user_passes_test(is_superuser)
def access_list(request):
    search_query = request.GET.get('q', '').strip()
    queryset = User.objects.filter(is_deleted=False).select_related('employee')

    if search_query:
        queryset = queryset.filter(
            Q(username__icontains=search_query) |
            Q(employee__first_name__icontains=search_query) |
            Q(employee__last_name__icontains=search_query) |
            Q(employee__email__icontains=search_query)
        )

    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'users': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
    }

    if request.headers.get('HX-Request'):
        if 'q' in request.GET or 'page' in request.GET:
            return render(request, 'users/access/partials/access_table.html', context)
        return render(request, 'users/access/access_list.html', context)

    return render(request, 'users/access/access_list_page.html', context)


@login_required
@user_passes_test(is_superuser)
def access_create(request):
    error = None
    if request.method == 'POST':
        form = UserAccessForm(request.POST)
        if not request.POST.get('password'):
            form.add_error('password', 'Debe ingresar una contraseña para el nuevo usuario.')

        if form.is_valid():
            form.save()
            response = HttpResponse()
            response['HX-Redirect'] = '/accesos/'
            return response
        else:
            error = 'No se pudo guardar la información. Por favor, verifique los datos.'
    else:
        form = UserAccessForm()

    context = {
        'form': form,
        'action_url': '/accesos/nuevo/',
        'title': 'Nuevo Acceso / Usuario',
        'error': error
    }

    if request.headers.get('HX-Request'):
        return render(request, 'users/access/partials/access_form.html', context)
    return render(request, 'users/access/access_form_page.html', context)


@login_required
@user_passes_test(is_superuser)
def access_update(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    error = None

    if request.method == 'POST':
        form = UserAccessForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            response = HttpResponse()
            response['HX-Redirect'] = '/accesos/'
            return response
        else:
            error = 'No se pudieron actualizar los cambios. Por favor, verifique los datos.'
    else:
        form = UserAccessForm(instance=user_obj)

    context = {
        'form': form,
        'action_url': f'/accesos/{pk}/editar/',
        'title': 'Editar Acceso / Usuario',
        'error': error
    }

    if request.headers.get('HX-Request'):
        return render(request, 'users/access/partials/access_form.html', context)
    return render(request, 'users/access/access_form_page.html', context)


@login_required
@user_passes_test(is_superuser)
def access_delete(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        user_obj.is_deleted = True
        user_obj.save()

        if request.headers.get('HX-Request'):
            queryset = User.objects.filter(is_deleted=False).select_related('employee')
            paginator = Paginator(queryset, 10)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            return render(request, 'users/access/partials/access_table.html', {'users': page_obj, 'page_obj': page_obj})

        response = HttpResponse()
        response['HX-Redirect'] = '/accesos/'
        return response

    return HttpResponse(status=405)