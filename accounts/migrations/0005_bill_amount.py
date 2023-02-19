# Generated by Django 3.2 on 2022-12-18 19:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_bill_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='bill',
            name='amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=11),
            preserve_default=False,
        ),
    ]