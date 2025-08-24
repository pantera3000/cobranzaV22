from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator

from django.db.models import Q, F
from django.http import HttpResponse
from django.contrib import messages
from .models import Documento
from .forms import DocumentoForm
from clientes.models import Cliente
from cobradores.models import Cobrador
import csv
from openpyxl import Workbook
from django.db import models
from django.utils import timezone
from datetime import date
import calendar
from django.http import JsonResponse
from django.db.models import Q, F, ExpressionWrapper, DecimalField
from cobros.models import Cobro
from devoluciones.models import Devolucion
from clientes.utils import registrar_log  # ✅ Importa la función







def cliente_search_api(request):
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse([], safe=False)
    
    clientes = Cliente.objects.filter(
        Q(nombre__icontains=query) | Q(dni_ruc__icontains=query)
    )[:10]

    results = []
    for cliente in clientes:
        results.append({
            'id': cliente.pk,
            'nombre': cliente.nombre,
            'dni_ruc': cliente.dni_ruc,
            'display': f"{cliente.nombre} ({cliente.dni_ruc})"
        })
    
    return JsonResponse(results, safe=False)




def documento_pendiente_autocomplete(request):
    query = request.GET.get('q', '')
    results = []

    if query:
        # Calcular saldo pendiente
        saldo_pendiente = ExpressionWrapper(
            F('monto_total') - F('monto_pagado') - F('monto_devolucion'),
            output_field=DecimalField()
        )

        documentos = Documento.objects.annotate(
            saldo=saldo_pendiente
        ).filter(
            saldo__gt=0  # Solo documentos con saldo pendiente
        ).filter(
            Q(numero__icontains=query) |
            Q(serie__icontains=query) |
            Q(cliente__nombre__icontains=query) |
            Q(cliente__dni_ruc__icontains=query)
        ).select_related('cliente')[:10]  # Máximo 10 resultados

        for doc in documentos:
            results.append({
                'id': doc.id,
                'text': f"{doc.get_tipo_display()} {doc.get_numero_completo()} - {doc.cliente.nombre} ({doc.cliente.dni_ruc})",
                'cliente': doc.cliente.nombre,
                'dni_ruc': doc.cliente.dni_ruc,
                'tipo': doc.get_tipo_display(),
                'numero': doc.get_numero_completo(),
                'saldo': float(doc.get_saldo_pendiente()),
                'monto_total': float(doc.monto_total),
            })

    return JsonResponse({'results': results, 'pagination': {'more': False}})




def documento_list(request):
    query = request.GET.get('q', '')
    tipo = request.GET.get('tipo', '')
    estado = request.GET.get('estado', '')
    cliente_id = request.GET.get('cliente', '')
    fecha_emision_desde = request.GET.get('fecha_emision_desde', '')
    fecha_emision_hasta = request.GET.get('fecha_emision_hasta', '')

    # ✅ Corrección segura para cliente_id
    if cliente_id and cliente_id != 'None':
        try:
            cliente_id = int(cliente_id)
        except (ValueError, TypeError):
            cliente_id = ''
    else:
        cliente_id = ''

    documentos = Documento.objects.all()

    # Filtros
    if query:
        documentos = documentos.filter(
            Q(numero__icontains=query) |
            Q(serie__icontains=query) |
            Q(cliente__nombre__icontains=query) |
            Q(cliente__dni_ruc__icontains=query)
        )
    if tipo:
        documentos = documentos.filter(tipo=tipo)
    if cliente_id:
        documentos = documentos.filter(cliente_id=cliente_id)
    if estado:
        # ✅ Calcular saldo pendiente
        documentos = documentos.annotate(
            saldo_pendiente=F('monto_total') - F('monto_pagado') - F('monto_devolucion')
        )

        if estado == 'pagado':
            documentos = documentos.filter(saldo_pendiente__lte=0)
        elif estado == 'pendiente':
            documentos = documentos.filter(
                monto_pagado__lte=0,
                monto_devolucion__lte=0,
                saldo_pendiente__gt=0,
                fecha_vencimiento__gte=timezone.now()
            )
        elif estado == 'pago_parcial':
            documentos = documentos.filter(
                monto_pagado__gt=0,
                saldo_pendiente__gt=0
            )
        elif estado == 'vencido':
            documentos = documentos.filter(
                saldo_pendiente__gt=0,
                fecha_vencimiento__lt=timezone.now()
            )

    # ✅ Filtro por fecha de emisión
    if fecha_emision_desde:
        documentos = documentos.filter(fecha_emision__date__gte=fecha_emision_desde)
    if fecha_emision_hasta:
        documentos = documentos.filter(fecha_emision__date__lte=fecha_emision_hasta)

    documentos = documentos.order_by('-fecha_emision')

    # ✅ Calcular monto total
    total_monto = documentos.aggregate(total=models.Sum('monto_total'))['total'] or 0

    paginator = Paginator(documentos, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    clientes = Cliente.objects.all().order_by('nombre')

    # ✅ Fechas útiles
    today = timezone.now().date()
    mes_inicio = today.replace(day=1)
    mes_fin = today.replace(day=calendar.monthrange(today.year, today.month)[1])

    if today.month == 1:
        mes_pasado_inicio = today.replace(year=today.year - 1, month=12, day=1)
        mes_pasado_fin = today.replace(year=today.year - 1, month=12, day=31)
    else:
        mes_pasado_inicio = today.replace(month=today.month - 1, day=1)
        mes_pasado_fin = today.replace(month=today.month - 1, day=calendar.monthrange(today.year, today.month - 1)[1])

    año_actual = today.year
    año_pasado = today.year - 1

    return render(request, 'documentos/documento_list.html', {
        'page_obj': page_obj,
        'query': query,
        'tipo': tipo,
        'estado': estado,
        'cliente_id': cliente_id,
        'clientes': clientes,
        'fecha_emision_desde': fecha_emision_desde,
        'fecha_emision_hasta': fecha_emision_hasta,
        'total_monto': total_monto,
        'today': today,
        'mes_inicio': mes_inicio,
        'mes_fin': mes_fin,
        'mes_pasado_inicio': mes_pasado_inicio,
        'mes_pasado_fin': mes_pasado_fin,
        'año_actual': año_actual,
        'año_pasado': año_pasado,
    })





def documento_create(request):
    if request.method == 'POST':
        form = DocumentoForm(request.POST)
        if form.is_valid():
            documento = form.save()

            # ✅ Registrar en el log de auditoría
            registrar_log(
                usuario=request.user,           # Usuario que está logueado
                cobrador=documento.cobrador,    # Cobrador del documento
                categoria='documento',          # Categoría del log
                accion='Creó documento',        # Acción realizada
                descripcion=f"Tipo: {documento.get_tipo_display()}, Número: {documento.get_numero_completo()}, Cliente: {documento.cliente.nombre}"
            )

            messages.success(request, f'Documento {documento.get_numero_completo()} creado exitosamente.')
            # return redirect('documentos:documento_list')

            # ✅ Redirigir a 'next' si existe
            next_url = request.POST.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('documentos:documento_list')


        else:
            messages.error(request, 'Por favor corrige los errores.')
    else:
        # ✅ Obtener ID del cliente desde la URL
        cliente_id = request.GET.get('cliente')
        initial = {}
        if cliente_id:
            try:
                # ✅ Solo pasa el ID, no el objeto
                initial['cliente'] = int(cliente_id)
            except (ValueError, TypeError):
                pass

        form = DocumentoForm(initial=initial)

    return render(request, 'documentos/documento_form.html', {
        'form': form,
        'title': 'Crear Documento'
    })


def documento_update(request, pk):
    documento = get_object_or_404(Documento, pk=pk)
    if request.method == 'POST':
        form = DocumentoForm(request.POST, instance=documento)
        if form.is_valid():
            form.save()
            messages.success(request, 'Documento actualizado exitosamente.')

            # return redirect('documentos:documento_list')

            # ✅ Redirigir a 'next' si existe
            next_url = request.POST.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('documentos:documento_list')


    else:
        form = DocumentoForm(instance=documento)
    return render(request, 'documentos/documento_form.html', {
        'form': form,
        'title': 'Editar Documento'
    })


def documento_delete(request, pk):
    documento = get_object_or_404(Documento, pk=pk)
    
    # ✅ Validación: no se puede eliminar si tiene pagos o devoluciones
    if documento.monto_pagado > 0 or documento.monto_devolucion > 0:
        messages.error(
            request, 
            'No se puede eliminar un documento con pagos o devoluciones registrados.'
        )
        return redirect('documentos:documento_detail', pk=pk)
    
    if request.method == 'POST':
        num = documento.get_numero_completo()  # ✅ Usas el método, no propiedad
        documento.delete()
        messages.success(request, f'Documento {num} eliminado exitosamente.')
        return redirect('documentos:documento_list')
    
    return render(request, 'documentos/documento_confirm_delete.html', {
        'documento': documento
    })


def documento_export_excel(request):
    from django.db.models import F

    documentos = Documento.objects.all().select_related('cliente', 'cobrador')
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Documentos"

    headers = [
        'Tipo', 'Serie', 'Número', 'Cliente', 'Cobrador',
        'Monto Total', 'Monto Pagado', 'Devolución',
        'Saldo Pendiente', 'Estado', 'Días', 'Emisión', 'Vencimiento'
    ]
    for col_num, header in enumerate(headers, 1):
        cell = sheet.cell(row=1, column=col_num)
        cell.value = header

    for doc in documentos:
        saldo = doc.get_saldo_pendiente()
        estado = doc.get_estado()
        dias = doc.get_dias_restantes()
        cobrador = doc.cobrador.nombre if doc.cobrador else '-'
        sheet.append([
            doc.get_tipo_display(),
            doc.serie or '-',
            doc.numero,
            doc.cliente.nombre,
            cobrador,
            float(doc.monto_total),
            float(doc.monto_pagado),
            float(doc.monto_devolucion),
            float(saldo),
            estado.capitalize(),
            f"{dias} días",
            doc.fecha_emision.strftime('%d/%m/%Y %H:%M'),
            doc.fecha_vencimiento.strftime('%d/%m/%Y %H:%M'),
        ])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=documentos.xlsx'
    workbook.save(response)
    return response


def documento_export_csv(request):
    from django.db.models import F

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=documentos.csv'

    writer = csv.writer(response)
    writer.writerow([
        'Tipo', 'Serie', 'Número', 'Cliente', 'Cobrador',
        'Monto Total', 'Monto Pagado', 'Devolución',
        'Saldo', 'Estado', 'Días', 'Emisión', 'Vencimiento'
    ])

    for doc in Documento.objects.all().select_related('cliente', 'cobrador'):
        saldo = doc.get_saldo_pendiente()
        estado = doc.get_estado()
        dias = doc.get_dias_restantes()
        cobrador = doc.cobrador.nombre if doc.cobrador else '-'
        writer.writerow([
            doc.get_tipo_display(),
            doc.serie or '-',
            doc.numero,
            doc.cliente.nombre,
            cobrador,
            doc.monto_total,
            doc.monto_pagado,
            doc.monto_devolucion,
            saldo,
            estado,
            f"{dias} días",
            doc.fecha_emision.strftime('%d/%m/%Y %H:%M'),
            doc.fecha_vencimiento.strftime('%d/%m/%Y %H:%M'),
        ])

    return response


def documento_detail(request, pk):
    documento = get_object_or_404(Documento, pk=pk)
    
    # ✅ Obtener cobros y devoluciones
    cobros_list = Cobro.objects.filter(documento=documento).order_by('-fecha')
    devoluciones_list = Devolucion.objects.filter(documento=documento).order_by('-fecha')

    # ✅ Calcular cuántos documentos tiene cada referencia
    # ✅ Calcular cuántos documentos tiene cada referencia (en todo el sistema)
    referencias = [cobro.referencia for cobro in cobros_list if cobro.referencia]
    referencia_count = {}
    if referencias:
        # Contar todos los cobros con esas referencias
        cobros_globales = Cobro.objects.filter(referencia__in=referencias)
        for cobro in cobros_globales:
            if cobro.referencia:
                if cobro.referencia not in referencia_count:
                    referencia_count[cobro.referencia] = 0
                referencia_count[cobro.referencia] += 1

    # ✅ Paginación para Cobros
    cobros_paginator = Paginator(cobros_list, 20)
    cobros_page_number = request.GET.get('cobros_page')
    cobros_page_obj = cobros_paginator.get_page(cobros_page_number)

    # ✅ Paginación para Devoluciones
    devoluciones_paginator = Paginator(devoluciones_list, 20)
    devoluciones_page_number = request.GET.get('devoluciones_page')
    devoluciones_page_obj = devoluciones_paginator.get_page(devoluciones_page_number)

    return render(request, 'documentos/documento_detail.html', {
        'documento': documento,
        'cobros': cobros_page_obj,
        'devoluciones': devoluciones_page_obj,
        'referencia_count': referencia_count,  # ✅ Añadido
    })