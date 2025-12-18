import calendar
from django.shortcuts import render, get_object_or_404, redirect

from datetime import datetime, time
from datetime import date, time

import datetime
from django.utils import timezone

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum  # ✅ Asegúrate de tener Sum
from django.db.models import F
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from clientes.models import Cliente
from django.http import HttpResponseRedirect
import csv
from openpyxl import Workbook
from .models import Cobro
from .forms import CobroForm
from documentos.models import Documento
import json
from datetime import date
import calendar
from cobradores.models import Cobrador  # ✅ Falta esta línea
from decimal import Decimal
from openpyxl import Workbook
from django.http import HttpResponse
from calendar import monthrange

from decimal import Decimal, InvalidOperation
from .utils import generar_correlativo  # ✅ Asegúrate de tener esta función
from django.http import JsonResponse

from clientes.utils import registrar_log  # ✅ Importar
from django.contrib.auth.decorators import login_required
from django.db import transaction
import json
from django.contrib.auth.decorators import permission_required
from clientes.models import LogActividad
from django.db.models import Count, Sum, Max  # ✅ Usamos agregaciones de Django

from .models import MetaMensual
from datetime import date

import traceback  # ✅ Para ver el error completo


from django.contrib.admin.views.decorators import staff_member_required


from .models import PlanillaCierre, DepositoParcial, Cobro



from django.template.loader import render_to_string
from weasyprint import HTML
import os

from django.http import HttpResponseForbidden





from datetime import datetime
import pytz


from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import PlanillaCierre, Cobro
from django.utils import timezone
from decimal import Decimal

@login_required
@require_POST
def actualizar_planilla(request, pk):
    planilla = get_object_or_404(PlanillaCierre, pk=pk)

    # ✅ Solo staff o superusuario pueden actualizar
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "No tienes permiso para actualizar este cierre.")
        return redirect('cobros:planilla_detalle', pk=planilla.pk)

    # Zona horaria
    lima_tz = pytz.timezone('America/Lima')
    inicio_dia = lima_tz.localize(datetime.combine(planilla.fecha, time.min))
    fin_dia = lima_tz.localize(datetime.combine(planilla.fecha, time.max))

    # Calcular nuevo total cobrado ese día
    nuevo_total = Cobro.objects.filter(
        cobrador=planilla.cobrador,
        fecha__gte=inicio_dia,
        fecha__lte=fin_dia
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

    # Actualizar planilla
    planilla.total_cobrado = nuevo_total
    planilla.actualizado_en = timezone.now()  # ✅ Registrar cuándo se actualizó
    planilla.save()  # Esto dispara actualizar_estado()

    messages.success(request, f"Cierre actualizado. Nuevo total: S/ {nuevo_total:.2f}")

    # ✅ Registrar en log (opcional)
    registrar_log(
        usuario=request.user,
        cobrador=planilla.cobrador,
        categoria='planilla',
        accion='Actualizó cierre',
        descripcion=f"Planilla ID: {pk}, Fecha: {planilla.fecha}, Total actualizado a S/ {nuevo_total:.2f}"
    )

    return redirect('cobros:planilla_detalle', pk=planilla.pk)


































# @staff_member_required
# def historial_metas(request):
@login_required
def historial_metas(request):
    # ✅ Permitir acceso si es staff, superuser o pertenece al grupo "Encargados Reparto"
    if not (
        request.user.is_staff or
        request.user.is_superuser or
        request.user.groups.filter(name='Encargados Reparto').exists()
    ):
        # return HttpResponseForbidden("No tienes permiso para acceder a esta página.")
        return render(request, 'cobros/no_permiso.html', {
            'titulo': 'Acceso denegado',
            'mensaje': 'No tienes permiso para acceder a esta página.',
            'url_anterior': request.META.get('HTTP_REFERER')  # Página de donde vino
        })



    metas = MetaMensual.objects.all().order_by('-mes')
    data_metas = []

    for meta in metas:
        primer_dia = meta.mes
        _, last_day = monthrange(primer_dia.year, primer_dia.month)
        ultimo_dia = primer_dia.replace(day=last_day)

        # ✅ Corregido: usar datetime.datetime.combine y datetime.time.min/max
        fecha_inicio = timezone.make_aware(
            datetime.combine(primer_dia, time.min)
        )
        fecha_fin = timezone.make_aware(
            datetime.combine(ultimo_dia, time.max)
        )

        cobros_mes = Cobro.objects.filter(
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

        porcentaje = 0
        if meta.monto_objetivo > 0:
            porcentaje = min((cobros_mes / meta.monto_objetivo) * 100, 100)

        data_metas.append({
            'meta': meta,
            'cobrado': cobros_mes,
            'porcentaje': porcentaje
        })

    return render(request, 'cobros/historial_metas.html', {
        'data_metas': data_metas
    })



# @staff_member_required
# def detalle_meta_mes(request, year, month):


@login_required
def detalle_meta_mes(request, year, month):
    # ✅ Verificar permisos: staff, superuser o encargado de reparto
    if not (
        request.user.is_staff or
        request.user.is_superuser or
        request.user.groups.filter(name='Encargados Reparto').exists()
    ):
        return render(request, 'cobros/no_permiso.html', {
            'titulo': 'Acceso denegado',
            'mensaje': 'No tienes permiso para acceder a esta página.',
            'url_anterior': request.META.get('HTTP_REFERER')  # Página de donde vino
        })

    try:
        # ✅ Convertir a entero
        year = int(year)
        month = int(month)
    except (ValueError, TypeError) as e:
        return render(request, 'cobros/detalle_meta_mes.html', {
            'error': f'Año o mes inválido: {year}/{month}',
        }, status=400)

    try:
        # ✅ Validar mes
        if month < 1 or month > 12:
            return render(request, 'cobros/detalle_meta_mes.html', {
                'error': f'Mes inválido: {month}. Debe estar entre 1 y 12.',
            }, status=400)

        # ✅ Fecha del mes
        mes_fecha = datetime(year, month, 1).date()  # ✅ Correcto

        # ✅ Intentar obtener la meta
        try:
            meta = MetaMensual.objects.get(mes=mes_fecha)
        except MetaMensual.DoesNotExist:
            meta = None

        # ✅ Fechas de inicio y fin del mes
        _, last_day = calendar.monthrange(year, month)
        fecha_inicio = timezone.make_aware(
            datetime(year, month, 1, 0, 0, 0)  # ✅ Correcto
        )
        fecha_fin = timezone.make_aware(
            datetime(year, month, last_day, 23, 59, 59)  # ✅ Correcto
        )

        # ✅ Cobros del mes agrupados por cobrador
        cobros_por_cobrador = (
            Cobro.objects
            .filter(
                fecha__gte=fecha_inicio,
                fecha__lte=fecha_fin,
                cobrador__isnull=False  # Asegúrate de que cobrador no sea None
            )
            .values('cobrador__nombre', 'cobrador__id')
            .annotate(total=Sum('monto'))
            .order_by('-total')
        )

        total_mes = sum(c['total'] for c in cobros_por_cobrador)

        # ✅ Renderizar
        return render(request, 'cobros/detalle_meta_mes.html', {
            'meta': meta,
            'year': year,
            'month': month,
            'month_name': mes_fecha.strftime('%B'),
            'cobros_por_cobrador': cobros_por_cobrador,
            'total_mes': total_mes,
        })

    except Exception as e:
        # ✅ Captura cualquier error y muéstralo
        error_msg = str(e)
        print("❌ Error en detalle_meta_mes:", error_msg)
        print("📌 Detalle del error:")
        import traceback
        traceback.print_exc()

        return render(request, 'cobros/detalle_meta_mes.html', {
            'error': f'Error interno: {error_msg}',
        }, status=500)






@staff_member_required
def meta_create_or_update(request):
    today = date.today()
    mes_actual = today.replace(day=1)

    # Obtener o crear la meta del mes
    meta, created = MetaMensual.objects.get_or_create(
        mes=mes_actual,
        defaults={'monto_objetivo': 0}
    )

    if request.method == 'POST':
        monto = request.POST.get('monto_objetivo')
        try:
            monto = float(monto)
            if monto < 0:
                raise ValueError("El monto no puede ser negativo")
            meta.monto_objetivo = monto
            meta.save()
            messages.success(request, f'Meta mensual actualizada a S/ {monto:,.2f}')
        except (ValueError, TypeError):
            messages.error(request, 'Monto inválido')

        return redirect('cobros:reporte_cartera')

    return render(request, 'cobros/meta_form.html', {
        'meta': meta,
        'created': created
    })





def obtener_proximo_correlativo(request):
    """Devuelve el próximo correlativo disponible"""
    proximo = generar_correlativo()
    return JsonResponse({'correlativo': proximo})



@permission_required('clientes.view_logactividad', raise_exception=True)
def log_actividad(request):
    logs = LogActividad.objects.all().select_related('usuario', 'cobrador').order_by('-fecha')

    categoria = request.GET.get('categoria')
    if categoria:
        logs = logs.filter(categoria=categoria)

    paginator = Paginator(logs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'clientes/log_actividad.html', {
        'page_obj': page_obj,
        'categoria': categoria,
        'categorias': LogActividad.CATEGORIA_OPCIONES
    })




from .utils import generar_correlativo  # ✅ Importa arriba

@transaction.atomic
def cobro_create(request):
    documento_inicial = None
    documento_inicial_data = None

    if request.method == 'POST':
        form = CobroForm(request.POST)
        if form.is_valid():
            cobro = form.save(commit=False)
            documento = cobro.documento
            saldo_pendiente = documento.get_saldo_pendiente()

            if cobro.monto <= 0:
                messages.error(request, "El monto debe ser mayor a 0.")
            else:
                if cobro.monto > saldo_pendiente:
                    exceso = cobro.monto - saldo_pendiente
                    messages.warning(
                        request,
                        f"Pago mayor al saldo. S/ {exceso:.2f} se registrará como saldo a favor del cliente."
                    )

                # ✅ Asignar quién registró este pago
                cobro.usuario_registro = request.user  # 👈 ¡Este es el cambio clave!

                # ✅ Generar correlativo SOLO aquí, al final
                cobro.correlativo = generar_correlativo()
                cobro.save()

                # ✅ Registrar log
                registrar_log(
                    usuario=request.user,
                    cobrador=cobro.cobrador,
                    categoria='cobro',
                    accion='Registró pago',
                    descripcion=f"Monto: S/ {cobro.monto:,.2f}, Documento: {documento}, Cliente: {documento.cliente.nombre}, Referencia: {cobro.referencia or '-'}"
                )

                messages.success(
                    request,
                    f"Pago de S/ {cobro.monto:,.2f} registrado exitosamente para {documento}."
                )

                next_url = request.POST.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('cobros:cobro_list')
        else:
            messages.error(request, 'Por favor corrige los errores.')
    else:
        documento_id = request.GET.get('documento')
        initial = {}

        if documento_id:
            try:
                doc = Documento.objects.get(pk=documento_id)
                saldo = doc.get_saldo_pendiente()

                if saldo > 0:
                    initial['documento'] = doc
                    documento_inicial = doc

                    data_dict = {
                        'id': doc.id,
                        'tipo_display': str(doc.get_tipo_display()),
                        'numero_completo': str(doc.get_numero_completo()),
                        'cliente_nombre': str(doc.cliente.nombre),
                        'cliente_dni': str(doc.cliente.dni_ruc),
                        'monto_total': float(doc.monto_total),
                        'saldo_pendiente': float(saldo),
                    }
                    documento_inicial_data = json.dumps(data_dict)
            except Documento.DoesNotExist:
                pass

        form = CobroForm(initial=initial)

    return render(request, 'cobros/cobro_form.html', {
        'form': form,
        'title': 'Registrar Pago',
        'documento_inicial': documento_inicial,
        'documento_inicial_data': documento_inicial_data,
    })



def cobro_list(request):
    query = request.GET.get('q', '')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    cobrador_id = request.GET.get('cobrador', '')

    # Iniciar queryset
    cobros = Cobro.objects.select_related('documento', 'documento__cliente', 'cobrador').all()

    # Filtros
    if query:
        cobros = cobros.filter(
            Q(documento__numero__icontains=query) |
            Q(documento__cliente__nombre__icontains=query) |
            Q(documento__cliente__dni_ruc__icontains=query) |
            Q(cobrador__nombre__icontains=query)
        )

    if fecha_desde:
        cobros = cobros.filter(fecha__date__gte=fecha_desde)
    if fecha_hasta:
        cobros = cobros.filter(fecha__date__lte=fecha_hasta)

    if cobrador_id:
        try:
            cobros = cobros.filter(cobrador_id=int(cobrador_id))
        except (ValueError, TypeError):
            cobrador_id = None  # Si no es válido, ignora el filtro

    # Obtener el cobrador seleccionado para mostrar en el filtro activo
    cobrador_seleccionado = None
    if cobrador_id:
        try:
            cobrador_seleccionado = Cobrador.objects.get(id=cobrador_id)
        except Cobrador.DoesNotExist:
            cobrador_id = None  # Si no existe, ignora

    # Calcular total cobrado
    total_cobrado = cobros.aggregate(total=Sum('monto'))['total'] or 0

    # ✅ Calcular cuántos documentos tiene cada referencia
    referencia_count = {}
    for cobro in cobros:
        ref = cobro.referencia
        if ref:
            if ref not in referencia_count:
                referencia_count[ref] = 0
            referencia_count[ref] += 1

    # Paginación
    paginator = Paginator(cobros, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Opciones para filtros rápidos
    cobradores = Cobrador.objects.all().order_by('nombre')
    today = date.today()
    mes_inicio = today.replace(day=1)
    mes_fin = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    año_actual = today.year
    año_pasado = today.year - 1

    # Mes pasado
    if today.month == 1:
        mes_pasado_inicio = today.replace(year=today.year - 1, month=12, day=1)
        mes_pasado_fin = today.replace(year=today.year - 1, month=12, day=31)
    else:
        mes_pasado_inicio = today.replace(month=today.month - 1, day=1)
        mes_pasado_fin = today.replace(month=today.month - 1, day=calendar.monthrange(today.year, today.month - 1)[1])

    # Contexto completo
    context = {
        'page_obj': page_obj,
        'query': query,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'cobrador_id': cobrador_id,
        'cobrador_seleccionado': cobrador_seleccionado,
        'cobradores': cobradores,
        'today': today,
        'mes_inicio': mes_inicio,
        'mes_fin': mes_fin,
        'mes_pasado_inicio': mes_pasado_inicio,
        'mes_pasado_fin': mes_pasado_fin,
        'total_cobrado': total_cobrado,
        'año_actual': año_actual,
        'año_pasado': año_pasado,
        'referencia_count': referencia_count,  # ✅ Añadido
    }

    return render(request, 'cobros/cobro_list.html', context)




    return render(request, 'cobros/cobro_list.html', {
        'page_obj': page_obj,
        'query': query,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    })


# cobros/views.py
from django.utils import timezone

def cobro_export_excel(request):
    """
    Exporta los cobros a Excel, aplicando los mismos filtros que en la vista de listado.
    Incluye las columnas 'Referencia' y 'Notas'.
    ✅ Ahora muestra las fechas en hora peruana (UTC-5)
    """
    # === 1. Obtener filtros (igual que en cobro_list) ===
    query = request.GET.get('q', '')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    cobrador_id = request.GET.get('cobrador', '')

    # === 2. Obtener y filtrar cobros ===
    cobros = Cobro.objects.select_related(
        'documento', 'documento__cliente', 'cobrador'
    ).all().order_by('-fecha')

    # Filtro por búsqueda
    if query:
        cobros = cobros.filter(
            Q(documento__numero__icontains=query) |
            Q(documento__cliente__nombre__icontains=query) |
            Q(documento__cliente__dni_ruc__icontains=query) |
            Q(cobrador__nombre__icontains=query)
        )

    # Filtro por fecha
    if fecha_desde:
        cobros = cobros.filter(fecha__date__gte=fecha_desde)
    if fecha_hasta:
        cobros = cobros.filter(fecha__date__lte=fecha_hasta)

    # Filtro por cobrador
    if cobrador_id:
        try:
            cobros = cobros.filter(cobrador_id=int(cobrador_id))
        except (ValueError, TypeError):
            pass

    # === 3. Crear libro de Excel ===
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Cobros"

    # === 4. Encabezados (con Referencia y Notas) ===
    headers = [
        'Documento',
        'Cliente',
        'Monto',
        'Cobrador',
        'Referencia',
        'Notas',
        'Tipo de Pago',
        'Fecha Pago',
        'Día del Pago',      # ✅ Nueva columna (sin hora)
        'Fecha Registro'
        'Día de Registro',    # ✅ Solo fecha (registro)
    ]
    for col_num, header in enumerate(headers, 1):
        cell = sheet.cell(row=1, column=col_num)
        cell.value = header

    # === 5. Agregar datos con conversión de zona horaria ===
    for cobro in cobros:
        try:
            tipo_pago_display = cobro.get_tipo_pago_display() or ""
        except:
            tipo_pago_display = ""

        # ✅ Convertir a hora local (Perú)
        fecha_local = timezone.localtime(cobro.fecha)
        creado_local = timezone.localtime(cobro.creado_en)

        sheet.append([
            f"{cobro.documento.get_tipo_display()} {cobro.documento.get_numero_completo()}",
            cobro.documento.cliente.nombre,
            float(cobro.monto),
            cobro.cobrador.nombre,
            cobro.referencia or "",
            cobro.notas or "",
            tipo_pago_display,
            fecha_local.strftime('%d/%m/%Y %H:%M'),          # ✅ Hora local
            fecha_local.strftime('%Y-%m-%d'),                # ✅ Solo fecha (ideal para filtro)
            creado_local.strftime('%d/%m/%Y %H:%M'),         # ✅ Hora local
            creado_local.strftime('%Y-%m-%d'),              # ✅ Solo fecha (registro)
        ])

    # === 6. Ajustar ancho de columnas ===
    column_widths = [18, 30, 12, 20, 20, 30, 18, 18, 14, 18, 14]  # Ajustado para nueva columna
    for i, width in enumerate(column_widths, 1):
        sheet.column_dimensions[chr(64 + i)].width = width


    # === 7. Activar autofiltro en la primera fila ===
    sheet.auto_filter.ref = sheet.dimensions  # Aplica filtro desde A1 hasta la última celda


    # === 8. Preparar respuesta HTTP ===
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=cobros.xlsx'
    workbook.save(response)
    return response




def cobro_export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=cobros.csv'

    writer = csv.writer(response)
    writer.writerow(['Documento', 'Cliente', 'Monto', 'Cobrador', 'Fecha Pago', 'Fecha Registro'])

    for cobro in Cobro.objects.select_related('documento', 'documento__cliente', 'cobrador').all():
        writer.writerow([
            f"{cobro.documento.get_tipo_display()} {cobro.documento.serie}-{cobro.documento.numero}",
            cobro.documento.cliente.nombre,
            cobro.monto,
            cobro.cobrador.nombre,
            cobro.fecha.strftime('%d/%m/%Y %H:%M'),
            cobro.creado_en.strftime('%d/%m/%Y %H:%M'),
        ])

    return response




def cobro_delete(request, pk):
    cobro = get_object_or_404(Cobro, pk=pk)
    if request.method == 'POST':
        monto = cobro.monto
        # Guardamos datos antes de eliminar
        documento = cobro.documento
        cliente_nombre = documento.cliente.nombre
        documento_numero = f"{documento.get_tipo_display()} {documento.get_numero_completo()}"
        referencia = cobro.referencia or "Sin referencia"  # ✅ Obtenemos la referencia

        cobro.delete()  # ← Aquí se actualiza monto_pagado (vía modelo)

        # ✅ Registrar en el log
        registrar_log(
            usuario=request.user,
            cobrador=cobro.cobrador,
            categoria='cobro',
            accion='Eliminó pago',
            descripcion=f"Monto: S/ {monto:,.2f}, Documento: {documento_numero}, Cliente: {cliente_nombre}, Referencia: {referencia}"
        )

        messages.success(request, f'Pago de S/ {monto:,.2f} eliminado correctamente.')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    return render(request, 'cobros/cobro_confirm_delete.html', {
        'cobro': cobro
    })









def pago_multiple(request):
    """Página para realizar múltiples pagos a la vez"""
    query = request.GET.get('q', '')
    page_number = request.GET.get('page', 1)

    # Filtrar documentos con saldo pendiente
    documentos = Documento.objects.filter(
        monto_total__gt=F('monto_pagado') + F('monto_devolucion')
    ).select_related('cliente').order_by('-fecha_emision')

    # Aplicar búsqueda si existe
    if query:
        documentos = documentos.filter(
            Q(cliente__nombre__icontains=query) |
            Q(numero__icontains=query) |
            Q(serie__icontains=query)
        )
    else:
        # Si no hay búsqueda, mostrar solo los últimos 10 (pero permitir paginación completa si se quiere)
        # Opcional: puedes dejar todos, o limitar aquí con Paginator
        pass  # Dejamos que el Paginator maneje todo

    # ✅ Aplicar paginación SIEMPRE
    paginator = Paginator(documentos, 20)  # 10 por página
    documentos_page = paginator.get_page(page_number)

    # ✅ Si no hay búsqueda, asegurarnos de que la página 1 muestre los más recientes
    # Pero no cortamos el QuerySet antes de paginar

    cobradores = Cobrador.objects.all()

    return render(request, 'cobros/pago_multiple.html', {
        'documentos': documentos_page,
        'query': query,
        'cobradores': cobradores
    })

# cobros/views.py
# cobros/views.py
# cobros/views.py
@transaction.atomic
def registrar_pagos_multiple(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        data = request.POST
        cobrador_id = data.get('cobrador')
        if not cobrador_id:
            return JsonResponse({'error': 'Debe seleccionar un cobrador'}, status=400)

        try:
            cobrador = Cobrador.objects.get(pk=cobrador_id)
        except Cobrador.DoesNotExist:
            return JsonResponse({'error': 'Cobrador no válido'}, status=400)

        referencia = data.get('referencia', '').strip()
        if not referencia:
            return JsonResponse({'error': 'La referencia es requerida'}, status=400)

        notas = data.get('notas', '').strip()

        total_registrado = 0
        errores = []

        pago_keys = [key for key in data.keys() if key.startswith('pago_') and key != 'pago_multiple']

        for key in pago_keys:
            doc_id_str = key.replace('pago_', '')
            try:
                doc_id = int(doc_id_str)
            except (ValueError, TypeError):
                errores.append(f"ID de documento inválido: {doc_id_str}")
                continue

            monto_str = data[key].replace(',', '.')
            try:
                monto = Decimal(monto_str)
                if monto <= 0:
                    continue
            except (InvalidOperation, ValueError):
                errores.append(f"Monto inválido para documento {doc_id}: '{data[key]}'")
                continue

            try:
                documento = Documento.objects.get(pk=doc_id)
                saldo = documento.get_saldo_pendiente()
                if monto > saldo:
                    print(f"⚠️ Pago mayor al saldo para {documento}: S/ {monto - saldo:.2f}")

                tipo_pago = data.get(f'tipo_pago_{doc_id}', '')

                # ✅ Crear el cobro asignando quién lo registró
                cobro = Cobro(
                    documento=documento,
                    cobrador=cobrador,
                    monto=monto,
                    fecha=timezone.now(),
                    referencia=referencia,
                    notas=notas,
                    tipo_pago=tipo_pago,
                    correlativo=generar_correlativo(),  # ✅ Genera uno por pago
                    usuario_registro=request.user      # ✅ ¡Este es el cambio clave!
                )
                cobro.save()
                total_registrado += monto

            except Documento.DoesNotExist:
                errores.append(f"Documento {doc_id} no existe")
            except Exception as e:
                errores.append(f"Error con documento {doc_id}: {str(e)}")

        # ✅ Registrar log
        if total_registrado > 0:
            try:
                from clientes.utils import registrar_log
                registrar_log(
                    usuario=request.user,
                    cobrador=cobrador,
                    categoria='cobro',
                    accion='Registró pago múltiple',
                    descripcion=f"Referencia: {referencia}, Total: S/ {total_registrado:.2f}, {len(pago_keys)} documentos, Notas: {notas or '-'}"
                )
            except Exception as log_error:
                print(f"❌ Error al registrar log: {log_error}")

        if errores:
            return JsonResponse({
                'success': False,
                'error': 'Errores al registrar pagos',
                'detalles': errores
            }, status=400)

        return JsonResponse({
            'success': True,
            'total_registrado': float(total_registrado),
        })

    except Exception as e:
        return JsonResponse({'error': 'Error interno del servidor'}, status=500)




def buscar_por_referencia(request):
    """Buscar pagos por referencia"""
    query = request.GET.get('q', '')
    pagos = []
    total_monto = 0
    referencia_count = {}

    if query:
        pagos = Cobro.objects.filter(
            referencia__icontains=query
        ).select_related('documento', 'documento__cliente', 'cobrador').order_by('-fecha')

        # ✅ Calcular total y conteo por referencia
        total_monto = sum(cobro.monto for cobro in pagos)

        for cobro in pagos:
            ref = cobro.referencia
            if ref:
                if ref not in referencia_count:
                    referencia_count[ref] = 0
                referencia_count[ref] += 1

    return render(request, 'cobros/buscar_por_referencia.html', {
        'query': query,
        'pagos': pagos,
        'total_monto': total_monto,
        'referencia_count': referencia_count,  # ✅ Añadido
    })


def historial_referencias(request):
    """Listado de todas las referencias con filtros y búsqueda"""
    # Obtener filtros
    filtro_fecha = request.GET.get('fecha')
    query = request.GET.get('q', '').strip()  # ✅ Obtener búsqueda

    # Empezamos con cobros que tengan referencia
    cobros = Cobro.objects.exclude(referencia__isnull=True).exclude(referencia='')

    # Aplicar búsqueda por referencia (si hay query)
    if query:
        cobros = cobros.filter(referencia__icontains=query)

    # Aplicar filtro por fecha usando zona horaria de Lima
    hoy = timezone.localtime(timezone.now()).date()

    if filtro_fecha == 'hoy':
        cobros = cobros.filter(fecha__date=hoy)
    elif filtro_fecha == 'ayer':
        ayer = hoy - timedelta(days=1)
        cobros = cobros.filter(fecha__date=ayer)
    elif filtro_fecha == 'semana':
        inicio_semana = hoy - timedelta(days=hoy.weekday())  # Lunes de esta semana
        cobros = cobros.filter(fecha__date__gte=inicio_semana)
    elif filtro_fecha == 'mes':
        cobros = cobros.filter(fecha__date__year=hoy.year, fecha__date__month=hoy.month)

    # Agrupar por referencia
    referencias = (
        cobros.values('referencia')
        .annotate(
            count=Count('id'),
            total=Sum('monto'),
            fecha=Max('fecha')  # Último pago con esa referencia
        )
        .order_by('-fecha')
    )

    # Paginación
    paginator = Paginator(referencias, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'cobros/historial_referencias.html', {
        'page_obj': page_obj,
        'filtro_fecha': filtro_fecha,
        'query': query,  # ✅ Pasar query al template
    })








def exportar_por_referencia(request):
    """Exportar pagos por referencia a Excel"""
    query = request.GET.get('q', '').strip()

    if not query:
        # Si no hay referencia, devolver vacío o error
        wb = Workbook()
        ws = wb.active
        ws.title = "Pagos por Referencia"
        ws.append(["Error: No se especificó una referencia"])
        filename = f"pagos_sin_referencia_{timezone.now().strftime('%Y%m%d_%H%M')}.xlsx"
    else:
        # Filtrar pagos por referencia
        pagos = Cobro.objects.filter(
            referencia__icontains=query
        ).select_related('documento', 'documento__cliente', 'cobrador').order_by('-fecha')

        wb = Workbook()
        ws = wb.active
        ws.title = f"Pagos - {query}"

        # Encabezados
        headers = ['Documento', 'Cliente', 'Monto (S/)', 'Cobrador', 'Fecha Pago', 'Referencia']
        ws.append(headers)

        # Datos
        for cobro in pagos:
            ws.append([
                f"{cobro.documento.get_tipo_display()} {cobro.documento.get_numero_completo()}",
                cobro.documento.cliente.nombre,
                float(cobro.monto),
                cobro.cobrador.nombre,
                cobro.fecha.strftime('%d/%m/%Y %H:%M'),
                cobro.referencia or ''
            ])

        # Ajustar ancho de columnas
        for col in ['A', 'B', 'F']:
            ws.column_dimensions[col].width = 20
        ws.column_dimensions['C'].width = 12
        ws.column_dimensions['D'].width = 18
        ws.column_dimensions['E'].width = 18

        filename = f"pagos_{query}_{timezone.now().strftime('%Y%m%d_%H%M')}.xlsx"

    # Preparar respuesta
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response






def reporte_cartera(request):

    # ✅ Usuarios autorizados
    usuarios_permitidos = ['adminaqp', 'juanc', 'CHRISTIAN']  # 👈 Cambia por los usernames que desees

    if not request.user.is_authenticated or request.user.username not in usuarios_permitidos:
        messages.warning(request, 'No tienes permiso para acceder al reporte de cartera.')
        return redirect('clientes:cliente_list')  # 👈 Cambia por tu URL de inicio

    # Si llega aquí, el usuario está autorizado
    today = timezone.now().date()




    """Reporte de Cartera de Cobranzas"""
    today = timezone.now().date()


    # ✅ Obtener meta mensual (si existe)
    try:
        meta = MetaMensual.objects.get(mes__year=today.year, mes__month=today.month)
    except MetaMensual.DoesNotExist:
        meta = None

    # === 1. Resumen General ===
    documentos = Documento.objects.all()
    total_facturado = documentos.aggregate(total=Sum('monto_total'))['total'] or 0
    total_pagado = sum(doc.monto_pagado for doc in documentos)
    total_devolucion = sum(doc.monto_devolucion for doc in documentos)
    total_pendiente = total_facturado - total_pagado - total_devolucion

    # Documentos vencidos (con saldo pendiente)
    vencidos = documentos.filter(
        fecha_vencimiento__lt=timezone.now(),
        monto_total__gt=F('monto_pagado') + F('monto_devolucion')
    )
    total_vencido = sum(doc.get_saldo_pendiente() for doc in vencidos)

    # === 2. Top 10 Clientes con Mayor Saldo Pendiente ===
    clientes_pendientes = []
    for cliente in Cliente.objects.all():
        docs = documentos.filter(cliente=cliente)
        saldo = sum(doc.get_saldo_pendiente() for doc in docs)
        if saldo > 0:
            clientes_pendientes.append({
                'cliente': cliente,
                'saldo': saldo,
                'vencido': sum(
                    doc.get_saldo_pendiente()
                    for doc in docs
                    if doc.fecha_vencimiento < timezone.now()
                )
            })
    # Ordenar por saldo descendente
    clientes_pendientes = sorted(clientes_pendientes, key=lambda x: x['saldo'], reverse=True)[:10]

    # === 3. Resumen por Cobrador ===
    cobradores_data = []
    for cobrador in Cobrador.objects.all():
        cobros = Cobro.objects.filter(cobrador=cobrador)
        total = cobros.aggregate(total=Sum('monto'))['total'] or 0
        if total > 0:
            cobradores_data.append({
                'cobrador': cobrador,
                'total_cobrado': total,
            })
    cobradores_data = sorted(cobradores_data, key=lambda x: x['total_cobrado'], reverse=True)

    # === 4. Evolución Mensual (últimos 6 meses) ===
    evolucion = []
    for i in range(6):
        mes = today - timedelta(days=30 * i)
        primer_dia = mes.replace(day=1)
        _, last_day = monthrange(mes.year, mes.month)
        ultimo_dia = mes.replace(day=last_day)

        # # ✅ Corregido: usar datetime.datetime.combine
        # fecha_desde_dt = timezone.make_aware(
        #     datetime.datetime.combine(primer_dia, datetime.datetime.min.time())
        # )
        # fecha_hasta_dt = timezone.make_aware(
        #     datetime.datetime.combine(ultimo_dia, datetime.datetime.max.time())
        # )
        # ✅ Corrección: usa datetime.combine y time.min/max
        fecha_desde_dt = timezone.make_aware(
            datetime.combine(primer_dia, time.min)
        )
        fecha_hasta_dt = timezone.make_aware(
            datetime.combine(ultimo_dia, time.max)
        )



        cobros_mes = Cobro.objects.filter(
            fecha__gte=fecha_desde_dt,
            fecha__lte=fecha_hasta_dt
        ).aggregate(total=Sum('monto'))['total'] or 0

        # ✅ Convertir a float para que sea compatible con JSON
        evolucion.append({
            'mes': primer_dia.strftime('%b %Y'),  # Ej: "Aug 2025"
            'cobrado': float(cobros_mes)  # ✅ Forzar a float
        })
    evolucion.reverse()
    print("📊 Evolución de cobros:", evolucion)  # 👈 Depuración

    context = {
        'total_facturado': total_facturado,
        'total_pagado': total_pagado,
        'total_devolucion': total_devolucion,
        'total_pendiente': total_pendiente,
        'total_vencido': total_vencido,
        'clientes_pendientes': clientes_pendientes,
        'cobradores_data': cobradores_data,
        'evolucion': evolucion,
        'fecha_reporte': today,
        'meta': meta,  # ✅ Añadido
    }

    return render(request, 'cobros/reporte_cartera.html', context)









def exportar_cartera_excel(request):
    """Exportar reporte de cartera a Excel"""
    # Reutiliza la lógica de resumen
    documentos = Documento.objects.all()
    total_facturado = documentos.aggregate(total=Sum('monto_total'))['total'] or 0
    total_pagado = sum(doc.monto_pagado for doc in documentos)
    total_devolucion = sum(doc.monto_devolucion for doc in documentos)
    total_pendiente = total_facturado - total_pagado - total_devolucion

    vencidos = documentos.filter(
        fecha_vencimiento__lt=timezone.now(),
        monto_total__gt=F('monto_pagado') + F('monto_devolucion')
    )
    total_vencido = sum(doc.get_saldo_pendiente() for doc in vencidos)

    # Crear libro
    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte Cartera"

    # Encabezado
    ws.append(["REPORTE DE CARTERA DE COBRANZAS", "", "", "", "", ""])
    ws.append(["Fecha del Reporte:", timezone.now().date().strftime('%d/%m/%Y'), "", "", "", ""])
    ws.append([])
    ws.append(["RESUMEN GENERAL", "", "", "", "", ""])
    ws.append(["Total Facturado", total_facturado])
    ws.append(["Total Cobrado", total_pagado])
    ws.append(["Devoluciones", total_devolucion])
    ws.append(["Saldo Pendiente", total_pendiente])
    ws.append(["Vencido", total_vencido])
    ws.append([])

    # Top clientes
    ws.append(["TOP 10 CLIENTES CON SALDO PENDIENTE", "", ""])
    ws.append(["Cliente", "Saldo", "Vencido"])
    for item in sorted(
        [{'cliente': c, 'saldo': sum(doc.get_saldo_pendiente() for doc in Documento.objects.filter(cliente=c)), 'vencido': sum(doc.get_saldo_pendiente() for doc in Documento.objects.filter(cliente=c, fecha_vencimiento__lt=timezone.now()))} for c in Cliente.objects.all() if sum(doc.get_saldo_pendiente() for doc in Documento.objects.filter(cliente=c)) > 0],
        key=lambda x: x['saldo'], reverse=True
    )[:10]:
        ws.append([item['cliente'].nombre, item['saldo'], item['vencido']])

    # Ajustar ancho
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 15

    # Respuesta
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=reporte_cartera.xlsx'
    wb.save(response)
    return response








from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Cobro, PlanillaCierre, Cobrador, DepositoParcial

from django.contrib.admin.views.decorators import staff_member_required

# @login_required
# def cerrar_planilla_del_dia(request):
#     # ✅ Obtener fecha actual en hora local (Perú)
#     hoy = timezone.localtime(timezone.now()).date()

#     # ✅ Si es superusuario
#     if request.user.is_superuser or request.user.is_staff:
#         cobradores = Cobrador.objects.all()

#         if request.method == 'POST':
#             cobrador_id = request.POST.get('cobrador')
#             if not cobrador_id:
#                 messages.error(request, "Debes seleccionar un cobrador.")
#                 return redirect('cobros:cerrar_planilla_del_dia')

#             try:
#                 cobrador = Cobrador.objects.get(pk=cobrador_id)
#             except Cobrador.DoesNotExist:
#                 messages.error(request, "Cobrador no válido.")
#                 return redirect('cobros:cerrar_planilla_del_dia')

#             # ✅ Calcular total cobrado del día (en hora local)
#             inicio_hoy = timezone.make_aware(
#                 datetime.datetime.combine(hoy, datetime.time.min)
#             )
#             fin_hoy = timezone.make_aware(
#                 datetime.datetime.combine(hoy, datetime.time.max)
#             )

#             total_cobrado = Cobro.objects.filter(
#                 cobrador=cobrador,
#                 fecha__gte=inicio_hoy,
#                 fecha__lte=fin_hoy
#             ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

#             # Crear o obtener planilla
#             planilla, created = PlanillaCierre.objects.get_or_create(
#                 cobrador=cobrador,
#                 fecha=hoy,
#                 defaults={
#                     'total_cobrado': total_cobrado,
#                     'notas': f'Cierre supervisado por admin - {request.user.username}'
#                 }
#             )

#             # Si ya existe, actualizar el total
#             if not created:
#                 planilla.total_cobrado = total_cobrado
#                 planilla.save()

#             messages.success(request, f'Cierre generado para {cobrador.nombre}. Total: S/ {total_cobrado:.2f}')
#             return redirect('cobros:planilla_detalle', pk=planilla.pk)

#         return render(request, 'cobros/admin_seleccionar_cobrador.html', {
#             'cobradores': cobradores
#         })

#     # ✅ Para cobradores normales
#     try:
#         cobrador = request.user.cobrador
#     except:
#         messages.error(request, "No estás asignado como cobrador.")
#         return redirect('home')

#     # ✅ Calcular total cobrado (en hora local)
#     inicio_hoy = timezone.make_aware(
#         datetime.datetime.combine(hoy, datetime.time.min)
#     )
#     fin_hoy = timezone.make_aware(
#         datetime.datetime.combine(hoy, datetime.time.max)
#     )

#     total_cobrado = Cobro.objects.filter(
#         cobrador=cobrador,
#         fecha__gte=inicio_hoy,
#         fecha__lte=fin_hoy
#     ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

#     # Crear o obtener planilla
#     planilla, created = PlanillaCierre.objects.get_or_create(
#         cobrador=cobrador,
#         fecha=hoy,
#         defaults={
#             'total_cobrado': total_cobrado,
#             'notas': f'Cierre automático del día {hoy}'
#         }
#     )

#     if not created:
#         planilla.total_cobrado = total_cobrado
#         planilla.save()

#     messages.info(request, f'Total cobrado: S/ {total_cobrado:.2f}')
#     return redirect('cobros:planilla_detalle', pk=planilla.pk)


@login_required
def cerrar_planilla_del_dia(request):
    # ✅ Obtener fecha actual en hora local (Perú)
    hoy = timezone.localtime(timezone.now()).date()

    # ✅ Definir grupos y usuarios permitidos
    grupos_permitidos = ['Puede Cerrar Planillas']  # Cambia al nombre real del grupo
    usuarios_permitidos = ['maria_cobrador', 'juanc', 'adminaqp']  # Ajusta según tus usuarios

    tiene_grupo = request.user.groups.filter(name__in=grupos_permitidos).exists()
    es_usuario_especial = request.user.username in usuarios_permitidos

    # ✅ Verificar si puede acceder como admin (cerrar para otros)
    if request.user.is_superuser or request.user.is_staff or tiene_grupo or es_usuario_especial:
        cobradores = Cobrador.objects.all()

        if request.method == 'POST':
            cobrador_id = request.POST.get('cobrador')
            if not cobrador_id:
                messages.error(request, "Debes seleccionar un cobrador.")
                return redirect('cobros:cerrar_planilla_del_dia')

            try:
                cobrador = Cobrador.objects.get(pk=cobrador_id)
            except Cobrador.DoesNotExist:
                messages.error(request, "Cobrador no válido.")
                return redirect('cobros:cerrar_planilla_del_dia')

            # ✅ Calcular total cobrado del día (en hora local)
            # ✅ Calcular total cobrado del día (en hora local)
            inicio_hoy = timezone.make_aware(
                datetime.combine(hoy, time.min)  # ✅ Mismo formato
            )
            fin_hoy = timezone.make_aware(
                datetime.combine(hoy, time.max)  # ✅ Consistente
            )

            total_cobrado = Cobro.objects.filter(
                cobrador=cobrador,
                fecha__gte=inicio_hoy,
                fecha__lte=fin_hoy
            ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

            # Crear o obtener planilla
            planilla, created = PlanillaCierre.objects.get_or_create(
                cobrador=cobrador,
                fecha=hoy,
                defaults={
                    'total_cobrado': total_cobrado,
                    'notas': f'Cierre supervisado por {request.user.username}'
                }
            )

            # Si ya existe, actualizar el total
            if not created:
                planilla.total_cobrado = total_cobrado
                planilla.save()

            messages.success(request, f'Cierre generado para {cobrador.nombre}. Total: S/ {total_cobrado:.2f}')

            # ✅ Registrar en el log
            registrar_log(
                usuario=request.user,
                cobrador=cobrador,
                categoria='planilla',
                accion='Cerró planilla de otro',
                descripcion=f"Cerró cierre del día para {cobrador.nombre}. Total: S/ {total_cobrado:.2f}"
            )

            return redirect('cobros:planilla_detalle', pk=planilla.pk)

        return render(request, 'cobros/admin_seleccionar_cobrador.html', {
            'cobradores': cobradores
        })

    # ✅ Para cobradores normales (cierran su propia planilla)
    try:
        cobrador = request.user.cobrador
    except:
        messages.error(request, "No estás asignado como cobrador.")
        return redirect('home')

    # ✅ Calcular total cobrado (en hora local)
    inicio_hoy = timezone.make_aware(
        datetime.datetime.combine(hoy, datetime.time.min)
    )
    fin_hoy = timezone.make_aware(
        datetime.datetime.combine(hoy, datetime.time.max)
    )

    total_cobrado = Cobro.objects.filter(
        cobrador=cobrador,
        fecha__gte=inicio_hoy,
        fecha__lte=fin_hoy
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

    # Crear o obtener planilla
    planilla, created = PlanillaCierre.objects.get_or_create(
        cobrador=cobrador,
        fecha=hoy,
        defaults={
            'total_cobrado': total_cobrado,
            'notas': f'Cierre automático del día {hoy} por {request.user.username}'
        }
    )

    if not created:
        planilla.total_cobrado = total_cobrado
        planilla.save()

    messages.info(request, f'Total cobrado: S/ {total_cobrado:.2f}')

    # ✅ Registrar en el log
    registrar_log(
        usuario=request.user,
        cobrador=cobrador,
        categoria='planilla',
        accion='Cerró su planilla',
        descripcion=f"Total: S/ {total_cobrado:.2f}"
    )

    return redirect('cobros:planilla_detalle', pk=planilla.pk)





@login_required
def planilla_detalle(request, pk):
    # ✅ Obtener planilla o 404
    planilla = get_object_or_404(PlanillaCierre, pk=pk)

    # ✅ Verificar permisos
    grupos_permitidos = ['Puede Ver Reporte de Cierres']
    usuarios_permitidos = ['maria_cobrador', 'juanc', 'adminaqp', 'VALERIA']

    tiene_grupo = request.user.groups.filter(name__in=grupos_permitidos).exists()
    es_usuario_especial = request.user.username in usuarios_permitidos

    if not (request.user.is_superuser or request.user.is_staff or
            (hasattr(request.user, 'cobrador') and request.user.cobrador == planilla.cobrador) or
            tiene_grupo or es_usuario_especial):
        messages.error(request, "No tienes permiso para ver esta planilla.")
        return redirect('cobros:cobro_list')

    # ✅ Obtener depósitos
    depositos = DepositoParcial.objects.filter(planilla=planilla).order_by('-fecha')

    # ✅ Calcular rango de fecha para el día de la planilla (en hora local)
    inicio_dia = timezone.make_aware(
        datetime.combine(planilla.fecha, time.min)  # ✅ Correcto
    )
    fin_dia = timezone.make_aware(
        datetime.combine(planilla.fecha, time.max)  # ✅ Correcto
    )

    # ✅ Obtener todos los cobros del cobrador en esa fecha
    cobros_del_dia = Cobro.objects.filter(
        cobrador=planilla.cobrador,
        fecha__gte=inicio_dia,
        fecha__lte=fin_dia
    ).select_related('documento', 'documento__cliente').order_by('-fecha')



    # ✅ Calcular total aquí, no en el template
    total_cobros = cobros_del_dia.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')


    # ✅ Si es POST, procesar depósito
    if request.method == 'POST':
        monto_str = request.POST.get('monto_deposito')
        notas = request.POST.get('notas', '')

        try:
            monto = Decimal(monto_str)
            if monto <= 0:
                messages.error(request, "El monto debe ser mayor a 0.")
            elif planilla.total_depositado + monto > planilla.total_cobrado:
                messages.error(
                    request,
                    f"El depósito excedería el total cobrado. "
                    f"Solo puedes depositar hasta S/ {(planilla.total_cobrado - planilla.total_depositado):.2f} más."
                )
            else:
                # ✅ Registrar depósito
                DepositoParcial.objects.create(
                    planilla=planilla,
                    monto=monto,
                    creado_por=request.user,
                    notas=notas
                )
                planilla.total_depositado += monto
                planilla.notas = notas
                planilla.actualizar_estado()
                messages.success(request, f"Depósito de S/ {monto:.2f} registrado.")

                # ✅ Registrar en el log de actividad
                registrar_log(
                    usuario=request.user,
                    cobrador=planilla.cobrador,
                    categoria='deposito',
                    accion='Registró depósito',
                    descripcion=f"Monto: S/ {monto:.2f}, Planilla: {planilla.fecha}, Cobrador: {planilla.cobrador.nombre}, Notas: {notas or '-'}"
                )

                return redirect('cobros:planilla_detalle', pk=planilla.pk)
        except Exception as e:
            messages.error(request, "Monto inválido.")
            return redirect('cobros:planilla_detalle', pk=planilla.pk)

    # ✅ Renderizar siempre una respuesta
    return render(request, 'cobros/planilla_detalle.html', {
        'planilla': planilla,
        'depositos': depositos,
        'cobros_del_dia': cobros_del_dia,  # ✅ Añadido: documentos cobrados
        'total_cobros': total_cobros,  # ✅ Enviado al template
    })







from datetime import datetime
import pytz

@login_required
def cerrar_planilla_fecha_especifica(request):
    # ✅ Verificar permisos (ajusta según tus necesidades)
    grupos_permitidos = ['Puede Cerrar Planillas']
    usuarios_permitidos = ['juanc', 'adminaqp', 'CHRISTIAN']

    tiene_grupo = request.user.groups.filter(name__in=grupos_permitidos).exists()
    es_usuario_especial = request.user.username in usuarios_permitidos

    if not (request.user.is_staff or request.user.is_superuser or tiene_grupo or es_usuario_especial):
        messages.error(request, "No tienes permiso para realizar esta acción.")
        return redirect('home')

    cobradores = Cobrador.objects.all().order_by('nombre')
    fecha_seleccionada = None
    cobrador_seleccionado = None
    total_cobrado = 0
    hay_cobros = False

    if request.method == 'POST':
        cobrador_id = request.POST.get('cobrador')
        fecha_str = request.POST.get('fecha')

        try:
            cobrador = get_object_or_404(Cobrador, pk=cobrador_id)
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()

            # ✅ Convertir a zona horaria local
            lima_tz = pytz.timezone('America/Lima')
            # inicio_dia = lima_tz.localize(datetime.combine(fecha, datetime.min.time()))
            # fin_dia = lima_tz.localize(datetime.combine(fecha, datetime.max.time()))
            inicio_dia = lima_tz.localize(datetime.combine(fecha, time.min))
            fin_dia = lima_tz.localize(datetime.combine(fecha, time.max))

            # ✅ Calcular total cobrado en esa fecha
            total_cobrado_decimal = Cobro.objects.filter(
                cobrador=cobrador,
                fecha__gte=inicio_dia,
                fecha__lte=fin_dia
            ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

            total_cobrado = float(total_cobrado_decimal)
            hay_cobros = Cobro.objects.filter(cobrador=cobrador, fecha__gte=inicio_dia, fecha__lte=fin_dia).exists()

            # ✅ Crear o obtener planilla
            planilla, created = PlanillaCierre.objects.get_or_create(
                cobrador=cobrador,
                fecha=fecha,
                defaults={
                    'total_cobrado': total_cobrado_decimal,
                    'notas': f'Cierre manual - {request.user.username}'
                }
            )

            if not created:
                planilla.total_cobrado = total_cobrado_decimal
                planilla.save()

            messages.success(request, f'Cierre generado para {cobrador.nombre} - {fecha.strftime("%d/%m/%Y")}. Total: S/ {total_cobrado:.2f}')
            return redirect('cobros:planilla_detalle', pk=planilla.pk)

        except Exception as e:
            messages.error(request, "Error al procesar el cierre. Verifica los datos ingresados.")

    # Para mostrar valores en el formulario
    fecha_seleccionada = request.POST.get('fecha', '')
    cobrador_seleccionado = request.POST.get('cobrador', '')

    return render(request, 'cobros/cerrar_planilla_fecha.html', {
        'cobradores': cobradores,
        'fecha_seleccionada': fecha_seleccionada,
        'cobrador_seleccionado': cobrador_seleccionado,
        'total_cobrado': total_cobrado,
        'hay_cobros': hay_cobros,
    })





from django.http import JsonResponse
from django.views.decorators.http import require_GET

@require_GET
@login_required
def calcular_total_cobrado(request):
    # ✅ Verificar permisos (igual que antes)
    grupos_permitidos = ['Puede Cerrar Planillas']
    usuarios_permitidos = ['juanc', 'adminaqp', 'maria']

    tiene_grupo = request.user.groups.filter(name__in=grupos_permitidos).exists()
    es_usuario_especial = request.user.username in usuarios_permitidos

    if not (request.user.is_staff or request.user.is_superuser or tiene_grupo or es_usuario_especial):
        return JsonResponse({'error': 'No tienes permiso'}, status=403)

    cobrador_id = request.GET.get('cobrador_id')
    fecha_str = request.GET.get('fecha')

    if not cobrador_id or not fecha_str:
        return JsonResponse({'total': 0, 'hay_cobros': False})

    try:
        cobrador = get_object_or_404(Cobrador, pk=cobrador_id)
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()

        lima_tz = pytz.timezone('America/Lima')
        inicio_dia = lima_tz.localize(datetime.combine(fecha, time.min))
        fin_dia = lima_tz.localize(datetime.combine(fecha, time.max))

        total = Cobro.objects.filter(
            cobrador=cobrador,
            fecha__gte=inicio_dia,
            fecha__lte=fin_dia
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

        hay_cobros = Cobro.objects.filter(cobrador=cobrador, fecha__gte=inicio_dia, fecha__lte=fin_dia).exists()

        return JsonResponse({
            'total': float(total),
            'hay_cobros': hay_cobros
        })
    except Exception as e:
        return JsonResponse({'total': 0, 'hay_cobros': False})





































@login_required
def historial_planillas(request):
    try:
        cobrador = request.user.cobrador
        planillas = PlanillaCierre.objects.filter(
            cobrador=cobrador,
            estado__in=['pendiente', 'parcial']
        ).order_by('-fecha')
    except:
        planillas = PlanillaCierre.objects.none()

    return render(request, 'cobros/historial_planillas.html', {
        'planillas': planillas
    })



@login_required
def mis_cierres(request):
    try:
        cobrador = request.user.cobrador
        planillas = PlanillaCierre.objects.filter(cobrador=cobrador).order_by('-fecha')
    except:
        planillas = PlanillaCierre.objects.none()

    # ✅ Paginación
    paginator = Paginator(planillas, 20)  # 20 por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ✅ Calcular conteos
    total = planillas.count()
    parciales = planillas.filter(estado='parcial').count()
    pendientes = planillas.filter(estado='pendiente').count()
    completados = planillas.filter(estado='completado').count()

    return render(request, 'cobros/mis_cierres.html', {
        'page_obj': page_obj,
        'planillas': page_obj,  # Para compatibilidad con el template
        'total': total,
        'parciales': parciales,
        'pendientes': pendientes,
        'completados': completados,
    })




@login_required
def mis_cierres_pdf(request):
    try:
        cobrador = request.user.cobrador
        planillas = PlanillaCierre.objects.filter(cobrador=cobrador).order_by('-fecha')
    except:
        planillas = PlanillaCierre.objects.none()

    # Calcular totales
    total_cobrado = planillas.aggregate(total=Sum('total_cobrado'))['total'] or Decimal('0.00')
    total_depositado = planillas.aggregate(total=Sum('total_depositado'))['total'] or Decimal('0.00')
    saldo_pendiente = total_cobrado - total_depositado

    # Renderizar HTML
    html_string = render_to_string('cobros/mis_cierres_pdf.html', {
        'planillas': planillas,
        'cobrador': cobrador,
        'total_cobrado': total_cobrado,
        'total_depositado': total_depositado,
        'saldo_pendiente': saldo_pendiente,
        'request': request,
    })

    # Generar PDF
    html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
    pdf = html.write_pdf()

    # Respuesta HTTP
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="mis_cierres_{cobrador.nombre}_{timezone.now().date()}.pdf"'
    return response



@login_required  # Solo usuarios autenticados
def admin_reporte_planillas(request):
    # ✅ Verificar permisos personalizados
    grupos_permitidos = ['Puede Ver Reporte de Cierres']  # Cambia al nombre real del grupo
    usuarios_permitidos = ['maria_cobrador', 'juanc', 'adminaqp', 'VA7LERIA']  # Usuarios específicos

    tiene_grupo = request.user.groups.filter(name__in=grupos_permitidos).exists()
    es_usuario_especial = request.user.username in usuarios_permitidos

    if not (request.user.is_staff or request.user.is_superuser or tiene_grupo or es_usuario_especial):
        messages.error(request, "No tienes permiso para ver este reporte.")
        return redirect('cobros:cobro_list')  # O a donde quieras redirigir

    # Si tiene permiso, continuar con la lógica normal
    planillas = PlanillaCierre.objects.all().select_related('cobrador').order_by('-fecha')

    # Filtros
    cobrador_id = request.GET.get('cobrador')
    fecha = request.GET.get('fecha')
    estado = request.GET.get('estado')

    if cobrador_id:
        try:
            planillas = planillas.filter(cobrador_id=int(cobrador_id))
        except ValueError:
            pass

    if fecha:
        try:
            planillas = planillas.filter(fecha=fecha)
        except ValueError:
            pass

    if estado and estado in ['pendiente', 'parcial', 'completado']:
        planillas = planillas.filter(estado=estado)

    cobradores = Cobrador.objects.all().order_by('nombre')

    # ✅ Paginación
    paginator = Paginator(planillas, 20)  # 20 por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'cobros/admin_reporte_planillas.html', {
        'page_obj': page_obj,
        'planillas': page_obj,
        'cobradores': cobradores,
        'filtros': request.GET,
    })



@staff_member_required
def reabrir_planilla(request, pk):
    planilla = get_object_or_404(PlanillaCierre, pk=pk)

    if planilla.estado != 'pendiente':
        # Eliminar depósitos parciales
        planilla.depositoparcial_set.all().delete()

        # ✅ Recalcular total_cobrado con los cobros actuales del día
        inicio_dia = timezone.make_aware(datetime.combine(planilla.fecha, time.min))
        fin_dia = timezone.make_aware(datetime.combine(planilla.fecha, time.max))

        nuevo_total = Cobro.objects.filter(
            cobrador=planilla.cobrador,
            fecha__gte=inicio_dia,
            fecha__lte=fin_dia
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

        # Reiniciar valores
        planilla.total_cobrado = nuevo_total
        planilla.total_depositado = Decimal('0.00')
        planilla.estado = 'pendiente'
        planilla.save()

        # ✅ Registrar en el log
        registrar_log(
            usuario=request.user,
            categoria='planilla',
            accion='Reabrió cierre',
            descripcion=f"Planilla ID: {pk}, Fecha: {planilla.fecha}, Cobrador: {planilla.cobrador.nombre}, Total cobrado actualizado a S/ {nuevo_total:.2f}"
        )

        messages.success(request, f"Cierre del {planilla.fecha} reabierto y total recalculado. El cobrador puede corregirlo.")
    else:
        messages.info(request, "El cierre ya está pendiente.")

    return redirect('cobros:admin_reporte_planillas')










@login_required
@require_POST
def eliminar_planilla(request, pk):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "No tienes permiso.")
        return redirect('cobros:admin_reporte_planillas')

    planilla = get_object_or_404(PlanillaCierre, pk=pk)
    nombre = planilla.cobrador.nombre
    fecha = planilla.fecha

    planilla.delete()

    messages.success(request, f"Planilla de {nombre} ({fecha}) eliminada correctamente.")
    return redirect('cobros:admin_reporte_planillas')

















def planilla_detalle_pdf(request, pk):
    planilla = get_object_or_404(PlanillaCierre, pk=pk)

    # Verificar permisos
    # ✅ Permitir a superusuario, staff o el cobrador asignado
    if not (request.user.is_superuser or
            request.user.is_staff or
            (hasattr(request.user, 'cobrador') and request.user.cobrador == planilla.cobrador)):
        messages.error(request, "No tienes permiso para ver este cierre.")
        return redirect('cobros:cobro_list')

    depositos = DepositoParcial.objects.filter(planilla=planilla).order_by('fecha')

    # Renderizar a HTML
    html_string = render_to_string('cobros/planilla_detalle_pdf.html', {
        'planilla': planilla,
        'depositos': depositos,
        'request': request  # Necesario para estáticos
    })

    # Generar PDF
    html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
    pdf = html.write_pdf()

    # Preparar respuesta
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="cierre_{planilla.cobrador.nombre}_{planilla.fecha}.pdf"'
    return response





def admin_reporte_planillas_pdf(request):
    # ✅ Verificar permisos personalizados (igual que en admin_reporte_planillas)
    grupos_permitidos = ['Puede Ver Reporte de Cierres']
    usuarios_permitidos = ['maria_cobrador', 'juanc', 'adminaqp', 'VALERIA', 'CHRISTIAN']  # Ajusta según tus usuarios

    tiene_grupo = request.user.groups.filter(name__in=grupos_permitidos).exists()
    es_usuario_especial = request.user.username in usuarios_permitidos

    if not (request.user.is_superuser or tiene_grupo or es_usuario_especial):
        messages.error(request, "No tienes permiso para exportar este reporte.")
        return redirect('cobros:cobro_list')

    # === 1. Obtener filtros ===
    cobrador_id = request.GET.get('cobrador')
    fecha = request.GET.get('fecha')
    estado = request.GET.get('estado')

    # === 2. Obtener planillas con filtros ===
    planillas = PlanillaCierre.objects.all().select_related('cobrador').order_by('-fecha')

    if cobrador_id:
        try:
            planillas = planillas.filter(cobrador_id=int(cobrador_id))
        except (ValueError, TypeError):
            pass

    if fecha:
        try:
            planillas = planillas.filter(fecha=fecha)
        except ValueError:
            pass

    if estado and estado in ['pendiente', 'parcial', 'completado']:
        planillas = planillas.filter(estado=estado)

    cobradores = Cobrador.objects.all().order_by('nombre')
    cobrador_filtro = cobradores.filter(id=cobrador_id).first() if cobrador_id else None

    # === 3. Renderizar a HTML ===
    html_string = render_to_string('cobros/admin_reporte_planillas_pdf.html', {
        'planillas': planillas,
        'cobrador_filtro': cobrador_filtro,
        'fecha_filtro': fecha,
        'estado_filtro': estado,
        'estado_display': dict(PlanillaCierre.estado.field.choices).get(estado),
        'total_cobrado': planillas.aggregate(total=Sum('total_cobrado'))['total'] or Decimal('0.00'),
        'total_depositado': planillas.aggregate(total=Sum('total_depositado'))['total'] or Decimal('0.00'),
        'total_pendiente': sum(p.saldo_pendiente for p in planillas),
        'request': request
    })

    # === 4. Generar PDF ===
    html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
    pdf = html.write_pdf()

    # === 5. Preparar respuesta ===
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_planillas_cierre.pdf"'
    return response































