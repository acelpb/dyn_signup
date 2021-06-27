import pytest
from django.conf import settings
from model_bakery import baker
from pytest_bdd import scenario, given, when, then, parsers

from signup.models import Signup


@pytest.mark.django_db
@scenario('signup.feature', 'Simple Signup')
def test_signup():
    pass


@pytest.mark.django_db
@scenario('signup.feature', 'Max capacity reached')
def test_max_participants_reached():
    pass


@given("a user", target_fixture="user")
def create_user():
    return baker.make(settings.AUTH_USER_MODEL)


@given("a ballad", target_fixture="ballad")
def create_ballad():
    return create_params_ballad(max_participants=25)


@given(parsers.cfparse("a ballad with max {max_participants:d} participants"),
       target_fixture="ballad")
def create_params_ballad(max_participants):
    return baker.make("signup.Ballad", max_participants=max_participants)


@when(parsers.cfparse("user submits {x:d} participants"))
def submit_barticipants(x, user, ballad, client):
    client.post()
    from signup.forms import MultiParticipantForm
    signup = Signup.objects.create(user=user)
    form = MultiParticipantForm(initial=[
        el.__dict__ for el in baker.prepare("signup.Participant", x, ballad=ballad, signup=signup)
    ])
    if form.is_valid():
        form.save()
    else:
        print(form.errors)
        assert False


@then(parsers.cfparse("the total count of participants for the ballad should be {x:d}"))
def check_total_participants(x, ballad):
    assert ballad.participant_set.count() == x


@then(parsers.cfparse("the user is linked to {x:d} participants"))
def check_user(x, user):
    assert Signup.objects.get(user=user).participant_set.count() == x
