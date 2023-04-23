# Created by aborsu at 18/04/23
Feature: As a user I want to be able to provide
  the details of all  the members of my group
  so that I can sign them up to dynamobile.


  Scenario: Signup a simple group
    Given a logged-in visitor on the group_edit page
    And his group of 2 participants
    When submitting his group information
    Then he is correctly redirected to the participant_review page
    And all participants have been added to the database
