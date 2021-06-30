# Generated by Django 3.2.4 on 2021-06-30 20:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('signup', '0004_auto_20210627_2255'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='ride',
            options={'verbose_name': 'ride'},
        ),
        migrations.AddField(
            model_name='participant',
            name='email',
            field=models.EmailField(blank=True, max_length=254, null=True, verbose_name='e-mail'),
        ),
    ]
