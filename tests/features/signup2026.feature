Feature: Signup 2026
  As a new user
  I want to log in and complete my signup for Dynamobile 2026
  So that I am registered for the event

  Scenario: Complete signup process for 2026
    Given I arrive on the signup 2026 home page
    When I submit my email address "test@example.com" for a login token
    And I click on the magic link received by email
    Then I should be logged in and redirected to the participant step

    When I fill the participant form for 1 participant:
      | first_name | last_name | email            | phone      | birthday   | city  | country  |
      | Jean       | Dupont    | jean@example.com | 0470123456 | 1980-05-15 | Namur | Belgique |
    And I submit the participant form
    Then I should be on the day selection step

    When I select all days for all participants
    And I submit the day selection form
    Then I should be on the extra info step

    When I set VAE to true for the first participant
    And I submit the extra info form
    Then I should be on the review step

    When I confirm my signup
    Then I should be on the completed step
    And I should see a confirmation message
    And a confirmation email should have been sent to "test@example.com"

  Scenario: Do not allow signup of underage participants
    Given I arrive on the signup 2026 home page
    When I submit my email address "test@example.com" for a login token
    And I click on the magic link received by email
    Then I should be logged in and redirected to the participant step

    When I fill the participant form for 1 participant:
      | first_name | last_name | email            | phone      | birthday   | city  | country  |
      | Jean       | Dupont    | jean@example.com | 0470123456 | 2025-05-15 | Namur | Belgique |
    And I submit the participant form
    Then I should see an error that the group must include at least one adult

  Scenario: Day selection step has a back button to the participant step
    Given I arrive on the signup 2026 home page
    When I submit my email address "test@example.com" for a login token
    And I click on the magic link received by email
    Then I should be logged in and redirected to the participant step

    When I fill the participant form for 1 participant:
      | first_name | last_name | email            | phone      | birthday   | city  | country  |
      | Jean       | Dupont    | jean@example.com | 0470123456 | 1980-05-15 | Namur | Belgique |
    And I submit the participant form
    Then I should be on the day selection step
    And I should see a back button to the participant step

  Scenario: Extra info step has a back button and includes the new fields
    Given I arrive on the signup 2026 home page
    When I submit my email address "test@example.com" for a login token
    And I click on the magic link received by email
    Then I should be logged in and redirected to the participant step

    When I fill the participant form for 1 participant:
      | first_name | last_name | email            | phone      | birthday   | city  | country  |
      | Jean       | Dupont    | jean@example.com | 0470123456 | 1980-05-15 | Namur | Belgique |
    And I submit the participant form
    Then I should be on the day selection step

    When I select all days for all participants
    And I submit the day selection form
    Then I should be on the extra info step
    And I should see a back button to the participant step
    And I should see the takes_car_back and extra_activities fields

  Scenario: Require participants signup with a VAE (electric bike) to read and close a pop up window that
