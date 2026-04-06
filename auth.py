"""
auth.py — Autenticação com Supabase + Controle de Acesso CORBANs
"""

import streamlit as st
from supabase import create_client, Client
import re
from datetime import datetime
from auth_styles import apply_auth_styles
import base64
import os
from profile_settings import carregar_preferencias, TEMAS


# ============================================================================
# CONEXÃO COM SUPABASE
# ============================================================================
@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


# ============================================================================
# VALIDAÇÕES
# ============================================================================

def validar_email(email: str) -> bool:
    email = email.strip().lower()
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(padrao, email):
        return False
    try:
        username, dominio = email.split('@')
    except ValueError:
        return False
    # CORBANs podem ter qualquer e-mail — removemos restrição de domínio
    return True


def validar_senha(senha: str) -> tuple[bool, str]:
    if len(senha) < 6:
        return False, "A senha deve ter pelo menos 6 caracteres"
    if len(senha) > 72:
        return False, "A senha deve ter no máximo 72 caracteres"
    return True, ""


def extrair_nome_curto(nome_completo: str) -> str:
    palavras = nome_completo.strip().split()
    return palavras[0] if palavras else nome_completo.strip()


# ============================================================================
# CADASTRO
# ============================================================================

def fazer_cadastro(
    email: str,
    senha: str,
    nome: str,
    setor: str,
    tipo_solicitado: str = "corban",   # 'operador' | 'corban'
) -> tuple[bool, str]:
    try:
        supabase = get_supabase_client()
        nome_formatado = extrair_nome_curto(nome)
        response = supabase.auth.sign_up({
            "email": email,
            "password": senha,
            "options": {
                "data": {
                    "nome": nome_formatado,
                    "setor": setor,
                    "tipo_solicitado": tipo_solicitado,
                    "data_cadastro": datetime.now().isoformat()
                }
            }
        })

        if response.user:
            # Cria perfil pendente na nova tabela
            try:
                from user_management import create_user_profile
                create_user_profile(
                    user_id=response.user.id,
                    email=email,
                    nome=nome_formatado,
                    setor=setor,
                    tipo_solicitado=tipo_solicitado,
                )
            except Exception as e:
                print(f"[auth] Erro ao criar perfil: {e}")

            tipo_label = "Operador Interno" if tipo_solicitado == "operador" else "CORBAN Parceiro"
            return True, (
                f"✅ Solicitação enviada com sucesso! "
                f"Sua conta ({tipo_label}) está em análise. "
                f"Você será notificado assim que o acesso for liberado."
            )
        else:
            return False, "Erro ao criar conta. Tente novamente."

    except Exception as e:
        error_msg = str(e)
        if "already registered" in error_msg.lower() or "already exists" in error_msg.lower():
            return False, "Este email já está cadastrado."
        elif "invalid email" in error_msg.lower():
            return False, "Email inválido."
        else:
            return False, f"Erro: {error_msg}"


# ============================================================================
# LOGIN — agora verifica status do perfil
# ============================================================================

def fazer_login(email: str, senha: str) -> tuple[bool, str, dict]:
    try:
        supabase = get_supabase_client()
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": senha
        })

        if not response.user:
            return False, "Credenciais inválidas.", {}

        user_data = {
            "id":           response.user.id,
            "email":        response.user.email,
            "nome":         response.user.user_metadata.get("nome", "Usuário"),
            "setor":        response.user.user_metadata.get("setor", "N/A"),
            "access_token": response.session.access_token,
        }

        # ── Verificar perfil de acesso ────────────────────────────────────
        try:
            from user_management import get_user_profile, create_legacy_profile

            profile = get_user_profile(response.user.id)

            if not profile:
                # Usuário legado (existia antes do sistema de aprovação)
                # → cria perfil como operador aprovado automaticamente
                create_legacy_profile(
                    user_id=response.user.id,
                    email=response.user.email,
                    nome=user_data["nome"],
                    setor=user_data["setor"],
                )
                profile = {
                    "tipo":         "operador",
                    "status":       "aprovado",
                    "nome_empresa": "",
                    "cor_primaria": "#7C3AED",
                    "logo_url":     "",
                }

            status = profile.get("status", "pendente")

            # Bloqueia acesso se não aprovado
            if status == "pendente":
                supabase.auth.sign_out()
                return False, (
                    "⏳ Sua conta está aguardando aprovação. "
                    "Assim que for liberada, você receberá acesso. "
                    "Se tiver dúvidas, entre em contato com o suporte."
                ), {}

            elif status == "rejeitado":
                supabase.auth.sign_out()
                return False, (
                    "❌ Seu acesso foi negado. "
                    "Entre em contato com o administrador para mais informações."
                ), {}

            elif status == "suspenso":
                supabase.auth.sign_out()
                return False, (
                    "🔒 Sua conta está suspensa temporariamente. "
                    "Entre em contato com o suporte."
                ), {}

            # Enriquece user_data com dados do perfil
            user_data["tipo"]         = profile.get("tipo", "corban")
            user_data["status"]       = status
            user_data["nome_empresa"] = profile.get("nome_empresa", "")
            user_data["cor_primaria"] = profile.get("cor_primaria", "#7C3AED")
            user_data["logo_url"]     = profile.get("logo_url", "")
            user_data["profile_id"]   = profile.get("id", "")

        except Exception as e:
            print(f"[auth] Erro ao verificar perfil: {e}")
            # Fallback seguro — trata como operador se o módulo falhar
            user_data["tipo"]         = "operador"
            user_data["status"]       = "aprovado"
            user_data["nome_empresa"] = ""
            user_data["cor_primaria"] = "#7C3AED"
            user_data["logo_url"]     = ""

        # ── Tracking ─────────────────────────────────────────────────────
        try:
            from tracking import track_login
            track_login(user_data)
        except Exception:
            pass

        return True, "Login realizado com sucesso!", user_data

    except Exception as e:
        error_msg = str(e).lower()
        if "invalid login credentials" in error_msg or "invalid" in error_msg:
            return False, "Email ou senha incorretos.", {}
        else:
            return False, f"Erro ao fazer login: {str(e)}", {}


# ============================================================================
# LOGOUT
# ============================================================================

def fazer_logout():
    try:
        from tracking import track_logout
        track_logout()
    except Exception:
        pass
    try:
        get_supabase_client().auth.sign_out()
    except Exception:
        pass
    for key in ['usuario', 'autenticado', 'access_token']:
        if key in st.session_state:
            del st.session_state[key]


def verificar_sessao() -> bool:
    return ('autenticado' in st.session_state and st.session_state.autenticado)


# ============================================================================
# INTERFACE DE LOGIN/CADASTRO
# ============================================================================

def render_auth_page():
    if verificar_sessao():
        return True

    apply_auth_styles()

    st.markdown("""
    <style>
        .main .block-container { padding-top: 2rem !important; padding-bottom: 2rem !important; }
        [data-testid="stHorizontalBlock"] { align-items: stretch !important; }
        #login-img-wrapper {
            position: sticky; top: 2rem;
            display: flex; align-items: center; justify-content: center;
            width: 100%; height: 100%; min-height: 460px;
        }
        #login-img-wrapper img {
            width: 100%; max-width: 100%; height: auto; max-height: 100%;
            object-fit: contain; border-radius: 1rem; display: block;
        }
        /* Radio buttons de tipo de acesso */
        div[data-testid="stRadio"] > div { flex-direction: row; gap: 1rem; }
        div[data-testid="stRadio"] label {
            background: #f8f7ff; border: 2px solid #ede9fe;
            border-radius: .65rem; padding: .5rem 1rem;
            cursor: pointer; transition: all .15s;
        }
        div[data-testid="stRadio"] label:has(input:checked) {
            background: #ede9fe; border-color: #7c3aed;
        }
    </style>
    """, unsafe_allow_html=True)

    col_left, col_right = st.columns([1.2, 1.8], gap="large")

    # ── Imagem ────────────────────────────────────────────────────────────
    with col_left:
        def get_img_as_base64(file_path):
            with open(file_path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        try:
            img_base64 = get_img_as_base64("assets/login.png")
            img_src = f"data:image/png;base64,{img_base64}"
        except Exception:
            img_src = ""
        st.markdown(f'<div id="login-img-wrapper"><img src="{img_src}" alt="Logo StarCheck"></div>',
                    unsafe_allow_html=True)

    # ── Formulário ────────────────────────────────────────────────────────
    with col_right:
        st.markdown(
            "<h1 style='color:#111827;font-size:2rem;font-weight:800;margin:0 0 .5rem;letter-spacing:-.02em;'>"
            "Bem-vindo!</h1>",
            unsafe_allow_html=True
        )
        st.markdown(
            "<p style='color:#6B7280;font-size:1rem;margin:0 0 2rem;'>"
            "Entre com sua conta ou solicite acesso</p>",
            unsafe_allow_html=True
        )

        tab_login, tab_cadastro = st.tabs(["🔑 Entrar", "📝 Solicitar Acesso"])

        # ── TAB LOGIN ─────────────────────────────────────────────────────
        with tab_login:
            with st.form("form_login", clear_on_submit=False):
                email_login = st.text_input("📧 Email", placeholder="seuemail@exemplo.com", key="email_login")
                senha_login = st.text_input("🔒 Senha", type="password", placeholder="••••••••", key="senha_login")
                st.markdown("<div style='margin-top:1.5rem;'>", unsafe_allow_html=True)
                submit_login = st.form_submit_button("Entrar", use_container_width=True, type="primary")
                st.markdown("</div>", unsafe_allow_html=True)

                if submit_login:
                    if not email_login or not senha_login:
                        st.error("⚠️ Preencha todos os campos.")
                    else:
                        with st.spinner("Autenticando..."):
                            sucesso, mensagem, user_data = fazer_login(email_login, senha_login)
                            if sucesso:
                                st.session_state.autenticado    = True
                                st.session_state.usuario        = user_data
                                st.session_state.access_token   = user_data.get("access_token")
                                # Se for admin, marcar para redirecionamento direto ao painel admin
                                if user_data.get("tipo") == "admin":
                                    st.session_state["is_admin_redirect"] = True
                                st.success(mensagem)
                                st.rerun()
                            else:
                                st.error(f"❌ {mensagem}")

        # ── TAB CADASTRO ──────────────────────────────────────────────────
        with tab_cadastro:
            # Banner informativo
            st.info(
                "**Como funciona?**  \n"
                "Preencha o formulário abaixo. Sua solicitação será analisada pela equipe "
                "Starbank e você receberá o acesso em até 24h úteis.",
                icon="ℹ️"
            )

            with st.form("form_cadastro", clear_on_submit=True):
                nome_cadastro = st.text_input("👤 Nome Completo",        placeholder="João da Silva")
                email_cadastro = st.text_input("📧 Email",               placeholder="joao@suaempresa.com.br")
                setor_cadastro = st.text_input("🏢 Empresa / Setor",     placeholder="Ex: Star Crédito Ltda — Comercial")

                # ── Tipo de acesso ────────────────────────────────────────
                tipo_solicitado = st.radio(
                    "🎯 Tipo de acesso",
                    options=["corban", "operador"],
                    format_func=lambda x: "🤝 CORBAN / Parceiro Externo" if x == "corban" else "🏢 Operador Interno Starbank",
                    index=0,
                    help=(
                        "CORBAN: parceiro externo com acesso isolado e marca própria.  \n"
                        "Operador Interno: equipe Starbank com acesso completo."
                    ),
                    key="tipo_solicitado_radio"
                )

                col1, col2 = st.columns(2)
                with col1:
                    senha_cadastro = st.text_input("🔒 Senha", type="password", placeholder="Mínimo 6 caracteres")
                with col2:
                    senha_confirmacao = st.text_input("🔒 Confirmar Senha", type="password", placeholder="Digite novamente")

                # Aviso extra para CORBANs
                if tipo_solicitado == "corban":
                    st.caption("💡 Como CORBAN, você terá acesso exclusivo às suas análises com a sua marca.")

                st.markdown("<div style='margin-top:1.5rem;'>", unsafe_allow_html=True)
                submit_cadastro = st.form_submit_button("Enviar Solicitação", use_container_width=True, type="primary")
                st.markdown("</div>", unsafe_allow_html=True)

                if submit_cadastro:
                    erros = []
                    if not nome_cadastro or len(nome_cadastro.strip()) < 3:
                        erros.append("Nome deve ter pelo menos 3 caracteres")
                    if not email_cadastro:
                        erros.append("Email é obrigatório")
                    if not setor_cadastro or len(setor_cadastro.strip()) < 2:
                        erros.append("Empresa/Setor é obrigatório")
                    valido_senha, msg_senha = validar_senha(senha_cadastro)
                    if not valido_senha:
                        erros.append(msg_senha)
                    if senha_cadastro != senha_confirmacao:
                        erros.append("As senhas não coincidem")

                    if erros:
                        for erro in erros:
                            st.error(f"⚠️ {erro}")
                    else:
                        with st.spinner("Enviando solicitação..."):
                            sucesso, mensagem = fazer_cadastro(
                                email_cadastro,
                                senha_cadastro,
                                nome_cadastro.strip(),
                                setor_cadastro.strip(),
                                tipo_solicitado,
                            )
                            if sucesso:
                                st.success(mensagem)
                            else:
                                st.error(f"❌ {mensagem}")

        st.markdown(
            "<div style='text-align:center;margin-top:2rem;color:#9CA3AF;font-size:.85rem;'>"
            "<p style='margin:0;'>v3.0 · StarCheck · Sistema Inteligente de Análise de Holerites</p></div>",
            unsafe_allow_html=True
        )

    return False


# ============================================================================
# SIDEBAR — Info compacta do usuário (sem alterações no visual)
# ============================================================================

def render_user_info_sidebar():
    if verificar_sessao() and 'usuario' in st.session_state:
        user = st.session_state.usuario
        nome  = user.get('nome', 'Usuário')
        setor = user.get('setor', 'N/A')
        tipo  = user.get('tipo', 'corban')

        prefs       = carregar_preferencias()
        tema_config = prefs.get('tema_config', TEMAS.get('Roxo Padrão', {
            "gradient": "linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%)",
            "shadow":   "rgba(139, 92, 246, 0.25)"
        }))

        # CORBANs usam a cor da empresa como gradiente
        if tipo == "corban":
            cor = user.get("cor_primaria", "#7C3AED")
            tema_config = {
                "gradient": f"linear-gradient(135deg, {cor}cc, {cor})",
                "shadow":   "rgba(0,0,0,0.15)"
            }

        avatar = prefs.get('avatar', '👤')

        # Badge de tipo
        tipo_badge = {
            "admin":    ("🔑", "#4C1D95"),
            "operador": ("🏢", "#1D4ED8"),
            "corban":   ("🤝", "#059669"),
        }.get(tipo, ("👤", "#6B7280"))

        st.markdown(f"""
        <style>
            [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {{
                align-items: center !important; gap: 8px !important;
            }}
            [data-testid="stSidebar"] [data-testid="column"]:nth-child(2) button {{
                background-color: #ffffff !important; color: #444 !important;
                border: 1px solid #e0e0e0 !important; border-radius: 10px !important;
                height: 52px !important; width: 45px !important;
                padding: 0 !important; margin: 0 !important;
                display: flex !important; align-items: center !important;
                justify-content: center !important;
                box-shadow: 0 2px 5px rgba(0,0,0,.08) !important;
            }}
        </style>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns([0.8, 0.2], vertical_alignment="center")

        with col1:
            nome_empresa = user.get("nome_empresa", "")
            subtitulo = nome_empresa if (tipo == "corban" and nome_empresa) else setor
            st.markdown(f"""
            <div style="
                background: {tema_config['gradient']};
                border-radius: .75rem; padding: .75rem .85rem;
                box-shadow: 0 3px 10px {tema_config['shadow']};
                display: flex; align-items: center; gap: .65rem;
                height: 45px; margin-bottom: .9rem; box-sizing: border-box;
            ">
                <div style="width:32px;height:32px;background:rgba(255,255,255,.25);
                    border-radius:50%;display:flex;align-items:center;justify-content:center;
                    font-size:1.1rem;border:1.5px solid rgba(255,255,255,.3);flex-shrink:0;">
                    {avatar}
                </div>
                <div style="flex:1;min-width:0;">
                    <div style="font-weight:600;color:white;font-size:.85rem;line-height:1.2;
                        white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{nome}</div>
                    <div style="font-size:.7rem;color:rgba(255,255,255,.8);line-height:1.2;
                        white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                        {tipo_badge[0]} {subtitulo}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            if tipo != "corban":
                if st.button("✏️", key="btn_edit_profile"):
                    st.session_state['modo_atual'] = 'Perfil'
                    st.rerun()
