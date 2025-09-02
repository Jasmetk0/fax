from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView

from .forms import TournamentForm
from .models import Tournament


class TournamentListView(ListView):
    model = Tournament
    template_name = "msa/tournament_list.html"


class TournamentDetailView(DetailView):
    model = Tournament
    slug_field = "slug"
    template_name = "msa/tournament_detail.html"


class TournamentCreateView(CreateView):
    model = Tournament
    form_class = TournamentForm
    template_name = "msa/tournament_form.html"

    def get_success_url(self):
        return reverse("msa:tournament_detail", kwargs={"slug": self.object.slug})
