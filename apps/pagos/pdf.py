from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def build_ticket_pdf_response(ticket):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ticket_{ticket.codigo}.pdf"'

    pdf = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    _draw_header(pdf, width, height)
    _draw_ticket_details(pdf, ticket, height)
    _draw_qr(pdf, ticket, height)

    pdf.showPage()
    pdf.save()
    return response


def _draw_header(pdf, width, height):
    pdf.setFont('Helvetica-Bold', 20)
    pdf.drawCentredString(width / 2, height - 80, 'VibePas - Tu Entrada')
    pdf.setFont('Helvetica', 12)
    pdf.drawCentredString(width / 2, height - 110, 'Presenta este codigo en la entrada')
    pdf.line(50, height - 125, width - 50, height - 125)


def _draw_ticket_details(pdf, ticket, height):
    rows = [
        ('Evento:', ticket.reserva.evento.nombre, height - 160),
        ('Tipo:', ticket.reserva.tipo_ticket.nombre, height - 190),
        ('Titular:', ticket.reserva.usuario.username, height - 220),
        ('Precio:', f'${ticket.precio_final}', height - 250),
        ('Codigo:', ticket.codigo, height - 280),
    ]
    for label, value, y in rows:
        pdf.setFont('Helvetica-Bold', 13)
        pdf.drawString(60, y, label)
        pdf.setFont('Helvetica', 13)
        pdf.drawString(160, y, str(value))

    pdf.line(50, height - 300, A4[0] - 50, height - 300)


def _draw_qr(pdf, ticket, height):
    if not ticket.qr_code:
        return

    try:
        ticket.qr_code.open('rb')
        pdf.drawImage(ImageReader(ticket.qr_code.file), 60, height - 450, width=120, height=120)
    except (OSError, ValueError):
        return
    finally:
        ticket.qr_code.close()
