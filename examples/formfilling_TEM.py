# SPDX‑License‑Identifier: Polyform‑Noncommercial‑1.0.0
import os
import time
import json
from dotenv import load_dotenv
from collections import defaultdict
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY not found. Please set it in a .env file or export it.")

client = OpenAI(
  api_key=OPENAI_API_KEY
)

model_name = "gpt-3.5-turbo"

class TETNode:
    def __init__(self, name, parent=None, dependencies=None):
        self.name = name
        self.parent = parent
        self.children = []
        self.dependencies = dependencies or []
        self.context_history = []

    def to_dict(self):
        return {
            "name": self.name,
            "parent": self.parent,
            "children": self.children,
            "context_history": self.context_history,
            "dependencies": self.dependencies
        }

class TETManager:
    def __init__(self):
        self.node_map = {}

    def add_node(self, name, parent=None):
        node = TETNode(name, parent=parent)
        self.node_map[name] = node
        if parent and parent in self.node_map:
            self.node_map[parent].children.append(name)

    def update_or_add_node(self, name, user_input=None, parent=None, dependencies=None):
        if name in self.node_map and self.node_map.get(name):
            node = self.node_map.get(name)
            node.context_history.append({"role": "user", "content": user_input})
        else:
            self.add_node(name, parent)
            node = self.node_map.get(name)
            node.context_history.append({"role": "user", "content": user_input})

        # Handle dependencies if provided
        if dependencies:
            node = self.node_map.get(name)
            if node:
                node.dependencies = dependencies

    def updateGptReply(self, name, gpt_reply):
        if name in self.node_map: 
            node = self.node_map.get(name)
            if node:
                node.context_history.append({"role": "assistant", "content": gpt_reply})


    def get_by_name(self, name):
        if not name:
            return None
        node = self.node_map.get(name)
        if not node:
            print(f"❌ get_by_name: Node '{name}' not found in node_map.")
            return None
        return node

    def extract_parentAndDependencyPrompt(self, node, seen, extract_prompt):
        if not node:
            return
        context_nodes = []
        current_node = node
        while node:
            if node.name and node.name not in seen:
                context_nodes.insert(0, node)
                seen.add(node.name)
            print(f"\nCurrent node: {node.name}, parent: {node.parent}")
            node = self.get_by_name(node.parent) if node.parent else None
        for n in context_nodes:
            if n != current_node and n.context_history:
                extract_prompt.extend(n.context_history)
        if current_node:
            for dep in current_node.dependencies:
                print(f"\n*************************")
                print(f"dep: {dep}")
                if dep not in seen:
                    dep_node = self.get_by_name(dep)
                    if dep_node:
                        self.extract_parentAndDependencyPrompt(dep_node, seen, extract_prompt)
                        seen.add(dep)
            extract_prompt.extend(current_node.context_history)

    def extract_prompt_with_parents(self, name, current_user_input):
        extract_prompt = []
        seen = set()
        current_node = self.get_by_name(name)
        if current_node:
            print(f"\nextract_prompt_with_parents, current_node = {current_node.name}")
            self.extract_parentAndDependencyPrompt(current_node, seen, extract_prompt)
            # extract_prompt.extend(current_node.context_history)
        return extract_prompt

# ========== Test Runner ==========

user_inputs = [
    "$token@fill$Help me fill out a form, I will provide some of my information to you.",
    "$token@name$My name is John Doe.",
    "$token@email$My email is john@example.com.",
    "$token@address$My address is Market Street, San Francisco.",
    "$token@name$Sorry, to correct, my name is John Smith.",
    "$token@submit$Help to repeat my information, Then submit."
]

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

TET = TETManager()
token_usage = []

# Iterate through the user inputs and process them
for idx, user_input in enumerate(user_inputs):
    task_title = extract_task_title(user_input)  # Extract task title
    real_user_input = extract_real_user_input(user_input)  # Extract real user input

    # Iterate through the fields and update them
    if task_title == "token@fill":
        TET.update_or_add_node(task_title, user_input=real_user_input, parent=None)
    fields = ["token@name", "token@email", "token@address"]
    if task_title in fields:
        TET.update_or_add_node(task_title, user_input=real_user_input, parent="token@fill")
    # Update 'submit' node to depend on the fields name, email, and address
    if task_title == "token@submit":
        TET.update_or_add_node(task_title, user_input=real_user_input, parent="token@fill",dependencies=["token@name", "token@email", "token@address"])

    messages = []
    previousPrompt = TET.extract_prompt_with_parents(task_title, real_user_input) or []
    print(f"previousPrompt: {previousPrompt}")
    messages.extend(previousPrompt)
    # Extract context and construct prompt for GPT
    print(f"\n~~~~ Round {idx+1} ~~~~~~")
    print(f"messages: {messages}")

    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=0.2
    )

    reply = response.choices[0].message.content
    usage = response.usage

    # update gpt_reply
    TET.updateGptReply(task_title, reply)

    # Record token usage
    token_usage.append({
        "round": idx + 1,
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens
    })

    # Print status of the current round
    print(f"\n=== Round {idx+1} ===")
    print(f"User input: {messages}")
    print(f"GPT Reply: {reply}")
    print(f"Token usage: {usage}")

# Print token usage summary
print("\nToken Usage Summary:")
for item in token_usage:
    print(item)
