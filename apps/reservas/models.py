# Autor: Thomas Osorio

from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User

from apps.eventos.models import Evento, TipoTicket


class Reserva(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservas')
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='reservas')
    tipo_ticket = models.ForeignKey(TipoTicket, on_delete=models.CASCADE, related_name='reservas')
    cantidad = models.PositiveIntegerField()
    fecha_reserva = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')

    def clean(self):
        if self.cantidad and self.tipo_ticket_id:
            tipo = self.tipo_ticket
            if self.cantidad > tipo.cantidad_disponible:
                raise ValidationError(
                    f'Solo hay {tipo.cantidad_disponible} disponibles'
                )

    def __str__(self):
        return f'Reserva #{self.id} - {self.usuario.username}'


class Ticket(models.Model):
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE, related_name='tickets')
    codigo = models.CharField(max_length=100, unique=True)
    qr_code = models.ImageField(upload_to='tickets/qr/', null=True, blank=True)
    precio_final = models.DecimalField(max_digits=10, decimal_places=2)
    usado = models.BooleanField(default=False)

    def __str__(self):
        return self.codigo
