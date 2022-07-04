# Generated by Django 4.0.3 on 2022-06-25 13:04

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=55)),
                ('IBAN', models.CharField(max_length=16)),
                ('current_ballance', models.DecimalField(decimal_places=2, default=0, max_digits=11)),
            ],
        ),
        migrations.CreateModel(
            name='Operation',
            fields=[
                ('number', models.IntegerField(primary_key=True, serialize=False, unique=True)),
                ('date', models.DateField()),
                ('description', models.CharField(max_length=255)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=11)),
                ('currency', models.TextField(default='EUR')),
                ('effective_date', models.DateField()),
                ('counterparty_IBAN', models.CharField(max_length=255)),
                ('counterparty_name', models.CharField(max_length=255)),
                ('communication', models.CharField(max_length=255)),
                ('reference', models.CharField(max_length=255)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.account')),
            ],
        ),
        migrations.CreateModel(
            name='ExpenseReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('beneficiary_account', models.TextField()),
                ('total', models.DecimalField(decimal_places=2, max_digits=11)),
                ('beneficiary', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
