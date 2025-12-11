"""
Qwen2.5-32B for complex tool calling on A100 40GB with vLLM
"""
import json
import os
import subprocess
from typing import Any

import aiohttp
import modal


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MODEL_NAME = os.getenv("HF_MODEL_ID", "Qwen/Qwen2.5-7B-Instruct-1M")  # Qwen2.5, NOT Qwen3
MODEL_REVISION = os.getenv("HF_MODEL_REVISION", "main")
GPU_TYPE = os.getenv("MODAL_GPU", "H100")
FAST_BOOT = os.getenv("FAST_BOOT", "true").lower() == "true"
HF_SECRET_NAME = os.getenv("HF_SECRET_NAME", "huggingface-token")

MINUTES = 60
VLLM_PORT = 8000
N_GPU = int(os.getenv("N_GPU", "1"))


# ---------------------------------------------------------------------------
# Volumes for caching
# ---------------------------------------------------------------------------
hf_cache_vol = modal.Volume.from_name("huggingface-cache", create_if_missing=True)
vllm_cache_vol = modal.Volume.from_name("vllm-cache", create_if_missing=True)


# ---------------------------------------------------------------------------
# Image with vLLM - V1 engine REQUIRED for tool calling
# Qwen2.5 uses built-in chat template, no need to download separately
# ---------------------------------------------------------------------------
vllm_image = (
    modal.Image.from_registry("nvidia/cuda:12.8.0-devel-ubuntu22.04", add_python="3.12")
    .entrypoint([])
    .uv_pip_install(
        "vllm==0.6.6",
        "huggingface-hub==0.36.0",
        "flashinfer-python==0.3.1",
    )
    .env({
        "HF_XET_HIGH_PERFORMANCE": "1",
        "VLLM_USE_V1": "1",  # REQUIRED for tool calling
    })
)


app = modal.App("qwen25-32b-tool-calling-vllm")


@app.function(
    image=vllm_image,
    gpu=f"{GPU_TYPE}:{N_GPU}",
    scaledown_window=15 * MINUTES,
    timeout=10 * MINUTES,
    secrets=[modal.Secret.from_name(HF_SECRET_NAME)],
    volumes={
        "/root/.cache/huggingface": hf_cache_vol,
        "/root/.cache/vllm": vllm_cache_vol,
    },
)
@modal.concurrent(max_inputs=32)
@modal.web_server(port=VLLM_PORT, startup_timeout=10 * MINUTES)
def serve():
    """
    Run vLLM OpenAI-compatible server with Qwen2.5-32B tool calling.
    Official docs: https://docs.vllm.ai/en/stable/features/tool_calling.html
    """
    import os
    
    # Ensure V1 engine is enabled (required for tool calling)
    os.environ["VLLM_USE_V1"] = "1"
    
    cmd = [
        "vllm",
        "serve",
        MODEL_NAME,
        "--host", "0.0.0.0",
        "--port", str(VLLM_PORT),
    ]
    
    # Tool calling flags for Qwen2.5
    # Qwen2.5 uses hermes parser and has built-in chat template
    cmd += [
        "--enable-auto-tool-choice",
        "--tool-call-parser", "hermes",  # Qwen2.5 works best with hermes
    ]
    
    # Memory optimization for A100 40GB with Qwen2.5-32B
    cmd += [
        "--max-model-len", "1010000",  # A100 40GB can handle this comfortably
        "--gpu-memory-utilization", "0.95",
    ]
    
    # Performance settings
    cmd += ["--enforce-eager" if FAST_BOOT else "--no-enforce-eager"]
    cmd += ["--tensor-parallel-size", str(N_GPU)]
    
    # Model alias for easier client access
    cmd += ["--served-model-name", MODEL_NAME, "qwen"]

    print("🚀 Starting Qwen2.5-32B-Instruct with vLLM")
    print("Command:", " ".join(cmd))
    print(f"Environment: VLLM_USE_V1={os.environ.get('VLLM_USE_V1')}")
    subprocess.Popen(" ".join(cmd), shell=True)


# ---------------------------------------------------------------------------
# Test entrypoint
# ---------------------------------------------------------------------------
@app.local_entrypoint()
async def test(test_timeout=10 * MINUTES, content=None):
    """Test Qwen2.5-32B with complex tool calling scenarios."""
    url = serve.get_web_url()
    
    messages = [
        {"role": "user", "content": content or "What's the weather in Tokyo and convert it to Fahrenheit?"}
    ]
    
    # Complex multi-tool example
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "City name"}
                    },
                    "required": ["location"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "convert_temperature",
                "description": "Convert temperature between units",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "number"},
                        "from_unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                        "to_unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
                    },
                    "required": ["value", "from_unit", "to_unit"]
                }
            }
        }
    ]
    
    async with aiohttp.ClientSession(base_url=url) as session:
        print(f"\n{'='*60}")
        print(f"Testing Qwen2.5-32B Tool Calling at {url}")
        print(f"{'='*60}\n")
        
        # Health check
        print("Running health check...")
        async with session.get("/health", timeout=test_timeout - 1 * MINUTES) as resp:
            assert resp.status == 200
            print("✅ Health check passed\n")
        
        # Tool calling request
        print(f"Query: {messages[0]['content']}\n")
        print(f"Available tools: {len(tools)}\n")
        
        await _send_request(session, "qwen", messages, tools)


async def _send_request(session, model, messages, tools):
    """Send chat completion with tool calling."""
    payload = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "stream": True
    }
    
    headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
    
    async with session.post("/v1/chat/completions", json=payload, headers=headers, timeout=60) as resp:
        resp.raise_for_status()
        
        print("Response:")
        async for raw in resp.content:
            line = raw.decode().strip()
            if not line or line == "data: [DONE]":
                continue
            
            if line.startswith("data: "):
                line = line[6:]
            
            try:
                chunk = json.loads(line)
                if chunk.get("object") == "chat.completion.chunk":
                    delta = chunk["choices"][0]["delta"]
                    
                    if "tool_calls" in delta:
                        for tc in delta["tool_calls"]:
                            func = tc.get("function", {})
                            print(f"\n🔧 Tool Call: {func.get('name')}")
                            print(f"   Arguments: {func.get('arguments')}")
                    elif "content" in delta and delta["content"]:
                        print(delta["content"], end="", flush=True)
            except:
                pass
        print("\n")
