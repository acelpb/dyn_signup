"""Backfill payee info on existing open refund placeholders.

Refunds must go back to the bank account that paid: copy the counterparty
of the latest settled payment for the same event onto the placeholder.
"""

from django.db import migrations


def backfill_payees(apps, schema_editor):
    OperationValidation = apps.get_model("accounts", "OperationValidation")

    refunds = OperationValidation.objects.filter(
        operation__isnull=True, amount__lt=0, expected_iban=""
    ).exclude(content_type=None)
    for refund in refunds:
        previous_payment = (
            OperationValidation.objects.filter(
                content_type=refund.content_type,
                object_id=refund.object_id,
                operation__isnull=False,
            )
            .select_related("operation")
            .order_by("-operation__date")
            .first()
        )
        if previous_payment:
            refund.expected_iban = previous_payment.operation.counterparty_IBAN
            refund.expected_counterparty_name = (
                previous_payment.operation.counterparty_name
            )
            refund.save(update_fields=["expected_iban", "expected_counterparty_name"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0024_bill_open_items"),
    ]

    operations = [
        migrations.RunPython(backfill_payees, migrations.RunPython.noop),
    ]
