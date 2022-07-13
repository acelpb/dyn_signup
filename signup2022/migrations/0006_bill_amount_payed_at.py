# Generated by Django 3.2 on 2022-07-13 22:08

from django.db import migrations, models


def fill_amount_payed_at(apps, schema_editor):
    Bill = apps.get_model('signup2022', 'Bill')
    for bill in Bill.objects.filter(payed_at__isnull=False):
        bill.amount_payed_at = bill.amount - bill.ballance


class Migration(migrations.Migration):

    dependencies = [
        ('signup2022', '0005_alter_bill_payed_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='bill',
            name='amount_payed_at',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.RunPython(fill_amount_payed_at, migrations.RunPython.noop),
    ]
