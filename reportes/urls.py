from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    path('clientes-vencidos/', views.reporte_clientes_vencidos, name='clientes_vencidos'),
    path('cobradores/', views.reporte_cobradores, name='cobradores'),
    path('pagos-parciales/', views.reporte_pagos_parciales, name='pagos_parciales'),
    path('totales/', views.reporte_totales, name='totales'),
    path('exportar/<str:tipo>/', views.exportar_excel, name='exportar_excel'),


    path('documentos-proximos-vencer/', views.reporte_documentos_proximos_vencer, name='documentos_proximos_vencer'),
    path('top-clientes-pendientes/', views.reporte_top_clientes_pendientes, name='top_clientes_pendientes'),
]