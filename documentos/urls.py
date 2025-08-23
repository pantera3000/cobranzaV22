from django.urls import path
from . import views

app_name = 'documentos'

urlpatterns = [
    path('', views.documento_list, name='documento_list'),
    path('crear/', views.documento_create, name='documento_create'),
    path('editar/<int:pk>/', views.documento_update, name='documento_update'),
    path('eliminar/<int:pk>/', views.documento_delete, name='documento_delete'),
    path('detalle/<int:pk>/', views.documento_detail, name='documento_detail'),
    path('exportar/excel/', views.documento_export_excel, name='documento_export_excel'),
    path('exportar/csv/', views.documento_export_csv, name='documento_export_csv'),

    path('autocomplete-pendiente/', views.documento_pendiente_autocomplete, name='documento_pendiente_autocomplete'),
    path('api/cliente-search/', views.cliente_search_api, name='cliente_search_api'),
]