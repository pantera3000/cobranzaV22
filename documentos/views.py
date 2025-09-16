from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q, F, ExpressionWrapper, DecimalField
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from .models import Documento, Despacho, DetalleDespacho
from .forms import DocumentoForm
from clientes.models import Cliente
from cobradores.models import Cobrador
from cobros.models import Cobro
from devoluciones.models import Devolucion
from clientes.utils import registrar_log  # ✅ Importa la función
import csv
from openpyxl import Workbook
from openpyxl.styles import Font
import pandas as pd
from django.db import models, transaction
from django.utils import timezone
from datetime import date
import calendar
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.urls import reverse
from django.template.loader import render_to_string
from weasyprint import HTML








# documentos/views.py


from .models import Despacho

@login_required
def modo_repartidor(request):
    """Página simple y segura solo para repartidores"""
    
    # ✅ Obtener el último reporte abierto (del día actual o más reciente)
    try:
        ultimo_despacho = Despacho.objects.filter(
            repartidor=request.user,
            estado='abierto'
        ).latest('fecha')
    except Despacho.DoesNotExist:
        ultimo_despacho = None

    return render(request, 'documentos/repartidor.html', {
        'ultimo_despacho': ultimo_despacho
    })









# ✅ Lista de usuarios que tienen acceso completo a todos los reportes de reparto
USUARIOS_PERMITIDOS = ['juanc', 'adminaqp', 'VALERIA']  # 👈 Añade aquí los usernames que desees


USUARIOS_PERMITIDOS_CREAR = ['juanc', 'adminaqp', 'usuario0122']  # Lista específica



def descargar_plantilla_excel(request):
    """Descarga una plantilla Excel para importar documentos"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Plantilla Documentos"

    headers = [
        "Cliente (Nombre o DNI)", "Tipo", "Serie", "Número", 
        "Monto Total", "Fecha Emisión (YYYY-MM-DD)", "Fecha Vencimiento (YYYY-MM-DD)"
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    ws.append(["Juan Pérez", "factura", "F001", "0001", "500.00", "2025-09-01", "2025-09-30"])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="plantilla_documentos.xlsx"'
    wb.save(response)
    return response


def importar_documentos_excel(request):
    if request.method == 'POST' and request.FILES.get('archivo_excel'):
        archivo = request.FILES['archivo_excel']
        try:
            df = pd.read_excel(archivo)
            documentos_creados = 0
            errores = []

            for index, row in df.iterrows():
                try:
                    cliente_nombre_o_dni = str(row['Cliente (Nombre o DNI)']).strip()
                    tipo = row['Tipo'].strip().lower()
                    serie = str(row['Serie']).strip()
                    numero = str(row['Número']).strip()
                    monto_total = float(row['Monto Total'])
                    fecha_emision = row['Fecha Emisión (YYYY-MM-DD)']
                    fecha_vencimiento = row['Fecha Vencimiento (YYYY-MM-DD)']

                    cliente = Cliente.objects.filter(
                        Q(nombre__icontains=cliente_nombre_o_dni) | 
                        Q(dni_ruc=cliente_nombre_o_dni)
                    ).first()

                    if not cliente:
                        errores.append(f"Fila {index+2}: Cliente '{cliente_nombre_o_dni}' no encontrado.")
                        continue

                    Documento.objects.create(
                        cliente=cliente,
                        tipo=tipo,
                        serie=serie,
                        numero=numero,
                        monto_total=monto_total,
                        fecha_emision=fecha_emision,
                        fecha_vencimiento=fecha_vencimiento
                    )
                    documentos_creados += 1

                except Exception as e:
                    errores.append(f"Fila {index+2}: Error en datos - {str(e)}")

            if documentos_creados > 0:
                messages.success(request, f"✅ {documentos_creados} documentos importados correctamente.")
            if errores:
                for error in errores:
                    messages.warning(request, error)

        except Exception as e:
            messages.error(request, f"❌ Error al leer el archivo: {str(e)}")

    return redirect('documentos:documento_list')


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
        saldo_pendiente = ExpressionWrapper(
            F('monto_total') - F('monto_pagado') - F('monto_devolucion'),
            output_field=DecimalField()
        )

        documentos = Documento.objects.annotate(saldo=saldo_pendiente).filter(
            saldo__gt=0
        ).filter(
            Q(numero__icontains=query) |
            Q(serie__icontains=query) |
            Q(cliente__nombre__icontains=query) |
            Q(cliente__dni_ruc__icontains=query)
        ).select_related('cliente')[:10]

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

    if cliente_id and cliente_id != 'None':
        try:
            cliente_id = int(cliente_id)
        except (ValueError, TypeError):
            cliente_id = ''
    else:
        cliente_id = ''

    documentos = Documento.objects.all()

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

    if fecha_emision_desde:
        documentos = documentos.filter(fecha_emision__date__gte=fecha_emision_desde)
    if fecha_emision_hasta:
        documentos = documentos.filter(fecha_emision__date__lte=fecha_emision_hasta)

    documentos = documentos.order_by('-fecha_emision')

    total_monto = documentos.aggregate(total=models.Sum('monto_total'))['total'] or 0

    paginator = Paginator(documentos, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    clientes = Cliente.objects.all().order_by('nombre')
    hoy = timezone.localtime(timezone.now()).date()

    mes_inicio = hoy.replace(day=1)
    mes_fin = hoy.replace(day=calendar.monthrange(hoy.year, hoy.month)[1])

    if hoy.month == 1:
        mes_pasado_inicio = hoy.replace(year=hoy.year - 1, month=12, day=1)
        mes_pasado_fin = hoy.replace(year=hoy.year - 1, month=12, day=31)
    else:
        mes_pasado_inicio = hoy.replace(month=hoy.month - 1, day=1)
        mes_pasado_fin = hoy.replace(month=hoy.month - 1, day=calendar.monthrange(hoy.year, hoy.month - 1)[1])

    año_actual = hoy.year
    año_pasado = hoy.year - 1

    # ✅ Determinar si el usuario es repartidor
    es_repartidor = request.user.groups.filter(name='Repartidores').exists()
    # Opcional: incluir usuarios específicos como repartidores
    if not es_repartidor:
        es_repartidor = request.user.username in ['maria_cobrador', 'otro_usuario']



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
        'today': hoy,
        'mes_inicio': mes_inicio,
        'mes_fin': mes_fin,
        'mes_pasado_inicio': mes_pasado_inicio,
        'mes_pasado_fin': mes_pasado_fin,
        'año_actual': año_actual,
        'año_pasado': año_pasado,
        'es_repartidor': es_repartidor,  # ✅ Para usar en base.html
    })


def documento_create(request):
    if request.method == 'POST':
        form = DocumentoForm(request.POST)
        if form.is_valid():
            documento = form.save()
            registrar_log(
                usuario=request.user,
                cobrador=documento.cobrador,
                categoria='documento',
                accion='Creó documento',
                descripcion=f"Tipo: {documento.get_tipo_display()}, Número: {documento.get_numero_completo()}, Cliente: {documento.cliente.nombre}"
            )
            messages.success(request, f'Documento {documento.get_numero_completo()} creado exitosamente.')
            next_url = request.POST.get('next')
            return redirect(next_url) if next_url else redirect('documentos:documento_list')
        else:
            messages.error(request, 'Por favor corrige los errores.')
    else:
        cliente_id = request.GET.get('cliente')
        initial = {}
        if cliente_id:
            try:
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
    original = {
        'tipo': documento.get_tipo_display(),
        'serie': documento.serie,
        'numero': documento.numero,
        'cliente': documento.cliente.nombre,
        'monto_total': documento.monto_total,
        'fecha_emision': documento.fecha_emision,
        'fecha_vencimiento': documento.fecha_vencimiento,
    }

    if request.method == 'POST':
        form = DocumentoForm(request.POST, instance=documento)
        if form.is_valid():
            documento = form.save()
            cambios = []
            if original['tipo'] != documento.get_tipo_display():
                cambios.append(f"Tipo: {original['tipo']} → {documento.get_tipo_display()}")
            if original['serie'] != documento.serie:
                cambios.append(f"Serie: {original['serie'] or '-'} → {documento.serie or '-'}")
            if original['numero'] != documento.numero:
                cambios.append(f"Número: {original['numero']} → {documento.numero}")
            if original['cliente'] != documento.cliente.nombre:
                cambios.append(f"Cliente: {original['cliente']} → {documento.cliente.nombre}")
            if original['monto_total'] != documento.monto_total:
                cambios.append(f"Monto: S/ {original['monto_total']:,.2f} → S/ {documento.monto_total:,.2f}")
            if original['fecha_emision'].date() != documento.fecha_emision.date():
                cambios.append(f"Fecha emisión: {original['fecha_emision'].strftime('%d/%m/%Y')} → {documento.fecha_emision.strftime('%d/%m/%Y')}")
            if original['fecha_vencimiento'].date() != documento.fecha_vencimiento.date():
                cambios.append(f"Fecha vencimiento: {original['fecha_vencimiento'].strftime('%d/%m/%Y')} → {documento.fecha_vencimiento.strftime('%d/%m/%Y')}")

            if cambios:
                descripcion = f"Documento: {original['tipo']} {original['serie']}-{original['numero']} | " + " | ".join(cambios)
                registrar_log(
                    usuario=request.user,
                    cobrador=None,
                    categoria='documento',
                    accion='Editó documento',
                    descripcion=descripcion
                )
            messages.success(request, 'Documento actualizado exitosamente.')
            next_url = request.POST.get('next')
            return redirect(next_url) if next_url else redirect('documentos:documento_list')
    else:
        form = DocumentoForm(instance=documento)

    return render(request, 'documentos/documento_form.html', {
        'form': form,
        'title': 'Editar Documento'
    })


def documento_delete(request, pk):
    try:
        documento = get_object_or_404(Documento, pk=pk)
        if documento.monto_pagado > 0 or documento.monto_devolucion > 0:
            messages.error(request, 'No se puede eliminar un documento con pagos o devoluciones registrados.')
            return redirect('documentos:documento_detail', pk=pk)

        if request.method == 'POST':
            num = f"{documento.serie}-{documento.numero}" if documento.serie else str(documento.numero or "Sin número")
            cliente_nombre = documento.cliente.nombre if documento.cliente else "Cliente desconocido"
            referencia = documento.referencia or "Sin referencia"
            documento.delete()

            try:
                from clientes.models import LogActividad
                LogActividad.objects.create(
                    usuario=request.user if request.user.is_authenticated else None,
                    cobrador=None,
                    categoria='documento',
                    accion='Eliminó documento',
                    descripcion=f"Documento: {num}, Cliente: {cliente_nombre}, Referencia: {referencia}"
                )
            except:
                pass

            messages.success(request, f'Documento {num} eliminado exitosamente.')
            return redirect('documentos:documento_list')

        return render(request, 'documentos/documento_confirm_delete.html', {'documento': documento})

    except Exception as e:
        print(f"❌ Error en documento_delete: {e}")
        messages.error(request, 'Ocurrió un error inesperado.')
        return redirect('documentos:documento_list')


def documento_export_excel(request):
    query = request.GET.get('q', '')
    tipo = request.GET.get('tipo', '')
    estado = request.GET.get('estado', '')
    cliente_id = request.GET.get('cliente', '')
    fecha_emision_desde = request.GET.get('fecha_emision_desde', '')
    fecha_emision_hasta = request.GET.get('fecha_emision_hasta', '')

    documentos = Documento.objects.select_related('cliente', 'cobrador').all()

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
        try:
            documentos = documentos.filter(cliente_id=int(cliente_id))
        except:
            pass
    if estado:
        documentos = documentos.annotate(saldo_pendiente=F('monto_total') - F('monto_pagado') - F('monto_devolucion'))
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
            documentos = documentos.filter(monto_pagado__gt=0, saldo_pendiente__gt=0)
        elif estado == 'vencido':
            documentos = documentos.filter(saldo_pendiente__gt=0, fecha_vencimiento__lt=timezone.now())

    if fecha_emision_desde:
        documentos = documentos.filter(fecha_emision__date__gte=fecha_emision_desde)
    if fecha_emision_hasta:
        documentos = documentos.filter(fecha_emision__date__lte=fecha_emision_hasta)

    documentos = documentos.order_by('-fecha_emision')

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
        dias = doc.get_dias_restantes
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
    try:
        documento = Documento.objects.get(pk=pk)
    except Documento.DoesNotExist:
        messages.warning(request, 'El documento ya no existe.')
        return redirect('documentos:documento_list')
    
    cobros_list = Cobro.objects.filter(documento=documento).order_by('-fecha')
    devoluciones_list = Devolucion.objects.filter(documento=documento).order_by('-fecha')

    referencias = [cobro.referencia for cobro in cobros_list if cobro.referencia]
    referencia_count = {}
    if referencias:
        cobros_globales = Cobro.objects.filter(referencia__in=referencias)
        for cobro in cobros_globales:
            if cobro.referencia:
                if cobro.referencia not in referencia_count:
                    referencia_count[cobro.referencia] = 0
                referencia_count[cobro.referencia] += 1

    cobros_paginator = Paginator(cobros_list, 20)
    cobros_page_number = request.GET.get('cobros_page')
    cobros_page_obj = cobros_paginator.get_page(cobros_page_number)

    devoluciones_paginator = Paginator(devoluciones_list, 20)
    devoluciones_page_number = request.GET.get('devoluciones_page')
    devoluciones_page_obj = devoluciones_paginator.get_page(devoluciones_page_number)

    es_repartidor = request.user.groups.filter(name='Repartidores').exists()
    if not es_repartidor:
        es_repartidor = request.user.username in ['maria_cobrador', 'otro_usuario']

    return render(request, 'documentos/documento_detail.html', {
        'documento': documento,
        'cobros': cobros_page_obj,
        'devoluciones': devoluciones_page_obj,
        'referencia_count': referencia_count,
        'es_repartidor': es_repartidor,  # ✅ Para usar en base.html
    })


# === MÓDULO DE DESPACHO / REPARTO ===

def despacho_detalle(request, despacho_id):
    """
    Vista principal para el repartidor: ver lista y registrar cobros.
    Acceso: repartidor asignado, staff, superuser, encargado o usuario permitido.
    """
    despacho = get_object_or_404(Despacho, pk=despacho_id)

    if not (
        request.user == despacho.repartidor 
        or request.user.is_staff 
        or request.user.is_superuser 
        or request.user.groups.filter(name='Encargados Reparto').exists()
        or request.user.username in USUARIOS_PERMITIDOS
    ):
        messages.error(request, "No tienes permiso para ver este reporte.")
        return redirect('documentos:despacho_lista')

    detalles = despacho.detalles.select_related('documento', 'cliente').all()

    return render(request, 'documentos/despacho_detalle.html', {
        'despacho': despacho,
        'detalles': detalles,
    })


def despacho_lista(request):
    """
    Lista todos los reportes de despacho.
    Por defecto: muestra todos (sin filtro de fecha).
    Los repartidores ven solo los suyos.
    Staff, superuser, encargados y usuarios permitidos ven todos.
    """
    hoy = timezone.localtime(timezone.now()).date()
    despachos = Despacho.objects.select_related('repartidor', 'creado_por').all().order_by('-fecha')

    fecha = request.GET.get('fecha')
    repartidor_id = request.GET.get('repartidor')
    estado = request.GET.get('estado')

    if fecha:
        try:
            f = timezone.datetime.strptime(fecha, '%Y-%m-%d').date()
            despachos = despachos.filter(fecha=f)
        except ValueError:
            pass

    if repartidor_id:
        try:
            despachos = despachos.filter(repartidor__id=int(repartidor_id))
        except (ValueError, TypeError):
            pass

    if estado and estado in ['abierto', 'cerrado']:
        despachos = despachos.filter(estado=estado)

    # 🔐 Restringir acceso
    if not (
        request.user.is_staff 
        or request.user.is_superuser 
        or request.user.groups.filter(name='Encargados Reparto').exists()
        or request.user.groups.filter(name='Puede Crear Reportes').exists()
        or request.user.username in USUARIOS_PERMITIDOS
    ):
        despachos = despachos.filter(repartidor=request.user)

    # ✅ Anotar valores reales antes de paginar
    despachos = despachos.prefetch_related('detalles__documento')

    # Convertimos a lista para calcular valores dinámicos
    despachos_list = []

    for d in despachos:
        detalles = d.detalles.all()

        # Calcular total enviado
        total_enviado = sum(det.documento.monto_total for det in detalles)

        # Calcular saldo pendiente REAL de todos los documentos
        saldo_pendiente_real = sum(
            det.documento.get_saldo_pendiente() 
            for det in detalles
        )

        # Calcular total cobrado REAL
        total_cobrado_real = total_enviado - saldo_pendiente_real

        # ✅ Asignar atributos calculados (para usar en el template)
        d.total_enviado_calc = total_enviado
        d.total_cobrado_calc = total_cobrado_real
        d.saldo_pendiente_calc = saldo_pendiente_real

        despachos_list.append(d)

    # Paginación manual
    paginator = Paginator(despachos_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    repartidores = User.objects.filter(
        models.Q(groups__name='Repartidores') |
        models.Q(is_staff=True)
    ).distinct().order_by('username')

    # ✅ Calcular permisos para el template
    es_repartidor = request.user.groups.filter(name='Repartidores').exists()
    if not es_repartidor:
        es_repartidor = request.user.username in ['maria_cobrador']  # Usuarios especiales

    es_encargado = request.user.groups.filter(name='Encargados Reparto').exists()
    puede_crear_reporte = request.user.groups.filter(name='Puede Crear Reportes').exists()

    return render(request, 'documentos/despacho_lista.html', {
        'page_obj': page_obj,
        'repartidores': repartidores,
        'fecha': fecha or '',
        'estado': estado or '',
        'repartidor_id': repartidor_id or '',
        'usuarios_permitidos': USUARIOS_PERMITIDOS,
        'es_repartidor': es_repartidor,
        'es_encargado': es_encargado,
        'puede_crear_reporte': puede_crear_reporte,
    })

def despacho_crear(request):
    """
    Encargado crea un nuevo reporte de despacho.
    Busca y agrega documentos pendientes.
    Ahora con paginación y búsqueda.
    """
    query = request.GET.get('q', '')
    hoy = timezone.localtime(timezone.now()).date()

    # Filtrar documentos con saldo pendiente
    documentos = Documento.objects.filter(
        monto_total__gt=F('monto_pagado') + F('monto_devolucion')
    ).select_related('cliente').order_by('-fecha_emision')

    # Aplicar búsqueda
    if query:
        documentos = documentos.filter(
            Q(cliente__nombre__icontains=query) |
            Q(numero__icontains=query) |
            Q(serie__icontains=query)
        )

    # ✅ Paginación: 20 documentos por página
    paginator = Paginator(documentos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ✅ Permisos ampliados: staff, superuser, encargados pueden elegir repartidor
    if (
        request.user.is_staff 
        or request.user.is_superuser 
        or request.user.username in USUARIOS_PERMITIDOS_CREAR
        or request.user.groups.filter(name='Encargados Reparto').exists()
    ):
        repartidor_id = request.GET.get('repartidor_id')
        if not repartidor_id:
            posibles_nombres = ['Repartidttores', 'repartttidores', 'Cobradores', 'cobradores', 'Delivery']
            repartidores = User.objects.filter(groups__name__in=posibles_nombres).distinct()
            if not repartidores.exists():
                try:
                    from cobradores.models import Cobrador
                    cobradores_ids = Cobrador.objects.values_list('user_id', flat=True)
                    repartidores = User.objects.filter(id__in=cobradores_ids)
                except:
                    repartidores = User.objects.none()
            return render(request, 'documentos/despacho_seleccionar_repartidor.html', {
                'repartidores': repartidores
            })
        repartidor = get_object_or_404(User, pk=repartidor_id)
    else:
        repartidor = request.user

    try:
        despacho, created = Despacho.objects.get_or_create(
            fecha=hoy,
            repartidor=repartidor,
            defaults={
                'creado_por': request.user,
                'estado': 'abierto'
            }
        )
        if not created and despacho.estado == 'cerrado':
            messages.warning(request, f"Este reporte estaba cerrado. Lo reabrimos para edición.")
            despacho.estado = 'abierto'
            despacho.save()
    except Exception:
        try:
            despacho = Despacho.objects.get(fecha=hoy, repartidor=repartidor)
            if despacho.estado != 'abierto':
                messages.info(request, f"Reporte encontrado pero estaba {despacho.get_estado_display()}. Corrigiendo...")
                despacho.estado = 'abierto'
                despacho.save()
        except Despacho.DoesNotExist:
            messages.error(request, "No existe ni se pudo crear el reporte.")
            return redirect('documentos:despacho_lista')
        except Exception:
            messages.error(request, "Error crítico al acceder al despacho.")
            return redirect('documentos:despacho_lista')

    detalles = despacho.detalles.select_related('documento', 'cliente').all()

    return render(request, 'documentos/despacho_crear.html', {
        'documentos': page_obj,  # ✅ Ahora es una página, no todo el queryset
        'despacho': despacho,
        'detalles': detalles,
        'query': query,
        'repartidor': repartidor,
        'paginator': paginator,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,  # ✅ Necesario si usas {{ page_obj.number }}
    })

@transaction.atomic
def despacho_agregar_documento(request, despacho_id):
    try:
        despacho = Despacho.objects.select_related('repartidor').get(pk=despacho_id)
    except Despacho.DoesNotExist:
        messages.error(request, "El reporte de despacho no existe.")
        return redirect('documentos:despacho_lista')

    # ✅ Verificar permisos: repartidor, staff, superuser, encargado o permitido
    if not (
        request.user == despacho.repartidor 
        or request.user.is_staff 
        or request.user.is_superuser 
        or request.user.groups.filter(name='Encargados Reparto').exists()
        or request.user.username in USUARIOS_PERMITIDOS
    ):
        messages.error(request, "No tienes permiso para modificar este reporte.")
        return redirect('documentos:despacho_lista')

    if request.method == 'POST':
        doc_id = request.POST.get('documento_id')
        numero_pedido = request.POST.get('numero_pedido', '').strip()
        notas = request.POST.get('notas', '').strip()

        if not doc_id or not doc_id.isdigit():
            messages.error(request, "ID de documento inválido.")
            return redirect('documentos:despacho_crear', despacho_id=despacho.id)

        try:
            documento = Documento.objects.get(pk=doc_id)
        except Documento.DoesNotExist:
            messages.error(request, "Documento no encontrado.")
            return redirect('documentos:despacho_crear', despacho_id=despacho.id)

        if documento.get_saldo_pendiente() <= 0:
            messages.warning(request, f"{documento} ya está pagado.")
        elif DetalleDespacho.objects.filter(despacho=despacho, documento=documento).exists():
            messages.warning(request, f"{documento} ya está en el despacho.")
        else:
            DetalleDespacho.objects.create(
                despacho=despacho,
                documento=documento,
                cliente=documento.cliente,
                numero_pedido=numero_pedido,
                notas=notas
            )
            messages.success(request, f"✅ {documento} agregado al despacho.")

    url_base = reverse('documentos:despacho_crear')
    return redirect(f"{url_base}?repartidor_id={despacho.repartidor.id}")


@transaction.atomic
def despacho_registrar_cobro(request, despacho_id):
    despacho = get_object_or_404(Despacho, pk=despacho_id)

    # if not (
    #     request.user == despacho.repartidor 
    #     or request.user.is_staff 
    #     or request.user.is_superuser 
    #     or request.user.groups.filter(name='Encargados Reparto').exists()
    #     or request.user.groups.filter(name='Repartidor').exists()
    #     or request.user.username in USUARIOS_PERMITIDOS
    # ):
    #     messages.error(request, "No tienes permiso para registrar cobros aquí.")
    #     return redirect('documentos:despacho_lista')

    grupos_permitidos = ['Encargados Reparto', 'Repartidores']  # ✅ Grupos permitidos

    tiene_grupo = request.user.groups.filter(name__in=grupos_permitidos).exists()

    if not (
        request.user == despacho.repartidor
        or request.user.is_staff
        or request.user.is_superuser
        or tiene_grupo
        or request.user.username in USUARIOS_PERMITIDOS
    ):
        messages.error(request, "No tienes permiso para registrar cobros aquí.")
        return redirect('documentos:despacho_lista')




    if request.method == 'POST':
        total_cobrado = Decimal('0.00')
        
        for key, value in request.POST.items():
            if key.startswith('cobrado_'):
                detalle_id = key.replace('cobrado_', '')
                try:
                    detalle = DetalleDespacho.objects.select_related('documento').get(pk=detalle_id, despacho=despacho)
                    cobrado = Decimal(value or '0.00')

                    saldo_doc = detalle.documento.get_saldo_pendiente()
                    if cobrado > saldo_doc:
                        cobrado = saldo_doc
                        messages.warning(request, f"En {detalle.documento}: cobro ajustado a S/ {saldo_doc}")

                    detalle.cobrado = cobrado

                    medio_pago = request.POST.get(f'medio_{detalle_id}', '').strip()
                    if cobrado > 0:
                        if not medio_pago:
                            messages.warning(request, f"En {detalle.documento}: debes seleccionar un medio de pago.")
                            continue
                        detalle.medio_pago = medio_pago
                    else:
                        detalle.medio_pago = None

                    detalle.observaciones = request.POST.get(f'obs_{detalle_id}', '')
                    detalle.save()

                    if cobrado > 0:
                        detalle.documento.monto_pagado += cobrado
                        detalle.documento.save()

                        try:
                            cobrador_instance = despacho.repartidor.cobrador
                        except Cobrador.DoesNotExist:
                            messages.error(request, f"El usuario {despacho.repartidor.username} no tiene perfil de Cobrador.")
                            continue

                        from cobros.models import Cobro
                        from cobros.utils import generar_correlativo

                        Cobro.objects.create(
                            documento=detalle.documento,
                            cobrador=cobrador_instance,
                            monto=cobrado,
                            fecha=timezone.now(),
                            referencia=f"REPARTO-{despacho.fecha}",
                            notas=f"Cobro parcial en reparto. Medio: {detalle.get_medio_pago_display() or 'N/A'}. Obs: {detalle.observaciones or ''}",
                            tipo_pago=detalle.medio_pago or 'otro',
                            
                            correlativo=generar_correlativo(),
                            usuario_registro=request.user  # ✅ ¡Este es el cambio clave!
                            
                        )

                    total_cobrado += cobrado

                except Exception as e:
                    messages.error(request, f"Error en {detalle_id}: {str(e)}")


        # ✅ REGISTRAR EN EL LOG DE AUDITORÍA
        if total_cobrado > 0:
            try:
                from clientes.utils import registrar_log
                registrar_log(
                    usuario=request.user,
                    cobrador=cobrador_instance,
                    categoria='cobro',
                    accion='Registró cobro en reparto',
                    descripcion=f"Reparto ID: {despacho.id}, Fecha: {despacho.fecha}, Total cobrado: S/ {total_cobrado:.2f}, Registrado por: {request.user.get_full_name() or request.user.username}"
                )
            except Exception as log_error:
                print(f"❌ Error al registrar log de reparto: {log_error}")



        messages.success(request, f"✅ Cobros registrados correctamente. Total: S/ {total_cobrado:.2f}")
        return redirect('documentos:despacho_detalle', despacho_id=despacho.id)

    return redirect('documentos:despacho_detalle', despacho_id=despacho.id)


@login_required
def despacho_cerrar(request, despacho_id):
    despacho = get_object_or_404(Despacho, pk=despacho_id)
    
    # ✅ Verificar permisos
    if (
        request.user.is_staff 
        or request.user.is_superuser 
        or request.user == despacho.creado_por
        or request.user.groups.filter(name='Encargados Reparto').exists()
    ):
        despacho.estado = 'cerrado'
        despacho.save()

        # ✅ Registrar en el log
        try:
            from clientes.utils import registrar_log
            registrar_log(
                usuario=request.user,
                cobrador=None,
                categoria='reparto',
                accion='Cerró reporte de reparto',
                descripcion=f"Reporte ID: {despacho.id}, Fecha: {despacho.fecha}, Repartidor: {despacho.repartidor.get_full_name() or despacho.repartidor.username}"
            )
        except Exception as e:
            print(f"❌ Error al registrar log al cerrar reparto: {e}")

        messages.success(request, "✅ Despacho cerrado.")
    else:
        messages.error(request, "No tienes permiso para cerrar este reporte.")

    return redirect('documentos:despacho_detalle', despacho_id=despacho.id)

@login_required
def despacho_reabrir(request, despacho_id):
    despacho = get_object_or_404(Despacho, pk=despacho_id)
    
    # ✅ Corregido: 'Encargados Reparto' (no 'Repar5to')
    if (
        request.user.is_staff 
        or request.user.is_superuser 
        or request.user.groups.filter(name='Encargados Repar55to').exists()
    ):
        despacho.estado = 'abierto'
        despacho.save()

        # ✅ Registrar en el log
        try:
            from clientes.utils import registrar_log
            registrar_log(
                usuario=request.user,
                cobrador=None,
                categoria='reparto',
                accion='Reabrió reporte de reparto',
                descripcion=f"Reporte ID: {despacho.id}, Fecha: {despacho.fecha}, Repartidor: {despacho.repartidor.get_full_name() or despacho.repartidor.username}"
            )
        except Exception as e:
            print(f"❌ Error al registrar log al reabrir reparto: {e}")

        messages.success(request, "✅ Despacho reabierto.")
    else:
        messages.error(request, "No tienes permiso para reabrir este reporte.")
        
    return redirect('documentos:despacho_detalle', despacho_id=despacho.id)


# @login_required
# def despacho_eliminar(request, despacho_id):
#     despacho = get_object_or_404(Despacho, pk=despacho_id)
    
#     if request.user.is_staff or request.user.is_superuser:
#         # ✅ Verificar si ya hay cobros reales
#         from cobros.models import Cobro
#         documentos_ids = despacho.detalles.values_list('documento__id', flat=True)
#         tiene_cobros = Cobro.objects.filter(
#             documento__id__in=documentos_ids,
#             referencia__startswith=f"REPARTO-{despacho.fecha}"
#         ).exists()

#         if tiene_cobros:
#             messages.warning(request, "❌ No puedes eliminar este reporte porque ya se registraron pagos. Usa 'Reabrir' para corregir.")
#             return redirect('documentos:despacho_detalle', despacho_id=despacho.id)

#         repartidor_nombre = despacho.repartidor.get_full_name() or despacho.repartidor.username
#         despacho.delete()
#         messages.success(request, f"🗑️ Despacho de {repartidor_nombre} eliminado.")
        
#     return redirect('documentos:despacho_lista')



# si deseo que encargados tambien eliminin reprotes
# @login_required
# def despacho_eliminar(request, despacho_id):
#     despacho = get_object_or_404(Despacho, pk=despacho_id)
    
#     if (
#         request.user.is_staff 
#         or request.user.is_superuser 
#         or request.user.groups.filter(name='Encargados Reparto').exists()
#     ):
#         repartidor_nombre = despacho.repartidor.get_full_name() or despacho.repartidor.username
        
#         detalles = despacho.detalles.all()
#         from cobros.models import Cobro
#         documentos_ids = [d.documento.id for d in detalles]
#         Cobro.objects.filter(
#             documento__id__in=documentos_ids,
#             referencia=f"REPARTO-{despacho.fecha}"
#         ).delete()

#         despacho.delete()
#         messages.success(request, f"🗑️ Despacho de {repartidor_nombre} eliminado. Pagos asociados anulados.")
#     else:
#         messages.error(request, "No tienes permiso para eliminar este reporte.")
        
#     return redirect('documentos:despacho_lista')





@login_required
def despacho_eliminar(request, despacho_id):
    despacho = get_object_or_404(Despacho, pk=despacho_id)
    
    if request.user.is_staff or request.user.is_superuser:
        repartidor_nombre = despacho.repartidor.get_full_name() or despacho.repartidor.username
        
        # ✅ Obtener todos los detalles antes de eliminar
        detalles = despacho.detalles.all()
        
        # ✅ Obtener IDs de documentos para actualizar después
        from cobros.models import Cobro
        documentos_ids = [d.documento.id for d in detalles]
        
        # ✅ Eliminar primero los Cobros relacionados
        cobros_eliminados = Cobro.objects.filter(
            documento__id__in=documentos_ids,
            referencia=f"REPARTO-{despacho.fecha}"
        )
        count = cobros_eliminados.count()
        cobros_eliminados.delete()

        # ✅ Actualizar monto_pagado de cada documento afectado
        from .models import Documento
        documentos_afectados = Documento.objects.filter(id__in=documentos_ids)
        for doc in documentos_afectados:
            doc.actualizar_montos()  # ← Esto recalcula monto_pagado desde cero

        # ✅ Luego eliminar el despacho
        despacho.delete()
        
        messages.success(request, f"🗑️ Despacho de {repartidor_nombre} eliminado. {count} pago(s) asociado(s) anulado(s) y montos actualizados.")
    else:
        messages.error(request, "No tienes permiso para eliminar este reporte.")

    return redirect('documentos:despacho_lista')





@login_required
def despacho_pdf(request, despacho_id):
    despacho = get_object_or_404(Despacho, pk=despacho_id)

    if not (
        request.user == despacho.creado_por 
        or request.user.is_superuser 
        or request.user.groups.filter(name='Encargados Reparto').exists()
        or request.user.username in USUARIOS_PERMITIDOS
    ):
        return HttpResponse("No tienes permiso para ver este reporte.", status=403)

    detalles = despacho.detalles.select_related('documento', 'cliente').all()

    html_string = render_to_string('documentos/despacho_pdf.html', {
        'despacho': despacho,
        'detalles': detalles,
        'request': request
    })

    html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_reparto_{despacho.fecha}_{despacho.repartidor}.pdf"'
    return response


@login_required
def despacho_liquidacion_pdf(request, despacho_id):
    despacho = get_object_or_404(Despacho, pk=despacho_id)

    if not (
        request.user == despacho.repartidor 
        or request.user == despacho.creado_por 
        or request.user.is_superuser 
        or request.user.groups.filter(name='Encargados Reparto').exists()
        or request.user.username in USUARIOS_PERMITIDOS
    ):
        return HttpResponse("No tienes permiso para ver esta liquidación.", status=403)

    detalles = despacho.detalles.select_related('documento', 'cliente').all()

    html_string = render_to_string('documentos/despacho_liquidacion_pdf.html', {
        'despacho': despacho,
        'detalles': detalles,
        'request': request
    })

    html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="liquidacion_reparto_{despacho.fecha}_{despacho.repartidor}.pdf"'
    return response









# documentos/views.py
# documentos/views.py
from openpyxl import Workbook
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Despacho






@login_required
def despacho_export_excel(request):
    if not (request.user.is_staff or request.user.is_superuser or request.user.groups.filter(name='Encargados Reparto').exists()):
        messages.error(request, "No tienes permiso para exportar.")
        return redirect('documentos:despacho_lista')

    # Aplicar filtros
    fecha = request.GET.get('fecha')
    repartidor_id = request.GET.get('repartidor')
    estado = request.GET.get('estado')

    despachos = Despacho.objects.select_related('repartidor', 'creado_por').all()

    if fecha:
        despachos = despachos.filter(fecha=fecha)
    if repartidor_id:
        despachos = despachos.filter(repartidor__id=repartidor_id)
    if estado:
        despachos = despachos.filter(estado=estado)

    # Preparar datos
    data = []
    for d in despachos:
        # Obtener todos los documentos del reparto
        detalles = d.detalles.select_related('documento').all()
        
        total_enviado = Decimal('0.00')
        total_cobrado_real = Decimal('0.00')  # Sumar todos los cobros, no solo del reparto

        for det in detalles:
            doc = det.documento
            total_enviado += doc.monto_total

            # ✅ Usar el saldo real del documento (incluye pagos individuales, múltiples, etc.)
            total_cobrado_real += (doc.monto_total - doc.get_saldo_pendiente())

        saldo_pendiente_real = total_enviado - total_cobrado_real

        data.append({
            'Fecha': d.fecha,
            'Repartidor': d.repartidor.get_full_name() or d.repartidor.username,
            'Total Enviado': float(total_enviado),
            'Total Cobrado (real)': float(total_cobrado_real),
            'Pendiente (real)': float(saldo_pendiente_real),
            'Estado': d.get_estado_display(),
            'Creado por': d.creado_por.get_full_name() or d.creado_por.username,
        })

    # Crear Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Reportes de Reparto"

    headers = list(data[0].keys()) if data else ['No hay datos']
    ws.append(headers)

    # Estilo de encabezado
    from openpyxl.styles import Font
    for cell in ws[1]:
        cell.font = Font(bold=True)

    # Añadir filas
    for row in data:
        ws.append(list(row.values()))

    # Formato de moneda para columnas numéricas
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=3, max_col=5):
        for cell in row:
            cell.number_format = '"S/ "#,##0.00'

    # Respuesta HTTP
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="reportes_reparto.xlsx"'
    wb.save(response)
    return response

# documentos/views.py
from weasyprint import HTML
from django.template.loader import render_to_string

# documentos/views.py



from decimal import Decimal

@login_required
def despacho_export_pdf(request):
    if not (request.user.is_staff or request.user.is_superuser or request.user.groups.filter(name='Encargados Reparto').exists()):
        return HttpResponse("No tienes permiso.", status=403)

    # Aplicar filtros
    fecha = request.GET.get('fecha')
    repartidor_id = request.GET.get('repartidor')
    estado = request.GET.get('estado')

    despachos = Despacho.objects.select_related('repartidor', 'creado_por').all()

    if fecha:
        try:
            f = timezone.datetime.strptime(fecha, '%Y-%m-%d').date()
            despachos = despachos.filter(fecha=f)
        except ValueError:
            pass
    if repartidor_id:
        try:
            despachos = despachos.filter(repartidor__id=int(repartidor_id))
        except (ValueError, TypeError):
            pass
    if estado and estado in ['abierto', 'cerrado']:
        despachos = despachos.filter(estado=estado)

    # ✅ Recalcular montos reales para cada despacho
    despachos_con_totales = []
    for d in despachos:
        detalles = d.detalles.all()
        
        total_enviado = sum(det.documento.monto_total for det in detalles)
        
        # Calcular saldo pendiente real usando el método del modelo
        saldo_pendiente_real = sum(
            det.documento.get_saldo_pendiente() 
            for det in detalles
        )
        
        total_cobrado_real = total_enviado - saldo_pendiente_real

        # Añadir atributos calculados al objeto
        d.total_enviado_calc = total_enviado
        d.total_cobrado_calc = total_cobrado_real
        d.saldo_pendiente_calc = saldo_pendiente_real

        despachos_con_totales.append(d)

    # Obtener repartidor seleccionado (para mostrar en encabezado)
    repartidor = None
    if repartidor_id:
        try:
            repartidor = User.objects.get(id=repartidor_id)
        except User.DoesNotExist:
            pass

    # Renderizar HTML
    html_string = render_to_string('documentos/despacho_export_pdf.html', {
        'despachos': despachos_con_totales,
        'request': request,
        'fecha': fecha,
        'repartidor': repartidor,
        'estado': estado,
    })

    html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reportes_reparto.pdf"'
    return response