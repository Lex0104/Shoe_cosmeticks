from datetime import datetime, time, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import cache_page
from django.views.generic import DeleteView, DetailView, ListView, UpdateView

from restaurant.forms import ReservationAdminForm, ReservationForm
from restaurant.models import Reservation, Table, Worker
from restaurant.services import send_reservation_notification

from .tasks import send_mail_feedback
from .utils import round_time_to_next_slot


def home(request):
    message_sent = False
    if request.method == "POST":
        email = request.POST.get("email")
        message = request.POST.get("message")

        send_mail_feedback.delay(email, message)

        message_sent = True

    return render(request, "restaurant/home.html", {"message_sent": message_sent})


@cache_page(60 * 30)
def history(request):
    return render(request, "restaurant/history.html")


@cache_page(60 * 10)
def reservation_success(request):
    return render(request, "restaurant/reservation_success.html")


class ReservationView(View):
    template_name = "restaurant/reservation.html"

    def get(self, request):
        tables = Table.objects.order_by("number")
        table_id = request.GET.get("table_id")
        if table_id:
            form = ReservationForm(initial={"table": table_id})
        else:
            form = ReservationForm()
        return render(request, self.template_name, {"tables": tables, "form": form})

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect("users:login")

        tables = Table.objects.all().order_by("number")
        form = ReservationForm(request.POST)
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.owner = request.user
            reservation.save()
            send_reservation_notification(reservation, action="created", user=request.user, request=request)
            return redirect("restaurant:reservation_success")
        return render(request, self.template_name, {"tables": tables, "form": form})


@method_decorator(cache_page(60 * 5), name="dispatch")
class TableDetailView(DetailView):
    model = Table
    template_name = "restaurant/table_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        table = self.object

        now = timezone.localtime()
        days_ahead = 7
        slot_duration = timedelta(minutes=30)

        free_slots = []

        start_dt = round_time_to_next_slot(now)

        for day_offset in range(days_ahead):
            current_date = (now + timedelta(days=day_offset)).date()

            reserved_times = Reservation.objects.filter(table=table, date=current_date, is_active=True).values_list(
                "time", flat=True
            )

            if day_offset == 0:
                current_time = start_dt.time()
            else:
                current_time = time(0, 0)

            slot_dt = datetime.combine(current_date, current_time)
            end_dt = datetime.combine(current_date, time(23, 30))

            while slot_dt <= end_dt:
                slot_time = slot_dt.time()
                if slot_time not in reserved_times:
                    free_slots.append({"date": current_date, "time": slot_time.strftime("%H:%M")})
                slot_dt += slot_duration

        context["free_slots"] = free_slots
        return context


@method_decorator(cache_page(60 * 5), name="dispatch")
class ReservationListView(LoginRequiredMixin, ListView):
    model = Reservation
    template_name = "restaurant/reservation_list.html"
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        if not user.groups.filter(name="Manager").exists():
            raise PermissionDenied

        queryset = Reservation.objects.filter(is_active=True)

        date_str = self.request.GET.get("date")
        if date_str:
            date_obj = parse_date(date_str)
            if date_obj:
                queryset = queryset.filter(date=date_obj)

        table_number = self.request.GET.get("table_number")
        if table_number and table_number.isdigit():
            queryset = queryset.filter(table__number=int(table_number))

        queryset = queryset.order_by("date", "time", "table__number")

        return queryset


class ReservationUpdateView(LoginRequiredMixin, UpdateView):
    model = Reservation
    template_name = "restaurant/reservation_update.html"
    form_class = ReservationAdminForm
    success_url = reverse_lazy("restaurant:home")

    def get_success_url(self):
        if self.request.user == self.object.owner:
            return reverse("users:user_detail", args=[self.request.user.pk])
        return reverse("restaurant:home")

    def form_valid(self, form):
        response = super().form_valid(form)
        send_reservation_notification(
            reservation=self.object, action="updated", user=self.request.user, request=self.request
        )
        return response

    def get_form_class(self):
        user = self.request.user
        if user == self.object.owner or user.groups.filter(name="Manager").exists():
            return ReservationAdminForm
        raise PermissionDenied


class ReservationDeleteView(LoginRequiredMixin, DeleteView):
    template_name = "restaurant/confirm_delete.html"
    model = Reservation
    success_url = reverse_lazy("restaurant:home")

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        if obj.owner == user or user.groups.filter(name="Manager").exists():
            return obj
        raise PermissionDenied

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        reservation = self.object
        user = request.user

        response = super().post(request, *args, **kwargs)

        send_reservation_notification(
            reservation=reservation,
            action="deleted",
            user=user,
        )
        return response


@method_decorator(cache_page(60 * 15), name="dispatch")
class WorkerListView(ListView):
    template_name = "restaurant/about.html"
    model = Worker

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        workers = Worker.objects.all()

        administrative_position = [Worker.owner, Worker.manager]
        context["administrative"] = [worker for worker in workers if worker.position in administrative_position]

        kitchen_position = [Worker.the_chef, Worker.sous_chef, Worker.chef]
        context["kitchen"] = [worker for worker in workers if worker.position in kitchen_position]

        hall_position = [Worker.hostesses, Worker.waiter, Worker.bartender]
        context["hall"] = [worker for worker in workers if worker.position in hall_position]

        context["administrative"] = sorted(context["administrative"], key=lambda w: w.position)
        context["kitchen"] = sorted(
            context["kitchen"], key=lambda w: (w.position != Worker.the_chef, w.position != Worker.sous_chef)
        )
        context["hall"] = sorted(context["hall"], key=lambda w: (w.position != Worker.hostesses, w.position))

        return context