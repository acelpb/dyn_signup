from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from pytest_bdd import scenario, given, when, then


@scenario("login.feature", "A new user")
def test_login(transactional_db):
    return


@scenario("login.feature", "An admin")
def test_admin_has_choice(transactional_db):
    return


@given("arrives on the signup page after starting a signup", target_fixture="response")
def get_login_page(client):
    return client.get(reverse("group_edit"), follow=True)


@when("he submits his email address for a one-shot token")
def submit_login(visitor, response):
    response = response.client.post(
        response.request["PATH_INFO"], data={"email": visitor.email}
    )
    assert response.status_code == 302


@then("the visitor should have been added to the databae")
def check_exists(visitor):
    assert get_user_model().objects.get(username=visitor.email.lower())


@then("an email with a valid token should be sent out")
def check_email(visitor):
    assert len(mail.outbox) == 1
    from magiclink.models import MagicLink

    token = MagicLink.objects.get(email=visitor.email.lower()).token
    assert token in mail.outbox[0].body


@when("the admin arrives at the admin logging page", target_fixture="response")
def open_admin_login(admin, client):
    return client.get(reverse("admin:login"))


@then("he has the option to login either with a single use token")
def check_can_login_token(response):
    assert b'<a href="/auth/login/">' in response.content


@then("he has the option to login with a password")
def check_can_login_password(response):
    from django.contrib.admin.forms import AdminAuthenticationForm

    assert isinstance(response.context["form"], AdminAuthenticationForm)
    assert b'form action="/admin/login/" method="post"' in response.content
    assert b'<input type="submit"' in response.content


@then("he has the option to reset his password")
def check_can_reset_password(response):
    assert b'<a href="/admin/password_reset/">' in response.content
