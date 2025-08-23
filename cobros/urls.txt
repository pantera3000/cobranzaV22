from django.urls import path
from . import views

app_name = 'cobros'

urlpatterns = [
    path('', views.cobro_list, name='cobro_list'),
    path('crear/', views.cobro_create, name='cobro_create'),
    path('exportar/excel/', views.cobro_export_excel, name='cobro_export_excel'),
    path('exportar/csv/', views.cobro_export_csv, name='cobro_export_csv'),

    path('eliminar/<int:pk>/', views.cobro_delete, name='cobro_delete'),

    path('pago-multiple/', views.pago_multiple, name='pago_multiple'),
    path('registrar-pagos-multiple/', views.registrar_pagos_multiple, name='registrar_pagos_multiple'),

    path('buscar-por-referencia/', views.buscar_por_referencia, name='buscar_por_referencia'),

    path('historial-referencias/', views.historial_referencias, name='historial_referencias'),

    path('exportar-por-referencia/', views.exportar_por_referencia, name='exportar_por_referencia'),

    path('reporte-cartera/', views.reporte_cartera, name='reporte_cartera'),

    path('exportar-cartera-excel/', views.exportar_cartera_excel, name='exportar_cartera_excel'),
]