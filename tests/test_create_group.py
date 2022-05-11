from datetime import timedelta
from pathlib import Path

from django.core import mail
from django.urls import reverse
from django.utils import timezone
from pytest_bdd import scenario, given, when, then, parsers
from pytest_django.asserts import assertRedirects

from signup2022.models import Signup, Participant


@scenario('create_group.feature', 'Simple Signup')
def test_signup():
    pass


@given("signup is open")
def signup_is_open(settings):
    settings.DYNAMOBILE_START_SIGNUP = timezone.now() - timedelta(days=1)


@given("a visitor", target_fixture="visitor")
def create_test_user(django_user_model):
    return django_user_model.objects.create(username="test", email='test@test.com', password="something")


@given(parsers.re(r"a group with (?P<adults>\d+) adult participant"),
       converters=dict(start=int),
       target_fixture="group")
def create_group_of_participants(adults, visitor):
    group = Signup.objects.create(owner=visitor)
    Participant.objects.create(
        signup_group=group,
        first_name='Augustin',
        last_name='Borsu',
        email='a.borsu@test.com',
        birthday='1988-05-09',
        city='Schaerbeek',
        country='Belgique',
        vae=False,
    )
    return group


@when("the visitor submits his group for a full participation", target_fixture='response')
def submit_participation(visitor, client):
    client.force_login(visitor)
    return client.post(reverse("participant_review"))


@then("the group is validated and a bill is created")
def check_group_and_bill(visitor, response):
    assertRedirects(response, reverse('day_edit'), target_status_code=302)
    visitor.refresh_from_db()
    assert visitor.signup.validated_at is not None
    assert visitor.signup.bill is not None


@then("an email is sent with the amount to be paid")
def check_email(visitor, settings):
    assert len(mail.outbox) == 1
    html_content = next(
        (_[0] for _ in mail.outbox[0].alternatives if _[1] == 'text/html'),
        None,
    )
    assert f"{visitor.signup.bill.amount:2}€".replace(".", ',') in html_content
