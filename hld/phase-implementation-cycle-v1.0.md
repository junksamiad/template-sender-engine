# Phase Implementation Cycle

This document outlines the standard cycle of steps to follow during each phase of implementation. Following this consistent approach will ensure proper development, testing, documentation, and deployment practices throughout the project.

## Implementation Cycle Steps

### 1. Setup New Implementation / Functionality Locally
- Use the existing virtual environment
- Implement new features according to the phase requirements
- Follow the architecture and design patterns established in the roadmap
- Ensure code quality and adherence to project standards

### 2. Create and Run Local Tests
- Develop comprehensive test cases for the new functionality
- Run tests in the local environment
- Log test results in the appropriate phase testing folder
- Debug and fix any issues until all tests pass
- Only proceed when all functionality is working correctly

### 3. Update Documentation
- Update progress information in roadmap and phase docs
- Use green emoji ticks ✅ to highlight completed items
- Update any relevant diagrams to reflect the current state
- Document any challenges encountered and their solutions
- Note any deviations from the original plan and their justification

### 4. Git Repository Management
- **Branch Management**:
  - For initial setup: Create the main repository if not already done
  - For each new phase: Create a dedicated phase branch from the previous phase branch, not from main
    ```bash
    # Example: When starting Phase 1, branch from Phase 0
    git checkout phase-0
    git checkout -b phase-1
    
    # Example: When starting Phase 2, branch from Phase 1
    git checkout phase-1
    git checkout -b phase-2
    ```
  - Always branch from the most recent phase to ensure you have the latest code
  - Do not pull from remote before creating a new branch as the local code is already up-to-date

- **Commit Practices**:
  - Make incremental, logical commits during development
  - Follow proper commit message conventions
    ```bash
    git commit -m "Phase N, Section X.Y: Brief description of changes"
    ```
  - Include relevant documentation updates with code changes

- **Phase Completion**:
  - When the phase is complete, push the branch to the remote repository
    ```bash
    git push -u origin phase-N
    ```
  - Create a pull request against the previous phase branch, not main
  - The previous phase branch serves as the source of truth for completed work
  - Main branch is only updated at major milestones

### 5. Deploy to AWS
- Use CDK to deploy new functionality to AWS
- Consider using CDK diff or other quick redeploy tools for incremental updates
- Ensure all necessary AWS resources are properly configured
- Verify deployment was successful

### 6. Create and Run AWS Tests
- Develop test cases specific to the AWS environment
- Run tests against the deployed infrastructure
- Log test results in the appropriate phase testing folder
- Debug and fix any issues until all tests pass
- Only proceed when all functionality is working correctly in AWS

### 7. Update AWS Documentation
- Update progress information in roadmap, phase, and AWS docs
- Use green emoji ticks ✅ to highlight completed items
- Update any relevant AWS diagrams to reflect the current state
- Document any AWS-specific challenges encountered and their solutions
- Note any deviations from the original deployment plan

### 8. Final Phase Review and Handoff
- Verify all implementation steps are complete and documented
- Ensure all tests are passing in both local and AWS environments
- Confirm all phase documentation is updated with green ticks
- Create comprehensive summary of the phase implementation
- Request formal review from the human supervisor
- Address any feedback or requested changes
- Once approved, the phase is considered complete

## Phase Completion

When all steps in the implementation cycle have been completed successfully, the phase can be considered complete. A final review should be conducted before moving on to the next phase to ensure all objectives have been met and properly documented. The following checklist should be completed:

- ☐ All implementation tasks marked with green ticks (✅)
- ☐ All local and AWS tests passing successfully
- ☐ All documentation updated appropriately
- ☐ All code committed and pushed to the repository
- ☐ Pull request created for the phase branch
- ☐ Phase review conducted and approved
- ☐ New branch created for the next phase directly from current phase branch 