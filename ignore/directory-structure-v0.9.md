# WhatsApp AI Chatbot Directory Structure

This document outlines the proposed directory structure for the WhatsApp AI chatbot project. The structure is designed to support a phased implementation approach, clear separation of concerns, and comprehensive documentation.

## Top-Level Structure

```
whatsapp-ai-chatbot/
├── roadmap/           # Project planning and architecture documentation
├── src/               # Source code for the application
├── tests/             # Test suites organized by phase and component
├── .env.example       # Example environment variables
├── requirements.txt   # Python dependencies
└── README.md          # Project overview and setup instructions
```

## Roadmap Directory

The roadmap directory contains all planning documents, architecture diagrams, and implementation guides:

```
roadmap/
├── overview.md                # High-level project overview
├── architecture_diagram.png   # System architecture diagram
├── directory_structure.md     # This file - directory structure documentation
├── aws/                       # AWS-specific documentation
│   ├── stack_overview.md      # Overview of AWS stack components
│   ├── infrastructure_diagram.png  # AWS infrastructure diagram
│   └── deployment_guide.md    # Guide for deploying to AWS
├── phase1/                    # Phase 1 documentation
│   ├── requirements.md        # Requirements for Phase 1
│   ├── architecture_diagram.png  # Phase 1 architecture diagram
│   ├── dev/
│   │   ├── setup_guide.md     # Development setup instructions
│   │   └── implementation_notes.md  # Implementation details
│   ├── prod/
│   │   ├── deployment_guide.md  # Production deployment guide
│   │   └── monitoring_guide.md  # Monitoring setup guide
│   └── testing/
│       ├── local/
│       │   ├── test_cases.md  # Local test cases
│       │   └── results.md     # Test results documentation
│       └── deployed/
│           ├── test_cases.md  # Deployed environment test cases
│           └── results.md     # Test results documentation
├── phase2/                    # Phase 2 documentation
│   └── [similar structure to phase1]
└── phase3/                    # Phase 3 documentation
    └── [similar structure to phase1]
```

## Source Code Directory

The src directory contains all application code, organized by component:

```
src/
├── api/                # API endpoints and request handling
│   ├── __init__.py
│   ├── routes.py       # API route definitions
│   ├── models.py       # Request/response models
│   └── validation.py   # Input validation logic
├── db/                 # Database interactions
│   ├── __init__.py
│   ├── dynamo.py       # DynamoDB client and operations
│   ├── models.py       # Data models
│   └── repositories/   # Repository pattern implementations
│       ├── __init__.py
│       ├── company.py  # Company data repository
│       └── conversation.py  # Conversation repository
├── openai/             # OpenAI integration
│   ├── __init__.py
│   ├── client.py       # OpenAI client setup
│   ├── assistants.py   # Assistant management
│   └── threads.py      # Thread operations
├── twilio/             # Twilio integration
│   ├── __init__.py
│   ├── client.py       # Twilio client setup
│   └── templates.py    # Template message handling
└── utils/              # Utility functions and helpers
    ├── __init__.py
    ├── context.py      # Request context management
    ├── logging.py      # Logging utilities
    └── errors.py       # Error handling utilities
```

## Tests Directory

The tests directory mirrors the src structure but is organized by implementation phase:

```
tests/
├── phase1/                    # Phase 1 tests
│   ├── api/
│   │   ├── test_endpoints.py  # API endpoint tests
│   │   └── test_validation.py # Input validation tests
│   ├── db/
│   │   ├── test_mock_dynamo.py  # Mock DynamoDB tests
│   │   └── test_data_models.py  # Data model tests
│   └── conftest.py            # Phase 1 test fixtures
├── phase2/                    # Phase 2 tests
│   ├── api/
│   │   └── test_error_handling.py  # Error handling tests
│   ├── db/
│   │   ├── test_company_config.py  # Company config tests
│   │   └── test_conversation_storage.py  # Conversation storage tests
│   └── conftest.py            # Phase 2 test fixtures
├── phase3/                    # Phase 3 tests
│   ├── openai/
│   │   ├── test_assistant_integration.py  # OpenAI integration tests
│   │   └── test_thread_management.py      # Thread management tests
│   ├── twilio/
│   │   └── test_message_sending.py        # Twilio message tests
│   └── conftest.py            # Phase 3 test fixtures
├── common/                    # Shared test utilities
│   ├── test_utils.py          # Utility function tests
│   └── test_helpers.py        # Helper function tests
└── conftest.py                # Shared test fixtures
```

## Implementation Notes

1. **Phased Approach**: The directory structure supports the phased implementation plan, with clear separation between phases in both documentation and tests.

2. **Separation of Concerns**: Each component (API, database, OpenAI, Twilio) has its own directory, promoting modularity and maintainability.

3. **Documentation**: Comprehensive documentation is included at each level, from high-level architecture to specific implementation details.

4. **Testing**: Test directories mirror the source code structure but are organized by implementation phase, allowing for incremental testing as the project progresses.

5. **Configuration**: Environment variables and configuration are separated from code, following best practices for security and deployment flexibility.

This directory structure provides a solid foundation for the WhatsApp AI chatbot project, supporting both current requirements and future expansion. 