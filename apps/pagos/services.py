from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404

from apps.reservas import services as reserva_services
from apps.reservas.models import Reserva

from .email_utils import enviar_confirmacion
from .models import Pago


METODOS_VALIDOS = {'tarjeta', 'pse', 'efectivo'}


@transaction.atomic
def procesar_pago(reserva_id, metodo, usuario):
    """Approve payment, confirm reservation and generate its tickets."""
    if metodo not in METODOS_VALIDOS:
        raise ValidationError('Metodo de pago no valido.')

    reserva = _get_reserva_pendiente_para_pago(reserva_id, usuario)
    pago = _aprobar_pago(reserva, metodo)

    reserva_services.confirmar_reserva(reserva)
    tickets = reserva_services.generar_tickets(reserva)

    transaction.on_commit(lambda: enviar_confirmacion(reserva, pago))

    return pago, tickets


def _get_reserva_pendiente_para_pago(reserva_id, usuario):
    reserva = get_object_or_404(
        Reserva.objects.select_for_update().select_related('evento', 'tipo_ticket'),
        pk=reserva_id,
        usuario=usuario,
    )
    if reserva.estado != 'pendiente':
        raise ValidationError('Este pase no puede ser pagado.')
    return reserva


def _aprobar_pago(reserva, metodo):
    monto = reserva.cantidad * reserva.tipo_ticket.precio
    pago, _ = Pago.objects.get_or_create(
        reserva=reserva,
        defaults={'metodo': metodo, 'monto': monto},
    )
    pago.metodo = metodo
    pago.monto = monto
    pago.estado = 'aprobado'
    pago.save()
    return pago
