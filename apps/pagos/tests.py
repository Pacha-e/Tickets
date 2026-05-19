from django.test import TestCase
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core import mail
from django.core.exceptions import ValidationError
from django.http import Http404
from django.test import override_settings
from django.urls import reverse

from apps.eventos.models import CategoriaEvento, Evento, Lugar, TipoTicket
from apps.pagos.models import Pago
from apps.pagos import services
from apps.reservas import services as reserva_services
from apps.reservas.models import Reserva, Ticket


def _make_base_data():
    categoria = CategoriaEvento.objects.create(nombre='Rock')
    lugar = Lugar.objects.create(
        nombre='Coliseo', direccion='Cra 1', ciudad='Bogota', capacidad=5000
    )
    evento = Evento.objects.create(
        nombre='Festival Pago',
        descripcion='desc',
        fecha='2026-12-01',
        hora='20:00',
        capacidad=500,
        organizador='Org',
        categoria=categoria,
        lugar=lugar,
    )
    tipo = TipoTicket.objects.create(
        evento=evento, nombre='General', precio=50000, cantidad_disponible=20
    )
    return evento, tipo


class ProcesarPagoTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.settings_override = override_settings(
            MEDIA_ROOT=self.media_root,
            EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        )
        self.settings_override.enable()
        self.usuario = User.objects.create_user(
            'pagador', password='pass', email='pagador@example.com'
        )
        self.otro_usuario = User.objects.create_user('otro', password='pass')
        self.evento, self.tipo = _make_base_data()
        self.reserva = reserva_services.crear_reserva(
            self.usuario, self.evento.id, self.tipo.id, 2
        )

    def tearDown(self):
        self.settings_override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def test_procesar_pago_confirma_reserva_crea_tickets_qr_y_email(self):
        with self.captureOnCommitCallbacks(execute=True):
            pago, tickets = services.procesar_pago(self.reserva.id, 'tarjeta', self.usuario)

        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, 'confirmada')
        self.assertEqual(pago.estado, 'aprobado')
        self.assertEqual(pago.monto, self.reserva.cantidad * self.tipo.precio)
        self.assertEqual(len(tickets), 2)
        self.assertEqual(Ticket.objects.filter(reserva=self.reserva).count(), 2)
        self.assertTrue(all(ticket.qr_code for ticket in tickets))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Pase Confirmado', mail.outbox[0].subject)

    def test_procesar_pago_rechaza_metodo_invalido_sin_efectos(self):
        with self.assertRaises(ValidationError):
            services.procesar_pago(self.reserva.id, 'crypto', self.usuario)

        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, 'pendiente')
        self.assertFalse(Pago.objects.exists())
        self.assertFalse(Ticket.objects.exists())

    def test_procesar_pago_no_permite_reserva_de_otro_usuario(self):
        with self.assertRaises(Http404):
            services.procesar_pago(self.reserva.id, 'pse', self.otro_usuario)

    def test_pagar_view_post_redirige_a_exitoso(self):
        self.client.login(username='pagador', password='pass')
        response = self.client.post(
            reverse('pagar', args=[self.reserva.id]),
            {'metodo': 'efectivo'},
            follow=True,
        )

        self.assertRedirects(response, reverse('pago_exitoso', args=[self.reserva.id]))
        self.assertContains(response, 'ticket-qr__image')

    def test_pagar_view_rechaza_metodo_invalido(self):
        self.client.login(username='pagador', password='pass')
        response = self.client.post(
            reverse('pagar', args=[self.reserva.id]),
            {'metodo': 'crypto'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Pago.objects.exists())

    def test_pagar_view_reserva_ya_confirmada_redirige(self):
        reserva_services.confirmar_reserva(self.reserva)
        self.client.login(username='pagador', password='pass')

        response = self.client.get(reverse('pagar', args=[self.reserva.id]))

        self.assertRedirects(response, '/reservas/mis-reservas/')

    def test_descargar_ticket_pdf_incluye_respuesta_pdf(self):
        self.client.login(username='pagador', password='pass')
        _, tickets = services.procesar_pago(self.reserva.id, 'tarjeta', self.usuario)

        response = self.client.get(reverse('descargar_ticket', args=[tickets[0].id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_urls_de_descarga_no_colisionan(self):
        self.assertEqual(reverse('descargar_ticket', args=[99]), '/pagos/ticket/99/pdf/')
        self.assertEqual(
            reverse('descargar_reserva_ticket', args=[99]),
            '/reservas/descargar/99/',
        )
