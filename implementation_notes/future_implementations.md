# Future Implementation Ideas: Cross-Channel Conversation Handling

This document captures concepts discussed regarding potential future enhancements to enable the AI Multi-Comms Engine to handle conversations seamlessly across multiple channels (e.g., WhatsApp, Email, SMS) initiated from a single request.

## 1. Core Goal & Challenge

-   **Goal:** Allow a single logical conversation thread to persist and be updated via replies received on different channels (e.g., initiate via API targeting WhatsApp & Email, user replies via WhatsApp, AI considers this, user then replies via Email, AI considers both previous messages).
-   **Challenge:** How to link replies arriving via different identifiers (phone number vs. email address) back to the same logical conversation thread, especially for database lookups and state management.

## 2. Initial Sending: SNS Fan-Out

-   If an initial request needs to trigger messages on multiple channels simultaneously (e.g., `channel_method: ["whatsapp", "email"]` or `"all"`), using **AWS SNS Fan-Out** is the recommended pattern.
-   The Channel Router (or preceding service) publishes **one** message (containing the request context) to an SNS Topic.
-   Separate SQS queues for each channel processor (WhatsApp, Email, SMS) subscribe to this SNS Topic.
-   SNS automatically delivers a copy of the message to each subscribed queue.
-   This decouples the router from the downstream queues and simplifies the sending logic compared to the router manually sending to multiple SQS queues.

## 3. Enabling Unified AI Context: Pre-computation & Shared `thread_id`

-   To allow the OpenAI Assistant to maintain context across channels, the **OpenAI `thread_id` must be established *before* fanning out** the request to individual channel processors.
-   **Revised Flow:**
    1.  API request received.
    2.  A service (potentially the Router, or a new preceding service) interacts with the OpenAI Assistant **first** to generate the initial message content and, crucially, **obtain the `thread_id`**.
    3.  The context object passed to SNS includes this **shared `thread_id`**.
    4.  Downstream channel processors receive the context (including the shared `thread_id`) via their SQS queue.
    5.  Channel processors send the message using their respective APIs (Twilio/SendGrid) and create/update records in the `conversations` database, storing the **shared `thread_id`** in each relevant record.

## 4. Database Models for Cross-Channel Context

Two main approaches were discussed for storing conversation data when using a shared `thread_id`:

### Option A: Multiple Records per Logical Conversation (Channel-Specific Partitions)

-   **Structure:** Maintain the current schema pattern (`conversations-db-schema-v1.0.md`). Create separate records in DynamoDB for each channel the message was sent to via fan-out. One record partitioned by `recipient_tel` for WhatsApp, another by `recipient_email` for Email, etc.
-   **Link:** All these separate records store the **same shared `thread_id`** obtained during pre-computation.
-   **Reply Lookup:** Use the primary key lookup relevant to the channel the reply arrived on (e.g., query by `recipient_tel` for WhatsApp reply, query `MessageIdIndex` GSI for Email reply based on headers).
-   **AI Context:** Extract the `thread_id` from the found record. Pass this `thread_id` to the AI Assistant. The Assistant retrieves the unified history associated with that thread.
-   **Pros:** Aligns with DynamoDB strengths (efficient PK lookups), simpler item schema, significantly less complex concurrency management (updates target different items).
-   **Cons:** The logical conversation is represented by multiple physical DB records.

### Option B: Single Record per Logical Conversation (`thread_id` as PK)

-   **Structure:** Create **one single record** in DynamoDB for the entire logical conversation, regardless of how many channels are involved.
    -   **Primary Key:** Use the shared `thread_id` as the Partition Key.
    -   **Attributes:** The item must store all potentially relevant identifiers needed for lookups (`recipient_tel`, `recipient_email`, `company_whatsapp_number`, `company_sms_number`, `initial_email_message_id`, etc.) and the `messages` list (containing entries from all channels).
-   **Reply Lookup:** Requires specific **Global Secondary Indexes (GSIs)** to map incoming reply identifiers back to the `thread_id` (the table's PK).
    -   Example GSI (WhatsApp/SMS): PK=`company_whatsapp_sms_number`, SK=`recipient_tel`, Projects=`thread_id`.
    -   Example GSI (Email): PK=`initial_email_message_id`, Projects=`thread_id`.
    -   The Reply Handler queries the appropriate GSI based on the reply channel to find the `thread_id`, then does a `GetItem` using the `thread_id` to fetch the full record.
-   **AI Context:** Extract the `thread_id` (which is the PK) and pass to the AI Assistant.
-   **Pros:** Represents the logical conversation as a single DB entity. Achieves unified AI context.
-   **Cons:** Requires careful GSI design and management. **Introduces significant update concurrency challenges**, as replies from different channels will attempt to read and write to the *same single* DynamoDB item. Requires robust concurrency control mechanisms (e.g., optimistic locking, queue-based locking).

## 5. Concurrency Control for Single Record Model (Option B)

-   If pursuing Option B, managing concurrent updates to the single conversation record is critical.
-   A potential strategy involves implementing a locking mechanism, possibly at the SQS processing level for the Reply Handler:
    1.  When a reply message for a specific `thread_id` is picked up for processing, acquire a lock (e.g., using a separate DynamoDB table acting as a mutex, or an external locking service) for that `thread_id`.
    2.  If the lock is acquired, proceed with AI interaction and database update.
    3.  Release the lock upon completion (success or failure).
    4.  If the lock cannot be acquired (another process holds it), the message should be returned to the queue (e.g., by increasing its visibility timeout) to be retried later.
-   This serializes updates for a given `thread_id`, preventing race conditions and data loss, but adds complexity and potential processing delays.

## 6. Recommendation Summary (for Future Enhancement)

-   Using **SNS Fan-Out** is recommended for distributing a single request to multiple channel queues.
-   Achieving **unified AI context** requires **AI pre-computation** to establish a shared `thread_id` before fan-out.
-   Storing conversation data using **Option A (Multiple Records + Shared `thread_id`)** is architecturally simpler, aligns better with DynamoDB patterns, and avoids complex concurrency issues while still delivering the unified AI context.
-   Storing conversation data using **Option B (Single Record + GSIs)** provides a unified data entity but requires significant GSI management and robust concurrency control implementation.

This document provides a starting point for designing a cross-channel conversation system if this becomes a future requirement.

## 7. API Resilience Enhancements (Client-Side Retries & Advanced Error Handling)

- **Consideration:** Implement client-side retry mechanisms (e.g., exponential backoff with jitter, potentially adaptive rate limiting or circuit breaking) for external API calls, particularly for interactions with the OpenAI API. More granular exception handling (catching specific API errors) could also be implemented.
- **Rationale:** While the initial build relies on the broader SQS retry mechanism for simplicity and anticipated traffic levels, implementing client-side retries directly around specific API calls can handle transient network issues, rate limits (`429`), or temporary server errors (`5xx`) more efficiently and quickly. Similarly, granular error handling can allow for more tailored responses or metrics based on specific failure types.
- **Reference:** Detailed patterns and example implementations for exponential backoff, adaptive rate limiting, and circuit breaking specifically for OpenAI calls are documented in the LLD section: `lld/processing-engines/whatsapp/05-openai-integration.md` (Section 3: Rate Limit Handling with Exponential Backoff). This should be reviewed if higher resilience or throughput becomes necessary.
- **Initial Deployment Decision (v1.0):** For the initial deployment phase, the implementation of internal client-side retries, more granular exception handling beyond standard logging, and circuit breaker patterns was explicitly **deferred**. The focus was placed on rapid deployment, utilizing the built-in SQS retry/DLQ mechanism as the primary resilience strategy against transient errors. These advanced patterns remain as potential future enhancements if testing or operational monitoring indicates they are required.

## 8. Operational Refinements

-   **SQS Heartbeat Optimization:** Modify the instantiation of the `SQSHeartbeat` utility within the channel processor Lambdas (currently `whatsapp-channel-processor-dev`) to explicitly pass the actual SQS queue visibility timeout (e.g., 905 seconds for the WhatsApp queue) as the `visibility_timeout_sec` parameter. This would ensure the heartbeat mechanism fully utilizes the configured buffer, rather than defaulting to extending to 600 seconds. 