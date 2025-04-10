# AI Multi-Comms Engine - Testing Strategy Guide

## 1. Overview

This document outlines the agreed-upon strategy for testing the AI Multi-Comms Engine application within the `src_dev` environment. It defines the different levels of testing, their scope, tools, and execution environment.

The strategy employs three main types of tests:

1.  **Unit Tests:** Verify individual code components in isolation.
2.  **Integration Tests:** Verify interactions between components and AWS services, primarily run locally using AWS SAM CLI.
3.  **End-to-End (E2E) Tests:** Verify the complete system flow in a deployed AWS environment.

## 2. Unit Testing

*   **Goal:** Ensure individual functions/methods/classes work correctly according to their specifications. Catch bugs in specific code units early.
*   **Scope:** Smallest testable parts of the code within each Lambda function's modules (`utils/`, `services/`, `core/`).
*   **Environment:** Purely local. No AWS connection or credentials required.
*   **Tools:** `pytest` framework, `moto` library (for mocking AWS Boto3 clients), `unittest.mock` (for mocking other libraries like `openai`, `twilio`).
*   **Execution:** Run locally via `pytest`. Should be fast and executable without network access.
*   **Mocking:** *All* external dependencies (AWS services via Boto3, OpenAI API, Twilio API) **must** be mocked.
*   **Reference:** See `tests/unit_test_plan.md` for detailed test cases.

## 3. Integration Testing

*   **Goal:** Verify the interactions, data contracts, and permissions *between* system components and *with* AWS services.
*   **Scope:** Interactions like API Gateway <-> Lambda, Lambda <-> DynamoDB, Lambda <-> SQS, Lambda <-> Secrets Manager.
*   **Environment:** Primarily local, leveraging **AWS SAM CLI** (`sam build`, `sam local invoke`, `sam local start-api`).
*   **AWS Interaction:**
    *   SAM local commands can be configured to interact with **real deployed AWS resources** in the development environment (e.g., `company-data-dev` table, `ai-multi-comms-whatsapp-queue-dev`, Secrets Manager). This is achieved by:
        1.  Ensuring your local environment has valid AWS credentials configured (e.g., via environment variables, AWS config files).
        2.  Providing appropriate environment variables to the `sam local invoke` or `sam local start-api` commands (e.g., via `--env-vars env.json`) that contain the actual names/ARNs/URLs of the deployed AWS resources.
    *   This approach validates IAM permissions, resource configurations, and real service interactions locally.
    *   Alternatively, local simulation tools like `LocalStack` could be used if desired, but the primary approach involves targeting real dev resources via SAM local for higher fidelity.
*   **Tools:** `pytest` (for test structure/assertions), `boto3` (for potential test setup/verification against AWS), AWS SAM CLI, `curl` (for testing `sam local start-api`).
*   **Execution:** Run locally via `pytest` scripts that orchestrate `sam local invoke` or direct interaction with `sam local start-api`.
*   **Mocking:** Mocking is minimal. External *third-party* APIs (OpenAI, Twilio) might still be mocked at this stage to avoid costs/side effects, but interactions between internal components and AWS services should use the real (dev) services via SAM local.
*   **Reference:** See `tests/integration_test_plan.md` for detailed test cases.

## 4. End-to-End (E2E) Testing

*   **Goal:** Validate the entire system flow from start to finish in a fully deployed environment, simulating real user interaction.
*   **Scope:** The complete request lifecycle: Client -> API Gateway -> Channel Router -> SQS -> Channel Processor -> DynamoDB -> Secrets Manager -> OpenAI -> Twilio -> Final DynamoDB update.
*   **Environment:** Fully deployed stack on AWS (e.g., the `dev` environment).
*   **AWS Interaction:** Interacts with all live, deployed AWS resources and external services (OpenAI, Twilio).
*   **Tools:** `curl`, Scripting (e.g., Python with `requests` and `boto3`), AWS Console/CLI for verification.
*   **Execution:** Run manually or via automated scripts against the deployed HTTP endpoint.
*   **Mocking:** No mocking. Tests run against the actual deployed system and external services.
*   **Reference:** See `tests/e2e_test_plan.md` for detailed test cases.

## 5. Rationale Summary

This tiered approach provides comprehensive test coverage:

*   **Unit tests** ensure code correctness quickly and cheaply.
*   **Integration tests** (using SAM local against real dev resources) provide high confidence in component interactions and AWS configurations *without* requiring full deployment for every test, significantly speeding up the development loop for integration issues.
*   **E2E tests** give the final validation that the entire deployed system works as expected for real user scenarios. 