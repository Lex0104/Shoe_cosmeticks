from django.contrib import admin
from image_cropping import ImageCroppingMixin

from restaurant.models import Reservation, Table, Worker


@admin.register(Table)
class TableAdmin(ImageCroppingMixin, admin.ModelAdmin):
    list_display = ("id", "number", "number_of_seats")
    list_filter = ("number_of_seats",)
    search_fields = ("number_of_seats",)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "table", "date", "time")
    list_filter = ("owner", "date")
    search_fields = ("comment", "owner")


@admin.register(Worker)
class WorkerAdmin(ImageCroppingMixin, admin.ModelAdmin):
    list_display = ("id", "first_name", "last_name", "position")
    list_filter = ("position",)
    search_fields = ("first_name", "last_name", "position")
