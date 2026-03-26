"""
crm_page.py — Busca de Servidores no RD Station CRM
Autenticação OAuth2 automática (access token, refresh token, renovação).
Busca em TODO o CRM por nome, retornando TODAS as negociações encontradas.
"""

import streamlit as st
import requests
import json
import os
import re
import time
from datetime import datetime, timedelta
from urllib.parse import quote

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG OAuth2
# ══════════════════════════════════════════════════════════════════════════════
_CLIENT_ID     = "b3d84db1-2264-4ffe-aa92-c659405aa41b"
_CLIENT_SECRET = "ef1ca47f4b74486080071218913b02b7"
_TOKEN_FILE    = "rd_crm_tokens.json"
_REDIRECT_URI  = "https://starbank-holerites-xyzp.streamlit.app/"

# ══════════════════════════════════════════════════════════════════════════════
# GERENCIAMENTO DE TOKENS
# ══════════════════════════════════════════════════════════════════════════════

def _redirect_uri() -> str:
    return _REDIRECT_URI


def _auth_url() -> str:
    return (
        "https://accounts.rdstation.com/oauth/authorize"
        "?response_type=code"
        f"&client_id={_CLIENT_ID}"
        f"&redirect_uri={quote(_redirect_uri(), safe='')}"
    )


def _save_tokens(access: str, refresh: str, expires_in: int):
    exp = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
    with open(_TOKEN_FILE, "w") as f:
        json.dump({"access_token": access, "refresh_token": refresh, "expires_at": exp}, f)
    st.session_state["crm_token"]  = access
    st.session_state["crm_expiry"] = datetime.fromisoformat(exp)


def _load_tokens() -> bool:
    if not os.path.exists(_TOKEN_FILE):
        return False
    try:
        with open(_TOKEN_FILE) as f:
            t = json.load(f)
        exp = datetime.fromisoformat(t["expires_at"])
        if exp > datetime.now() + timedelta(minutes=5):
            st.session_state["crm_token"]  = t["access_token"]
            st.session_state["crm_expiry"] = exp
            return True
        return _do_refresh(t["refresh_token"])
    except Exception:
        return False


def _do_refresh(rt: str) -> bool:
    try:
        r = requests.post(
            "https://api.rd.services/oauth2/token",
            data={
                "client_id":     _CLIENT_ID,
                "client_secret": _CLIENT_SECRET,
                "refresh_token": rt,
                "grant_type":    "refresh_token",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        if r.ok:
            d = r.json()
            _save_tokens(d["access_token"], d["refresh_token"], d["expires_in"])
            return True
    except Exception:
        pass
    _clear_tokens()
    return False


def _exchange_code(code: str) -> bool:
    try:
        r = requests.post(
            "https://api.rd.services/oauth2/token",
            data={
                "client_id":     _CLIENT_ID,
                "client_secret": _CLIENT_SECRET,
                "code":          code,
                "redirect_uri":  _redirect_uri(),
                "grant_type":    "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        if r.ok:
            d = r.json()
            _save_tokens(d["access_token"], d["refresh_token"], d["expires_in"])
            return True
        return False
    except Exception:
        return False


def _clear_tokens():
    if os.path.exists(_TOKEN_FILE):
        os.remove(_TOKEN_FILE)
    st.session_state.pop("crm_token",  None)
    st.session_state.pop("crm_expiry", None)


def _get_token() -> str | None:
    if "crm_token" not in st.session_state:
        _load_tokens()
    exp = st.session_state.get("crm_expiry")
    if not exp or exp <= datetime.now() + timedelta(minutes=2):
        if not _load_tokens():
            return None
    return st.session_state.get("crm_token")


# ══════════════════════════════════════════════════════════════════════════════
# CHAMADAS À API RD STATION CRM
# ══════════════════════════════════════════════════════════════════════════════

def _api_get(path: str, params: dict = None) -> dict | None:
    tok = _get_token()
    if not tok:
        return None
    url     = f"https://api.rd.services{path}"
    headers = {"Authorization": f"Bearer {tok}"}
    for tentativa in range(3):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=15)
            if r.status_code == 401:
                if _load_tokens():
                    headers["Authorization"] = f"Bearer {st.session_state.get('crm_token', tok)}"
                    continue
                return None
            if r.status_code == 429:
                time.sleep(2 * (tentativa + 1))
                continue
            if r.ok:
                return r.json()
            return None
        except Exception:
            if tentativa == 2:
                break
            time.sleep(1)
    return None


def buscar_deals_por_nome(nome: str) -> list:
    """
    Busca TODAS as negociações que contenham o nome pesquisado, varrendo
    todo o CRM sem limite de páginas ou quantidade de resultados.

    Estratégia:
      1. Tenta filtro nativo da API (filter[name]) — percorre todas as
         páginas do filtro até esgotar os resultados.
      2. Se a API ignorar o filtro (retornar dados sem correspondência),
         faz varredura completa página a página em todo o CRM.

    Retorna lista ordenada do mais recente ao mais antigo.
    """
    nome_l = nome.strip().lower()

    # ── Tentativa 1: filtro nativo por nome, todas as páginas ────────────────
    achados_filtro: list[dict] = []
    pagina = 1
    filtro_funcionou = False

    resp = _api_get("/crm/v2/deals", {
        "filter[name]": nome,
        "sort":         "-created_at",
        "page[size]":   100,
        "page[number]": 1,
    })

    if resp and isinstance(resp.get("data"), list):
        pagina_filtrados = [d for d in resp["data"] if nome_l in (d.get("name") or "").lower()]
        if pagina_filtrados:
            filtro_funcionou = True
            achados_filtro.extend(pagina_filtrados)

            # Continua paginando enquanto houver próxima página
            while resp.get("links", {}).get("next"):
                pagina += 1
                resp = _api_get("/crm/v2/deals", {
                    "filter[name]": nome,
                    "sort":         "-created_at",
                    "page[size]":   100,
                    "page[number]": pagina,
                })
                if not resp or not resp.get("data"):
                    break
                for d in resp["data"]:
                    if nome_l in (d.get("name") or "").lower():
                        achados_filtro.append(d)
                time.sleep(0.1)

    if filtro_funcionou:
        achados_filtro.sort(key=lambda d: d.get("created_at") or "", reverse=True)
        return achados_filtro

    # ── Tentativa 2: varredura completa de TODO o CRM ─────────────────────────
    # Percorre todas as páginas disponíveis sem nenhum limite artificial.
    achados: list[dict] = []
    pagina  = 1
    total_registros_est = None

    pb  = st.progress(0.0)
    msg = st.empty()

    while True:
        msg.caption(
            f"🔍 Varrendo página {pagina} do CRM… "
            f"({len(achados)} negociação(ões) encontrada(s) até agora)"
        )

        resp = _api_get("/crm/v2/deals", {
            "sort":         "-created_at",
            "page[size]":   100,
            "page[number]": pagina,
        })

        if not resp:
            break

        dados = resp.get("data", [])
        if not dados:
            break

        # Tenta capturar total de registros via meta para exibir progresso real
        meta = resp.get("meta") or {}
        if not total_registros_est:
            total_raw = meta.get("total") or meta.get("count") or meta.get("total_count")
            if total_raw:
                total_registros_est = int(total_raw)

        for d in dados:
            if nome_l in (d.get("name") or "").lower():
                achados.append(d)

        # Progresso: usa total real se disponível, senão anima ciclicamente
        if total_registros_est and total_registros_est > 0:
            registros_vistos = pagina * 100
            pb.progress(min(registros_vistos / total_registros_est, 1.0))
        else:
            pb.progress((pagina % 20) / 20)

        # Encerra quando não há próxima página E a página veio com menos de 100 itens
        tem_next_link = bool(resp.get("links", {}).get("next"))
        pagina_cheia  = len(dados) == 100

        if not tem_next_link and not pagina_cheia:
            break

        pagina += 1
        time.sleep(0.1)  # respeita rate limit

    pb.progress(1.0)
    time.sleep(0.25)
    pb.empty()
    msg.empty()

    achados.sort(key=lambda d: d.get("created_at") or "", reverse=True)
    return achados


def _get_contato(contact_id: str) -> dict:
    if not contact_id:
        return {}
    r = _api_get(f"/crm/v2/contacts/{contact_id}")
    return (r or {}).get("data", {})


def _get_org(org_id: str) -> dict:
    if not org_id:
        return {}
    r = _api_get(f"/crm/v2/organizations/{org_id}")
    return (r or {}).get("data", {})


def _get_arquivos(deal_id: str) -> list:
    r = _api_get(f"/crm/v2/deals/{deal_id}/files")
    return (r or {}).get("data", [])


def _get_atividades(deal_id: str) -> list:
    r = _api_get(f"/crm/v2/deals/{deal_id}/activities")
    if r and r.get("data"):
        return r["data"]
    r2 = _api_get(f"/crm/v2/deals/{deal_id}/notes")
    return (r2 or {}).get("data", [])


# ══════════════════════════════════════════════════════════════════════════════
# UTILITÁRIOS DE FORMATAÇÃO
# ══════════════════════════════════════════════════════════════════════════════

def _fmt_date(raw: str) -> str:
    if not raw:
        return "—"
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return raw[:10] if len(raw) >= 10 else raw


def _fmt_date_relative(raw: str) -> str:
    if not raw:
        return "—"
    try:
        dt  = datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None)
        now = datetime.now()
        diff = now - dt
        if diff.days == 0:
            h = diff.seconds // 3600
            return f"há {h}h" if h else "agora mesmo"
        if diff.days == 1:
            return "ontem"
        if diff.days < 7:
            return f"há {diff.days} dias"
        if diff.days < 30:
            return f"há {diff.days // 7} semana(s)"
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return raw[:10] if len(raw) >= 10 else raw


def _fmt_phone(phone: str) -> str:
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11:
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    return phone


def _cpf_mask(cpf: str) -> str:
    d = re.sub(r"\D", "", cpf or "")
    if len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    return cpf or "—"


def _ext_icon(nome: str) -> str:
    ext = nome.rsplit(".", 1)[-1].lower() if "." in nome else ""
    return {
        "pdf": "📄", "jpg": "🖼️", "jpeg": "🖼️", "png": "🖼️",
        "doc": "📝", "docx": "📝", "xls": "📊", "xlsx": "📊",
    }.get(ext, "📁")


def _render_info_grid(tags: list):
    if not tags:
        return
    html = '<div class="crm-info-grid">'
    for icon, label, value in tags:
        html += (
            f'<div class="crm-info-tag">'
            f'  <span class="crm-info-icon">{icon}</span>'
            f'  <div class="crm-info-text">'
            f'    <p class="crm-info-label">{label}</p>'
            f'    <p class="crm-info-value">{value}</p>'
            f'  </div>'
            f'</div>'
        )
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def _section_label(label: str):
    st.markdown(f'<div class="crm-section-label">{label}</div>', unsafe_allow_html=True)


def _pill(text: str, color: str = "#7C3AED", bg: str = "#EDE9FE") -> str:
    return (
        f'<span style="background:{bg};color:{color};'
        f'padding:.18rem .6rem;border-radius:99px;'
        f'font-size:.68rem;font-weight:700;">{text}</span>'
    )


# ══════════════════════════════════════════════════════════════════════════════
# CSS GLOBAL
# ══════════════════════════════════════════════════════════════════════════════

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

section[data-testid="stMain"] { font-family: 'Inter', sans-serif; }

.crm-hero {
    background: linear-gradient(135deg, #3B0764 0%, #6D28D9 55%, #7C3AED 100%);
    border-radius: 1.4rem;
    padding: 2rem 2.25rem 1.85rem;
    margin-bottom: 1.75rem;
    box-shadow: 0 12px 40px rgba(109,40,217,.28);
    position: relative; overflow: hidden;
}
.crm-hero::before {
    content: ''; position: absolute; top: -40px; right: -40px;
    width: 220px; height: 220px;
    background: rgba(255,255,255,.05); border-radius: 50%;
}
.crm-hero::after {
    content: ''; position: absolute; bottom: -60px; left: -20px;
    width: 160px; height: 160px;
    background: rgba(255,255,255,.04); border-radius: 50%;
}
.crm-hero-eyebrow {
    font-size: .68rem; font-weight: 700; letter-spacing: .14em;
    color: rgba(255,255,255,.55); text-transform: uppercase; margin: 0 0 .5rem;
}
.crm-hero-title {
    color: #fff; font-size: 1.6rem; font-weight: 800;
    margin: 0 0 .45rem; letter-spacing: -.5px; line-height: 1.2;
}
.crm-hero-sub {
    color: rgba(255,255,255,.65); font-size: .86rem; margin: 0; line-height: 1.65;
}

.crm-status-bar {
    display: flex; align-items: center; gap: .5rem;
    background: #F0FDF4; border: 1px solid #BBF7D0;
    border-radius: .65rem; padding: .5rem 1rem;
    font-size: .8rem; font-weight: 600; color: #166534; margin-bottom: 1.25rem;
}
.crm-status-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #22C55E; box-shadow: 0 0 0 3px rgba(34,197,94,.2); flex-shrink: 0;
}

.crm-auth-wrap {
    background: linear-gradient(160deg, #F5F3FF 0%, #EDE9FE 100%);
    border: 1.5px solid #C4B5FD; border-radius: 1.25rem;
    padding: 3rem 2.25rem; text-align: center;
    max-width: 500px; margin: 2.5rem auto;
    box-shadow: 0 8px 24px rgba(124,58,237,.1);
}
.crm-auth-icon  { font-size: 3rem; margin-bottom: 1rem; }
.crm-auth-title { font-size: 1.2rem; font-weight: 800; color: #4C1D95; margin-bottom: .55rem; }
.crm-auth-desc  { font-size: .87rem; color: #6B7280; margin-bottom: 2rem; line-height: 1.7; }
.crm-auth-cta   {
    display: inline-flex; align-items: center; gap: .5rem;
    background: linear-gradient(135deg, #7C3AED, #4C1D95);
    color: white !important; font-weight: 700; font-size: .9rem;
    padding: .8rem 2.25rem; border-radius: .75rem; text-decoration: none;
    box-shadow: 0 6px 20px rgba(124,58,237,.35);
    transition: transform .15s, box-shadow .15s; letter-spacing: .02em;
}
.crm-auth-cta:hover { transform: translateY(-1px); box-shadow: 0 10px 28px rgba(124,58,237,.45); }
.crm-auth-note { margin-top: 1.1rem; font-size: .7rem; color: #A78BFA; }

.crm-search-label {
    font-size: .72rem; font-weight: 700; color: #7C3AED;
    text-transform: uppercase; letter-spacing: .1em; margin-bottom: .55rem;
}
.crm-search-hint {
    font-size: .76rem; color: #9CA3AF;
    margin-top: .55rem; display: flex; align-items: center; gap: .35rem;
}

.crm-result-meta {
    display: flex; align-items: center; gap: .5rem;
    font-size: .8rem; color: #6B7280; font-weight: 500; margin-bottom: 1rem;
}
.crm-result-count {
    background: #7C3AED; color: #fff;
    font-size: .72rem; font-weight: 800;
    padding: .15rem .6rem; border-radius: 99px;
}

[data-testid="stExpander"] summary {
    border-radius: .75rem !important;
    background: linear-gradient(135deg, #FAFAFA, #F5F3FF) !important;
    border: 1.5px solid #E5E7EB !important;
    border-left: 4px solid #7C3AED !important;
    padding: .9rem 1.2rem !important;
    margin-bottom: .45rem !important;
    font-weight: 700 !important; font-size: .92rem !important;
    color: #111827 !important;
    transition: box-shadow .2s, border-color .2s !important;
}
[data-testid="stExpander"] summary:hover {
    box-shadow: 0 4px 16px rgba(109,40,217,.12) !important;
    border-color: #C4B5FD !important;
}
[data-testid="stExpander"] > div:last-child {
    border: 1.5px solid #E5E7EB !important;
    border-top: none !important;
    border-radius: 0 0 .75rem .75rem !important;
    padding: 1.2rem 1.4rem !important;
    margin-bottom: .8rem !important;
    background: #FAFAFA !important;
}

.crm-info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
    gap: .55rem; margin: .5rem 0 .9rem;
}
.crm-info-tag {
    display: flex; align-items: flex-start; gap: .6rem;
    background: #fff; border: 1px solid #E5E7EB;
    border-radius: .6rem; padding: .6rem .85rem;
    transition: border-color .15s, box-shadow .15s;
}
.crm-info-tag:hover { border-color: #C4B5FD; box-shadow: 0 2px 8px rgba(109,40,217,.08); }
.crm-info-icon  { font-size: .92rem; flex-shrink: 0; margin-top: .1rem; }
.crm-info-text  { min-width: 0; }
.crm-info-label {
    font-size: .58rem; color: #A78BFA; font-weight: 800;
    text-transform: uppercase; letter-spacing: .09em; margin: 0 0 .18rem;
}
.crm-info-value {
    font-size: .84rem; color: #111827; font-weight: 600;
    margin: 0; word-break: break-word; line-height: 1.4;
}

.crm-section-label {
    font-size: .65rem; font-weight: 800; color: #7C3AED;
    text-transform: uppercase; letter-spacing: .12em;
    display: flex; align-items: center; gap: .45rem; margin: 1.1rem 0 .5rem;
}
.crm-section-label::after {
    content: ''; flex: 1; height: 1.5px;
    background: linear-gradient(90deg, #DDD6FE, transparent);
}

.crm-doc-item {
    display: flex; align-items: center; gap: .65rem;
    padding: .5rem .9rem;
    background: #F0FDF4; border: 1px solid #BBF7D0;
    border-radius: .55rem; margin-bottom: .35rem;
    font-size: .83rem; color: #065F46; font-weight: 600; transition: background .15s;
}
.crm-doc-item:hover { background: #DCFCE7; }
.crm-doc-meta { font-size: .7rem; color: #6EE7B7; margin-left: auto; flex-shrink: 0; }

.crm-note-item {
    background: #fff; border: 1px solid #E5E7EB;
    border-left: 3px solid #A78BFA;
    border-radius: 0 .6rem .6rem 0;
    padding: .75rem 1rem; margin-bottom: .42rem;
    font-size: .84rem; color: #374151; line-height: 1.65;
}
.crm-note-meta {
    font-size: .69rem; color: #9CA3AF;
    margin-top: .4rem; display: flex; gap: .55rem; flex-wrap: wrap; align-items: center;
}
.crm-note-tag {
    background: #EDE9FE; color: #7C3AED;
    padding: .07rem .48rem; border-radius: 99px;
    font-size: .63rem; font-weight: 800;
    text-transform: uppercase; letter-spacing: .06em;
}

.crm-empty {
    text-align: center; padding: 3.5rem 1rem; color: #9CA3AF;
}
.crm-empty-icon { font-size: 2.75rem; margin-bottom: .75rem; }
.crm-empty-txt  { font-size: .95rem; color: #6B7280; font-weight: 600; }
.crm-empty-sub  { font-size: .82rem; color: #D1D5DB; margin-top: .45rem; }

.crm-none-tag {
    display: inline-block;
    background: #F9FAFB; color: #9CA3AF;
    font-size: .75rem; padding: .28rem .75rem;
    border-radius: .4rem; border: 1px solid #E5E7EB; margin-top: .1rem;
}

.crm-divider {
    height: 1px;
    background: linear-gradient(90deg, #EDE9FE, #E5E7EB, transparent);
    margin: 1rem 0;
}
</style>
"""


# ══════════════════════════════════════════════════════════════════════════════
# RENDER PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def render_crm_page():
    st.markdown(_CSS, unsafe_allow_html=True)

    # ── Capturar OAuth callback ───────────────────────────────────────────────
    qp = st.query_params
    if "code" in qp and not st.session_state.get("crm_token"):
        with st.spinner("🔄 Concluindo autenticação com o RD Station…"):
            ok = _exchange_code(qp["code"])
        st.query_params.clear()
        if ok:
            st.success("✅ Conectado ao RD Station CRM com sucesso!")
            time.sleep(0.8)
            st.rerun()
        else:
            st.error("❌ Falha na autenticação. Verifique as credenciais e tente novamente.")

    # ── Hero header ───────────────────────────────────────────────────────────
    st.markdown("""
    <div class="crm-hero">
        <p class="crm-hero-eyebrow">⚡ RD Station CRM</p>
        <div class="crm-hero-title">Busca de Servidores</div>
        <p class="crm-hero-sub">
            Pesquise pelo nome e veja
            <strong style="color:rgba(255,255,255,.9)">todas as negociações encontradas</strong>
            em todo o CRM — do mais recente ao mais antigo.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Autenticação ──────────────────────────────────────────────────────────
    tok = _get_token()

    if not tok:
        auth_link = _auth_url()
        redirect  = _redirect_uri()
        st.markdown(f"""
        <div class="crm-auth-wrap">
            <div class="crm-auth-icon">🔐</div>
            <div class="crm-auth-title">Conectar ao RD Station CRM</div>
            <div class="crm-auth-desc">
                Para buscar servidores, autorize o acesso ao CRM.<br>
                Após autorizar você será redirecionado de volta automaticamente.
            </div>
            <a class="crm-auth-cta" href="{auth_link}" target="_top">
                🔑 &nbsp;Autorizar acesso ao CRM
            </a>
            <div class="crm-auth-note">Redirect URI: <code>{redirect}</code></div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Status bar + desconectar ──────────────────────────────────────────────
    c_status, c_disc = st.columns([6, 1])
    with c_status:
        st.markdown(
            '<div class="crm-status-bar">'
            '  <div class="crm-status-dot"></div>'
            '  Conectado ao RD Station CRM'
            '</div>',
            unsafe_allow_html=True
        )
    with c_disc:
        if st.button("🔌 Sair", key="crm_btn_disc",
                     help="Remove a conexão com o CRM",
                     use_container_width=True):
            _clear_tokens()
            st.session_state.pop("crm_resultados", None)
            st.session_state.pop("crm_query",      None)
            st.rerun()

    # ── Campo de busca ────────────────────────────────────────────────────────
    st.markdown('<div class="crm-search-label">🔍 Buscar cliente</div>', unsafe_allow_html=True)

    col_inp, col_btn = st.columns([5, 1])
    with col_inp:
        nome_busca = st.text_input(
            "nome_busca_crm",
            placeholder="Ex: João da Silva, Maria Oliveira…",
            label_visibility="collapsed",
            key="crm_input_nome",
        )
    with col_btn:
        buscar_clicked = st.button(
            "Buscar", type="primary",
            use_container_width=True, key="crm_btn_buscar"
        )

    st.markdown(
        '<p class="crm-search-hint">'
        '💡 Varre <strong>todo o CRM</strong> e retorna '
        '<strong>todas as negociações</strong> com esse nome, '
        'da mais recente à mais antiga.'
        '</p>',
        unsafe_allow_html=True
    )

    # ── Executar busca ────────────────────────────────────────────────────────
    if buscar_clicked:
        nome_limpo = (nome_busca or "").strip()
        if len(nome_limpo) < 2:
            st.warning("⚠️ Digite pelo menos 2 caracteres para buscar.")
        else:
            for k in list(st.session_state.keys()):
                if k.startswith("crm_detail_"):
                    del st.session_state[k]

            with st.spinner(f'Buscando "{nome_limpo}" em todo o CRM…'):
                resultados = buscar_deals_por_nome(nome_limpo)

            st.session_state["crm_resultados"] = resultados
            st.session_state["crm_query"]      = nome_limpo

    # ── Exibir resultados ─────────────────────────────────────────────────────
    resultados: list | None = st.session_state.get("crm_resultados")
    query: str              = st.session_state.get("crm_query", "")

    if resultados is None:
        st.markdown("""
        <div class="crm-empty">
            <div class="crm-empty-icon">🔎</div>
            <div class="crm-empty-txt">Pronto para buscar</div>
            <div class="crm-empty-sub">Digite um nome acima e clique em <strong>Buscar</strong>.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    if len(resultados) == 0:
        st.markdown(f"""
        <div class="crm-empty">
            <div class="crm-empty-icon">😕</div>
            <div class="crm-empty-txt">Nenhuma negociação encontrada para <strong>"{query}"</strong></div>
            <div class="crm-empty-sub">Verifique a grafia ou tente termos diferentes.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    n = len(resultados)
    plural = "negociações encontradas" if n > 1 else "negociação encontrada"
    st.markdown(
        f'<div class="crm-result-meta">'
        f'  <span class="crm-result-count">{n}</span>'
        f'  {plural} para&nbsp;<em>"{query}"</em>'
        f'  &nbsp;·&nbsp; da mais recente à mais antiga'
        f'</div>',
        unsafe_allow_html=True
    )

    # ── Cards de resultado — todos, sem limite ────────────────────────────────
    for idx, deal in enumerate(resultados):
        deal_id     = deal.get("id", "")
        deal_name   = deal.get("name") or "Sem nome"
        criado_em   = _fmt_date(deal.get("created_at", ""))
        criado_rel  = _fmt_date_relative(deal.get("created_at", ""))
        atualizado  = _fmt_date(deal.get("updated_at", ""))
        contact_id  = deal.get("contact_id", "")
        org_id      = deal.get("organization_id", "")
        stage_id    = deal.get("stage_id", "")
        pipeline_id = deal.get("pipeline_id", "")
        cf_deal     = deal.get("custom_fields") or {}

        # Label: destaca o mais recente, enumera os demais
        if idx == 0:
            ordem_label = "🟢 Mais recente"
        else:
            ordem_label = f"#{idx + 1}"

        expander_label = f"{ordem_label}  ·  {deal_name}  ·  {criado_em}"

        with st.expander(expander_label, expanded=(idx == 0)):

            detail_key = f"crm_detail_{deal_id}"

            if detail_key not in st.session_state:
                with st.spinner("Carregando dados do card…"):
                    contato    = _get_contato(contact_id)
                    org        = _get_org(org_id)
                    arquivos   = _get_arquivos(deal_id)
                    atividades = _get_atividades(deal_id)
                st.session_state[detail_key] = {
                    "contato":    contato,
                    "org":        org,
                    "arquivos":   arquivos,
                    "atividades": atividades,
                }

            det        = st.session_state[detail_key]
            contato    = det["contato"]
            org        = det["org"]
            arquivos   = det["arquivos"]
            atividades = det["atividades"]

            # ── INFORMAÇÕES DO CARD ──────────────────────────────────────────
            _section_label("📋 Informações do Card")

            tags_card = [
                ("🆔", "ID do Card",  deal_id   or "—"),
                ("📅", "Criado em",   criado_em),
                ("🔄", "Atualizado",  atualizado),
            ]
            if stage_id:
                tags_card.append(("📍", "Estágio ID",  stage_id))
            if pipeline_id:
                tags_card.append(("🗂️", "Pipeline ID", pipeline_id))

            _CF_SKIP = {"id", "name", "created_at", "updated_at",
                        "contact_id", "organization_id", "stage_id", "pipeline_id"}
            for k, v in cf_deal.items():
                if k not in _CF_SKIP and v is not None and str(v).strip():
                    tags_card.append(("⚙️", k.replace("_", " ").title(), str(v)))

            _render_info_grid(tags_card)

            st.markdown('<div class="crm-divider"></div>', unsafe_allow_html=True)

            # ── CONTATO ──────────────────────────────────────────────────────
            _section_label("👤 Contato")

            if contato:
                tags_c = []
                nome_c = contato.get("name") or "—"
                tags_c.append(("👤", "Nome Completo", nome_c))

                cpf_raw = (
                    contato.get("cpf")
                    or (contato.get("custom_fields") or {}).get("cpf")
                    or (contato.get("custom_fields") or {}).get("CPF")
                    or cf_deal.get("cpf")
                    or cf_deal.get("CPF")
                    or ""
                )
                if cpf_raw:
                    tags_c.append(("🪪", "CPF", _cpf_mask(str(cpf_raw))))

                emails = contato.get("emails") or []
                if isinstance(emails, list):
                    for i, em in enumerate(emails[:3]):
                        ev = em.get("email", "") if isinstance(em, dict) else str(em)
                        if ev:
                            tags_c.append(("📧", f"E-mail{'' if i == 0 else f' {i+1}'}", ev))
                elif isinstance(emails, str) and emails:
                    tags_c.append(("📧", "E-mail", emails))

                phones = contato.get("phones") or []
                if isinstance(phones, list):
                    for i, ph in enumerate(phones[:3]):
                        pv = ph.get("phone", "") if isinstance(ph, dict) else str(ph)
                        if pv:
                            tags_c.append(("📞", f"Telefone{'' if i == 0 else f' {i+1}'}", _fmt_phone(pv)))
                elif isinstance(phones, str) and phones:
                    tags_c.append(("📞", "Telefone", _fmt_phone(phones)))

                _CF_CONT_SKIP = {"cpf", "CPF", "name", "id", "emails", "phones"}
                for k, v in (contato.get("custom_fields") or {}).items():
                    if k not in _CF_CONT_SKIP and v is not None and str(v).strip():
                        tags_c.append(("⚙️", k.replace("_", " ").title(), str(v)))

                _render_info_grid(tags_c)

            elif contact_id:
                st.caption("ℹ️ Contato não encontrado ou sem permissão de acesso.")
            else:
                st.markdown('<span class="crm-none-tag">Nenhum contato vinculado ao card</span>',
                            unsafe_allow_html=True)

            st.markdown('<div class="crm-divider"></div>', unsafe_allow_html=True)

            # ── ORGANIZAÇÃO ──────────────────────────────────────────────────
            _section_label("🏢 Organização")

            if org:
                tags_o = []
                if org.get("name"):
                    tags_o.append(("🏢", "Nome",     org["name"]))
                if org.get("website"):
                    tags_o.append(("🌐", "Website",  org["website"]))
                if org.get("phone"):
                    tags_o.append(("📞", "Telefone", _fmt_phone(org["phone"])))
                if org.get("cnpj"):
                    tags_o.append(("🆔", "CNPJ",     org["cnpj"]))
                if org.get("city"):
                    estado = org.get("state", "")
                    city   = org["city"] + (f" — {estado}" if estado else "")
                    tags_o.append(("📍", "Cidade",   city))
                for k, v in (org.get("custom_fields") or {}).items():
                    if v is not None and str(v).strip():
                        tags_o.append(("⚙️", k.replace("_", " ").title(), str(v)))
                _render_info_grid(tags_o)

            elif org_id:
                st.caption("ℹ️ Organização não encontrada ou sem permissão de acesso.")
            else:
                st.markdown('<span class="crm-none-tag">Nenhuma organização vinculada</span>',
                            unsafe_allow_html=True)

            st.markdown('<div class="crm-divider"></div>', unsafe_allow_html=True)

            # ── DOCUMENTOS ───────────────────────────────────────────────────
            _section_label(f"📎 Documentos ({len(arquivos)})")

            if arquivos:
                docs_html = ""
                for arq in arquivos:
                    nome_arq = arq.get("name") or arq.get("filename") or "Arquivo sem nome"
                    tamanho  = arq.get("size") or arq.get("file_size") or 0
                    tam_str  = f"{tamanho / 1024:.1f} KB" if tamanho else ""
                    data_arq = _fmt_date(arq.get("created_at") or arq.get("inserted_at") or "")
                    info_str = " · ".join(filter(None, [
                        tam_str,
                        data_arq if data_arq != "—" else "",
                    ]))
                    docs_html += (
                        f'<div class="crm-doc-item">'
                        f'  <span>{_ext_icon(nome_arq)}</span>'
                        f'  <span style="flex:1;">{nome_arq}</span>'
                        f'  <span class="crm-doc-meta">{info_str}</span>'
                        f'</div>'
                    )
                st.markdown(docs_html, unsafe_allow_html=True)
            else:
                st.markdown(
                    '<span class="crm-none-tag">Nenhum documento anexado ao card</span>',
                    unsafe_allow_html=True
                )

            st.markdown('<div class="crm-divider"></div>', unsafe_allow_html=True)

            # ── ANOTAÇÕES ────────────────────────────────────────────────────
            notas = [
                a for a in atividades
                if any(a.get(k) for k in ("body", "content", "note", "description", "text"))
            ] or atividades

            _section_label(f"📝 Anotações ({min(len(notas), 10)} mais recentes)")

            if notas:
                notes_html = ""
                for nota in notas[:10]:
                    corpo = (
                        nota.get("body")
                        or nota.get("content")
                        or nota.get("note")
                        or nota.get("description")
                        or nota.get("text")
                        or ""
                    )
                    if not str(corpo).strip():
                        continue

                    tipo_raw = nota.get("type") or nota.get("kind") or ""
                    tipo     = tipo_raw.replace("_", " ").title() if tipo_raw else ""
                    dt       = _fmt_date(nota.get("created_at") or nota.get("inserted_at") or "")

                    usuario = nota.get("user") or nota.get("author") or {}
                    if isinstance(usuario, dict):
                        usr_nome = usuario.get("name") or ""
                    else:
                        usr_nome = str(usuario) if usuario else ""

                    tipo_tag = f'<span class="crm-note-tag">{tipo}</span>' if tipo else ""
                    meta_txt = " · ".join(filter(None, [
                        dt if dt != "—" else "",
                        usr_nome,
                    ]))

                    notes_html += (
                        f'<div class="crm-note-item">'
                        f'  {str(corpo)}'
                        f'  <div class="crm-note-meta">'
                        f'    {tipo_tag}'
                        f'    <span>{meta_txt}</span>'
                        f'  </div>'
                        f'</div>'
                    )

                if notes_html:
                    st.markdown(notes_html, unsafe_allow_html=True)
                else:
                    st.markdown(
                        '<span class="crm-none-tag">Atividades encontradas mas sem texto legível</span>',
                        unsafe_allow_html=True
                    )
            else:
                st.markdown(
                    '<span class="crm-none-tag">Nenhuma anotação encontrada neste card</span>',
                    unsafe_allow_html=True
                )
