"""
Login Page Class for https://practicetestautomation.com/practice-test-login/
"""
import time

from django.urls import reverse
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from django.conf import settings
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
        self.driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()  # Submit button ID

    def verify_successful_login(self):
        try:
            logout_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            assert logout_button.text.lower() == "déconnexion"
            return logout_button.is_displayed()
        except NoSuchElementException:
            assert False, "Logout button does not exist."