
import json
from openai import OpenAI
import sys, os, json, argparse

# ✅ GPT client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY not found. Please set it in a .env file or export it.")
client = OpenAI(api_key=OPENAI_API_KEY)

user_inputs = [
    "To make soup, wash and chop celery.",
    "To make dumplings, chop tomatoes and peel & chop shrimp.",
    "Also use celery in dumplings.",
    "Wait! There's no celery in the refrigerator at all. Let's all use mushrooms instead.",
    "Can you list all ingredients used in the soup?",
    "Did I ever say to remove celery from the dumplings?",
    "I think celery was never part of the soup. Can you double-check?"
]

messages = []
scratchpad = []
context = ""
results = []

for step, user_input in enumerate(user_inputs):
    print(f"\n=== Round {step + 1} ===")
    context += f"User: {user_input}\n"
    
    prompt = f"""You are a helpful cooking assistant using the ReAct reasoning framework.
You are helping the user manage two dishes: soup and dumplings.

Your goal is to respond step-by-step using the following format:
Thought: ...
Action: ...
Observation: ...

Use the user history and your previous assistant replies to determine what ingredients have been added or removed.

Context so far:
{context}

Scratchpad:
{chr(10).join(scratchpad)}
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    reply = response.choices[0].message.content.strip()
    print(f"User: {user_input}")
    print(reply)

    context += f"Assistant: {reply}\n"
    scratchpad.append(reply)

    results.append({
        "round": step + 1,
        "user_input": user_input,
        "gpt_reply": reply,
        "context": context
    })

with open("cooking_react_aligned_results.json", "w") as f:
    json.dump(results, f, indent=2)
