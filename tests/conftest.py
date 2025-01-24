import pytest
from django.conf import settings
from model_bakery import baker
from pytest_bdd import given
import pytest



@given(name="a participant", target_fixture="participant")
def participant():
    email = baker.random_gen.gen_email()
    return baker.make(settings.AUTH_USER_MODEL, email=email)


@given(name="an admin", target_fixture="admin")
def admin(admin_user):
    return admin_user


@pytest.fixture(name="staff")
def staff(django_user_model):
    staff_user = django_user_model.objects.create_user(username="staff", password="something")
    staff_user.is_staff = True
    staff_user.save()
    return staff_user

@pytest.fixture
def selenium(selenium):
    selenium.implicitly_wait(10)
    selenium.maximize_window()
    return selenium


@pytest.fixture(autouse=True)
def use_dummy_cache_backend(settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        }
    }
    settings.DEBUG = True
    settings.STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    settings.MIDDLEWARE = [
        x for x in settings.MIDDLEWARE
        if x != "whitenoise.middleware.WhiteNoiseMiddleware"
    ]
