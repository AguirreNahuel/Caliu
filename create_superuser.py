import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Ecommers.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

if username and password:
    if not User.objects.filter(username=username).exists():
        user = User(
            username=username,
            is_staff=True,
            is_superuser=True,
            is_active=True,
            is_deleted=False
        )
        user.set_password(password)
        user.save()
        print(f"Superusuario '{username}' creado con éxito.")
    else:
        print(f"El usuario '{username}' ya existe.")