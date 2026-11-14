# SmartRoute AI — Project Prompt and Human–AI Collaboration Guide

## Purpose of this document

This file is a reusable professional prompt for developing, reviewing, testing, and extending SmartRoute AI with an AI coding assistant. It summarizes the application context, technical expectations, development challenges, effective prompt patterns, and the responsibilities shared by the human developer and AI assistant.

It intentionally excludes private conversation history, personal information, credentials, and unnecessary implementation discussions.

## Project overview

SmartRoute AI is a school transport operations application that connects three user groups through a shared backend:

1. **Drivers** manage active trips, report bus locations, view route start/end points and stops, and update student journey events.
2. **Administrators** monitor fleet activity, trip status, routes, buses, locations, and student events across the operation.
3. **Parents** view the journey status of their linked child, including whether the child is waiting, boarded, absent, or dropped off.

The project also includes an operations dashboard, analytics, deterministic synthetic data generation, role-based authentication, and automated regression tests.

## Technology and architecture

- **Backend:** Python, FastAPI, SQLAlchemy, and Pydantic
- **Database:** SQLite for local development
- **Frontend:** HTML, CSS, and vanilla JavaScript
- **Application server:** Uvicorn
- **Testing:** Python `unittest` with black-box HTTP requests
- **Data:** Deterministic synthetic student, driver, bus, route, stop, attendance, and notification records

The frontend communicates only with versioned backend APIs. Authorization and business rules are enforced by the backend rather than relying on frontend visibility controls.

## Core functional requirements

### Authentication and roles

- Provide Driver, Admin, and Parent login options.
- Enforce access permissions on every protected backend endpoint.
- Open the selected portal in a new browser tab while keeping the login page available.
- Store password hashes rather than plaintext passwords.
- Use expiring sessions and invalidate sessions during logout.

### Driver portal

- Show only the authenticated driver's assigned bus, route, stops, and students.
- Display an understandable route map with start point, ordered stops, and end point.
- Allow the driver to start, complete, and restart a trip.
- Show immediate progress and success feedback for trip actions.
- Enable location and student-event controls only while a trip is active.
- Send driver updates to the shared backend so admin and parent views receive consistent information.

### Admin portal

- Present all active routes and their assigned resources.
- Display trip states, reported locations, capacity information, students onboard, and recent events.
- Keep information understandable through clear labels, status colors, cards, and summaries.

### Parent portal

- Restrict each parent to their linked child.
- Show the child's current journey status, route, bus, latest location, and event timeline.
- Reflect updates recorded by the assigned driver.

### Data and analytics

- Use synthetic data only; never include real student or guardian information.
- Provide deterministic Indian demonstration names.
- Preserve assignment, attendance, notification, trip, and event history unless the database is intentionally regenerated.
- Present analytics in a readable form with definitions for calculated metrics.

## Development issues encountered and professional resolutions

### 1. Preserving features during interface improvements

**Issue:** Visual redesigns can unintentionally remove navigation, dashboard sections, actions, or data that already work.

**Resolution:** Treat existing behavior as a contract. Inventory routes, controls, API calls, and displayed data before changing layouts. Make focused changes and run regression tests afterward.

**Effective prompt pattern:**

> Improve the readability and visual hierarchy of this page while preserving every existing feature, route, API call, button, data section, and permission rule. Before editing, identify the current functional elements. After editing, verify that each one remains available.

### 2. Making analytics understandable at a glance

**Issue:** Raw metrics, progress bars, and route records can be difficult to understand when labels, values, and explanations are visually crowded.

**Resolution:** Group related information into cards, apply a consistent color palette, separate values from definitions, and clearly label calculated or descriptive metrics.

**Effective prompt pattern:**

> Redesign the analytics page for quick comprehension. Use a consistent accessible color palette, summary cards, readable spacing, clear metric names, short explanations, and responsive layouts. Do not change the underlying calculations or remove data.

### 3. Connecting three portals through one source of truth

**Issue:** Driver, admin, and parent views can become inconsistent if each portal stores or calculates status independently.

**Resolution:** Record trip, location, and student events in the backend. Each portal reads role-appropriate views of the same records. The frontend should never act as the authoritative data store.

**Effective prompt pattern:**

> Implement a shared backend event flow where driver updates are stored once and exposed through role-specific APIs. Admins may see all operational data, drivers only their assignments, and parents only their linked child. Add authorization tests for every boundary.

### 4. Securely opening portals in a new tab

**Issue:** Opening a portal in another tab can lose the authenticated session or expose credentials in the URL.

**Resolution:** Transfer only the issued session data through browser-controlled storage, never place credentials or tokens in query parameters, and keep backend role validation active.

**Effective prompt pattern:**

> After successful login, open the correct role portal in a new tab and leave the login page open. Do not transmit credentials or session tokens in the URL. Verify the new tab has an authenticated session and cannot access another role's endpoints.

### 5. Supporting every seeded driver account

**Issue:** A single hard-coded driver account does not demonstrate whether assignments and access restrictions work for the full fleet.

**Resolution:** Generate one application account per seeded driver, link it to the matching driver record, and test that every account sees only its assigned route, bus, and students.

**Effective prompt pattern:**

> Create access for every seeded driver using a consistent demonstration credential policy. Link each account to its driver record and add parameterized tests confirming that all drivers can sign in and cannot view another driver's assignment.

### 6. Trip start status not appearing immediately

**Issue:** The backend successfully starts a trip, but the interface may appear stuck because success feedback is cleared during refresh or a disabled button continues to show a waiting cursor.

**Resolution:** Separate the temporary request state from the completed trip state. Show **Starting…** only while the request is pending, then show **Trip started**, the start time, enabled trip controls, and a persistent success message. Use a progress cursor only during the active request.

**Effective prompt pattern:**

> Make Start Trip provide immediate and reliable feedback. While the API request is pending, disable duplicate submissions and show “Starting…”. On success, show “Trip started”, display the start time, enable location and student actions, and preserve the success message after refreshing dashboard data. Restore the prior state on failure.

### 7. Starting a new trip after completion

**Issue:** A completed daily trip can leave the driver portal locked in a terminal state even when another demonstration run is required.

**Resolution:** Define explicit trip-state transitions and allow a completed trip to begin a new run while preserving historical events and resetting only the current-run student states.

**Effective prompt pattern:**

> Implement explicit `not_started`, `in_progress`, and `completed` trip states. Permit “Start another trip” after completion, preserve historical events, and ensure the new run initially shows all assigned students as waiting.

### 8. Navigation leading to an unexpected page

**Issue:** A shared brand link can point to an old root page instead of the current role portal.

**Resolution:** Give each role page a safe role-specific brand destination and test the navigation links as part of the regression suite.

**Effective prompt pattern:**

> Audit all SmartRoute brand and navigation links. The login brand should return to login, while each role portal brand should return to that same portal. Add automated checks so future layout changes cannot reintroduce the issue.

### 9. Reproducible setup and database safety

**Issue:** Generic setup instructions may omit the correct working directory, dependency file, database-reset warning, ports, credentials, or test environment.

**Resolution:** Verify setup from a clean copy and document first-time setup separately from normal startup. Explain that seed generation replaces the database and run tests against a copied database.

**Effective prompt pattern:**

> Write setup instructions only after executing them in a clean environment. Include the exact project root, virtual-environment commands, dependency installation, optional database generation with a data-loss warning, server command, URLs, health check, demo workflow, isolated test database, expected test result, shutdown, and troubleshooting.

## Reusable master prompt for future development

Use the following prompt when asking an AI coding assistant to work on this repository:

```text
You are contributing to SmartRoute AI, a FastAPI, SQLAlchemy, SQLite, HTML, CSS, and vanilla JavaScript school transport application with Driver, Admin, and Parent portals.

Goal:
[Describe the required feature or bug fix in one clear paragraph.]

Required workflow:
1. Inspect the current implementation, data model, API contract, and tests before editing.
2. Preserve all existing features unless removal is explicitly requested.
3. Keep the backend as the source of truth and enforce role permissions server-side.
4. Use only synthetic data and do not introduce secrets or personal information.
5. Make the smallest cohesive implementation that solves the problem.
6. Provide clear loading, success, empty, and error states in the UI.
7. Keep layouts responsive and accessible, with understandable labels and keyboard-compatible controls.
8. Add or update regression tests for success cases, failure cases, authorization boundaries, and relevant UI assets.
9. Run syntax checks, database validation when applicable, and the full regression suite.
10. Report the files changed, behavior verified, test results, and any remaining limitations.

Acceptance criteria:
[List observable outcomes that must be true for the task to be complete.]

Constraints:
[List any files, APIs, database records, visual styles, or behaviors that must remain unchanged.]
```

## Focused prompt templates

### Bug investigation

```text
Diagnose this behavior before changing code: [describe the behavior]. Reproduce it, trace the frontend event, API request, backend state change, and refreshed UI state. Explain the root cause, implement the smallest safe fix, and add a regression test that fails before the fix and passes afterward.
```

### New feature

```text
Add [feature] for [role]. Define the user-visible workflow, backend API contract, validation rules, authorization requirements, database changes, loading/error/success states, and test cases. Preserve existing portals and verify cross-role data visibility.
```

### UI improvement

```text
Improve the clarity and responsiveness of [page or component]. Preserve every existing action and data point. Use semantic HTML, accessible controls, consistent status colors, concise labels, readable spacing, and clear mobile behavior. Verify the page at desktop and narrow viewport sizes.
```

### Security and authorization review

```text
Review authentication and authorization for [workflow]. Confirm that frontend restrictions are backed by server-side role checks, sessions expire and logout invalidates them, tokens are not placed in URLs, passwords are hashed, and users cannot access records belonging to another role or assignment. Add negative authorization tests.
```

### Regression testing

```text
Create black-box regression coverage for [workflow]. Test valid behavior, invalid input, repeated actions, authorization boundaries, state transitions, asset availability, and data visibility in every affected portal. Run tests against an isolated copied database and report the exact results.
```

## Human and AI responsibilities

### Human developer responsibilities

- Define the real operational need and priority.
- Confirm terminology, workflows, visual preferences, and acceptance criteria.
- Decide which trade-offs are acceptable.
- Review security-sensitive behavior and production readiness.
- Approve database resets, deployments, releases, and external integrations.
- Perform final user acceptance testing with realistic scenarios.

### AI assistant responsibilities

- Inspect existing code and avoid assumptions that conflict with the repository.
- Translate requirements into scoped implementation tasks.
- Identify likely regressions and preserve unrelated functionality.
- Implement code, tests, and documentation consistently.
- Explain root causes and trade-offs in plain language.
- Verify work with repeatable commands and observable results.
- Avoid exposing secrets, real personal data, or private conversation content.

### Shared collaboration loop

1. The human states the desired outcome and constraints.
2. The AI inspects the existing system and reports important findings.
3. The human clarifies any product decision that materially changes scope.
4. The AI implements a focused change and automated coverage.
5. The AI reports verification evidence and known limitations.
6. The human performs acceptance testing and provides specific feedback.
7. Both repeat the loop until the observable acceptance criteria are satisfied.

## Definition of done

A SmartRoute AI change is complete when:

- The requested behavior is visible and understandable to the intended role.
- Existing portal features continue to work.
- Backend validation and role authorization are enforced.
- Loading, success, failure, and empty states are handled.
- Synthetic data remains internally consistent.
- Relevant automated tests pass against an isolated database.
- Python and JavaScript syntax checks pass.
- Setup or user documentation is updated when the workflow changes.
- No credentials, real personal data, generated caches, or temporary test artifacts are introduced into version control.

## Professional collaboration principle

Human expertise supplies product intent, operational context, judgment, and final accountability. AI assistance supplies rapid code analysis, implementation support, test generation, documentation, and repeatable verification. The strongest result comes from short feedback cycles, explicit acceptance criteria, evidence-based testing, and careful preservation of working functionality.
