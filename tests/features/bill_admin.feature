Feature: Bill lifecycle in the admin
  A bill's amount lives in its payment lines (the ventilation), never in a
  field. A bill stays fully editable until it has been paid, then it is
  locked.

  Scenario: Creating a bill registers its amount as an open payment line
    Given I am logged in to the admin as a treasurer
    When I create a bill named "Fournitures" of 123.45 euros
    Then the bill "Fournitures" totals 123.45 euros with 123.45 euros left to pay

  Scenario: The amount can be corrected while nothing is paid
    Given a bill "Location" of 100 euros
    And I am logged in to the admin as a treasurer
    When I change the bill amount to 150 euros
    Then the bill "Location" totals 150 euros with 150 euros left to pay

  Scenario: The amount is locked once a payment is settled
    Given a bill "Location" of 100 euros partially paid with 40 euros
    And I am logged in to the admin as a treasurer
    When I change the bill amount to 150 euros
    Then I am told to edit the ventilation instead
    And the bill "Location" totals 100 euros with 60 euros left to pay

  Scenario: The ventilation can be edited until the bill is paid
    Given a bill "Location" of 100 euros
    And I am logged in to the admin as a treasurer
    When I split the bill into lines of 60 and 40 euros
    Then the bill "Location" totals 100 euros with 100 euros left to pay
    And the bill has 2 open payment lines

  Scenario: A settled payment line cannot be deleted
    Given a bill "Location" of 100 euros partially paid with 40 euros
    And I am logged in to the admin as a treasurer
    When I try to delete the settled payment line
    Then the deletion is refused
    And the bill "Location" totals 100 euros with 60 euros left to pay

  Scenario: A ventilation line must be a negative amount
    Given a bill "Location" of 100 euros
    And I am logged in to the admin as a treasurer
    When I add a ventilation line of 50 euros
    Then I am told the amount must be negative

  Scenario: A paid bill can no longer be edited by a treasurer
    Given a bill "Location" of 100 euros fully paid
    And I am logged in to the admin as a treasurer
    When I try to rename the bill
    Then the change is refused
    And the bill is still named "Location"

  Scenario: A bill without any payment line is not shown as paid
    Given a bill "Vide" without any payment line
    And a bill "Location" of 100 euros fully paid
    And I am logged in to the admin as a treasurer
    When I look at the bill list
    Then the bill "Vide" is not marked as paid
    And the bill "Location" is marked as paid
