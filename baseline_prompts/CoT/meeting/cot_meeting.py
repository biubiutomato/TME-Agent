import time
import json
from collections import defaultdict
from openai import OpenAI
import sys, os, json, argparse

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


# CoT template (insert CoT reasoning structure)
cot_template = """Let's think step by step.
1. Interpret the current user input: "{user_input}"
2. Retrieve relevant context from previous interactions.
3. Identify the intended action or update.
4. Modify the current state accordingly and respond with an updated result or summary."""

system_prompt = {
    "role": "system",
    "content": (
        "You are a helpful and intelligent assistant that supports users in completing multi-step tasks.\n"
        "In each interaction, reason step by step:\n"
        "1. Interpret the latest user input.\n"
        "2. Recall relevant information from previous steps.\n"
        "3. Update the task state accordingly.\n"
        "4. Respond clearly, reflecting the most up-to-date and consistent result.\n\n"
        "Your goal is to ensure continuity, handle corrections, and avoid contradictions across steps."
    )
}

messages = [system_prompt]
results = []
token_usage = []

# Process each user input in a loop
for idx, user_input in enumerate(user_inputs):
    formatted_prompt = cot_template.format(user_input=user_input)
    messages.append({"role": "user", "content": formatted_prompt})

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.3
    )

    reply = response.choices[0].message.content
    usage = response.usage

    messages.append({"role": "assistant", "content": reply})

    token_summary = {
        "round": idx + 1,
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens
    }

    results.append({
        "round": idx + 1,
        "user_input": user_input,
        "formatted_prompt": formatted_prompt,
        "gpt_reply": reply,
        "token_usage": token_summary
    })

    token_usage.append(token_summary)

    print(f"\n=== Round {idx+1} ===")
    print(f"User Input: {user_input}")
    print(f"GPT Reply:\n{reply}")
    print(f"Token usage: {token_summary}")

# Write results to files
with open("cot_trip_planning_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

with open("cot_token_usage.json", "w", encoding="utf-8") as f:
    json.dump(token_usage, f, ensure_ascii=False, indent=2)

print("\n✅ CoT Trip Planning Finished.")
