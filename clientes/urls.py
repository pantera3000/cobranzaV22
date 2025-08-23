from django.urls import path
from . import views

app_name = 'clientes'

urlpatterns = [
    path('', views.cliente_list, name='cliente_list'),
    path('crear/', views.cliente_create, name='cliente_create'),
    path('detalle/<int:pk>/', views.cliente_detail, name='cliente_detail'),
    path('editar/<int:pk>/', views.cliente_update, name='cliente_update'),
    path('eliminar/<int:pk>/', views.cliente_delete, name='cliente_delete'),
    path('exportar/excel/', views.cliente_export_excel, name='cliente_export_excel'),
    path('exportar/csv/', views.cliente_export_csv, name='cliente_export_csv'),

    path('log/', views.log_actividad, name='log_actividad'),
    path('config/', views.empresa_config, name='empresa_config'),

    path('log/limpiar/', views.limpiar_log, name='limpiar_log'),
]