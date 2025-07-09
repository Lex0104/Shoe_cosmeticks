from .tasks import send_reservation_email
from .utils import build_reservation_mail


def send_reservation_notification(reservation, action, user=None, request=None):
    if user and user.id != reservation.owner_id:
        return

    subject, body = build_reservation_mail(reservation, action, request=request)
    if subject and body:
        send_reservation_email.delay(subject, body)