"""Create open items (placeholders) for bills not fully paid yet.

Bills used to store their expectation only in the `amount` field; open-item
accounting expects a placeholder OperationValidation per unpaid remainder.
"""

from django.db import migrations
from django.db.models import Sum


def create_bill_placeholders(apps, schema_editor):
    Bill = apps.get_model("accounts", "Bill")
    OperationValidation = apps.get_model("accounts", "OperationValidation")
    ContentType = apps.get_model("contenttypes", "ContentType")

    bill_ct, _ = ContentType.objects.get_or_create(app_label="accounts", model="bill")
    for bill in Bill.objects.all():
        linked = OperationValidation.objects.filter(
            content_type=bill_ct, object_id=bill.id
        )
        # Payments are stored negative; remaining > 0 means still to pay.
        paid_or_open = linked.aggregate(total=Sum("amount"))["total"] or 0
        remaining = bill.amount + paid_or_open
        if remaining > 0:
            OperationValidation.objects.create(
                operation=None,
                content_type=bill_ct,
                object_id=bill.id,
                amount=-remaining,
                due_date=bill.date,
            )


def remove_bill_placeholders(apps, schema_editor):
    OperationValidation = apps.get_model("accounts", "OperationValidation")
    ContentType = apps.get_model("contenttypes", "ContentType")
    bill_ct = ContentType.objects.filter(app_label="accounts", model="bill").first()
    if bill_ct:
        OperationValidation.objects.filter(
            content_type=bill_ct, operation__isnull=True
        ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0023_bill_category_bill_iban"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(create_bill_placeholders, remove_bill_placeholders),
    ]
