import json
import re
import requests
from typing import Any

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b"

SYSTEM_PROMPT = """You are an expert AI game master for a life simulation engine called LifeOS.
The user will provide a paragraph describing their current real-life chaos, stress, tasks, and problems.
Your job is to convert their text into a strict JSON scenario format.

The JSON MUST have the following structure exactly:
{
  "name": "custom_chaos",
  "display_name": "Custom User Scenario",
  "profile": {
    "name": "User",
    "role": "Custom",
    "age": 25,
    "stress": <float 0.0 to 1.0>,
    "energy": <float 0.0 to 1.0>,
    "money": <float representing bank balance, can be negative>,
    "relationship": <float 0.0 to 1.0>,
    "sleep_hours": <float 0 to 10>
  },
  "tasks": [
    {
      "id": "t1",
      "title": "<task name>",
      "deadline_hours": <int hours until due>,
      "priority": <int 1 to 5>,
      "remaining_effort": <float hours of work needed>,
      "status": "todo"
    }
  ],
  "events": [
    {
      "timestep": <int hours into the future, e.g., 4>,
      "event_type": "custom_event",
      "description": "<what might happen based on their input>",
      "impact": {
        "stress": <float change, e.g. 0.1 or -0.1>,
        "energy": <float change>
      }
    }
  ]
}

CRITICAL: Extract at least 2-3 tasks.
CRITICAL: Generate 3-4 HIGHLY SPECIFIC chaotic events (e.g., "Landlord calls for rent", "Hunger cramps from skipping breakfast"). Do NOT output generic events.
Output ONLY the raw JSON. Do not include markdown code blocks.
"""

def generate_scenario_from_text(user_input: str) -> dict[str, Any]:
    prompt = f"User's current situation: {user_input}\n\nGenerate the JSON scenario now:"
    
    payload = {
        "model": MODEL_NAME,
        "system": SYSTEM_PROMPT,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=300)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to connect to local Ollama instance: {e}")
        
    result_text = response.json().get("response", "")
    
    # Robust JSON extraction to strip <think> blocks or extra chat text
    match = re.search(r'(\{[\s\S]*\})', result_text)
    if match:
        result_text = match.group(1)
        
    try:
        scenario_data = json.loads(result_text)
        return scenario_data
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse Ollama output as JSON. Output was:\n{result_text}\nError: {e}")

def generate_actionable_report(user_text: str, top_actions: list[str]) -> str:
    """Generate a final 3-step survival guide based on the simulated actions."""
    prompt = f"""You are an AI survival guide. Based on the user's situation and the agent's simulated actions, give a 3-step actionable advice list. Keep it very short, punchy, and actionable.

User's Chaos: "{user_text}"
Agent's Top Actions Taken: {', '.join(top_actions)}

Format your output as exactly 3 bullet points. No intro, no outro."""
    
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 150
        }
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        
        result_text = response.json().get("response", "")
        # Remove <think> blocks if present
        result_text = re.sub(r'<think>.*?</think>', '', result_text, flags=re.DOTALL).strip()
        return result_text
    except Exception as e:
        return f"Error generating report: {e}"
