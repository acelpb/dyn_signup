# Generated by Django 4.0.3 on 2022-05-01 11:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('signup2022', '0002_alter_participant_managers_participant_d2022_07_18_and_more'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='participant',
            managers=[
            ],
        ),
        migrations.AddField(
            model_name='signup',
            name='on_hold',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='signup',
            name='on_hold_partial',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='signup',
            name='on_hold_vae',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='participant',
            name='country',
            field=models.CharField(default='Belgique', max_length=150, verbose_name='pays de résidence'),
        ),
    ]
