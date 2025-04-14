# Recommendations for Next Service Development (Lessons Learned)

This document summarizes key recommendations and best practices derived from the development and CI/CD implementation of the AI Multi-Comms Engine (`template-sender-engine`), intended to streamline the setup of future related microservices.

## 1. Project Structure & Python Imports (CRITICAL)

*   **Problem:** Significant effort was spent resolving conflicts between local `pytest` imports and AWS Lambda runtime imports (`ImportError: attempted relative import with no known parent package`). Folder naming also caused some confusion.
*   **Solution/Recommendation:**
    *   **Source Folder:** Use a standard `src` directory for all application source code, rather than environment-specific names like `src_dev`.
    *   **Avoid Reserved Names:** Do not use folder names that might conflict with common terms or keywords, such as `lambda`.
    *   **Lambda Packaging:** Adopt the **`lambda_pkg` structure** from the start for all Python Lambda functions within the `src` directory.
        *   Create a `lambda_pkg` subdirectory inside your main Lambda function directory (e.g., `src/my_new_service/app/lambda_pkg/`).
        *   Place **all** Python source code (`index.py`, `utils/`, `services/`, etc.) **inside** `lambda_pkg`.
        *   Ensure `__init__.py` exists in `lambda_pkg` and all subdirectories intended as packages.
        *   Write **all intra-function imports** within `lambda_pkg` using **explicit relative imports** (e.g., `from .utils import helper`, `from .services import db_service`).
        *   Place the Lambda's `requirements.txt` file in the parent directory (e.g., `src/my_new_service/app/requirements.txt`).
*   **Reference:** `implementation_notes/python_lambda_imports_setup.md`

## 2. Infrastructure as Code (IaC) - SAM

*   **Lesson:** Manually creating resources initially led to inconsistencies and required a full rebuild using IaC later. Resource naming conventions needed careful consideration.
*   **Recommendation (Infrastructure Definition):**
    *   **Define via SAM:** Define **all** AWS resources (Lambda, DynamoDB, SQS, API GW, IAM Roles, etc.) for **all** environments (`dev`, `prod`) within a single AWS SAM `template.yaml` file from the beginning.
    *   **Phased Rollout (Optional):** While full IaC from the start is ideal, an alternative approach during initial exploration is to build manually via AWS CLI, verify functionality, and *then* translate the working infrastructure into the `template.yaml`. **Caution:** This requires careful tracking and can delay catching IaC-related issues. Full IaC from day one is generally preferred for consistency.
    *   **Parameterization:** Use SAM Parameters (e.g., `EnvironmentName`, `LogLevel`) extensively to differentiate environment configurations (resource names, settings). This is the primary method for managing `dev` vs `prod`.
    *   **Resource Naming:** Plan resource names carefully beforehand. Use the `EnvironmentName` parameter consistently to suffix resources (e.g., `MyTable-${EnvironmentName}`, resulting in `MyTable-dev`, `MyTable-prod`). Stick to a convention like `-dev` and `-prod`.
    *   **Linking Resources:** Use SAM intrinsic functions (`!Sub`, `!Ref`, `!GetAtt`) to link resources within the template (e.g., passing a Queue ARN to a Lambda's environment variables).
    *   **Deployment Command:** Deploy environments using `sam deploy --stack-name my-service-${EnvironmentName} --parameter-overrides EnvironmentName=prod ...`.

## 3. CI/CD Pipeline Setup (GitHub Actions)

*   **Lesson:** Setting up CI/CD involved debugging permissions, test configurations, and deployment flags iteratively.
*   **Recommendation:** Implement CI/CD early in the development process.
    *   **Structure:** Use separate workflow files for `dev` and `prod` (`dev_cicd.yml`, `prod_cicd.yml`).
    *   **Triggers:** Configure triggers for both `push` (for deployment) and `pull_request` (for checks) against the respective target branches (`develop`, `main`).
    *   **Jobs:** Separate jobs for `pr_checks` (lint, unit test, build check) and `build-and-deploy`. Use `if` conditions based on `github.event_name` to control job execution.
    *   **Build:** Use `sam build --use-container` for consistent Lambda packaging.
    *   **Deploy:** Use `sam deploy --no-confirm-changeset --no-fail-on-empty-changeset` for automated deployments.
    *   **CI Testing Fix:** The CI environment needed the `src` directory added to the Python path for tests to pass. This was achieved by adding `export PYTHONPATH=$PYTHONPATH:./src` (or `./src_dev` in the original project) within the `run` block of the unit test step in the workflow YAML files.
    *   **Local Testing Environment:** Document clearly how to replicate the CI environment locally for running tests (especially `PYTHONPATH`). Add a `README.md` to `tests/unit/`.

## 4. IAM Roles & Permissions (OIDC Focus)

*   **Lesson:** Debugging deployment role permissions was time-consuming, particularly resource scoping (`iam:GetRole`, Lambda resource patterns, SQS patterns). Trust policy conditions also required adjustment.
*   **Recommendation:**
    *   **Authentication:** Use **OIDC** (`aws-actions/configure-aws-credentials@v4` with `role-to-assume`) instead of storing AWS access keys in GitHub secrets. Set up the IAM OIDC provider once.
    *   **Separate Roles:** Create **distinct** IAM roles for GitHub Actions deployments to `dev` and `prod` environments (e.g., `MyService-GitHubActions-Deploy-Dev-Role`, `MyService-GitHubActions-Deploy-Prod-Role`).
    *   **Trust Policies:** Configure trust policies to allow assumption *only* from your specific repository and the intended branch (`ref:refs/heads/develop` or `ref:refs/heads/main`). *Note: We temporarily broadened this to `:*` for debugging; revert to specific branches for better security.*
    *   **Permissions Policies (Deployment Roles):**
        *   Create separate, dedicated permissions policies for each deployment role (dev/prod).
        *   Start with the permissions known to be needed by SAM/CloudFormation (CFN actions, S3, PassRole, specific service actions like `lambda:*`, `sqs:*`, `dynamodb:*`, `iam:*`, `logs:*`, `apigateway:*`, `secretsmanager:Get*`).
        *   **Resource Scoping:** Be mindful that CloudFormation might need broader permissions than initially obvious (e.g., `iam:GetRole` on specific Lambda execution roles). Scope resources using `${EnvironmentName}` patterns (e.g., `arn:aws:lambda:*:*:function:my-service-${EnvironmentName}-*`). Be prepared to use `"*"` for certain resources (like Lambda management) if specific patterns prove problematic during deployment, but document this clearly.
    *   **Permissions Policies (Lambda Execution Roles):** Define these *within* the SAM template. Grant only the permissions the Lambda *function itself* needs at runtime (e.g., `dynamodb:PutItem` on `MyTable-${EnvironmentName}`, `secretsmanager:GetSecretValue` on specific `prod`/`dev` secrets).

## 5. Secrets Management

*   **Lesson:** Using environment-specific secrets in AWS Secrets Manager worked well.
*   **Recommendation:**
    *   Store sensitive credentials (API keys, tokens) in AWS Secrets Manager.
    *   Use a clear naming convention incorporating the environment (e.g., `my-service/twilio-api-key-dev`, `my-service/openai-api-key-prod`).
    *   Lambda functions should read the *reference/name* of the secret to fetch from configuration (e.g., environment variables set via SAM template) rather than hardcoding names.
    *   Ensure Lambda Execution Role IAM policies only grant access to the specific secrets needed for that environment.

## 6. Testing Strategy

*   **Lesson:** Unit tests are essential but don't catch integration or deployment issues. Python path differences between local and CI were a major hurdle. Tests need to be written considering the deployment environment.
*   **Recommendation:**
    *   **Unit Tests:** Write comprehensive unit tests (`tests/unit/`) using `pytest`. Mock external dependencies (AWS services using `moto` or `unittest.mock`, external APIs using `unittest.mock`). Run these automatically in the `pr_checks` CI job. Document the local `PYTHONPATH` requirement (`tests/unit/README.md`).
    *   **Deployment-Aware Tests:** Design tests (especially unit tests involving imports) with the final Lambda deployment structure (`lambda_pkg`) and CI/CD environment (`PYTHONPATH` adjustments) in mind from the start. Research best practices for testing code intended for Lambda and GitHub Actions environments to avoid late-stage refactoring.
    *   **Integration/E2E Tests:** Plan for these early. Running them post-deployment against the `dev` environment (triggered from the `dev` CI/CD workflow) is often the most practical approach for SAM applications. Ensure tests target the correct deployed endpoints and have necessary credentials.

## 7. Configuration Management

*   **Lesson:** Using SAM parameters for infrastructure naming/config and Lambda environment variables for application config worked effectively.
*   **Recommendation:** Continue this pattern. Pass `EnvironmentName` via `--parameter-overrides`. Define Lambda environment variables within the `template.yaml` `Properties.Environment.Variables` section, often referencing SAM parameters or resource attributes (`!Ref`, `!GetAtt`).

## 8. Documentation

*   **Lesson:** Maintaining LLDs, handover notes, and progress trackers was helpful (though sometimes scattered). Documenting specific setup steps (like Python imports or local testing requirements) is vital.
*   **Recommendation:** Maintain key design documents (HLD, LLDs for major components/configurations like CI/CD, IAM, APIs). Keep progress trackers if useful during active development. Create READMEs within relevant directories (e.g., `tests/unit/`) for specific instructions. Consolidate documentation into a logical structure (like the `docs & setup/` and `implementation_notes/` folders you created). 