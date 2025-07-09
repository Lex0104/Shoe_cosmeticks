from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand

from restaurant.models import Reservation


class Command(BaseCommand):
    help = "Создаёт группу Manager с правом изменения брони"

    def handle(self, *args, **options):
        group_name = "Manager"
        content_type = ContentType.objects.get_for_model(Reservation)
        can_change_reservation = Permission.objects.get(codename="change_reservation", content_type=content_type)

        group, created = Group.objects.get_or_create(name=group_name)
        if created:
            self.stdout.write(self.style.SUCCESS(f'Группа "{group_name}" создана.'))
        else:
            self.stdout.write(self.style.WARNING(f'Группа "{group_name}" уже существует.'))

        group.permissions.add(
            can_change_reservation,
        )

        group.save()