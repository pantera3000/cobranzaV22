from django.urls import path
from . import views

app_name = 'devoluciones'

urlpatterns = [
    path('', views.devolucion_list, name='devolucion_list'),
    path('crear/', views.devolucion_create, name='devolucion_create'),
    path('exportar/excel/', views.devolucion_export_excel, name='devolucion_export_excel'),
    path('exportar/csv/', views.devolucion_export_csv, name='devolucion_export_csv'),

    path('eliminar/<int:pk>/', views.devolucion_delete, name='devolucion_delete'),
]