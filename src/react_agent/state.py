"""Define the state structures for the agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from langgraph.graph import MessagesState


class MessageRole(str, Enum):
    """Roles in the conversation."""
    MEMBER = "member"
    SYSTEM = "system"
    AGENT = "agent"


@dataclass
class ConversationMessage:
    """A single message in the member-system conversation."""
    role: MessageRole
    content: str
    timestamp: Optional[str] = None
    

@dataclass
class EscalationContext:
    """Context about why this conversation is being escalated."""
    reason: Optional[str] = None
    urgency: Optional[str] = None  # low, medium, high
    member_sentiment: Optional[str] = None  # frustrated, confused, satisfied, etc.


@dataclass
class ServiceCoverage:
    """Coverage details for a specific service type."""
    in_network_copay_non_hospital: Optional[str] = None
    in_network_copay_hospital: Optional[str] = None
    out_of_network_coinsurance: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class PlanCoverage:
    """Plan coverage details for various service types."""
    diagnostic_radiology: Optional[ServiceCoverage] = None
    # Can extend with other service types as needed


@dataclass
class PatientData:
    """Patient/member information for context."""
    name: Optional[str] = None
    mrn: Optional[str] = None
    member_id: Optional[str] = None
    dob: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    insurance: Optional[str] = None
    zip: Optional[str] = None
    address: Optional[str] = None
    pcp: Optional[str] = None
    plan_name: Optional[str] = None
    plan_type: Optional[str] = None
    coverage: Optional[PlanCoverage] = None


@dataclass
class ProposedResponse:
    """The agent's proposed next message for the human agent."""
    message: str
    reasoning: str
    suggested_tone: str  # empathetic, professional, apologetic, etc.
    confidence_score: float  # 0.0 to 1.0, representing confidence in response appropriateness
    relevant_docs: List[str] = field(default_factory=list)
    key_points: List[str] = field(default_factory=list)


class InputState(MessagesState):
    """Defines the input state for the agent, inheriting from MessagesState.

    This class represents the narrower interface to the outside world.
    """

    conversation_history: List[ConversationMessage] = field(
        default_factory=list,
        metadata={"description": "The conversation between member and automated system"}
    )

    escalation_context: Optional[EscalationContext] = None

    patient_data: Optional[PatientData] = None


class State(InputState):
    """Represents the complete state of the agent, extending InputState.
    
    This class stores all information needed throughout the agent's lifecycle.
    """
    
    # Output: Proposed response for the human agent
    proposed_response: Optional[ProposedResponse] = None
    
    # Track which docs were accessed during reasoning
    accessed_documents: List[str] = field(default_factory=list)
