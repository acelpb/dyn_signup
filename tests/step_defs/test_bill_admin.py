from decimal import Decimal

from django.contrib.auth.models import Permission
from django.urls import reverse
from model_bakery import baker
from pytest_bdd import given, parsers, scenario, then, when

from accounts.models import Bill, Operation

PREFIX = "accounts-operationvalidation-content_type-object_id"


@scenario(
    "bill_admin.feature",
    "Creating a bill registers its amount as an open payment line",
)
def test_create_bill_registers_amount(db):
    pass


@scenario("bill_admin.feature", "The amount can be corrected while nothing is paid")
def test_amount_editable_before_payment(db):
    pass


@scenario("bill_admin.feature", "The amount is locked once a payment is settled")
def test_amount_locked_after_settlement(db):
    pass


@scenario("bill_admin.feature", "The ventilation can be edited until the bill is paid")
def test_ventilation_editable_until_paid(db):
    pass


@scenario("bill_admin.feature", "A settled payment line cannot be deleted")
def test_settled_line_cannot_be_deleted(db):
    pass


@scenario("bill_admin.feature", "A ventilation line must be a negative amount")
def test_ventilation_line_must_be_negative(db):
    pass


@scenario("bill_admin.feature", "A paid bill can no longer be edited by a treasurer")
def test_paid_bill_locked(db):
    pass


@scenario("bill_admin.feature", "A bill without any payment line is not shown as paid")
def test_empty_bill_not_paid(db):
    pass


def _decimal(number):
    return Decimal(str(number))


def _inline_data(rows):
    data = {
        f"{PREFIX}-TOTAL_FORMS": str(len(rows)),
        f"{PREFIX}-INITIAL_FORMS": str(sum(1 for row in rows if row.get("id"))),
        f"{PREFIX}-MIN_NUM_FORMS": "0",
        f"{PREFIX}-MAX_NUM_FORMS": "1000",
    }
    for index, row in enumerate(rows):
        for key, value in row.items():
            data[f"{PREFIX}-{index}-{key}"] = value
    return data


def _existing_rows(bill):
    return [
        {
            "id": str(line.pk),
            "validation_type": str(line.validation_type or ""),
            "amount": str(line.amount),
        }
        for line in bill.payments.order_by("pk")
    ]


def _post_change(client, bill, amount, rows, name=None):
    return client.post(
        reverse("admin:accounts_bill_change", args=[bill.pk]),
        {
            "name": name or bill.name,
            "date": bill.date.strftime("%d/%m/%Y"),
            "amount": str(amount),
            "category": "",
            "iban": "",
            **_inline_data(rows),
        },
    )


@given("I am logged in to the admin as a treasurer", target_fixture="treasurer_client")
def treasurer_client(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="treasurer", password="something", is_staff=True
    )
    user.user_permissions.set(
        Permission.objects.filter(content_type__app_label="accounts")
    )
    client.force_login(user)
    return client


@given(parsers.parse('a bill "{name}" of {amount:g} euros'), target_fixture="bill")
def bill(name, amount):
    bill = baker.make(Bill, name=name)
    bill.set_amount(_decimal(amount))
    return bill


@given(
    parsers.parse(
        'a bill "{name}" of {amount:g} euros partially paid with {paid:g} euros'
    ),
    target_fixture="bill",
)
def partially_paid_bill(name, amount, paid):
    bill = baker.make(Bill, name=name)
    bill.set_amount(_decimal(amount))
    operation = baker.make(Operation, amount=-_decimal(paid))
    bill.payments.get().settle(operation, amount=-_decimal(paid))
    return bill


@given(
    parsers.parse('a bill "{name}" of {amount:g} euros fully paid'),
    target_fixture="bill",
)
def paid_bill(name, amount):
    bill = baker.make(Bill, name=name)
    bill.set_amount(_decimal(amount))
    operation = baker.make(Operation, amount=-_decimal(amount))
    bill.payments.get().settle(operation)
    return bill


@given(
    parsers.parse('a bill "{name}" without any payment line'),
    target_fixture="empty_bill",
)
def empty_bill(name):
    return baker.make(Bill, name=name)


@when(
    parsers.parse('I create a bill named "{name}" of {amount:g} euros'),
    target_fixture="response",
)
def create_bill(treasurer_client, name, amount):
    return treasurer_client.post(
        reverse("admin:accounts_bill_add"),
        {
            "name": name,
            "date": "01/07/2026",
            "amount": str(amount),
            "category": "",
            "iban": "",
            **_inline_data([]),
        },
    )


@when(
    parsers.parse("I change the bill amount to {amount:g} euros"),
    target_fixture="response",
)
def change_amount(treasurer_client, bill, amount):
    return _post_change(treasurer_client, bill, amount, _existing_rows(bill))


@when(
    parsers.parse("I split the bill into lines of {first:g} and {second:g} euros"),
    target_fixture="response",
)
def split_bill(treasurer_client, bill, first, second):
    line = bill.payments.get()
    rows = [
        {"id": str(line.pk), "validation_type": "", "amount": str(-_decimal(first))},
        {"id": "", "validation_type": "", "amount": str(-_decimal(second))},
    ]
    total = _decimal(first) + _decimal(second)
    return _post_change(treasurer_client, bill, total, rows)


@when("I try to delete the settled payment line", target_fixture="response")
def delete_settled_line(treasurer_client, bill):
    rows = _existing_rows(bill)
    settled_ids = set(
        str(pk) for pk in bill.payments.settled().values_list("pk", flat=True)
    )
    for row in rows:
        if row["id"] in settled_ids:
            row["DELETE"] = "on"
    total = -sum(line.amount for line in bill.payments.all())
    return _post_change(treasurer_client, bill, total, rows)


@when(
    parsers.parse("I add a ventilation line of {amount:g} euros"),
    target_fixture="response",
)
def add_positive_line(treasurer_client, bill, amount):
    rows = _existing_rows(bill)
    rows.append({"id": "", "validation_type": "", "amount": str(_decimal(amount))})
    total = -sum(line.amount for line in bill.payments.all())
    return _post_change(treasurer_client, bill, total, rows)


@when("I try to rename the bill", target_fixture="response")
def rename_bill(treasurer_client, bill):
    return _post_change(
        treasurer_client,
        bill,
        -sum(line.amount for line in bill.payments.all()),
        _existing_rows(bill),
        name="Renommée",
    )


@when("I look at the bill list", target_fixture="response")
def bill_list(treasurer_client):
    return treasurer_client.get(reverse("admin:accounts_bill_changelist"))


@then(
    parsers.parse(
        'the bill "{name}" totals {total:g} euros with {remaining:g} euros left to pay'
    )
)
def check_totals(name, total, remaining):
    bill = Bill.objects.with_amounts().get(name=name)
    assert bill.amount == _decimal(total)
    assert bill.remaining == _decimal(remaining)


@then("I am told to edit the ventilation instead")
def check_ventilation_error(response):
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "modifiez les lignes de ventilation" in content


@then(parsers.parse("the bill has {count:d} open payment lines"))
def check_open_lines(bill, count):
    assert bill.payments.open().count() == count


@then("the deletion is refused")
def check_deletion_refused(response):
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Une ligne déjà réglée ne peut pas être supprimée." in content


@then("I am told the amount must be negative")
def check_negative_amount_error(response):
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "doit être négatif" in content


@then("the change is refused")
def check_change_refused(response):
    assert response.status_code == 403


@then(parsers.parse('the bill is still named "{name}"'))
def check_bill_name(bill, name):
    bill.refresh_from_db()
    assert bill.name == name


@then(parsers.parse('the bill "{name}" is not marked as paid'))
def check_not_paid(response, name):
    bills = {b.name: b for b in response.context["cl"].result_list}
    assert not bills[name]._payed


@then(parsers.parse('the bill "{name}" is marked as paid'))
def check_paid(response, name):
    bills = {b.name: b for b in response.context["cl"].result_list}
    assert bills[name]._payed
