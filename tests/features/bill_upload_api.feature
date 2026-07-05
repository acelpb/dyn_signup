Feature: Bill upload API
  As the treasurer
  I want an authenticated API to create bills with their document
  So that an LLM assistant can upload bills for me

  Scenario: A bill is created with a valid token
    Given the bill upload API is configured with a token
    When I post a bill with the valid token
    Then the bill is created with its document

  Scenario: A request with a wrong token is rejected
    Given the bill upload API is configured with a token
    When I post a bill with a wrong token
    Then the request is rejected as unauthorized
    And no bill is created

  Scenario: The API is disabled when no token is configured
    Given the bill upload API has no token configured
    When I post a bill with an empty token
    Then the request is rejected as unauthorized
    And no bill is created

  Scenario: Invalid data is rejected
    Given the bill upload API is configured with a token
    When I post a bill without an amount
    Then the request is rejected with validation errors
    And no bill is created

  Scenario: Duplicate bills are rejected
    Given the bill upload API is configured with a token
    And an identical bill already exists
    When I post a bill with the valid token
    Then the request is rejected as a duplicate
