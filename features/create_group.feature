Feature: Create a group of participant
    This allows for the creation of participant groups.

    Scenario: Simple Signup
        Given signup is open
        And a visitor
        And a group with 1 adult participant

        When the visitor submits his group for a full participation

        Then the group is validated and a bill is created
        And an email is sent with the amount to be paid

    Scenario: Partial Signup before partial signup date
        Given signup is open
        And a visitor
        And a group with 1 adult participant

        When the visitor submits his group for a partial participation

        Then the group is validated and a bill is created
        And an email is sent with the amount to be paid
