"""Tests for the participant mailing-list sync (newsletter sync button)."""

import pytest
from django.utils import timezone
from model_bakery import baker

from signup2026.models import Participant, Signup


def make_signup(**kwargs):
    defaults = {
        "year": 2026,
        "validated_at": timezone.now(),
        "on_hold_at": None,
        "cancelled_at": None,
    }
    defaults.update(kwargs)
    return baker.make(Signup, **defaults)


@pytest.mark.django_db
def test_active_emails_includes_participants_and_owner():
    signup = make_signup(owner__email="Owner@Example.com")
    baker.make(Participant, signup_group=signup, email="P1@Example.com")
    baker.make(Participant, signup_group=signup, email="p2@example.com")

    assert Participant.active_emails() == {
        "owner@example.com",
        "p1@example.com",
        "p2@example.com",
    }


@pytest.mark.django_db
def test_active_emails_excludes_non_active_signups():
    not_validated = make_signup(validated_at=None, owner__email="a@example.com")
    on_hold = make_signup(on_hold_at=timezone.now(), owner__email="b@example.com")
    cancelled = make_signup(cancelled_at=timezone.now(), owner__email="c@example.com")
    wrong_year = make_signup(year=2025, owner__email="d@example.com")

    for signup, email in (
        (not_validated, "p-a@example.com"),
        (on_hold, "p-b@example.com"),
        (cancelled, "p-c@example.com"),
        (wrong_year, "p-d@example.com"),
    ):
        baker.make(Participant, signup_group=signup, email=email)

    assert Participant.active_emails() == set()


@pytest.mark.django_db
def test_active_emails_skips_empty_emails():
    signup = make_signup(owner__email="owner@example.com")
    baker.make(Participant, signup_group=signup, email="")

    assert Participant.active_emails() == {"owner@example.com"}
