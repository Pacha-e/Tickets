from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.views.defaults import page_not_found, server_error

from config.sitemaps import EventoSitemap
from config.views import health

handler404 = page_not_found
handler500 = server_error

_sitemaps = {'eventos': EventoSitemap}


def robots_txt(request):
    lines = [
        'User-agent: *',
        'Allow: /',
        f'Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml',
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain')


urlpatterns = [
    path('robots.txt', robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap, {'sitemaps': _sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/', admin.site.urls),
    path('health', health, name='health'),

    path('accounts/login/', auth_views.LoginView.as_view(
        template_name='auth/login.html'
    ), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('', include('apps.usuarios.urls')),
    path('', include('apps.eventos.urls')),
    path('reservas/', include('apps.reservas.urls')),
    path('pagos/', include('apps.pagos.urls')),
]

# Servir archivos de media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
