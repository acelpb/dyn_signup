# Generated by Django 4.1.7 on 2023-03-06 22:15

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0013_justification_title"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExpenseFile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("file", models.FileField(blank=True, null=True, upload_to="")),
            ],
        ),
    ]
