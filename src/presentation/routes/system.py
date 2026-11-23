"""Rutas de estado y sesión del administrador."""
from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.core.settings import SESSION_COOKIE_NAME, SESSION_MAX_AGE_SECONDS
from src.modules.security.access_proxy import UserSession
from src.presentation.auth import (
    create_session_token,
    require_admin_session,
    verify_admin_credentials,
)
from src.presentation.holder import ElectoralSystemHolder
from src.presentation.schemas import AdminLoginRequest


def build_router(holder: ElectoralSystemHolder) -> APIRouter:
    router = APIRouter(tags=["Estado y sesión"])

    @router.get("/api/health")
    def health_check() -> Dict[str, str]:
        return {"status": "ONLINE", "system": "E-Voting Platform", "mode": holder.current_mode}

    @router.post("/api/admin/login")
    def admin_login(req: AdminLoginRequest, response: Response) -> Dict[str, str]:
        if not verify_admin_credentials(req.username, req.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario o contraseña incorrectos.",
            )
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=create_session_token(),
            max_age=SESSION_MAX_AGE_SECONDS,
            httponly=True,
            samesite="strict",
            secure=False,
            path="/",
        )
        return {"status": "SESION_INICIADA"}

    @router.post("/api/admin/logout")
    def admin_logout(response: Response) -> Dict[str, str]:
        response.delete_cookie(SESSION_COOKIE_NAME, path="/")
        return {"status": "SESION_CERRADA"}

    @router.get("/api/admin/session")
    def admin_session(session: UserSession = Depends(require_admin_session)) -> Dict[str, str]:
        return {"status": "AUTENTICADO", "user_id": session.user_id, "role": session.role.value}

    return router
