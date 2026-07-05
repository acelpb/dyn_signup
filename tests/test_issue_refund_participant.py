from datetime import date

import pytest
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from accounts.models import OperationValidation
from signup2026.models import Participant, Signup


@pytest.mark.django_db
def test_offer_refund_links_to_participant(admin_client):
    # Setup: Create a signup with a negative balance
    user = User.objects.create_user(username="testuser", email="test@example.com")
    signup = Signup.objects.create(owner=user)
    participant = Participant.objects.create(
        signup_group=signup,
        first_name="John",
        last_name="Doe",
        birthday=date(1990, 1, 1),
        city="Brussels",
    )

    # Manually set a negative balance by creating a validation that exceeds amount_due
    # Assuming signup.balance() or signup.balance uses amount_due and amount_payed
    # Let's mock or ensure balance is negative.
    # In signup2026/admin.py, offer_refund checks signup.balance

    # We need to make sure signup.balance() returns a negative value.
    # amount_payed comes from OperationValidation
    # amount_due comes from calculate_amounts()

    # Manually set a negative balance by creating a validation linked to the participant
    # with_amounts() uses a subquery on Participant.payments

    participant_ct = ContentType.objects.get_for_model(Participant)
    from accounts.models import IncomeChoices

    OperationValidation.objects.create(
        content_type=participant_ct,
        object_id=participant.id,
        amount=1000,  # Payed 1000, balance should be 465 - 1000 = -535
        validation_type=IncomeChoices.SIGNUP,
        operation=None,
    )

    # If amount_due is 60, balance will be 60 - 100 = -40
    # Let's assume for this test we can control it.

    from django.contrib.admin.sites import AdminSite

    from signup2026.admin import SignupAdmin

    admin_site = AdminSite()
    signup_admin = SignupAdmin(Signup, admin_site)

    # Mock request
    from django.contrib.messages.storage.base import BaseStorage
    from django.test import RequestFactory

    request = RequestFactory().get(
        reverse("admin:signup2026_signup_change", args=[signup.id])
    )
    storage = BaseStorage(request)
    storage._queued_messages = []
    request._messages = storage
    request.user = User.objects.get(is_superuser=True)  # or admin_client.user

    # We need to ensure signup has balance attribute as expected by admin
    # signup = Signup.objects.with_amounts().get(pk=signup.id)
    # The action expects the object from the queryset

    signup_with_amounts = Signup.objects.with_amounts().get(pk=signup.id)

    response = signup_admin.offer_refund(request, signup_with_amounts)
    # response might be None if messages.error was called and it returned.
    # But here balance should be negative.
    # Oh, wait. I created a validation of 100. What is amount_due?
    # Signup calculate_amounts() needs to be called to set amount_due_calculated on participants.

    signup_with_amounts.calculate_amounts()
    # Re-fetch with amounts
    signup_with_amounts = Signup.objects.with_amounts().get(pk=signup.id)
    print(f"Balance: {signup_with_amounts.balance}")

    response = signup_admin.offer_refund(request, signup_with_amounts)
    if response is None:
        print(f"Messages: {[m.message for m in storage._queued_messages]}")
    assert response is not None, "Action returned None, check messages"
    assert response.status_code == 302  # Redirects back to change page

    # Check if OperationValidation was created for Participant instead of Signup
    participant_ct = ContentType.objects.get_for_model(Participant)
    validations = OperationValidation.objects.filter(
        content_type=participant_ct, object_id=participant.id, amount__lt=0
    )

    assert validations.exists(), (
        "Refund validation should be linked to Participant and have negative amount"
    )
    assert validations.first().amount < 0

    # Verify that it appears in PendingPaymentsView
    from accounts.views import PendingPaymentsView

    view = PendingPaymentsView()
    view.request = request
    context = view.get_context_data()

    refund_ids = [r.id for r in context["refunds"]]
    assert validations.first().id in refund_ids, (
        "Refund should appear in pending payments"
    )

    # Verify context contains the participant as object
    refund_v = [r for r in context["refunds"] if r.id == validations.first().id][0]
    assert refund_v.event == participant


@pytest.mark.django_db
def test_accept_as_donation_links_to_participant(admin_client):
    # Setup: Create a signup with a negative balance
    user = User.objects.create_user(
        username="testuser_donation", email="test_donation@example.com"
    )
    signup = Signup.objects.create(owner=user)
    participant = Participant.objects.create(
        signup_group=signup,
        first_name="John",
        last_name="Doe",
        birthday=date(1990, 1, 1),
        city="Brussels",
    )

    # Manually set a negative balance by creating a validation linked to the participant
    participant_ct = ContentType.objects.get_for_model(Participant)
    from accounts.models import IncomeChoices

    OperationValidation.objects.create(
        content_type=participant_ct,
        object_id=participant.id,
        amount=1000,
        validation_type=IncomeChoices.SIGNUP,
        operation=None,
    )

    from django.contrib.admin.sites import AdminSite

    from signup2026.admin import SignupAdmin

    admin_site = AdminSite()
    signup_admin = SignupAdmin(Signup, admin_site)

    # Mock request
    from django.contrib.messages.storage.base import BaseStorage
    from django.test import RequestFactory

    request = RequestFactory().get(
        reverse("admin:signup2026_signup_change", args=[signup.id])
    )
    storage = BaseStorage(request)
    storage._queued_messages = []
    request._messages = storage
    request.user = User.objects.get(is_superuser=True)

    signup_with_amounts = Signup.objects.with_amounts().get(pk=signup.id)
    signup_with_amounts.calculate_amounts()
    signup_with_amounts = Signup.objects.with_amounts().get(pk=signup.id)

    response = signup_admin.accept_as_donation(request, signup_with_amounts)
    assert response is not None
    assert response.status_code == 302

    # The donation must be linked to the Signup (participant-linked validations
    # count as payments in with_amounts(), which would keep the balance negative).
    signup_ct = ContentType.objects.get_for_model(Signup)
    validations = OperationValidation.objects.filter(
        content_type=signup_ct,
        object_id=signup.id,
        validation_type=IncomeChoices.DONATION,
    )

    assert validations.exists(), "Donation validation should be linked to Signup"
    assert validations.first().amount > 0

    # Converting the excess settles the account.
    assert Signup.objects.with_amounts().get(pk=signup.id).balance == 0
