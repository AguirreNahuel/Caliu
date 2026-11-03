import os
from django.db import models
from django.db.models import Q, CheckConstraint
from django.utils.text import slugify
from .validators import validate_product_image

def product_image_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    name_slug = slugify(instance.name) if instance.name else 'producto'
    return f'products/{name_slug}.{ext}'

# 1. Manager personalizado para filtrar automáticamente registros no eliminados
class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Nombre")
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    is_deleted = models.BooleanField(default=False, verbose_name="Eliminada")

    # Definición de Managers
    objects = ActiveManager()       # Traerá solo las categorías activas por defecto
    all_objects = models.Manager()  # Traerá todas (incluyendo las eliminadas para la papelera)

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['name']

    def save(self, *args, **kwargs):
        # 2. Lógica para evitar duplicados en slugs de Categorías
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Category.all_objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL,
        null=True,     
        blank=True,
        related_name="products", 
        verbose_name="Categoría"
    )
    name = models.CharField(max_length=200, verbose_name="Nombre del producto")
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(verbose_name="Descripción")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio")
    stock = models.PositiveIntegerField(default=0, verbose_name="Stock disponible")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    is_deleted = models.BooleanField(default=False, verbose_name="Eliminado")
    image = models.ImageField(
        upload_to=product_image_upload_path, 
        validators=[validate_product_image], 
        blank=True, 
        null=True, 
        verbose_name="Imagen"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última actualización")

    # Definición de Managers
    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['-created_at']
        constraints = [
            CheckConstraint(
                condition=Q(price__gte=0), 
                name="price_gte_zero"
            ),
            CheckConstraint(
                condition=Q(stock__gte=0), 
                name="stock_gte_zero"
            ),
        ]

    def save(self, *args, **kwargs):
        # 3. Lógica robusta para autoincrementar slugs repetidos y evitar el Error 500 (IntegrityError)
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.all_objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name