import httpx
import json
from typing import Dict, Any
from backend.config import VERIFY_SSL

_shared_client = None

def get_shared_client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is None:
        # Long timeout for LLMs, verify=VERIFY_SSL for local certs if needed
        _shared_client = httpx.AsyncClient(verify=VERIFY_SSL, timeout=120.0)
    return _shared_client

def clean_and_parse_json(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    clean = text.strip()
    # Try raw load
    try:
        parsed = json.loads(clean)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    # Try markdown json block
    if '```json' in clean:
        try:
            candidate = clean.split('```json')[1].split('```')[0].strip()
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    elif '```' in clean:
        try:
            candidate = clean.split('```')[1].split('```')[0].strip()
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    # Search backwards for '{' to find the last valid JSON object block
    text_len = len(clean)
    for i in range(text_len - 1, -1, -1):
        if clean[i] == '{':
            for j in range(text_len - 1, i, -1):
                if clean[j] == '}':
                    candidate = clean[i:j+1]
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        continue
    return {}

async def call_gemini(api_key: str, model: str, system_instruction: str, prompt: str) -> str:
    # Gemini 1.5/2.0/3.5 API endpoint
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2
        }
    }
    client = get_shared_client()
    response = await client.post(url, headers=headers, json=payload, timeout=30.0)
    if response.status_code != 200:
        print(f"[AI Gemini Error] Status: {response.status_code}, Response: {response.text}")
        raise Exception(f"Gemini API Error ({response.status_code}): {response.text}")
    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]

async def call_openai(api_key: str, model: str, system_instruction: str, prompt: str) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json"
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ]
    }
    client = get_shared_client()
    response = await client.post(url, headers=headers, json=payload, timeout=30.0)
    if response.status_code != 200:
        print(f"[AI OpenAI Error] Status: {response.status_code}, Response: {response.text}")
        raise Exception(f"OpenAI API Error ({response.status_code}): {response.text}")
    data = response.json()
    return data["choices"][0]["message"]["content"]

async def call_anthropic(api_key: str, model: str, system_instruction: str, prompt: str) -> str:
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "content-type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    if api_key:
        headers["x-api-key"] = api_key
    payload = {
        "model": model,
        "max_tokens": 1500,
        "temperature": 0.2,
        "system": system_instruction,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    client = get_shared_client()
    response = await client.post(url, headers=headers, json=payload, timeout=30.0)
    if response.status_code != 200:
        print(f"[AI Anthropic Error] Status: {response.status_code}, Response: {response.text}")
        raise Exception(f"Anthropic API Error ({response.status_code}): {response.text}")
    data = response.json()
    return data["content"][0]["text"]

async def call_custom(api_key: str, base_url: str, model: str, system_instruction: str, prompt: str) -> str:
    if not base_url:
        raise Exception("Custom Base URL is required for Custom provider")
    clean_url = base_url.rstrip('/')
    if "localhost" in clean_url:
        clean_url = clean_url.replace("localhost", "127.0.0.1")
    url = f"{clean_url}/chat/completions"
    headers = {
        "Content-Type": "application/json"
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }
    print(f"[AI Custom Request] URL: {url}, Model: {model}")
    client = get_shared_client()
    response = await client.post(url, headers=headers, json=payload, timeout=120.0)
    if response.status_code != 200:
        print(f"[AI Custom Error] Status: {response.status_code}, Response: {response.text}")
        raise Exception(f"Custom API Error ({response.status_code}): {response.text}")
    
    try:
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as json_err:
        text = response.text
        if "data:" in text:
            full_content = ""
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        continue
                    try:
                        chunk_data = json.loads(data_str)
                        choices = chunk_data.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content", "")
                            if not content:
                                message = choices[0].get("message", {})
                                content = message.get("content", "")
                            full_content += content
                    except Exception:
                        pass
                if full_content:
                    return full_content
            
            print(f"[AI Custom Parse Error] Response was not valid JSON/SSE: {text[:500]}")
            raise json_err

async def call_semburat_gateway(base_url: str, model: str, system_instruction: str, prompt: str) -> str:
    """
    Adapter to route LLM requests through the custom Semburat/Anthropic API Gateway.
    Handles both synchronous responses (local models) and polling (asynchronous remote proxy).
    """
    import asyncio
    
    if not base_url:
        raise Exception("Custom Base URL is required for Semburat Gateway")
        
    clean_url = base_url.rstrip('/')
    
    # Combine system instruction and user prompt as expected by the gateway
    full_prompt = f"{system_instruction}\n\nUser Prompt:\n{prompt}"
    
    payload = {
        "model": model,
        "prompt": full_prompt,
        "max_tokens": 4096
    }
    
    submit_url = f"{clean_url}?action=submit"
    print(f"[Semburat Gateway Submit] URL: {submit_url}, Model: {model}")
    
    client = get_shared_client()
    
    # 1. Submit Request
    response = await client.post(submit_url, json=payload, timeout=30.0)
    if response.status_code != 200:
        print(f"[Semburat Gateway Error] Submit Status: {response.status_code}, Response: {response.text}")
        raise Exception(f"Gateway submission failed ({response.status_code}): {response.text}")
    
    # Determine if it's async (returns JSON with session_id) or sync (returns raw text or custom JSON)
    try:
        data = response.json()
        session_id = data.get("session_id")
    except Exception:
        # If not JSON, it might be raw text return for sync local model
        return response.text
        
    # 2. If it returned a session_id, poll for completion
    if session_id:
        status_url = f"{clean_url}?action=status&id={session_id}"
        max_attempts = 60  # 3 minutes max (60 attempts * 3 seconds)
        print(f"[Semburat Gateway Async] Session: {session_id}. Polling...")
        
        for attempt in range(1, max_attempts + 1):
            await asyncio.sleep(3.0)  # Wait 3 seconds
            try:
                status_res = await client.get(status_url)
                if status_res.status_code != 200:
                    continue
                
                status_data = status_res.json()
            except Exception as poll_err:
                print(f"[Semburat Gateway Polling Error] Attempt {attempt}: {poll_err}")
                continue
            
            status = status_data.get("status")
            result = status_data.get("result")
            
            if status == "ready":
                return result  # Returns the generated AI text
            elif status == "failed":
                raise Exception(f"Generation failed on remote proxy: {result}")
            
            print(f"[Semburat Gateway Polling] Attempt {attempt}/{max_attempts}: Still processing...")
        
        # Timeout reached, clean up server-side files
        cleanup_url = f"{clean_url}?action=cleanup&id={session_id}"
        await client.delete(cleanup_url)
        raise Exception("Gateway request timed out waiting for AI response.")
        
    # If JSON was returned but no session_id, return the data itself (or extract result field if structured)
    return data.get("result", response.text)
