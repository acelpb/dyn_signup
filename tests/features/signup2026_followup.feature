Feature: Signup 2026 follow-up extra info form
  As a registered participant of Dynamobile 2026
  I want to fill in a follow-up form after my registration
  So that the organisers can prepare reservations and the July 20 loops

  Scenario: Group owner fills the follow-up form for all participants
    Given a validated 2026 signup owned by "owner@example.com" with participants:
      | first_name | last_name | email             |
      | Owner      | Boss      | owner@example.com |
      | Kid        | Boss      |                   |
    When the owner opens the follow-up form
    Then the form should show 2 participants
    And the July 20 choice should not offer a blank option
    When the owner submits the follow-up form choosing July 20 "option1", tandem pilot, car return "brussels" and lodging on July 16
    Then the answers should be saved for every participant
    And the answers should record July 20 choice "option1" and tandem pilot true
    And every participant should have car return "brussels"
    And every participant should be lodging on July 16

  Scenario: An individual participant only sees their own follow-up form
    Given a validated 2026 signup owned by "owner@example.com" with participants:
      | first_name | last_name | email              |
      | Owner      | Boss      | owner@example.com  |
      | Member     | Friend    | member@example.com |
    When "member@example.com" opens the follow-up form
    Then the form should show 1 participants

  Scenario: The form becomes read-only 10 days before departure
    Given the departure is in 5 days
    And a validated 2026 signup owned by "owner@example.com" with participants:
      | first_name | last_name | email             |
      | Owner      | Boss      | owner@example.com |
    When the owner opens the follow-up form
    Then the form should be read-only
    And the form should show a message to contact the organisers

  Scenario: Volunteer roles are hidden for minor participants
    Given a validated 2026 signup owned by "owner@example.com" with participants:
      | first_name | last_name | email             | birthday   |
      | Owner      | Boss      | owner@example.com | 1980-01-01 |
      | Kid        | Boss      |                   | 2015-01-01 |
    When the owner opens the follow-up form
    Then the volunteer roles should be shown for "Owner"
    And the volunteer roles should be hidden for "Kid"

  Scenario: An anonymous user cannot access the follow-up form
    When an anonymous user opens the follow-up form
    Then they should be redirected to the login page
