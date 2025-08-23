from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.http import HttpResponseRedirect
import csv
from openpyxl import Workbook
from .models import Devolucion
from .forms import DevolucionForm
from documentos.models import Documento
from cobradores.models import Cobrador  # ✅ Asegúrate de tener este import
from clientes.utils import registrar_log  # ✅ Importa la función de registro
import json  # 👈 Añadir arriba del archivo
import calendar
from datetime import date






def devolucion_list(request):
    query = request.GET.get('q', '')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    cobrador_id = request.GET.get('cobrador', '')

    devoluciones = Devolucion.objects.select_related('documento', 'documento__cliente', 'cobrador').all()

    if query:
        devoluciones = devoluciones.filter(
            Q(documento__numero__icontains=query) |
            Q(documento__cliente__nombre__icontains=query) |
            Q(documento__cliente__dni_ruc__icontains=query) |
            Q(cobrador__nombre__icontains=query)
        )

    if fecha_desde:
        devoluciones = devoluciones.filter(fecha__date__gte=fecha_desde)
    if fecha_hasta:
        devoluciones = devoluciones.filter(fecha__date__lte=fecha_hasta)

    if cobrador_id:
        try:
            devoluciones = devoluciones.filter(cobrador_id=int(cobrador_id))
        except (ValueError, TypeError):
            pass

    # ✅ Calcular total devuelto
    total_devuelto = devoluciones.aggregate(total=Sum('monto'))['total'] or 0

    paginator = Paginator(devoluciones, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ✅ Cobradores para el filtro
    cobradores = Cobrador.objects.all().order_by('nombre')

    # ✅ Fechas útiles
    today = date.today()
    mes_inicio = today.replace(day=1)
    mes_fin = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    año_actual = today.year
    año_pasado = today.year - 1

    # ✅ Mes pasado
    if today.month == 1:
        mes_pasado_inicio = today.replace(year=today.year - 1, month=12, day=1)
        mes_pasado_fin = today.replace(year=today.year - 1, month=12, day=31)
    else:
        mes_pasado_inicio = today.replace(month=today.month - 1, day=1)
        mes_pasado_fin = today.replace(month=today.month - 1, day=calendar.monthrange(today.year, today.month - 1)[1])

    return render(request, 'devoluciones/devolucion_list.html', {
        'page_obj': page_obj,
        'query': query,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'cobrador_id': cobrador_id,
        'cobradores': cobradores,
        'total_devuelto': total_devuelto,
        'today': today,
        'mes_inicio': mes_inicio,
        'mes_fin': mes_fin,
        'mes_pasado_inicio': mes_pasado_inicio,
        'mes_pasado_fin': mes_pasado_fin,
        'año_actual': año_actual,
        'año_pasado': año_pasado,
    })



@transaction.atomic
def devolucion_create(request):
    documento_inicial = None
    documento_inicial_data = None

    if request.method == 'POST':
        form = DevolucionForm(request.POST)
        if form.is_valid():
            devolucion = form.save(commit=False)
            documento = devolucion.documento

            # Validar saldo no negativo
            nuevo_saldo = (
                documento.monto_total 
                - documento.monto_pagado 
                - documento.monto_devolucion 
                - devolucion.monto
            )
            if nuevo_saldo < 0:
                messages.error(
                    request,
                    f"El monto de devolución no puede ser tan alto. "
                    f"El saldo pendiente quedaría negativo."
                )
            else:
                devolucion.save()
                documento.monto_devolucion += devolucion.monto
                documento.save()

                # ✅ Registrar en el log de auditoría
                registrar_log(
                    usuario=request.user,           # 👈 Usuario del sistema (quien hizo login)
                    cobrador=devolucion.cobrador,   # 👈 Cobrador del pago
                    categoria='devolucion',
                    accion='Registró devolución',
                    descripcion=f"Monto: S/ {devolucion.monto:,.2f}, Documento: {devolucion.documento.get_numero_completo()}, Cliente: {devolucion.documento.cliente.nombre}"
                )

                messages.success(
                    request,
                    f"Devolución de S/ {devolucion.monto:,.2f} registrada exitosamente para {documento}."
                )

                # ✅ Redirigir a 'next' si existe
                next_url = request.POST.get('next')  # Viene del campo oculto
                if next_url:
                    return redirect(next_url)
                return redirect('devoluciones:devolucion_list')
        else:
            messages.error(request, 'Por favor corrige los errores.')
    else:
        documento_id = request.GET.get('documento')
        initial = {}

        if documento_id:
            try:
                doc = Documento.objects.get(pk=documento_id)
                initial['documento'] = doc
                documento_inicial = doc

                # ✅ Preparar datos para el frontend
                documento_inicial_data = json.dumps({
                    'id': doc.id,
                    'tipo_display': str(doc.get_tipo_display()),
                    'numero_completo': str(doc.get_numero_completo()),
                    'cliente_nombre': str(doc.cliente.nombre),
                    'cliente_dni': str(doc.cliente.dni_ruc),
                    'monto_total': float(doc.monto_total),
                    'saldo_pendiente': float(doc.get_saldo_pendiente()),
                })
            except Documento.DoesNotExist:
                pass

        form = DevolucionForm(initial=initial)

    return render(request, 'devoluciones/devolucion_form.html', {
        'form': form,
        'title': 'Registrar Devolución',
        'documento_inicial': documento_inicial,
        'documento_inicial_data': documento_inicial_data,
    })




def devolucion_export_excel(request):
    devoluciones = Devolucion.objects.select_related('documento', 'documento__cliente', 'cobrador').all()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Devoluciones"

    headers = ['Documento', 'Cliente', 'Monto', 'Cobrador', 'Notas', 'Fecha Devolución', 'Registrado']
    for col_num, header in enumerate(headers, 1):
        cell = sheet.cell(row=1, column=col_num)
        cell.value = header

    for dev in devoluciones:
        sheet.append([
            f"{dev.documento.get_tipo_display()} {dev.documento.serie}-{dev.documento.numero}",
            dev.documento.cliente.nombre,
            float(dev.monto),
            dev.cobrador.nombre,
            dev.notas or "",  # ✅ Notas
            dev.fecha.strftime('%d/%m/%Y %H:%M'),
            dev.creado_en.strftime('%d/%m/%Y %H:%M'),
        ])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=devoluciones.xlsx'
    workbook.save(response)
    return response


def devolucion_export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=devoluciones.csv'

    writer = csv.writer(response)
    writer.writerow(['Documento', 'Cliente', 'Monto', 'Cobrador', 'Fecha Devolución', 'Registrado'])

    for dev in Devolucion.objects.select_related('documento', 'documento__cliente', 'cobrador').all():
        writer.writerow([
            f"{dev.documento.get_tipo_display()} {dev.documento.serie}-{dev.documento.numero}",
            dev.documento.cliente.nombre,
            dev.monto,
            dev.cobrador.nombre,
            dev.notas or "",  # ✅ Notas
            dev.fecha.strftime('%d/%m/%Y %H:%M'),
            dev.creado_en.strftime('%d/%m/%Y %H:%M'),
        ])

    return response



def devolucion_delete(request, pk):
    devolucion = get_object_or_404(Devolucion, pk=pk)
    documento = devolucion.documento
    if request.method == 'POST':
        monto = devolucion.monto
        # Guardamos datos antes de eliminar
        cliente_nombre = documento.cliente.nombre
        documento_numero = f"{documento.get_tipo_display()} {documento.get_numero_completo()}"
        
        devolucion.delete()
        documento.monto_devolucion -= monto
        documento.save()
        
        # ✅ Registrar en el log
        registrar_log(
            usuario=request.user,
            cobrador=devolucion.cobrador,
            categoria='devolucion',
            accion='Eliminó devolución',
            descripcion=f"Monto: S/ {monto:,.2f}, Documento: {documento_numero}, Cliente: {cliente_nombre}"
        )

        messages.success(request, f'Devolución de S/ {monto:,.2f} eliminada correctamente.')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    
    return render(request, 'devoluciones/devolucion_confirm_delete.html', {
        'devolucion': devolucion
    })