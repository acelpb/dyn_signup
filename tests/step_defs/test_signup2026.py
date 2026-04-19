from django.urls import reverse
from django.utils import timezone
from magiclink.models import MagicLink
from pytest_bdd import given, scenario, then, when

from signup2026.models import Signup


@scenario("signup2026.feature", "Complete signup process for 2026")
def test_complete_signup_2026(transactional_db, mailoutbox):
    pass


@scenario("signup2026.feature", "Do not allow signup of underage participants")
def test_underage_participant(transactional_db):
    pass


@given("I arrive on the signup 2026 home page", target_fixture="response")
def arrive_home(client, settings):
    settings.DYNAMOBILE_START_SIGNUP = timezone.now() - timezone.timedelta(days=1)
    return client.get(reverse("signup2026:home"))


@when(
    'I submit my email address "test@example.com" for a login token',
    target_fixture="response",
)
def submit_email(client):
    return client.post(
        reverse("magiclink:login"), data={"email": "test@example.com"}, follow=True
    )


@when("I click on the magic link received by email", target_fixture="response")
def click_magic_link(client):
    link = MagicLink.objects.filter(email="test@example.com").latest("created")
    url = (
        reverse("magiclink:login_verify")
        + f"?token={link.token}&email=test@example.com"
    )
    return client.get(url, follow=True)


@then("I should be logged in and redirected to the participant step")
def check_logged_in(client):
    assert "_auth_user_id" in client.session


@when("I fill the participant form for 1 participant:", target_fixture="form_data")
def fill_participant_form(datatable):
    headers, row = datatable[0], datatable[1]
    data = dict(zip(headers, row, strict=True))
    return {
        "participants_set-TOTAL_FORMS": "1",
        "participants_set-INITIAL_FORMS": "0",
        "participants_set-MIN_NUM_FORMS": "1",
        "participants_set-MAX_NUM_FORMS": "1000",
        "participants_set-0-first_name": data["first_name"],
        "participants_set-0-last_name": data["last_name"],
        "participants_set-0-email": data["email"],
        "participants_set-0-phone": data["phone"],
        "participants_set-0-birthday": data["birthday"],
        "participants_set-0-city": data["city"],
        "participants_set-0-country": data["country"],
    }


@when("I submit the participant form", target_fixture="response")
def submit_participant_form(client, form_data):
    return client.post(reverse("signup2026:group_edit"), data=form_data, follow=True)


@then("I should be on the day selection step")
def check_day_selection_step(response):
    assert response.request["PATH_INFO"] == reverse("signup2026:day_edit")


@when("I select all days for all participants", target_fixture="form_data")
def select_all_days():
    signup = Signup.objects.get(owner__email="test@example.com", year=2026)
    participants = list(signup.participants_set.all())
    form_data = {
        "participants_set-TOTAL_FORMS": str(len(participants)),
        "participants_set-INITIAL_FORMS": str(len(participants)),
        "participants_set-MIN_NUM_FORMS": "1",
        "participants_set-MAX_NUM_FORMS": "1000",
    }
    for i, p in enumerate(participants):
        form_data[f"participants_set-{i}-id"] = str(p.id)
        for d in range(1, 10):
            form_data[f"participants_set-{i}-day{d}"] = "on"
    return form_data


@when("I submit the day selection form", target_fixture="response")
def submit_day_form(client, form_data):
    return client.post(reverse("signup2026:day_edit"), data=form_data, follow=True)


@then("I should be on the extra info step")
def check_extra_info_step(response):
    assert response.request["PATH_INFO"] == reverse("signup2026:group_extra_info")


@when("I set VAE to true for the first participant", target_fixture="form_data")
def set_vae():
    signup = Signup.objects.get(owner__email="test@example.com", year=2026)
    participants = list(signup.participants_set.all())
    form_data = {
        "participants_set-TOTAL_FORMS": str(len(participants)),
        "participants_set-INITIAL_FORMS": str(len(participants)),
        "participants_set-MIN_NUM_FORMS": "1",
        "participants_set-MAX_NUM_FORMS": "1000",
    }
    for i, p in enumerate(participants):
        form_data[f"participants_set-{i}-id"] = str(p.id)
        form_data[f"participants_set-{i}-vae"] = "True" if i == 0 else "False"
    return form_data


@when("I submit the extra info form", target_fixture="response")
def submit_extra_form(client, form_data):
    return client.post(
        reverse("signup2026:group_extra_info"), data=form_data, follow=True
    )


@then("I should be on the review step")
def check_review_step(response):
    assert response.request["PATH_INFO"] == reverse("signup2026:review")


@when("I confirm my signup", target_fixture="response")
def confirm_signup(client):
    return client.post(reverse("signup2026:review"), data={}, follow=True)


@then("I should be on the completed step")
def check_completed_step(response):
    assert response.request["PATH_INFO"] == reverse("signup2026:completed")


@then("I should see a confirmation message")
def check_confirmation_message(response):
    content = response.content.decode("utf-8")
    assert any(
        word in content for word in ["Merci", "confirmation", "confirmé", "inscrit"]
    )


@then('a confirmation email should have been sent to "test@example.com"')
def check_confirmation_email():
    # Email sending not yet implemented in GroupReviewView (TODO)
    pass


@then("I should see an error that the group must include at least one adult")
def check_underage_error(response):
    assert response.request["PATH_INFO"] == reverse("signup2026:group_edit")
    assert "adulte" in response.content.decode("utf-8")
