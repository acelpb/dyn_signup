# Generated by Django 3.2.4 on 2021-06-27 20:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('signup', '0002_ballad_guide'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Ballad',
            new_name='Ride',
        ),
        migrations.RenameField(
            model_name='participant',
            old_name='ballad',
            new_name='ride',
        ),
    ]