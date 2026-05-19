from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from apps.eventos.models import Evento

from . import services
from .forms import ReservaForm
from .models import Reserva
from .pdf import build_reservation_ticket_pdf_response


@login_required
def mis_reservas(request):
    reservas = (
        Reserva.objects.filter(usuario=request.user)
        .exclude(estado='cancelada')
        .select_related('evento', 'tipo_ticket')
        .order_by('-fecha_reserva')
    )
    return render(request, 'reservas/mis_reservas.html', {'reservas': reservas})


@login_required
def crear_reserva(request, evento_id):
    evento = get_object_or_404(Evento, pk=evento_id)

    if request.method == 'POST':
        form = ReservaForm(request.POST, evento=evento)
        if form.is_valid():
            try:
                reserva = services.crear_reserva(
                    usuario=request.user,
                    evento_id=evento.id,
                    tipo_ticket_id=form.cleaned_data['tipo_ticket'].id,
                    cantidad=form.cleaned_data['cantidad'],
                )
                return redirect('confirmacion_reserva', reserva_id=reserva.pk)
            except ValidationError as exc:
                messages.error(request, exc.messages[0])
                return redirect('crear_reserva', evento_id=evento.id)
    else:
        initial = {}
        if tipo_id := request.GET.get('tipo'):
            initial['tipo_ticket'] = tipo_id
        form = ReservaForm(evento=evento, initial=initial)

    return render(request, 'reservas/crear_reserva.html', {'form': form, 'evento': evento})


@login_required
def confirmacion_reserva(request, reserva_id):
    reserva = get_object_or_404(
        Reserva.objects.select_related('evento', 'tipo_ticket', 'evento__lugar'),
        pk=reserva_id,
        usuario=request.user,
    )
    return render(request, 'reservas/confirmacion_reserva.html', {'reserva': reserva})


@login_required
def cancelar_reserva(request, reserva_id):
    if request.method != 'POST':
        return redirect('mis_reservas')

    try:
        services.cancelar_reserva(reserva_id=reserva_id, usuario=request.user)
        messages.success(request, 'Pase cancelado correctamente.')
    except ValidationError as exc:
        messages.warning(request, exc.messages[0])

    return redirect('mis_reservas')


@login_required
def descargar_ticket_pdf(request, reserva_id):
    reserva = get_object_or_404(
        Reserva.objects.select_related('evento', 'tipo_ticket', 'evento__lugar', 'usuario'),
        pk=reserva_id,
        usuario=request.user,
    )

    if reserva.estado != 'confirmada':
        messages.error(request, 'Solo puedes descargar pases confirmados.')
        return redirect('mis_reservas')

    return build_reservation_ticket_pdf_response(reserva)
