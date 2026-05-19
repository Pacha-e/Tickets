from django.contrib.sitemaps import Sitemap
from apps.eventos.models import Evento


class EventoSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Evento.objects.all().order_by('-fecha')

    def location(self, obj):
        from django.urls import reverse
        return reverse('detalle_evento', args=[obj.pk])

    def lastmod(self, obj):
        return obj.fecha
