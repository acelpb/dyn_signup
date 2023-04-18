# Created by aborsu at 18/04/23
Feature: User Login
  As a normal user I want to be able to login using a one time password received through email.
  As an admin, I may login using a one time password,
    but I can also decide to use a login/password combination.
  As an admin, I should have the ability to reset my password.

  New users generating a one time password will be automagically added to the list of users.

  TODO: New admins are added manually by an existing admin.
  TODO: Users who have no signup attached to them and no activity since 30 days will be deleted.

  Scenario: A new user
    Given a new visitor
    And arrives on the signup page after starting a signup
    When he submits his email address for a one-shot token
    Then the visitor should have been added to the databae
    And an email with a valid token should be sent out

  Scenario: An admin
    Given an admin
    When the admin arrives at the admin logging page
    Then he has the option to login either with a single use token
    And he has the option to login with a password
    And he has the option to reset his password
