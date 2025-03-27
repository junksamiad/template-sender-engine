# AI Agent Implementation Guide

This document serves as a comprehensive guide for AI agents tasked with implementing the AI Multi-Communications Engine. It explains how to navigate the documentation, follow the implementation roadmap, and execute each phase correctly.

## Quick Start

### Immediate Action Steps

1. **First, familiarize yourself with the high-level architecture:**
   - Review `hld/multi-comms-engine-hld-v1.0.md` to understand the overall system
   - Examine `hld/diagrams-v1.0.md` to visualize the architecture
   - Study `hld/directory-structure-v1.0.md` to understand the project organization

2. **Next, understand the implementation approach:**
   - Read `hld/phase-implementation-cycle-v1.0.md` to understand the standard implementation cycle
   - Review `hld/implementation-roadmap-v1.0.md` to see the complete roadmap broken down by phases
   - Each phase builds on the previous one, so follow them sequentially
   - **Important**: Pay close attention to the "Key LLD References" section under each phase in the roadmap, which links to the specific LLD documents relevant for that phase

3. **Assess current project progress:**
   - Check the implementation roadmap for phases marked with green ticks (✅)
   - Review phase plan documents to identify completed tasks (marked with ✅)
   - Examine commit history to understand recent work
   - This assessment helps you understand which phase and task to work on next

4. **Initialize your work on the current phase:**
   - Study the current phase implementation plan in detail
   - Create phase notes file if not already created:
     ```bash
     cp hld/templates/phase-notes-template.md hld/notes/phase0-notes.md
     # Edit and replace '0' with current phase number
     ```
   - Create phase branch if not already done:
     ```bash
     git checkout -b phase-0  # Replace '0' with current phase number
     ```
   - Begin with the first uncompleted task in the current phase plan

## Key Files Reference Table

| Purpose | File Path | What to Do With It |
|---------|-----------|-------------------|
| Project Overview | `hld/multi-comms-engine-hld-v1.0.md` | Read and understand |
| Implementation Methodology | `hld/phase-implementation-cycle-v1.0.md` | Follow for each task |
| Complete Roadmap | `hld/implementation-roadmap-v1.0.md` | Use as a map for all phases and find LLD document references |
| Directory Structure | `hld/directory-structure-v1.0.md` | Follow when creating files |
| Current Phase Plan | `hld/phases/phase0-implementation-plan-v1.0.md` | Implement tasks; mark with ✅ when done |
| Phase Notes Template | `hld/templates/phase-notes-template.md` | Copy to create phase notes |
| Component Documentation Template | `hld/templates/component-doc-template.md` | Use when documenting components |
| LLD Documents | `lld/` directory | Consult specific LLD documents referenced in the roadmap for each phase |

## Detailed Implementation Workflow

For each phase, follow this precise implementation workflow:

### Step 1: Begin a Phase

1. Open the detailed phase plan document (e.g., `hld/phases/phase0-implementation-plan-v1.0.md`)
2. Check existing green ticks (✅) to identify which tasks have already been completed
3. Create a phase notes document in `hld/notes/` (using `hld/templates/phase-notes-template.md` as a template) if not already created
4. Create a branch for the phase (e.g., `git checkout -b phase-0`) if not already done
5. Review all LLD documents referenced in the "Key LLD References" section for that phase in the implementation roadmap

### Step 2: Implement Tasks

For each task listed in the phase plan:

1. Check the task details in the phase implementation plan
2. For design information, consult the corresponding LLD document in the `lld/` directory as referenced in the implementation roadmap
3. Follow the directory structure in `hld/directory-structure-v1.0.md` to know where to place new code
4. Implement the task following the cycle defined in `hld/phase-implementation-cycle-v1.0.md`:
   - Set up the functionality locally
   - Create and run local tests
   - Update documentation
   - Commit changes to the Git repository
   - Deploy to AWS
   - Create and run AWS tests
   - Update AWS documentation
   - Commit final changes

5. After completing a task, mark it with a green tick (✅) in the phase plan document
6. Document important information in the phase notes document:
   - Record the completion date and status in the Implementation Progress section
   - Document any key decisions made
   - Note any challenges encountered and their solutions
   - Track AWS resources created
   - Document any performance observations
   - Note any security considerations
   - Document lessons learned

### Step 3: Document Components

For each component implemented:

1. Create a component documentation file using `hld/templates/component-doc-template.md` as a template
2. Place the documentation in the appropriate location (e.g., under `docs/api/` for API documentation)
3. Include diagrams, interfaces, data flows, and other important details
4. Reference this documentation in the phase notes
5. Reference any relevant LLD documents that guided your implementation

### Step 4: Complete the Phase

When all tasks in a phase are complete:

1. Ensure all items in the phase plan are marked with a green tick (✅)
2. Verify all tests are passing
3. Confirm all documentation is updated
4. Create a pull request to merge the phase branch into the main branch
5. Move on to the next phase

## The Standard Implementation Cycle

The implementation cycle defined in `hld/phase-implementation-cycle-v1.0.md` must be followed for each task in order:

1. **Setup New Implementation / Functionality Locally**
   - Use the existing virtual environment
   - Implement new features according to the phase requirements
   - Follow the architecture and design patterns established in the roadmap
   - Ensure code quality and adherence to project standards

2. **Create and Run Local Tests**
   - Develop comprehensive test cases for the new functionality
   - Run tests in the local environment
   - Log test results in the appropriate phase testing folder
   - Debug and fix any issues until all tests pass
   - Only proceed when all functionality is working correctly

3. **Update Documentation**
   - Update progress information in roadmap and phase docs
   - Use green emoji ticks ✅ to highlight completed items
   - Update any relevant diagrams to reflect the current state
   - Document any challenges encountered and their solutions
   - Note any deviations from the original plan and their justification

4. **Commit Changes to Git Repository**
   - For Phase 1: Create a new git repository if not already done
   - For subsequent phases: Branch off main branch with phase name
   - Follow proper commit message conventions
   - Include appropriate documentation updates in commits

5. **Deploy to AWS**
   - Use CDK to deploy new functionality to AWS
   - Consider using CDK diff or other quick redeploy tools for incremental updates
   - Ensure all necessary AWS resources are properly configured
   - Verify deployment was successful

6. **Create and Run AWS Tests**
   - Develop test cases specific to the AWS environment
   - Run tests against the deployed infrastructure
   - Log test results in the appropriate phase testing folder
   - Debug and fix any issues until all tests pass
   - Only proceed when all functionality is working correctly in AWS

7. **Update AWS Documentation**
   - Update progress information in roadmap, phase, and AWS docs
   - Use green emoji ticks ✅ to highlight completed items
   - Update any relevant AWS diagrams to reflect the current state
   - Document any AWS-specific challenges encountered and their solutions
   - Note any deviations from the original deployment plan

8. **Commit Final Changes**
   - Commit all final changes to the git repository on the relevant phase branch
   - Include updated documentation and test results
   - Consider creating a pull request for merging into the main branch when the phase is complete

## GitHub Repository Management

1. Create one commit per logical task completion
2. Use descriptive commit messages:
   ```
   Phase 0: Complete task 1.1 - Install required software
   
   - Installed Node.js v16.14.0
   - Installed TypeScript 4.7.4
   - Installed AWS CDK 2.50.0
   - Installed Git 2.37.1
   ```
3. After completing all tasks in the current phase, create a pull request

## Documentation Maintenance

As you implement, maintain these documentation types:

- **HLD Documentation**: High-level architecture and design decisions
- **LLD Documentation**: Detailed design of specific components
- **Code Documentation**: Comments and documentation within the code
- **Implementation Notes**: Records of progress, decisions, and issues
- **Component Documentation**: Detailed documentation of individual components
- **User Documentation**: Guides for end-users of the system

## Phase-Specific Guidelines

**IMPORTANT IMPLEMENTATION ORDER**: Follow these phases in this specific order:
1. First implement Phases 0-3 (Environment Setup through WhatsApp Processing Engine)
2. Then implement Phases 6-8 (DLQ Processing, Testing, and Documentation)
3. Finally, return to Phases 4-5 (Email and SMS Processing Engines) as future enhancements

This order ensures that the WhatsApp processing engine is fully implemented and robust before expanding to additional channels.

### Phase 0: Environment Setup and Infrastructure Preparation

Focus on setting up the development environment and AWS infrastructure:
- Set up all required software and tools
- Configure AWS access and permissions
- Create the foundational AWS resources needed for subsequent phases
- Establish project standards and practices

Key LLD documents to reference:
- None (this is the foundational phase)

### Phase 1: Database Layer and Foundational Components

Implement the data layer and core utilities:
- Create the DynamoDB tables
- Set up the Secrets Manager configuration
- Implement shared utilities (context object, error handling, etc.)

Key LLD documents to reference:
- `lld/db/conversations-db-schema-v1.0.md`
- `lld/db/wa-company-data-db-schema-v1.0.md`
- `lld/secrets-manager/aws-referencing-v1.0.md`
- `lld/context-object/context-object-v1.0.md`
- `lld/cloudwatch-dashboard/cloudwatch-dashboard-setup-v1.0.md`

### Phase 2: Channel Router Implementation

Implement the Channel Router component:
- Set up API Gateway
- Develop the Router Lambda
- Configure message queues
- Implement error handling and monitoring

Key LLD documents to reference:
- `lld/channel-router/channel-router-documentation-v1.0.md`
- `lld/channel-router/channel-router-diagrams-v1.0.md`
- `lld/channel-router/error-handling-v1.0.md`
- `lld/channel-router/message-queue-architecture-v1.0.md`
- `lld/context-object/context-object-v1.0.md`

### Phase 3: WhatsApp Processing Engine

Implement the WhatsApp Processing Engine:
- Create the WhatsApp Lambda
- Integrate with OpenAI
- Integrate with Twilio
- Implement error handling and the heartbeat pattern

Key LLD documents to reference:
- All documents in `lld/processing-engines/whatsapp/` (01-09)

### Phase 6: DLQ Processing and System Recovery

Implement the Dead Letter Queue processor and recovery mechanisms:
- Create DLQ processor Lambda
- Develop error analysis and categorization
- Implement retry mechanism for recoverable errors
- Build system recovery processes

Key LLD documents to reference:
- `lld/processing-engines/whatsapp/07-error-handling-strategy.md`
- `lld/processing-engines/whatsapp/08-monitoring-observability.md`
- `lld/cloudwatch-dashboard/cloudwatch-dashboard-setup-v1.0.md`
- `lld/channel-router/error-handling-v1.0.md`

### Phase 7: Comprehensive Testing and Optimization

Focus on system-wide testing and performance optimization:
- Implement end-to-end testing
- Conduct load testing and failure testing
- Optimize system performance
- Enhance monitoring and observability

Key LLD documents to reference:
- `lld/cloudwatch-dashboard/cloudwatch-dashboard-setup-v1.0.md`
- `lld/processing-engines/whatsapp/08-monitoring-observability.md`
- All component documentation for optimization targets

### Phase 8: Documentation and Handover

Complete comprehensive documentation and operational handover:
- Finalize system documentation
- Create operational procedures
- Develop user guides and API documentation
- Prepare frontend integration guides

Key LLD documents to reference:
- `lld/frontend/frontend-documentation-v1.0.md`
- All component documentation for reference

### Phase 4: Email Processing Engine (Future Implementation)

Implement the Email Processing Engine after completing Phases 0-3 and 6-8:
- Create the Email Lambda
- Integrate with OpenAI for email content
- Implement Email Service integration
- Configure error handling and monitoring

Key LLD documents to reference:
- Similar to WhatsApp Processing Engine documents, but adapted for email
- `lld/context-object/context-object-v1.0.md`
- `lld/db/conversations-db-schema-v1.0.md`
- `lld/cloudwatch-dashboard/cloudwatch-dashboard-setup-v1.0.md`

### Phase 5: SMS Processing Engine (Future Implementation)

Implement the SMS Processing Engine after completing Phases 0-3 and 6-8:
- Create the SMS Lambda
- Integrate with OpenAI for SMS content
- Implement SMS Service integration
- Configure error handling and monitoring

Key LLD documents to reference:
- Similar to WhatsApp Processing Engine documents, but adapted for SMS
- `lld/context-object/context-object-v1.0.md`
- `lld/db/conversations-db-schema-v1.0.md`
- `lld/cloudwatch-dashboard/cloudwatch-dashboard-setup-v1.0.md`

## Handling Challenges

When encountering challenges:

1. Document the challenge in the phase notes
2. Research potential solutions
3. If the challenge relates to design, consult the relevant LLD documents from the "Key LLD References" section in the implementation roadmap
4. Implement the solution
5. Document the solution and outcome in the phase notes

## Tracking Progress

Use these mechanisms to track progress:

1. Update checkboxes in the phase plan documents ([ ] → [✅])
2. Maintain the Implementation Progress section in phase notes
3. Create component documentation for each completed component
4. Update the main roadmap when a phase is completed

## Using LLD References Effectively

The LLD references in the implementation roadmap are critical to successful implementation:

1. **Before starting a phase:** Read all referenced LLD documents thoroughly to understand the design details
2. **During implementation:** Refer back to specific sections of LLD documents when implementing related features
3. **When facing challenges:** Check if the LLD documents provide guidance on how to address similar issues
4. **During review:** Verify that your implementation follows the patterns specified in the LLD documents
5. **For documentation:** Reference the LLD documents in your component documentation to maintain traceability

## Final Notes

- Always prioritize following the standard implementation cycle
- Record all significant decisions and challenges
- Maintain comprehensive documentation
- Ensure all code has appropriate tests
- Follow the directory structure defined in `hld/directory-structure-v1.0.md`
- Refer to the LLD documents linked in the implementation roadmap for each phase
- Always check the current progress (green ticks ✅) before starting work to ensure you're working on the correct task

## Begin Now

Start by checking which phase and task are next based on the green ticks (✅) in the implementation roadmap and phase plan documents. 