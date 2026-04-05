import time

from pytest_bdd import given, scenario, then, when


@scenario("../features/submit_bill.feature", "Staff member creates a bill")
def test_my_feature(transactional_db):
    pass


@given("I am logged in as a staff_member", target_fixture="logged_in_staff")
def staff_session(live_server, selenium, staff):
    # Ensure the password change is persisted before attempting login
    staff.set_password("password")
    staff.save()
    from tests.pages.login_page import LoginPage

    login_page = LoginPage(selenium)
    login_page.open_page(live_server.url)
    login_page.login(staff.username, "password")
    login_page.verify_successful_login()
    return selenium


@when('I navigate to the "Create Bill" page')
def navigate_to_bill(live_server, logged_in_staff):
    logged_in_staff.get(live_server.url + "/admin/accounts/bill/add/")
    time.sleep(20)


@given("I fill in the bill details")
def fill_in_bill_details():
    raise NotImplementedError("STEP: And I fill in the bill details")


@given("I submit the bill")
def submit_bill():
    raise NotImplementedError("STEP: And I submit the bill")


@then("I should see a confirmation message")
def should_see_confirmation_message():
    raise NotImplementedError("STEP: Then I should see a confirmation message")


@given('the bill should be in the "Pending" status')
def bill_should_be_pending():
    raise NotImplementedError('STEP: And the bill should be in the "Pending" status')


@given("I should be able to track the status of the bill I created")
def should_be_able_to_track_bill_status():
    raise NotImplementedError(
        "STEP: And I should be able to track the status of the bill I created"
    )


@given("I choose to itemize the bill")
def choose_to_itemize_bill():
    raise NotImplementedError("STEP: And I choose to itemize the bill")


@given("I add multiple items with their respective amounts")
def add_multiple_items_with_amounts():
    raise NotImplementedError(
        "STEP: And I add multiple items with their respective amounts"
    )


@given("the bill should be split into the specified items")
def bill_should_be_split_into_items():
    raise NotImplementedError(
        "STEP: And the bill should be split into the specified items"
    )


@given("I am logged in as an accountant")
def logged_in_as_accountant():
    raise NotImplementedError("STEP: Given I am logged in as an accountant")


@then("I should see a list of all bills")
def should_see_list_of_all_bills():
    raise NotImplementedError("STEP: Then I should see a list of all bills")


@when("I select a bill")
def select_a_bill():
    raise NotImplementedError("STEP: When I select a bill")


@given('I change the status to "Payed-Pending-Transaction"')
def change_status_to_payed_pending_transaction():
    raise NotImplementedError(
        'STEP: And I change the status to "Payed-Pending-Transaction"'
    )


@then("the bill status should be updated")
def bill_status_should_be_updated():
    raise NotImplementedError("STEP: Then the bill status should be updated")


@when("I link the bill to a transaction")
def link_bill_to_transaction():
    raise NotImplementedError("STEP: When I link the bill to a transaction")


@then('the bill status should be "Payed"')
def bill_status_should_be_payed():
    raise NotImplementedError('STEP: Then the bill status should be "Payed"')


@given("I am logged in as an admin")
def logged_in_as_admin():
    raise NotImplementedError("STEP: Given I am logged in as an admin")


@given("I should not be able to change the status of any bill")
def should_not_be_able_to_change_any_bill_status():
    raise NotImplementedError(
        "STEP: And I should not be able to change the status of any bill"
    )


@given("I should not be able to link any bill to a transaction")
def should_not_be_able_to_link_any_bill_to_transaction():
    raise NotImplementedError(
        "STEP: And I should not be able to link any bill to a transaction"
    )
