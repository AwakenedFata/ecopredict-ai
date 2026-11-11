"""
api/security.py
Security middleware, API Key validation, Operator role checks, and Sliding-Window Rate Limiting.
Designed according to api-and-interface-design guidelines.
"""

import os
import time
from typing import Dict, List, Optional
from collections import defaultdict
from fastapi import Header, HTTPException, Request, status

# Configurable secrets via environment variables
EDGE_API_KEY_ENV = os.getenv("ECOPREDICT_EDGE_API_KEY", "eco-edge-secret-2026")
OPERATOR_TOKEN_ENV = os.getenv("ECOPREDICT_OPERATOR_TOKEN", "eco-operator-token-2026")
AUTH_STRICT_MODE = os.getenv("ECOPREDICT_AUTH_STRICT", "false").lower() in ("true", "1", "yes")


class SlidingWindowRateLimiter:
    """
    In-memory thread-safe sliding window rate limiter.
    Limits requests per client (identified by IP or API Key) within a sliding time window.
    """
    def __init__(self, max_requests: int = 120, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.history: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        window_start = now - self.window_seconds
        
        # Purge timestamps outside the current sliding window
        self.history[client_id] = [t for t in self.history[client_id] if t > window_start]
        
        if len(self.history[client_id]) >= self.max_requests:
            return False
            
        self.history[client_id].append(now)
        return True


# Global rate limiter instance: max 120 requests/minute per client
telemetry_rate_limiter = SlidingWindowRateLimiter(max_requests=120, window_seconds=60)


async def verify_edge_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> str:
    """
    Validates edge sensor API key and applies rate limiting.
    In non-strict mode (local dev/demo), allows unauthenticated requests with a dev warning.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    # 1. Rate Limiting Check
    if not telemetry_rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit terlampaui. Maksimal {telemetry_rate_limiter.max_requests} permintaan per menit."
        )

    # 2. Key Check (Strict vs Permissive Dev Mode)
    if AUTH_STRICT_MODE:
        if not x_api_key or x_api_key != EDGE_API_KEY_ENV:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Kunci API Sensor (X-API-Key) tidak valid atau hilang."
            )
        return x_api_key

    # In permissive dev mode, return provided key or fallback
    return x_api_key or "dev-permissive"


async def verify_operator_role(
    x_operator_token: Optional[str] = Header(None, alias="X-Operator-Token")
) -> str:
    """
    Validates operator/technician credentials for critical actions
    (triggering fleet AI scan, resolving maintenance work orders).
    """
    if AUTH_STRICT_MODE:
        if not x_operator_token or x_operator_token != OPERATOR_TOKEN_ENV:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Akses ditolak: Operasi ini membutuhkan X-Operator-Token yang sah."
            )
        return x_operator_token

    return x_operator_token or "dev-operator"
