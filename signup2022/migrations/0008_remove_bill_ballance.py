# Generated by Django 4.1.4 on 2022-12-29 00:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('signup2022', '0007_alter_bill_options_alter_participant_options_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='bill',
            name='ballance',
        ),
    ]
