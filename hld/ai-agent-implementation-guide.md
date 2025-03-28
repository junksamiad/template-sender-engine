# AI Agent Implementation Guide

This document serves as a concise guide for AI agents implementing the AI Multi-Communications Engine.

## ⚠️ IMPORTANT CREDENTIAL MANAGEMENT ⚠️

Before any implementation or deployment, understand the credential management approach:

1. **Credential Architecture**: The system uses AWS Secrets Manager for all credentials, with references stored in DynamoDB. Study `lld/secrets-manager/aws-referencing-v1.0.md` and `hld/aws-secrets-summary.md` to understand this pattern.

2. **Local Testing**: When implementing functionality locally, request necessary test credentials from the human supervisor. These should match the format defined in the secrets architecture.

3. **AWS Production**: `hld/aws-production-credentials-template.md` contains the template for documenting AWS resources. The actual credentials will be provided by the human supervisor when needed.

⚠️ **DO NOT proceed with AWS deployment without first requesting credentials and explicit authorization!** ⚠️

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

## Key Files Reference

| Purpose | File Path | Description |
|---------|-----------|-------------|
| Project Overview | `hld/multi-comms-engine-hld-v1.0.md` | Overall system architecture |
| Implementation Order | `hld/implementation-roadmap-v1.0.md` | Complete roadmap and phase order |
| Implementation Methodology | `hld/phase-implementation-cycle-v1.0.md` | Standard process for each task |
| Current Phase Plan | `hld/phases/phase<N>-implementation-plan-v1.0.md` | Specific tasks for current phase |
| **AWS SECRETS STRUCTURE** | `lld/secrets-manager/aws-referencing-v1.0.md` | Credential management architecture |
| **SECRETS SUMMARY** | `hld/aws-secrets-summary.md` | Summary of secret structures |
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
2. Before starting implementation:
   - Study the credential architecture in `lld/secrets-manager/aws-referencing-v1.0.md`
   - Request any necessary test credentials from the human supervisor
   - Set up mock data that follows the same structure for local testing
3. For each section, complete the full implementation cycle before moving to the next section:

   1. Setup the functionality locally
   2. Create and run local tests
   3. Update documentation
   4. Commit changes to Git
   5. Before AWS deployment:
      - **STOP and request AWS credentials**
      - Document planned resources in the AWS resources document
      - Request explicit authorization for deployment
   6. Deploy to AWS
   7. Create and run AWS tests
   8. Update AWS documentation
   9. Commit final changes

3. After completing a section:
   - Summarize what was accomplished
   - Identify any challenges or deviations
   - **ALWAYS REQUEST HUMAN AUTHORIZATION before proceeding to the next section**

**DO NOT attempt to implement multiple sections simultaneously or jump ahead in the plan.**

## Credential Management

When implementing functionality that requires credentials:

1. **Follow the established pattern**: Use the AWS Secrets Manager reference architecture
2. **For local testing**: Request test credentials from the human supervisor
3. **For mock data**: Create data in the same format as the production system
4. **Key files to review**:
   - `lld/secrets-manager/aws-referencing-v1.0.md` (credential architecture)
   - `lld/db/wa-company-data-db-schema-v1.0.md` (DB schema with credential references)
   - `hld/aws-secrets-summary.md` (summary of secret structures)

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
- Create a pull request to merge into main branch
- Move to the next phase in the implementation order

## Begin Implementation

1. Identify which phase and task are next based on the green ticks (✅) in the implementation roadmap and phase plan documents
2. Work on only ONE section of the current phase plan
3. Complete the ENTIRE implementation cycle for that section
4. Present your work and request explicit authorization before proceeding to the next section

Remember: Small, manageable chunks with human review between each section ensures the highest quality implementation. 