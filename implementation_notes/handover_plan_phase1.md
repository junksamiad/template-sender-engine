# Handover Plan - Phase 1: IaC Consolidation, Testing & Basic CI/CD

## 1. Overall Goal

The primary objective is to establish a robust, automated, and reliable development and deployment lifecycle for the AI Multi-Comms Engine. This involves:

1.  Managing all AWS infrastructure using Infrastructure as Code (IaC) via AWS SAM for consistency across environments.
2.  Implementing a comprehensive automated testing suite (Unit, Integration) to ensure code quality and prevent regressions.
3.  Setting up a basic Continuous Integration/Continuous Deployment (CI/CD) pipeline to automate testing and deployment to the development environment.

## 2. Current Status (as of 2025-04-10)

*   **Repository:** `template-sender-engine` (single codebase model).
*   **Git Branches:**
    *   `main`: Clean initial commit representing the working application code.
    *   `develop`: Created from `main`, contains merged IaC definitions and fixes.
    *   Local branches: Currently checked out on `develop`.
*   **Infrastructure Definition:**
    *   `template.yaml` (in root) defines the complete application infrastructure (API GW, Lambdas, Tables, Queues, Roles, Alarms, SNS, etc.) using AWS SAM.
    *   The template is parameterized (e.g., `EnvironmentName`, `LogLevel`) to support multiple environments.
*   **AWS Deployments:**
    *   **`prod` Environment:** Successfully deployed using `sam deploy --stack-name ai-multi-comms-prod --parameter-overrides EnvironmentName=prod ...`. Infrastructure is managed by the `ai-multi-comms-prod` CloudFormation stack. End-to-end flow validated via `curl` test.
    *   **`dev` Environment:** Currently exists on AWS but consists of resources created **manually via the AWS CLI** during earlier development phases. It is **not** managed by CloudFormation/SAM.
*   **Code Status:**
    *   Codebase uses environment variables (`os.environ.get`) to read resource names (Tables, Queues) and configurations, making it environment-agnostic.
    *   Includes fixes for Lambda permissions, Base64 request body handling, and Python imports identified during `prod` deployment troubleshooting.
*   **Testing:**
    *   Test plans created: `tests/unit_test_plan.md`, `tests/integration_test_plan.md`, `tests/e2e_test_plan.md`.
    *   Testing strategy guide created: `tests/testing_guide.md`.
    *   No automated tests have been implemented yet.
    *   Manual E2E testing performed via `samples/e2e_test_curl.sh` (updated for `prod`).
*   **Scripts:**
    *   `src_dev/docs & setup/onboarding-scripts/create_company_record.py`: Updated to target `dev` or `prod` tables via `DEPLOY_ENV` variable.
    *   `src_dev/docs & setup/onboarding-scripts/create_channel_secrets.py`: Created to interactively generate secret names for `dev` or `prod`.

## 3. Next Steps (Detailed Plan)

### Step 1: Recreate `dev` Environment using SAM

*   **Purpose:** Achieve Infrastructure as Code (IaC) consistency between `dev` and `prod` environments. Ensure the `dev` environment is managed by CloudFormation/SAM, identical in structure (but different in configuration) to `prod`.
*   **Branching:** Create a new feature branch from `develop`, e.g., `git checkout develop && git checkout -b feature/recreate-dev-sam`.
*   **Prerequisites:**
    *   SAM CLI installed and configured with AWS credentials.
    *   `template.yaml` (on the `develop` branch) is finalized and validated through the successful `prod` deployment.
*   **Actions:**
    1.  **Manual Cleanup (AWS Console/CLI):**
        *   Carefully identify and **delete** all existing AWS resources associated with the *manually created* `dev` environment. This includes:
            *   Lambda functions (`channel-router-dev`, `whatsapp-channel-processor-dev`).
            *   IAM Roles & Policies (`ai-multi-comms-channel-router-dev-role`, `ai-multi-comms-whatsapp-channel-processor-dev-role`, associated policies).
            *   DynamoDB tables (`company-data-dev`, `conversations-dev`).
            *   SQS Queues & DLQs (`ai-multi-comms-whatsapp-queue-dev`, `-dlq-dev`, and potentially email/sms variants).
            *   API Gateway (`ai-multi-comms-dev-api`, including stages, resources, methods, API Keys, Usage Plans associated only with this dev API).
            *   Any other related resources (CloudWatch Alarms, SNS topics if manually created for dev).
        *   **Caution:** Double-check resource names before deletion to avoid impacting the `prod` environment or unrelated resources.
    2.  **Deploy `dev` Stack via SAM:**
        *   Run the `sam deploy` command targeting a new stack for dev:
            ```bash
            sam deploy \
                --template-file template.yaml \
                --stack-name ai-multi-comms-dev \
                --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
                --resolve-s3 \
                --parameter-overrides EnvironmentName=dev LogLevel=DEBUG # Or INFO
            ```
        *   Monitor the deployment in the CloudFormation console until `CREATE_COMPLETE`.
    3.  **Configure `dev` Specifics:**
        *   Create a `dev` API Key (e.g., `test-company-dev`) and Usage Plan (e.g., `dev-usage-plan`) via AWS Console/CLI.
        *   Associate the new key with the plan and the plan with the `dev` stage of the *newly created* `ai-multi-comms-api-dev`.
        *   Ensure secrets exist in Secrets Manager with `-dev` suffixes (e.g., `ai-multi-comms/openai-api-key/whatsapp-dev`) and contain appropriate *development* credentials.
        *   Use the `create_company_record.py` script (with `DEPLOY_ENV=dev` or no env var set) to populate the `ai-multi-comms-company-data-dev` table, ensuring secret references point to the `-dev` secrets.
        *   Subscribe an appropriate endpoint (e.g., dev team email) to the `ai-multi-comms-critical-alerts-dev` SNS topic.
    4.  **Test `dev` Environment:**
        *   Update `samples/e2e_test_curl.sh` with the new `dev` API Gateway URL and `dev` API Key.
        *   Run the script and verify end-to-end functionality (WhatsApp message received).
        *   Check CloudWatch logs for the new `-dev` Lambdas.
*   **Merge:** If deployment and testing are successful, merge the `feature/recreate-dev-sam` branch (although it might not contain code changes, only confirmation of process) into `develop`.

### Step 2: Implement Testing Framework

*   **Purpose:** Create automated tests based on the existing test plans (`tests/unit_test_plan.md`, `tests/integration_test_plan.md`) to validate code logic and component interactions, enabling faster feedback and safer refactoring.
*   **Branching:** Perform work on separate feature branches created from `develop` (e.g., `feature/add-unit-tests-router`, `feature/add-router-integration-tests`).
*   **Unit Tests:**
    *   **Location:** Create test files within the `tests/unit/` directory structure (e.g., `tests/unit/channel-router/utils/test_request_parser.py`).
    *   **Tools:** Use `pytest` for test running/assertions and `moto` for mocking AWS services (Boto3 calls).
    *   **Scope:** Focus on testing individual functions/methods in isolation within both `channel-router` and `whatsapp-channel-processor` Lambda code (`core/`, `services/`, `utils/`). Mock all external dependencies.
    *   **Execution:** Run locally using `pytest tests/unit/`.
*   **Integration Tests:**
    *   **Location:** Create test files within `tests/integration/` (e.g., `tests/integration/channel-router/test_router_sqs.py`).
    *   **Tools:** Use `pytest`, AWS SAM CLI (`sam local invoke`, `sam local start-api`), potentially `boto3` for test setup/verification against AWS.
    *   **Scope:** Test interactions between components and *real* (or simulated) AWS services, primarily targeting the **`dev`** environment resources created by SAM in Step 1.
        *   Example: Test API Gateway -> Router Lambda integration using `sam local start-api`.
        *   Example: Test Router Lambda -> DynamoDB interaction using `sam local invoke` pointing to `ai-multi-comms-company-data-dev` table.
        *   Example: Test Processor Lambda -> Secrets Manager interaction using `sam local invoke` pointing to `dev` secrets.
    *   **Execution:** Run locally using `pytest` orchestrating SAM CLI commands or direct Boto3 interaction.
    *   **Reference:** Follow `tests/testing_guide.md` for the strategy on using SAM local against real resources.
*   **Merge:** Merge completed test branches into `develop` after they pass locally.

### Step 3: Set up Basic CI/CD Pipeline

*   **Purpose:** Automate the process of running unit tests and deploying validated code to the `dev` environment.
*   **Branching:** Create a new feature branch from `develop` (e.g., `feature/setup-basic-ci`).
*   **Tool:** GitHub Actions (assuming code is hosted on GitHub). Alternative: AWS CodePipeline/CodeBuild.
*   **Workflow File:** Create `.github/workflows/cicd.yml` (or similar).
*   **Trigger:** Configure the workflow to trigger on pushes or merges to the `develop` branch.
*   **Workflow Steps:**
    1.  **Checkout Code:** Use `actions/checkout`.
    2.  **Setup Python:** Use `actions/setup-python`.
    3.  **Install Dependencies:** Install project dependencies (`pip install -r requirements.txt` if applicable for tools) and test dependencies (`pip install pytest moto boto3 ...`).
    4.  **Run Linters (Optional):** e.g., `flake8`.
    5.  **Run Unit Tests:** Execute `pytest tests/unit/`. Fail the workflow if tests fail.
    6.  **Configure AWS Credentials:** Use `aws-actions/configure-aws-credentials` to securely provide AWS credentials (stored as GitHub Actions secrets) needed for SAM deployment.
    7.  **Install SAM CLI:** Ensure SAM CLI is available on the runner.
    8.  **Run `sam build` (Optional but Recommended):** Explicitly build artifacts: `sam build --use-container`.
    9.  **Run `sam deploy` to `dev`:** Execute the `sam deploy` command targeting the `dev` stack, passing `EnvironmentName=dev`:
        ```bash
        sam deploy \
            --stack-name ai-multi-comms-dev \
            --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
            --resolve-s3 \
            --parameter-overrides EnvironmentName=dev LogLevel=INFO \
            --no-confirm-changeset # Auto-approve deployment to dev
        ```
*   **Merge:** Merge the `feature/setup-basic-ci` branch into `develop`.

## 4. Future Considerations

*   Expand CI/CD pipeline to include integration tests (potentially against `dev` after deployment).
*   Implement promotion strategy to `prod` (e.g., trigger on merge to `main`, require manual approval before `sam deploy` to `prod`).
*   Refine `.gitignore` to exclude build artifacts properly.
*   Consider adding API Key/Usage Plan management to the SAM template (using `AWS::ApiGateway::ApiKey`, `UsagePlan`, `UsagePlanKey` resources). 