import json
from collections import defaultdict
from openai import OpenAI
import sys, os, json, argparse

# ✅ GPT client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY not found. Please set it in a .env file or export it.")
client = OpenAI(api_key=OPENAI_API_KEY)

user_inputs = [
    "Schedule a team meeting on Thursday at 2 PM with Alice, Bob, and Carol.",
    "Carol can’t make it at 2 PM. Move it to 4 PM.",
    "Actually, Bob is only free before 3. Split it into two parts—Bob from 2 to 2:45, the rest at 4.",
    "On second thought, just make it a single 3 PM meeting with everyone.",
    "Why does it still show two sessions?"
]


messages = []
scratchpad = []
filled_fields = {}
token_tree = defaultdict(list)
results = []
token_usage = []

for step, user_input in enumerate(user_inputs):
    messages.append({"role": "user", "content": user_input})

    prompt = f"""You are a helpful assistant using the ReAct framework.
You are planning a task for the user with fields such as destination, start, date, hotel, or others depending on the task context.

Each round, your output should follow this format:
Thought: ...
Action: ...
Observation: ...

Current filled fields: {json.dumps(filled_fields)}
Scratchpad:
{chr(10).join(scratchpad)}

Latest user message: "{user_input}"
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    reply = response.choices[0].message.content.strip()
    usage = response.usage
    print(f"\n=== Round {step + 1} ===")
    print(f"User: {user_input}")
    print(reply)


    scratchpad.append(reply)
    messages.append({"role": "assistant", "content": reply})

    
    if ":" in user_input:
        raw_field, raw_value = user_input.split(":", 1)
        field = raw_field.strip().lower()
        value = raw_value.strip()
    else:
        field = None
        value = user_input.strip()


    action_line = next((l for l in reply.splitlines() if l.strip().lower().startswith("action:")), None)
    if not action_line or not field:
        continue

    action_text = action_line.split(":", 1)[1].strip().lower()

    if action_text.startswith("update(") or action_text.startswith("set("):
        filled_fields[field] = value
        token_tree[field].append((f"Round {step + 1}", value))
    elif action_text.startswith("remove("):
        filled_fields.pop(field, None)
        token_tree[field].append((f"Round {step + 1}", "[REMOVED]"))

    token_summary = {
        "round": step + 1,
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens
    }

    results.append({
        "round": step + 1,
        "user_input": user_input,
        "gpt_reply": reply,
        "filled_fields": dict(filled_fields),
        "token_usage": token_summary
    })

    token_usage.append(token_summary)

with open("react_results.json", "w") as f:
    json.dump(results, f, indent=2)

with open("react_token_tree.json", "w") as f:
    json.dump(token_tree, f, indent=2)

with open("react_token_usage.json", "w") as f:
    json.dump(token_usage, f, indent=2)

print("\n====== Final Slot Tree ======")
for field, history in token_tree.items():
    print(f"- {field}:")
    for round_id, val in history:
        print(f"  - {round_id}: {val}")