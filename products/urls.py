from django.urls import path
from . import views


urlpatterns = [
    path('productos/', views.product_list, name='product_list'),
    path('productos/crear/', views.product_create, name='product_create'),
    path('productos/<int:pk>/update/', views.product_update, name='product_update'),
    path('productos/<int:pk>/delete/', views.product_delete, name='product_delete'),

    path('categorias/', views.category_list, name='category_list'),
    path('categorias/create/', views.category_create, name='category_create'),
    path('categorias/<int:pk>/update/', views.category_update, name='category_update'),
    path('categorias/<int:pk>/delete/', views.category_delete, name='category_delete'),

    path('productos/papelera/', views.product_trash_list, name='product_trash_list'),
    path('productos/papelera/<int:pk>/delete/', views.product_permanent_delete, name='product_permanent_delete'),
    path('productos/papelera/restaurar/<int:pk>/', views.product_restore, name='product_restore'),
]
