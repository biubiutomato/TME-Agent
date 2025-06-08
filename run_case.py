# run_case.py

import sys, os, json, argparse

# Ensure root directory is in import path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Import shared modules
from v2.TaskMemoryStructure import TaskMemoryTree, TaskNode
from v2.trim import (
    filter_dependency_nodes, enforce_logical_dependencies,
    detect_shared_object_dependency, infer_dag_edges_from_llm
)
from v2.input_splitter import decompose_user_input_with_llm
# from v2.intent_classifier import query_llm_classification
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY not found. Please set it in a .env file or export it.")
client = OpenAI(api_key=OPENAI_API_KEY)

def run_case(json_file_path):
    with open(json_file_path) as f:
        user_inputs = json.load(f)

    memory_forest = []

    def call_llm(prompt):
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content

    def parsedJson(content):
        try:
            if content.strip().startswith("```"):
                content = "\n".join(line for line in content.strip().splitlines() if not line.startswith("```") )
            return json.loads(content)
        except Exception as e:
            print("\n❌ Failed to parse JSON:", e)
            print("Raw content:", content)
            return {
                "intent_type": "error",
                "subtask_title": "",
                "parent_node": "",
                "dependency_nodes": []
            }

    def find_or_create_task_tree(task_title, forest):
        for tree in forest:
            if tree.root and task_title.lower() in tree.root.slot.lower():
                return tree
        new_tree = TaskMemoryTree()
        forest.append(new_tree)
        return new_tree

    def find_node_global(slot, forest):
        for t in forest:
            node = t.find_node_by_slot(slot)
            if node:
                return node
        return None

    def replace_slot_global(forest, old_slot, new_slot, new_value):
        for tree in forest:
            if tree.find_node_by_slot(old_slot):
                tree.replace_slot_and_propagate(old_slot, new_slot, new_value)

    def collect_all_nodes(forest):
        return [node for tree in forest for node in tree.nodes]

    for round, user_input in enumerate(user_inputs, start=1):
        print(f"\n[Round {round}] User: {user_input}")

        split = decompose_user_input_with_llm(user_input)
        task_title = list(split["task"].keys())[0]
        task_phrase = list(split["task"].values())[0]
        substeps = split["substeps"]

        tree = find_or_create_task_tree(task_title, memory_forest)
        all_nodes = collect_all_nodes(memory_forest)

        if not substeps:
            prompt = query_llm_classification(user_input, all_nodes)
            llm_response = call_llm(prompt)
            parsed = parsedJson(llm_response)
            parsed = enforce_logical_dependencies(parsed, all_nodes)

            shared = detect_shared_object_dependency(parsed["subtask_title"], parsed["subtask_title"], all_nodes)
            parsed["dependency_nodes"].extend(d for d in shared if d not in parsed["dependency_nodes"])

            edges = infer_dag_edges_from_llm(user_input, all_nodes, client)
            edge_handled = False
            replacement_done = False

            for edge in edges:
                if parsed.get("intent_type") == "update":
                    replace_slot_global(memory_forest, edge["to"], edge["from"], user_input)
                    replacement_done = True
                else:
                    from_node = find_node_global(edge["from"], memory_forest)
                    to_node = find_node_global(edge["to"], memory_forest)
                    if from_node and to_node and edge["to"] not in from_node.dependencies:
                        from_node.dependencies.append(edge["to"])
                        edge_handled = True

            if edge_handled or replacement_done:
                print("💬 LLM Answer (Direct):", parsed.get("ai_response", user_input))
                continue

            parsed["dependency_nodes"] = filter_dependency_nodes(
                parsed["subtask_title"], parsed["parent_node"],
                parsed["dependency_nodes"], all_nodes
            )

            if parsed["intent_type"] == "rollback":
                parsed["intent_type"] = "update"

            if parsed["intent_type"] == "new":
                node = TaskNode(
                    slot=parsed["subtask_title"],
                    value=user_input,
                    parent=parsed["parent_node"],
                    dependencies=parsed["dependency_nodes"],
                    user_response=user_input,
                    ai_response=parsed.get("ai_response", "")
                )
                tree.add_node(node)

            elif parsed["intent_type"] == "update":
                existing = find_node_global(parsed["subtask_title"], memory_forest)
                old_slot = parsed["subtask_title"]
                if not existing and parsed["parent_node"]:
                    old_slot = parsed["parent_node"]
                    existing = find_node_global(old_slot, memory_forest)
                if existing:
                    replace_slot_global(memory_forest, old_slot, parsed["subtask_title"], user_input)
                    continue

        else:
            tree.add_node(TaskNode(slot=task_title, value=task_phrase, parent=None, user_response=user_input))
            for sub in substeps:
                substep_title, substep_phrase = list(sub.items())[0]
                prompt = query_llm_classification(substep_phrase, all_nodes)
                llm_response = call_llm(prompt)
                parsed = parsedJson(llm_response)
                parsed = enforce_logical_dependencies(parsed, all_nodes)

                shared = detect_shared_object_dependency(substep_title, substep_title, all_nodes)
                parsed["dependency_nodes"].extend(d for d in shared if d not in parsed["dependency_nodes"])

                parsed["dependency_nodes"] = filter_dependency_nodes(
                    parsed["subtask_title"], parsed["parent_node"],
                    parsed["dependency_nodes"], all_nodes
                )

                node = TaskNode(
                    slot=substep_title, value=substep_phrase, parent=task_title,
                    dependencies=parsed["dependency_nodes"],
                    user_response=user_input,
                    ai_response=parsed.get("ai_response", "")
                )
                tree.add_node(node)

                parent_node = tree.find_node_by_slot(task_title)
                if parent_node and substep_title not in parent_node.dependencies:
                    parent_node.dependencies.append(substep_title)

        if parsed.get("intent_type") == "check":
            memory_context = "\n".join(
                f"- Slot: {n.slot} | Value: {n.value} | History: {n.history}" for n in all_nodes
            )
            check_prompt = f"""
You are a memory-aware assistant.

Here is the current memory:
{memory_context}

Now answer the user's question:
\"{user_input}\"

Respond based only on memory. If uncertain, say so.
""".strip()
            answer = call_llm(check_prompt)
            print("\n💬 LLM Answer (Memory-based):", answer)
        else:
            print("\n💬 LLM Answer (Direct):", parsed.get("ai_response", user_input))

    print("\n📦 Final Slot Nodes:")
    for tree in memory_forest:
        if tree.root:
            print(f"\n🌳 Task Tree Root: {tree.root.slot}")
            for n in tree.nodes:
                print(f"<{n.slot}: {n.value} | Parent: {n.parent or 'ROOT'} | Deps: {n.dependencies} | History: {n.history}>")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("case_file", help="Path to case JSON file (e.g., cases/travel_case.json)")
    parser.add_argument("--mode", choices=["general", "cart"], default="general", help="Classifier type")
    args = parser.parse_args()

    if args.mode == "cart":
        from v2.intent_classifier_specific.intent_classifier_cart import query_llm_classification
    else:
        from v2.intent_classifier_general import query_llm_classification

    run_case(args.case_file)


