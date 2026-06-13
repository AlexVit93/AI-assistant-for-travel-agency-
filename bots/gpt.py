import os
import httpx

from openai import AsyncOpenAI

from bots.prompt import HEAD_PROMPT

gpt = AsyncOpenAI(api_key=os.getenv("AI_KEY"),
                  http_client=httpx.AsyncClient())

dialogues = {}

async def get_assistant_response(user_id, user_message, custom_messages=None):
    if user_id not in dialogues:
        dialogues[user_id] = []
    
    if custom_messages is not None:
        messages = custom_messages
    else:
        dialogues[user_id].append({"role": "user", "content": user_message})
        messages = [{"role": "system", "content": HEAD_PROMPT}] + dialogues[user_id]
    
    response = await gpt.chat.completions.create(
        messages=messages,
        model="gpt-4o-mini"
    )
    response_text = response.choices[0].message.content
    dialogues[user_id].append({"role": "assistant", "content": response_text})
    return response_text
