from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from .models import Perfil


class RegistroTests(TestCase):
    def test_registro_get_muestra_formulario(self):
        response = self.client.get(reverse('registro'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="username"')

    def test_registro_post_crea_usuario_perfil_y_login(self):
        response = self.client.post(
            reverse('registro'),
            {
                'username': 'nuevo',
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            },
        )

        user = User.objects.get(username='nuevo')
        self.assertRedirects(response, reverse('home'))
        self.assertTrue(Perfil.objects.filter(user=user).exists())

    def test_registro_usuario_autenticado_redirige_home(self):
        User.objects.create_user('existente', password='pass')
        self.client.login(username='existente', password='pass')

        response = self.client.get(reverse('registro'))

        self.assertRedirects(response, reverse('home'))
