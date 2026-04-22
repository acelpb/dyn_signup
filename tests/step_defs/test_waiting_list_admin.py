from django.urls import reverse
from django.utils import timezone
from model_bakery import baker
from pytest_bdd import given, scenario, then, when

from signup2026.models import Participant, Signup


@scenario("waiting_list_admin.feature", "All participants on hold are displayed")
def test_waiting_list_displayed(transactional_db):
    pass


@scenario(
    "waiting_list_admin.feature",
    "Admin can unblock a participant from the waiting list",
)
def test_unblock_participant(transactional_db, mailoutbox):
    pass


@given(
    'a validated signup on hold exists for "waiting@example.com"',
    target_fixture="on_hold_signup",
)
def on_hold_signup(settings):
    settings.DYNAMOBILE_START_SIGNUP = timezone.now() - timezone.timedelta(days=1)
    settings.DYNAMOBILE_START_PARTIAL_SIGNUP = timezone.now() + timezone.timedelta(
        days=30
    )
    owner = baker.make("auth.User", email="waiting@example.com")
    signup = baker.make(
        Signup,
        owner=owner,
        year=2026,
        validated_at=timezone.now(),
        on_hold_at=timezone.now(),
        on_hold_vae=False,
        on_hold_partial=False,
    )
    baker.make(
        Participant,
        signup_group=signup,
        first_name="Jean",
        last_name="Attente",
        birthday=timezone.datetime(1985, 6, 1).date(),
        vae=False,
        day1=True,
        day2=True,
        day3=True,
        day4=True,
        day5=True,
        day6=True,
        day7=True,
        day8=True,
        day9=True,
    )
    return signup


@when("I visit the waiting list admin page", target_fixture="response")
def visit_admin_page(admin_client):
    url = reverse("admin:signup2026_waitinglistparticipant_changelist")
    return admin_client.get(url)


@then('I should see the participant from "waiting@example.com"')
def check_participant_visible(response):
    content = response.content.decode("utf-8")
    assert response.status_code == 200
    assert "Attente" in content


@when('I unblock the participant from "waiting@example.com"', target_fixture="response")
def unblock_participant(admin_client, on_hold_signup):
    participant = on_hold_signup.participants_set.first()
    url = reverse("admin:signup2026_waitinglistparticipant_changelist")
    return admin_client.post(
        url,
        {
            "action": "unblock_participant",
            "_selected_action": [str(participant.id)],
            "select_across": "0",
            "index": "0",
        },
        follow=True,
    )


@then('the signup for "waiting@example.com" should no longer be on hold')
def check_not_on_hold(on_hold_signup):
    on_hold_signup.refresh_from_db()
    assert on_hold_signup.on_hold_at is None
    assert on_hold_signup.on_hold_vae is False
    assert on_hold_signup.on_hold_partial is False


@then("the signup amounts should be calculated")
def check_amounts_calculated(on_hold_signup):
    participant = on_hold_signup.participants_set.first()
    participant.refresh_from_db()
    assert participant.amount_due_calculated is not None
    assert participant.amount_due_calculated > 0


@then('a confirmation email should be sent to "waiting@example.com"')
def check_email_sent(mailoutbox):
    assert any("waiting@example.com" in m.to for m in mailoutbox)
