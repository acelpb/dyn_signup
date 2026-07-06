"""Open-item accounting on OperationValidation.

A placeholder (operation=None) is an open item — a payable/receivable
waiting to be settled by an imported bank operation, possibly in parts.
"""

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth.models import User

from accounts.forms import LinkToBillForm
from accounts.models import (
    Account,
    Bill,
    ExpenditureChoices,
    Operation,
    OperationValidation,
)


@pytest.fixture
def account(db):
    return Account.objects.create(name="Compte courant", IBAN="BE68539007547034")


@pytest.fixture
def user(db):
    return User.objects.create_user(username="treasurer")


def make_operation(account, amount, number=1, **kwargs):
    return Operation.objects.create(
        account=account,
        year=2026,
        number=number,
        date=datetime.date(2026, 7, 1),
        effective_date=datetime.date(2026, 7, 1),
        description="virement",
        amount=amount,
        counterparty_IBAN=kwargs.pop("counterparty_IBAN", "BE71096123456769"),
        counterparty_name=kwargs.pop("counterparty_name", "John Doe"),
        communication="",
        reference="",
        **kwargs,
    )


@pytest.fixture
def bill(db):
    return Bill.objects.create(
        name="Location salle",
        amount=Decimal("100.00"),
        date=datetime.date(2026, 6, 15),
        category=ExpenditureChoices.ROOM_RENTAL,
        iban="BE71096123456769",
    )


def open_item(bill):
    "The placeholder automatically created when the bill was saved."
    return bill.payments.get(operation__isnull=True)


@pytest.mark.django_db
class TestSettle:
    def test_full_settlement_attaches_operation(self, account, bill):
        item = open_item(bill)
        operation = make_operation(account, Decimal("-100.00"))

        settled = item.settle(operation)

        assert settled.pk == item.pk
        item.refresh_from_db()
        assert item.operation == operation
        assert not item.is_open

    def test_partial_settlement_splits_the_item(self, account, bill, user):
        item = open_item(bill)
        operation = make_operation(account, Decimal("-40.00"))

        settled = item.settle(operation, user=user, amount=Decimal("-40.00"))

        assert settled.pk != item.pk
        assert settled.operation == operation
        assert settled.amount == Decimal("-40.00")
        assert settled.validation_type == item.validation_type
        assert settled.event == bill
        assert settled.created_by == user
        item.refresh_from_db()
        assert item.is_open
        assert item.amount == Decimal("-60.00")

    def test_rejects_settling_a_settled_item(self, account, bill):
        item = open_item(bill)
        operation = make_operation(account, Decimal("-100.00"))
        item.settle(operation)
        with pytest.raises(ValueError, match="already settled"):
            item.settle(operation)

    def test_rejects_partial_larger_than_open_amount(self, account, bill):
        item = open_item(bill)
        operation = make_operation(account, Decimal("-150.00"))
        with pytest.raises(ValueError, match="more than the open amount"):
            item.settle(operation, amount=Decimal("-150.00"))

    def test_rejects_partial_with_opposite_sign(self, account, bill):
        item = open_item(bill)
        operation = make_operation(account, Decimal("40.00"))
        with pytest.raises(ValueError, match="same sign"):
            item.settle(operation, amount=Decimal("40.00"))


@pytest.mark.django_db
class TestBillOpenItem:
    def test_bill_creation_creates_placeholder(self, bill):
        item = open_item(bill)
        assert item.amount == Decimal("-100.00")
        assert item.validation_type == ExpenditureChoices.ROOM_RENTAL
        assert item.due_date == bill.date
        assert item.expected_iban == bill.iban

    def test_editing_unpaid_bill_syncs_placeholder(self, bill):
        bill.amount = Decimal("120.00")
        bill.category = ExpenditureChoices.EQUIPMENT
        bill.save()

        item = open_item(bill)
        assert item.amount == Decimal("-120.00")
        assert item.validation_type == ExpenditureChoices.EQUIPMENT

    def test_no_sync_once_a_payment_is_settled(self, account, bill):
        operation = make_operation(account, Decimal("-40.00"))
        open_item(bill).settle(operation, amount=Decimal("-40.00"))

        bill.amount = Decimal("200.00")
        bill.save()

        assert open_item(bill).amount == Decimal("-60.00")

    def test_link_form_settles_the_whole_bill(self, account, bill):
        operation = make_operation(account, Decimal("-100.00"))
        form = LinkToBillForm(data={"operations": [operation.pk], "bill": bill.pk})
        assert form.is_valid()
        form.save()

        assert not bill.payments.filter(operation__isnull=True).exists()
        settled = bill.payments.get(operation=operation)
        assert settled.amount == Decimal("-100.00")
        assert settled.validation_type == ExpenditureChoices.ROOM_RENTAL

    def test_link_form_partial_payment_splits_the_item(self, account, bill):
        operation = make_operation(account, Decimal("-40.00"))
        form = LinkToBillForm(data={"operations": [operation.pk], "bill": bill.pk})
        assert form.is_valid()
        form.save()

        settled = bill.payments.get(operation=operation)
        assert settled.amount == Decimal("-40.00")
        assert settled.validation_type == ExpenditureChoices.ROOM_RENTAL
        assert open_item(bill).amount == Decimal("-60.00")

    def test_link_form_overpayment_keeps_operation_justified(self, account, bill):
        operation = make_operation(account, Decimal("-120.00"))
        form = LinkToBillForm(data={"operations": [operation.pk], "bill": bill.pk})
        assert form.is_valid()
        form.save()

        assert not bill.payments.filter(operation__isnull=True).exists()
        settled_total = sum(v.amount for v in bill.payments.filter(operation=operation))
        assert settled_total == Decimal("-120.00")


@pytest.mark.django_db
class TestRefundPayeeStamping:
    def test_offer_refund_stamps_the_account_that_paid(self, account):
        from django.contrib.contenttypes.models import ContentType
        from django.utils import timezone

        from accounts.models import IncomeChoices
        from signup2026.models import Participant, Signup

        owner = User.objects.create_user(username="owner", email="owner@example.com")
        signup = Signup.objects.create(owner=owner)
        participant = Participant.objects.create(
            signup_group=signup,
            first_name="John",
            last_name="Doe",
            birthday=datetime.date(1990, 1, 1),
            city="Brussels",
            amount_due_modified=Decimal("100.00"),
        )
        operation = make_operation(
            account,
            Decimal("130.00"),
            counterparty_IBAN="BE71096123456769",
            counterparty_name="Jane Payer",
        )
        OperationValidation.objects.create(
            operation=operation,
            amount=Decimal("130.00"),
            event=participant,
            validation_type=IncomeChoices.SIGNUP,
        )

        signup.offer_refund(owner)

        refund = OperationValidation.objects.payables().get(
            content_type=ContentType.objects.get_for_model(Participant),
            object_id=participant.id,
        )
        assert refund.amount == Decimal("-30.00")
        assert refund.expected_iban == "BE71096123456769"
        assert refund.expected_counterparty_name == "Jane Payer"
        assert refund.due_date == timezone.localdate()


@pytest.mark.django_db
class TestSettleEventEndpoint:
    def settle_url(self, operation, event):
        from django.contrib.contenttypes.models import ContentType
        from django.urls import reverse

        return reverse(
            "admin:accounts_operation_settle_event",
            args=[
                operation.pk,
                ContentType.objects.get_for_model(type(event)).pk,
                event.pk,
            ],
        )

    def test_settles_all_open_items_of_the_event(self, admin_client, account, bill):
        operation = make_operation(account, Decimal("-100.00"))

        response = admin_client.get(self.settle_url(operation, bill))

        assert response.status_code == 302
        assert not bill.payments.filter(operation__isnull=True).exists()
        assert bill.payments.get(operation=operation).amount == Decimal("-100.00")

    def test_partial_operation_splits_single_open_item(
        self, admin_client, account, bill
    ):
        operation = make_operation(account, Decimal("-40.00"))

        admin_client.get(self.settle_url(operation, bill))

        assert bill.payments.get(operation=operation).amount == Decimal("-40.00")
        assert open_item(bill).amount == Decimal("-60.00")

    def test_refuses_amount_mismatch_with_several_items(
        self, admin_client, account, bill
    ):
        bill.payments.create(operation=None, amount=Decimal("-10.00"))
        operation = make_operation(account, Decimal("-40.00"))

        admin_client.get(self.settle_url(operation, bill))

        assert not bill.payments.filter(operation__isnull=False).exists()

    def test_refuses_unvalidated_expense_report(self, admin_client, account):
        from accounts.models import ExpenseReport

        report = ExpenseReport.objects.create(
            title="NDF-2026-1", iban="BE68539007547034", validated=False
        )
        line = report.expenses.create(operation=None, amount=Decimal("-42.50"))
        operation = make_operation(account, Decimal("-42.50"))

        admin_client.get(self.settle_url(operation, report))

        line.refresh_from_db()
        assert line.is_open


@pytest.mark.django_db
class TestPendingPaymentsEntries:
    def test_bill_entry_carries_payee_and_due_date(self, admin_client, bill):
        from django.urls import reverse

        response = admin_client.get(reverse("pending_payments"))

        entries = [
            e for e in response.context["pending_payments"] if e["event"] == bill
        ]
        assert len(entries) == 1
        entry = entries[0]
        assert entry["type_label"] == "Facture"
        assert entry["to_pay"] == Decimal("100.00")
        assert entry["payee_iban"] == bill.iban
        assert entry["due_date"] == bill.date
        assert response.context["total"] == Decimal("100.00")

    def test_matching_operation_ranked_by_iban(self, admin_client, account, bill):
        from django.urls import reverse

        other = make_operation(
            account,
            Decimal("-100.00"),
            number=2,
            counterparty_IBAN="BE00000000000000",
            counterparty_name="Autre",
        )
        matching = make_operation(
            account,
            Decimal("-100.00"),
            number=3,
            counterparty_IBAN=bill.iban,
            counterparty_name="Proprietaire",
        )

        response = admin_client.get(reverse("pending_payments"))

        (entry,) = [
            e for e in response.context["pending_payments"] if e["event"] == bill
        ]
        assert [m["operation"] for m in entry["matches"]][0] == matching
        assert entry["matches"][0]["iban_match"] is True
        assert {m["operation"] for m in entry["matches"]} == {matching, other}


@pytest.mark.django_db
class TestQuerySet:
    def test_open_settled_and_payables(self, account, bill):
        placeholder = open_item(bill)
        operation = make_operation(account, Decimal("-40.00"))
        settled = placeholder.settle(operation, amount=Decimal("-40.00"))

        assert placeholder in OperationValidation.objects.open()
        assert settled not in OperationValidation.objects.open()
        assert settled in OperationValidation.objects.settled()
        assert placeholder in OperationValidation.objects.payables()
