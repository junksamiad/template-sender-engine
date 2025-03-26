# WhatsApp Processing Engine - Business Onboarding Process

> **Part 10 of 10 in the WhatsApp Processing Engine documentation series**

## 1. Introduction

This document outlines the complete process for onboarding new businesses to the Adaptix Innovation multi-channel communications platform. The onboarding process is designed to be modular and flexible, allowing for quick setup of new businesses without code changes to the core platform. This document serves as a comprehensive guide for the operations team responsible for setting up new business clients.

## 2. Onboarding Overview

The onboarding process consists of several key phases:

1. **Business Requirements Analysis**: Understanding the client's business needs and use cases
2. **Twilio & WhatsApp Configuration**: Setting up messaging provider accounts
3. **Database Configuration**: Creating necessary records in DynamoDB
4. **Secrets Manager Configuration**: Storing credentials securely
5. **AI Assistant Configuration**: Setting up and training the OpenAI assistant
6. **Frontend Development**: Creating a custom frontend for the business use case
7. **Testing & Deployment**: Validating end-to-end functionality
8. **Monitoring Setup**: Configuring alerts and dashboards

Each phase builds upon the previous one, creating a complete solution tailored to the specific business needs.

## 3. Business Requirements Analysis

### 3.1 Initial Client Meeting

The first step is to understand the client's communication needs:

- **Primary Use Case**: What is the main scenario where the business needs to communicate with customers?
- **Data Sources**: What data will be used to populate message templates?
- **Conversation Flow**: What is the expected flow of the initial outbound message?
- **Integration Points**: How will the business trigger communications (API, UI, existing systems)?
- **Volume Expectations**: How many messages are expected to be sent daily/monthly?
- **Compliance Requirements**: Any specific regulatory considerations (GDPR, CCPA, industry regulations)

### 3.2 Template Design Planning

Based on the business requirements:

- Identify what information needs to be communicated in the template
- Define what variable data will be included in the template
- Draft the template text following WhatsApp guidelines
- Determine appropriate template category (UTILITY, MARKETING, AUTHENTICATION)
- Plan any header, footer, or button components

### 3.3 Technical Requirements Documentation

Create a requirements document that includes:

- Template structure and variables
- Data mapping strategy 
- Frontend integration requirements
- Testing scenarios
- Expected timeline for implementation

## 4. Twilio & WhatsApp Configuration

### 4.1 Twilio Account Setup

Set up the Twilio messaging infrastructure:

1. **Account Creation**: 
   - Create a new Twilio account for the business (or use their existing account)
   - Set up billing information and usage alerts

2. **Project Setup**:
   - Create a new project within Twilio
   - Enable WhatsApp messaging capability
   - Configure security settings and API access

3. **WhatsApp Sender Setup**:
   - Connect the Twilio project to Meta Business Manager
   - Register the business phone number for WhatsApp Business API
   - Complete the business verification process

### 4.2 Template Creation & Submission

1. **Template Drafting**:
   - Create the WhatsApp template in Twilio's interface
   - Add all components (header, body, footer, buttons) as needed
   - Include the appropriate variable placeholders (`{{1}}`, `{{2}}`, etc.)

2. **Compliance Review**:
   - Ensure the template follows WhatsApp guidelines
   - Check for any potential policy violations
   - Confirm appropriate category selection

3. **Template Submission**:
   - Submit the template for WhatsApp approval
   - Track approval status (typically takes 1-3 business days)
   - Address any rejection reasons if applicable

4. **Template Documentation**:
   - Once approved, document the final template structure
   - Note the approved template ID and Twilio content SID
   - Create a mapping document for variables

## 5. Database Configuration

### 5.1 Creating Company/Project Entry in wa_company_data

Create a new entry in the DynamoDB `wa_company_data` table:

```javascript
/**
 * Example wa_company_data entry for a new business
 */
{
  "company_id": "business-name",  // Lowercase, hyphenated unique identifier
  "project_id": "use-case-name",  // Specific use case identifier
  "company_name": "Business Name Ltd.",  // Human-readable company name
  "project_name": "Customer Engagement Bot",  // Human-readable project name
  "api_key_reference": "secret/api-keys/business-name/use-case-name",  // Reference to API key in Secrets Manager
  "allowed_channels": ["whatsapp", "email"],  // Communication channels for this project
  "rate_limits": {
    "requests_per_minute": 60,
    "requests_per_day": 5000,
    "concurrent_conversations": 25,
    "max_message_length": 4096
  },
  "project_status": "active",  // Set to "pending" until launch
  "company_rep": {
    "company_rep_1": "Primary Contact Name",
    "company_rep_2": "Secondary Contact Name",
    "company_rep_3": null,
    "company_rep_4": null,
    "company_rep_5": null
  },
  "ai_config": {
    "assistant_id_template_sender": "asst_123abc...",  // ID of the OpenAI Assistant
    "assistant_id_replies": "",  // Optional - for reply handling if applicable
    "assistant_id_3": "",
    "assistant_id_4": "",
    "assistant_id_5": "",
    "ai_api_key_reference": "openai/global"  // Reference to OpenAI API key
  },
  "channel_config": {
    "whatsapp": {
      "whatsapp_credentials_id": "whatsapp/business-name/use-case-name",  // Reference to credentials in Secrets Manager
      "company_whatsapp_number": "+1234567890"  // The business's WhatsApp number
    },
    "email": {
      "email_credentials_id": "email/business-name/use-case-name",
      "company_email": "communications@business-name.com"
    }
  },
  "created_at": "2023-06-15T14:30:45.123Z",
  "updated_at": "2023-06-15T14:30:45.123Z"
}
```

### 5.2 Setting Up API Authentication

1. **Generate API Key**:
   - Generate a secure API key for the business
   - Document the API key securely for sharing with the client

2. **Store API Key Reference**:
   - Store the API key in Secrets Manager with appropriate permissions
   - Use the reference in the `api_key_reference` field

3. **Authentication Configuration**:
   - Set up API Gateway authentication to validate the API key
   - Configure rate limiting for the API key

## 6. Secrets Manager Configuration

### 6.1 Storing Twilio Credentials

Create a new secret in AWS Secrets Manager containing Twilio credentials and template SID:

```javascript
/**
 * Twilio credentials structure in AWS Secrets Manager
 */
{
  "twilio_account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "twilio_auth_token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "twilio_template_sid": "HXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  // Template SID for the specific use case
}
```

The secret should be stored with a path matching the `whatsapp_credentials_id` defined in the DynamoDB record.

### 6.2 Access Control Configuration

Configure appropriate access policies:

- Limit access to specific Lambda functions
- Implement least privilege principle
- Set up rotation schedules if needed
- Enable encryption with a customer-managed KMS key if required

### 6.3 Other Credentials

If needed, set up additional credentials for other channels:

- Email sending credentials (SendGrid, SES)
- SMS credentials (Twilio)
- Any other required API keys

## 7. AI Assistant Configuration

### 7.1 Creating the OpenAI Assistant

1. **Assistant Creation**:
   - Create a new assistant in the OpenAI platform
   - Assign an appropriate name and description

2. **Model Selection**:
   - Choose the appropriate model (e.g., gpt-4-turbo)
   - Configure model parameters (temperature, max tokens)

### 7.2 System Instructions Configuration

Create detailed system instructions that include:

1. **Context Understanding**:
   - Instructions on how to parse the context object
   - Explanation of the data structure specific to the business use case

2. **Template-Specific Instructions**:
   - Details about the approved WhatsApp template structure
   - Variable mapping guidelines (which data maps to which template variable)
   - Format requirements for the contentVariables output

3. **Output Format Requirements**:
   - Explicit instructions to return content variables in the expected JSON format
   - Example of the expected output structure

4. **Error Handling Guidelines**:
   - Instructions for handling missing or invalid data
   - Fallback strategies for required template variables

Example system instructions:

```
You are a variable mapping assistant for WhatsApp template messages.

Your task is to analyze the provided JSON context object and extract the appropriate data to fill in template variables for a WhatsApp message.

The WhatsApp template has the following structure:
- Header: "Job Application Update"
- Body: "Hello {{1}}, We received your application for the {{2}} position. The hiring team would like to discuss {{3}} with you. Please reply to schedule a conversation."
- Footer: "Sent by Business Name Ltd."

You must return a JSON object with the following numbered variables:
1. The recipient's first name (found in recipient_data.recipient_first_name)
2. The job title (found in project_data.job_title)
3. The specific discussion topic based on project_data.clarification_points

Output format must be:
{
  "1": "First Name",
  "2": "Job Title",
  "3": "Discussion Topic"
}

If any required data is missing, use appropriate default values. For example, if first name is missing, use "Applicant".
```

### 7.3 Testing the Assistant

Before deployment:

1. Create test context objects with various data scenarios
2. Run multiple test runs with the assistant
3. Validate the output variables against expectations
4. Refine the system instructions as needed based on test results

## 8. Frontend Development

### 8.1 Frontend Requirements

Based on the business use case, determine:

- User interface requirements
- Data input fields needed
- Integration points with existing systems
- Authentication mechanisms
- User roles and permissions

### 8.2 Frontend Implementation Options

Choose the appropriate implementation approach:

1. **Standalone Web Application**:
   - Build a custom React/Vue/Angular application
   - Deploy to AWS S3 with CloudFront
   - Implement appropriate authentication

2. **Embedded Component**:
   - Create an embeddable widget/component
   - Provide documentation for integration into the client's existing systems
   - Implement cross-origin communication if needed

3. **API-Only Integration**:
   - Provide detailed API documentation
   - Create example code in relevant languages
   - Implement robust error handling and status reporting

### 8.3 Frontend Development Process

1. **Design Phase**:
   - Create wireframes and mockups
   - Get client approval on the design
   - Define component structure

2. **Implementation Phase**:
   - Develop the frontend application/component
   - Implement API integration with the communications platform
   - Add validation and error handling

3. **Testing Phase**:
   - Test across different browsers and devices
   - Validate all API integrations
   - Perform security testing

4. **Deployment Phase**:
   - Set up hosting infrastructure
   - Configure custom domain if needed
   - Implement monitoring and analytics

### 8.4 Frontend Configuration

Ensure the frontend is configured with:

- Correct API endpoint URLs
- Proper API key handling
- Appropriate error messages
- Analytics tracking
- Logging mechanisms

## 9. Testing & Deployment

### 9.1 Integration Testing

Perform end-to-end testing of the complete flow:

1. Frontend request submission
2. API authentication and processing
3. Queue message handling
4. OpenAI processing
5. Template message sending
6. Status webhook handling

### 9.2 Load Testing

If the expected volume is significant:

- Test with projected peak loads
- Validate queue handling under load
- Confirm rate limiting works as expected
- Check for any performance bottlenecks

### 9.3 Deployment Checklist

Before going live:

- Confirm all AWS resources are properly configured
- Verify all permissions and IAM roles
- Enable appropriate logging and monitoring
- Configure alerting for critical failures
- Document the deployment architecture

### 9.4 Soft Launch

Consider a phased rollout:

1. Start with limited test users
2. Monitor initial performance closely
3. Address any issues before full launch
4. Gradually increase message volume

## 10. Monitoring & Operations

### 10.1 Monitoring Setup

Configure monitoring for:

- API request volume and errors
- Queue depths and processing times
- Lambda function performance
- OpenAI API usage and costs
- Template sending success rates
- DynamoDB usage and performance

### 10.2 Alerting Configuration

Set up alerts for:

- Failed message sending attempts
- OpenAI API errors
- Abnormal message volumes
- Credential or authentication issues
- DynamoDB throttling or capacity issues

### 10.3 Ongoing Operations

Establish processes for:

- Regular review of CloudWatch logs
- Monthly cost analysis
- Performance optimization
- Template update management
- Regular security reviews

## 11. Documentation & Handover

### 11.1 Business Documentation

Provide the client with:

- API integration documentation
- Frontend user guides
- Template information and limitations
- Contact information for support
- SLA and escalation procedures

### 11.2 Technical Documentation

Create internal documentation including:

- Complete architecture diagram
- Configuration details for all components
- Troubleshooting guide
- Credential management procedures
- Template update process

### 11.3 Training

Provide training for:

- Client's technical team
- Internal support staff
- Account managers
- Operations team

## 12. Common Issues & Troubleshooting

### 12.1 Template Approval Issues

- **Rejection Reasons**: Common reasons WhatsApp rejects templates and how to address them
- **Resubmission Process**: Steps to modify and resubmit templates
- **Category Selection**: Guidance on choosing the appropriate template category

### 12.2 Integration Challenges

- **Data Mapping Issues**: Troubleshooting variable mapping problems
- **API Authentication**: Resolving common authentication errors
- **Rate Limiting**: Handling rate limit exceeded scenarios
- **Webhook Configuration**: Fixing webhook delivery issues

### 12.3 AI Processing Problems

- **Content Variable Generation**: Resolving OpenAI output format issues
- **Assistant Configuration**: Fixing system instruction problems
- **Token Limitations**: Managing large context objects
- **Error Handling**: Strategies for recovery from AI processing failures

## 13. Maintenance & Updates

### 13.1 Template Updates

Process for updating existing templates:

1. Draft the updated template
2. Submit for WhatsApp approval
3. Update Secrets Manager with new template SID
4. Update OpenAI assistant instructions if needed
5. Test the updated template thoroughly
6. Communicate changes to the client

### 13.2 Scaling Considerations

Guidelines for scaling the implementation:

- When to increase Lambda concurrency limits
- DynamoDB capacity planning
- SQS queue scaling considerations
- OpenAI rate limit management

### 13.3 Periodic Reviews

Schedule for regular reviews:

- Quarterly performance reviews
- Monthly cost analysis
- Template effectiveness evaluation
- Security and compliance assessment 