
# trim.py
import json

def build_slot_tree(nodes):
    parent_map = {}
    for n in nodes:
        parent = n.parent or "ROOT"
        if parent not in parent_map:
            parent_map[parent] = []
        parent_map[parent].append(n.slot)
    return parent_map

def is_descendant(target_slot, root_slot, parent_map):
    visited = set()
    queue = [root_slot]
    while queue:
        current = queue.pop(0)
        if current == target_slot:
            return True
        children = parent_map.get(current, [])
        queue.extend(children)
    return False

def filter_dependency_nodes(slot_title, parent_node, dependencies, all_nodes):
    # ⚠️ all_nodes may come from multiple trees (forest). Ensure correct parent mapping.
    parent_map = build_slot_tree(all_nodes)
    return [
        d for d in dependencies
        if is_descendant(d, parent_node, parent_map) or d == parent_node
    ]


def enforce_logical_dependencies(parsed, memory_nodes):
    """Post-process LLM prediction to ensure critical dependencies are enforced."""
    all_slots = [n.slot for n in memory_nodes]
    if parsed["subtask_title"] == "find hotel" or parsed["subtask_title"] == "set hotel":
        if "set destination" in all_slots and "set destination" not in parsed["dependency_nodes"]:
            parsed["dependency_nodes"].append("set destination")
    # Enforce rule: search flights → needs departure, destination, and date if they exist
    if parsed["subtask_title"] == "search flights":
        for required in ["set departure location", "set destination", "set departure date"]:
            if required in all_slots and required not in parsed["dependency_nodes"]:
                parsed["dependency_nodes"].append(required)
    return parsed

def infer_and_add_dependencies(new_node, existing_nodes):
    """
    Check if new_node shares slot/value with existing memory.
    If so, mark it as dependent and generate rationale.
    """
    shared_value = new_node.value
    shared_nodes = [n for n in existing_nodes if n.value == shared_value and n is not new_node]

    for other in shared_nodes:
        if new_node not in other.dependencies:
            new_node.dependencies.append(other)
            explanation = (
                f"Detected shared ingredient '{shared_value}' used in multiple tasks. "
                f"Added a dependency from <{new_node.slot}> to <{other.slot}>."
            )
            new_node.ai_response += "\n" + explanation


def extract_object_keywords(text: str) -> list:
    """Simple keyword extractor: returns likely object-level nouns from a slot name or user input."""
    import re
    text = text.lower()
    keywords = re.findall(r'\b(celery|shrimp|tomato|mushroom|onion|carrot|lettuce|egg|ingredient|soup|dumpling)\b', text)
    return list(set(keywords))


def detect_shared_object_dependency(user_input: str, current_slot: str, all_nodes: list) -> list:
    """
    Detect whether the current user input references shared objects from other tasks,
    such as 'celery', 'mushroom', etc. If so, return the list of slots where such objects appear
    as dependencies to be added for the current node.
    """
    shared_deps = []
    keywords = extract_object_keywords(user_input)
    for node in all_nodes:
        if any(k in node.slot.lower() for k in keywords):
            if node.slot != current_slot:  # Avoid self-loop
                shared_deps.append(node.slot)
    return shared_deps

def infer_dag_edges_from_llm(user_input: str, all_nodes: list, client=None) -> list:
    """
    Use LLM to infer which DAG edges (from→to) should be created based on user input.
    Returns a list of {from, to} edges.
    """
    if client is None:
        return []

    context = "\n".join(
        [f"- Slot: {n.slot}, under Task: {n.parent or 'ROOT'}" for n in all_nodes]
    )

    prompt = f"""
You are a task memory planner that builds DAGs between subtasks.

Below is the current memory:
{context}

Now the user says:
"{user_input}"

Your job is to infer whether this instruction semantically **reuses** or **replaces** any existing slot.

✅ If user input implies that one step should **replace** another 
(e.g., "use mushrooms instead of celery"), generate a DAG edge 
**from the new step to the one it replaces**.

✅ If user input depends on earlier slots (e.g., "also add tomatoes to the soup"),
create an edge from the current instruction to that earlier slot.

Return a list of directed edges in JSON format like:
[
  {{ "from": "<current step or new slot>", "to": "<existing slot being reused or replaced>" }}
]

If no dependencies or replacements exist, return [].
Only respond with valid JSON.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        content = response.choices[0].message.content.strip()
        print("🔥")
        print(content)
        print("🔥end====")

        if content.startswith("```json"):
            content = content.split("```json")[-1].split("```")[0].strip()

        return json.loads(content)
    except Exception as e:
        print("❌ Failed to parse DAG edge response:", e)
        return []