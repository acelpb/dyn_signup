from pytest_bdd import scenario, given, when, then, parsers
import pytest
from django.conf import settings
from model_bakery import baker
from pytest_bdd import scenario, given, when, then, parsers

from signup.models import Signup


@pytest.mark.django_db
@scenario('signup.feature', 'Simple Signup')
def test_publish():
    pass


@given("a user", target_fixture="user")
def create_user():
    return baker.make(settings.AUTH_USER_MODEL)


@given("a ballad", target_fixture="ballad")
def create_ballad():
    return baker.make("signup.Ballad")


@when(parsers.cfparse("user submits {x:d} participants"))
def submit_barticipants(x, user, ballad):
    signup = Signup.objects.create(user=user)
    baker.make("signup.Participant", x, ballad=ballad, signup=signup)


@then(parsers.cfparse("the total count of participants for the ballad should be {x:d}"))
def check_total_participants(x, ballad):
    assert ballad.participant_set.count() == x


@then(parsers.cfparse("the user is linked to {x:d} participants"))
def check_user(x, user):
    assert Signup.objects.get(user=user).participant_set.count() == x
