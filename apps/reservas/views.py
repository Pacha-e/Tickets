# Autor: Thomas Osorio

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from apps.eventos.models import Evento
from .models import Reserva
from .forms import ReservaForm


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
            reserva = form.save(commit=False)
            reserva.usuario = request.user
            reserva.evento = evento
            reserva.save()

            # Descontar disponibilidad del tipo de ticket
            tipo = reserva.tipo_ticket
            tipo.cantidad_disponible -= reserva.cantidad
            tipo.save()

            return redirect('confirmacion_reserva', reserva_id=reserva.pk)
    else:
        # Pre-seleccionar tipo si viene por querystring (?tipo=<id>)
        initial = {}
        tipo_id = request.GET.get('tipo')
        if tipo_id:
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

    reserva = get_object_or_404(Reserva, pk=reserva_id, usuario=request.user)

    if reserva.estado == 'pendiente':
        # Devolver disponibilidad al tipo de ticket
        tipo = reserva.tipo_ticket
        tipo.cantidad_disponible += reserva.cantidad
        tipo.save()

        reserva.estado = 'cancelada'
        reserva.save()
        messages.success(request, 'Pase cancelado correctamente.')
    else:
        messages.warning(request, 'Solo se pueden cancelar pases en estado pendiente.')

    return redirect('mis_reservas')
