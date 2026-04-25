from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("signup2026", "0007_waiting_list_participant_proxy"),
    ]

    operations = [
        migrations.AddField(
            model_name="signup",
            name="payment_confirmation_sent_at",
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
    ]
