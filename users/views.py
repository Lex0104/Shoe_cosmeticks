from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, UpdateView

from restaurant.models import Reservation
from users.forms import UserForm, UserRegisterForm
from users.models import User


class UserCreateView(CreateView):
    model = User
    template_name = "users/register.html"
    form_class = UserRegisterForm
    success_url = reverse_lazy("restaurant:home")


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    template_name = "users/user_detail.html"
    paginate_by = 5

    def get_object(self, queryset=None):
        if self.request.user.pk == self.kwargs.get("pk"):
            return get_object_or_404(User, pk=self.kwargs.get("pk"))
        else:
            raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()

        user_reservations = Reservation.objects.filter(owner=user).order_by("date", "time")

        paginator = Paginator(user_reservations, self.paginate_by)
        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context["page_obj"] = page_obj
        return context


class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    template_name = "users/user_form.html"
    form_class = UserForm

    def get_success_url(self):
        return reverse("users:user_detail", args=[self.kwargs.get("pk")])

    def get_form_class(self):
        user = self.request.user
        if user == self.object:
            return UserForm
        raise PermissionDenied