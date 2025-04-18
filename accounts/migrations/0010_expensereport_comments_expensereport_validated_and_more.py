# Generated by Django 4.1.7 on 2023-02-21 19:54

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0009_expensereport_signed_expensereport_submitted_date"),
    ]

    operations = [
        migrations.AddField(
            model_name="expensereport",
            name="comments",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="expensereport",
            name="validated",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="expensereport",
            name="beneficiary",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
