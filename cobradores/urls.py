from django.urls import path
from . import views

app_name = 'cobradores'

urlpatterns = [
    path('', views.cobrador_list, name='cobrador_list'),
    path('<int:pk>/', views.cobrador_detail, name='cobrador_detail'),
    path('crear/', views.cobrador_create, name='cobrador_create'),
    path('editar/<int:pk>/', views.cobrador_update, name='cobrador_update'),
    path('eliminar/<int:pk>/', views.cobrador_delete, name='cobrador_delete'),
    path('exportar/excel/', views.cobrador_export_excel, name='cobrador_export_excel'),
    path('exportar/csv/', views.cobrador_export_csv, name='cobrador_export_csv'),
]