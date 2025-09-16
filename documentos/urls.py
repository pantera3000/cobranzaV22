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



    path('descargar-plantilla/', views.descargar_plantilla_excel, name='descargar_plantilla_excel'),
    path('importar-excel/', views.importar_documentos_excel, name='importar_documentos_excel'),




    # --- Módulo: Reporte de Despacho ---
    path('despachos/', views.despacho_lista, name='despacho_lista'),
    path('despachos/crear/', views.despacho_crear, name='despacho_crear'),
    path('despachos/<int:despacho_id>/', views.despacho_detalle, name='despacho_detalle'),
    path('despachos/<int:despacho_id>/agregar/', views.despacho_agregar_documento, name='despacho_agregar_documento'),
    path('despachos/<int:despacho_id>/registrar-cobro/', views.despacho_registrar_cobro, name='despacho_registrar_cobro'),
    path('despachos/<int:despacho_id>/cerrar/', views.despacho_cerrar, name='despacho_cerrar'),
    path('despachos/<int:despacho_id>/reabrir/', views.despacho_reabrir, name='despacho_reabrir'),
    path('despachos/<int:despacho_id>/eliminar/', views.despacho_eliminar, name='despacho_eliminar'),
    
    # --- PDFs ---
    path('despachos/<int:despacho_id>/pdf/', views.despacho_pdf, name='despacho_pdf'),
    path('despachos/<int:despacho_id>/liquidacion-pdf/', views.despacho_liquidacion_pdf, name='despacho_liquidacion_pdf'),


    path('repartidor/', views.modo_repartidor, name='modo_repartidor'),


    # documentos/urls.py
    path('export/excel/', views.despacho_export_excel, name='despacho_export_excel'),
    path('export/pdf/', views.despacho_export_pdf, name='despacho_export_pdf'),

    # ... tus otras rutas ...
]




