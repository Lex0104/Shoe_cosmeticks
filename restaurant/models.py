from django.db import models
from image_cropping import ImageCropField, ImageRatioField

from users.models import User


class Table(models.Model):
    image = ImageCropField(upload_to="restaurant/images", verbose_name="Изображение столика", blank=True, null=True)
    cropping = ImageRatioField("image", free_crop=True)
    number = models.PositiveIntegerField(verbose_name="Номер столика", null=True)
    number_of_seats = models.PositiveSmallIntegerField(verbose_name="Количество мест")

    def __str__(self):
        return f"{self.number}"

    class Meta:
        verbose_name = "Столик"
        verbose_name_plural = "Столики"
        ordering = ["number"]


class Reservation(models.Model):
    date = models.DateField(verbose_name="Дата, на которую забронирован столик")
    time = models.TimeField(verbose_name="Время, на которое забронирован столик")
    owner = models.ForeignKey(
        User, on_delete=models.SET_NULL, verbose_name="Гость", blank=True, null=True, related_name="reservation"
    )
    table = models.ForeignKey(Table, on_delete=models.SET_NULL, verbose_name="Забронированный столик", null=True)
    comment = models.TextField(verbose_name="Комментарий к бронированию", blank=True, null=True)
    is_active = models.BooleanField(verbose_name="Бронь активна", default=True)
    reminder_sent = models.BooleanField(verbose_name="Напоминание отправлено", default=False)

    def __str__(self):
        return f"{self.date} - {self.time}. {self.table}"

    class Meta:
        verbose_name = "Бронь"
        verbose_name_plural = "Брони"
        ordering = ["date"]


class Worker(models.Model):
    owner = "Владелец"
    manager = "Управляющий"
    the_chef = "Шев-повар"
    sous_chef = "Су-шеф"
    chef = "Повар"
    hostesses = "Администратор зала"
    waiter = "Официант"
    bartender = "Бармен"

    JOB_TITLE = [
        (owner, "Владелец"),
        (manager, "Управляющий"),
        (the_chef, "Шев-повар"),
        (sous_chef, "Су-шев"),
        (chef, "Повар"),
        (hostesses, "Администратор зала"),
        (waiter, "Официант"),
        (bartender, "Бармен"),
    ]

    first_name = models.CharField(max_length=30, verbose_name="Имя сотрудника")
    last_name = models.CharField(max_length=50, verbose_name="Фамилия сотрудника")
    position = models.CharField(max_length=20, choices=JOB_TITLE, verbose_name="Должность")
    avatar = ImageCropField(
        upload_to="restaurant/workers/images", verbose_name="Фото сотрудника", blank=True, null=True
    )
    cropping = ImageRatioField("avatar", free_crop=True)
    description = models.TextField(verbose_name="Описание сотрудника", blank=True, null=True)

    def __str__(self):
        return f"{self.position}"

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"
        ordering = ["id"]