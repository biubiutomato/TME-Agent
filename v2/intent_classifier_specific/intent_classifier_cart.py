
# intent_classifier_cart.py

def query_llm_classification(user_input, existing_nodes):
    context = "\n".join([
        f"[{i+1}] ({n.parent or 'ROOT'}) {n.slot}: {n.value}"
        for i, n in enumerate(existing_nodes)
    ])
    
    prompt = f"""
You are a task memory classifier for a **shopping cart assistant**.

Each node in memory represents an **object-level slot** — e.g., "add object", "remove object".

User may refer to the same object again to add it or remove it, or replace it (remove it and add another)
You must classify user input as:

- "new": Adding a new object to the cart that has not appeared before.
- "update": 
    - Modifying an existing object (e.g., changing its color, quantity, brand, or description).
    - Replacing a previously added object with a different version.
    - You must preserve the **object identity** but update its configuration.
    - Removing all quantities object from the cart.
- "check": User is reflecting on or asking about an object that already exists.

You must infer intent based on **object identity** and **language patterns**.

Also return:
- subtask_title: value-agnostic, object-specific, title of the object.
- parent_node: always use "Cart Root" unless otherwise specified.
- dependency_nodes: empty nodes.
- ai_response: a one-sentence natural language reply as if from the assistant.

---

Current Cart Memory:
{context or "None"}

User Input:
"{user_input}"

Please respond in strict JSON format with the following fields:
- intent_type
- subtask_title
- parent_node
- dependency_nodes
- ai_response
"""

    return prompt

