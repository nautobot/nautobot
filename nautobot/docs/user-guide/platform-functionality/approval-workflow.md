# Approval Workflows

Approval Workflows allows for a multi-stage review and approval of processes before making changes, running or creating specific objects in the system. They are defined in advance and attached to specific models based on certain constraints.

## Model Reference

```mermaid
---
title: Approval Workflow Entity Relationship Diagram
---
erDiagram
    "extras.ApprovalWorkflowDefinition" {
        string name
        ContentType model_content_type FK
        json model_constraints
        int priority
    }
    "extras.ApprovalWorkflowStageDefinition" {
        ApprovalWorkflowDefinition approval_workflow_definition FK
        int weight
        string name
        int min_approvers
        string denial_message
        Group approver_group FK
    }
    "extras.ApprovalWorkflow" {
        ApprovalWorkflowDefinition approval_workflow_definition FK
        GenericForeignKey object_under_review FK
        ContentType object_under_review_content_type FK
        uuid object_under_review_object_id
        choices current_state
        datetime decision_date
        User user FK
        string user_name
    }
    "extras.ApprovalWorkflowStage" {
        ApprovalWorkflow approval_workflow FK
        ApprovalWorkflowStageDefinition approval_workflow_stage_definition FK
        choices state
        datetime decision_date
    }
    "extras.ApprovalWorkflowStageResponse" {
        ApprovalWorkflowStage approval_workflow_stage FK
        User user FK
        string comments
        choices state
    }

    "contenttypes.ContentType"[ContentType] {}
    "users.User"[User] {}
    "users.Group"[Group] {}
    "models.Model"[Model] {}

    "extras.ApprovalWorkflowDefinition" }o--|| "contenttypes.ContentType": "applies to model"
    "extras.ApprovalWorkflowDefinition" ||--o{ "extras.ApprovalWorkflowStageDefinition": "defines stages"
    "extras.ApprovalWorkflowStageDefinition" }o--|| "users.Group": "approver group"
    "extras.ApprovalWorkflowDefinition" ||--o{ "extras.ApprovalWorkflow": "creates instances"
    "extras.ApprovalWorkflow" }o--|| "models.Model": "object under review"
    "extras.ApprovalWorkflow" ||--o{ "extras.ApprovalWorkflowStage": "has stage instances"
    "extras.ApprovalWorkflowStage" ||--o{ "extras.ApprovalWorkflowStageResponse": "has responses"
    "extras.ApprovalWorkflowStageResponse" }o--|| "users.User": "submitted by"
```

### ApprovalWorkflowDefinition

The template for a workflow, specifying which model(s) it applies to, any constraints, and the ordered list of stages. Represents a reusable definition of an approval workflow.

**Attributes:**

- **find_for_model(model_instance)** (manager) - Finds the best-matching workflow for a given object.

### ApprovalWorkflowStageDefinition

A single approval stage within a workflow definition, specifying the approver group and required number of approvers.

### ApprovalWorkflow

A concrete instance of a workflow triggered for a specific object under review.

- Automatically changes to `Denied` if any stage is denied.
- Automatically changes to `Approved` if all stages are approved.
- Calls object’s `on_workflow_approved()` or `on_workflow_denied()` when final state is reached.

**Attributes:**

- **active_stage** (property) - The next stage that requires action.

### ApprovalWorkflowStage

A stage instance within a workflow execution. Progresses from `Pending` → `Approved`/`Denied`.

- Approves automatically when minimum approvals are met.
- Denies immediately if any denial is submitted.
- Triggers parent workflow state updates.

**Attributes:**

- **remaining_approvals** (property) - How many more approvals are needed to pass.
- **is_active_stage** (property) - Whether this stage is currently open for approvals.
- **users_that_already_approved** (property) - List of users who have approved.
- **users_that_already_denied** (property) - List of users who have denied.
- **should_render_state** (property) - Whether to display the stage state in the UI.

### ApprovalWorkflowStageResponse

A single user's input on a specific stage - this may be an explicit decision (`approve`/`deny`) or simply a comment without a decision.

- Saving a response can trigger stage and workflow state updates.

## How-To Guides

### Attach Workflow to a Model Instance

Workflows are automatically attached after creating, running, or updating an object that complies with the workflow model and constraints. Manual attachment is not available.

### Using Approval Workflow via UI

#### Create an Approval Workflow Definition with stages

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

without `model_constraints`

```no-highlight
curl -X POST \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=1.3; indent=4" \
-d '{
    "name": "Scheduled Job Run Workflow",
    "model_content_type": "extras.scheduledjob",
    "priority": 0
}' \
http://nautobot/api/extras/approval-workflow-definitions/
```

with `model_constraints`

```no-highlight
curl -X POST \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=1.3; indent=4" \
-d '{
    "name": "Scheduled Job Run Workflow",
    "model_content_type": "extras.scheduledjob",
    "model_constraints": {"name": "Bulk Delete Objects Scheduled Job"},
    "priority": 0
}' \
http://nautobot/api/extras/approval-workflow-definitions/
```

#### Create an Approval Workflow Stage Definition

`denial_message` is optional

```no-highlight
curl -X POST \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=1.3; indent=4" \
-d '{
    "approval_workflow_definition": "<APPROVAL-WORKFLOW-DEFINITION-ID>",
    "weight": 0,
    "name": "Initial Review",
    "min_approvers": 1,
    "denial_message": "Rejected during initial review.",
    "approver_group": "initial-approval-group"
}' \
http://nautobot/api/extras/approval-workflow-stage-definitions/
```

#### Approve/Deny a Stage

```no-highlight
curl -X POST \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=1.3; indent=4" \
-d '{"comment": "Approved for deployment"}' \
http://nautobot/api/extras/approval-workflow-stages/$APPROVAL_WORKFLOW_STAGE_ID/approve
```

```no-highlight
curl -X POST \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=1.3; indent=4" \
-d '{"comment": "Deny reason"}' \
http://nautobot/api/extras/approval-workflow-stages/$APPROVAL_WORKFLOW_STAGE_ID/deny
```

#### Comment on an Approval Workflow Stage

The `comment` endpoint allows a user to attach a non-approval comment to a specific stage within an approval workflow. This endpoint does not change the state of the stage, and is intended for adding informational messages, questions, or updates related to the approval process.

- This will attach a comment to the specified stage.
- The stage state will remain unchanged.
- The user must have the `change_approvalworkflowstage` permission.

```no-highlight
curl -X POST \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=1.3; indent=4" \
-d '{"comments": "Waiting for additional testing."}' \
http://nautobot/api/extras/approval-workflow-stages/$APPROVAL_WORKFLOW_STAGE_ID/comment
```

#### List Pending/Done Approvals

Retrieves a list of approval workflow stages filtered by their status relative to the current user using the `pending_my_approvals` query parameter on the standard list endpoint:

- `?pending_my_approvals=true` — Returns stages pending approval by the current user.

```no-highlight
curl -X GET \
-H "Authorization: Token $TOKEN" \
-H "Accept: application/json; version=1.3; indent=4" \
http://nautobot/api/extras/approval-workflow-stages/?pending_my_approvals=true
```

- `?pending_my_approvals=false` — Returns stages the current user has already approved/denied.

```no-highlight
curl -X GET \
-H "Authorization: Token $TOKEN" \
-H "Accept: application/json; version=1.3; indent=4" \
http://nautobot/api/extras/approval-workflow-stages/?pending_my_approvals=false
```

If the parameter is omitted, all stages are returned regardless of approval status.

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
