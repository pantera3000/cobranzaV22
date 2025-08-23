# clientes/middleware.py
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

class LoginRequiredMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        print("✅ Middleware: Inicializado")  # Depuración
        self.get_response = get_response

    def __call__(self, request):
        print("🔍 Middleware: Ejecutándose...")  # Depuración
        print("👤 Usuario:", request.user, "| Autenticado:", request.user.is_authenticated)

        # URLs públicas
        allowed_paths = [
            reverse('login'),
            reverse('logout'),
        ]

        # Permitir acceso a estáticos
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            print("✅ Acceso a estático permitido")
            return self.get_response(request)

        # Permitir acceso a .well-known
        if request.path.startswith('/.well-known/'):
            print("✅ Acceso a .well-known permitido")
            return self.get_response(request)

        # Verificar autenticación
        if not request.user.is_authenticated:
            if not any(request.path.startswith(path) for path in allowed_paths):
                print(f"🔒 Redirigiendo {request.path} a login")
                return redirect(f"{reverse('login')}?next={request.get_full_path()}")

        response = self.get_response(request)
        return response