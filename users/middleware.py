# users/middleware.py

class HTMXAxesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Si Axes bloquea la IP (código 429) y la petición viene de HTMX
        if response.status_code == 429 and request.META.get('HTTP_HX_REQUEST') == 'true':
            # 1. Cambiamos el estado a 200 (éxito) para obligar a HTMX a procesarlo
            response.status_code = 200
            
            # 2. Le ordenamos a HTMX que reemplace todo el <body> con la pantalla de bloqueo
            response['HX-Retarget'] = 'body'

        return response