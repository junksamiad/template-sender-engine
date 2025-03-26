# AI Agent Implementation Guide

This document serves as a comprehensive guide for AI agents tasked with implementing the AI Multi-Communications Engine. It explains how to navigate the documentation, follow the implementation roadmap, and execute each phase correctly.

## Getting Started

1. **First, familiarize yourself with the high-level architecture:**
   - Review `hld/multi-comms-engine-hld-v1.0.md` to understand the overall system
   - Examine `hld/diagrams-v1.0.md` to visualize the architecture
   - Study `hld/directory-structure-v1.0.md` to understand the project organization

2. **Next, understand the implementation approach:**
   - Read `ignore/phase-implementation-cycle-v1.0.md` to understand the standard implementation cycle
   - Review `hld/implementation-roadmap-v1.0.md` to see the complete roadmap broken down by phases
   - Each phase builds on the previous one, so follow them sequentially

## Implementation Workflow

For each phase, follow this precise implementation workflow:

### Step 1: Begin a Phase

1. Open the detailed phase plan document (e.g., `hld/phases/phase0-implementation-plan-v1.0.md`)
2. Create a phase notes document in `hld/notes/` (using `hld/templates/phase-notes-template.md` as a template)
3. Create a branch for the phase (e.g., `git checkout -b phase-0`)

### Step 2: Implement Tasks

For each task listed in the phase plan:

1. Check the task details in the phase implementation plan
2. For design information, consult the corresponding LLD document in the `lld/` directory
3. Follow the directory structure in `hld/directory-structure-v1.0.md` to know where to place new code
4. Implement the task following the cycle defined in `ignore/phase-implementation-cycle-v1.0.md`:
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

### Step 4: Complete the Phase

When all tasks in a phase are complete:

1. Ensure all items in the phase plan are marked with a green tick (✅)
2. Verify all tests are passing
3. Confirm all documentation is updated
4. Create a pull request to merge the phase branch into the main branch
5. Move on to the next phase

## Documentation Maintenance

As you implement, maintain these documentation types:

- **HLD Documentation**: High-level architecture and design decisions
- **LLD Documentation**: Detailed design of specific components
- **Code Documentation**: Comments and documentation within the code
- **Implementation Notes**: Records of progress, decisions, and issues
- **Component Documentation**: Detailed documentation of individual components
- **User Documentation**: Guides for end-users of the system

## Phase-Specific Guidelines

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

### Phase 3: WhatsApp Processing Engine

Implement the WhatsApp Processing Engine:
- Create the WhatsApp Lambda
- Integrate with OpenAI
- Integrate with Twilio
- Implement error handling and the heartbeat pattern

Key LLD documents to reference:
- All documents in `lld/processing-engines/whatsapp/`

## Handling Challenges

When encountering challenges:

1. Document the challenge in the phase notes
2. Research potential solutions
3. If the challenge relates to design, consult the relevant LLD documents
4. Implement the solution
5. Document the solution and outcome in the phase notes

## Tracking Progress

Use these mechanisms to track progress:

1. Update checkboxes in the phase plan documents ([ ] → [✅])
2. Maintain the Implementation Progress section in phase notes
3. Create component documentation for each completed component
4. Update the main roadmap when a phase is completed

## Final Notes

- Always prioritize following the standard implementation cycle
- Record all significant decisions and challenges
- Maintain comprehensive documentation
- Ensure all code has appropriate tests
- Follow the directory structure defined in `hld/directory-structure-v1.0.md`

By following this guide, you will systematically implement the AI Multi-Communications Engine according to the defined roadmap and architecture. 