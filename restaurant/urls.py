from django.urls import path

from . import views
from .apps import RestaurantConfig
from .views import (
    ReservationDeleteView,
    ReservationListView,
    ReservationUpdateView,
    ReservationView,
    TableDetailView,
    WorkerListView,
)

app_name = RestaurantConfig.name

urlpatterns = [
    path("", views.home, name="home"),
    path("history/", views.history, name="history"),
    path("about/", WorkerListView.as_view(), name="about"),
    path("table/<int:pk>/", TableDetailView.as_view(), name="table_detail"),
    path("reservation/", ReservationView.as_view(), name="reservation"),
    path("reservation/list/", ReservationListView.as_view(), name="reservation_list"),
    path("reservation/success/", views.reservation_success, name="reservation_success"),
    path("reservation/<int:pk>/update/", ReservationUpdateView.as_view(), name="reservation_update"),
    path("reservation/<int:pk>/delete/", ReservationDeleteView.as_view(), name="reservation_delete"),
]