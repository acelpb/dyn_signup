import random

from django.contrib.auth import get_user_model
from django.urls import reverse
from faker import Faker
from model_bakery import baker
from pytest_bdd import scenario, given, when, then, parsers

random
fake = Faker()


def create_formset_post_data(response, new_form_data=None):
    if new_form_data is None:
        new_form_data = []
    csrf_token = response.context["csrf_token"]
    formset = response.context.get("formset") or response.context.get("form")
    prefix_template = formset.empty_form.prefix  # default is 'form-__prefix__'
    # extract initial formset data
    management_form_data = formset.management_form.initial
    form_data_list = formset.initial or []  # this is a list of dict objects
    # add new form data and update management form data
    form_data_list.extend(new_form_data)
    management_form_data["TOTAL_FORMS"] = len(form_data_list)
    # initialize the post data dict...
    post_data = dict(csrf_token=csrf_token)
    # add properly prefixed management form fields
    for key, value in management_form_data.items():
        prefix = prefix_template.replace("__prefix__", "")
        post_data[prefix + key] = value
    # add properly prefixed data form fields
    for index, form_data in enumerate(form_data_list):
        for key, value in form_data.items():
            prefix = prefix_template.replace("__prefix__", f"{index}-")
            post_data[prefix + key] = value
    return post_data


# %%
# %%


@scenario("GroupDetails.feature", "Signup a simple group")
def test_simple_group(transactional_db):
    return


@given(
    parsers.parse("a {logged} visitor on the {page} page"),
    target_fixture="response",
)
def generate_user(logged, page, client):
    visitor = baker.make(get_user_model())
    if logged == "logged-in":
        client.force_login(visitor)
    return client.get(reverse(page))


@given(
    parsers.parse("his group of {n:d} participants"),
    target_fixture="participants",
)
def create_participants(n):
    return baker.prepare("signup2023.Participant", _quantity=n)


@when("submitting his group information", target_fixture="submit_response")
def submit_group(response, participants):
    assert response.status_code == 200
    post_data = create_formset_post_data(
        response,
        [
            {
                key: getattr(particpant, key) or ""
                for key in response.context["form"].empty_form.fields.keys()
                if key == key.lower()
            }
            for particpant in participants
        ],
    )
    return response.client.post(
        response.request["PATH_INFO"], data=post_data, follow=True
    )


@then("he is correctly redirected to the participant_review page")
def check_successful_page_open(submit_response):
    assert not submit_response.context["form"].errors


@then("all participants have been added to the database")
def check_participant(participants):
    from signup2023.models import Participant

    for participant in participants:
        Participant.objects.get(
            first_name=participant.first_name, last_name=participant.last_name
        )
