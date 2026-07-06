from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from model_bakery import baker
from pytest_bdd import given, scenario, then, when

from accounts.models import Bill, ExpenseReport, Operation, OperationValidation


@scenario("pending_payments.feature", "Treasurer sees all payments to make in one view")
def test_pending_payments_displayed(db):
    pass


@scenario("pending_payments.feature", "Fully reimbursed expense reports are not listed")
def test_reimbursed_expense_report_hidden(db):
    pass


@scenario(
    "pending_payments.feature",
    "A matching imported operation is suggested for an expense report",
)
def test_matching_operation_suggested_for_expense_report(db):
    pass


@scenario(
    "pending_payments.feature", "A matching imported operation is suggested for a bill"
)
def test_matching_operation_suggested_for_bill(db):
    pass


@scenario(
    "pending_payments.feature", "A regular user cannot access the pending payments page"
)
def test_regular_user_denied(db):
    pass


@given("an expense report awaiting reimbursement", target_fixture="pending_report")
def pending_report():
    beneficiary = baker.make(
        "auth.User", first_name="Marie", last_name="Curie", email="marie@example.com"
    )
    report = baker.make(
        ExpenseReport,
        title="NDF-TEST-1",
        beneficiary=beneficiary,
        iban="BE68539007547034",
        validated=True,
    )
    OperationValidation.objects.create(amount=Decimal("-42.50"), event=report)
    return report


@given("a bill awaiting payment", target_fixture="unpaid_bill")
def unpaid_bill():
    bill = baker.make(Bill, name="Location salle")
    bill.set_amount(Decimal("250.00"))
    return bill


@given("a bill already paid", target_fixture="paid_bill")
def paid_bill():
    bill = baker.make(Bill, name="Facture payee")
    bill.set_amount(Decimal("100.00"))
    operation = baker.make(Operation, amount=Decimal("-100.00"))
    bill.payments.get(operation__isnull=True).settle(operation)
    return bill


@given("an expense report fully reimbursed", target_fixture="reimbursed_report")
def reimbursed_report():
    report = baker.make(
        ExpenseReport,
        title="NDF-PAYEE",
        iban="BE68539007547034",
        validated=True,
    )
    operation = baker.make(Operation, amount=Decimal("-15.00"))
    OperationValidation.objects.create(
        operation=operation, amount=Decimal("-15.00"), event=report
    )
    return report


@given(
    "an imported unjustified operation matching the expense report",
    target_fixture="matching_operation",
)
def matching_operation(pending_report):
    return baker.make(
        Operation,
        amount=Decimal("-42.50"),
        counterparty_IBAN="BE68 5390 0754 7034",
        counterparty_name="Marie Curie",
    )


@given("an imported unjustified operation with a different amount")
def non_matching_operation():
    return baker.make(
        Operation,
        amount=Decimal("-999.99"),
        counterparty_name="Autre Fournisseur",
    )


@given(
    "an imported unjustified operation matching the bill",
    target_fixture="bill_operation",
)
def bill_operation(unpaid_bill):
    return baker.make(
        Operation,
        amount=Decimal("-250.00"),
        counterparty_name="Proprietaire Salle",
    )


@when("I visit the pending payments page", target_fixture="response")
def visit_pending_payments(admin_client):
    return admin_client.get(reverse("pending_payments"))


@then("I see the expense report with its IBAN and amount")
def check_expense_report_visible(response, pending_report):
    content = response.content.decode("utf-8")
    assert response.status_code == 200
    assert "NDF-TEST-1" in content
    assert "BE68539007547034" in content
    assert "42.50" in content or "42,50" in content


@then("I see the unpaid bill with its remaining amount")
def check_unpaid_bill_visible(response):
    content = response.content.decode("utf-8")
    assert "Location salle" in content
    assert "250.00" in content or "250,00" in content


@then("I do not see the paid bill")
def check_paid_bill_hidden(response):
    assert "Facture payee" not in response.content.decode("utf-8")


@then("I do not see the reimbursed expense report")
def check_reimbursed_report_hidden(response):
    assert response.status_code == 200
    assert "NDF-PAYEE" not in response.content.decode("utf-8")


@then("I see a link to connect the matching operation to the expense report")
def check_expense_report_match_link(response, pending_report, matching_operation):
    content = response.content.decode("utf-8")
    url = reverse(
        "admin:accounts_operation_settle_event",
        args=[
            matching_operation.pk,
            ContentType.objects.get_for_model(ExpenseReport).pk,
            pending_report.pk,
        ],
    )
    assert url in content
    assert "IBAN ✓" in content


@then("the operation with a different amount is not suggested")
def check_non_matching_operation_hidden(response):
    assert "Autre Fournisseur" not in response.content.decode("utf-8")


@then("I see a link to connect the matching operation to the bill")
def check_bill_match_link(response, unpaid_bill, bill_operation):
    content = response.content.decode("utf-8")
    url = reverse(
        "admin:accounts_operation_settle_event",
        args=[
            bill_operation.pk,
            ContentType.objects.get_for_model(Bill).pk,
            unpaid_bill.pk,
        ],
    )
    assert url in content


@when("the participant visits the pending payments page", target_fixture="response")
def participant_visits(client, participant):
    client.force_login(participant)
    return client.get(reverse("pending_payments"))


@then("the access is denied")
def check_access_denied(response):
    assert response.status_code == 403
