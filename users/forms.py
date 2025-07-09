from django.contrib.auth.forms import UserCreationForm
from django.forms import ModelForm

from users.models import User


class UserRegisterForm(UserCreationForm):
    usable_password = None

    class Meta:
        model = User
        fields = ("email", "phone_number", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["email"].widget.attrs.update({"placeholder": "Укажите ваш email", "class": "form-control"})

        self.fields["phone_number"].widget.attrs.update(
            {"placeholder": "Укажите номер телефона", "class": "form-control"}
        )

        self.fields["password1"].widget.attrs.update({"placeholder": "Создайте пароль", "class": "form-control"})

        self.fields["password2"].widget.attrs.update({"placeholder": "Повторите пароль", "class": "form-control"})


class UserForm(ModelForm):

    class Meta:
        model = User
        fields = ("email", "phone_number", "first_name", "last_name")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["email"].widget.attrs.update({"readonly class": "form-control-plaintext text-white"})

        self.fields["phone_number"].widget.attrs.update(
            {"placeholder": "Введите номер телефона", "class": "form-control"}
        )

        self.fields["first_name"].widget.attrs.update({"placeholder": "Введите имя", "class": "form-control"})

        self.fields["last_name"].widget.attrs.update({"placeholder": "Укажите фамилию", "class": "form-control"})

        self.fields["first_name"].label = "Имя"
        self.fields["last_name"].label = "Фамилия"