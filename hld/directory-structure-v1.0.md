# AI Multi-Communications Engine - Directory Structure v1.0

This document outlines the detailed directory structure for the AI Multi-Communications Engine project, designed to support our phased implementation approach, clear separation of concerns, and comprehensive documentation.

## Top-Level Structure

```
ai-multi-comms-engine/
├── hld/                        # High-Level Design documentation
├── lld/                        # Low-Level Design documentation
├── src/                        # Source code for the application
├── tests/                      # Test suites organized by phase and component
├── scripts/                    # Utility scripts for development and deployment
├── infrastructure/             # CDK infrastructure code
├── docs/                       # Generated documentation and guides
├── .github/                    # GitHub workflows and templates
├── .vscode/                    # VSCode configuration
├── .env.example                # Example environment variables
├── package.json                # Node.js package configuration
├── tsconfig.json               # TypeScript configuration
├── jest.config.js              # Jest test configuration
├── .eslintrc.js                # ESLint configuration
├── .prettierrc                 # Prettier configuration
├── .gitignore                  # Git ignore file
└── README.md                   # Project overview and setup instructions
```

## High-Level Design (HLD) Directory

The HLD directory contains high-level architecture documents, implementation roadmaps, and phase planning:

```
hld/
├── multi-comms-engine-hld-v1.0.md       # Main HLD document
├── implementation-roadmap-v1.0.md       # Implementation roadmap
├── diagrams-v1.0.md                     # System architecture diagrams
├── directory-structure-v1.0.md          # This file
├── ai-agent-implementation-guide.md     # Guide for AI agent implementation
├── phases/                              # Phase-specific implementation plans
│   ├── phase0-implementation-plan-v1.0.md
│   ├── phase1-implementation-plan-v1.0.md
│   ├── phase2-implementation-plan-v1.0.md
│   └── ...
├── templates/                           # Templates for documentation
│   ├── phase-notes-template.md
│   └── component-doc-template.md
└── notes/                               # Implementation notes by phase
    ├── phase0-notes.md                  # Phase 0 progress tracking and learnings
    ├── phase0-aws-resources.md          # Phase 0 AWS resources documentation
    ├── phase1-notes.md                  # Phase 1 progress tracking and learnings
    ├── phase1-aws-resources.md          # Phase 1 AWS resources documentation
    └── ...
```

## Low-Level Design (LLD) Directory

The LLD directory contains detailed component-specific design documents:

```
lld/
├── channel-router/                      # Channel Router documents
│   ├── channel-router-documentation-v1.0.md
│   ├── channel-router-diagrams-v1.0.md
│   ├── error-handling-v1.0.md
│   └── message-queue-architecture-v1.0.md
├── context-object/                      # Context Object schema
│   └── context-object-v1.0.md
├── db/                                  # Database schemas
│   ├── conversations-db-schema-v1.0.md
│   └── wa-company-data-db-schema-v1.0.md
├── processing-engines/                  # Processing Engine documents
│   └── whatsapp/
│       ├── 01-overview-architecture.md
│       ├── 02-sqs-integration.md
│       └── ...
├── frontend/                            # Frontend integration
│   └── frontend-documentation-v1.0.md
├── secrets-manager/                     # Secrets management
│   └── aws-referencing-v1.0.md
└── cloudwatch-dashboard/                # Monitoring
    └── cloudwatch-dashboard-setup-v1.0.md
```

## Source Code Directory

The src directory contains all application code, organized by component:

```
src/
├── channel-router/                      # Channel Router component
│   ├── handler.ts                       # Lambda handler
│   ├── router.ts                        # Routing logic
│   ├── validation.ts                    # Request validation
│   └── authentication.ts                # Authentication logic
├── processing-engines/                  # Processing engines
│   ├── whatsapp/                        # WhatsApp engine
│   │   ├── handler.ts                   # Lambda handler
│   │   ├── conversation.ts              # Conversation management
│   │   ├── openai.ts                    # OpenAI integration
│   │   ├── twilio.ts                    # Twilio integration
│   │   └── error-handler.ts             # Error handling
│   ├── email/                           # Email engine
│   │   └── ...
│   └── sms/                             # SMS engine
│       └── ...
├── shared/                              # Shared utilities
│   ├── context/                         # Context object
│   │   ├── context.ts                   # Context definition
│   │   ├── validator.ts                 # Context validation
│   │   └── factory.ts                   # Context creation
│   ├── db/                              # Database utilities
│   │   ├── dynamo-client.ts             # DynamoDB client
│   │   ├── conversations.ts             # Conversations table access
│   │   └── company-data.ts              # Company data table access
│   ├── secrets/                         # Secrets utilities
│   │   ├── secrets-client.ts            # Secrets Manager client
│   │   ├── reference.ts                 # Reference handling
│   │   └── resolver.ts                  # Credential resolution
│   ├── utils/                           # Utility functions
│   │   ├── logging.ts                   # Logging utilities
│   │   ├── error.ts                     # Error handling
│   │   ├── circuit-breaker.ts           # Circuit breaker
│   │   └── heartbeat.ts                 # SQS heartbeat
│   └── monitoring/                      # Monitoring utilities
│       ├── metrics.ts                   # Metric publishing
│       └── alarms.ts                    # Alarm utilities
├── dlq-processor/                       # DLQ processing
│   ├── handler.ts                       # Lambda handler
│   └── processor.ts                     # Processing logic
└── types/                               # TypeScript type definitions
    ├── context.types.ts                 # Context object types
    ├── database.types.ts                # Database models
    └── api.types.ts                     # API models
```

## Infrastructure Directory

The infrastructure directory contains all CDK infrastructure code:

```
infrastructure/
├── bin/                                 # CDK entry point
│   └── infrastructure.ts
├── lib/                                 # CDK constructs
│   ├── channel-router-stack.ts          # Channel Router stack
│   ├── whatsapp-engine-stack.ts         # WhatsApp Engine stack
│   ├── email-engine-stack.ts            # Email Engine stack
│   ├── sms-engine-stack.ts              # SMS Engine stack
│   ├── database-stack.ts                # DynamoDB stack
│   ├── monitoring-stack.ts              # Monitoring stack
│   ├── secrets-stack.ts                 # Secrets Manager stack
│   └── network-stack.ts                 # VPC stack
├── config/                              # Stack configuration
│   ├── dev.json                         # Development environment
│   ├── staging.json                     # Staging environment
│   └── prod.json                        # Production environment
└── constructs/                          # Custom constructs
    ├── dynamo-table.ts                  # DynamoDB table construct
    ├── lambda-function.ts               # Lambda function construct
    ├── sqs-queue.ts                     # SQS queue construct
    └── api-gateway.ts                   # API Gateway construct
```

## Tests Directory

The tests directory contains all test code, organized by test type and component:

```
tests/
├── unit/                                # Unit tests
│   ├── channel-router/                  # Channel Router tests
│   │   ├── router.test.ts
│   │   ├── validation.test.ts
│   │   └── authentication.test.ts
│   ├── shared/                          # Shared utilities tests
│   │   ├── context.test.ts
│   │   ├── circuit-breaker.test.ts
│   │   └── ...
│   └── processing-engines/              # Processing engines tests
│       ├── whatsapp/
│       │   ├── openai.test.ts
│       │   └── ...
│       └── ...
├── integration/                         # Integration tests
│   ├── database/                        # Database integration tests
│   │   ├── conversations.test.ts
│   │   └── company-data.test.ts
│   ├── secrets/                         # Secrets Manager tests
│   │   └── resolver.test.ts
│   └── monitoring/                      # Monitoring tests
│       └── metrics.test.ts
├── e2e/                                 # End-to-end tests
│   ├── channel-router.test.ts
│   ├── whatsapp-engine.test.ts
│   └── ...
└── fixtures/                            # Test fixtures
    ├── context-objects/                 # Sample context objects
    ├── database/                        # Sample database records
    └── responses/                       # Sample API responses
```

## Scripts Directory

The scripts directory contains utility scripts for development, deployment, and maintenance:

```
scripts/
├── setup/                               # Setup scripts
│   ├── setup-dev-env.sh                 # Dev environment setup
│   └── bootstrap-aws.sh                 # AWS bootstrap
├── deploy/                              # Deployment scripts
│   ├── deploy-dev.sh                    # Deploy to dev
│   ├── deploy-staging.sh                # Deploy to staging
│   └── deploy-prod.sh                   # Deploy to production
├── test/                                # Test scripts
│   ├── run-unit-tests.sh                # Run unit tests
│   ├── run-integration-tests.sh         # Run integration tests
│   └── run-e2e-tests.sh                 # Run e2e tests
└── utils/                               # Utility scripts
    ├── update-deps.sh                   # Update dependencies
    ├── lint-fix.sh                      # Run linter with fixes
    └── generate-docs.sh                 # Generate documentation
```

## Docs Directory

The docs directory contains generated documentation and guides:

```
docs/
├── api/                                 # API documentation
│   └── channel-router-api.md            # Channel Router API
├── guides/                              # User guides
│   ├── setup-guide.md                   # Setup guide
│   ├── development-guide.md             # Development guide
│   └── deployment-guide.md              # Deployment guide
├── architecture/                        # Architecture documentation
│   ├── system-overview.md               # System overview
│   └── component-interactions.md        # Component interactions
└── operations/                          # Operations documentation
    ├── monitoring-guide.md              # Monitoring guide
    └── troubleshooting-guide.md         # Troubleshooting guide
```

## Documentation Organization Guidelines

For consistent documentation:

1. **Phase Implementation Plans**: Located in `hld/phases/` - define tasks, deliverables, and requirements for each phase
2. **Phase Implementation Notes**: Located in `hld/notes/` - track progress, decisions, challenges and lessons learned
3. **AWS Resources Documentation**: Phase-specific AWS resources documented in `hld/notes/phase<N>-aws-resources.md`
4. **Component Documentation**: Component-specific details in relevant LLD directories

This structure ensures clear separation between:
- What to implement (implementation plans)
- How it's being implemented (implementation notes)
- What was created (AWS resources documentation)

## Implementation Notes

1. **Phased Approach**: The directory structure supports our phased implementation plan with clear organization of code, tests, and documentation.

2. **Separation of Concerns**: Each component (Channel Router, Processing Engines, etc.) has its own directory, promoting modularity and maintainability.

3. **Infrastructure as Code**: CDK infrastructure code is separated from application code for clearer distinction between infrastructure and application logic.

4. **Testing Strategy**: Tests are organized by type (unit, integration, e2e) and then by component for easy navigation and management.

5. **Documentation**: Comprehensive documentation is included at each level, from high-level architecture to specific implementation details.

6. **Environment Configuration**: Environment-specific configuration is separated from code, following best practices for security and deployment flexibility.

This directory structure provides a solid foundation for the AI Multi-Communications Engine project, supporting both current requirements and future expansion. 