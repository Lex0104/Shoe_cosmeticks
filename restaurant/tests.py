from datetime import date, time, timedelta
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date

from restaurant.forms import ReservationAdminForm
from restaurant.models import Reservation, Table, Worker
from restaurant.views import ReservationListView, ReservationUpdateView
from users.models import User


class HomeViewTests(TestCase):
    def test_get_request_home(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["message_sent"])
        self.assertTemplateUsed(response, "restaurant/home.html")

    @patch("restaurant.views.send_mail_feedback.delay")
    def test_post_request_sends_mail(self, mock_send_mail):
        data = {"email": "test@example.com", "message": "Hello"}
        response = self.client.post("/", data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["message_sent"])
        mock_send_mail.assert_called_once_with("test@example.com", "Hello")


class HistoryViewTest(TestCase):
    def test_get_request_history(self):
        response = self.client.get("/history/")
        cache.clear()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<h1 class="display-6">История ресторана</h1>')


class ReservationViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("restaurant:reservation")
        self.user = User.objects.create(email="test@mail.example", password="testpass")
        self.table1 = Table.objects.create(number=1, number_of_seats=2)
        self.table2 = Table.objects.create(number=2, number_of_seats=3)

    def test_get_without_table_id(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertIn("tables", response.context)
        self.assertFalse(response.context["form"].initial)
        tables = response.context["tables"]
        self.assertIn(self.table1, tables)
        self.assertIn(self.table2, tables)
        self.assertTemplateUsed(response, "restaurant/reservation.html")

    def test_get_with_table_id(self):
        response = self.client.get(self.url, {"table_id": self.table1.id})
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertEqual(form.initial.get("table"), str(self.table1.id) or self.table1.id)
        self.assertTemplateUsed(response, "restaurant/reservation.html")

    def test_post_unauthenticated_redirects_to_login(self):
        data = {
            "table": self.table1.id,
            "date": "2025-07-01",
            "time": "18:00",
            "number_of_seats": 2,
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("users:login"), response.url)

    @patch("restaurant.views.send_reservation_notification")
    def test_post_valid_authenticated_creates_reservation(self, mock_send_notification):
        self.client.force_login(self.user)
        data = {
            "table": self.table1.id,
            "date": "2025-07-01",
            "time": "18:00",
            "guests": 2,
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse("restaurant:reservation_success"))
        reservation = Reservation.objects.filter(owner=self.user, table=self.table1, date="2025-07-01").first()
        self.assertIsNotNone(reservation)
        mock_send_notification.assert_called_once()
        args, kwargs = mock_send_notification.call_args
        self.assertEqual(kwargs.get("action"), "created")
        self.assertEqual(kwargs.get("user"), self.user)

    def test_post_invalid_data_rerenders_form_with_errors(self):
        self.client.force_login(self.user)
        data = {
            "table": "",
            "date": "invalid-date",
            "time": "25:00",
            "number_of_seats": -1,
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertTrue(form.errors)
        self.assertTemplateUsed(response, "restaurant/reservation.html")


class TableDetailViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.table = Table.objects.create(number=1, number_of_seats=4)
        self.url = reverse("restaurant:table_detail", kwargs={"pk": self.table.pk})
        self.user = User.objects.create(email="test@mail.example", password="testpass")

        today = timezone.localdate()
        Reservation.objects.create(
            table=self.table,
            date=today,
            time=time(12, 0),
            owner=self.user,
        )

    def test_get_request_table_detail(self):
        cache.clear()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<p>Изображение отсутствует</p>")

    def test_free_slots_in_context(self):
        cache.clear()
        response = self.client.get(self.url)
        free_slots = response.context["free_slots"]

        self.assertIsInstance(free_slots, list)
        self.assertTrue(all("date" in slot and "time" in slot for slot in free_slots))

        today_str = timezone.localdate().strftime("%Y-%m-%d")
        for slot in free_slots:
            if slot["date"] == timezone.localdate():
                self.assertNotEqual(slot["time"], "12:00")


class ReservationListViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("restaurant:reservation_list")  # замените на ваш URL name

        # Создаём группу "Manager"
        self.manager_group = Group.objects.create(name="Manager")

        # Создаём пользователя менеджера и добавляем в группу
        self.manager_user = User.objects.create(email="manager@example.com", password="pass1234")
        self.manager_user.groups.add(self.manager_group)

        # Создаём обычного пользователя
        self.normal_user = User.objects.create(email="user@example.com", password="pass1234")

        self.table1 = Table.objects.create(number=1, number_of_seats=4)
        self.table2 = Table.objects.create(number=2, number_of_seats=6)

        today = date.today()
        self.res1 = Reservation.objects.create(
            owner=self.manager_user, table=self.table1, date=today, time=time(18, 0), is_active=True
        )
        self.res2 = Reservation.objects.create(
            owner=self.manager_user,
            table=self.table2,
            date=today + timedelta(days=1),
            time=time(19, 0),
            is_active=True,
        )
        self.res3 = Reservation.objects.create(
            owner=self.manager_user,
            table=self.table1,
            date=today + timedelta(days=2),
            time=time(20, 0),
            is_active=False,  # неактивная бронь
        )

    def test_permission_denied_in_get_queryset(self):
        factory = RequestFactory()
        request = factory.get(self.url)
        request.user = self.normal_user

        view = ReservationListView()
        view.request = request

        with self.assertRaises(PermissionDenied):
            view.get_queryset()

    def test_access_allowed_for_manager(self):
        self.client.force_login(self.manager_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Список активных резервов")

    def test_filter_by_date(self):
        self.client.force_login(self.manager_user)
        date_str = (date.today() + timedelta(days=1)).isoformat()
        response = self.client.get(self.url, {"date": date_str})
        self.assertEqual(response.status_code, 200)
        reservations = response.context["reservation_list"]
        self.assertTrue(all(res.date == parse_date(date_str) for res in reservations))
        # Проверяем, что не попадает неактивная бронь
        self.assertTrue(all(res.is_active for res in reservations))

    def test_filter_by_table_number(self):
        self.client.force_login(self.manager_user)
        response = self.client.get(self.url, {"table_number": "1"})
        self.assertEqual(response.status_code, 200)
        reservations = response.context["reservation_list"]
        self.assertTrue(all(res.table.number == 1 for res in reservations))
        self.assertTrue(all(res.is_active for res in reservations))


class ReservationUpdateViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.manager_group = Group.objects.create(name="Manager")

        self.owner_user = User.objects.create(email="owner@example.com", password="pass1234")
        self.manager_user = User.objects.create(email="manager@example.com", password="pass1234")
        self.manager_user.groups.add(self.manager_group)
        self.other_user = User.objects.create(email="other@example.com", password="pass1234")

        self.table = Table.objects.create(number=1, number_of_seats=4)
        self.reservation = Reservation.objects.create(
            owner=self.owner_user, table=self.table, date="2025-07-01", time="18:00", is_active=True
        )
        self.url = reverse("restaurant:reservation_update", kwargs={"pk": self.reservation.pk})

    def test_owner_can_access_update(self):
        self.client.force_login(self.owner_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurant/reservation_update.html")

    def test_manager_can_access_update(self):
        self.client.force_login(self.manager_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurant/reservation_update.html")

    def test_other_user_cannot_access_update(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)  # PermissionDenied приводит к 403

    def test_get_form_class_owner(self):
        self.client.force_login(self.owner_user)
        view = ReservationUpdateView()
        view.request = self.client.request().wsgi_request
        view.object = self.reservation
        view.request.user = self.owner_user
        form_class = view.get_form_class()
        self.assertEqual(form_class, ReservationAdminForm)

    def test_get_form_class_manager(self):
        self.client.force_login(self.manager_user)
        view = ReservationUpdateView()
        view.request = self.client.request().wsgi_request
        view.object = self.reservation
        view.request.user = self.manager_user
        form_class = view.get_form_class()
        self.assertEqual(form_class, ReservationAdminForm)

    def test_get_form_class_other_user_raises_permission_denied(self):
        self.client.force_login(self.other_user)
        view = ReservationUpdateView()
        view.request = self.client.request().wsgi_request
        view.object = self.reservation
        view.request.user = self.other_user
        with self.assertRaises(PermissionDenied):
            view.get_form_class()

    @patch("restaurant.views.send_reservation_notification")
    def test_post_valid_update_calls_notification_and_redirects(self, mock_send_notification):
        self.client.force_login(self.owner_user)
        data = {
            "table": self.table.pk,
            "date": "2025-07-02",
            "time": "19:00:00",
            "is_active": True,
        }
        response = self.client.post(self.url, data)
        expected_url = reverse("users:user_detail", args=[self.owner_user.pk])
        self.assertRedirects(response, expected_url)

        self.reservation.refresh_from_db()
        self.assertEqual(str(self.reservation.date), "2025-07-02")
        self.assertEqual(str(self.reservation.time), "19:00:00")

        mock_send_notification.assert_called_once_with(
            reservation=self.reservation, action="updated", user=self.owner_user, request=response.wsgi_request
        )


class ReservationDeleteViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.manager_group = Group.objects.create(name="Manager")

        self.owner_user = User.objects.create(email="owner@example.com", password="pass1234")
        self.manager_user = User.objects.create(email="manager@example.com", password="pass1234")
        self.manager_user.groups.add(self.manager_group)
        self.other_user = User.objects.create(email="other@example.com", password="pass1234")

        self.table = Table.objects.create(number=1, number_of_seats=4)
        self.reservation = Reservation.objects.create(
            owner=self.owner_user, table=self.table, date="2025-07-01", time="18:00", is_active=True
        )
        self.url = reverse("restaurant:reservation_delete", kwargs={"pk": self.reservation.pk})

    def test_owner_can_access_delete(self):
        self.client.force_login(self.owner_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurant/confirm_delete.html")

    def test_manager_can_access_delete(self):
        self.client.force_login(self.manager_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurant/confirm_delete.html")

    def test_other_user_cannot_access_delete(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)  # PermissionDenied приводит к 403

    @patch("restaurant.views.send_reservation_notification")
    def test_post_delete_calls_notification_and_redirects(self, mock_send_notification):
        self.client.force_login(self.owner_user)
        response = self.client.post(self.url)
        # Проверяем редирект после удаления
        self.assertRedirects(response, reverse("restaurant:home"))
        # Проверяем, что бронь удалена из базы
        exists = Reservation.objects.filter(pk=self.reservation.pk).exists()
        self.assertFalse(exists)
        # Проверяем вызов уведомления
        mock_send_notification.assert_called_once()
        args, kwargs = mock_send_notification.call_args
        self.assertEqual(kwargs.get("reservation"), self.reservation)
        self.assertEqual(kwargs.get("action"), "deleted")
        self.assertEqual(kwargs.get("user"), self.owner_user)

    def test_post_delete_permission_denied_for_other_user(self):
        self.client.force_login(self.other_user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)
        # Бронь должна остаться
        exists = Reservation.objects.filter(pk=self.reservation.pk).exists()
        self.assertTrue(exists)


class WorkerListViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("restaurant:about")  # замените на ваш URL name

        # Создадим работников с разными позициями
        # Предполагается, что у Worker есть поле position и константы
        self.worker_owner = Worker.objects.create(first_name="Owner", last_name="owner", position=Worker.owner)
        self.worker_manager = Worker.objects.create(first_name="Manager", last_name="manager", position=Worker.manager)
        self.worker_chef = Worker.objects.create(first_name="Chef", last_name="chef", position=Worker.the_chef)
        self.worker_sous_chef = Worker.objects.create(
            first_name="Sous Chef", last_name="little chef", position=Worker.sous_chef
        )
        self.worker_hostess = Worker.objects.create(
            first_name="Hostess", last_name="hostess", position=Worker.hostesses
        )
        self.worker_waiter = Worker.objects.create(first_name="Waiter", last_name="waiter", position=Worker.waiter)
        self.worker_bartender = Worker.objects.create(
            first_name="Bartender", last_name="bartender", position=Worker.bartender
        )

    def test_get_status_and_template(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Наша миссия и наши ценности")

    def test_context_lists_correctness_and_sorting(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        administrative = response.context["administrative"]
        kitchen = response.context["kitchen"]
        hall = response.context["hall"]

        # Проверяем, что в списках правильные объекты
        self.assertIn(self.worker_owner, administrative)
        self.assertIn(self.worker_manager, administrative)

        self.assertIn(self.worker_chef, kitchen)
        self.assertIn(self.worker_sous_chef, kitchen)

        self.assertIn(self.worker_hostess, hall)
        self.assertIn(self.worker_waiter, hall)
        self.assertIn(self.worker_bartender, hall)

        # Проверка сортировки administrative по position (возрастающая)
        administrative_positions = [w.position for w in administrative]
        self.assertEqual(administrative_positions, sorted(administrative_positions))

        # Проверка сортировки kitchen с учётом приоритета the_chef и sous_chef
        self.assertEqual(kitchen[0], self.worker_chef)
        self.assertEqual(kitchen[1], self.worker_sous_chef)

        # Проверка сортировки hall с приоритетом hostesses
        self.assertEqual(hall[0], self.worker_hostess)
