# Generated by Django 4.1.4 on 2022-12-28 20:48
from django.contrib.contenttypes.models import ContentType
from django.db import migrations
from django.db.models import F, OuterRef, Subquery


def convert_from_signup_to_bill(apps, schema_editor):
    Signup = apps.get_model("signup2022", "signup")
    OperationValidation = apps.get_model("accounts", "operationvalidation")
    OperationValidation.objects.filter(
        content_type=ContentType.objects.get_by_natural_key("signup2022", "signup")
    ).annotate(
        bill_id=Subquery(
            Signup.objects.filter(id=OuterRef("object_id")).values("bill__id")[:1]
        )
    ).update(
        content_type=ContentType.objects.get_by_natural_key("signup2022", "bill"),
        object_id=F("bill_id"),
    )


def convert_from_bill_to_signup(apps, schema_editor):
    Signup = apps.get_model("signup2022", "signup")
    OperationValidation = apps.get_model("accounts", "operationvalidation")
    OperationValidation.objects.filter(
        content_type=ContentType.objects.get_by_natural_key("signup2022", "bill")
    ).annotate(
        signup_id=Subquery(
            Signup.objects.filter(bill__id=OuterRef("object_id")).values("id")[:1]
        )
    ).update(
        content_type=ContentType.objects.get_by_natural_key("signup2022", "signup"),
        object_id=F("signup_id"),
    )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_bill_amount"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="signupoperation",
            options={
                "verbose_name": "paiement inscriptions 2022",
                "verbose_name_plural": "paiements inscriptions 2022",
            },
        ),
        migrations.RunPython(convert_from_signup_to_bill, convert_from_bill_to_signup),
    ]
