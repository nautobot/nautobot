# Contacts and Teams

## How to Assign Contacts and Teams to Nautobot Objects

In order to assign contacts/teams to a particular object, we first need to define `Status` and `Role` objects for the content type `extras:contactassociation`. Once that is done, we can navigate to the detail view of the object. We will use a circuit in this example.

![Circuit](./images/contact-and-team/ss_circuit_light.png#only-light){ .on-glb }
![Circuit](./images/contact-and-team/ss_circuit_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/circuits/circuits/957c7d20-4b81-5902-8fc8-78ca885069e7/`"

At the top right corner, you should see a group of buttons and one of them should say **Add Contact**.
![Circuit Add Contact Button](./images/contact-and-team/ss_circuit_button_light.png#only-light){ .on-glb }
![Circuit Add Contact Button](./images/contact-and-team/ss_circuit_button_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/circuits/circuits/957c7d20-4b81-5902-8fc8-78ca885069e7/?tab=contacts`"
Click on the **Add Contact** button and it will redirect you to a page with forms on three separate tabs.
![Contact Form](./images/contact-and-team/ss_contact_forms_light.png#only-light){ .on-glb }
![Contact Form](./images/contact-and-team/ss_contact_forms_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/extras/contact-associations/add-new-contact/?return_url=/circuits/circuits/957c7d20-4b81-5902-8fc8-78ca885069e7/%3Ftab%3Dcontacts&associated_object_id=957c7d20-4b81-5902-8fc8-78ca885069e7&associated_object_type=1`"

1. The first tab contains a form that allows the user to create a **new** contact and associate it with the object.
2. The second tab contains a form that allows the user to create a **new** team and associate it with the object.
3. The third tab contains a form that allows the user to select an **existing** contact or team and associate it with the object.
![Contact Form Tabs](./images/contact-and-team/ss_contact_form_tabs_light.png#only-light){ .on-glb }
![Contact Form Tabs](./images/contact-and-team/ss_contact_form_tabs_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/extras/contact-associations/add-new-contact/?return_url=/circuits/circuits/957c7d20-4b81-5902-8fc8-78ca885069e7/%3Ftab%3Dcontacts&associated_object_id=957c7d20-4b81-5902-8fc8-78ca885069e7&associated_object_type=1`"

### Assign a New Contact/Team

Which form to use depends on the use case but in this example, we will use the first form which creates a **new** contact instance and associates it with the object.

1. We first fill out the contact information.
![Contact Info](./images/contact-and-team/ss_new_contact_info_light.png#only-light){ .on-glb }
![Contact Info](./images/contact-and-team/ss_new_contact_info_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/extras/contact-associations/add-new-contact/?return_url=/circuits/circuits/957c7d20-4b81-5902-8fc8-78ca885069e7/%3Ftab%3Dcontacts&associated_object_id=957c7d20-4b81-5902-8fc8-78ca885069e7&associated_object_type=1`"

2. Then we fill out the information needed for the assignment of this contact to the object.
![Contact Association Info](./images/contact-and-team/ss_new_contact_association_info_light.png#only-light){ .on-glb }
![Contact Association Info](./images/contact-and-team/ss_new_contact_association_info_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/extras/contact-associations/add-new-contact/?return_url=/circuits/circuits/957c7d20-4b81-5902-8fc8-78ca885069e7/%3Ftab%3Dcontacts&associated_object_id=957c7d20-4b81-5902-8fc8-78ca885069e7&associated_object_type=1`"
3. Click **Create** at the bottom of the page.
4. It will redirect us to the detail view of the circuit.
5. We can click on the **Contacts** tab that displays a table of contacts and teams that are associated with this circuit. Our New Contact should be in the table.

![Table with New Contact](./images/contact-and-team/ss_new_contact_table_light.png#only-light){ .on-glb }
![Table with New Contact](./images/contact-and-team/ss_new_contact_table_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/circuits/circuits/957c7d20-4b81-5902-8fc8-78ca885069e7/?tab=contacts`"

### Assign an Existing Contact/Team

In this example, we will use the third form which links an existing contact to the object.

1. Navigate to the detail view of the Circuit.
2. Find and click on the **Add Contact** button.
3. Select the third tab **Assign Contact/Team**.
![Existing Contact Form](./images/contact-and-team/ss_existing_contact_form_light.png#only-light){ .on-glb }
![Existing Contact Form](./images/contact-and-team/ss_existing_contact_form_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/extras/contact-associations/assign-contact-team/?return_url=/circuits/circuits/957c7d20-4b81-5902-8fc8-78ca885069e7/%3Ftab%3Dcontacts&associated_object_id=957c7d20-4b81-5902-8fc8-78ca885069e7&associated_object_type=1`"
4. Select the existing contact to link to the object. (Notice that an existing team dropdown is no longer enabled because those two form fields are mutually exclusive)

![Existing Contact Selected](./images/contact-and-team/ss_existing_contact_selected_light.png#only-light){ .on-glb }
![Existing Contact Selected](./images/contact-and-team/ss_existing_contact_selected_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/extras/contact-associations/assign-contact-team/?return_url=/circuits/circuits/957c7d20-4b81-5902-8fc8-78ca885069e7/%3Ftab%3Dcontacts&associated_object_id=957c7d20-4b81-5902-8fc8-78ca885069e7&associated_object_type=1`"
5. Select the desired role and status and click **Create**.
![Existing Contact Association](./images/contact-and-team/ss_existing_contact_association_light.png#only-light){ .on-glb }
![Existing Contact Association](./images/contact-and-team/ss_existing_contact_association_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/extras/contact-associations/assign-contact-team/?return_url=/circuits/circuits/957c7d20-4b81-5902-8fc8-78ca885069e7/%3Ftab%3Dcontacts&associated_object_id=957c7d20-4b81-5902-8fc8-78ca885069e7&associated_object_type=1`"
6. The page should redirect us to the detail view of the circuit.
7. We can click on the **Contacts** tab that displays a table of contacts and teams that are associated with this circuit. Both our Existing Contact and New Contact should in the table.
![Table with New Contact and Existing Contact](./images/contact-and-team/ss_existing_contact_table_light.png#only-light){ .on-glb }
![Table with New Contact and Existing Contact](./images/contact-and-team/ss_existing_contact_table_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/circuits/circuits/957c7d20-4b81-5902-8fc8-78ca885069e7/?tab=contacts`"
