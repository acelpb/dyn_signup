import time

import pytest
from tests.pages.login_page import LoginPage


@pytest.mark.login
def test_login_functionality(selenium, live_server, admin_user):
    """
    Test the login functionality of the Practice Test Automation website
    """
    selenium.implicitly_wait(10)
    login_page = LoginPage(selenium)

    # Open Page
    login_page.open_page(live_server.url)

    # Enter Username and Password
    login_page.enter_username("admin")
    login_page.enter_password("password")

    # Click Login
    login_page.click_login()

    # Verify Successful Login by checking the presence of a logout button
    assert login_page.verify_successful_login()
