# AI Multi-Communications Engine

A scalable, cloud-based system designed to enable businesses to send personalized AI-generated messages through multiple communication channels including WhatsApp, Email, and SMS.

## System Overview

The AI Multi-Communications Engine is built on AWS serverless technologies and integrates with:
- OpenAI for AI-powered message generation
- Twilio for WhatsApp/SMS delivery
- Email service providers for email delivery

The system components include:
- Channel Router for request processing
- Channel-specific processing engines
- Comprehensive monitoring and observability
- Dead Letter Queue processing

## Project Structure

```
ai-multi-comms-engine/
├── hld/                        # High-Level Design documentation
├── lld/                        # Low-Level Design documentation
├── src/                        # Source code for the application
│   ├── channel-router/         # Channel Router component
│   ├── processing-engines/     # Processing engines for each channel
│   │   ├── whatsapp/          
│   │   ├── email/             
│   │   └── sms/               
│   ├── shared/                 # Shared utilities and components
│   ├── infrastructure/         # CDK Infrastructure code
│   └── monitoring/             # Monitoring and observability
├── tests/                      # Test suites organized by phase and component
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── e2e/                    # End-to-end tests
├── scripts/                    # Utility scripts for development and deployment
```

## Development Setup

### Prerequisites

- Python 3.9+
- Node.js 16.x or later
- AWS CLI configured with appropriate credentials
- AWS CDK 2.x

### Virtual Environment Setup

```bash
# Create a virtual environment
python -m venv venv

# Activate the environment (macOS/Linux)
source venv/bin/activate
# OR (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### AWS CDK Setup

```bash
# Install AWS CDK globally
npm install -g aws-cdk

# Bootstrap AWS environment (if not already done)
cdk bootstrap

# Deploy infrastructure
cdk deploy
```

## Implementation Roadmap

The implementation follows a phased approach:
1. Environment Setup and Infrastructure Preparation
2. Database Layer and Foundational Components
3. Channel Router Implementation
4. WhatsApp Processing Engine
5. DLQ Processing and System Recovery
6. Comprehensive Testing and Optimization
7. Documentation and Handover
8. Email and SMS Processing Engines (Future Enhancements)

## Documentation

Refer to the following documentation for more details:
- High-Level Design (HLD): `hld/multi-comms-engine-hld-v1.0.md`
- Implementation Roadmap: `hld/implementation-roadmap-v1.0.md`
- Low-Level Design (LLD): Various documents in the `lld/` directory

## License

Proprietary and Confidential 