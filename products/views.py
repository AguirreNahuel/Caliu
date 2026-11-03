from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q
from django.http import HttpResponse
from django.urls import reverse
from .models import Product, Category
from .forms import ProductForm, CategoryForm
from django.contrib.auth.decorators import login_required, user_passes_test


def is_staff_member(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

@login_required
@user_passes_test(is_staff_member)
def product_list(request):
    search_query = request.GET.get('q', '').strip()
    
    # Excluyo productos marcados como eliminados para que no aparezcan en el listado principal
    products = Product.objects.select_related('category')

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    paginator = Paginator(products, 6)
    page_number = request.GET.get('page', 1)

    try:
        page_obj = paginator.get_page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.get_page(1)

    context = {
        'products': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
    }

    # Manejo las peticiones HTMX para actualizar dinámicamente la tabla o la vista completa
    if request.headers.get('HX-Request'):
        if 'q' in request.GET or 'page' in request.GET:
            return render(request, 'products/partials/product_table.html', context)
        
        return render(request, 'products/partials/product_list.html', context)

    # Petición HTTP estándar por si recargan la página
    return render(request, 'products/product_list_page.html', context)


@login_required
@user_passes_test(is_staff_member)
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                response = HttpResponse()
                response['HX-Redirect'] = reverse('product_list')
                return response
            return redirect('product_list')
    else:
        form = ProductForm()

    context = {
        'form': form,
        'title': 'Crear Nuevo Producto',
        'action_url': reverse('product_create'),
    }

    if request.headers.get('HX-Request'):
        return render(request, 'products/partials/product_form.html', context)

    return render(request, 'products/product_form_page.html', context)


@login_required
@user_passes_test(is_staff_member)
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk, is_deleted=False)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                response = HttpResponse()
                response['HX-Redirect'] = reverse('product_list')
                return response
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)

    context = {
        'form': form,
        'product': product,
        'title': f'Editar Producto: {product.name}',
        'action_url': reverse('product_update', kwargs={'pk': product.pk}),
    }

    if request.headers.get('HX-Request'):
        return render(request, 'products/partials/product_form.html', context)

    return render(request, 'products/product_form_page.html', context)


@login_required
@user_passes_test(is_staff_member)
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk, is_deleted=False)
    
    if request.method == 'POST':
        # Aplico borrado lógico (Soft Delete) mandándolo a la papelera
        product.is_deleted = True
        product.save()

    search_query = request.GET.get('q', '').strip()
    products = Product.objects.select_related('category')

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    paginator = Paginator(products, 6)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'products': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'products/partials/product_table.html', context)

    return redirect('product_list')


def is_superuser(user):
    return user.is_authenticated and user.is_superuser

@login_required
@user_passes_test(is_superuser)
def product_trash_list(request):
    if not request.user.is_superuser:
        return redirect('product_list')
        
    search_query = request.GET.get('q', '').strip()
    products = Product.all_objects.filter(is_deleted=True).select_related('category')

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    paginator = Paginator(products, 6)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'products': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
    }

    # 1. Bloque HTMX (con sus 2 posibles salidas según lo que se pida)
    if request.headers.get('HX-Request'):
        if 'q' in request.GET or 'page' in request.GET:
            return render(request, 'products/partials/product_trash_table.html', context)
        
        return render(request, 'products/partials/product_trash.html', context)

    # 2. Petición estándar / F5 (página completa)
    return render(request, 'products/product_trash_page.html', context)


@login_required
@user_passes_test(is_superuser)
def product_permanent_delete(request, pk):
    # Me aseguro de que solo un superusuario pueda ejecutar el borrado físico definitivo
    if not request.user.is_superuser:
        return redirect('product_list')

    product = get_object_or_404(Product, pk=pk, is_deleted=True)
    
    if request.method == 'POST':
        # Borro el registro por completo de la base de datos de forma irreversible
        product.delete()

    search_query = request.GET.get('q', '').strip()
    products = Product.objects.filter(is_deleted=True).select_related('category')

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    paginator = Paginator(products, 6)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'products': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'products/partials/product_trash_table.html', context)

    return redirect('product_trash_list')


@login_required
@user_passes_test(is_superuser)
def product_restore(request, pk):
    # Verificamos que sea superusuario
    if not request.user.is_superuser:
        return redirect('product_list')

    product = get_object_or_404(Product, pk=pk, is_deleted=True)
    
    if request.method == 'POST':
        # Quitamos el soft delete para que vuelva a estar activo
        product.is_deleted = False
        product.save()

    search_query = request.GET.get('q', '').strip()
    products = Product.objects.filter(is_deleted=True).select_related('category')

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    paginator = Paginator(products, 6)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'products': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
    }

    # Si es HTMX, devolvemos la tabla actualizada de la papelera
    if request.headers.get('HX-Request'):
        return render(request, 'products/partials/product_trash_table.html', context)

    return redirect('product_trash_list')


@login_required
@user_passes_test(is_staff_member)
def category_list(request):
    search_query = request.GET.get('q', '').strip()
    
    # Excluyo las categorías eliminadas lógicamente
    categories = Category.objects.filter(is_deleted=False)

    if search_query:
        categories = categories.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    paginator = Paginator(categories, 6)
    page_number = request.GET.get('page', 1)

    try:
        page_obj = paginator.get_page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.get_page(1)

    context = {
        'categories': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
    }

    if request.headers.get('HX-Request'):
        if 'q' in request.GET or 'page' in request.GET:
            return render(request, 'categories/partials/category_table.html', context)
        return render(request, 'categories/category_list.html', context)

    return render(request, 'categories/category_list_page.html', context)


@login_required
@user_passes_test(is_staff_member)
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                response = HttpResponse()
                response['HX-Redirect'] = reverse('category_list')
                return response
            return redirect('category_list')
    else:
        form = CategoryForm()

    context = {
        'form': form,
        'title': 'Crear Nueva Categoría',
        'action_url': reverse('category_create'),
    }

    if request.headers.get('HX-Request'):
        return render(request, 'categories/partials/category_form.html', context)

    return render(request, 'categories/category_form_page.html', context)


@login_required
@user_passes_test(is_staff_member)
def category_update(request, pk):
    category = get_object_or_404(Category, pk=pk, is_deleted=False)

    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                response = HttpResponse()
                response['HX-Redirect'] = reverse('category_list')
                return response
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)

    context = {
        'form': form,
        'category': category,
        'title': f'Editar Categoría: {category.name}',
        'action_url': reverse('category_update', kwargs={'pk': category.pk}),
    }

    if request.headers.get('HX-Request'):
        return render(request, 'categories/partials/category_form.html', context)

    return render(request, 'categories/category_form_page.html', context)


@login_required
@user_passes_test(is_staff_member)
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk, is_deleted=False)
    
    if request.method == 'POST':
        # Aplico soft delete a la categoría
        category.is_deleted = True
        category.save()

    search_query = request.GET.get('q', '').strip()
    categories = Category.objects.filter(is_deleted=False)

    if search_query:
        categories = categories.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    paginator = Paginator(categories, 6)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'categories': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'categories/partials/category_table.html', context)

    return redirect('category_list')