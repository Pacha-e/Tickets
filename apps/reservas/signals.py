# Author: Juan José Baron Osorio
import uuid
from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Ticket


@receiver(pre_save, sender=Ticket)
def generar_codigo_unico(sender, instance, **kwargs):
    # Genera código único solo si el ticket aún no tiene uno
    if not instance.codigo:
        instance.codigo = str(uuid.uuid4()).replace('-', '').upper()[:20]