"""
Tests to verify that all admin pages load without errors.
Grouped by Django application.
"""

import datetime
from decimal import Decimal

import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from model_bakery import baker

from accounts.models import IncomeChoices, OperationValidation

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get(client, url):
    response = client.get(url)
    assert response.status_code == 200, f"GET {url} returned {response.status_code}"
    return response


# ===========================================================================
# accounts app
# ===========================================================================


@pytest.mark.django_db
class TestAccountsAdminPages:
    @pytest.fixture(autouse=True)
    def login_as_admin(self, client, admin_user):
        client.force_login(admin_user)
        self.client = client

    # --- Account ---

    def test_account_changelist(self):
        get(self.client, reverse("admin:accounts_account_changelist"))

    def test_account_add(self):
        get(self.client, reverse("admin:accounts_account_add"))

    def test_account_change(self):
        account = baker.make("accounts.Account")
        get(self.client, reverse("admin:accounts_account_change", args=[account.pk]))

    # --- Operation ---

    def test_operation_changelist(self):
        get(self.client, reverse("admin:accounts_operation_changelist"))

    def test_operation_add(self):
        get(self.client, reverse("admin:accounts_operation_add"))

    def test_operation_change(self):
        operation = baker.make("accounts.Operation")
        get(
            self.client, reverse("admin:accounts_operation_change", args=[operation.pk])
        )

    # --- OperationValidation ---

    def test_operationvalidation_changelist(self):
        get(self.client, reverse("admin:accounts_operationvalidation_changelist"))

    def test_operationvalidation_add(self):
        get(self.client, reverse("admin:accounts_operationvalidation_add"))

    def test_operationvalidation_change(self):
        ov = baker.make("accounts.OperationValidation")
        get(
            self.client,
            reverse("admin:accounts_operationvalidation_change", args=[ov.pk]),
        )

    # --- Bill ---

    def test_bill_changelist(self):
        get(self.client, reverse("admin:accounts_bill_changelist"))

    def test_bill_add(self):
        get(self.client, reverse("admin:accounts_bill_add"))

    def test_bill_change(self):
        bill = baker.make("accounts.Bill")
        get(self.client, reverse("admin:accounts_bill_change", args=[bill.pk]))

    # --- ExpenseReport ---

    def test_expensereport_changelist(self):
        get(self.client, reverse("admin:accounts_expensereport_changelist"))

    def test_expensereport_add(self):
        get(self.client, reverse("admin:accounts_expensereport_add"))

    def test_expensereport_change(self, admin_user):
        report = baker.make(
            "accounts.ExpenseReport",
            beneficiary=admin_user,
            submitted_date=datetime.date.today(),
            iban="BE71096123456769",
        )
        get(
            self.client,
            reverse("admin:accounts_expensereport_change", args=[report.pk]),
        )


# ===========================================================================
# signup2026 app
# ===========================================================================


@pytest.mark.django_db
class TestSignup2026AdminPages:
    @pytest.fixture(autouse=True)
    def login_as_admin(self, client, admin_user):
        client.force_login(admin_user)
        self.client = client

    def _make_signup(self, owner=None):
        if owner is None:
            owner = baker.make("auth.User")
        return baker.make("signup2026.Signup", owner=owner, year=2026)

    def _make_participant(self, signup=None):
        if signup is None:
            signup = self._make_signup()
        return baker.make(
            "signup2026.Participant",
            signup_group=signup,
            birthday=datetime.date(1990, 1, 1),
        )

    # --- Signup ---

    def test_signup_changelist(self):
        get(self.client, reverse("admin:signup2026_signup_changelist"))

    def test_signup_add(self):
        get(self.client, reverse("admin:signup2026_signup_add"))

    def test_signup_change(self):
        signup = self._make_signup()
        get(self.client, reverse("admin:signup2026_signup_change", args=[signup.pk]))

    # --- Participant ---

    def test_participant_changelist(self):
        get(self.client, reverse("admin:signup2026_participant_changelist"))

    def test_participant_change(self):
        participant = self._make_participant()
        get(
            self.client,
            reverse("admin:signup2026_participant_change", args=[participant.pk]),
        )

    # --- WaitingListParticipant ---

    def test_waitinglistparticipant_changelist(self):
        get(self.client, reverse("admin:signup2026_waitinglistparticipant_changelist"))

    # --- ExtraParticipantInfo ---

    def test_extraparticipantinfo_changelist(self):
        get(self.client, reverse("admin:signup2026_extraparticipantinfo_changelist"))

    def test_extraparticipantinfo_add(self):
        get(self.client, reverse("admin:signup2026_extraparticipantinfo_add"))

    def test_extraparticipantinfo_change(self):
        participant = self._make_participant()
        extra = baker.make("signup2026.ExtraParticipantInfo", participant=participant)
        get(
            self.client,
            reverse("admin:signup2026_extraparticipantinfo_change", args=[extra.pk]),
        )


# ===========================================================================
# Operation → Signup2026 linking
# ===========================================================================


@pytest.mark.django_db
class TestOperationLinkToSignup2026:
    """
    Given a signup2026.Signup with id=55 and an Operation with communication="55"
    that has no OperationValidation yet:
      - the admin changelist shows a button to link the operation to that signup
      - clicking the link allocates the operation amount across unpaid participants
      - any remainder is recorded as a donation against the signup itself
    """

    @pytest.fixture(autouse=True)
    def login_as_admin(self, client, admin_user):
        client.force_login(admin_user)
        self.client = client

    def _make_signup(self):
        owner = baker.make("auth.User")
        return baker.make("signup2026.Signup", id=55, owner=owner, year=2026)

    def _make_participant(self, signup, amount_due):
        return baker.make(
            "signup2026.Participant",
            signup_group=signup,
            birthday=datetime.date(1990, 1, 1),
            amount_due_calculated=Decimal(str(amount_due)),
        )

    def _add_payment(self, participant, amount):
        ct = ContentType.objects.get_for_model(participant)
        baker.make(
            "accounts.OperationValidation",
            content_type=ct,
            object_id=participant.id,
            amount=Decimal(str(amount)),
        )

    def _make_operation(self, signup_id, amount):
        return baker.make(
            "accounts.Operation",
            communication=str(signup_id),
            year=2026,
            amount=Decimal(str(amount)),
        )

    def test_changelist_shows_link_button_for_signup2026(self):
        signup = self._make_signup()
        self._make_operation(signup.id, 200)

        response = get(self.client, reverse("admin:accounts_operation_changelist"))
        assert f"Link to #{signup.id}" in response.content.decode()

    def test_link_creates_operation_validations_per_participant(self):
        """
        Operation amount 200, two participants owing 100 each (p2 has paid 50 already).
        Expect two OperationValidations of 100 each with type SIGNUP, no donation.
        """
        signup = self._make_signup()
        p1 = self._make_participant(signup, amount_due=100)
        p2 = self._make_participant(signup, amount_due=150)
        self._add_payment(p2, 50)
        operation = self._make_operation(signup.id, 200)

        url = reverse(
            "admin:accounts_operation_link_to_signup2026",
            args=[operation.id, signup.id],
        )
        response = self.client.get(url)
        assert response.status_code == 302

        validations = OperationValidation.objects.filter(operation=operation)
        assert validations.count() == 2

        ct = ContentType.objects.get_for_model(p1)
        v1 = validations.get(content_type=ct, object_id=p1.id)
        assert v1.amount == Decimal("100.00")
        assert v1.validation_type == IncomeChoices.SIGNUP

        v2 = validations.get(content_type=ct, object_id=p2.id)
        assert v2.amount == Decimal("100.00")
        assert v2.validation_type == IncomeChoices.SIGNUP

    def test_link_creates_donation_for_excess_amount(self):
        """
        Operation amount 150, one participant owing 100.
        Expect one SIGNUP validation of 100 and one DONATION of 50 against the signup.
        """
        signup = self._make_signup()
        p1 = self._make_participant(signup, amount_due=100)
        operation = self._make_operation(signup.id, 150)

        url = reverse(
            "admin:accounts_operation_link_to_signup2026",
            args=[operation.id, signup.id],
        )
        self.client.get(url)

        validations = OperationValidation.objects.filter(operation=operation)
        assert validations.count() == 2

        ct_participant = ContentType.objects.get_for_model(p1)
        v1 = validations.get(content_type=ct_participant, object_id=p1.id)
        assert v1.amount == Decimal("100.00")
        assert v1.validation_type == IncomeChoices.SIGNUP

        signup_ct = ContentType.objects.get_for_model(signup)
        donation = validations.get(content_type=signup_ct, object_id=signup.id)
        assert donation.amount == Decimal("50.00")
        assert donation.validation_type == IncomeChoices.DONATION

    def test_link_sends_payment_confirmation_when_fully_paid(self, mailoutbox):
        """When linking makes the signup fully paid, a confirmation email is sent."""
        from django.utils import timezone

        owner = baker.make("auth.User", email="owner@example.com")
        signup = baker.make(
            "signup2026.Signup",
            id=55,
            owner=owner,
            year=2026,
            validated_at=timezone.now(),
        )
        self._make_participant(signup, amount_due=100)
        operation = self._make_operation(signup.id, 100)

        url = reverse(
            "admin:accounts_operation_link_to_signup2026",
            args=[operation.id, signup.id],
        )
        self.client.get(url)

        assert len(mailoutbox) == 1
        assert "owner@example.com" in mailoutbox[0].to

        signup.refresh_from_db()
        assert signup.payment_confirmation_sent_at is not None

    def test_link_does_not_send_confirmation_when_not_fully_paid(self, mailoutbox):
        """When the operation only partially covers the dues, no confirmation is sent."""
        from django.utils import timezone

        owner = baker.make("auth.User")
        signup = baker.make(
            "signup2026.Signup",
            id=55,
            owner=owner,
            year=2026,
            validated_at=timezone.now(),
        )
        self._make_participant(signup, amount_due=200)
        operation = self._make_operation(signup.id, 100)

        url = reverse(
            "admin:accounts_operation_link_to_signup2026",
            args=[operation.id, signup.id],
        )
        self.client.get(url)

        assert len(mailoutbox) == 0
        signup.refresh_from_db()
        assert signup.payment_confirmation_sent_at is None


# ===========================================================================
# Signup2026 admin — manual payment confirmation button
# ===========================================================================


@pytest.mark.django_db
class TestSignup2026PaymentConfirmationButton:
    @pytest.fixture(autouse=True)
    def login_as_admin(self, client, admin_user):
        client.force_login(admin_user)
        self.client = client

    def test_send_payment_confirmation_action_sends_email_and_sets_timestamp(
        self, mailoutbox
    ):
        """The change-view action sends the confirmation mail and sets the timestamp."""
        from django.utils import timezone

        owner = baker.make("auth.User", email="user@example.com")
        signup = baker.make(
            "signup2026.Signup",
            owner=owner,
            year=2026,
            validated_at=timezone.now(),
            payment_confirmation_sent_at=None,
        )

        url = reverse(
            "admin:signup2026_signup_actions",
            kwargs={"pk": signup.pk, "tool": "send_payment_confirmation"},
        )
        response = self.client.post(url)
        assert response.status_code == 302

        assert len(mailoutbox) == 1
        assert "user@example.com" in mailoutbox[0].to

        signup.refresh_from_db()
        assert signup.payment_confirmation_sent_at is not None

    def test_send_payment_confirmation_resets_timestamp(self, mailoutbox):
        """Triggering the action again resets payment_confirmation_sent_at to now."""
        from django.utils import timezone

        earlier = timezone.now() - timezone.timedelta(days=5)
        owner = baker.make("auth.User", email="user@example.com")
        signup = baker.make(
            "signup2026.Signup",
            owner=owner,
            year=2026,
            validated_at=timezone.now(),
            payment_confirmation_sent_at=earlier,
        )

        url = reverse(
            "admin:signup2026_signup_actions",
            kwargs={"pk": signup.pk, "tool": "send_payment_confirmation"},
        )
        self.client.post(url)

        assert len(mailoutbox) == 1
        signup.refresh_from_db()
        assert signup.payment_confirmation_sent_at > earlier
