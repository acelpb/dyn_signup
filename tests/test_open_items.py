"""Open-item accounting on OperationValidation.

A placeholder (operation=None) is an open item — a payable/receivable
waiting to be settled by an imported bank operation, possibly in parts.
"""

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth.models import User

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
    )


def open_item(bill, amount=Decimal("-100.00")):
    return OperationValidation.objects.create(
        operation=None,
        event=bill,
        amount=amount,
        validation_type=ExpenditureChoices.ROOM_RENTAL,
        due_date=bill.date,
        expected_iban="BE71096123456769",
    )


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
class TestQuerySet:
    def test_open_settled_and_payables(self, account, bill):
        placeholder = open_item(bill)
        operation = make_operation(account, Decimal("-40.00"))
        settled = placeholder.settle(operation, amount=Decimal("-40.00"))

        assert placeholder in OperationValidation.objects.open()
        assert settled not in OperationValidation.objects.open()
        assert settled in OperationValidation.objects.settled()
        assert placeholder in OperationValidation.objects.payables()
