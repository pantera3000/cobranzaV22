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

    path('obtener-correlativo/', views.obtener_proximo_correlativo, name='obtener_proximo_correlativo'),

    path('meta/configurar/', views.meta_create_or_update, name='meta_create_or_update'),

    path('historial-metas/', views.historial_metas, name='historial_metas'),
    path('detalle-meta/<int:year>/<int:month>/', views.detalle_meta_mes, name='detalle_meta_mes'),



    path('cerrar-planilla/', views.cerrar_planilla_del_dia, name='cerrar_planilla_del_dia'),
    path('planilla/<int:pk>/', views.planilla_detalle, name='planilla_detalle'),
    path('historial-planillas/', views.historial_planillas, name='historial_planillas'),
    path('admin-reporte-planillas/', views.admin_reporte_planillas, name='admin_reporte_planillas'),


    path('mis-cierres/', views.mis_cierres, name='mis_cierres'),

    path('reabrir-planilla/<int:pk>/', views.reabrir_planilla, name='reabrir_planilla'),

    path('planilla/<int:pk>/pdf/', views.planilla_detalle_pdf, name='planilla_detalle_pdf'),

    path('admin-reporte-planillas/pdf/', views.admin_reporte_planillas_pdf, name='admin_reporte_planillas_pdf'),

    path('mis-cierres/pdf/', views.mis_cierres_pdf, name='mis_cierres_pdf'),

    path('cerrar-planilla-fecha/', views.cerrar_planilla_fecha_especifica, name='cerrar_planilla_fecha_especifica'),

    path('calcular-total/', views.calcular_total_cobrado, name='calcular_total_cobrado'),


    path('planilla/<int:pk>/actualizar/', views.actualizar_planilla, name='actualizar_planilla'),



    path('planilla/<int:pk>/eliminar/', views.eliminar_planilla, name='eliminar_planilla'),




]