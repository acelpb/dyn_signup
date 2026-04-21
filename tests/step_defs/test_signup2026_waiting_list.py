from django.urls import reverse
from django.utils import timezone
from magiclink.models import MagicLink
from model_bakery import baker
from pytest_bdd import given, scenario, then, when

from signup2026.models import Participant, Signup


@scenario(
    "signup2026_waiting_list.feature",
    "Signup is placed on hold when the participant limit is reached",
)
def test_on_hold_participant_limit(transactional_db):
    pass


@scenario(
    "signup2026_waiting_list.feature",
    "Signup is placed on hold when the VAE limit is reached",
)
def test_on_hold_vae_limit(transactional_db):
    pass


# --- Background / setup steps ---


@given("the participant limit is set to 1")
def set_participant_limit(settings):
    settings.DYNAMOBILE_START_SIGNUP = timezone.now() - timezone.timedelta(days=1)
    settings.DYNAMOBILE_START_PARTIAL_SIGNUP = timezone.now() + timezone.timedelta(
        days=30
    )
    settings.DYNAMOBILE_MAX_PARTICIPANTS = 1
    settings.DYNAMOBILE_MAX_VAE_PARTICIPANTS = 20


@given("the VAE participant limit is set to 1")
def set_vae_limit(settings):
    settings.DYNAMOBILE_START_SIGNUP = timezone.now() - timezone.timedelta(days=1)
    settings.DYNAMOBILE_START_PARTIAL_SIGNUP = timezone.now() + timezone.timedelta(
        days=30
    )
    settings.DYNAMOBILE_MAX_PARTICIPANTS = 120
    settings.DYNAMOBILE_MAX_VAE_PARTICIPANTS = 1


@given("an existing validated signup with 1 participant exists")
def existing_validated_signup():
    owner = baker.make("auth.User", email="existing@example.com")
    signup = baker.make(
        Signup, owner=owner, year=2026, validated_at=timezone.now(), on_hold_at=None
    )
    baker.make(
        Participant,
        signup_group=signup,
        birthday=timezone.datetime(1985, 1, 1).date(),
        vae=False,
    )


@given("an existing validated signup with 1 VAE participant exists")
def existing_validated_vae_signup():
    owner = baker.make("auth.User", email="existing_vae@example.com")
    signup = baker.make(
        Signup, owner=owner, year=2026, validated_at=timezone.now(), on_hold_at=None
    )
    baker.make(
        Participant,
        signup_group=signup,
        birthday=timezone.datetime(1985, 1, 1).date(),
        vae=True,
    )


# --- New user flow steps ---


@given('I am a new user completing the signup flow for "late@example.com"')
def new_user_flow(client):
    _complete_flow(client, email="late@example.com", vae=False)


@given('I am a new user completing the signup flow for "vae_late@example.com" with VAE')
def new_user_vae_flow(client):
    _complete_flow(client, email="vae_late@example.com", vae=True)


def _complete_flow(client, email, vae):
    # Login via magic link
    client.post(reverse("magiclink:login"), data={"email": email}, follow=True)
    link = MagicLink.objects.filter(email=email).latest("created")
    url = reverse("magiclink:login_verify") + f"?token={link.token}&email={email}"
    client.get(url, follow=True)

    # Create participant
    participant_data = {
        "participants_set-TOTAL_FORMS": "1",
        "participants_set-INITIAL_FORMS": "0",
        "participants_set-MIN_NUM_FORMS": "1",
        "participants_set-MAX_NUM_FORMS": "1000",
        "participants_set-0-first_name": "Test",
        "participants_set-0-last_name": "User",
        "participants_set-0-email": email,
        "participants_set-0-phone": "0470000000",
        "participants_set-0-birthday": "1990-06-01",
        "participants_set-0-city": "Bruxelles",
        "participants_set-0-country": "Belgique",
    }
    client.post(reverse("signup2026:group_edit"), data=participant_data, follow=True)

    # Select all days
    signup = Signup.objects.get(owner__email=email, year=2026)
    participants = list(signup.participants_set.all())
    day_data = {
        "participants_set-TOTAL_FORMS": str(len(participants)),
        "participants_set-INITIAL_FORMS": str(len(participants)),
        "participants_set-MIN_NUM_FORMS": "1",
        "participants_set-MAX_NUM_FORMS": "1000",
    }
    for i, p in enumerate(participants):
        day_data[f"participants_set-{i}-id"] = str(p.id)
        for d in range(1, 10):
            day_data[f"participants_set-{i}-day{d}"] = "on"
    client.post(reverse("signup2026:day_edit"), data=day_data, follow=True)

    # Extra info (VAE)
    extra_data = {
        "participants_set-TOTAL_FORMS": str(len(participants)),
        "participants_set-INITIAL_FORMS": str(len(participants)),
        "participants_set-MIN_NUM_FORMS": "1",
        "participants_set-MAX_NUM_FORMS": "1000",
    }
    if vae:
        extra_data["vae_popup_confirmed"] = "true"
    for i, p in enumerate(participants):
        extra_data[f"participants_set-{i}-id"] = str(p.id)
        extra_data[f"participants_set-{i}-vae"] = "True" if vae else "False"
        extra_data[f"participants_set-{i}-takes_car_back"] = "no"
    client.post(reverse("signup2026:group_extra_info"), data=extra_data, follow=True)


@when("I confirm my signup", target_fixture="response")
def confirm_signup(client):
    return client.post(reverse("signup2026:review"), data={}, follow=True)


@then("I should be on the completed step")
def check_completed_step(response):
    assert response.request["PATH_INFO"] == reverse("signup2026:completed")


@then("my signup should be on hold")
def check_on_hold(client):
    signup = Signup.objects.get(
        owner=client.session["_auth_user_id"] and _get_user(client), year=2026
    )
    assert signup.on_hold_at is not None


@then("my signup should be on hold for VAE")
def check_on_hold_vae(client):
    signup = Signup.objects.get(owner=_get_user(client), year=2026)
    assert signup.on_hold_at is not None
    assert signup.on_hold_vae is True


def _get_user(client):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user_id = client.session["_auth_user_id"]
    return User.objects.get(pk=user_id)
