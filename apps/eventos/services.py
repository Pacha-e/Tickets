from django.db.models import Q
from django.shortcuts import get_object_or_404

from .models import CategoriaEvento, Evento


def get_categorias():
    return CategoriaEvento.objects.order_by('nombre')


def get_eventos_disponibles(filters: dict):
    """Return a filtered, select_related queryset of Evento."""
    qs = Evento.objects.select_related('categoria', 'lugar').order_by('fecha')

    if categoria_id := filters.get('categoria'):
        qs = qs.filter(categoria_id=categoria_id)
    if fecha_inicio := filters.get('fecha_inicio'):
        qs = qs.filter(fecha__gte=fecha_inicio)
    if fecha_fin := filters.get('fecha_fin'):
        qs = qs.filter(fecha__lte=fecha_fin)
    if q := filters.get('q'):
        qs = qs.filter(Q(nombre__icontains=q) | Q(descripcion__icontains=q))

    return qs


def get_evento_detalle(evento_id):
    """Return single Evento with prefetched tipos_ticket."""
    return get_object_or_404(
        Evento.objects.select_related('categoria', 'lugar').prefetch_related('tipos_ticket'),
        pk=evento_id,
    )
