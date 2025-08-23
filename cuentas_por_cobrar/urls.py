from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect  # ✅ Import correcto

from django.shortcuts import render
from clientes.models import EmpresaConfig

def login_view(request):
    config = EmpresaConfig.objects.first()
    if not config:
        config = EmpresaConfig.objects.create(nombre="Cuentas por Cobrar")
    return auth_views.LoginView.as_view(
        template_name='registration/login.html',
        extra_context={'config': config}
    )(request)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('clientes/', include('clientes.urls')),
    path('cobradores/', include('cobradores.urls')),
    path('documentos/', include('documentos.urls')),
    path('cobros/', include('cobros.urls')),
    path('devoluciones/', include('devoluciones.urls')),
    path('reportes/', include('reportes.urls')),
    
    
   

    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),  # ✅ Redirige al inicio



    # 🔥 Redirección raíz: / → /clientes/
    path('', lambda request: redirect('clientes:cliente_list'), name='home'),
]