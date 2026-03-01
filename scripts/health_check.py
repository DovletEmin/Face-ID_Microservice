"""Health check script for all Face ID services."""

import asyncio
import sys

import httpx

SERVICES = {
    "API Gateway": "http://localhost:8000/api/v1/health",
    "Camera Service": "http://localhost:8001/api/v1/camera/health",
    "Face Service": "http://localhost:8002/api/v1/face/health",
    "Auth Service": "http://localhost:8003/api/v1/auth/health",
}


async def check_health():
    """Check health of all services."""
    print("=" * 50)
    print("Face ID — System Health Check")
    print("=" * 50)

    all_ok = True
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in SERVICES.items():
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"  ✓ {name}: {data.get('status', 'ok')}")
                else:
                    print(f"  ✗ {name}: HTTP {resp.status_code}")
                    all_ok = False
            except Exception as e:
                print(f"  ✗ {name}: {e}")
                all_ok = False

    print("=" * 50)
    if all_ok:
        print("All services healthy!")
    else:
        print("Some services are down.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(check_health())
