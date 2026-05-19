from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from apps.reservas.models import Reserva, Ticket

from . import services
from .pdf import build_ticket_pdf_response


@login_required
def pagar(request, reserva_id):
    reserva = get_object_or_404(
        Reserva.objects.select_related('evento', 'tipo_ticket', 'evento__lugar', 'pago'),
        pk=reserva_id,
        usuario=request.user,
    )

    if hasattr(reserva, 'pago') and reserva.pago.estado == 'aprobado':
        return redirect('pago_exitoso', reserva_id=reserva_id)

    if reserva.estado != 'pendiente':
        messages.warning(request, 'Este pase no puede ser pagado.')
        return redirect('mis_reservas')

    monto = reserva.cantidad * reserva.tipo_ticket.precio

    if request.method == 'POST':
        metodo = request.POST.get('metodo')
        try:
            services.procesar_pago(
                reserva_id=reserva_id,
                metodo=metodo,
                usuario=request.user,
            )
            return redirect('pago_exitoso', reserva_id=reserva_id)
        except ValidationError as exc:
            messages.error(request, exc.messages[0])

    return render(request, 'pagos/pagar.html', {'reserva': reserva, 'monto': monto})


@login_required
def pago_exitoso(request, reserva_id):
    reserva = get_object_or_404(
        Reserva.objects.select_related('evento', 'tipo_ticket', 'evento__lugar', 'pago')
        .prefetch_related('tickets'),
        pk=reserva_id,
        usuario=request.user,
    )
    return render(request, 'pagos/pago_exitoso.html', {'reserva': reserva})


@login_required
def descargar_ticket(request, ticket_id):
    ticket = get_object_or_404(
        Ticket.objects.select_related(
            'reserva__evento',
            'reserva__tipo_ticket',
            'reserva__usuario',
        ),
        pk=ticket_id,
        reserva__usuario=request.user,
    )
    return build_ticket_pdf_response(ticket)
