# Autor: Thomas Osorio

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from apps.reservas.models import Reserva
from .models import Pago


@login_required
def pagar(request, reserva_id):
    reserva = get_object_or_404(
        Reserva.objects.select_related('evento', 'tipo_ticket', 'evento__lugar'),
        pk=reserva_id,
        usuario=request.user,
    )

    # Only pending reservations can be paid
    if reserva.estado != 'pendiente':
        messages.warning(request, 'Este pase no puede ser pagado.')
        return redirect('mis_reservas')

    # Already has a payment — redirect to success
    if hasattr(reserva, 'pago') and reserva.pago.estado == 'aprobado':
        return redirect('pago_exitoso', reserva_id=reserva_id)

    monto = reserva.cantidad * reserva.tipo_ticket.precio

    if request.method == 'POST':
        metodo = request.POST.get('metodo')
        if metodo not in ('tarjeta', 'pse', 'efectivo'):
            messages.error(request, 'Seleccioná un método de pago válido.')
        else:
            pago, created = Pago.objects.get_or_create(
                reserva=reserva,
                defaults={'metodo': metodo, 'monto': monto},
            )
            if not created:
                pago.metodo = metodo
                pago.monto = monto

            pago.estado = 'aprobado'
            pago.save()

            reserva.estado = 'confirmada'
            reserva.save()

            return redirect('pago_exitoso', reserva_id=reserva_id)

    return render(request, 'pagos/pagar.html', {
        'reserva': reserva,
        'monto': monto,
    })


@login_required
def pago_exitoso(request, reserva_id):
    reserva = get_object_or_404(
        Reserva.objects.select_related('evento', 'tipo_ticket', 'evento__lugar', 'pago'),
        pk=reserva_id,
        usuario=request.user,
    )
    return render(request, 'pagos/pago_exitoso.html', {'reserva': reserva})
