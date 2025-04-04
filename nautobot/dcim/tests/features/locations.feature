Feature: Locations
  In order to represent the geographical structure of my organization's infrastructure,
  As a Network Engineer
  I want to record in Nautobot an appropriate set of LocationType and Location records.

  Background:
    Given I have appropriate Nautobot permissions:
      | model             | permissions            |
      | dcim.locationtype | add,change,delete,view |
      | dcim.location     | add,change,delete,view |
    And I am logged in to Nautobot

  Scenario: Creating a hierarchy of LocationTypes
    When I navigate to the "Add LocationType" view
    And I make the following form entries:
      | name              | nestable |
      | Geographic Region | True     |
    And I submit the form
    Then a LocationType exists in Nautobot with the following properties:
      | name              | parent | nestable |
      | Geographic Region | None   | True     |
    And Nautobot shows the "LocationType Detail" view for the LocationType with name "Geographic Region"

    When I click the "Add child" button
    Then Nautobot shows the "Add LocationType" view with the following presets:
      | parent            |
      | Geographic Region |
    When I make the following form entries:
      | name |
      | City |
    And I submit the form
    Then a LocationType exists in Nautobot with the following properties:
      | name | parent              | nestable |
      | City | Geographic Region   | False    |
    And Nautobot shows the "LocationType Detail" view for the LocationType with name "City"

    When I click the "Add child" button
    Then Nautobot shows the "Add LocationType" view with the following presets:
      | parent |
      | City   |
    When I make the following form entries:
      | name     | content_types |
      | Building | [dcim.device] |
    And I submit the form
    Then a LocationType exists in Nautobot with the following properties:
      | name     | parent | nestable | content_types |
      | Building | City   | False    | [dcim.device] |
    And Nautobot shows the "LocationType Detail" view for the LocationType with name "Building"

  Scenario: Creating a hierarchy of Locations
    Given that LocationType records exist with the following properties:
      | name              | parent            | nestable |
      | Geographic Region | None              | True     |
      | City              | Geographic Region | False    |
      | Building          | City              | False    |
    When I navigate to the "Add Location" view
    And I make the following form entries:
      | name          | location_type     | status |
      | United States | Geographic Region | Active |
    And I submit the form
    Then a Location exists in Nautobot with the following properties:
      | name          | location_type     | parent | status |
      | United States | Geographic Region | None   | Active |
    And Nautobot shows the "Location Detail" view for the Location with name "United States"

    When I click the "Add child" button
    Then Nautobot shows the "Add Location" view with the following presets:
      | parent        |
      | United States |
    When I make the following form entries:
      | name           | location_type     | status | time_zone |
      | North Carolina | Geographic Region | Active | America/New York |
    And I submit the form
    Then a Location exists in Nautobot with the following properties:
      | name           | location_type     | parent        | status | time_zone        |
      | North Carolina | Geographic Region | United States | Active | America/New York |
    And Nautobot shows the "Location Detail" view for the Location with name "North Carolina"

    When I click the "Add child" button
    Then Nautobot shows the "Add Location" view with the following presets:
      | parent         |
      | North Carolina |
    When I make the following form entries:
      | name   | location_type | status  |
      | Durham | City          | Planned |
    And I submit the form
    Then a Location exists in Nautobot with the following properties:
      | name   | location_type | parent         | status  |
      | Durham | City          | North Carolina | Planned |
    And Nautobot shows the "Location Detail" view for the Location with name "Durham"

    When I click the "Add child" button
    Then Nautobot shows the "Add Location" view with the following presets:
      | parent |
      | Durham |
    When I make the following form entries:
      | name                       | location_type | status  | physical_address     |
      | Durham Bulls Athletic Park | Building      | Planned | 409 Blackwell Street |
    And I submit the form via the "Create and Add Another" button
    Then a Location exists in Nautobot with the following properties:
      | name                       | location_type | parent | status  | physical_address     |
      | Durham Bulls Athletic Park | Building      | Durham | Planned | 409 Blackwell Street |
    And Nautobot shows the "Add Location" view with the following presets:
      | parent | location_type | status  |
      | Durham | Building      | Planned |
    When I make the following form entries:
      | name                          |
      | Durham Performing Arts Center |
    And I submit the form
    Then a Location exists in Nautobot with the following properties:
      | name                          | location_type | parent | status  |
      | Durham Performing Arts Center | Building      | Durham | Planned |
    And Nautobot shows the "Location Detail" view for the Location with name "Durham Performing Arts Center"

    When I click on the "Durham" link
    Then Nautobot shows the "Location Detail" view for the Location with name "Durham"
    And the table "Children" includes rows with the following properties:
      | name                          | status  |
      | Durham Bulls Athletic Park    | Planned |
      | Durham Performing Arts Center | Planned |

  Scenario Outline: Missing required fields for Location
    Given that LocationType records exist with the following properties:
      | name              | parent            | nestable |
      | Geographic Region | None              | True     |
      | City              | Geographic Region | False    |
      | Building          | Building          | False    |
    When I navigate to the "Add Location" view
    And I make the following form entries:
      | name   | location_type   | parent   | status   |
      | <name> | <location_type> | <parent> | <status> |
    And I submit the form
    Then Nautobot shows the "Add Location" view with the following presets:
      | name   | location_type   | parent   | status   |
      | <name> | <location_type> | <parent> | <status> |
    And the field "<required_field>" shows error message "<error_message>"

    Scenarios:
      | name          | location_type     | parent | status | required_field | error_message                      |
      |               | Geographic Region | None   | Active | name           | Please fill out this field.        |
      | United States | None              | None   | Active | location_type  | Please select an item in the list. |
      | United States | Geographic Region | None   | None   | status         | Please select an item in the list. |
      | Durham        | City              | None   | Active | parent         | A Location of type City must have a parent Location. |
