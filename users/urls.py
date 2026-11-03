# users/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Autenticación y 2FA con HTMX
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # CRUD Empleados
    path('empleados/', views.employee_list, name='employee_list'),
    path('empleados/nuevo/', views.employee_create, name='employee_create'),
    path('empleados/<int:pk>/editar/', views.employee_update, name='employee_update'),
    path('empleados/<int:pk>/eliminar/', views.employee_delete, name='employee_delete'),

    #CRUD Accessos
    path('accesos/', views.access_list, name='access_list'),
    path('accesos/nuevo/', views.access_create, name='access_create'),
    path('accesos/<int:pk>/editar/', views.access_update, name='access_update'),
    path('accesos/<int:pk>/eliminar/', views.access_delete, name='access_delete'),
]