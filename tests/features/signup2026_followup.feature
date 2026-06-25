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
    When the owner submits the follow-up form choosing July 20 "option1", tandem pilot and car return "brussels"
    Then the answers should be saved for every participant
    And the answers should record July 20 choice "option1" and tandem pilot true
    And every participant should have car return "brussels"

  Scenario: An individual participant only sees their own follow-up form
    Given a validated 2026 signup owned by "owner@example.com" with participants:
      | first_name | last_name | email              |
      | Owner      | Boss      | owner@example.com  |
      | Member     | Friend    | member@example.com |
    When "member@example.com" opens the follow-up form
    Then the form should show 1 participants

  Scenario: An anonymous user cannot access the follow-up form
    When an anonymous user opens the follow-up form
    Then they should be redirected to the login page
