# products/validators.py
from django.core.exceptions import ValidationError
from PIL import Image

def validate_product_image(file):
    """
    Valida que el archivo subido sea verdaderamente una imagen analizando
    su contenido binario con Pillow, previniendo la subida de archivos falsos o maliciosos.
    """
    # 1. Validación básica opcional de tamaño máximo (ejemplo: 5 MB)
    max_file_size = 5 * 1024 * 1024  # 5 MB
    if file.size > max_file_size:
        raise ValidationError("El tamaño del archivo no puede superar los 5 MB.")

    try:
        # Intentamos abrir la imagen con Pillow
        img = Image.open(file)
        img.verify() # Verifica si es un archivo de imagen corrupto o falso
    except Exception:
        raise ValidationError("El archivo subido no es una imagen válida.")

    # 2. Opcional: Validar formatos permitidos de forma estricta (ej: JPEG, PNG, WEBP)
    valid_formats = ['JPEG', 'PNG', 'WEBP']
    # Nota: img.format solo está disponible antes de verify() o abriéndolo de nuevo, 
    # por lo que es una buena práctica reabrir o validar el formato chequeando el contenido:
    if img.format not in valid_formats:
        raise ValidationError(f"Formato de imagen no permitido ({img.format}). Use JPEG, PNG o WEBP.")
    
    # Es una buena práctica limpiar el puntero del archivo tras leerlo por si se procesa después
    file.seek(0)