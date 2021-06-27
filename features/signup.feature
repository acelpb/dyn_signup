Feature: Signup
    A site for participants to signup.

    Scenario: Simple Signup
        Given a user
        And a ballad

        When user submits 3 participants

        Then the total count of participants for the ballad should be 3
        And the user is linked to 3 participants

    Scenario: Max capacity reached
        Given a user
        And a ballad with max 2 participants

        When user submits 3 participants

        Then the total count of participants for the ballad should be 0
        And the user is linked to 0 participants
