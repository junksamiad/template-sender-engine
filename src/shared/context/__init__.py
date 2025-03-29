"""
Context module for the AI Multi-Communications Engine.

This module provides the context object structure and utilities for managing context
throughout the application's processing flow.
"""

from src.shared.context.models import (
    ContextObject,
    FrontendPayload,
    CompanyData,
    RecipientData,
    ProjectData,
    RequestData,
    WaCompanyDataPayload,
    ProjectRateLimits,
    ChannelConfig,
    WhatsAppConfig,
    SMSConfig,
    EmailConfig,
    AIConfigContext,
    ConversationData,
    Metadata
)
from src.shared.context.serialization import (
    serialize_context,
    deserialize_context
)
from src.shared.context.validation import validate_context

__all__ = [
    'ContextObject',
    'FrontendPayload',
    'CompanyData',
    'RecipientData',
    'ProjectData',
    'RequestData',
    'WaCompanyDataPayload',
    'ProjectRateLimits',
    'ChannelConfig',
    'WhatsAppConfig',
    'SMSConfig',
    'EmailConfig',
    'AIConfigContext',
    'ConversationData',
    'Metadata',
    'serialize_context',
    'deserialize_context',
    'validate_context'
] 