Feature: Submit a bill for payment

  Scenario: Staff member creates a bill
    Given I am logged in as a staff_member
    When I navigate to the "Create Bill" page
#    And I fill in the bill details
#    And I submit the bill
#    Then I should see a confirmation message
#    And the bill should be in the "Pending" status
#    And I should be able to track the status of the bill I created
#
#  Scenario: Staff member itemizes a bill
#    Given I am logged in as a staff_member
#    When I navigate to the "Create Bill" page
#    And I fill in the bill details
#    And I choose to itemize the bill
#    And I add multiple items with their respective amounts
#    And I submit the bill
#    Then I should see a confirmation message
#    And the bill should be in the "Pending" status
#    And the bill should be split into the specified items
#
#  Scenario: Accountant views and updates bill status
#    Given I am logged in as an accountant
#    When I navigate to the "View Bills" page
#    Then I should see a list of all bills
#    When I select a bill
#    And I change the status to "Payed-Pending-Transaction"
#    Then the bill status should be updated
#    When I link the bill to a transaction
#    Then the bill status should be "Payed"
#
#  Scenario: Admin views all bills
#    Given I am logged in as an admin
#    When I navigate to the "View Bills" page
#    Then I should see a list of all bills
#    And I should not be able to change the status of any bill
#    And I should not be able to link any bill to a transaction