Feature: Waiting list admin 2026
  As an admin managing Dynamobile 2026 registrations
  I want to manage participants on the waiting list
  So that I can unblock participants when spots become available

  Scenario: All participants on hold are displayed
    Given a validated signup on hold exists for "waiting@example.com"
    When I visit the waiting list admin page
    Then I should see the participant from "waiting@example.com"

  Scenario: Admin can unblock a participant from the waiting list
    Given a validated signup on hold exists for "waiting@example.com"
    When I unblock the participant from "waiting@example.com"
    Then the signup for "waiting@example.com" should no longer be on hold
    And the signup amounts should be calculated
    And a confirmation email should be sent to "waiting@example.com"
