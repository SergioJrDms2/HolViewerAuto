"""
Módulo Admin - StarCheck
Gerenciamento de cartões via painel administrativo com Supabase.
"""

import streamlit as st
import hashlib
import pandas as pd
from auth import get_supabase_client

# ============================================================================
# CONFIGURAÇÕES DO ADMIN
# ============================================================================

ADMIN_EMAIL         = "admin.starbank@gmail.com"
ADMIN_PASSWORD_HASH = hashlib.sha256("123456".encode()).hexdigest()
TABLE               = "cartoes_config"

CATEGORIAS = {
    "nossos_produtos":       ("🏠 Nossos Produtos",           "Produtos/cartões da própria empresa", "#7C3AED"),
    "cartoes_conhecidos":    ("✅ Cartões que Compramos",      "Cartões de concorrentes que adquirimos", "#10B981"),
    "cartoes_nao_comprados": ("❌ Cartões que NÃO Compramos",  "Cartões que não são de interesse", "#EF4444"),
    "cartoes_desconhecidos": ("❓ Cartões Desconhecidos",      "Cartões ainda não classificados", "#F59E0B"),
}

DEFAULT_CARTOES = {
    "nossos_produtos": [
        "STARCARD", "ANTICIPAY", "STARBANK", "UASPREV"
    ],
    "cartoes_conhecidos": [
        "NIO", "DAYCOVAL", "BMG", "PAN", "MEUCASHCARD", "PINE",
        "BRADESCO", "SANTANDER / OLÉ", "BIG CARD", "DAYC", "IND",
        "PANAMERICANO", "MASTER", "CREDCESTA SAQUE"
    ],
    "cartoes_nao_comprados": [
        "CREDCESTA COMPRA", "QISTA", "PIX CARD", "C CONSIG", "CAPITAL",
        "MAXIMA", "FY DIGITAL", "CLICKBANK", "PIXCARD", "VEMCARD"
    ],
    "cartoes_desconhecidos": [
        "CREDIFIN - CARTAO SAQUE", "FY DIGITAL"
    ],
}


# ============================================================================
# SUPABASE — OPERAÇÕES
# ============================================================================

def _sb():
    return get_supabase_client()


def _seed_defaults_if_empty():
    """Popula a tabela com valores padrão se estiver vazia."""
    try:
        resp = _sb().table(TABLE).select("id").limit(1).execute()
        if resp.data:
            return
        rows = [
            {"nome": nome, "categoria": cat}
            for cat, nomes in DEFAULT_CARTOES.items()
            for nome in nomes
        ]
        _sb().table(TABLE).insert(rows).execute()
    except Exception as e:
        st.warning(f"Aviso ao inicializar banco: {e}")


@st.cache_data(ttl=30)
def load_cartoes(categoria: str) -> list:
    """Retorna lista de nomes de cartões de uma categoria (do Supabase)."""
    try:
        resp = (
            _sb()
            .table(TABLE)
            .select("nome")
            .eq("categoria", categoria)
            .order("nome")
            .execute()
        )
        return [r["nome"] for r in resp.data]
    except Exception:
        return DEFAULT_CARTOES.get(categoria, [])


def add_cartao(nome: str, categoria: str) -> tuple:
    nome = nome.strip().upper()
    if not nome:
        return False, "Nome não pode ser vazio."
    try:
        _sb().table(TABLE).insert({"nome": nome, "categoria": categoria}).execute()
        load_cartoes.clear()
        return True, f"Cartão **{nome}** adicionado!"
    except Exception as e:
        msg = str(e)
        if "duplicate" in msg.lower() or "unique" in msg.lower():
            return False, f"**{nome}** já existe nesta categoria."
        return False, f"Erro: {msg}"


def remove_cartao(nome: str, categoria: str) -> tuple:
    try:
        _sb().table(TABLE).delete().eq("nome", nome).eq("categoria", categoria).execute()
        load_cartoes.clear()
        return True, f"**{nome}** removido."
    except Exception as e:
        return False, f"Erro: {e}"


def move_cartao(nome: str, cat_origem: str, cat_destino: str) -> tuple:
    try:
        _sb().table(TABLE)\
            .update({"categoria": cat_destino})\
            .eq("nome", nome)\
            .eq("categoria", cat_origem)\
            .execute()
        load_cartoes.clear()
        return True, f"**{nome}** movido para {CATEGORIAS[cat_destino][0]}."
    except Exception as e:
        msg = str(e)
        if "duplicate" in msg.lower() or "unique" in msg.lower():
            return False, f"**{nome}** já existe em {CATEGORIAS[cat_destino][0]}."
        return False, f"Erro: {msg}"


# ============================================================================
# AUTENTICAÇÃO DO ADMIN
# ============================================================================

def check_admin_credentials(email: str, password: str) -> bool:
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    return email.strip().lower() == ADMIN_EMAIL and pw_hash == ADMIN_PASSWORD_HASH


def render_admin_login():
    st.markdown("""
        <style>
            .login-container {
                max-width: 500px;
                margin: 3rem auto;
                padding: 3rem;
                background: white;
                border-radius: 1.5rem;
                box-shadow: 0 10px 30px rgba(124, 58, 237, 0.1);
                border: 1px solid #E2E8F0;
            }
            .login-icon {
                font-size: 4rem;
                text-align: center;
                margin-bottom: 1.5rem;
            }
            .login-title {
                text-align: center;
                font-size: 2rem;
                font-weight: 800;
                background: linear-gradient(135deg, #7C3AED 0%, #4C1D95 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 0.5rem;
            }
            .login-subtitle {
                text-align: center;
                color: #64748B;
                margin-bottom: 2rem;
                font-size: 0.95rem;
            }
        </style>
    """, unsafe_allow_html=True)
    

    _, col, _ = st.columns([1, 2, 1])
    with col:
        with st.form("admin_login_form", clear_on_submit=False):
            email = st.text_input("📧 E-mail", placeholder="admin.starbank@gmail.com")
            senha = st.text_input("🔑 Senha", type="password")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.form_submit_button("🚀 Entrar", use_container_width=True):
                if check_admin_credentials(email, senha):
                    st.session_state["admin_logged_in"] = True
                    st.success("✅ Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("❌ E-mail ou senha incorretos.")


# ============================================================================
# PAINEL ADMIN PRINCIPAL
# ============================================================================

def render_admin_panel():
    # CSS específico para o painel admin
    st.markdown("""
        <style>
            .admin-header {
                background: linear-gradient(135deg, #7C3AED 0%, #4C1D95 100%);
                color: white;
                padding: 2rem;
                border-radius: 1rem;
                margin-bottom: 2rem;
            }
            .admin-title {
                font-size: 2.5rem;
                font-weight: 800;
                margin: 0;
                color: white;
            }
            .admin-subtitle {
                margin-top: 0.5rem;
                opacity: 0.9;
                font-size: 1rem;
            }
            .stat-card {
                background: linear-gradient(135deg, #F8FAFC 0%, #F1F5F9 100%);
                padding: 1.5rem;
                border-radius: 0.75rem;
                text-align: center;
                border: 1px solid #E2E8F0;
            }
            .stat-number {
                font-size: 2.5rem;
                font-weight: 800;
                color: #7C3AED;
            }
            .stat-label {
                color: #64748B;
                font-size: 0.9rem;
                margin-top: 0.25rem;
            }
            .add-card-section {
                background: linear-gradient(135deg, #F5F3FF 0%, #EDE9FE 100%);
                padding: 1.5rem;
                border-radius: 0.75rem;
                border: 2px dashed #A78BFA;
                margin-bottom: 1.5rem;
            }
            
            /* NOVA TABELA DE CARTÕES */
            .cartoes-table {
                width: 100%;
                border-collapse: separate;
                border-spacing: 0;
                margin: 1rem 0;
            }
            .cartoes-table thead {
                background: linear-gradient(135deg, #F8FAFC 0%, #F1F5F9 100%);
            }
            .cartoes-table th {
                padding: 1rem;
                text-align: left;
                font-weight: 600;
                color: #334155;
                border-bottom: 2px solid #E2E8F0;
                font-size: 0.9rem;
            }
            .cartoes-table tbody tr {
                border-bottom: 1px solid #F1F5F9;
                transition: all 0.2s ease;
            }
            .cartoes-table tbody tr:hover {
                background: #F8FAFC;
            }
            .cartoes-table td {
                padding: 0.75rem 1rem;
                color: #334155;
            }
            .cartao-nome {
                font-weight: 600;
                color: #1E293B;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }
            .cartao-badge {
                display: inline-block;
                padding: 0.25rem 0.75rem;
                border-radius: 1rem;
                font-size: 0.8rem;
                font-weight: 500;
                background: #F1F5F9;
                color: #64748B;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Header
    col_title, col_logout = st.columns([6, 1])

    
    with col_title:
        st.markdown("""
            <div class='admin-header'>
                <h1 class='admin-title'>Gerenciamento de Cartões</h1>
                <p class='admin-subtitle'>
                    Alterações são salvas no Supabase e valem para <strong>todos os usuários</strong> imediatamente.
                </p>
            </div>
        """, unsafe_allow_html=True)
    
    with col_logout:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state["admin_logged_in"] = False
            st.session_state["show_admin_page"] = False
            st.success("✅ Logout realizado!")
            st.rerun()

    # Estatísticas
    st.markdown("### 📊 Visão Geral")
    cols = st.columns(4, gap="medium")
    
    for idx, (cat_key, (cat_label, _, cat_color)) in enumerate(CATEGORIAS.items()):
        cartoes = load_cartoes(cat_key)
        with cols[idx]:
            st.markdown(f"""
                <div class='stat-card'>
                    <div class='stat-number' style='color: {cat_color}'>{len(cartoes)}</div>
                    <div class='stat-label'>{cat_label}</div>
                </div>
            """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

    # Tabs
    tab_labels = [info[0] for info in CATEGORIAS.values()]
    tabs = st.tabs(tab_labels)

    for (cat_key, (cat_label, cat_desc, cat_color)), tab in zip(CATEGORIAS.items(), tabs):
        with tab:
            st.markdown(f"<p style='color: #64748B; margin-bottom: 1.5rem;'>{cat_desc}</p>", unsafe_allow_html=True)
            
            cartoes = load_cartoes(cat_key)

            # Seção de adicionar
            st.markdown(f"""
                <div class='add-card-section'>
                    <h4 style='color: {cat_color}; margin: 0 0 1rem 0;'>➕ Adicionar Novo Cartão</h4>
                </div>
            """, unsafe_allow_html=True)
            
            col_input, col_btn = st.columns([3, 1], gap="small")
            
            with col_input:
                novo = st.text_input(
                    "Nome do cartão",
                    placeholder="Digite o nome (será convertido para MAIÚSCULAS)",
                    key=f"input_{cat_key}",
                    label_visibility="collapsed"
                )
            
            with col_btn:
                st.markdown("<div style='margin-top: 0px;'>", unsafe_allow_html=True)
                if st.button("➕ Adicionar", key=f"btn_add_{cat_key}", use_container_width=True):
                    if novo.strip():
                        ok, msg = add_cartao(novo, cat_key)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.warning("⚠️ Digite um nome válido!")
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("---")

            # Lista de cartões - NOVA VISUALIZAÇÃO
            if not cartoes:
                st.info(f"📭 Nenhum cartão nesta categoria ainda.")
                continue

            st.markdown(f"<h4 style='color: {cat_color}; margin-bottom: 1rem;'>📋 {len(cartoes)} Cartão(ões) Cadastrado(s)</h4>", unsafe_allow_html=True)
            
            outras = {k: v[0] for k, v in CATEGORIAS.items() if k != cat_key}

            # Criar DataFrame para exibição em tabela
            dados_tabela = []
            for cartao in cartoes:
                dados_tabela.append({
                    "Cartão": cartao,
                    "Mover para": "",
                    "Ações": ""
                })
            
            # Usando colunas para criar layout tabular personalizado
            for idx, cartao in enumerate(cartoes):
                # Container para cada linha
                with st.container():
                    c1, c2, c3, c4 = st.columns([3.5, 2.5, 1, 0.5], gap="small")
                    
                    with c1:
                        st.markdown(
                            f"""
                            <div style='
                                padding: 12px; 
                                background: {('#F8FAFC' if idx % 2 == 0 else '#FFFFFF')}; 
                                border-radius: 0.5rem 0 0 0.5rem;
                                border-left: 3px solid {cat_color};
                            '>
                                <span style='font-size: 1.2rem; margin-right: 8px;'>💳</span>
                                <span style='font-weight: 600; color: #1E293B;'>{cartao}</span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    
                    with c2:
                        st.markdown(f"<div style='padding-top: 4px;'>", unsafe_allow_html=True)
                        destino = st.selectbox(
                            "Destino",
                            options=list(outras.keys()),
                            format_func=lambda k: outras[k],
                            key=f"dest_{cat_key}_{cartao}_{idx}",
                            label_visibility="collapsed"
                        )
                        st.markdown("</div>", unsafe_allow_html=True)
                    
                    with c3:
                        st.markdown(f"<div style='padding-top: 4px;'>", unsafe_allow_html=True)
                        if st.button("🔄", key=f"mv_{cat_key}_{cartao}_{idx}", use_container_width=True, help="Mover cartão"):
                            ok, msg = move_cartao(cartao, cat_key, destino)
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                        st.markdown("</div>", unsafe_allow_html=True)
                    
                    with c4:
                        st.markdown(f"<div style='padding-top: 4px;'>", unsafe_allow_html=True)
                        confirm_key = f"confirm_del_{cat_key}_{cartao}_{idx}"
                        
                        if st.button(
                            "🗑️", 
                            key=f"del_{cat_key}_{cartao}_{idx}",
                            use_container_width=True,
                            help="Deletar cartão"
                        ):
                            if st.session_state.get(confirm_key, False):
                                ok, msg = remove_cartao(cartao, cat_key)
                                if ok:
                                    st.success(msg)
                                    st.session_state[confirm_key] = False
                                    st.rerun()
                                else:
                                    st.error(msg)
                            else:
                                st.session_state[confirm_key] = True
                                st.warning("⚠️ Clique novamente!")
                        st.markdown("</div>", unsafe_allow_html=True)
                    
                    # Linha horizontal sutil entre items
                    if idx < len(cartoes) - 1:
                        st.markdown("<div style='border-bottom: 1px solid #F1F5F9; margin: 0.25rem 0;'></div>", unsafe_allow_html=True)

    # Exportação
    st.markdown("<hr style='margin: 3rem 0 2rem'>", unsafe_allow_html=True)
    st.markdown("### 📥 Exportar Configurações")
    
    col1, col2 = st.columns(2, gap="medium")
    
    with col1:
        try:
            resp = _sb().table(TABLE)\
                .select("nome, categoria, criado_em")\
                .order("categoria")\
                .execute()
            df = pd.DataFrame(resp.data)
            if not df.empty:
                df.columns = ["Cartão", "Categoria", "Adicionado em"]
                
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📊 Exportar CSV",
                    data=csv,
                    file_name="cartoes_config.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        except Exception as e:
            st.error(f"Erro ao preparar exportação: {e}")
    
    with col2:
        with st.expander("Visualizar Todos os Dados"):
            try:
                resp = _sb().table(TABLE)\
                    .select("nome, categoria, criado_em")\
                    .order("categoria")\
                    .execute()
                df = pd.DataFrame(resp.data)
                if not df.empty:
                    df.columns = ["Cartão", "Categoria", "Adicionado em"]
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhum dado no banco.")
            except Exception as e:
                st.error(f"Erro ao carregar visão geral: {e}")


# ============================================================================
# PONTO DE ENTRADA
# ============================================================================

def init_db():
    """Garante que a tabela está populada. Chamado pelo main.py."""
    _seed_defaults_if_empty()


def render_admin_page():
    """Renderiza login ou painel conforme sessão."""
    _seed_defaults_if_empty()
    if not st.session_state.get("admin_logged_in", False):
        render_admin_login()
    else:
        render_admin_panel()
