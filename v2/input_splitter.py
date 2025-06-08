import os, json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def decompose_user_input_with_llm(user_input: str) -> dict:
    """
    Decompose a user's instruction into a task + object-centric substeps,
    each mapped to the corresponding phrase in the original input.
    """

    prompt = f"""
You are a general-purpose task decomposition assistant.

Given a user instruction, output a structured breakdown consisting of:
- a high-level task
- optionally, object-level substeps (if the instruction contains multiple objects or object-action pairs)

### Rules:
1. If the instruction contains multiple objects or parameters (e.g., "chop tomatoes and peel shrimp"), decompose them into substeps.
2. If the instruction includes multiple actions applied to the **same object** (e.g., "wash and chop celery"), group them into **one substep**, e.g., "prepare celery".
3. If the instruction is not a task (e.g., a question, reflection, or correction), just return the entire input under `"task"`, and leave `"substeps"` empty.

### Output format (strict JSON):
{{
  "task": {{
    "<task title>": "<original phrase>"
  }},
  "substeps": [
    {{
      "<substep title>": "<original phrase>"
    }}
  ]
}}

Instruction: "{user_input}"
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    print("********")
    print(user_input)
    print("^^^^^^^^")
    try:
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"):
            lines = content.splitlines()
            content = "\n".join(line for line in lines if not line.strip().startswith("```"))

        return json.loads(content)
    except Exception as e:
        print("⚠️ Failed to parse LLM output:", e)
        print("Raw content:", content)
        return {"task": {}, "substeps": []}
