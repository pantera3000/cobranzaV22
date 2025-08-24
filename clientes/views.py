from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.contrib import messages
from .models import Cliente
from .models import Cliente, LogActividad  # ✅ Asegúrate de importar LogActividad
from .forms import ClienteForm
from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from .models import Cliente, EmpresaConfig  # ✅ Añade EmpresaConfig aquí
import csv
from openpyxl import Workbook
from documentos.models import Documento
from cobros.models import Cobro
from devoluciones.models import Devolucion
from django.db.models import Sum, F
from django.utils import timezone  # ✅ Falta: para timezone.now()
from .utils import registrar_log  # ✅ IMPORTA la función aquí
from django.contrib.auth.decorators import login_required, permission_required

from datetime import timedelta


from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from .models import LogActividad

@user_passes_test(lambda u: u.is_superuser)
def limpiar_log(request):
    if request.method == 'POST':
        # Configura aquí cuántos meses atrás quieres borrar
        meses = int(request.POST.get('meses', 6))  # Por defecto: 6 meses
        limite = timezone.now() - timedelta(days=30 * meses)

        # Cuenta cuántos registros se eliminarán
        total_a_borrar = LogActividad.objects.filter(fecha__lt=limite).count()

        # Borra los registros antiguos
        LogActividad.objects.filter(fecha__lt=limite).delete()

        messages.success(
            request,
            f'Log de auditoría limpiado. Se eliminaron {total_a_borrar} registros anteriores a {meses} meses.'
        )
    return redirect('clientes:log_actividad')




@permission_required('clientes.change_empresaconfig', raise_exception=True)
def empresa_config(request):
    config = EmpresaConfig.objects.first()
    if not config:
        config = EmpresaConfig.objects.create(nombre="Empresa sin nombre")

    if request.method == 'POST':
        config.nombre = request.POST.get('nombre')
        config.ruc = request.POST.get('ruc')
        config.direccion = request.POST.get('direccion')
        config.telefono = request.POST.get('telefono')
        config.correo = request.POST.get('correo')
        if 'logo' in request.FILES:
            config.logo = request.FILES['logo']
        config.save()
        messages.success(request, 'Configuración actualizada.')
        return redirect('clientes:empresa_config')

    return render(request, 'clientes/empresa_config.html', {
        'config': config
    })




@permission_required('clientes.view_logactividad', raise_exception=True)
def log_actividad(request):
    # Obtener logs de los últimos 30 días (ajusta según necesidad)
    fecha_inicio = timezone.now() - timedelta(days=30)
    logs = LogActividad.objects.filter(fecha__gte=fecha_inicio).select_related('usuario', 'cobrador').order_by('-fecha')

    # Filtro por categoría
    categoria = request.GET.get('categoria')
    if categoria:
        logs = logs.filter(categoria=categoria)

    # Paginación
    paginator = Paginator(logs, 25)  # 25 por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'clientes/log_actividad.html', {
        'page_obj': page_obj,
        'categoria': categoria,
        'categorias': LogActividad.CATEGORIA_OPCIONES,
    })


def cliente_list(request):
    query = request.GET.get('q', '')
    if query:
        clientes = Cliente.objects.filter(
            Q(nombre__icontains=query) | Q(dni_ruc__icontains=query)
        )
    else:
        clientes = Cliente.objects.all()

    paginator = Paginator(clientes, 10)  # 10 por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'clientes/cliente_list.html', {
        'page_obj': page_obj,
        'query': query
    })


def cliente_detail(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)

    # Filtros y paginación para Documentos
    docs_query = request.GET.get('docs_q')
    if docs_query == 'None':
        docs_query = None
    docs_page = request.GET.get('docs_page', 1)
    documentos = Documento.objects.filter(cliente=cliente).order_by('-fecha_emision')
    if docs_query:
        documentos = documentos.filter(
            Q(numero__icontains=docs_query) |
            Q(serie__icontains=docs_query)
        )
    docs_paginator = Paginator(documentos, 20)
    docs_page_obj = docs_paginator.get_page(docs_page)

    # Filtros y paginación para Cobros (Pagos)
    cobros_query = request.GET.get('cobros_q')
    if cobros_query == 'None':
        cobros_query = None
    cobros_page = request.GET.get('cobros_page', 1)
    cobros = Cobro.objects.filter(documento__cliente=cliente).select_related('documento').order_by('-fecha')
    if cobros_query:
        cobros = cobros.filter(
            Q(documento__numero__icontains=cobros_query) |
            Q(monto__icontains=cobros_query)
        )
    cobros_paginator = Paginator(cobros, 20)
    cobros_page_obj = cobros_paginator.get_page(cobros_page)



    

    # Filtros y paginación para Devoluciones
    devoluciones_query = request.GET.get('devoluciones_q')
    if devoluciones_query == 'None':
        devoluciones_query = None
    devoluciones_page = request.GET.get('devoluciones_page', 1)
    devoluciones = Devolucion.objects.filter(documento__cliente=cliente).select_related('documento').order_by('-fecha')
    if devoluciones_query:
        devoluciones = devoluciones.filter(
            Q(documento__numero__icontains=devoluciones_query) |
            Q(monto__icontains=devoluciones_query)
        )
    devoluciones_paginator = Paginator(devoluciones, 20)
    devoluciones_page_obj = devoluciones_paginator.get_page(devoluciones_page)

    # ✅ Cálculos de resumen
    total_facturado = documentos.aggregate(total=Sum('monto_total'))['total'] or 0
    total_pagado = sum(doc.monto_pagado for doc in documentos)
    total_devolucion = sum(doc.monto_devolucion for doc in documentos)
    saldo_pendiente = total_facturado - total_pagado - total_devolucion

    # Documentos vencidos con saldo pendiente
    vencidos = documentos.filter(
        fecha_vencimiento__lt=timezone.now(),
        monto_total__gt=F('monto_pagado') + F('monto_devolucion')
    )
    total_vencido = sum(doc.get_saldo_pendiente() for doc in vencidos)


    # ✅ Calcular cuántos documentos tiene cada referencia
    referencia_count = {}
    for cobro in cobros:
        ref = cobro.referencia
        if ref:
            if ref not in referencia_count:
                referencia_count[ref] = 0
            referencia_count[ref] += 1



    return render(request, 'clientes/cliente_detail.html', {
        'cliente': cliente,
        'docs_page_obj': docs_page_obj,
        'cobros_page_obj': cobros_page_obj,
        'devoluciones_page_obj': devoluciones_page_obj,
        'docs_query': docs_query,
        'cobros_query': cobros_query,
        'devoluciones_query': devoluciones_query,
        'referencia_count': referencia_count,  # ✅ Añadido

        # ✅ Datos del resumen
        'total_facturado': total_facturado,
        'total_pagado': total_pagado,
        'total_devolucion': total_devolucion,
        'saldo_pendiente': saldo_pendiente,
        'total_vencido': total_vencido,
    })



# clientes/views.py
def cliente_create(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save()  # ✅ Guardamos el objeto para usarlo
            # ✅ Registrar log
            registrar_log(
                usuario=request.user,
                categoria='cliente',
                accion='Creó cliente',
                descripcion=f"Nombre: {cliente.nombre}, DNI/RUC: {cliente.dni_ruc}"
            )
            messages.success(request, 'Cliente creado exitosamente.')
            return redirect('clientes:cliente_list')
    else:
        form = ClienteForm()
    return render(request, 'clientes/cliente_form.html', {
        'form': form,
        'title': 'Crear Cliente'
    })


def cliente_update(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente actualizado exitosamente.')
            return redirect('clientes:cliente_list')
    else:
        form = ClienteForm(instance=cliente)
    return render(request, 'clientes/cliente_form.html', {
        'form': form,
        'title': 'Editar Cliente'
    })


# clientes/views.py
def cliente_delete(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        # ✅ Registrar log antes de eliminar
        registrar_log(
            usuario=request.user,
            categoria='cliente',
            accion='Eliminó cliente',
            descripcion=f"Nombre: {cliente.nombre}, DNI/RUC: {cliente.dni_ruc}"
        )
        cliente.delete()
        messages.success(request, 'Cliente eliminado exitosamente.')
        return redirect('clientes:cliente_list')
    return render(request, 'clientes/cliente_confirm_delete.html', {
        'cliente': cliente
    })


def cliente_export_excel(request):
    clientes = Cliente.objects.all()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Clientes"

    # Encabezados
    headers = ['Nombre', 'DNI/RUC', 'Dirección', 'Teléfono', 'Correo', 'Notas', 'Creado en']
    for col_num, header in enumerate(headers, 1):
        cell = sheet.cell(row=1, column=col_num)
        cell.value = header

    # Datos
    for cliente in clientes:
        row = [
            cliente.nombre,
            cliente.dni_ruc,
            cliente.direccion or '',
            cliente.telefono or '',
            cliente.correo or '',
            cliente.notas or '',
            cliente.creado_en.strftime('%d/%m/%Y %H:%M')
        ]
        sheet.append(row)

    # Preparar respuesta HTTP
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=clientes.xlsx'
    workbook.save(response)
    return response


def cliente_export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=clientes.csv'

    writer = csv.writer(response)
    writer.writerow(['Nombre', 'DNI/RUC', 'Dirección', 'Teléfono', 'Correo', 'Notas', 'Creado en'])

    for cliente in Cliente.objects.all():
        writer.writerow([
            cliente.nombre,
            cliente.dni_ruc,
            cliente.direccion or '',
            cliente.telefono or '',
            cliente.correo or '',
            cliente.notas or '',
            cliente.creado_en.strftime('%d/%m/%Y %H:%M')
        ])

    return response