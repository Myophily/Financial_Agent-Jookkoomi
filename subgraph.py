# subgraph.py

"""
Defines subgraphs for each analysis group (Fundamental, Technical, Sentiment, Macro).
Each subgraph runs independently and processes parts sequentially.
"""

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, ToolMessage, SystemMessage, RemoveMessage
import time
import yfinance as yf

# Monitoring system
from monitoring.decorators import monitor_subgraph_node
from monitoring.core import MonitoringContext

from state import GroupWorkerState
from llm import model, model_with_tools, str_parser
from tools import tools
from prompts import PART_TITLES, get_core_system_prompt, get_part_prompt, NEEDED_TOOLS
from utils.text_cleaning import clean_trailing_spaces

# Configuration for part-level delays
PART_DELAY_SECONDS = 90  # Delay before each part analysis starts (except first part in each group)


def create_group_subgraph(group_name: str, part_range: tuple[int, int]):
    """
    Factory function to create a subgraph for a specific analysis group.

    Args:
        group_name: Group name ("fundamental", "technical", "sentiment", "macro")
        part_range: Part range to process (start, end) e.g., (1, 5)

    Returns:
        Compiled subgraph app
    """

    # Group state key mapping
    group_state_key_map = {
        "fundamental": "fundamental_sections",
        "technical": "technical_sections",
        "sentiment": "sentiment_sections",
        "macro": "macro_sections"
    }

    state_key = group_state_key_map[group_name]
    start_part, end_part = part_range

    def get_company_name(ticker: str) -> str:
        """
        Gets company name from stock ticker using yfinance.
        Args:
            ticker (str): Stock ticker (e.g., '005930' or 'AAPL')
        Returns:
            str: Company name (returns 'N/A' if fetch fails)
        """
        try:
            # Determine if Korean stock (ticker consisting of digits only)
            is_korean_stock = ticker.isdigit()
            yf_ticker = f"{ticker}.KS" if is_korean_stock else ticker

            # Get company info using yfinance
            stock = yf.Ticker(yf_ticker)
            info = stock.info

            # Return shortName or longName
            return info.get('shortName', info.get('longName', 'N/A'))
        except Exception as e:
            print(f"--- [{group_name.upper()}] Failed to fetch company name: {e} ---")
            return 'N/A'

    @monitor_subgraph_node
    def initialize_group(state: GroupWorkerState) -> dict:
        """
        First node of the group subgraph.
        Generates the initial prompt for the first part.
        """
        print(f"--- [{group_name.upper()}] Group initialization (Part {start_part}-{end_part}) ---")

        target_stock = state['target_stock']
        current_date = state.get('current_date')  # Extract current date
        company_name = get_company_name(target_stock)  # Get company name
        first_part_instructions = get_part_prompt(start_part)
        part_title = PART_TITLES[start_part - 1]
        needed_tools = NEEDED_TOOLS[start_part - 1]

        user_prompt = f"""
Starting analysis.
Now starting **PART {start_part}: {part_title}**.

* Target Stock: {target_stock}
* Company Name: {company_name}
* Required Tools: {needed_tools}

{first_part_instructions}

Use provided tools to collect necessary data or news.
"""

        return {
            "messages": [
                SystemMessage(content=get_core_system_prompt(current_date)),
                HumanMessage(content=user_prompt)
            ],
            "current_part": start_part,
            "tool_call_count": 0
        }

    @monitor_subgraph_node
    def run_part_analysis(state: GroupWorkerState) -> dict:
        """
        Performs analysis for the current part.
        Calls tools or returns analysis results.
        """
        current_part = state['current_part']

        # Delay before part execution (skip first part in each group)
        if current_part > start_part:
            print(f"--- [{group_name.upper()}] Waiting {PART_DELAY_SECONDS}s before Part {current_part} ({PART_TITLES[current_part - 1]}) ---")
            time.sleep(PART_DELAY_SECONDS)

        messages = state['messages']
        tool_call_count = state.get('tool_call_count', 0)
        target_stock = state['target_stock']

        # Get monitoring context
        monitor = MonitoringContext.get_instance()

        print(f"--- [{group_name.upper()}] Analyzing Part {current_part}/{end_part} ---")

        # Detect state after tool execution and add guidance message
        if messages and isinstance(messages[-1], ToolMessage):
            current_title = PART_TITLES[current_part - 1]

            if tool_call_count >= 5:
                print(f"--- [{group_name.upper()}] Part {current_part}: tool call limit reached (5) ---")
                reminder = HumanMessage(content=f"""
Tool call limit reached (maximum 5 calls).

Please complete the analysis for PART {current_part} ({current_title}) based on the data collected so far.

**Important**: Do not call any more tools. Generate and output the analysis results immediately using the information collected so far.
""")
            else:
                reminder = HumanMessage(content=f"""
Tool execution results received.

Please now complete the analysis for PART {current_part} ({current_title}).

**Guidelines**:
1. If the collected data is sufficient, generate and output the analysis results.
2. Only use tools again if additional data is absolutely necessary.
3. Do not repeatedly call the same tool with the same arguments.
4. Current tool call count: {tool_call_count + 1}/5
""")
            messages = messages + [reminder]

        # LLM call (tool limit check) - includes retry logic
        max_retries = 2  # 2 retries per part (total 3 attempts)

        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    delay = 1.5 * (2 ** (attempt - 1))  # 1.5s, 3s
                    print(f"--- [{group_name.upper()}] Part {current_part}: {delay}s later retry ({attempt + 1}/{max_retries + 1}) ---")
                    time.sleep(delay)

                # Record LLM call start time
                llm_start_time = time.time()

                if tool_call_count >= 5:
                    print(f"--- [{group_name.upper()}] Part {current_part}: Using model without tools ---")
                    response = model.invoke(messages)
                else:
                    response = model_with_tools.invoke(messages)

                # Record LLM call monitoring
                if monitor:
                    llm_latency_ms = (time.time() - llm_start_time) * 1000
                    monitor.record_llm_call(
                        graph_name=group_name,
                        part=current_part,
                        request_messages=messages,
                        response=response,
                        latency_ms=llm_latency_ms
                    )

                # AI 응답 출력
                print(f"\n{'='*80}")
                print(f"[{group_name.upper()}] Part {current_part} - AI Response")
                print(f"{'='*80}")
                # Normalize content for consistent display
                content_str = str_parser.invoke(response)
                print(f"Response Length: {len(content_str)} chars")
                print(f"Stop Reason: {response.response_metadata.get('finish_reason')}") # Check why the model stopped
                print("-" * 20 + " RAW CONTENT START " + "-" * 20)
                print(repr(content_str)) # Use repr() to see all hidden special characters
                print("-" * 20 + " RAW CONTENT END " + "-" * 20)
                print(f"Tool Calls: {len(response.tool_calls) if response.tool_calls else 0}")
                print(f"{'='*80}\n")

                # Exit loop on success
                break

            except Exception as e:
                print(f"--- [{group_name.upper()}] Part {current_part}: LLM call failed ({attempt + 1}/{max_retries + 1}) ---")
                print(f"--- Error: {str(e)[:100]} ---")

                if attempt == max_retries:
                    # Raise exception when all retries fail (handled at upper level)
                    print(f"--- [{group_name.upper()}] Part {current_part}: All retries failed, treating as group failure ---")
                    raise Exception(f"Part {current_part} LLM call failed (retried {max_retries + 1} times): {str(e)[:200]}")

        # Log when retry is successful
        if attempt > 0:
            print(f"--- [{group_name.upper()}] Part {current_part}: Retry successful ({attempt + 1}th attempt) ---")

        # When tool calls are requested
        if response.tool_calls:
            print(f"--- [{group_name.upper()}] Part {current_part}: Tool usage requested: {', '.join([tc['name'] for tc in response.tool_calls])} ---")
            new_tool_call_count = tool_call_count + 1
            print(f"--- [{group_name.upper()}] Part {current_part}: Tool calls: {new_tool_call_count}/5 ---")

            return {
                "messages": [response],
                "tool_call_count": new_tool_call_count
            }

        # Analysis complete (no tool calls)
        else:
            print(f"--- [{group_name.upper()}] Part {current_part} analysis complete ---")
            # Use StrOutputParser to ensure string output (handles both string and list)
            analysis_result = str_parser.invoke(response)
            next_part = current_part + 1

            messages_to_return = [response]

            # If there is a next part within the group
            if next_part <= end_part:
                next_title = PART_TITLES[next_part - 1]
                needed_tools = NEEDED_TOOLS[next_part - 1]
                next_part_instructions = get_part_prompt(next_part)

                user_prompt = f"""
PART {current_part} ({PART_TITLES[current_part - 1]}) has been completed.
The analysis results have been saved.

Now starting **PART {next_part} ({next_title})**.

* Target Stock: {target_stock}
* Required Tools: {needed_tools}

{next_part_instructions}
"""
                # [Modified] Reset messages if not sentiment group (excluding SystemMessage)
                if group_name != "sentiment":
                    # Delete all non-SystemMessage messages (based on current state)
                    messages_to_clear = [m for m in state['messages'] if not isinstance(m, SystemMessage)]
                    cleanup_messages = [RemoveMessage(id=m.id) for m in messages_to_clear if m.id]

                    # Add only new prompt for next part (reset context by excluding previous response)
                    messages_to_return = cleanup_messages + [HumanMessage(content=user_prompt)]
                else:
                    # Keep conversation history for sentiment group
                    messages_to_return.append(HumanMessage(content=user_prompt))

                return {
                    "messages": messages_to_return,
                    state_key: [clean_trailing_spaces(analysis_result)],  # Clean before saving
                    "current_part": next_part,
                    "tool_call_count": 0
                }

            # All parts complete for the group
            else:
                print(f"--- [{group_name.upper()}] Group analysis complete (Part {start_part}-{end_part}) ---")
                return {
                    "messages": messages_to_return,
                    state_key: [clean_trailing_spaces(analysis_result)],  # Clean before saving
                    "current_part": next_part
                }

    @monitor_subgraph_node
    def execute_tools_in_group(state: GroupWorkerState) -> dict:
        """
        Executes requested tools and returns results.
        """
        current_part = state['current_part']

        # Get monitoring context
        monitor = MonitoringContext.get_instance()

        print(f"--- [{group_name.upper()}] Part {current_part}: tool execution ---")

        last_message = state['messages'][-1]
        tool_messages = []
        tool_map = {tool.name: tool for tool in tools}

        for tool_call in last_message.tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['args']

            if tool_name in tool_map:
                tool_function = tool_map[tool_name]
                print(f"--- [{group_name.upper()}] Executing: {tool_name}({tool_args}) ---")

                try:
                    # Record tool execution start time
                    tool_start_time = time.time()

                    result = tool_function.invoke(tool_args)

                    # Record tool execution monitoring (success)
                    if monitor:
                        tool_latency_ms = (time.time() - tool_start_time) * 1000
                        monitor.record_tool_call(
                            graph_name=group_name,
                            part=current_part,
                            tool_name=tool_name,
                            tool_args=tool_args,
                            result=result,
                            latency_ms=tool_latency_ms,
                            success=True
                        )

                    tool_messages.append(
                        ToolMessage(
                            content=str(result),
                            tool_call_id=tool_call['id'],
                            name=tool_name
                        )
                    )

                except Exception as e:
                    # Record tool execution monitoring (failure)
                    if monitor:
                        tool_latency_ms = (time.time() - tool_start_time) * 1000 if 'tool_start_time' in locals() else 0
                        monitor.record_tool_call(
                            graph_name=group_name,
                            part=current_part,
                            tool_name=tool_name,
                            tool_args=tool_args,
                            result=str(e),
                            latency_ms=tool_latency_ms,
                            success=False,
                            error=str(e)
                        )

                    print(f"--- [{group_name.upper()}] Tool execution error: {e} ---")
                    tool_messages.append(
                        ToolMessage(
                            content=f"Tool execution error: {e}",
                            tool_call_id=tool_call['id'],
                            name=tool_name
                        )
                    )
            else:
                tool_messages.append(
                    ToolMessage(
                        content=f"Tool '{tool_name}' not found.",
                        tool_call_id=tool_call['id'],
                        name=tool_name
                    )
                )

        return {"messages": tool_messages}

    def should_continue_in_group(state: GroupWorkerState) -> str:
        """
        Determines the next step within the group subgraph.
        """
        last_message = state['messages'][-1]

        # When tool calls are requested
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "execute_tools"

        # All parts complete for the group
        if state['current_part'] > end_part:
            return END

        # Continue analysis for next part
        return "run_part_analysis"

    # Build subgraph
    subgraph = StateGraph(GroupWorkerState)

    # Add nodes
    subgraph.add_node("initialize_group", initialize_group)
    subgraph.add_node("run_part_analysis", run_part_analysis)
    subgraph.add_node("execute_tools", execute_tools_in_group)

    # Connect edges
    subgraph.set_entry_point("initialize_group")
    subgraph.add_edge("initialize_group", "run_part_analysis")

    subgraph.add_conditional_edges(
        "run_part_analysis",
        should_continue_in_group,
        {
            "execute_tools": "execute_tools",
            "run_part_analysis": "run_part_analysis",
            END: END
        }
    )

    subgraph.add_edge("execute_tools", "run_part_analysis")

    # Compile (without checkpointer - managed by parent graph)
    return subgraph.compile()


# Create subgraph instances for each group
fundamental_subgraph = create_group_subgraph("fundamental", (1, 5))
technical_subgraph = create_group_subgraph("technical", (6, 8))
sentiment_subgraph = create_group_subgraph("sentiment", (9, 11))
macro_subgraph = create_group_subgraph("macro", (12, 15))
