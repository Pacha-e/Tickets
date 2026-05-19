from abc import ABC, abstractmethod
from io import BytesIO
import uuid

from django.core.files.base import ContentFile

from .models import Ticket


class TicketGenerator(ABC):
    @abstractmethod
    def generate(self, reserva) -> list:
        ...


class UUIDTicketGenerator(TicketGenerator):
    def generate(self, reserva) -> list:
        tickets = [
            Ticket(
                reserva=reserva,
                codigo=str(uuid.uuid4()),
                precio_final=reserva.tipo_ticket.precio,
            )
            for _ in range(reserva.cantidad)
        ]
        return Ticket.objects.bulk_create(tickets)


class QRTicketGenerator(TicketGenerator):
    def generate(self, reserva) -> list:
        import qrcode

        tickets = []
        for _ in range(reserva.cantidad):
            ticket = Ticket(
                reserva=reserva,
                codigo=str(uuid.uuid4()),
                precio_final=reserva.tipo_ticket.precio,
            )
            qr = qrcode.make(ticket.codigo)
            buffer = BytesIO()
            qr.save(buffer, format='PNG')
            ticket.qr_code.save(
                f'{ticket.codigo}.png',
                ContentFile(buffer.getvalue()),
                save=False,
            )
            ticket.save()
            tickets.append(ticket)
        return tickets
