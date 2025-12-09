# monitoring/decorators.py

"""
Decorators for automatic instrumentation of LangGraph nodes.
Provides non-intrusive monitoring with graceful error handling.
"""

import functools
import time
from typing import Callable

from .core import MonitoringContext


def monitor_node(node_name: str, graph_name: str) -> Callable:
    """
    Decorator for parent graph nodes (in graph.py).

    Automatically captures:
    - Node execution start/end
    - Execution duration
    - State snapshots before/after
    - Errors and exceptions

    Args:
        node_name: Name of the node function
        graph_name: Name of the graph ("main")

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(state, *args, **kwargs):
            monitor = MonitoringContext.get_instance()

            # Graceful degradation: if monitoring not initialized, just run the function
            if not monitor:
                return func(state, *args, **kwargs)

            try:
                # Pre-execution
                monitor.record_event(
                    "node_start",
                    node_type="parent",
                    graph_name=graph_name,
                    node_name=node_name
                )
                monitor.record_state_snapshot(f"{node_name}_input", state)

                # Execute node
                start_time = time.time()
                result = func(state, *args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                # Post-execution
                monitor.record_event(
                    "node_end",
                    node_type="parent",
                    graph_name=graph_name,
                    node_name=node_name,
                    duration_ms=round(duration_ms, 2)
                )

                # Record output state snapshot (if result is a dict)
                if isinstance(result, dict):
                    monitor.record_state_snapshot(f"{node_name}_output", result)

                return result

            except Exception as e:
                # Record error but re-raise to maintain normal error handling
                try:
                    monitor.record_error(e, context=f"{graph_name}.{node_name}")
                except:
                    pass  # Don't let monitoring errors break the workflow

                raise  # Re-raise original exception

        return wrapper
    return decorator


def monitor_subgraph_node(func: Callable) -> Callable:
    """
    Decorator for subgraph nodes (in subgraph.py).

    Extracts graph_name from state automatically.
    Captures node execution metrics and errors.

    Args:
        func: Node function to decorate

    Returns:
        Decorated function
    """
    @functools.wraps(func)
    def wrapper(state, *args, **kwargs):
        monitor = MonitoringContext.get_instance()

        # Graceful degradation
        if not monitor:
            return func(state, *args, **kwargs)

        # Extract graph name and part from state
        graph_name = state.get('group_name', 'unknown_subgraph')
        node_name = func.__name__
        current_part = state.get('current_part')

        try:
            # Pre-execution
            monitor.record_event(
                "node_start",
                node_type="subgraph",
                graph_name=graph_name,
                node_name=node_name,
                part=current_part
            )

            # Execute node
            start_time = time.time()
            result = func(state, *args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000

            # Post-execution
            monitor.record_event(
                "node_end",
                node_type="subgraph",
                graph_name=graph_name,
                node_name=node_name,
                part=current_part,
                duration_ms=round(duration_ms, 2)
            )

            return result

        except Exception as e:
            # Record error but re-raise
            try:
                monitor.record_error(e, context=f"{graph_name}.{node_name}")
            except:
                pass  # Don't let monitoring errors break the workflow

            raise  # Re-raise original exception

    return wrapper
