# Deployment Workflow Handover (AI Multi-Comms Engine)

## 1. Overview

This document describes the current infrastructure setup, version control strategy, and deployment workflow for the AI Multi-Comms Engine. The primary goal is to maintain consistency between environments using Infrastructure as Code (IaC) and prepare for future CI/CD implementation.

## 2. Infrastructure Setup: AWS SAM

*   **Tool:** AWS Serverless Application Model (SAM) is used for defining and deploying all AWS infrastructure resources.
*   **Template:** The complete infrastructure is defined in the `template.yaml` file located in the project root.
*   **Management:** Both `dev` and `prod` environments are managed by separate CloudFormation stacks created using this single `template.yaml` file.
*   **Parameterization:** The `template.yaml` uses parameters (defined in the `Parameters:` section) to differentiate between environments:
    *   `EnvironmentName` (String, Default: `dev`): Used to suffix resource names (e.g., `ai-multi-comms-prod`, `ai-multi-comms-dev`) and configure environment-specific settings.
    *   `LogLevel` (String, Default: `INFO`): Sets the logging level for Lambda functions.
    *   `ProjectPrefix` (String, Default: `ai-multi-comms`): Used as a prefix for most resource names.
    *   Other parameters control Lambda memory/timeout.
*   **Environments Deployed:**
    *   `prod`: Managed by CloudFormation stack `ai-multi-comms-prod`. Deployed via `sam deploy --stack-name ai-multi-comms-prod --parameter-overrides EnvironmentName=prod ...`.
    *   `dev`: Managed by CloudFormation stack `ai-multi-comms-dev`. Deployed via `sam deploy --stack-name ai-multi-comms-dev --parameter-overrides EnvironmentName=dev ...`.

## 3. Version Control: Git Workflow (Single Repository)

*   **Repository:** A single Git repository (`template-sender-engine` on GitHub) holds all application code, IaC templates, tests, documentation, and scripts.
*   **Branching Strategy:**
    *   **`main`:** Represents the stable, production-ready codebase. Reflects what is (or should be) deployed to the `prod` environment. Receives merges *only* from `develop` after thorough testing.
    *   **`develop`:** The main integration branch for ongoing development. Represents the code state for the next potential release and is the source for deployments to the `dev` environment. All feature branches are merged into `develop` first.
    *   **`feature/*`:** Used for developing new features or bug fixes. Branched *from* `develop`. Work is done in isolation here. Merged back *into* `develop` via Pull Requests after local testing and review.

## 4. Build Process: SAM Build with Container

*   **Command:** `sam build --use-container`
*   **Purpose:** To reliably package Lambda function code and dependencies (from `requirements.txt` files within each Lambda's directory) before deployment.
*   **Mechanism:** Uses Docker locally to create a build environment that closely matches the AWS Lambda execution environment, ensuring dependencies are compiled and packaged correctly.
*   **Output:** Creates build artifacts in the `.aws-sam/build/` directory (including a processed `template.yaml`).
*   **When:** This command should typically be run *before* `sam deploy`, especially when dependencies change or to ensure a clean build.

## 5. Deployment Process: SAM Deploy

*   **Command:** `sam deploy ...`
*   **Purpose:** To create or update the AWS resources defined in `template.yaml` via CloudFormation.
*   **Mechanism:** Takes the template and packaged code artifacts (usually from `.aws-sam/build/`), creates a CloudFormation Change Set, and executes it.
*   **Targeting Environments:** The target environment is determined by:
    1.  `--stack-name`: Specifies the CloudFormation stack to create or update (e.g., `ai-multi-comms-dev` or `ai-multi-comms-prod`).
    2.  `--parameter-overrides`: Sets the values for parameters defined in `template.yaml`. Crucially, `EnvironmentName=dev` or `EnvironmentName=prod` is used here to control resource naming and configuration within the template logic.
*   **IAM Capabilities:** Requires `--capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM` because the template creates named IAM roles and policies.
*   **Code Upload:** Uses `--resolve-s3` to automatically upload packaged Lambda code to the SAM-managed S3 bucket (`aws-sam-cli-managed-default...`).
*   **Current Workflow Trigger:** Deployments are currently performed manually via the terminal after merging code to the appropriate branch (`develop` for `dev` environment, `main` for `prod` environment).

## 6. Configuration Handling

*   **Infrastructure:** Environment-specific infrastructure details (resource names, some settings) are handled by the `EnvironmentName` parameter and intrinsic functions (`!Sub`, `!Ref`) within `template.yaml`.
*   **Application:** Lambda functions read configuration (like target DynamoDB table names, SQS Queue URLs, specific external service parameters) from **Environment Variables**.
*   **Setting Env Vars:** These Lambda environment variables are set during deployment by the `sam deploy` command, using values derived from the `template.yaml` parameters or resource references (e.g., `WHATSAPP_QUEUE_URL: !Ref WhatsAppQueue`).
*   **Secrets:** Sensitive credentials (API Keys for OpenAI, Twilio, SendGrid) are stored in AWS Secrets Manager. Secrets are named using a convention including the environment (`...-dev` or `...-prod`). The *references* (names) of the secrets to use are stored in the `company-data-${EnvironmentName}` DynamoDB table and read by the Lambda at runtime.

## 7. Next Steps (from handover_plan_phase1.md)

1.  **Implement Testing Framework:** Begin writing unit and integration tests based on the plans in the `tests/` directory.
2.  **Set up Basic CI/CD:** Implement a pipeline (e.g., GitHub Actions) to automate unit testing and deployment to the `dev` environment on merges to the `develop` branch. 