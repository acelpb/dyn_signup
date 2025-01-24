import time

import pytest
from pytest_bdd import given, scenario, then, when


@scenario("../features/submit_bill.feature", "Staff member creates a bill")
def test_my_feature(transactional_db):
    pass


@given("I am logged in as a staff_member", target_fixture="logged_in_staff")
def staff_session(live_server, selenium, staff):
    staff.set_password("password")
    from tests.pages.login_page import LoginPage
    login_page = LoginPage(selenium)
    login_page.open_page(live_server.url)
    login_page.login(staff.username,"password")
    login_page.verify_successful_login()
    return selenium


@when('I navigate to the "Create Bill" page')
def navigate_to_bill(live_server, logged_in_staff):
    logged_in_staff.get(live_server.url + "/admin/accounts/bill/add/")
    time.sleep(20)

@given("I fill in the bill details")
def step_impl():
    raise NotImplementedError("STEP: And I fill in the bill details")


@given("I submit the bill")
def step_impl():
    raise NotImplementedError("STEP: And I submit the bill")


@then("I should see a confirmation message")
def step_impl():
    raise NotImplementedError("STEP: Then I should see a confirmation message")


@given('the bill should be in the "Pending" status')
def step_impl():
    raise NotImplementedError('STEP: And the bill should be in the "Pending" status')


@given("I should be able to track the status of the bill I created")
def step_impl():
    raise NotImplementedError(
        "STEP: And I should be able to track the status of the bill I created"
    )


@given("I choose to itemize the bill")
def step_impl():
    raise NotImplementedError("STEP: And I choose to itemize the bill")


@given("I add multiple items with their respective amounts")
def step_impl():
    raise NotImplementedError(
        "STEP: And I add multiple items with their respective amounts"
    )


@given("the bill should be split into the specified items")
def step_impl():
    raise NotImplementedError(
        "STEP: And the bill should be split into the specified items"
    )


@given("I am logged in as an accountant")
def step_impl():
    raise NotImplementedError("STEP: Given I am logged in as an accountant")


@then("I should see a list of all bills")
def step_impl():
    raise NotImplementedError("STEP: Then I should see a list of all bills")


@when("I select a bill")
def step_impl():
    raise NotImplementedError("STEP: When I select a bill")


@given('I change the status to "Payed-Pending-Transaction"')
def step_impl():
    raise NotImplementedError(
        'STEP: And I change the status to "Payed-Pending-Transaction"'
    )


@then("the bill status should be updated")
def step_impl():
    raise NotImplementedError("STEP: Then the bill status should be updated")


@when("I link the bill to a transaction")
def step_impl():
    raise NotImplementedError("STEP: When I link the bill to a transaction")


@then('the bill status should be "Payed"')
def step_impl():
    raise NotImplementedError('STEP: Then the bill status should be "Payed"')


@given("I am logged in as an admin")
def step_impl():
    raise NotImplementedError("STEP: Given I am logged in as an admin")


@given("I should not be able to change the status of any bill")
def step_impl():
    raise NotImplementedError(
        "STEP: And I should not be able to change the status of any bill"
    )


@given("I should not be able to link any bill to a transaction")
def step_impl():
    raise NotImplementedError(
        "STEP: And I should not be able to link any bill to a transaction"
    )
