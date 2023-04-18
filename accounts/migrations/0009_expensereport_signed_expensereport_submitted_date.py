# Generated by Django 4.1.4 on 2023-02-19 20:18

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0008_alter_operationvalidation_content_type_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="expensereport",
            name="signed",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="expensereport",
            name="submitted_date",
            field=models.DateField(null=True),
        ),
    ]
