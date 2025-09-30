---
description: Execute a development plan with full Archon task management integration
argument-hint: [plan-file-path]
---

# Execute Development Plan with Archon Task Management

You are about to execute a comprehensive development plan with integrated Archon task management. This workflow ensures systematic task tracking and implementation throughout the entire development process.

## Critical Requirements

**MANDATORY**: Throughout the ENTIRE execution of this plan, you MUST maintain continuous usage of Archon for task management. DO NOT drop or skip Archon integration at any point. Every task from the plan must be tracked in Archon from creation to completion.

## Step 1: Read and Parse the Plan

Read the plan file specified in: $ARGUMENTS

The plan file will contain:
- A list of tasks to implement
- References to existing codebase components and integration points
- Context about where to look in the codebase for implementation

## Step 2: Create All Tasks in Tasks.md

For EACH task identified in the plan:
1. Create a corresponding task in a Tasks.md file in the root directory of the project
2. Set initial status as "todo"
3. Include detailed descriptions from the plan
4. Maintain the task order/priority from the plan

**IMPORTANT**: Create ALL tasks in Archon upfront before starting implementation. This ensures complete visibility of the work scope.

## Step 3: Codebase Analysis

Before implementation begins:
1. Analyze ALL integration points mentioned in the plan
2. Use Grep and Glob tools to:
   - Understand existing code patterns
   - Identify where changes need to be made
   - Find similar implementations for reference
3. Read all referenced files and components
4. Build a comprehensive understanding of the codebase context

## Step 4: Implementation Cycle

For EACH task in sequence:

### 4.1 Start Task
- Move the current task to "doing" status in Archon: `mcp__archon__manage_task("update", task_id=..., status="doing")`
- Use TodoWrite to track local subtasks if needed

### 4.2 Implement
- Execute the implementation based on:
  - The task requirements from the plan
  - Your codebase analysis findings
  - Best practices and existing patterns
- Make all necessary code changes
- Ensure code quality and consistency

### 4.3 Complete Task
- Once implementation is complete, move task to "review" status: `mcp__archon__manage_task("update", task_id=..., status="review")`
- DO NOT mark as "done" yet - this comes after validation

### 4.4 Proceed to Next
- Move to the next task in the list
- Repeat steps 5.1-5.3

**CRITICAL**: Only ONE task should be in "doing" status at any time. Complete each task before starting the next.

## Step 5: Validation Phase

After ALL tasks are in "review" status:

**IMPORTANT: Use the `validator` agent for comprehensive testing**
1. Launch the validator agent using the Task tool
   - Provide the validator with a detailed description of what was built
   - Include the list of features implemented and files modified
   - The validator will create simple, effective unit tests
   - It will run tests and report results

The validator agent will:
- Create focused unit tests for the main functionality
- Test critical edge cases and error handling
- Run the tests using the project's test framework
- Report what was tested and any issues found

Additional validation you should perform:
- Check for integration issues between components
- Ensure all acceptance criteria from the plan are met

## Step 6: Finalize Tasks in Archon

After successful validation:

1. For each task that has corresponding unit test coverage:
   - Move from "review" to "done" status: `mcp__archon__manage_task("update", task_id=..., status="done")`

2. For any tasks without test coverage:
   - Leave in "review" status for future attention
   - Document why they remain in review (e.g., "Awaiting integration tests")

## Step 7: Final Report

Provide a summary including:
- Total tasks created and completed
- Any tasks remaining in review and why
- Test coverage achieved
- Key features implemented
- Any issues encountered and how they were resolved

## Workflow Rules

1. **NEVER** skip Archon task management at any point
2. **ALWAYS** create all tasks in Archon before starting implementation
3. **MAINTAIN** one task in "doing" status at a time
4. **VALIDATE** all work before marking tasks as "done"
5. **TRACK** progress continuously through Archon status updates
6. **ANALYZE** the codebase thoroughly before implementation
7. **TEST** everything before final completion

## Error Handling

If at any point Archon operations fail:
1. Retry the operation
2. If persistent failures, document the issue but continue tracking locally
3. Never abandon the Archon integration - find workarounds if needed

Remember: The success of this execution depends on maintaining systematic task management through Archon throughout the entire process. This ensures accountability, progress tracking, and quality delivery.