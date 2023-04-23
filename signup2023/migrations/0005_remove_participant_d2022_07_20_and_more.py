# Generated by Django 4.1.7 on 2023-04-23 13:29

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("signup2023", "0004_rename_d2022_07_21_participant_d2023_07_21_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="participant",
            name="d2022_07_20",
        ),
        migrations.AddField(
            model_name="participant",
            name="pre_departure",
            field=models.BooleanField(
                default=False,
                help_text="Je souhaite venir la veille du départ",
                verbose_name="20-07",
            ),
        ),
        migrations.AlterField(
            model_name="participant",
            name="vae",
            field=models.CharField(
                choices=[("🦵🚲", "NORMAL_BIKE"), ("🔋🚲", "ELECTRIC_BIKE")],
                help_text="Vélo à assistance électrique",
                max_length=17,
                verbose_name="VAE",
            ),
        ),
    ]