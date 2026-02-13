"""
auth.py — Sistema de Autenticação com Supabase (Design Moderno)
Login, cadastro e gerenciamento de sessão.

Dependências:
    pip install supabase

Configuração no .streamlit/secrets.toml:
    [supabase]
    url = "https://seu-projeto.supabase.co"
    key = "sua-anon-key-aqui"
"""

import streamlit as st
from supabase import create_client, Client
import re
from datetime import datetime
from auth_styles import apply_auth_styles
import streamlit as st
import base64
import os
from profile_settings import carregar_preferencias, TEMAS


# ============================================================================
# CONEXÃO COM SUPABASE
# ============================================================================

@st.cache_resource
def get_supabase_client() -> Client:
    """Retorna cliente do Supabase (singleton cacheado)."""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


# ============================================================================
# FUNÇÕES DE AUTENTICAÇÃO
# ============================================================================

def validar_email(email: str) -> bool:
    """Valida formato do email e domínio autorizado (.starbank ou .startec no username)."""
    email = email.strip().lower()
    # Valida formato básico do email
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(padrao, email):
        return False
    
    # Separa username e domínio
    username = email.split('@')[0]
    
    # Verifica se o username termina com .starbank ou .startec
    dominios_autorizados = ['.starbank', '.startec']
    return any(username.endswith(dominio) for dominio in dominios_autorizados)


def validar_senha(senha: str) -> tuple[bool, str]:
    """
    Valida força da senha.
    Retorna (válido, mensagem_erro).
    """
    if len(senha) < 6:
        return False, "A senha deve ter pelo menos 6 caracteres"
    if len(senha) > 72:
        return False, "A senha deve ter no máximo 72 caracteres"
    return True, ""


def extrair_nome_curto(nome_completo: str) -> str:
    """
    Extrai apenas o primeiro nome.
    Exemplo: "João da Silva Santos" -> "João"
    """
    palavras = nome_completo.strip().split()
    return palavras[0] if palavras else nome_completo.strip()


def fazer_cadastro(email: str, senha: str, nome: str, setor: str) -> tuple[bool, str]:
    """
    Cadastra um novo usuário no Supabase Auth e salva dados adicionais.
    Retorna (sucesso, mensagem).
    """
    try:
        supabase = get_supabase_client()
        
        # Extrai apenas primeiro e segundo nome
        nome_formatado = extrair_nome_curto(nome)
        
        # Cria usuário no Supabase Auth
        response = supabase.auth.sign_up({
            "email": email,
            "password": senha,
            "options": {
                "data": {
                    "nome": nome_formatado,
                    "setor": setor,
                    "data_cadastro": datetime.now().isoformat()
                }
            }
        })
        
        if response.user:
            return True, "Cadastro realizado com sucesso! Você já pode fazer login."
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


def fazer_login(email: str, senha: str) -> tuple[bool, str, dict]:
    """
    Autentica usuário no Supabase.
    Retorna (sucesso, mensagem, dados_usuario).
    """
    try:
        supabase = get_supabase_client()
        
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": senha
        })
        
        if response.user:
            user_data = {
                "id": response.user.id,
                "email": response.user.email,
                "nome": response.user.user_metadata.get("nome", "Usuário"),
                "setor": response.user.user_metadata.get("setor", "N/A"),
                "access_token": response.session.access_token
            }
            
            # 🆕 ATUALIZA/CRIA registro na tabela user_preferences com dados do usuário
            try:
                # Busca preferências existentes
                pref_response = supabase.table('user_preferences').select('*').eq('user_id', response.user.id).execute()
                
                if pref_response.data and len(pref_response.data) > 0:
                    # Atualiza registro existente mantendo tema e avatar, mas atualizando nome/setor/email
                    pref_existente = pref_response.data[0]
                    dados_atualizados = {
                        'user_id': response.user.id,
                        'tema': pref_existente.get('tema', 'Roxo Padrão'),
                        'avatar': pref_existente.get('avatar', '👤'),
                        'nome': user_data['nome'],
                        'setor': user_data['setor'],
                        'email': user_data['email']
                    }
                    supabase.table('user_preferences').upsert(dados_atualizados, on_conflict='user_id').execute()
                else:
                    # Cria novo registro com valores padrão
                    dados_novos = {
                        'user_id': response.user.id,
                        'tema': 'Roxo Padrão',
                        'avatar': '👤',
                        'nome': user_data['nome'],
                        'setor': user_data['setor'],
                        'email': user_data['email']
                    }
                    supabase.table('user_preferences').insert(dados_novos).execute()
            except Exception as e:
                # Se falhar ao atualizar preferências, apenas loga o erro mas continua o login
                print(f"Aviso: Não foi possível atualizar preferências: {str(e)}")
            
            return True, "Login realizado com sucesso!", user_data
        else:
            return False, "Credenciais inválidas.", {}
            
    except Exception as e:
        error_msg = str(e).lower()
        if "invalid login credentials" in error_msg or "invalid" in error_msg:
            return False, "Email ou senha incorretos.", {}
        else:
            return False, f"Erro ao fazer login: {str(e)}", {}


def fazer_logout():
    """Encerra a sessão do usuário."""
    try:
        supabase = get_supabase_client()
        supabase.auth.sign_out()
    except:
        pass
    
    # Limpa session state
    for key in ['usuario', 'autenticado', 'access_token']:
        if key in st.session_state:
            del st.session_state[key]


def verificar_sessao() -> bool:
    """
    Verifica se há uma sessão ativa.
    Retorna True se o usuário está autenticado.
    """
    if 'autenticado' in st.session_state and st.session_state.autenticado:
        return True
    return False


# ============================================================================
# INTERFACE DE LOGIN/CADASTRO - DESIGN MODERNO
# ============================================================================

def render_auth_page():
    """
    Renderiza a tela de autenticação moderna (login ou cadastro).
    Retorna True se o usuário está autenticado, False caso contrário.
    """
    
    # Verifica se já está autenticado
    if verificar_sessao():
        return True
    
    # Aplica estilos CSS
    apply_auth_styles()
    
    # Layout em duas colunas - estilo plataforma
    col_left, col_right = st.columns([1.2, 1.8], gap="large")
    
    # ══════════════════════════════════════════════════════════════════════
    # COLUNA ESQUERDA - Logo e Informações
    # ══════════════════════════════════════════════════════════════════════
    with col_left:
        # --- 1. Mantenha sua função de imagem ---
        def get_img_as_base64(file_path):
            with open(file_path, "rb") as f:
                data = f.read()
            return base64.b64encode(data).decode()

        # Ajuste o caminho se necessário
        image_path = "assets/LogoStarcheckWhite.png" 

        try:
            img_base64 = get_img_as_base64(image_path)
            img_src = f"data:image/png;base64,{img_base64}"
        except Exception:
            img_src = "" 

        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%); border-radius: 1.5rem; padding: 3rem 2rem; min-height: 600px; display: flex; flex-direction: column; justify-content: center; box-shadow: 0 20px 50px rgba(139, 92, 246, 0.3);'>
        <div style='text-align: center; color: white;'>
        <img src='{img_src}' style='width: 200px; margin-bottom: 2rem;'>
        <div style='margin-top: 3rem;'>
        <h2 style='font-size: 1.75rem; font-weight: 800; margin-bottom: 1rem; line-height: 1.2; color: white;'>StarCheck - Analisador de Holerite</h2>
        <p style='font-size: 1.05rem; opacity: 0.9; line-height: 1.6; margin-bottom: 2rem; color: white;'>Faça upload do seu holerite em PDF e obtenha análises detalhadas.</p>
        </div>
        <div style='background: rgba(255, 255, 255, 0.15); border-radius: 1rem; padding: 1.5rem; margin-top: 2rem; backdrop-filter: blur(10px);'>
        <div style='display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem;'>
        <div style='width: 40px; height: 40px; background: rgba(255, 255, 255, 0.2); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.25rem;'>⚡</div>
        <div style='text-align: left;'><div style='font-weight: 700; font-size: 0.95rem; color: white;'>Processamento Rápido</div><div style='font-size: 0.85rem; opacity: 0.8; color: white;'>Análise em segundos</div></div>
        </div>
        <div style='display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem;'>
        <div style='width: 40px; height: 40px; background: rgba(255, 255, 255, 0.2); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.25rem;'>💡</div>
        <div style='text-align: left;'><div style='font-weight: 700; font-size: 0.95rem; color: white;'>Insights Inteligentes</div><div style='font-size: 0.85rem; opacity: 0.8; color: white;'>Oportunidades identificadas</div></div>
        </div>
        <div style='display: flex; align-items: center; gap: 1rem;'>
        <div style='width: 40px; height: 40px; background: rgba(255, 255, 255, 0.2); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.25rem;'>🔒</div>
        <div style='text-align: left;'><div style='font-weight: 700; font-size: 0.95rem; color: white;'>100% Seguro</div><div style='font-size: 0.85rem; opacity: 0.8; color: white;'>Seus dados protegidos</div></div>
        </div>
        </div>
        </div>
        </div>
        """, unsafe_allow_html=True)
    
    # ══════════════════════════════════════════════════════════════════════
    # COLUNA DIREITA - Formulário de Login/Cadastro
    # ══════════════════════════════════════════════════════════════════════
    with col_right:
        # Título
        st.markdown("<h1 style='color: #111827; font-size: 2rem; font-weight: 800; margin: 0 0 0.5rem 0; letter-spacing: -0.02em;'>Bem-vindo!</h1>", unsafe_allow_html=True)
        st.markdown("<p style='color: #6B7280; font-size: 1rem; margin: 0 0 2rem 0;'>Entre com sua conta ou crie uma nova</p>", unsafe_allow_html=True)
        
        # Tabs: Login e Cadastro
        tab_login, tab_cadastro = st.tabs(["🔑 Entrar", "📝 Criar Conta"])
        
        # ──────────────────────────────────────────────────────────────────
        # TAB LOGIN
        # ──────────────────────────────────────────────────────────────────
        with tab_login:
            with st.form("form_login", clear_on_submit=False):
                email_login = st.text_input(
                    "📧 Email",
                    placeholder="seunome.starbank@gmail.com",
                    key="email_login"
                )
                senha_login = st.text_input(
                    "🔒 Senha",
                    type="password",
                    placeholder="••••••••",
                    key="senha_login"
                )
                
                st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
                submit_login = st.form_submit_button("Entrar", use_container_width=True, type="primary")
                
                if submit_login:
                    if not email_login or not senha_login:
                        st.error("⚠️ Preencha todos os campos.")
                    elif not validar_email(email_login):
                        st.error("⚠️ Email inválido. Use o formato: seunome.starbank@email.com ou seunome.startec@email.com")
                    else:
                        with st.spinner("Autenticando..."):
                            sucesso, mensagem, user_data = fazer_login(email_login, senha_login)
                            
                            if sucesso:
                                st.session_state.autenticado = True
                                st.session_state.usuario = user_data
                                st.session_state.access_token = user_data.get("access_token")
                                st.success(mensagem)
                                st.rerun()
                            else:
                                st.error(f"❌ {mensagem}")
        
        # ──────────────────────────────────────────────────────────────────
        # TAB CADASTRO
        # ──────────────────────────────────────────────────────────────────
        with tab_cadastro:
            with st.form("form_cadastro", clear_on_submit=True):
                nome_cadastro = st.text_input(
                    "👤 Nome Completo",
                    placeholder="João da Silva",
                    key="nome_cadastro"
                )
                email_cadastro = st.text_input(
                    "📧 Email",
                    placeholder="Seu email institucional",
                    key="email_cadastro"
                )
                setor_cadastro = st.text_input(
                    "🏢 Setor",
                    placeholder="Ex: Comercial, Crédito, TI...",
                    key="setor_cadastro"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    senha_cadastro = st.text_input(
                        "🔒 Senha",
                        type="password",
                        placeholder="Mínimo 6 caracteres",
                        key="senha_cadastro"
                    )
                with col2:
                    senha_confirmacao = st.text_input(
                        "🔒 Confirmar Senha",
                        type="password",
                        placeholder="Digite novamente",
                        key="senha_confirmacao"
                    )
                
                st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
                submit_cadastro = st.form_submit_button("Criar Conta", use_container_width=True, type="primary")
                
                if submit_cadastro:
                    erros = []
                    
                    if not nome_cadastro or len(nome_cadastro.strip()) < 3:
                        erros.append("Nome deve ter pelo menos 3 caracteres")
                    if not email_cadastro or not validar_email(email_cadastro):
                        erros.append("Email inválido. Use seu email institucional.")
                    if not setor_cadastro or len(setor_cadastro.strip()) < 2:
                        erros.append("Setor é obrigatório")
                    
                    valido_senha, msg_senha = validar_senha(senha_cadastro)
                    if not valido_senha:
                        erros.append(msg_senha)
                    
                    if senha_cadastro != senha_confirmacao:
                        erros.append("As senhas não coincidem")
                    
                    if erros:
                        for erro in erros:
                            st.error(f"⚠️ {erro}")
                    else:
                        with st.spinner("Criando sua conta..."):
                            sucesso, mensagem = fazer_cadastro(
                                email_cadastro,
                                senha_cadastro,
                                nome_cadastro.strip(),
                                setor_cadastro.strip()
                            )
                            
                            if sucesso:
                                st.success(f"✅ {mensagem}")
                                st.info("💡 Agora você pode fazer login na aba 'Entrar'.")
                            else:
                                st.error(f"❌ {mensagem}")
        
        # Rodapé
        st.markdown("<div style='text-align: center; margin-top: 2rem; color: #9CA3AF; font-size: 0.85rem;'><p style='margin: 0;'>v2.0 · StarCheck · Sistema de Análise de Holerites</p></div>", unsafe_allow_html=True)
    
    return False


# ============================================================================
# SIDEBAR - INFO COMPACTA DO USUÁRIO COM ÍCONE SVG VERMELHO
# ============================================================================

def render_user_info_sidebar():
    """Renderiza info do usuário e botão de edição branco perfeitamente alinhados."""
    if verificar_sessao() and 'usuario' in st.session_state:
        user = st.session_state.usuario
        nome = user.get('nome', 'Usuário')
        setor = user.get('setor', 'N/A')
        
        prefs = carregar_preferencias()
        tema_config = prefs.get('tema_config', TEMAS.get('Roxo Padrão', {
            "gradient": "linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%)",
            "shadow": "rgba(139, 92, 246, 0.25)"
        }))
        avatar = prefs.get('avatar', '👤')

        # CSS para alinhar o botão branco perfeitamente ao lado do card
        st.markdown(f"""
        <style>
            /* 1. Remove o espaço que o Streamlit coloca entre colunas */
            [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {{
                align-items: center !important;
                gap: 8px !important;
            }}

            /* 2. Estilização do Botão Branco - usando seletor que funciona no Streamlit */
            [data-testid="stSidebar"] [data-testid="column"]:nth-child(2) button {{
                background-color: #ffffff !important;
                color: #444 !important;
                border: 1px solid #e0e0e0 !important;
                border-radius: 10px !important;
                height: 52px !important;
                width: 45px !important;
                padding: 0 !important;
                margin: 0 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                box-shadow: 0 2px 5px rgba(0,0,0,0.08) !important;
                transition: all 0.2s ease !important;
            }}
            
            /* Hover do botão branco */
            [data-testid="stSidebar"] [data-testid="column"]:nth-child(2) button:hover {{
                background-color: #f8f8f8 !important;
                border-color: #d0d0d0 !important;
                box-shadow: 0 3px 8px rgba(0,0,0,0.12) !important;
            }}

            /* 3. Centralização absoluta do emoji de lápis */
            [data-testid="stSidebar"] [data-testid="column"]:nth-child(2) button p {{
                margin: 0 !important;
                padding: 0 !important;
                line-height: 1 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                font-size: 1.2rem !important;
                width: 100% !important;
            }}
            
            /* 4. Remove o padding superior interno que o Streamlit coloca no bloco do botão */
            [data-testid="stSidebar"] div[data-testid="column"]:nth-child(2) > div {{
                padding-top: 0px !important;
            }}
        </style>
        """, unsafe_allow_html=True)

        # Usamos colunas com alinhamento centralizado forçado
        col1, col2 = st.columns([0.8, 0.2], vertical_alignment="center")
        
        with col1:
            st.markdown(f"""
            <div style="
                background: {tema_config['gradient']}; 
                border-radius: 0.75rem; 
                padding: 0.75rem 0.85rem; 
                box-shadow: 0 3px 10px {tema_config['shadow']}; 
                display: flex; 
                align-items: center; 
                gap: 0.65rem;
                height: 45px;
                margin-bottom: 0.9rem;
                box-sizing: border-box;
            ">
                <div style="width: 32px; height: 32px; background: rgba(255, 255, 255, 0.25); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.1rem; border: 1.5px solid rgba(255, 255, 255, 0.3); flex-shrink: 0;">
                    {avatar}
                </div>
                <div style="flex: 1; min-width: 0;">
                    <div style="font-weight: 600; color: white; font-size: 0.85rem; line-height: 1.2; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{nome}</div>
                    <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.8); line-height: 1.2; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{setor}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            if st.button("✏️", key="btn_edit_profile"):
                st.session_state['modo_selecionado'] = 'Perfil'
                st.rerun()
