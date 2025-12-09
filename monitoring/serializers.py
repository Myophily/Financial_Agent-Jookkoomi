# monitoring/serializers.py

"""
Serialization utilities for LangChain messages and AgentState.
Handles conversion of complex LangChain objects to JSON-serializable dictionaries.
"""

from typing import List, Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage


def serialize_message(message, full_content: bool = True) -> Dict[str, Any]:
    """
    Serialize a single LangChain message to a JSON-serializable dictionary.

    Args:
        message: LangChain message object (SystemMessage, HumanMessage, AIMessage, ToolMessage)
        full_content: If True, include full message content; if False, truncate to preview

    Returns:
        Dictionary with message data
    """
    msg_type = message.__class__.__name__
    content = getattr(message, 'content', '')

    serialized = {
        "type": msg_type,
        "id": getattr(message, 'id', None),
        "content": content,  # FULL content (no truncation per user preference)
        "content_length": len(content)
    }

    # AIMessage with tool calls
    if isinstance(message, AIMessage) and hasattr(message, 'tool_calls') and message.tool_calls:
        serialized["tool_calls"] = [
            {
                "id": tc.get('id'),
                "name": tc.get('name'),
                "arguments": tc.get('args', {})
            }
            for tc in message.tool_calls
        ]

    # ToolMessage metadata
    if isinstance(message, ToolMessage):
        serialized["tool_call_id"] = getattr(message, 'tool_call_id', None)
        serialized["tool_name"] = getattr(message, 'name', None)

    return serialized


def serialize_messages(messages: List, full_content: bool = True) -> List[Dict[str, Any]]:
    """
    Serialize a list of LangChain messages.

    Args:
        messages: List of LangChain message objects
        full_content: If True, include full message content

    Returns:
        List of serialized message dictionaries
    """
    return [serialize_message(msg, full_content) for msg in messages]


def _serialize_sections(sections: List[str]) -> List[Dict[str, Any]]:
    """
    Serialize list of report sections into structured format.

    Args:
        sections: List of markdown strings (one per part)

    Returns:
        List of dictionaries with part metadata and full content
    """
    if not sections:
        return []

    serialized = []
    for idx, content in enumerate(sections):
        # Handle None or non-string values gracefully
        if content is None:
            content = ""
        elif not isinstance(content, str):
            content = str(content)

        serialized.append({
            "part_number": idx + 1,
            "content": content,
            "char_length": len(content),
            "line_count": content.count('\n') + 1 if content else 0
        })

    return serialized


def serialize_state(state: Dict[str, Any], include_messages: bool = False, full_content: bool = True) -> Dict[str, Any]:
    """
    Serialize AgentState or GroupWorkerState to a JSON-serializable dictionary.

    Args:
        state: State dictionary from LangGraph
        include_messages: If True, include full message serialization
        full_content: If True, include full markdown content of report sections

    Returns:
        Dictionary with state data
    """
    serialized = {
        "target_stock": state.get('target_stock'),
        "current_part": state.get('current_part'),
        "tool_call_count": state.get('tool_call_count'),

        # EXISTING: Backward compatible counts
        "report_sections_count": len(state.get('report_sections', [])),
        "fundamental_sections_count": len(state.get('fundamental_sections', [])),
        "technical_sections_count": len(state.get('technical_sections', [])),
        "sentiment_sections_count": len(state.get('sentiment_sections', [])),
        "macro_sections_count": len(state.get('macro_sections', [])),

        "failed_groups": state.get('failed_groups', []),
        "permanently_failed_groups": state.get('permanently_failed_groups', [])
    }

    # NEW: Serialize full content if enabled
    if full_content:
        serialized.update({
            "report_sections_content": _serialize_sections(state.get('report_sections', [])),
            "fundamental_sections_content": _serialize_sections(state.get('fundamental_sections', [])),
            "technical_sections_content": _serialize_sections(state.get('technical_sections', [])),
            "sentiment_sections_content": _serialize_sections(state.get('sentiment_sections', [])),
            "macro_sections_content": _serialize_sections(state.get('macro_sections', [])),
            "unified_report_exists": bool(state.get('unified_report')),
            "unified_report_content": _serialize_sections(state.get('unified_report', []))
        })

    # EXISTING: Message serialization (unchanged)
    if include_messages:
        messages = state.get('messages', [])
        serialized["messages"] = serialize_messages(messages, full_content=True)
    else:
        serialized["messages_count"] = len(state.get('messages', []))

    return serialized
