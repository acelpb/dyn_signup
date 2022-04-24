# Generated by Django 4.0.3 on 2022-04-24 18:15

import datetime
from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Signup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('validated_at', models.DateTimeField(default=None, null=True)),
                ('cancelled_at', models.DateTimeField(default=None, null=True)),
                ('owner', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Participant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=150, verbose_name='Prénom')),
                ('last_name', models.CharField(max_length=150, verbose_name='Nom de Famille')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='adresse e-mail')),
                ('birthday', models.DateField(verbose_name='date de naissance')),
                ('city', models.CharField(max_length=150, verbose_name='ville de domicile')),
                ('country', models.CharField(default='Belgium', max_length=150, verbose_name='pays de résidence')),
                ('vae', models.BooleanField(help_text='Vélo à assistance électrique', verbose_name='VAE')),
                ('signup_group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='signup2022.signup')),
            ],
        ),
        migrations.CreateModel(
            name='DaySignup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day', models.DateField(choices=[(datetime.date(2022, 7, 18), '2022-07-18'), (datetime.date(2022, 7, 19), '2022-07-19'), (datetime.date(2022, 7, 20), '2022-07-20'), (datetime.date(2022, 7, 21), '2022-07-21'), (datetime.date(2022, 7, 22), '2022-07-22'), (datetime.date(2022, 7, 23), '2022-07-23')], validators=[django.core.validators.MinValueValidator(datetime.date(2022, 7, 18)), django.core.validators.MaxValueValidator(datetime.date(2022, 7, 23))])),
                ('created_at', models.DateField(auto_now_add=True)),
                ('cancelled', models.DateField(blank=True, null=True)),
                ('participant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='signup2022.participant')),
            ],
        ),
        migrations.CreateModel(
            name='Bill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('ballance', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('payed_at', models.DateTimeField(default=None, null=True)),
                ('signup', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='signup2022.signup')),
            ],
        ),
        migrations.AddConstraint(
            model_name='daysignup',
            constraint=models.UniqueConstraint(fields=('participant', 'day'), name='no double counting'),
        ),
    ]
