# Autor: Thomas Osorio

from django.db.models import Q
from django.views.generic import ListView, DetailView

from .models import CategoriaEvento, Evento


class EventoListView(ListView):
    model = Evento
    template_name = 'eventos/catalogo_eventos.html'
    context_object_name = 'eventos'
    ordering = ['fecha']
    paginate_by = 10

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related('categoria', 'lugar')
        )

        categoria_id = self.request.GET.get('categoria')
        if categoria_id:
            qs = qs.filter(categoria_id=categoria_id)

        fecha_inicio = self.request.GET.get('fecha_inicio')
        if fecha_inicio:
            qs = qs.filter(fecha__gte=fecha_inicio)

        fecha_fin = self.request.GET.get('fecha_fin')
        if fecha_fin:
            qs = qs.filter(fecha__lte=fecha_fin)

        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(Q(nombre__icontains=q))

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = CategoriaEvento.objects.all()

        # Para que la paginación conserve los filtros actuales.
        query_params = self.request.GET.copy()
        query_params.pop('page', None)
        context['pagination_query'] = query_params.urlencode()

        return context


class HomeView(EventoListView):
    """
    Mantiene el nombre `home` por compatibilidad con la navbar.
    """
    template_name = 'eventos/home.html'
    paginate_by = 6


class EventoDetailView(DetailView):
    model = Evento
    template_name = 'eventos/detalle_evento.html'
    context_object_name = 'evento'
