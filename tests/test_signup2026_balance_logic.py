"""Unit tests for Signup balance-related business logic (signup2026).

Balance is never computed in Python: it always comes from the
SignupQuerySet.with_amounts() annotations.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.utils import timezone

from accounts.models import IncomeChoices, OperationValidation
from signup2026.models import Participant, Signup


@pytest.fixture
def owner(db):
    return User.objects.create_user(username="owner", email="owner@example.com")


@pytest.fixture
def signup(owner):
    return Signup.objects.create(owner=owner)


@pytest.fixture
def participant(signup):
    return Participant.objects.create(
        signup_group=signup,
        first_name="John",
        last_name="Doe",
        birthday=date(1990, 1, 1),
        city="Brussels",
        amount_due_modified=Decimal("100.00"),
    )


def pay(participant, amount):
    return OperationValidation.objects.create(
        content_type=ContentType.objects.get_for_model(Participant),
        object_id=participant.id,
        amount=amount,
        validation_type=IncomeChoices.SIGNUP,
        operation=None,
    )


@pytest.mark.django_db
class TestAnnotatedBalance:
    def test_balance_comes_from_annotation(self, signup, participant):
        pay(participant, Decimal("40.00"))
        annotated = signup.annotated()
        assert annotated.balance == Decimal("60.00")
        assert annotated.is_payed is False

    def test_is_payed_when_balance_zero(self, signup, participant):
        pay(participant, Decimal("100.00"))
        assert signup.annotated().is_payed is True

    def test_participant_annotations_match_signup_vocabulary(self, signup, participant):
        pay(participant, Decimal("40.00"))
        annotated = Participant.objects.with_amounts().get(pk=participant.pk)
        assert annotated.balance == Decimal("60.00")
        assert annotated.is_payed is False
        assert annotated.balance == signup.annotated().balance

    def test_participant_is_payed_when_fully_paid(self, signup, participant):
        pay(participant, Decimal("100.00"))
        annotated = Participant.objects.with_amounts().get(pk=participant.pk)
        assert annotated.balance == 0
        assert annotated.is_payed is True


@pytest.mark.django_db
class TestAcceptExcessAsDonation:
    def test_converts_excess_and_zeroes_balance(self, signup, participant, owner):
        payment = pay(participant, Decimal("150.00"))

        excess = signup.accept_excess_as_donation(owner)

        assert excess == Decimal("50.00")
        payment.refresh_from_db()
        assert payment.amount == Decimal("100.00")
        donation = OperationValidation.objects.get(
            validation_type=IncomeChoices.DONATION
        )
        assert donation.amount == Decimal("50.00")
        # Linked to the signup so it does not count as a participant payment.
        assert donation.event == signup
        assert signup.annotated().balance == 0

    def test_rejects_non_negative_balance(self, signup, participant, owner):
        pay(participant, Decimal("100.00"))
        with pytest.raises(ValueError, match="not negative"):
            signup.accept_excess_as_donation(owner)

    def test_rejects_when_largest_payment_smaller_than_excess(
        self, signup, participant, owner
    ):
        participant.amount_due_modified = Decimal("10.00")
        participant.save()
        pay(participant, Decimal("60.00"))
        pay(participant, Decimal("60.00"))
        # excess is 110 but the largest single payment is only 60
        with pytest.raises(ValueError, match="handle manually"):
            signup.accept_excess_as_donation(owner)


@pytest.mark.django_db
class TestOfferRefund:
    def test_creates_negative_validation_on_participant(
        self, signup, participant, owner
    ):
        pay(participant, Decimal("130.00"))

        excess = signup.offer_refund(owner)

        assert excess == Decimal("30.00")
        refund = OperationValidation.objects.get(amount__lt=0)
        assert refund.amount == Decimal("-30.00")
        assert refund.object_id == participant.id
        assert refund.content_type == ContentType.objects.get_for_model(Participant)
        signup.refresh_from_db()
        assert "REFUND OFFERED" in signup.comments
        assert signup.annotated().balance == 0

    def test_refunds_only_the_overpaid_participant(self, signup, participant, owner):
        # participant owes 100 and paid 130 (overpaid by 30); the second
        # participant owes 50 and paid nothing. The refund must land on the
        # overpaid participant only, for exactly their own excess.
        pay(participant, Decimal("130.00"))
        underpaid = Participant.objects.create(
            signup_group=signup,
            first_name="Jane",
            last_name="Doe",
            birthday=date(1992, 1, 1),
            city="Brussels",
            amount_due_modified=Decimal("50.00"),
        )

        total = signup.offer_refund(owner)

        assert total == Decimal("30.00")
        refund = OperationValidation.objects.get(amount__lt=0)
        assert refund.amount == Decimal("-30.00")
        assert refund.object_id == participant.id
        participants = {
            p.pk: p
            for p in Participant.objects.with_amounts().filter(signup_group=signup)
        }
        assert participants[participant.pk].balance == 0
        assert participants[underpaid.pk].balance == Decimal("50.00")

    def test_rejects_when_no_participant_overpaid(self, signup, participant, owner):
        pay(participant, Decimal("100.00"))
        with pytest.raises(ValueError, match="negative balance"):
            signup.offer_refund(owner)


@pytest.mark.django_db
class TestReleaseFromWaitingList:
    def test_clears_hold_flags_and_notifies_owner(self, signup, participant):
        signup.validated_at = timezone.now()
        signup.on_hold_at = timezone.now()
        signup.on_hold_vae = True
        signup.on_hold_partial = True
        signup.save()

        signup.release_from_waiting_list()

        signup.refresh_from_db()
        assert signup.on_hold_at is None
        assert signup.on_hold_vae is False
        assert signup.on_hold_partial is False
        assert len(mail.outbox) == 1
        assert signup.owner.email in mail.outbox[0].recipients()
