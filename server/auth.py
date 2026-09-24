"""Operator login: users, session cookies, and the guard for /api/ and /backend/.

Passwords are scrypt-hashed and sessions are opaque random tokens; only the
SHA-256 of a token is stored, so a leaked database does not yield usable
cookies. Users are created from the command line (create_user.py), never
through an unauthenticated endpoint. The guard is the middleware below (for
/api/) plus /internal/session-check, which nginx calls with auth_request for
the /backend/ proxies that never touch the manager otherwise.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import time
from threading import Lock

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import db

COOKIE = "netopsui_session"
SESSION_TTL_S = 7 * 24 * 3600
MIN_PASSWORD = 10

_USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_SCRYPT = {"n": 2**14, "r": 8, "p": 1, "maxmem": 64 * 1024 * 1024}

# Reachable without a session: the login itself, logout (only clears the
# cookie) and the container healthcheck.
_PUBLIC_PATHS = {"/api/auth/login", "/api/auth/logout", "/api/health"}

router = APIRouter()


# ── passwords ────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, dklen=32, **_SCRYPT)
    return f"scrypt${salt.hex()}${dk.hex()}"


def _check_hash(password: str, stored: str) -> bool:
    try:
        _, salt_hex, dk_hex = stored.split("$")
        dk = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), dklen=32, **_SCRYPT)
        return hmac.compare_digest(dk, bytes.fromhex(dk_hex))
    except (ValueError, TypeError):
        return False


# Verified against when the username does not exist, so a wrong username and a
# wrong password take the same time.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def check_password_policy(password: str) -> None:
    if len(password) < MIN_PASSWORD:
        raise ValueError(f"password minimal {MIN_PASSWORD} karakter")
    if len(password) > 256:
        raise ValueError("password maksimal 256 karakter")


def upsert_user(username: str, password: str) -> bool:
    """Create the user, or reset the password of an existing one. Returns True if created."""
    if not _USERNAME_RE.match(username):
        raise ValueError("username: huruf/angka/titik/strip/garis bawah, maksimal 64 karakter")
    check_password_policy(password)
    with db.conn() as c:
        row = c.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if row:
            c.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(password), row["id"]))
            c.execute("DELETE FROM sessions WHERE user_id=?", (row["id"],))  # a reset logs everyone out
            return False
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hash_password(password)))
        return True


# ── sessions ─────────────────────────────────────────────────────────────────

def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _new_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with db.conn() as c:
        c.execute("DELETE FROM sessions WHERE expires_at <= ?", (time.time(),))
        c.execute("INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                  (_digest(token), user_id, time.time() + SESSION_TTL_S))
    return token


def session_user(request: Request) -> dict | None:
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    with db.conn() as c:
        r = c.execute("""SELECT u.id, u.username FROM sessions s JOIN users u ON u.id = s.user_id
                         WHERE s.token_hash=? AND s.expires_at > ?""", (_digest(token), time.time())).fetchone()
    return dict(r) if r else None


def _set_cookie(request: Request, response: Response, token: str) -> None:
    response.set_cookie(COOKIE, token, max_age=SESSION_TTL_S, httponly=True, samesite="strict", path="/",
                        secure=request.headers.get("x-forwarded-proto") == "https")


# ── brute-force throttle (in memory, per client address + username) ──────────

_FAIL_LIMIT = 5
_FAIL_WINDOW_S = 300
_fails: dict[tuple[str, str], list[float]] = {}
_fails_lock = Lock()


def _client_ip(request: Request) -> str:
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "")


def _recent_fails(key: tuple[str, str]) -> list[float]:
    cutoff = time.time() - _FAIL_WINDOW_S
    kept = [t for t in _fails.get(key, []) if t > cutoff]
    if kept:
        _fails[key] = kept
    else:
        _fails.pop(key, None)
    return kept


# ── guard ────────────────────────────────────────────────────────────────────

async def guard(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/") and path not in _PUBLIC_PATHS and session_user(request) is None:
        return JSONResponse({"detail": "Belum login"}, status_code=401, headers={"Cache-Control": "no-store"})
    return await call_next(request)


@router.get("/internal/session-check")
def session_check(request: Request) -> Response:
    """auth_request target for nginx: 204 with a valid session cookie, else 401."""
    return Response(status_code=204 if session_user(request) else 401, headers={"Cache-Control": "no-store"})


# ── routes ───────────────────────────────────────────────────────────────────

class LoginIn(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=256)


class PasswordIn(BaseModel):
    current: str = Field(max_length=256)
    new: str = Field(max_length=256)


@router.post("/api/auth/login")
def login(req: LoginIn, request: Request, response: Response) -> dict:
    key = (_client_ip(request), req.username.lower())
    with _fails_lock:
        if len(_recent_fails(key)) >= _FAIL_LIMIT:
            raise HTTPException(429, "Terlalu banyak percobaan gagal. Coba lagi beberapa menit lagi.")
    with db.conn() as c:
        row = c.execute("SELECT id, username, password_hash FROM users WHERE username=?", (req.username,)).fetchone()
    ok = _check_hash(req.password, row["password_hash"] if row else _DUMMY_HASH) and row is not None
    if not ok:
        with _fails_lock:
            _fails.setdefault(key, []).append(time.time())
        raise HTTPException(401, "Username atau password salah")
    with _fails_lock:
        _fails.pop(key, None)
    _set_cookie(request, response, _new_session(row["id"]))
    response.headers["Cache-Control"] = "no-store"
    return {"username": row["username"]}


@router.post("/api/auth/logout")
def logout(request: Request, response: Response) -> dict:
    token = request.cookies.get(COOKIE)
    if token:
        with db.conn() as c:
            c.execute("DELETE FROM sessions WHERE token_hash=?", (_digest(token),))
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.get("/api/auth/me")
def me(request: Request) -> dict:
    u = session_user(request)  # the guard already rejected anonymous callers
    return {"username": u["username"]}


@router.post("/api/auth/password")
def change_password(req: PasswordIn, request: Request) -> dict:
    u = session_user(request)
    with db.conn() as c:
        row = c.execute("SELECT password_hash FROM users WHERE id=?", (u["id"],)).fetchone()
    if not _check_hash(req.current, row["password_hash"]):
        raise HTTPException(400, "Password saat ini salah")
    try:
        check_password_policy(req.new)
    except ValueError as e:
        raise HTTPException(400, str(e))
    keep = _digest(request.cookies[COOKIE])
    with db.conn() as c:
        c.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(req.new), u["id"]))
        c.execute("DELETE FROM sessions WHERE user_id=? AND token_hash<>?", (u["id"], keep))  # other devices log out
    return {"ok": True}
