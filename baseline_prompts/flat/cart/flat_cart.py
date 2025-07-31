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
   "Add two iPhone cases (black and clear), a charger, and a MacBook stand to my cart.",
   "Remove the clear case and charger.",
   "Actually, keep the charger, and remove the black case instead.",
   "Now I’m not sure—what’s currently in my cart?",
   "Can you reset it to just the MacBook stand and charger?"
]


messages = []
results = []
token_tree = defaultdict(list)
token_usage = []

# Function to extract task_title from user input
def extract_task_title(user_input):
    task_title = None
    if '$' in user_input:
        task_title = user_input.split('$')[1]  # Extracting task title between $token@xxx$
    return task_title

def extract_real_user_input(user_input):
    real_user_input = None
    if '$' in user_input:
        real_user_input = user_input.split('$')[2] 
    return real_user_input

# Process each user input in a loop
for idx, user_input in enumerate(user_inputs):
    real_user_input = user_input
    messages.append({"role": "user", "content": real_user_input})

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

    # Store results for each round
    results.append({
        "round": idx + 1,
        "user_input": real_user_input,
        "gpt_reply": reply,
        "token_usage": token_summary
    })

    token_usage.append(token_summary)

    # Print the user input and GPT reply
    print(f"\n=== Round {idx+1} ===")
    print(f"User Input: {real_user_input}")
    print(f"GPT Reply: {reply}")
    print(f"Token usage: {token_summary}")

# Write the results to JSON files
with open("tet_form_filling_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

with open("tet_token_tree.json", "w", encoding="utf-8") as f:
    json.dump(token_tree, f, ensure_ascii=False, indent=2)

with open("tet_token_usage.json", "w", encoding="utf-8") as f:
    json.dump(token_usage, f, ensure_ascii=False, indent=2)

# Print token tree summary
print("\nToken Tree:")
for field, changes in token_tree.items():
    print(f"- {field}")
    for round_info, value in changes:
        print(f"  - {round_info}: {value}")

# Print token usage per round
print("\nToken Usage Per Round:")
for usage in token_usage:
    print(usage)
