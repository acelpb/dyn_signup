from django.urls import reverse
from django.utils import timezone
from pytest_bdd import given, parsers, scenario, then, when

from signup2026.models import ExtraParticipantInfo, Participant, Signup


@scenario(
    "signup2026_followup.feature",
    "Group owner fills the follow-up form for all participants",
)
def test_owner_fills_followup(db):
    pass


@scenario(
    "signup2026_followup.feature",
    "An individual participant only sees their own follow-up form",
)
def test_individual_participant_followup(db):
    pass


@scenario(
    "signup2026_followup.feature",
    "An anonymous user cannot access the follow-up form",
)
def test_anonymous_followup(db):
    pass


@given(
    parsers.parse(
        'a validated 2026 signup owned by "{owner_email}" with participants:'
    ),
    target_fixture="signup",
)
def validated_signup(django_user_model, owner_email, datatable):
    owner = django_user_model.objects.create_user(
        username=owner_email, email=owner_email, password="x"
    )
    signup = Signup.objects.create(owner=owner, year=2026, validated_at=timezone.now())
    headers, *rows = datatable
    for row in rows:
        data = dict(zip(headers, row, strict=True))
        Participant.objects.create(
            signup_group=signup,
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            birthday="1980-01-01",
            city="Namur",
        )
    return signup


@when("the owner opens the follow-up form", target_fixture="response")
def owner_opens(client, signup):
    client.force_login(signup.owner)
    return client.get(reverse("signup2026:followup_extra_info"))


@when(
    parsers.parse('"{email}" opens the follow-up form'),
    target_fixture="response",
)
def participant_opens(client, django_user_model, email):
    user, _ = django_user_model.objects.get_or_create(
        username=email, defaults={"email": email}
    )
    client.force_login(user)
    return client.get(reverse("signup2026:followup_extra_info"))


@when("an anonymous user opens the follow-up form", target_fixture="response")
def anonymous_opens(client):
    return client.get(reverse("signup2026:followup_extra_info"))


@then(parsers.parse("the form should show {count:d} participants"))
def form_shows_participants(response, count):
    assert response.status_code == 200
    assert response.context["formset"].total_form_count() == count


@when(
    parsers.parse(
        'the owner submits the follow-up form choosing July 20 "{choice}", '
        'tandem pilot and car return "{car_return}"'
    ),
    target_fixture="response",
)
def owner_submits(client, signup, choice, car_return):
    extras = list(
        ExtraParticipantInfo.objects.filter(participant__signup_group=signup).order_by(
            "participant_id"
        )
    )
    data = {
        "form-TOTAL_FORMS": str(len(extras)),
        "form-INITIAL_FORMS": str(len(extras)),
        "form-MIN_NUM_FORMS": "0",
        "form-MAX_NUM_FORMS": "1000",
    }
    for i, extra in enumerate(extras):
        data[f"form-{i}-id"] = str(extra.id)
        data[f"form-{i}-july20_loop"] = choice
        data[f"form-{i}-tandem_pilot"] = "on"
        data[f"form-{i}-takes_car_back"] = car_return
    return client.post(
        reverse("signup2026:followup_extra_info"), data=data, follow=True
    )


@then("the answers should be saved for every participant")
def answers_saved(signup):
    extras = ExtraParticipantInfo.objects.filter(participant__signup_group=signup)
    assert extras.count() == signup.participants_set.count()


@then(
    parsers.parse(
        'the answers should record July 20 choice "{choice}" and tandem pilot true'
    )
)
def answers_recorded(signup, choice):
    extras = ExtraParticipantInfo.objects.filter(participant__signup_group=signup)
    assert all(e.july20_loop == choice for e in extras)
    assert all(e.tandem_pilot for e in extras)


@then(parsers.parse('every participant should have car return "{car_return}"'))
def car_return_recorded(signup, car_return):
    participants = signup.participants_set.all()
    assert all(p.takes_car_back == car_return for p in participants)


@then("they should be redirected to the login page")
def redirected_to_login(response):
    assert response.status_code == 302
    assert "login" in response["Location"].lower()
