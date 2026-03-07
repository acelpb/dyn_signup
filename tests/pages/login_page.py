"""
Login Page Class for https://practicetestautomation.com/practice-test-login/
"""

from django.urls import reverse
from selenium.webdriver.common.by import By


class LoginPage:
    def __init__(self, driver):
        self.driver = driver

    def open_page(self, base_url):
        self.driver.get(base_url + reverse("admin:login"))

    def login(self, username, password):
        self.enter_username(username)
        self.enter_password(password)
        self.click_login()

    def enter_username(self, username):
        self.driver.find_element(By.ID, "id_username").send_keys(
            username
        )  # Username element ID

    def enter_password(self, password):
        self.driver.find_element(By.ID, "id_password").send_keys(
            password
        )  # Password element ID

    def click_login(self):
        self.driver.find_element(
            By.CSS_SELECTOR, "input[type='submit']"
        ).click()  # Submit button ID

    def verify_successful_login(self):
        try:
            # After login, wait until we are no longer on the login page, then
            # look for the logout link in the user tools.
            from django.urls import reverse
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import WebDriverWait

            wait = WebDriverWait(self.driver, 10)

            login_path = reverse("admin:login")
            wait.until(lambda d: not d.current_url.endswith(login_path))

            # Primary check: presence of the admin user tools bar indicates a logged-in state.
            user_tools = wait.until(
                EC.visibility_of_element_located((By.ID, "user-tools"))
            )
            return user_tools.is_displayed()
        except Exception:
            # Fallback to checking the logout link directly
            try:
                from django.urls import reverse

                logout_path = reverse("admin:logout")
                logout_link = self.driver.find_element(
                    By.CSS_SELECTOR, f"a[href^='{logout_path}']"
                )
                return logout_link.is_displayed()
            except Exception:
                # Last resort: raise with current page URL for debugging
                current = self.driver.current_url
                raise AssertionError(
                    f"Login likely failed; could not find user tools or logout link. Current URL: {current}"
                ) from None
