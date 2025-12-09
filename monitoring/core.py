# monitoring/core.py

"""
Core monitoring context for JooKkoomi LangGraph application.
Thread-safe singleton that tracks execution, costs, and state evolution.
"""

import os
import threading
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from langchain_core.output_parsers import StrOutputParser

from .writer import MonitoringWriter
from .serializers import serialize_messages, serialize_state
from .token_counter import extract_token_usage
from .cost_calculator import calculate_cost, get_model_name_from_response


class MonitoringContext:
    """
    Thread-safe singleton for comprehensive monitoring of JooKkoomi execution.

    Captures:
    - Execution timeline (all node executions)
    - LLM interactions (requests, responses, tokens, costs)
    - Tool executions (arguments, results, latency)
    - Parallel group tracking (4 subgraphs)
    - State evolution (snapshots at checkpoints)
    - Error tracking (exceptions, tracebacks, retries)

    Design:
    - Singleton pattern: Single instance shared across parent graph and 4 subgraphs
    - Thread-safe: Uses locks for parallel subgraph execution
    - Graceful degradation: Errors in monitoring never break workflow
    - Buffered writes: All data in memory, single JSON write at end
    """

    _instance: Optional['MonitoringContext'] = None
    _lock = threading.Lock()

    def __init__(self, ticker: str, emails: Union[str, List[str]], log_dir: str = "./monitoring_logs"):
        """
        Initialize monitoring context.

        Args:
            ticker: Stock ticker being analyzed
            emails: Recipient email(s) - accepts str or List[str]
            log_dir: Directory for monitoring logs
        """
        self.run_id = str(uuid.uuid4())
        self.ticker = ticker

        # Handle both string (backward compat) and list (new)
        if isinstance(emails, list):
            self.emails_list = emails
            self.email = emails[0] if emails else "unknown"  # for logs
        else:
            self.emails_list = [emails] if emails else []
            self.email = emails

        self.log_dir = log_dir

        # Thread-safe data structures
        self._timeline_lock = threading.Lock()
        self._timeline: List[Dict[str, Any]] = []
        self._parallel_groups: Dict[str, Dict[str, Any]] = {}

        # Cost tracking
        self._cost_summary = {
            "total_tokens": {"input": 0, "output": 0, "total": 0},
            "total_cost_usd": 0.0,
            "llm_calls": 0,
            "tool_calls": 0,
            "gemini_2_5_flash_lite_calls": 0,
            "gemini_2_5_pro_calls": 0
        }

        # State snapshots at key checkpoints
        self._state_snapshots: List[Dict[str, Any]] = []

        # Timestamps
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

        # Writer
        self.writer = MonitoringWriter(log_dir, ticker, self.run_id)

        # Read environment toggle (default: True)
        self.log_full_content = os.getenv('MONITOR_FULL_CONTENT', 'true').lower() == 'true'

    @classmethod
    def get_instance(cls) -> Optional['MonitoringContext']:
        """
        Get singleton instance (thread-safe).

        Returns:
            MonitoringContext instance or None if not initialized
        """
        return cls._instance

    def start(self):
        """
        Initialize monitoring session.
        Sets this instance as the global singleton.
        """
        with MonitoringContext._lock:
            MonitoringContext._instance = self

        self.start_time = datetime.utcnow()
        self.record_event("monitoring_start", status="initialized")

    def record_event(self, event_type: str, **kwargs):
        """
        Record a timeline event (thread-safe).

        Args:
            event_type: Type of event (node_start, node_end, llm_call, tool_call, error, etc.)
            **kwargs: Additional event data
        """
        with self._timeline_lock:
            event = {
                "sequence": len(self._timeline) + 1,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "thread_id": threading.current_thread().name,
                "event_type": event_type,
                **kwargs
            }
            self._timeline.append(event)

    def record_llm_call(
        self,
        graph_name: str,
        part: int,
        request_messages: List,
        response,
        latency_ms: float
    ):
        """
        Record LLM interaction with full content and cost tracking.

        Args:
            graph_name: Name of graph/subgraph (e.g., "fundamental", "main")
            part: Current part number
            request_messages: List of LangChain messages sent to LLM
            response: AIMessage response from LLM
            latency_ms: Response time in milliseconds
        """
        # Extract token usage (only if available)
        token_usage = extract_token_usage(response)

        # Get model name and calculate cost
        model_name = get_model_name_from_response(response)
        cost_usd = calculate_cost(model_name, token_usage)

        # Update cost summary (thread-safe)
        if token_usage:
            with self._timeline_lock:
                self._cost_summary["total_tokens"]["input"] += token_usage.get("input_tokens", 0)
                self._cost_summary["total_tokens"]["output"] += token_usage.get("output_tokens", 0)
                self._cost_summary["total_tokens"]["total"] += token_usage.get("total_tokens", 0)
                self._cost_summary["total_cost_usd"] += cost_usd
                self._cost_summary["llm_calls"] += 1

                # Track model-specific counts
                model_key = model_name.replace(".", "_").replace("-", "_") + "_calls"
                if model_key in self._cost_summary:
                    self._cost_summary[model_key] += 1

        # Serialize tool calls from response
        tool_calls_serialized = []
        if hasattr(response, 'tool_calls') and response.tool_calls:
            tool_calls_serialized = [
                {
                    "id": tc.get('id'),
                    "name": tc.get('name'),
                    "arguments": tc.get('args', {})
                }
                for tc in response.tool_calls
            ]

        # Record event
        self.record_event(
            "llm_call",
            graph_name=graph_name,
            part=part,
            llm_interaction={
                "request": {
                    "model": model_name,
                    "messages": serialize_messages(request_messages, full_content=True),
                    "temperature": 0.0
                },
                "response": {
                    "content": StrOutputParser().invoke(response) if hasattr(response, 'content') else str(response),  # Normalize to string
                    "tool_calls": tool_calls_serialized,
                    "token_usage": token_usage,  # None if not available
                    "cost_usd": cost_usd if token_usage else None,
                    "latency_ms": round(latency_ms, 2)
                }
            }
        )

    def record_tool_call(
        self,
        graph_name: str,
        part: int,
        tool_name: str,
        tool_args: Dict[str, Any],
        result: Any,
        latency_ms: float,
        success: bool,
        error: Optional[str] = None
    ):
        """
        Record tool execution with full result.

        Args:
            graph_name: Name of graph/subgraph
            part: Current part number
            tool_name: Name of tool executed
            tool_args: Arguments passed to tool
            result: Tool execution result
            latency_ms: Execution time in milliseconds
            success: True if tool executed successfully
            error: Error message if failed
        """
        # Update tool call count
        with self._timeline_lock:
            self._cost_summary["tool_calls"] += 1

        # Record event
        self.record_event(
            "tool_call",
            graph_name=graph_name,
            part=part,
            tool_execution={
                "tool_name": tool_name,
                "arguments": tool_args,
                "result": {
                    "success": success,
                    "data": str(result),  # FULL result content
                    "error": error
                },
                "latency_ms": round(latency_ms, 2)
            }
        )

    def start_parallel_group(self, group_name: str, part_range: tuple):
        """
        Mark start of parallel group execution.

        Args:
            group_name: Name of group (e.g., "fundamental")
            part_range: Tuple of (start_part, end_part)
        """
        with self._timeline_lock:
            self._parallel_groups[group_name] = {
                "thread_id": threading.current_thread().name,
                "start_time": datetime.utcnow().isoformat() + "Z",
                "part_range": list(part_range),
                "status": "running",
                "parts_completed": [],
                "retry_count": 0
            }

    def end_parallel_group(self, group_name: str, status: str, sections: List[str]):
        """
        Mark end of parallel group execution.

        Args:
            group_name: Name of group
            status: Status ("completed" or "failed")
            sections: List of completed section contents
        """
        with self._timeline_lock:
            if group_name in self._parallel_groups:
                end_time = datetime.utcnow()

                # Calculate duration
                start_time_str = self._parallel_groups[group_name]["start_time"]
                
                # [Modified] Remove timezone info to allow naive datetime operations
                # Previous: start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                start_time = datetime.fromisoformat(start_time_str.replace('Z', ''))
                
                duration = (end_time - start_time).total_seconds()

                # Update group data
                self._parallel_groups[group_name].update({
                    "end_time": end_time.isoformat() + "Z",
                    "duration_seconds": round(duration, 3),
                    "status": status,
                    "parts_completed": list(range(1, len(sections) + 1)),
                    "sections_count": len(sections)
                })

    def record_state_snapshot(self, checkpoint_name: str, state: Dict[str, Any]):
        """
        Record state snapshot at key checkpoint.

        Args:
            checkpoint_name: Name of checkpoint (e.g., "initialization", "combine_results_output")
            state: State dictionary from LangGraph
        """
        snapshot = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "checkpoint": checkpoint_name,
            "state": serialize_state(
                state,
                include_messages=False,
                full_content=self.log_full_content  # NEW: Pass toggle
            )
        }

        with self._timeline_lock:
            self._state_snapshots.append(snapshot)

    def record_error(self, exception: Exception, context: str):
        """
        Record exception with full traceback.

        Args:
            exception: Exception instance
            context: Context string (e.g., "main.run_analysis")
        """
        import traceback as tb

        self.record_event(
            "error",
            error={
                "error_type": type(exception).__name__,
                "error_message": str(exception),
                "traceback": tb.format_exc(),
                "context": context
            }
        )

    def finalize(self, status: str = "completed", failure_reason: Optional[str] = None):
        """
        Finalize monitoring and write JSON log file.

        Args:
            status: Overall status ("completed", "failed", "partial")
            failure_reason: Reason for failure if status is "failed"
        """
        self.end_time = datetime.utcnow()

        # Calculate duration
        if self.start_time:
            duration = (self.end_time - self.start_time).total_seconds()
        else:
            duration = 0.0

        # Build complete log data
        log_data = {
            "run_metadata": {
                "run_id": self.run_id,
                "ticker": self.ticker,
                "email": self.email,  # First recipient (backward compat)
                "emails": self.emails_list,  # All recipients (new)
                "start_time": self.start_time.isoformat() + "Z" if self.start_time else None,
                "end_time": self.end_time.isoformat() + "Z",
                "duration_seconds": round(duration, 3),
                "status": status,
                "failure_reason": failure_reason
            },
            "cost_summary": self._cost_summary,
            "execution_timeline": self._timeline,
            "parallel_execution_tracking": {
                "dispatch_timestamp": self.start_time.isoformat() + "Z" if self.start_time else None,
                "groups": self._parallel_groups
            },
            "state_evolution": self._state_snapshots
        }

        # Write to file
        self.writer.write(log_data)

        # Cleanup singleton instance
        with MonitoringContext._lock:
            MonitoringContext._instance = None
