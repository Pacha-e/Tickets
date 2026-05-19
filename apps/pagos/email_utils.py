from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


def enviar_confirmacion(reserva, pago):
    """Send booking confirmation email after successful payment."""
    if not reserva.usuario.email:
        return
    context = {'reserva': reserva, 'pago': pago}
    subject = f'Pase Confirmado: {reserva.evento.nombre}'
    plain = render_to_string('emails/reserva_confirmada.txt', context)
    html = render_to_string('emails/reserva_confirmada.html', context)
    send_mail(
        subject=subject,
        message=plain,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@vibepas.com'),
        recipient_list=[reserva.usuario.email],
        html_message=html,
        fail_silently=True,
    )


def enviar_cancelacion(reserva):
    """Send cancellation notification email."""
    if not reserva.usuario.email:
        return
    context = {'reserva': reserva}
    subject = f'Pase Cancelado: {reserva.evento.nombre}'
    plain = render_to_string('emails/reserva_cancelada.txt', context)
    html = render_to_string('emails/reserva_cancelada.html', context)
    send_mail(
        subject=subject,
        message=plain,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@vibepas.com'),
        recipient_list=[reserva.usuario.email],
        html_message=html,
        fail_silently=True,
    )
