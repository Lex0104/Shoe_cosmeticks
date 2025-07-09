from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelForm

from restaurant.models import Reservation, Table


class ReservationForm(ModelForm):
    table = forms.ModelChoiceField(
        queryset=Table.objects.all(),
        empty_label="Выберите столик",
        widget=forms.Select(attrs={"class": "form-control"}),
        label="Выберите столик",
    )

    class Meta:
        model = Reservation
        exclude = ("owner", "is_active", "reminder_sent")

        widgets = {
            "date": forms.TextInput(attrs={"class": "form-control flatpickr-date", "placeholder": "Выберите дату"}),
            "time": forms.TextInput(
                attrs={"class": "form-control flatpickr-time h-100", "placeholder": "Выберите время"}
            ),
            "comment": forms.Textarea(attrs={"class": "form-control", "rows": 5, "placeholder": "Комментарий"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        choices = []
        for table in self.fields["table"].queryset:
            label = f"{table.number}"
            choices.append((table.pk, label))

        self.fields["table"].choices = choices

        self.fields["date"].label = "Дата бронирования"
        self.fields["time"].label = "Время бронирования"

    def clean(self):
        cleaned_data = super().clean()
        table = cleaned_data.get("table")
        date = cleaned_data.get("date")
        time = cleaned_data.get("time")

        if table and date and time:
            conflict = Reservation.objects.filter(table=table, date=date, time=time, is_active=True)

            if self.instance.pk:
                conflict = conflict.exclude(pk=self.instance.pk)

            if conflict.exists():
                raise ValidationError(f"Столик {table.number} уже забронирован на выбранное время и дату.")

        return cleaned_data


class ReservationAdminForm(ModelForm):
    table = forms.ModelChoiceField(
        queryset=Table.objects.all(),
        empty_label="Выберите столик",
        widget=forms.Select(attrs={"class": "form-control"}),
        label="Выберите столик",
    )

    class Meta:
        model = Reservation
        exclude = ("is_active", "reminder_sent", "owner")

        widgets = {
            "date": forms.TextInput(attrs={"class": "form-control flatpickr-date", "placeholder": "Выберите дату"}),
            "time": forms.TextInput(
                attrs={"class": "form-control flatpickr-time h-100", "placeholder": "Выберите время"}
            ),
            "comment": forms.Textarea(attrs={"class": "form-control", "rows": 5, "placeholder": "Комментарий"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        choices = []
        for table in self.fields["table"].queryset:
            label = f"{table.number}"
            choices.append((table.pk, label))

        self.fields["table"].choices = choices

        self.fields["date"].label = "Дата бронирования"
        self.fields["time"].label = "Время бронирования"