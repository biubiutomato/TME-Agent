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
    "Help me schedule a trip based on the information I provide.",

    "destination: Set the destination to Seattle.",
    "start: I will depart from Chicago.",
    "date: I want to leave on June 10th.",

    "destination: Actually, make that San Francisco.",
    "date: Change the departure date to June 15th.",

    "destination: Sorry, go back to Seattle as originally planned.",
    "hotel: Find a hotel near downtown.",

    "start: By the way, wasn’t I departing from Boston?",
    "flight: Search for flights from Boston to San Francisco on June 10th.",

    "finalize: Can you generate a complete trip plan? What's my start, destination and start date?"
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
You are planning a trip for the user with the following fields: destination, start, hotel, flight.

Each round, your output should follow this format:
Thought: ...
Action: ...
Observation: ...

Current filled fields: {json.dumps(filled_fields)}
Scratchpad:
{chr(10).join(scratchpad)}

Latest user message: "{user_input}"
"""
    print(f"\n=== Round {step + 1} ===")
    print(f"📝 Prompt sent to GPT:\n{prompt}")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    reply = response.choices[0].message.content.strip()
    usage = response.usage
    print(f"🗣️ User: {user_input}")
    print(f"🤖 GPT Reply:\n{reply}")

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

    action_text = action_line.split(":", 1)[1].strip()

    if action_text.startswith("get("):
        filled_fields[field] = value
        token_tree[field].append((f"Round {step + 1}", value))

    elif action_text.startswith("update("):
        filled_fields[field] = value
        token_tree[field].append((f"Round {step + 1}", value))

    elif action_text.startswith("submit()"):
        scratchpad.append(f"Observation: Submitted plan: {filled_fields}")

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

with open("trip_react_results.json", "w") as f:
    json.dump(results, f, indent=2)

with open("trip_token_tree.json", "w") as f:
    json.dump(token_tree, f, indent=2)

with open("trip_token_usage.json", "w") as f:
    json.dump(token_usage, f, indent=2)

# ✅ print token tree 
print("\n====== Token Tree ======")
for field, changes in token_tree.items():
    print(f"- {field}:")
    for round_id, val in changes:
        print(f"  - {round_id}: {val}")

print("\n====== Token Usage ======")
for usage in token_usage:
    print(usage)


# ✅ Add hallucination detection (example keywords check)
final_output = memory.get("final_output", "").lower()
expected = {
    "destination": "seattle",
    "start": "chicago",
    "date": "june 15th"
}

print("\n===== HALLUCINATION CHECK =====")
for key, expected_value in expected.items():
    actual = final_output if key == "date" else memory.get(key, "").lower()
    if expected_value not in actual:
        print(f"❌ GPT hallucinated or forgot '{key}': expected '{expected_value}', got '{actual}'")
    else:
        print(f"✅ {key.title()} OK: {expected_value}")