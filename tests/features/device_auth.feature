Feature: Device authorization for API tokens
  As the treasurer
  I want my LLM assistant to request its own API token
  So that I can approve it in the app instead of sharing a secret by hand

  Scenario: An assistant obtains a token approved by the treasurer
    Given an assistant that started a device authorization
    Then polling for the token reports pending
    When the treasurer approves the request on the verification page
    Then polling for the token returns a token
    And the token can be used to upload a bill
    And polling again is rejected

  Scenario: The treasurer denies the request
    Given an assistant that started a device authorization
    When the treasurer denies the request on the verification page
    Then polling for the token reports the code as invalid

  Scenario: An expired device authorization yields no token
    Given an assistant that started a device authorization
    And the device authorization has expired
    Then polling for the token reports the code as expired

  Scenario: A regular user cannot approve a device authorization
    Given an assistant that started a device authorization
    And a participant
    When the participant opens the verification page
    Then the verification page access is denied
