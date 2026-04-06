"""
user_management.py — Controle de Acesso CORBANs · StarCheck
============================================================
Gerencia perfis, status de aprovação e notificações in-platform.

Tipos de usuário:
  'admin'    — acesso total, aprova outros usuários
  'operador' — operador interno Starbank, acesso completo exceto admin de usuários
  'corban'   — parceiro externo: isolamento total, white-label, sem admin

Status de aprovação:
  'pendente'  — aguarda revisão do admin
  'aprovado'  — acesso liberado
  'rejeitado' — acesso negado
  'suspenso'  — acesso temporariamente bloqueado
"""

from datetime import datetime, timezone
from typing import Optional
import streamlit as st


# ============================================================================
# HELPERS
# ============================================================================

def _sb():
    from auth import get_supabase_client
    return get_supabase_client()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(fn, default=None):
    """Executa fn com try/except silencioso."""
    try:
        return fn()
    except Exception as e:
        print(f"[user_management] {e}")
        return default


# ============================================================================
# PERFIL — LEITURA
# ============================================================================

def get_user_profile(user_id: str) -> dict:
    """Retorna o perfil completo de um usuário pelo UUID do auth."""
    return _safe(
        lambda: (_sb().table("user_profiles")
                      .select("*")
                      .eq("user_id", user_id)
                      .execute()
                      .data or [{}])[0],
        {}
    ) or {}


def get_all_users(status_filter: Optional[str] = None) -> list:
    """Retorna todos os usuários, opcionalmente filtrando por status."""
    def _fn():
        q = _sb().table("user_profiles").select("*").order("created_at", desc=True)
        if status_filter:
            q = q.eq("status", status_filter)
        return q.execute().data or []
    return _safe(_fn, [])


def get_pending_count() -> int:
    """Número de usuários aguardando aprovação."""
    return _safe(
        lambda: len(_sb().table("user_profiles")
                         .select("id")
                         .eq("status", "pendente")
                         .execute().data or []),
        0
    )


# ============================================================================
# PERFIL — ESCRITA
# ============================================================================

def create_user_profile(
    user_id: str,
    email: str,
    nome: str,
    setor: str,
    tipo_solicitado: str = "corban",
) -> bool:
    """
    Cria perfil pendente para novo usuário após signup.
    Gera notificação para o admin.
    Idempotente — se já existir perfil, não faz nada.
    """
    def _fn():
        # Idempotência
        existing = (_sb().table("user_profiles")
                         .select("id")
                         .eq("user_id", user_id)
                         .execute()
                         .data)
        if existing:
            return True

        # Cria perfil
        _sb().table("user_profiles").insert({
            "user_id": user_id,
            "email":   email,
            "nome":    nome,
            "setor":   setor,
            "tipo":    tipo_solicitado,
            "status":  "pendente",
            "created_at": _now(),
        }).execute()

        # Notificação admin
        tipo_label = "Operador Interno" if tipo_solicitado == "operador" else "CORBAN Parceiro"
        _sb().table("admin_notificacoes").insert({
            "tipo":        "novo_cadastro",
            "titulo":      f"Novo cadastro: {nome}",
            "mensagem":    (
                f"{nome} ({email}) solicitou acesso como {tipo_label}. "
                f"Setor informado: {setor or '—'}."
            ),
            "user_id_ref": user_id,
            "lida":        False,
            "created_at":  _now(),
        }).execute()
        return True

    return _safe(_fn, False)


def create_legacy_profile(user_id: str, email: str, nome: str, setor: str) -> bool:
    """
    Cria perfil aprovado como operador para usuários existentes
    que ainda não têm perfil na nova tabela (migração transparente).
    """
    return _safe(lambda: (
        _sb().table("user_profiles").insert({
            "user_id":    user_id,
            "email":      email,
            "nome":       nome,
            "setor":      setor,
            "tipo":       "operador",
            "status":     "aprovado",
            "aprovado_em": _now(),
            "notas_admin": "Perfil criado automaticamente — usuário legado.",
            "created_at": _now(),
        }).execute(),
        True
    )[-1], False)


def approve_user(
    user_id: str,
    tipo: str,
    admin_user_id: Optional[str],
    nome_empresa: str = "",
    cor_primaria: str = "#7C3AED",
    logo_url: str = "",
    notas: str = "",
) -> bool:
    """Aprova usuário, define tipo e configura white-label para CORBANs."""
    def _fn():
        payload: dict = {
            "status":       "aprovado",
            "tipo":         tipo,
            "aprovado_por": admin_user_id,
            "aprovado_em":  _now(),
            "notas_admin":  notas,
        }
        if tipo == "corban":
            payload["nome_empresa"] = nome_empresa.strip() or "CORBAN"
            payload["cor_primaria"] = cor_primaria or "#7C3AED"
            payload["logo_url"]     = logo_url.strip()

        _sb().table("user_profiles").update(payload).eq("user_id", user_id).execute()

        # Marca notificações deste usuário como lidas
        (_sb().table("admin_notificacoes")
              .update({"lida": True})
              .eq("user_id_ref", user_id)
              .execute())
        return True

    return _safe(_fn, False)


def reject_user(user_id: str, admin_user_id: Optional[str], notas: str = "") -> bool:
    def _fn():
        _sb().table("user_profiles").update({
            "status":       "rejeitado",
            "aprovado_por": admin_user_id,
            "aprovado_em":  _now(),
            "notas_admin":  notas,
        }).eq("user_id", user_id).execute()
        (_sb().table("admin_notificacoes")
              .update({"lida": True})
              .eq("user_id_ref", user_id)
              .execute())
        return True
    return _safe(_fn, False)


def suspend_user(user_id: str) -> bool:
    return _safe(
        lambda: (_sb().table("user_profiles")
                      .update({"status": "suspenso"})
                      .eq("user_id", user_id)
                      .execute(), True)[-1],
        False
    )


def reactivate_user(user_id: str) -> bool:
    return _safe(
        lambda: (_sb().table("user_profiles")
                      .update({"status": "aprovado"})
                      .eq("user_id", user_id)
                      .execute(), True)[-1],
        False
    )


def update_corban_config(
    user_id: str,
    nome_empresa: str,
    cor_primaria: str,
    logo_url: str,
) -> bool:
    return _safe(
        lambda: (_sb().table("user_profiles").update({
            "nome_empresa": nome_empresa,
            "cor_primaria": cor_primaria,
            "logo_url":     logo_url,
        }).eq("user_id", user_id).execute(), True)[-1],
        False
    )


# ============================================================================
# NOTIFICAÇÕES
# ============================================================================

def get_unread_count() -> int:
    return _safe(
        lambda: len(_sb().table("admin_notificacoes")
                         .select("id")
                         .eq("lida", False)
                         .execute().data or []),
        0
    )


def get_notifications(limit: int = 30) -> list:
    return _safe(
        lambda: (_sb().table("admin_notificacoes")
                      .select("*")
                      .order("created_at", desc=True)
                      .limit(limit)
                      .execute()
                      .data or []),
        []
    )


def mark_all_read() -> None:
    _safe(lambda: _sb().table("admin_notificacoes")
                        .update({"lida": True})
                        .eq("lida", False)
                        .execute())


# ============================================================================
# HELPERS DE SESSÃO — chamados no main.py
# ============================================================================

def is_admin() -> bool:
    """True se o usuário logado é admin."""
    try:
        return st.session_state.usuario.get("tipo") in ("admin",)
    except Exception:
        return False


def is_operador() -> bool:
    """True se operador interno ou admin."""
    try:
        return st.session_state.usuario.get("tipo") in ("admin", "operador")
    except Exception:
        return False


def is_corban() -> bool:
    """True se o usuário é CORBAN parceiro."""
    try:
        return st.session_state.usuario.get("tipo") == "corban"
    except Exception:
        return False


def corban_brand() -> dict:
    """
    Retorna configurações de marca do CORBAN logado.
    Retorna padrão Starbank se não for CORBAN.
    """
    try:
        u = st.session_state.usuario
        return {
            "nome_empresa": u.get("nome_empresa") or "Starbank Grupo",
            "cor_primaria": u.get("cor_primaria") or "#7C3AED",
            "logo_url":     u.get("logo_url") or "",
        }
    except Exception:
        return {
            "nome_empresa": "Starbank Grupo",
            "cor_primaria": "#7C3AED",
            "logo_url":     "",
        }
