
# intent_classifier_general.py
def query_llm_classification(user_input, existing_nodes):
    context = "\n".join([
        f"[{i+1}] ({n.parent or 'ROOT'}) {n.slot}: {n.value}"
        for i, n in enumerate(existing_nodes)
    ])
    
    prompt = f"""
You are a task memory classifier.

Existing Nodes:
{context or "None"}

User Input:
"{user_input}"

Please classify the user input using the following fields:

- intent_type: one of ["new", "update", "check"]
    - "new": This is the first time this slot appears in memory.
    - "update": This slot already exists, or the user is changing or reverting its value.
    - "check": The user is reflecting on, verifying, or asking about an existing slot. No change is made.

- For "update" intent:
    - Do NOT set dependency_nodes unless the update itself logically depends on other slot values.
    - Typically, updates to a known slot (e.g., changing or reverting the departure date) should have an empty dependency list.
    - You may leave parent_node blank or null — the system will find the existing slot to update.

- subtask_title: concise, value-agnostic task name like "set destination", "verify start location", etc.

- parent_node: 
    - use null if this is the root task
    - otherwise, use the exact subtask_title (string) of the most relevant existing node

- dependency_nodes: 
    - list all existing slots this task logically depends on to execute correctly. Do not include the slot itself.
    - list the subtask_title (string) of any logically required prior tasks (do NOT use index or ID).
    - Do NOT use numeric indexes like [1, 2, 3]. Always refer to node titles.
    - A slot should only depend on other slots if its value cannot be determined without them.
    - If the user is directly assigning a value (e.g., a date or city), and the meaning is self-contained, then it does not depend on any other slot.
    - Only include dependency_nodes that belong to the same logical task thread.
    - Do not include actions or slots that were created in a different task context, especially if they involve different locations, dates, or purposes.
    - Treat each new travel plan, request, or intention with a distinct destination or date as a separate task tree unless the user clearly connects them.
    - You must not list any dependency_nodes that were created outside the parent_node's tree. Only include dependencies that belong to the same memory structure.

You must infer intent based on **language patterns**:
- If the user says "wasn’t I", "didn’t I", "was I supposed to", "did I say", "I thought" → classify as **"check"**
- If the user says "actually", "change", "go back", "revert", "instead" → classify as **"update"**
- If the slot hasn’t appeared in memory yet, classify as **"new"**

In addition, generate a one-sentence AI response to the user input, as if you were the assistant replying in natural language.

Respond in strict JSON format only, with the following fields:
- intent_type
- subtask_title
- parent_node
- dependency_nodes
- ai_response
"""

    return prompt

