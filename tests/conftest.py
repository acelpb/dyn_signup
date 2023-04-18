from pytest_bdd import given
from model_bakery import baker
from django.conf import settings


@given("a new visitor", target_fixture="visitor")
def visitor():
    email = baker.random_gen.gen_email()
    return baker.prepare(settings.AUTH_USER_MODEL, email=email)


@given("an admin", target_fixture="admin")
def created_admin():
    return baker.make(settings.AUTH_USER_MODEL, is_superuser=True)
