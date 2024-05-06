Feature: Prefixes
  In order to manage my network IPAM data,
  As a Network Engineer
  I want to record in Nautobot an appropriate set of Prefixes and related data.

  Background:
    Given I have appropriate Nautobot permissions:
      | model          | permissions            |
      | ipam.namespace | add,change,delete,view |
      | ipam.prefix    | add,change,delete,view |
    And I am logged in to Nautobot

  Scenario: Creating a set of Prefixes in a custom Namespace
    When I navigate to the "Add Namespace" view
    And I make the following form entries:
      | name | description       |
      | CORP | Corporate network |
    And I submit the form
    Then a Namespace exists in Nautobot with the following properties:
      | name | description       |
      | CORP | Corporate network |
    And Nautobot shows the "Namespace Detail" view for the Namespace with name "CORP"
    # TODO: it would be nice to have the ability to create a Prefix directly from the Namespace detail view?

    When I navigate to the "Add Prefix" view
    And I make the following form entries:
      | prefix     | namespace | type      | status |
      | 10.0.0.0/8 | CORP      | Container | Active |
    And I submit the form
    Then a Prefix exists in Nautobot with the following properties:
      | prefix     | namespace | type      | status | parent |
      | 10.0.0.0/8 | CORP      | Container | Active | None   |
    And Nautobot shows the "Prefix Detail" view for the Prefix with prefix "10.0.0.0/8" and namespace "CORP"
    And the view shows a "Utilization" of "0%"

    When I click the "Clone" button
    Then Nautobot shows the "Add Prefix" view with the following presets:
      | namespace | type      | status |
      | CORP      | Container | Active |
    When I make the following form entries:
      | prefix        | type    |
      | 10.0.100.0/24 | Network |
    And I submit the form
    Then a Prefix exists in Nautobot with the following properties:
      | prefix        | namespace | type    | status | parent     |
      | 10.0.100.0/24 | CORP      | Network | Active | 10.0.0.0/8 |
    And Nautobot shows the "Prefix Detail" view for the Prefix with prefix "10.0.100.0/24" and namespace "CORP"
    And the view shows a "Utilization" of "0%"
    And the table "Parent Prefixes" includes rows with the following properties:
      | prefix     | type      |
      | 10.0.0.0/8 | Container |

    When I click the "Clone" button
    Then Nautobot shows the "Add Prefix" view with the following presets:
      | namespace | type    | status |
      | CORP      | Network | Active |
    When I make the following form entries:
      | prefix      | type      |
      | 10.0.0.0/16 | Container |
    And I submit the form
    Then a Prefix exists in Nautobot with the following properties:
      | prefix      | namespace | type      | status | parent     |
      | 10.0.0.0/16 | CORP      | Container | Active | 10.0.0.0/8 |
    And Nautobot shows the "Prefix Detail" view for the Prefix with prefix "10.0.0.0/16" and namespace "CORP"
    And the table "Parent Prefixes" includes rows with the following properties:
      | prefix     | type      |
      | 10.0.0.0/8 | Container |
    And the tab "Child Prefixes" includes a badge with the number "1"

    When I click the "Child Prefixes" tab
    Then Nautobot shows the "Child Prefixes" tab
    And the table "Child Prefixes" includes rows with the following properties:
      | prefix        | type    | status |
      | 10.0.0.0/18   | —       | —      |
      | 10.0.64.0/19  | —       | —      |
      | 10.0.96.0/22  | —       | —      |
      | 10.0.100.0/24 | Network | Active |

    When I click the "10.0.96.0/22" link
    Then Nautobot shows the "Add Prefix" view with the following presets:
      | prefix        | namespace |
      | 10.0.96.0/22  | CORP      |
    When I make the following form entries:
      | prefix       | type      | status |
      | 10.0.96.0/20 | Container | Active |
    And I submit the form
    Then a Prefix exists in Nautobot with the following properties:
      | prefix       | namespace | type      | status | parent      |
      | 10.0.96.0/20 | CORP      | Container | Active | 10.0.0.0/16 |
    And Nautobot shows the "Prefix Detail" view for the Prefix with prefix "10.0.96.0/20" and namespace "CORP"
    And the view shows a "Utilization" of "6%"
    And the table "Parent Prefixes" includes rows with the following properties:
      | prefix      | type      | status |
      | 10.0.0.0/8  | Container | Active |
      | 10.0.0.0/16 | Container | Active |
    And the tab "Child Prefixes" includes a badge with the number "1"

    When I navigate to the "Prefix List" view
    And specify a filter of "?namespace=CORP"
    Then the table "Prefixes" includes rows with the following properties:
      | prefix        | namespace | type      | status | children | utilization |
      | 10.0.0.0/8    | CORP      | Container | Active | 3        | 0%          |
      | 10.0.0.0/16   | CORP      | Container | Active | 2        | 6%          |
      | 10.0.96.0/20  | CORP      | Container | Active | 1        | 6%          |
      | 10.0.100.0/24 | CORP      | Network   | Active | 0        | 0%          |

    When I click the "Import" button
    Then Nautobot shows the "Prefix Bulk Import" view
    When I enter the following into the "csv_data" field:
      """
      prefix,status__name,type,namespace__name
      10.0.101.0/24,Reserved,network,CORP
      10.0.102.0/24,Reserved,network,CORP
      10.1.0.0/16,Reserved,container,CORP
      """
    And I submit the form
    Then several Prefixes exist in Nautobot with the following properties:
      | prefix        | namespace | type      | status   | parent       |
      | 10.0.101.0/24 | CORP      | Network   | Reserved | 10.0.96.0/20 |
      | 10.0.102.0/24 | CORP      | Network   | Reserved | 10.0.96.0/20 |
      | 10.1.0.0/16   | CORP      | Container | Reserved | 10.0.0.0/8   |
    And Nautobot shows the "Prefix Import Completed" view with 3 rows
    When I click the "View All" button
    Then Nautobot shows the "Prefix List" view
    When I specify a filter of "?namespace=CORP"
    Then the table "Prefixes" includes rows with the following properties:
      | prefix        | namespace | type      | status   | children | utilization |
      | 10.0.0.0/8    | CORP      | Container | Active   | 6        | 0%          |
      | 10.0.0.0/16   | CORP      | Container | Active   | 4        | 6%          |
      | 10.0.96.0/20  | CORP      | Container | Active   | 3        | 18%         |
      | 10.0.100.0/24 | CORP      | Network   | Active   | 0        | 0%          |
      | 10.0.101.0/24 | CORP      | Network   | Reserved | 0        | 0%          |
      | 10.0.102.0/24 | CORP      | Network   | Reserved | 0        | 0%          |
      | 10.1.0.0/16   | CORP      | Container | Reserved | 0        | 0%          |
