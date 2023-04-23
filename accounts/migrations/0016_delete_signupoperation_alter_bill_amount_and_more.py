# Generated by Django 4.1.7 on 2023-04-23 09:39

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_squashed_0015_expensefile_expense_report"),
    ]

    operations = [
        migrations.DeleteModel(
            name="SignupOperation",
        ),
        migrations.AlterField(
            model_name="bill",
            name="amount",
            field=models.DecimalField(decimal_places=2, max_digits=11),
        ),
        migrations.AlterField(
            model_name="justification",
            name="title",
            field=models.CharField(max_length=255),
        ),
    ]
