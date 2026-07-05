Feature: MCP server for LLM assistants
  As the treasurer
  I want the tool to expose an MCP endpoint
  So that claude.ai can upload bills even when a sandbox proxy blocks direct API calls

  Scenario: An assistant initializes and discovers the upload tool
    Given an issued API token
    When the assistant initializes the MCP session
    Then the server introduces itself with its protocol version
    When the assistant lists the MCP tools
    Then the upload_bill tool is listed

  Scenario: An assistant uploads a bill with its document through MCP
    Given an issued API token
    When the assistant calls upload_bill with a document
    Then the MCP call succeeds and the bill is created with its document

  Scenario: A duplicate upload through MCP is rejected
    Given an issued API token
    And an identical bill already exists
    When the assistant calls upload_bill with a document
    Then the MCP call reports an error mentioning the duplicate

  Scenario: A wrong token is rejected
    Given an issued API token
    When the assistant calls the MCP endpoint with a wrong token
    Then the MCP request is rejected as unauthorized

  Scenario: The treasurer generates a connector token in the browser
    When the treasurer generates a token on the token page
    Then the page shows the MCP URL once and the token works

  Scenario: A regular user cannot generate a token
    Given a participant
    When the participant opens the token page
    Then the token page access is denied
