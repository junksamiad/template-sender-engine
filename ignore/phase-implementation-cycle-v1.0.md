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

### 4. Commit Changes to Git Repository
- For Phase 1: Create a new git repository if not already done
- For subsequent phases: Branch off main branch with phase name
  - Example: `phase-2` branch for Phase 2
- Follow proper commit message conventions
- Include appropriate documentation updates in commits

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

### 8. Commit Final Changes
- Commit all final changes to the git repository on the relevant phase branch
- Include updated documentation and test results
- Consider creating a pull request for merging into the main branch when the phase is complete

## Phase Completion

When all steps in the implementation cycle have been completed successfully, the phase can be considered complete. A final review should be conducted before moving on to the next phase to ensure all objectives have been met and properly documented. 