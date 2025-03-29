# AI Agent Implementation Guide

This document serves as a concise guide for AI agents implementing the AI Multi-Communications Engine.

## ⚠️ IMPORTANT CREDENTIAL MANAGEMENT ⚠️

Before any implementation or deployment, understand the credential management approach:

1. **Credential Architecture**: The system uses AWS Secrets Manager for all credentials, with references stored in DynamoDB. Study `lld/secrets-manager/aws-referencing-v1.0.md` to understand this pattern.

2. **Local Testing**: When implementing functionality locally, request necessary test credentials from the human supervisor. These should match the format defined in the secrets architecture.

3. **AWS Production**: `hld/aws-production-credentials-template.md` contains the template for documenting AWS resources. The actual credentials will be provided by the human supervisor when needed.

⚠️ **DO NOT proceed with AWS deployment without first requesting credentials and explicit authorization!** ⚠️

## ⚙️ VIRTUAL ENVIRONMENT REQUIREMENT ⚙️

**ALWAYS use a Python virtual environment for ALL implementation work**

### Virtual Environment Setup

If no virtual environment exists:
```bash
# Create a virtual environment
python -m venv venv

# Activate the environment (macOS/Linux)
source venv/bin/activate
# OR (Windows)
venv\Scripts\activate

# Install dependencies if requirements file exists
pip install -r requirements.txt
```

### For Every Implementation Session

```bash
# Always activate the virtual environment first
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate     # Windows
```

### When Adding New Dependencies

```bash
# Install package with specific version
pip install package-name==1.2.3

# Update requirements.txt
pip freeze > requirements.txt
```

⚠️ **NEVER use the global Python environment for any project work** ⚠️

## Quick Start

### Immediate Action Steps

1. **Understand the architecture and approach:**
   - Review `hld/multi-comms-engine-hld-v1.0.md` for overall system architecture
   - Study `hld/implementation-roadmap-v1.0.md` for the complete implementation plan
   - Review `hld/phase-implementation-cycle-v1.0.md` for the standard implementation process
   - Follow phases in this order: 0-3, then 6-8, then 4-5 (future phases)

2. **Assess current progress:**
   - Check implementation roadmap for phases marked with green ticks (✅)
   - Review completed tasks in phase plans
   - Determine which phase and task to work on next

3. **Initialize work on the current phase:**
   - Study the phase implementation plan in detail
   - Create phase notes from the template if needed
   - Create phase branch if not already done
   - Begin with the first uncompleted task

## Documentation Organization

**IMPORTANT**: Maintain consistent documentation organization

1. **Phase Notes**: All implementation notes, progress tracking, and phase-specific documentation must be stored in the `hld/notes/` directory using the following naming conventions:
   - Phase progress notes: `hld/notes/phase<N>-notes.md`
   - Phase AWS resources: `hld/notes/phase<N>-aws-resources.md`
   - Phase technical documentation: `hld/notes/phase<N>-<document-name>.md`

2. **Implementation Plans**: Phase implementation plans remain in the `hld/phases/` directory.

3. **Component Documentation**: Component-specific documentation belongs in the appropriate LLD directory.

## Key Files Reference

| Purpose | File Path | Description |
|---------|-----------|-------------|
| Project Overview | `hld/multi-comms-engine-hld-v1.0.md` | Overall system architecture |
| Implementation Order | `hld/implementation-roadmap-v1.0.md` | Complete roadmap and phase order |
| Implementation Methodology | `hld/phase-implementation-cycle-v1.0.md` | Standard process for each task |
| Current Phase Plan | `hld/phases/phase<N>-implementation-plan-v1.0.md` | Specific tasks for current phase |
| Current Phase Notes | `hld/notes/phase<N>-notes.md` | Progress tracking for current phase |
| Current Phase AWS Resources | `hld/notes/phase<N>-aws-resources.md` | AWS resources for current phase |
| **AWS SECRETS ARCHITECTURE** | `lld/secrets-manager/aws-referencing-v1.0.md` | Credential management architecture |
| **AWS RESOURCES DOCUMENT** | `hld/aws-production-credentials-template.md` | AWS resources documentation |
| LLD Documents | `lld/` | Low-level design documents referenced in roadmap |
| Phase Notes Template | `hld/templates/phase-notes-template.md` | Template for phase notes |
| Component Documentation Template | `hld/templates/component-doc-template.md` | Template for component docs |

## Implementation Order

**IMPORTANT**: Follow phases in this specific order:
1. First implement Phases 0-3 (Environment Setup through WhatsApp Processing Engine)
2. Then implement Phases 6-8 (DLQ Processing, Testing, and Documentation)
3. Finally, return to Phases 4-5 (Email and SMS Processing Engines) as future enhancements

This order ensures the WhatsApp processing engine is fully implemented before expanding to additional channels.

## Standard Implementation Process

**CRITICAL: IMPLEMENT ONE SECTION AT A TIME**

1. Work on a single section of the current phase plan at a time (e.g., Section 1.1, then 1.2, etc.)
2. Begin with a thorough review:
   - Review previous phase's notes (hld/notes/phase<N-1>-notes.md)
   - Review deployed AWS resources (hld/notes/phase<N-1>-aws-resources.md)
   - Check for any dependencies or components needed in the current phase
3. Before starting implementation:
   - **Ensure the virtual environment is activated** (see Virtual Environment Requirement section)
   - Study the credential architecture in `lld/secrets-manager/aws-referencing-v1.0.md`
   - Request any necessary test credentials from the human supervisor
   - Set up mock data that follows the same structure for local testing
4. For each section, complete the full implementation cycle before moving to the next section:

   1. Setup the functionality locally
   2. Create and run local tests
   3. Update documentation
   4. Make incremental Git commits with clear messages
   5. Before AWS deployment:
      - **STOP and request AWS credentials**
      - Document planned resources in the AWS resources document
      - Request explicit authorization for deployment
   6. Deploy to AWS
   7. Create and run AWS tests
   8. Update AWS documentation
   9. Make final Git commits for the section

5. After completing a section:
   - Summarize what was accomplished
   - Identify any challenges or deviations
   - **ALWAYS REQUEST HUMAN AUTHORIZATION before proceeding to the next section**

**DO NOT attempt to implement multiple sections simultaneously or jump ahead in the plan.**

## Source Control and Git Practices

Every phase should follow these git practices to maintain a clean and traceable development history:

1. **Branch Management**:
   - **IMPORTANT: Branches function as sequential snapshots, like "Save As" operations**
   - Each phase has its own dedicated branch that represents a complete, working snapshot of the system at that phase
   - Create a dedicated branch for each phase from the previous phase branch, not from main
   - Always branch off the most recent phase branch:
   ```bash
   # Example: Creating phase-1 branch from phase-0 branch
   git checkout phase-0
   git checkout -b phase-1
   
   # Example: Creating phase-2 branch from phase-1 branch
   git checkout phase-1
   git checkout -b phase-2
   ```
   - Work exclusively on the phase branch until the phase is complete
   - Do not pull from remote before creating a new branch as the local code is already the latest

2. **Commit Practices**:
   - Make incremental, logical commits during development
   - Use clear, descriptive commit messages that explain what was done
   - Include the phase and section reference in commit messages
   ```bash
   git commit -m "Phase N, Section X.Y: Brief description of changes"
   ```

3. **Phase Completion Process**:
   - When the phase is complete, ensure all changes are committed
   - Push the branch to the remote repository as a complete snapshot of that phase
   ```bash
   git push -u origin phase-N
   ```
   - **DO NOT create pull requests or merge branches back** - each branch exists as an independent, complete snapshot
   - Notify the human supervisor that the phase is complete and the branch has been pushed

4. **Preparing for Next Phase**:
   - DO NOT check out the main branch - each phase builds on the previous phase
   - Create a new branch directly from the current phase branch:
   ```bash
   # While on phase-1 branch:
   git checkout -b phase-2
   ```

This branching strategy means:
- Each branch represents a complete, working snapshot of the system at a specific phase
- Branches function like "Save As" operations, creating a linear progression of development
- Each phase's code is built directly on the previous phase
- We maintain a clear historical record of each phase's implementation
- The main branch is only updated at major milestones
- Code is always developed incrementally
- We avoid losing work by never pulling down potentially outdated code

## Credential Management

When implementing functionality that requires credentials:

1. **Follow the established pattern**: Use the AWS Secrets Manager reference architecture
2. **For local testing**: Request test credentials from the human supervisor
3. **For mock data**: Create data in the same format as the production system
4. **Key files to review**:
   - `lld/secrets-manager/aws-referencing-v1.0.md` (credential architecture)
   - `lld/db/wa-company-data-db-schema-v1.0.md` (DB schema with credential references)

This ensures that local implementations match the production architecture.

## Handling Challenges

When encountering challenges:
1. Document in phase notes
2. Consult relevant LLD documents
3. Implement solution
4. Document outcome

## Documentation Maintenance

Maintain these documentation types throughout implementation:
- HLD Documentation (high-level architecture)
- LLD Documentation (detailed design)
- Code Documentation (inline code comments)
- Implementation Notes (progress records)
- Component Documentation (API specs, etc.)

## Phase Completion

When all tasks in a phase are complete:
- Ensure all items are marked with green ticks (✅)
- Verify all tests are passing
- Confirm all documentation is updated
- Push all changes to the git repository (to the phase branch only, no merge requests)
- Notify the human supervisor that the phase is complete
- Upon approval, prepare for the next phase by creating a new branch from the current phase branch

## Begin Implementation

1. **Activate the virtual environment** (this is mandatory for every implementation session)
   ```bash
   # macOS/Linux
   source venv/bin/activate
   # OR Windows
   venv\Scripts\activate
   ```

2. Identify which phase and task are next based on the green ticks (✅) in the implementation roadmap and phase plan documents
3. Work on only ONE section of the current phase plan
4. Complete the ENTIRE implementation cycle for that section
5. Present your work and request explicit authorization before proceeding to the next section

Remember: Small, manageable chunks with human review between each section ensures the highest quality implementation. 