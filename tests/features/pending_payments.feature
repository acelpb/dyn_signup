Feature: Pending payments overview
  As the treasurer
  I want to see every payment I still have to make in a single view
  So that I do not have to hunt through expense reports and bills separately

  Scenario: Treasurer sees all payments to make in one view
    Given an expense report awaiting reimbursement
    And a bill awaiting payment
    And a bill already paid
    When I visit the pending payments page
    Then I see the expense report with its IBAN and amount
    And I see the unpaid bill with its remaining amount
    And I do not see the paid bill

  Scenario: Fully reimbursed expense reports are not listed
    Given an expense report fully reimbursed
    When I visit the pending payments page
    Then I do not see the reimbursed expense report

  Scenario: A matching imported operation is suggested for an expense report
    Given an expense report awaiting reimbursement
    And an imported unjustified operation matching the expense report
    And an imported unjustified operation with a different amount
    When I visit the pending payments page
    Then I see a link to connect the matching operation to the expense report
    And the operation with a different amount is not suggested

  Scenario: A matching imported operation is suggested for a bill
    Given a bill awaiting payment
    And an imported unjustified operation matching the bill
    When I visit the pending payments page
    Then I see a link to connect the matching operation to the bill

  Scenario: A regular user cannot access the pending payments page
    Given a participant
    When the participant visits the pending payments page
    Then the access is denied
