from datetime import timedelta

from django.urls import reverse


def generate_new_reservation_body(reservation, url, name):
    return (
        f"НОВЫЙ РЕЗЕРВ!\n\n"
        f"Дата: {reservation.date}\n"
        f"Время: {reservation.time}\n"
        f"Гость: {name} - {reservation.owner}\n"
        f"Столик №{reservation.table}\n"
        f"Комментарий: {reservation.comment}\n"
        f"Ссылка для подтверждения: {url}"
    )


def generate_updated_reservation_body(reservation, url, name):
    return (
        f"ИЗМЕНЕНИЕ РЕЗЕРВА!\n\n"
        f"Дата: {reservation.date}\n"
        f"Время: {reservation.time}\n"
        f"Гость: {name} - {reservation.owner}\n"
        f"Столик №{reservation.table}\n"
        f"Комментарий: {reservation.comment}\n"
        f"Ссылка для подтверждения: {url}"
    )


def generate_deleted_reservation_body(reservation, name):
    return (
        f"ОТМЕНА РЕЗЕРВА!\n\n"
        f"Дата: {reservation.date}\n"
        f"Время: {reservation.time}\n"
        f"Гость: {name} - {reservation.owner}\n"
        f"Столик №{reservation.table}\n"
        f"Комментарий: {reservation.comment}\n"
    )


def build_reservation_mail(reservation, action, request=None):
    relative_url = reverse("restaurant:reservation_update", args=[reservation.pk])
    url = request.build_absolute_uri(relative_url) if request else relative_url
    name = reservation.owner.get_full_name()

    if action == "created":
        subject = "НОВЫЙ РЕЗЕРВ!!!"
        body = generate_new_reservation_body(reservation, url, name)

    elif action == "updated":
        subject = "ИЗМЕНЕНИЕ РЕЗЕРВА!!!"
        body = generate_updated_reservation_body(reservation, url, name)

    elif action == "deleted":
        subject = "РЕЗЕРВ БЫЛ ОТМЕНЁН!!!"
        body = generate_deleted_reservation_body(reservation, name)

    else:
        subject = body = None

    return subject, body


def round_time_to_next_slot(dt):
    minute = dt.minute
    if minute == 0:
        return dt.replace(minute=30, second=0, microsecond=0)
    elif minute <= 30:
        return dt.replace(minute=30, second=0, microsecond=0)
    else:
        dt = dt.replace(minute=0, second=0, microsecond=0)
        return dt + timedelta(hours=1)