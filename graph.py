# graph.py

import time

# LangChain/LangGraph core imports
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage, RemoveMessage
from monitoring.decorators import monitor_node

# Project imports
from state import AgentState
from llm import model, model_with_tools, model_str, model_pro, model_pro_str
from tools import tools
from prompts import PART_TITLES, get_core_system_prompt, get_part_prompt, NEEDED_TOOLS
from utils.text_cleaning import clean_trailing_spaces
from reporter import generate_and_send_report
from subgraph import fundamental_subgraph, technical_subgraph, sentiment_subgraph, macro_subgraph

# --- API Rate Limit Mitigation: Delays between group executions ---
GROUP_DELAYS = {
    "fundamental": 90,   # 90 seconds after Fundamental
    "technical": 90,     # 90 seconds after Technical
    "sentiment": 90,     # 90 seconds after Sentiment
    "macro": 0           # No delay after Macro (Part 16 has its own delay)
}
PART16_DELAY = 90        # 90 seconds before Part 16
UNIFY_REPORT_DELAY = 90  # 90 seconds before unify_report

# === Graph Node Definitions ===

# === Parallel Processing Node ===

@monitor_node(node_name="dispatch_parallel_groups", graph_name="main")
def dispatch_parallel_groups(state: AgentState) -> dict:
    """
    Executes 4 analysis groups sequentially.
    Waits a specified time after each group completion considering API rate limits.
    Failed groups are retried once using exponential backoff.
    """
    print("=" * 80)
    print("Sequential Analysis Starting: 4 Groups Sequential Execution (API Rate Limit Consideration)")
    print("    - Fundamental (Part 1-5) → 90s wait")
    print("    - Technical (Part 6-8) → 90s wait")
    print("    - Sentiment (Part 9-11) → 90s wait")
    print("  - Macro (Part 12-15)")
    print("=" * 80)

    target_stock = state['target_stock']
    current_date = state.get('current_date')  # Extract current date
    retry_counts = state.get('group_retry_counts', {})  # Track retry counts

    # Prepare initial state for each group
    group_configs = [
        ("fundamental", fundamental_subgraph, (1, 5), "fundamental_sections"),
        ("technical", technical_subgraph, (6, 8), "technical_sections"),
        ("sentiment", sentiment_subgraph, (9, 11), "sentiment_sections"),
        ("macro", macro_subgraph, (12, 15), "macro_sections")
    ]

    def execute_subgraph(group_name, subgraph, part_range, state_key):
        """Helper function to execute subgraph and return results"""
        from monitoring.core import MonitoringContext
        monitor = MonitoringContext.get_instance()

        try:
            # Monitoring: Record parallel group start
            if monitor:
                monitor.start_parallel_group(group_name, part_range)

            print(f"[{group_name.upper()}] group execution starting...")

            # Configure subgraph input state
            subgraph_input = {
                "target_stock": target_stock,
                "current_date": current_date,  # Pass date to subgraph
                "group_name": group_name,
                "part_range": part_range,
                "current_part": part_range[0],
                "tool_call_count": 0,
                "messages": [],
                "fundamental_sections": [],
                "technical_sections": [],
                "sentiment_sections": [],
                "macro_sections": [],
                "failed_groups": []
            }

            # Execute subgraph
            result = subgraph.invoke(subgraph_input)

            # Extract sections for the group from the result
            sections = result.get(state_key, [])

            # Monitoring: Record parallel group completion
            if monitor:
                monitor.end_parallel_group(group_name, "completed", sections)

            print(f"[{group_name.upper()}] group complete: {len(sections)}parts")

            return (group_name, state_key, sections, None)

        except Exception as e:
            # Monitoring: Record parallel group failure
            if monitor:
                monitor.end_parallel_group(group_name, "failed", [])

            print(f"[{group_name.upper()}] group execution failed: {e}")
            return (group_name, state_key, [], str(e))

    # Sequential execution with delays
    results = {}
    permanently_failed = []
    retried_groups = []

    for i, (group_name, subgraph, part_range, state_key) in enumerate(group_configs):
        print(f"\n{'='*80}")
        print(f"[{i+1}/4] {group_name.upper()} group execution starting...")
        print(f"{'='*80}")

        # First attempt
        _, _, sections, error = execute_subgraph(
            group_name, subgraph, part_range, state_key
        )

        # Process results
        if error:
            # Retry logic
            current_retry_count = retry_counts.get(group_name, 0)

            if current_retry_count >= 1:  # Skip if already retried once
                print(f"[{group_name.upper()}] Maximum retry count exceeded, marking as permanently failed")
                permanently_failed.append(group_name.capitalize())
            else:
                # Apply exponential backoff
                delay = 2.0 * (2 ** current_retry_count)  # 2s, 4s, 8s...
                print(f"[{group_name.upper()}] {delay}s after retry (attempt {current_retry_count + 2}/2)...")
                time.sleep(delay)

                # Execute retry
                retry_counts[group_name] = current_retry_count + 1
                _, _, sections, error = execute_subgraph(
                    group_name, subgraph, part_range, state_key
                )

                if error:
                    print(f"⚠️  {group_name.capitalize()} group retry failed: {error}")
                    permanently_failed.append(group_name.capitalize())
                else:
                    print(f"✓  {group_name.capitalize()} group retry successful!")
                    results[state_key] = sections
                    retried_groups.append(group_name.capitalize())
        else:
            results[state_key] = sections

        # Wait for API Rate Limit between groups (excluding the last group)
        inter_group_delay = GROUP_DELAYS.get(group_name, 0)
        if inter_group_delay > 0:
            print(f"⏱️  API Rate Limit consideration: {inter_group_delay}s waiting...")
            time.sleep(inter_group_delay)

    # Final result output
    print("\n" + "=" * 80)
    total_success = 4 - len(permanently_failed)
    print(f"Sequential analysis complete: {total_success}/4 groups successful")
    if retried_groups:
        print(f"Retry successful: {', '.join(retried_groups)}")
    if permanently_failed:
        print(f"Permanently failed: {', '.join(permanently_failed)}")
    print("=" * 80)

    # Return results (store each group's sections in the corresponding state key)
    update = {
        "fundamental_sections": results.get("fundamental_sections", []),
        "technical_sections": results.get("technical_sections", []),
        "sentiment_sections": results.get("sentiment_sections", []),
        "macro_sections": results.get("macro_sections", []),
        "failed_groups": [f"{g} (retry successful)" for g in retried_groups],
        "permanently_failed_groups": permanently_failed,
        "group_retry_counts": retry_counts
    }

    return update


@monitor_node(node_name="combine_results", graph_name="main")
def combine_results(state: AgentState) -> dict:
    """
    Integrates analysis results from 4 groups and stores them in report_sections.
    Handles partial results if any groups failed.
    Includes retry success and permanent failure information.
    """
    print("=" * 80)
    print("Sequential analysis complete: Integrating results")
    print("=" * 80)

    # Collect results from each group
    fundamental = state.get('fundamental_sections', [])
    technical = state.get('technical_sections', [])
    sentiment = state.get('sentiment_sections', [])
    macro = state.get('macro_sections', [])

    # Track failures
    retried_and_succeeded = state.get('failed_groups', [])
    permanently_failed = state.get('permanently_failed_groups', [])

    # Extract actual failed groups (excluding those that succeeded after retry)
    actual_failures = []

    # Expected number of parts for each group
    expected_counts = {
        "Fundamental": (5, len(fundamental)),
        "Technical": (3, len(technical)),
        "Sentiment": (3, len(sentiment)),
        "Macro": (4, len(macro))
    }

    # Detect failures
    for group_name, (expected, actual) in expected_counts.items():
        if actual < expected:
            print(f"⚠️  {group_name} group: {actual}/{expected} parts only completed")
            actual_failures.append(group_name)
        else:
            print(f"✓  {group_name} group: {actual}/{expected} parts complete")

    # Combine results (Order: Fundamental → Technical → Sentiment → Macro)
    combined = fundamental + technical + sentiment + macro

    print(f"\nTotal {len(combined)}parts integrated")

    # Add warning section for failed groups
    if actual_failures or permanently_failed:
        warning_parts = []
        warning_parts.append("## ⚠️ Partial Analysis Results Notice\n")

        # Display groups that succeeded after retry
        if retried_and_succeeded:
            retried_names = [g.replace(" (retry successful)", "") for g in retried_and_succeeded]
            warning_parts.append(f"**Groups successfully retried:** {', '.join(retried_names)}\n")

        # Display permanently failed groups
        if permanently_failed:
            warning_parts.append(f"**Incomplete groups:** {', '.join(permanently_failed)}\n")
            warning_parts.append("\nThe provided results are partial analysis based on available data.\n")

        warning_section = "\n".join(warning_parts)
        combined.insert(0, warning_section)

    print("=" * 80)

    return {
        "report_sections": combined,
        "failed_groups": permanently_failed  # Only permanently failed groups are passed as failed_groups
    }


@monitor_node(node_name="outlook_analysis", graph_name="main")
def outlook_analysis(state: AgentState) -> dict:
    """
    Part 16: Comprehensive Analysis and Forecast
    Integrates all previous analysis results to perform final investment judgment.
    """
    # API Rate Limit consideration: Wait before starting Part 16
    print(f"⏱️  Before starting Part 16 {PART16_DELAY}s waiting...")
    time.sleep(PART16_DELAY)

    print("=" * 80)
    print("Part 16: Comprehensive Analysis and Forecast Starting")
    print("=" * 80)

    target_stock = state['target_stock']
    current_date = state.get('current_date')  # Extract current date
    report_sections = state.get('report_sections', [])
    failed_groups = state.get('failed_groups', [])

    # Include all previous analysis results as context
    parts_full_content = "\n\n".join([
        f"### PART {i+1} Analysis Result:\n{section}"
        for i, section in enumerate(report_sections)
    ])

    # Generate comprehensive prompt specifically for Part 16
    comprehensive_prompt = f"""
PART XVI: Starting comprehensive analysis and forecast.

**Important**: Below are all analysis results from PART I ~ PART XV completed so far.
Please synthesize this information to perform final investment judgment and forecast.

---
## Previous Analysis Results (Complete)

{parts_full_content}

---

Now, strictly adhering to the current stage (PART XVI) methodology:
1. Systematically integrate all analysis results
2. Forecast stock future trends and prices
3. Evaluate risk factors and uncertainties
4. Specific trading strategies and investment recommendations

Please derive the above.

* Target Stock for Analysis: {target_stock}

{get_part_prompt(16)}
"""

    if failed_groups:
        comprehensive_prompt += f"""

**Warning**: The following groups have incomplete analysis: {', '.join(failed_groups)}
Please specify uncertainties taking this into consideration.
"""

    # Call LLM (Part 16 does not require tools, only synthesis from existing data)
    messages = [
        SystemMessage(content=get_core_system_prompt(current_date)),
        HumanMessage(content=comprehensive_prompt)
    ]

    print("--- (16/16) Part 16: Calling LLM ---")

    try:
        # Use string-returning chain (no tools needed for synthesis)
        analysis_result = model_str.invoke(messages)  # Returns string directly

        # Output AI response
        print(f"\n{'='*80}")
        print("Part 16 - Comprehensive Analysis Response")
        print(f"{'='*80}")
        print(f"Response Length: {len(analysis_result)} chars")
        print("-" * 20 + " RAW CONTENT START " + "-" * 20)
        print(repr(analysis_result)) # analysis_result is already a string
        print("-" * 20 + " RAW CONTENT END " + "-" * 20)
        print(f"{'='*80}\n")

        print("--- (16/16) Part 16 Analysis Complete ---")
        print("=" * 80)

        return {
            "report_sections": [clean_trailing_spaces(analysis_result)],
            "current_part": 17  # End signal
        }

    except Exception as e:
        # Fallback handling if Part 16 comprehensive analysis fails
        print(f"⚠️  Part 16 comprehensive analysis failed: {e}")
        print("--- Proceeding with incomplete report (Parts 1-15 only) ---")
        print("=" * 80)

        # If Part 16 fails, do not add an error page to the PDF.
        # Instead, generate the report with existing Parts 1-15.
        # However, add to 'permanently_failed_groups' to include a warning in the email body.

        return {
            "permanently_failed_groups": ["Part16_Synthesis"],
            "current_part": 17  # End signal
        }

@monitor_node(node_name="unify_report", graph_name="main")
def unify_report(state: AgentState) -> dict:
    """
    Report Format Unification Node

    Unifies format, style, and structure of all 16 sections using gemini-2.5-pro.
    Ensures consistent markdown format, professional tone, and structural patterns.

    Process:
    1. Extracts all completed report sections (Parts 1-16)
    2. Sends to gemini-2.5-pro with unification prompt
    3. Returns unified report sections in state
    4. Graceful fallback to preserve original sections if failed

    Args:
        state (AgentState): Current workflow state containing report_sections

    Returns:
        dict: Updated state with unified_report field
              Returns empty dict {} if failed to preserve original sections
    """
    # API Rate Limit consideration: Wait before starting report format unification
    print(f"⏱️  Before starting report format unification {UNIFY_REPORT_DELAY}s waiting...")
    time.sleep(UNIFY_REPORT_DELAY)

    print("=" * 80)
    print("Starting Report Format Unification (using gemini-2.5-pro)")
    print("=" * 80)

    target_stock = state['target_stock']
    report_sections = state.get('report_sections', [])

    # Validation: Check if there are sections to unify
    if not report_sections or len(report_sections) == 0:
        print("⚠️  Warning: No report sections to unify. Proceeding with original.")
        return {}

    # Check model availability
    if model_pro is None:
        print("⚠️  Warning: gemini-2.5-pro model unavailable. Proceeding with original report.")
        return {}

    print(f"Total {len(report_sections)} sections will be unified.")
    print("✓ gemini-2.5-pro model ready")

    # Prepare unification prompt
    combined_sections = "\n\n---PART_SEPARATOR---\n\n".join([
        f"## SECTION {i+1}\n{section}"
        for i, section in enumerate(report_sections)
    ])

    unification_prompt = f"""You are a professional editor of financial analysis reports.
Below is a {len(report_sections)}-part analysis report on {target_stock} stock.

**Your Mission:**
1. Unify markdown format consistently across all sections
2. Adjust writing style and tone professionally and consistently
3. Unify structural patterns (tables, lists, emphasis, etc.)

**Specific Tasks:**

### 1. Unify Markdown Heading Levels
- Each PART starts with `## PART I`, `## PART II`, etc. (level 2)
- Major sections within each PART use `###` (level 3)
- Detailed items use `####` (level 4)
- Never use `#` (level 1) - reserved for PDF title

### 2. Unify Writing Style
- Use formal tone consistently across all sections
- Maintain professional and objective tone
- Remove excessive emotional expressions

### 3. Unify Structural Elements
- Tables: Use markdown table format for all tables, bold header rows
- Lists: Use `1. 2. 3.` for ordered lists, `*` for unordered lists
- Emphasis: Use `**bold**` for important terms, plain text for supplementary explanations
- Code/Numbers: Organize financial data in table format

### 4. Content Preservation Principle
- **Important**: Never change the analysis content itself
- Preserve data, numbers, and analysis results as-is
- Only adjust format and writing style

**Input Report:**

{combined_sections}

**Output Format:**
Separate each section with `---PART_SEPARATOR---`.
Each section must be written in unified format.

Now unify the format and writing style of the above report and output it."""

    # Call gemini-2.5-pro to perform unification
    try:
        from langchain_core.messages import HumanMessage

        print("Calling gemini-2.5-pro...")
        # Use string-returning chain (automatically handles list/string)
        unified_content = model_pro_str.invoke([HumanMessage(content=unification_prompt)])

        # Output AI response
        print(f"\n{'='*80}")
        print("Report Unification - AI Response")
        print(f"{'='*80}")
        print(f"Unified Content Length: {len(unified_content)} chars")
        print(f"\nFull Content:")
        print(repr(unified_content))
        print(f"{'='*80}\n")

        # Split unified sections
        unified_sections = unified_content.split("---PART_SEPARATOR---")
        unified_sections = [clean_trailing_spaces(s.strip()) for s in unified_sections if s.strip()]

        # Validation: Check section count
        if len(unified_sections) != len(report_sections):
            print(f"⚠️  Warning: Unified section count({len(unified_sections)}) differs from original({len(report_sections)}).")
            print("Proceeding with original report.")
            return {}

        print(f"✓ Report format unification complete: {len(unified_sections)} sections")
        print("=" * 80)

        # Return unified sections (overwrite unified_report)
        return {
            "unified_report": unified_sections
        }

    except Exception as e:
        print(f"❌ Report unification failed: {e}")
        print("Proceeding with original report.")
        import traceback
        traceback.print_exc()
        return {}

@monitor_node(node_name="translate_report", graph_name="main")
def translate_report(state: AgentState) -> dict:
    """
    Report Translation Node

    Translates all report sections to Korean using gemini-2.5-pro.
    Maintains markdown structure and formatting from unified_report.

    Process:
    1. Extracts sections to translate (unified_report if available, else report_sections)
    2. Sends to gemini-2.5-pro with translation prompt
    3. Returns Korean sections in state
    4. Graceful fallback to empty list if failed (triggers English-only PDF)

    Args:
        state (AgentState): Current workflow state containing report_sections or unified_report

    Returns:
        dict: Updated state with korean_report field
              Returns empty dict {} if failed to trigger English-only fallback
    """
    print("\n" + "=" * 80)
    print("[Translate Report] Starting Korean translation...")
    print("=" * 80)

    target_stock = state['target_stock']
    current_date = state['current_date']

    # Priority: unified_report if exists, else report_sections
    unified_report = state.get('unified_report', [])
    report_sections = state.get('report_sections', [])

    # Determine source for translation
    source_sections = unified_report if unified_report else report_sections

    if not source_sections or len(source_sections) == 0:
        print("⚠️  Warning: No report sections to translate. Proceeding with English-only.")
        return {}

    if unified_report:
        print(f"Translating from unified_report: {len(source_sections)} sections")
    else:
        print(f"Translating from report_sections: {len(source_sections)} sections")

    # Verify gemini-2.5-pro availability
    if model_pro is None:
        print("⚠️  Warning: gemini-2.5-pro model unavailable. Proceeding with English-only report.")
        return {}

    print(f"Total {len(source_sections)} sections will be translated to Korean.")
    print("✓ gemini-2.5-pro model ready for translation")

    try:
        from langchain_core.messages import HumanMessage

        # Combine sections with separator for batch translation
        combined_sections = "\n\n---PART_SEPARATOR---\n\n".join([
            f"## Part {i+1}\n{section}"
            for i, section in enumerate(source_sections)
        ])

        translation_prompt = f"""You are a professional financial report translator specializing in English-to-Korean translation.

Below is a {len(source_sections)}-part stock analysis report in English on {target_stock}.

**Your Mission:**
1. Translate ALL sections to natural, professional Korean
2. Preserve ALL markdown formatting exactly (headings, tables, lists, bold, etc.)
3. Maintain technical accuracy for financial terms
4. Use formal business Korean tone (formal ending)

**Critical Requirements:**

### 1. Preserve Markdown Structure
- Keep ALL heading levels unchanged (`##`, `###`, `####`)
- Keep table formatting intact (markdown table syntax)
- Keep list formatting (numbered `1.`, bulleted `*`)
- Keep emphasis markers (`**bold**`, `*italic*`)
- Keep code blocks and numbers unchanged

### 2. Financial Terminology Standards
- Use standard Korean financial terms from Korea Exchange (KRX)
- Examples:
  - "Market Cap" → "시가총액"
  - "P/E Ratio" → "주가수익비율 (PER)"
  - "Revenue" → "매출액"
  - "Operating Margin" → "영업이익률"
  - "ROE" → "자기자본이익률 (ROE)"
  - "Debt Ratio" → "부채비율"

### 3. Tone and Style
- Use formal business Korean (formal ending)
- Maintain professional and objective tone
- Keep sentence structure clear and concise
- Preserve emphasis and importance from original

### 4. Content Preservation
- **Critical**: Do NOT change numbers, dates, or data
- Do NOT add explanations or interpretations
- Do NOT omit any parts or subsections
- Only translate text, preserve structure and data

**Input Report (English):**

{combined_sections}

**Output Format:**
Separate each translated part with `---PART_SEPARATOR---`.
Each Part MUST maintain exact markdown structure from input.

Now translate the above report to Korean following all requirements."""

        print("Calling gemini-2.5-pro for Korean translation...")
        # Use string-returning chain (automatically handles list/string)
        korean_content = model_pro_str.invoke([HumanMessage(content=translation_prompt)])

        # Output AI response (for debugging)
        print(f"\n{'='*80}")
        print("Korean Translation - AI Response")
        print(f"{'='*80}")
        print(f"Translated Content Length: {len(korean_content)} chars")
        print(f"\nFirst 500 chars preview:")
        print(repr(korean_content[:500]))
        print(f"{'='*80}\n")

        # Split sections
        korean_sections = korean_content.split("---PART_SEPARATOR---")
        korean_sections = [clean_trailing_spaces(s.strip()) for s in korean_sections if s.strip()]

        # Validation: section count must match
        if len(korean_sections) != len(source_sections):
            print(f"⚠️  Warning: Korean section count({len(korean_sections)}) differs from original({len(source_sections)}).")
            print("Proceeding with English-only report.")
            return {}

        print(f"✓ Korean translation complete: {len(korean_sections)} sections")
        print("=" * 80)

        return {
            "korean_report": korean_sections
        }

    except Exception as e:
        print(f"❌ Korean translation failed: {e}")
        print("Proceeding with English-only report.")
        import traceback
        traceback.print_exc()
        return {}

# --- 2. Build the StateGraph ---

workflow_memory = MemorySaver()
workflow = StateGraph(AgentState)

# The dispatch_parallel_groups node internally executes 4 subgraphs in parallel.

# 1. Add nodes
workflow.add_node("dispatch_parallel_groups", dispatch_parallel_groups)
workflow.add_node("combine_results", combine_results)
workflow.add_node("outlook_analysis", outlook_analysis)
workflow.add_node("unify_report", unify_report)  # Report format unification node
workflow.add_node("translate_report", translate_report)  # Korean translation node
workflow.add_node("generate_and_send_report", generate_and_send_report)

# 2. Connect edges
# START → Parallel execution → Combine results → Part 16 Comprehensive → Format unification → Translate → Generate report → END
workflow.set_entry_point("dispatch_parallel_groups")
workflow.add_edge("dispatch_parallel_groups", "combine_results")
workflow.add_edge("combine_results", "outlook_analysis")
workflow.add_edge("outlook_analysis", "unify_report")  # Format unification after Part 16
workflow.add_edge("unify_report", "translate_report")  # Korean translation after unification
workflow.add_edge("translate_report", "generate_and_send_report")  # Generate report after translation
workflow.add_edge("generate_and_send_report", END)

# --- 3. Compile the Graph (App "assembly complete") ---
app = workflow.compile(checkpointer=workflow_memory)
