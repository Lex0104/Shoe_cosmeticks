from datetime import datetime, timedelta

from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone

from config import settings
from restaurant.models import Reservation


@shared_task
def send_mail_feedback(email, message):
    subject = "Обратная связь с сайта"
    body = f"От: {email}\n\nСообщение:\n{message}"
    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [settings.FEEDBACK_EMAIL],
        fail_silently=False,
    )


@shared_task
def send_reservation_email(subject, body):
    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [settings.EMAIL_ADMIN],
        fail_silently=False,
    )


@shared_task
def check_reservation():
    today = timezone.localdate()
    now = timezone.now()
    reservations = Reservation.objects.filter(date=today, is_active=True)
    for reservation in reservations:
        reservation_datetime = datetime.combine(today, reservation.time)

        if timezone.is_aware(now):
            from django.utils.timezone import make_aware

            reservation_datetime = make_aware(reservation_datetime, timezone.get_current_timezone())

        if now - reservation_datetime > timedelta(minutes=30):
            reservation.is_active = False
            reservation.save()