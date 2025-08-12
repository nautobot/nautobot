# Approval Workflows

Approval Workflows allows for a multi-stage review and approval of processes before making changes, running or creating specific objects in the system. They are defined in advance and attached to specific models based on certain constraints.

## Model Reference

### ApprovalWorkflowDefinition

The template for a workflow, specifying which model(s) it applies to, any constraints, and the ordered list of stages. Represents a reusable definition of an approval workflow.

**Attributes:**

- **name**: Unique name for the workflow.
- **model_content_type**: The model to which this workflow applies.
- **model_constraints**: Optional JSON constraints to further limit applicable objects.
- **priority**: Determines selection when multiple workflows match. Lower means higher priority.
- **approval_workflow_stage_definitions**: Related stages, ordered by weight.
- **find_for_model(model_instance)** (manager) - Finds the best-matching workflow for a given object.

### ApprovalWorkflowStageDefinition

A single approval stage within a workflow definition, specifying the approver group and required number of approvers.

**Attributes:**

- **name** - Stage name.
- **approval_workflow_definition** - Parent workflow definition.
- **weight** - Order in which the stage is processed. Lower weights come earlier.
- **min_approvers** - Minimum number of approvals required for the stage to pass.
- **denial_message** - Optional message shown when denied.
- **approver_group** - Group of users eligible to approve this stage.

### ApprovalWorkflow

A concrete instance of a workflow triggered for a specific object under review.

- Automatically changes to `Denied` if any stage is denied.
- Automatically changes to `Approved` if all stages are approved.
- Calls object’s `on_workflow_approved()` or `on_workflow_denied()` when final state is reached.

**Attributes:**

- **approval_workflow_definition** - The definition it’s based on.
- **object_under_review** - Generic foreign key to the object being reviewed.
- **current_state** - Current workflow state (`Pending`, `Approved`, `Denied`).
- **decision_date** - Date/time of final decision.
- **user** - User who triggered the workflow.
- **active_stage** (property) - The next stage that requires action.

### ApprovalWorkflowStage

A stage instance within a workflow execution. Progresses from `Pending` → `Approved`/`Denied`.

- Approves automatically when minimum approvals are met.
- Denies immediately if any denial is submitted.
- Triggers parent workflow state updates.

**Attributes:**

- **approval_workflow** - Parent workflow instance.
- **approval_workflow_stage_definition** - Stage definition this instance is based on.
- **state** - Stage state (`Pending`, `Approved`, `Denied`).
- **decision_date** - Date/time when the stage reached a terminal state.
- **remaining_approvals** (property) - How many more approvals are needed to pass.
- **is_active_stage** (property) - Whether this stage is currently open for approvals.
- **users_that_already_approved** (property) - List of users who have approved.
- **users_that_already_denied** (property) - List of users who have denied.
- **should_render_state** (property) - Whether to display the stage state in the UI.

### ApprovalWorkflowStageResponse

A single user's input on a specific stage - this may be an explicit decision (`approve`/`deny`) or simply a comment without a decision.

- Saving a response can trigger stage and workflow state updates.

**Attributes:**

- **approval_workflow_stage** - Stage being responded to.
- **user** - Approving/denying or commenting user.
- **comments** - Optional explanation.
- **state** - `Pending`, `Approved`, or `Denied`.

## How-To Guides

### Using Approval Workflow via UI

#### Create an Approval Workflow Definition

1. Go to `Approvals > Workflow Definitions > Add Approval Workflow Definition`.
2. Enter:
    - **Name** (e.g., "Scheduled Job Run Workflow").
    - **Model** (e.g., `extras|scheduled job`).
    - **Constraints** (optional JSON filter, e.g., `{"name": "Bulk Delete Objects Scheduled Job"}`).
    - **Priority** (lower means higher priority).
3. In the **Approval Workflow Stage Definitions** section, define one or more stages:
    - **Stage Name** (e.g, "Stage1").
    - **Weight** (order in which the stage is executed).
    - **Minimum Approvers** (number of approvals required).
    - **Approver Group** (group of users eligible to approve)
    - **Denial Message** (optional message shown if denied).

#### Attach Workflow to a Model Instance

Workflows are automatically attached after creating, running, or updating an object that complies with the workflow model and constraints. Manual attachment is not available.

#### Approve or Deny a Stage

1. Go to `Approvals > Approval Dashboard` or on the right `User dropdown menu > Approval Dashboard` and select the **My Approvals** tab.
2. Locate the relevant object under review in the table. The table displays:
    - **Object under review** - Linked to the object’s detail view.
    - **Workflow** - Name of the workflow definition (linked to the workflow detail view).
    - **Current Stage** - Stage awaiting action.
    - **Actions Needed** - Remaining approvals required.
    - **State** - Current workflow state.
3. To approve the stage, select the green button.  
4. To deny the stage, select the red button.
5. After the decision action, a confirmation window appears where a comment can be added before confirming the action.

#### View My Requests

1. Open the **Approval Dashboard** and select the **My Requests** tab.
2. The table lists all workflows initiated by the current user. The columns include:
    - **Approval Workflow Definition** - Linked to the workflow definition.
    - **Object Type Under Review** - Model and object type for the request.
    - **Object Under Review** - Linked to the specific object awaiting or having received approval.
    - **Current State** - State of the workflow (e.g., `Pending`, `Approved`, `Denied`).
    - **User** - Requesting user.

#### Check Workflow State

1. Go to `Approvals > Approval Workflow Definition`
2. Select the required workflow definition.
3. In the **Workflows** list, all workflows for this definition are displayed.
4. Select the details button for a specific workflow.
5. View **Approval Workflow** details view contains:
    - **Approval Workflow** panel:
        - **Approval Workflow Definition** - Linked definition for the workflow.
        - **Object Under Review** - Object subject to approval.
        - **Current State** - Workflow status.
        - **Approval Date** - Date of final decision.
        - **Requesting User** - User who initiated the workflow.
    - **Stages** panel:
        - **Stage** - Stage name.
        - **Actions Needed** - Remaining approvals required.
        - **State** - Current stage status.
        - **Decision Date** - Date of stage decision.
    - **Responses** panel:
        - **Stage** - Stage name.
        - **User** - Responding user.
        - **Comments** - Submitted comment.
        - **State** - Decision state (`Pending`, `Approved`, `Denied`).

### Using Approval Workflow via API

#### Create an Approval Workflow Definition

#### Attach Workflow to a Model Instance

#### Approve or Deny a Stage

#### Comment a Stage

#### View My Requests

#### Check Workflow State

## Permissions and Group Setup

### Dashboard Access

- **My Approvals tab only** - `extras.view_approvalworkflowstage`  
  Allows viewing assigned approvals but not making decisions.
- **Make approval/denial decisions** - `extras.change_approvalworkflowstage`  
  Allows approving or denying stages.
- **My Requests tab and workflow details** - `extras.view_approvalworkflow`  
  Allows viewing workflows initiated by the user and their details.
- **View responses in workflow details** - `extras.view_approvalworkflowstageresponse`  
  Allows viewing individual user responses in the details view.

### Workflow and Definition Management

- **View Approval Workflows** – `extras.view_approvalworkflow`
- **View Workflow Definitions** – `extras.view_approvalworkflowdefinition`
- **Add Workflow Definitions** – `extras.add_approvalworkflowdefinition`

### Stage and Stage Definition Management

- **View Workflow Stages** – `extras.view_approvalworkflowstage`
- **Modify Workflow Stages** – `extras.change_approvalworkflowstage`
- **View Stage Definitions** – `extras.view_approvalworkflowstagedefinition`
- **View Stage Responses** – `extras.view_approvalworkflowstageresponse`

### Approver Groups

Approval actions are controlled not only by permissions but also by **approver group membership** defined in each workflow definition:

- Each **Approval Workflow Stage Definition** specifies an **Approver Group** (user group authorized to act on that stage).
- A user must belong to the stage’s approver group to:
    - See the stage in the **My Approvals** tab.
    - Perform approval or denial actions.
- If the user has the required permissions but is **not** a member of the approver group, the stage will not appear in their dashboard and no actions will be available.

## Upgrade Considerations

**From Nautobot 2.x**  
  If upgrading from Nautobot 2.x, the management command `check_job_approval_status` is available to identify Jobs and Scheduled Jobs that have `approval_required=True`. Running this command prior to upgrading helps detect and address these cases by:
      - Approving (and running) or denying scheduled jobs that require approval.
      - Defining approval workflows for Jobs where appropriate.
