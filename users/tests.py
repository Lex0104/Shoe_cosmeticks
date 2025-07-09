from datetime import date, time, timedelta

from django.core.exceptions import PermissionDenied
from django.test import Client, TestCase
from django.urls import reverse

from restaurant.models import Reservation, Table
from users.models import User


class UserCreateViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("users:register")

    def test_get_request_returns_registration_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/register.html")
        self.assertIn("form", response.context)

    def test_post_valid_data_creates_user_and_redirects(self):
        data = {
            "email": "newuser@example.com",
            "password1": "StrongPassword123",
            "password2": "StrongPassword123",
        }
        response = self.client.post(self.url, data)
        # Проверяем редирект на success_url (домашнюю страницу ресторана)
        self.assertRedirects(response, reverse("restaurant:home"))

        # Проверяем, что пользователь создан
        user_exists = User.objects.filter(email="newuser@example.com").exists()
        self.assertTrue(user_exists)


class UserDetailViewTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.user = User.objects.create(email="user@example.com", password="pass1234")
        self.other_user = User.objects.create(email="other@example.com", password="pass1234")

        self.table = Table.objects.create(number=1, number_of_seats=4)

        today = date.today()
        for i in range(7):
            Reservation.objects.create(
                owner=self.user, table=self.table, date=today + timedelta(days=i), time=time(18, 0), is_active=True
            )

        self.url = reverse("users:user_detail", kwargs={"pk": self.user.pk})

    def test_owner_can_access_page(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/user_detail.html")

        # Проверяем, что в контексте есть пагинированный объект
        page_obj = response.context["page_obj"]
        self.assertTrue(page_obj)
        self.assertEqual(page_obj.paginator.per_page, 5)

        # Проверяем, что бронирования принадлежат пользователю
        for reservation in page_obj:
            self.assertEqual(reservation.owner, self.user)

    def test_other_user_cannot_access_page(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)


class UserUpdateViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(email="user@example.com", password="pass1234")
        self.other_user = User.objects.create(email="other@example.com", password="pass1234")
        self.url = reverse("users:user_update", kwargs={"pk": self.user.pk})

    def test_owner_can_access_update(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/user_form.html")
        self.assertIn("form", response.context)

    def test_other_user_cannot_access_update(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_post_valid_update_redirects(self):
        self.client.force_login(self.user)
        data = {"email": "user@example.com", "first_name": "Test"}
        response = self.client.post(self.url, data)
        expected_url = reverse("users:user_detail", args=[self.user.pk])
        self.assertRedirects(response, expected_url)

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Test")

    def test_get_form_class_owner(self):
        from users.views import UserUpdateView

        view = UserUpdateView()
        view.request = self.client.request().wsgi_request
        view.object = self.user
        view.request.user = self.user
        form_class = view.get_form_class()
        from users.forms import UserForm

        self.assertEqual(form_class, UserForm)

    def test_get_form_class_other_user_raises_permission_denied(self):
        from users.views import UserUpdateView

        view = UserUpdateView()
        view.request = self.client.request().wsgi_request
        view.object = self.user
        view.request.user = self.other_user
        with self.assertRaises(PermissionDenied):
            view.get_form_class()