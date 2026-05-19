import os
import shutil
import tempfile
import threading
import unittest

from django.contrib.auth.models import User
from django.core import mail
from django.db import close_old_connections, connection
from django.core.exceptions import ValidationError
from django.test import TestCase, TransactionTestCase, override_settings

from apps.eventos.models import CategoriaEvento, Evento, Lugar, TipoTicket
from apps.reservas import services
from apps.reservas.models import Reserva, Ticket
from apps.reservas.ticket_generator import QRTicketGenerator, UUIDTicketGenerator


def _make_base_data():
    categoria = CategoriaEvento.objects.create(nombre='Rock')
    lugar = Lugar.objects.create(
        nombre='Coliseo', direccion='Cra 1', ciudad='Bogotá', capacidad=5000
    )
    evento = Evento.objects.create(
        nombre='Festival Test',
        descripcion='desc',
        fecha='2026-12-01',
        hora='20:00',
        capacidad=500,
        organizador='Org',
        categoria=categoria,
        lugar=lugar,
    )
    return evento


class CrearReservaTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user('tester', password='pass')
        self.evento = _make_base_data()
        self.tipo = TipoTicket.objects.create(
            evento=self.evento, nombre='General', precio=50000, cantidad_disponible=100
        )

    def test_reserva_descuenta_cantidad_disponible(self):
        services.crear_reserva(self.usuario, self.evento.id, self.tipo.id, 5)
        self.tipo.refresh_from_db()
        self.assertEqual(self.tipo.cantidad_disponible, 95)

    def test_no_se_puede_reservar_mas_de_lo_disponible(self):
        tipo_escaso = TipoTicket.objects.create(
            evento=self.evento, nombre='VIP', precio=100000, cantidad_disponible=2
        )
        with self.assertRaises(ValidationError):
            services.crear_reserva(self.usuario, self.evento.id, tipo_escaso.id, 5)
        tipo_escaso.refresh_from_db()
        self.assertEqual(tipo_escaso.cantidad_disponible, 2)  # no se modificó

    def test_no_se_puede_reservar_tipo_de_otro_evento(self):
        otro_evento = Evento.objects.create(
            nombre='Otro Festival',
            descripcion='desc',
            fecha='2026-12-02',
            hora='21:00',
            capacidad=100,
            organizador='Org',
            categoria=self.evento.categoria,
            lugar=self.evento.lugar,
        )
        tipo_otro_evento = TipoTicket.objects.create(
            evento=otro_evento,
            nombre='VIP',
            precio=100000,
            cantidad_disponible=2,
        )

        with self.assertRaises(ValidationError):
            services.crear_reserva(
                self.usuario,
                self.evento.id,
                tipo_otro_evento.id,
                1,
            )

        tipo_otro_evento.refresh_from_db()
        self.assertEqual(tipo_otro_evento.cantidad_disponible, 2)

    def test_cancelar_reserva_restaura_disponibilidad(self):
        reserva = services.crear_reserva(self.usuario, self.evento.id, self.tipo.id, 3)
        self.tipo.refresh_from_db()
        self.assertEqual(self.tipo.cantidad_disponible, 97)

        services.cancelar_reserva(reserva.id, self.usuario)
        self.tipo.refresh_from_db()
        self.assertEqual(self.tipo.cantidad_disponible, 100)

        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, 'cancelada')

    def test_ticket_codigo_es_unico(self):
        reserva1 = services.crear_reserva(self.usuario, self.evento.id, self.tipo.id, 1)
        reserva2 = services.crear_reserva(self.usuario, self.evento.id, self.tipo.id, 1)

        gen = UUIDTicketGenerator()
        tickets1 = gen.generate(reserva1)
        tickets2 = gen.generate(reserva2)

        codigos = {t.codigo for t in tickets1} | {t.codigo for t in tickets2}
        self.assertEqual(len(codigos), 2)

    def test_qr_ticket_generator_crea_imagenes_por_ticket(self):
        media_root = tempfile.mkdtemp()
        with override_settings(MEDIA_ROOT=media_root):
            reserva = services.crear_reserva(self.usuario, self.evento.id, self.tipo.id, 2)
            tickets = QRTicketGenerator().generate(reserva)

            self.assertEqual(len(tickets), 2)
            self.assertEqual(Ticket.objects.filter(reserva=reserva).count(), 2)
            for ticket in tickets:
                self.assertTrue(ticket.qr_code.name.startswith('tickets/qr/'))
                self.assertTrue(os.path.exists(ticket.qr_code.path))
        shutil.rmtree(media_root, ignore_errors=True)

    def test_generar_tickets_no_duplica_si_la_reserva_ya_tiene_tickets(self):
        media_root = tempfile.mkdtemp()
        with override_settings(MEDIA_ROOT=media_root):
            reserva = services.crear_reserva(self.usuario, self.evento.id, self.tipo.id, 1)
            first = services.generar_tickets(reserva)
            second = services.generar_tickets(reserva)

            self.assertEqual(first, second)
            self.assertEqual(Ticket.objects.filter(reserva=reserva).count(), 1)
        shutil.rmtree(media_root, ignore_errors=True)


class ReservaModelCleanTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user('tester2', password='pass')
        self.evento = _make_base_data()
        self.tipo = TipoTicket.objects.create(
            evento=self.evento, nombre='General', precio=30000, cantidad_disponible=10
        )

    def test_clean_raises_when_cantidad_exceeds_disponible(self):
        reserva = Reserva(
            usuario=self.usuario,
            evento=self.evento,
            tipo_ticket=self.tipo,
            cantidad=50,
        )
        with self.assertRaises(ValidationError):
            reserva.clean()

    def test_clean_passes_when_cantidad_ok(self):
        reserva = Reserva(
            usuario=self.usuario,
            evento=self.evento,
            tipo_ticket=self.tipo,
            cantidad=5,
        )
        reserva.clean()  # no exception


class ReservaViewTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(
            'viewer', password='pass', email='viewer@example.com'
        )
        self.evento = _make_base_data()
        self.tipo = TipoTicket.objects.create(
            evento=self.evento, nombre='General', precio=30000, cantidad_disponible=10
        )

    def test_crear_reserva_requiere_login(self):
        response = self.client.get(f'/reservas/crear/{self.evento.id}/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])

    def test_crear_reserva_post_crea_y_redirige_a_confirmacion(self):
        self.client.login(username='viewer', password='pass')
        response = self.client.post(
            f'/reservas/crear/{self.evento.id}/',
            {'tipo_ticket': self.tipo.id, 'cantidad': 2},
        )

        reserva = Reserva.objects.get(usuario=self.usuario)
        self.assertRedirects(
            response,
            f'/reservas/confirmacion/{reserva.id}/',
            fetch_redirect_response=False,
        )
        self.tipo.refresh_from_db()
        self.assertEqual(self.tipo.cantidad_disponible, 8)

    def test_cancelar_reserva_post_restaura_disponibilidad(self):
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            self.client.login(username='viewer', password='pass')
            reserva = services.crear_reserva(self.usuario, self.evento.id, self.tipo.id, 4)

            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(f'/reservas/cancelar/{reserva.id}/')

        self.assertRedirects(response, '/reservas/mis-reservas/')
        reserva.refresh_from_db()
        self.tipo.refresh_from_db()
        self.assertEqual(reserva.estado, 'cancelada')
        self.assertEqual(self.tipo.cantidad_disponible, 10)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Pase Cancelado', mail.outbox[0].subject)

    def test_confirmacion_reserva_renderiza(self):
        self.client.login(username='viewer', password='pass')
        reserva = services.crear_reserva(self.usuario, self.evento.id, self.tipo.id, 1)

        response = self.client.get(f'/reservas/confirmacion/{reserva.id}/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.evento.nombre)

    def test_mis_reservas_oculta_canceladas(self):
        self.client.login(username='viewer', password='pass')
        activa = services.crear_reserva(self.usuario, self.evento.id, self.tipo.id, 1)
        cancelada = services.crear_reserva(self.usuario, self.evento.id, self.tipo.id, 1)
        services.cancelar_reserva(cancelada.id, self.usuario)

        response = self.client.get('/reservas/mis-reservas/')

        self.assertEqual(list(response.context['reservas']), [activa])
        self.assertNotIn(cancelada, response.context['reservas'])

    def test_descargar_reserva_ticket_pendiente_redirige(self):
        self.client.login(username='viewer', password='pass')
        reserva = services.crear_reserva(self.usuario, self.evento.id, self.tipo.id, 1)

        response = self.client.get(f'/reservas/descargar/{reserva.id}/')

        self.assertRedirects(response, '/reservas/mis-reservas/')

    def test_descargar_reserva_ticket_confirmada_devuelve_pdf(self):
        self.client.login(username='viewer', password='pass')
        reserva = services.crear_reserva(self.usuario, self.evento.id, self.tipo.id, 1)
        services.confirmar_reserva(reserva)

        response = self.client.get(f'/reservas/descargar/{reserva.id}/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')


class ReservaConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.usuario1 = User.objects.create_user('thread1', password='pass')
        self.usuario2 = User.objects.create_user('thread2', password='pass')
        self.evento = _make_base_data()
        self.tipo = TipoTicket.objects.create(
            evento=self.evento, nombre='Unico', precio=70000, cantidad_disponible=1
        )

    @unittest.skipIf(connection.vendor == 'sqlite', 'select_for_update requiere PostgreSQL')
    def test_reservas_concurrentes_no_sobrevenden(self):
        barrier = threading.Barrier(3)
        results = []

        def intentar_reserva(user_id):
            close_old_connections()
            barrier.wait()
            try:
                usuario = User.objects.get(pk=user_id)
                reserva = services.crear_reserva(usuario, self.evento.id, self.tipo.id, 1)
                results.append(('ok', reserva.id))
            except Exception as exc:
                results.append(('error', type(exc).__name__))
            finally:
                close_old_connections()

        threads = [
            threading.Thread(target=intentar_reserva, args=(self.usuario1.id,)),
            threading.Thread(target=intentar_reserva, args=(self.usuario2.id,)),
        ]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join()

        self.tipo.refresh_from_db()
        self.assertEqual(self.tipo.cantidad_disponible, 0)
        self.assertEqual(Reserva.objects.count(), 1)
        self.assertEqual(sum(1 for status, _ in results if status == 'ok'), 1)
        self.assertEqual(sum(1 for status, _ in results if status == 'error'), 1)
