import asyncio
import time

import httpx

API_BASE = "http://127.0.0.1:8000"


async def run_benchmark():
    print("Starting smart stadium copilot benchmark...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Fetch Demo Token
        try:
            auth_start = time.perf_counter()
            resp = await client.post(f"{API_BASE}/api/auth/demo-token?role=fan")
            auth_time = (time.perf_counter() - auth_start) * 1000
            if resp.status_code != 200:
                print(f"Auth failed with status {resp.status_code}. Is the server running?")
                return
            token = resp.json()["access_token"]
            print(f"-> Auth successful! Time: {auth_time:.2f}ms")
        except Exception as e:
            print(f"Could not connect to server at {API_BASE}: {e}")
            print("Please ensure uvicorn is running: backend/.venv/Scripts/python -m uvicorn backend.main:app")
            return

        headers = {"Authorization": f"Bearer {token}"}
        payload = {"message": "Where is the nearest restroom to Gate 2?", "language": "en"}

        # 2. Cold Request (First time RAG compilation / agent loading)
        print("\nSending Cold Request (RAG lookup + agent routing)...")
        start = time.perf_counter()
        resp = await client.post(f"{API_BASE}/api/chat", json=payload, headers=headers)
        cold_time = (time.perf_counter() - start) * 1000
        print(f"-> Cold Response Status: {resp.status_code}. Latency: {cold_time:.2f}ms")

        # 3. Warm Requests (Exercising TTL caching)
        print("\nSending 5 Warm Requests (Cached lookup)...")
        latencies = []
        for i in range(5):
            start = time.perf_counter()
            resp = await client.post(f"{API_BASE}/api/chat", json=payload, headers=headers)
            warm_time = (time.perf_counter() - start) * 1000
            latencies.append(warm_time)
            print(f"   [Warm Run {i+1}] Latency: {warm_time:.2f}ms")

        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        print("\nWarm Latency stats (N=5):")
        print(f"-> P50: {p50:.2f}ms")
        print(f"-> P95: {p95:.2f}ms")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
