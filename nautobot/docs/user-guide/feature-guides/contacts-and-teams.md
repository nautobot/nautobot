# Contacts and Teams

## How to Assign Contacts and Teams to Nautobot Objects

In order to assign contacts/teams to a particular object, we first need to define `Status` and `Role` objects for contenttype `extras:contactassociation`. Once that is done, we can navigate to the detail view of the object. We will use a circuit in this example.

![Circuit](./images/contact-and-team/circuit.png)

At the top right corner, you should see a group of buttons and one of them should say **Add Contact**.

![Circuit Add Contact Button](./images/contact-and-team/circuit_button.png)

Click on the **Add Contact** button and it will redirect you to a page with forms on three separate tabs.

![Contact Form](./images/contact-and-team/contact_forms.png)

1. The first tab contains a form that allows the user to create a **new** contact and associate it with the object.
2. The second tab contains a form that allows the user to create a **new** team and associate it with the object.
3. The third tab contains a form that allows the user to select an **existing** contact or team and associate it with the object.

![Contact Form Tabs](./images/contact-and-team/contact_form_tabs.png)

### Assign a New Contact/Team

Which form to use depends on the use case but in this example, we will use the first form which creates a **new** contact instance and associates it with the object.

1. We first fill out the contact information.
![Contact Info](./images/contact-and-team/new_contact_info.png)
2. Then we fill out the information needed for the assignment of this contact to the object.
![Contact Association Info](./images/contact-and-team/new_contact_association_info.png)
3. Click **Create** at the bottom of the page.
4. It will redirect us to the detail view of the circuit.
5. We can click on the **Contacts** tab that displays a table of contacts and teams that are associated with this circuit. Our New Contact should be in the table.

![Table with New Contact](./images/contact-and-team/new_contact_table.png)

### Assign an Existing Contact/Team

In this example, we will use the third form which links an existing contact to the object.

1. Navigate to the detail view of the Circuit.
2. Find and click on the **Add Contact** button.
3. Select the third tab **Assign Contact/Team**.
![Existing Contact Form](./images/contact-and-team/existing_contact_form.png)
4. Select the existing contact to link to the object. (Notice that an existing team dropdown is no longer enabled because those two form fields are mutually exclusive)
![Existing Contact Selected](./images/contact-and-team/existing_contact_selected.png)
5. Select the desired role and status and click **Create**.
![Existing Contact Association](./images/contact-and-team/existing_contact_association.png)
6. The page should redirect us to the detail view of the circuit.
7. We can click on the **Contacts** tab that displays a table of contacts and teams that are associated with this circuit. Both our Existing Contact and New Contact should in the table.

![Table with New Contact and Existing Contact](./images/contact-and-team/existing_contact_table.png)
