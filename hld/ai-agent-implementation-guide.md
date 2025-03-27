# AI Agent Implementation Guide

This document serves as a concise guide for AI agents implementing the AI Multi-Communications Engine.

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
| Test Configuration | `hld/test-environment-config.md` | Test accounts and credentials setup |
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
   - Check `hld/test-environment-config.md` for required test accounts and credentials
   - Ensure all necessary test configurations are available
   - Request any missing credentials from the human supervisor
3. For each section, complete the full implementation cycle before moving to the next section:

   1. Setup the functionality locally
   2. Create and run local tests
   3. Update documentation
   4. Commit changes to Git
   5. Deploy to AWS
   6. Create and run AWS tests
   7. Update AWS documentation
   8. Commit final changes

3. After completing a section:
   - Summarize what was accomplished
   - Identify any challenges or deviations
   - **ALWAYS REQUEST HUMAN AUTHORIZATION before proceeding to the next section**

**DO NOT attempt to implement multiple sections simultaneously or jump ahead in the plan.**

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