"""Chat with Emma by typing (no microphone, no Cartesia needed). Uses the same prompt and tools.

Run:  python scripts/chat_test.py      Type 'quit' to stop.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _http import request  # noqa: E402

from cramble import config  # noqa: E402
from cramble.prompt import GREETING, build_system_prompt  # noqa: E402
from cramble.restaurant import Restaurant  # noqa: E402
from cramble.storage import FailsafeLog, create_store  # noqa: E402
from cramble.tools import TOOL_SCHEMAS, AgentTools  # noqa: E402

TOOLS = [{"type": "function", "function": {
    "name": s["name"], "description": s["description"],
    "parameters": {"type": "object", "properties": s["properties"], "required": s["required"]}}}
    for s in TOOL_SCHEMAS]


def ask_llm(messages):
    status, data = request("https://api.groq.com/openai/v1/chat/completions",
                           headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
                           body={"model": config.GROQ_LLM_MODEL, "messages": messages, "tools": TOOLS,
                                 "temperature": 0.6})
    if status != 200:
        raise RuntimeError(f"Groq error {status}: {data}")
    return data["choices"][0]["message"]


async def main():
    if not config.GROQ_API_KEY:
        print("Add GROQ_API_KEY to your .env file first.")
        return
    restaurant = Restaurant(config.RESTAURANT_DATA_FILE)
    store = create_store()
    store.setup()
    tools = AgentTools(restaurant, store, FailsafeLog(config.DATA_DIR))
    prompt = build_system_prompt(restaurant, config.SYSTEM_PROMPT_FILE)
    messages = [{"role": "system", "content": prompt}, {"role": "assistant", "content": GREETING}]
    print(f"\n(Bookings save to: {store.name})\n\nEmma: {GREETING}")

    while True:
        try:
            text = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text.lower() in ("quit", "exit", "bye"):
            break
        if not text:
            continue
        messages.append({"role": "user", "content": text})
        for _ in range(5):  # allow a few tool calls in a row
            reply = ask_llm(messages)
            messages.append({k: v for k, v in reply.items() if k in ("role", "content", "tool_calls")})
            if not reply.get("tool_calls"):
                print(f"\nEmma: {reply.get('content', '')}")
                break
            for call in reply["tool_calls"]:
                args = json.loads(call["function"].get("arguments") or "{}")
                result = await tools.call(call["function"]["name"], args)
                print(f"   [tool {call['function']['name']} -> {json.dumps(result)}]")
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result)})


if __name__ == "__main__":
    asyncio.run(main())
