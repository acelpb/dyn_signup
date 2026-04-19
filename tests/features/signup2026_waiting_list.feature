Feature: Signup 2026 waiting list
  As a user signing up for Dynamobile 2026
  I want to be informed when I am placed on a waiting list
  So that I know my registration is pending

  Scenario: Signup is placed on hold when the participant limit is reached
    Given the participant limit is set to 1
    And an existing validated signup with 1 participant exists
    And I am a new user completing the signup flow for "late@example.com"
    When I confirm my signup
    Then I should be on the completed step
    And my signup should be on hold

  Scenario: Signup is placed on hold when the VAE limit is reached
    Given the VAE participant limit is set to 1
    And an existing validated signup with 1 VAE participant exists
    And I am a new user completing the signup flow for "vae_late@example.com" with VAE
    When I confirm my signup
    Then I should be on the completed step
    And my signup should be on hold for VAE
