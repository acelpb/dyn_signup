# Generated by Django 4.1.7 on 2023-04-23 17:02

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("signup2023", "0005_remove_participant_d2022_07_20_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="participant",
            name="vae",
            field=models.BooleanField(
                choices=[(False, "🦵🚲"), (True, "🔋🚲")],
                default=False,
                help_text="Vélo à assistance électrique",
                max_length=17,
                verbose_name="VAE",
            ),
        ),
    ]