from django.test import TestCase
from django.test import override_settings
from django.urls import reverse

from . import services
from .models import CategoriaEvento, Evento, Lugar, TipoTicket


class EventoServicesTests(TestCase):
    def setUp(self):
        self.rock = CategoriaEvento.objects.create(nombre='Rock')
        self.jazz = CategoriaEvento.objects.create(nombre='Jazz')
        self.lugar = Lugar.objects.create(
            nombre='Arena', direccion='Calle 1', ciudad='Medellin', capacidad=1000
        )
        self.evento_rock = Evento.objects.create(
            nombre='Noche Rock',
            descripcion='guitarras distorsionadas',
            fecha='2026-08-10',
            hora='20:00',
            capacidad=300,
            organizador='Org',
            categoria=self.rock,
            lugar=self.lugar,
        )
        self.evento_jazz = Evento.objects.create(
            nombre='Club Azul',
            descripcion='sesion acustica',
            fecha='2026-09-10',
            hora='21:00',
            capacidad=200,
            organizador='Org',
            categoria=self.jazz,
            lugar=self.lugar,
        )
        TipoTicket.objects.create(
            evento=self.evento_rock, nombre='General', precio=30000, cantidad_disponible=5
        )

    def test_get_eventos_disponibles_filtra_por_categoria_fecha_y_busqueda(self):
        qs = services.get_eventos_disponibles(
            {
                'categoria': self.rock.id,
                'fecha_inicio': '2026-08-01',
                'fecha_fin': '2026-08-31',
                'q': 'guitarras',
            }
        )

        self.assertEqual(list(qs), [self.evento_rock])

    def test_get_evento_detalle_prefetch_tipos_ticket(self):
        evento = services.get_evento_detalle(self.evento_rock.id)

        self.assertEqual(evento.nombre, 'Noche Rock')
        self.assertEqual(len(evento.tipos_ticket.all()), 1)


class EventoViewAndSeoTests(TestCase):
    def setUp(self):
        self.categoria = CategoriaEvento.objects.create(nombre='Rock')
        self.lugar = Lugar.objects.create(
            nombre='Arena', direccion='Calle 1', ciudad='Medellin', capacidad=1000
        )
        self.evento = Evento.objects.create(
            nombre='Noche Rock',
            descripcion='guitarras distorsionadas',
            fecha='2026-08-10',
            hora='20:00',
            capacidad=300,
            organizador='Org',
            categoria=self.categoria,
            lugar=self.lugar,
        )

    def test_catalogo_eventos_filtra_por_nombre(self):
        response = self.client.get(reverse('catalogo_eventos'), {'q': 'Noche'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Noche Rock')

    def test_detalle_evento_incluye_open_graph(self):
        response = self.client.get(reverse('detalle_evento', args=[self.evento.id]))

        self.assertContains(response, 'property="og:type" content="event"')
        self.assertContains(response, 'Noche Rock')

    def test_robots_txt_y_sitemap_responden(self):
        robots = self.client.get('/robots.txt')
        sitemap = self.client.get('/sitemap.xml')

        self.assertContains(robots, 'Sitemap: http://testserver/sitemap.xml')
        self.assertEqual(sitemap.status_code, 200)
        self.assertIn('application/xml', sitemap['Content-Type'])

    @override_settings(DEBUG=False, ALLOWED_HOSTS=['testserver'])
    def test_404_personalizado_renderiza(self):
        response = self.client.get('/no-existe/')

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, '404', status_code=404)
