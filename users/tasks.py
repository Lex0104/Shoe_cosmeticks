from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone

from config import settings
from restaurant.models import Reservation


@shared_task
def send_mail_reservation_reminder():
    today = timezone.localdate()
    reservations = Reservation.objects.filter(date=today, is_active=True, reminder_sent=False)

    for reservation in reservations:
        subject = "У ВАС ЗАРЕЗЕРВИРОВАН СТОЛИК!!!"
        message = (
            f"Здравствуйте, {reservation.owner.get_full_name()}!\n\n"
            f"У вас зарезервирован столик №{reservation.table.number}.\n"
            f"Дата бронирования: {reservation.date}.\n"
            f"Время бронирования: {reservation.time}.\n\n"
            "Спасибо, что выбрали нас!"
        )

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [reservation.owner.email],
            fail_silently=False,
        )

        reservation.reminder_sent = True
        reservation.save(update_fields=["reminder_sent"])
        print(f"Reminder sent flag updated for reservation {reservation.pk}")