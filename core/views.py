# core/views.py
import json
import os
from django.conf import settings
from django.shortcuts import render


def home_view(request):
    json_path = os.path.join(settings.BASE_DIR, 'core', 'data', 'planes.json')

    with open(json_path, 'r', encoding='utf-8') as f:
        planes = json.load(f)

    context = {
        'planes': planes,
        'whatsapp_number': settings.WHATSAPP_NUMBER,
        'whatsapp_message': settings.WHATSAPP_DEFAULT_MESSAGE,
    }
    return render(request, 'core/home.html', context)