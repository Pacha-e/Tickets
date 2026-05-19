from io import BytesIO

from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def build_reservation_ticket_pdf_response(reserva):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    _draw_reservation_ticket(pdf, reserva)

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="vibepas_ticket_{reserva.id}.pdf"'
    return response


def _draw_reservation_ticket(pdf, reserva):
    pdf.setFont('Helvetica-Bold', 24)
    pdf.drawString(100, 700, 'VIBEPAS - Ticket de Entrada')

    pdf.setFont('Helvetica', 14)
    pdf.drawString(100, 650, f'Evento: {reserva.evento.nombre}')
    pdf.drawString(100, 620, f'Lugar: {reserva.evento.lugar.nombre}')
    pdf.drawString(100, 590, f'Fecha: {reserva.evento.fecha} a las {reserva.evento.hora}')
    pdf.drawString(100, 560, f'Tipo de Pase: {reserva.tipo_ticket.nombre}')
    pdf.drawString(100, 530, f'Cantidad: {reserva.cantidad}')
    pdf.drawString(100, 500, f'Titular: {_ticket_holder(reserva)}')

    pdf.setFont('Helvetica-Oblique', 12)
    pdf.drawString(100, 450, f'Reserva #{reserva.id} - Rock on!')


def _ticket_holder(reserva):
    user = reserva.usuario
    full_name = f'{user.first_name} {user.last_name}'.strip()
    return full_name or user.username
