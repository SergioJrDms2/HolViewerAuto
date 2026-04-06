"""
admin.py — Painel Administrativo StarCheck
Responsabilidade: Gestão de Usuários (CORBANs/Operadores/Admins) + Notificações
Dashboard completo com métricas, gráficos e exportação
"""

import streamlit as st
import hashlib
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from auth import get_supabase_client
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import io

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

ADMIN_EMAIL         = "admin.starbank@gmail.com"
ADMIN_PASSWORD_HASH = hashlib.sha256("8650234".encode()).hexdigest()


# ============================================================================
# HELPERS INTERNOS
# ============================================================================

def _sb():
    return get_supabase_client()


def _status_badge(status: str) -> str:
    badges = {
        "pendente":  ("🟡", "#92400e", "#fef3c7"),
        "aprovado":  ("🟢", "#14532d", "#dcfce7"),
        "rejeitado": ("🔴", "#991b1b", "#fee2e2"),
        "suspenso":  ("🔵", "#1e3a8a", "#dbeafe"),
    }
    ico, txt, bg = badges.get(status, ("⚪", "#374151", "#f3f4f6"))
    return (
        f'<span style="background:{bg};color:{txt};font-size:.72rem;font-weight:700;'
        f'padding:.2rem .65rem;border-radius:99px;white-space:nowrap;">'
        f'{ico} {status.upper()}</span>'
    )


def _tipo_badge(tipo: str) -> str:
    badges = {
        "admin":    ("🔑", "#4c1d95", "#ede9fe"),
        "operador": ("🏢", "#1e3a8a", "#dbeafe"),
        "corban":   ("🤝", "#065f46", "#dcfce7"),
    }
    ico, txt, bg = badges.get(tipo, ("❓", "#374151", "#f3f4f6"))
    return (
        f'<span style="background:{bg};color:{txt};font-size:.72rem;font-weight:700;'
        f'padding:.2rem .65rem;border-radius:99px;">'
        f'{ico} {tipo.upper()}</span>'
    )


# ============================================================================
# TROCAR SENHA — usa Admin API do Supabase (requer service_role key)
# ============================================================================

def _alterar_senha_usuario(user_id: str, nova_senha: str) -> tuple[bool, str]:
    """
    Altera a senha de qualquer usuário via Supabase Auth Admin API.
    REQUERIMENTO: st.secrets["supabase"]["service_role_key"] configurado.
    """
    if len(nova_senha) < 6:
        return False, "A senha deve ter pelo menos 6 caracteres."
    if len(nova_senha) > 72:
        return False, "A senha deve ter no máximo 72 caracteres."
    try:
        from supabase import create_client
        service_key = st.secrets["supabase"].get("service_role_key", "")
        if not service_key:
            return False, (
                "⚠️ service_role_key não configurada em secrets.toml. "
                "Adicione: [supabase] service_role_key = '...'"
            )
        url = st.secrets["supabase"]["url"]
        admin_client = create_client(url, service_key)
        admin_client.auth.admin.update_user_by_id(user_id, {"password": nova_senha})
        return True, "Senha alterada com sucesso!"
    except Exception as e:
        return False, f"Erro ao alterar senha: {e}"


# ============================================================================
# AUTENTICAÇÃO ADMIN
# ============================================================================

def check_admin_credentials(email: str, password: str) -> bool:
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    return email.strip().lower() == ADMIN_EMAIL and pw_hash == ADMIN_PASSWORD_HASH


def render_admin_login():
    st.markdown("""
    <style>
    .main .block-container { max-width: 460px !important; margin: 4rem auto !important; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center;margin-bottom:2rem;">
        <div style="font-size:2.5rem;">🔐</div>
        <h2 style="margin:.5rem 0 .25rem;color:#111827;">Painel Administrativo</h2>
        <p style="color:#6b7280;font-size:.9rem;">Acesso restrito — equipe StarCheck</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("admin_login_form", clear_on_submit=False):
        email = st.text_input("📧 E-mail", placeholder="admin.starbank@gmail.com")
        senha = st.text_input("🔑 Senha", type="password", placeholder="••••••••")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("Entrar", use_container_width=True, type="primary"):
            if check_admin_credentials(email, senha):
                st.session_state["admin_logged_in"] = True
                st.success("✅ Acesso autorizado!")
                st.rerun()
            else:
                st.error("❌ E-mail ou senha incorretos.")


# ============================================================================
# PAINEL DE USUÁRIOS
# ============================================================================

def _calcular_tendencias(todos: list) -> dict:
    """Calcula tendências comparando com período anterior (7 dias)."""
    hoje = datetime.now()
    semana_atual = hoje - timedelta(days=7)
    semana_anterior = semana_atual - timedelta(days=7)
    
    novos_atual = sum(1 for u in todos if u.get("created_at") and 
                      semana_atual <= datetime.fromisoformat(str(u.get("created_at")).replace("Z", "+00:00").replace("+00:00", "")) <= hoje)
    novos_anterior = sum(1 for u in todos if u.get("created_at") and 
                         semana_anterior <= datetime.fromisoformat(str(u.get("created_at")).replace("Z", "+00:00").replace("+00:00", "")) < semana_atual)
    
    tendencia = ((novos_atual - novos_anterior) / max(novos_anterior, 1)) * 100 if novos_anterior else 0
    return {"novos": novos_atual, "tendencia": round(tendencia, 1)}


def _render_kpi_card(col, titulo: str, valor: int, cor: str, icone: str, subtitulo: str = ""):
    """Renderiza um card de KPI estilizado."""
    with col:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, {cor}15 0%, {cor}08 100%);
            border-left: 4px solid {cor};
            border-radius: 12px;
            padding: 1.2rem 1rem;
            margin-bottom: 1rem;
        ">
            <div style="font-size: 2rem; margin-bottom: 0.3rem;">{icone}</div>
            <div style="font-size: 2rem; font-weight: 700; color: #1f2937;">{valor}</div>
            <div style="font-size: 0.85rem; font-weight: 600; color: #6b7280; text-transform: uppercase;">{titulo}</div>
            {f'<div style="font-size: 0.75rem; color: #9ca3af; margin-top: 0.3rem;">{subtitulo}</div>' if subtitulo else ''}
        </div>
        """, unsafe_allow_html=True)


def _render_dashboard(todos: list):
    """Renderiza dashboard completo com gráficos e métricas."""
    
    # ── Métricas Principais ───────────────────────────────────────────
    n_total = len(todos)
    n_pend = sum(1 for u in todos if u.get("status") == "pendente")
    n_aprov = sum(1 for u in todos if u.get("status") == "aprovado")
    n_rej = sum(1 for u in todos if u.get("status") == "rejeitado")
    n_susp = sum(1 for u in todos if u.get("status") == "suspenso")
    n_corban = sum(1 for u in todos if u.get("tipo") == "corban" and u.get("status") == "aprovado")
    n_op = sum(1 for u in todos if u.get("tipo") == "operador" and u.get("status") == "aprovado")
    n_admin = sum(1 for u in todos if u.get("tipo") == "admin" and u.get("status") == "aprovado")
    
    # Tendências
    tendencias = _calcular_tendencias(todos)
    
    # Cards de KPI
    c1, c2, c3, c4, c5 = st.columns(5)
    _render_kpi_card(c1, "Total Usuários", n_total, "#7C3AED", "👥", f"+{tendencias['novos']} novos (7d)")
    _render_kpi_card(c2, "Pendentes", n_pend, "#F59E0B", "🟡", "Aguardando aprovação")
    _render_kpi_card(c3, "Aprovados", n_aprov, "#10B981", "✅", f"{n_corban} CORBANs, {n_op} Ops")
    _render_kpi_card(c4, "Rejeitados", n_rej, "#EF4444", "❌", "Acesso negado")
    _render_kpi_card(c5, "Suspensos", n_susp, "#3B82F6", "🔵", "Temporariamente bloqueados")
    
    # ── Gráficos ─────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    
    g1, g2 = st.columns(2)
    
    with g1:
        # Gráfico de Distribuição por Status
        status_counts = Counter(u.get("status", "desconhecido") for u in todos)
        cores_status = {"aprovado": "#10B981", "pendente": "#F59E0B", 
                       "rejeitado": "#EF4444", "suspenso": "#3B82F6"}
        
        fig_status = go.Figure(data=[go.Pie(
            labels=list(status_counts.keys()),
            values=list(status_counts.values()),
            hole=.4,
            marker_colors=[cores_status.get(s, "#9CA3AF") for s in status_counts.keys()],
            textinfo='label+percent',
            textfont_size=11,
        )])
        fig_status.update_layout(
            title="📊 Distribuição por Status",
            showlegend=False,
            margin=dict(t=40, b=20, l=20, r=20),
            height=280,
        )
        st.plotly_chart(fig_status, use_container_width=True)
    
    with g2:
        # Gráfico de Distribuição por Tipo
        tipo_counts = Counter(u.get("tipo", "desconhecido") for u in todos if u.get("status") == "aprovado")
        
        fig_tipo = go.Figure(data=[go.Bar(
            x=[t.upper() for t in tipo_counts.keys()],
            y=list(tipo_counts.values()),
            marker_color=["#7C3AED", "#3B82F6", "#10B981"],
            text=list(tipo_counts.values()),
            textposition='auto',
        )])
        fig_tipo.update_layout(
            title="👤 Usuários Ativos por Tipo",
            xaxis_title="",
            yaxis_title="Quantidade",
            margin=dict(t=40, b=30, l=40, r=20),
            height=280,
            plot_bgcolor='rgba(0,0,0,0)',
        )
        st.plotly_chart(fig_tipo, use_container_width=True)
    
    # ── Atividade Recente & Exportação ──────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    
    a1, a2 = st.columns([2, 1])
    
    with a1:
        st.markdown("##### 📈 Atividade Recente (últimos 7 dias)")
        
        # Simular dados de atividade (cadastros por dia)
        hoje = datetime.now()
        dias = [(hoje - timedelta(days=i)).strftime("%d/%m") for i in range(6, -1, -1)]
        
        # Contar cadastros por dia
        cadastros_por_dia = []
        for i in range(7):
            dia_ref = hoje - timedelta(days=i)
            count = sum(1 for u in todos if u.get("created_at") and 
                       datetime.fromisoformat(str(u.get("created_at")).replace("Z", "+00:00").replace("+00:00", "")).date() == dia_ref.date())
            cadastros_por_dia.append(count)
        cadastros_por_dia.reverse()
        
        fig_ativ = go.Figure(data=[go.Scatter(
            x=dias,
            y=cadastros_por_dia,
            mode='lines+markers',
            line=dict(color='#7C3AED', width=3),
            marker=dict(size=8, color='#7C3AED'),
            fill='tozeroy',
            fillcolor='rgba(124, 58, 237, 0.1)',
        )])
        fig_ativ.update_layout(
            margin=dict(t=20, b=30, l=40, r=20),
            height=200,
            xaxis_title="",
            yaxis_title="Cadastros",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
        )
        st.plotly_chart(fig_ativ, use_container_width=True)
    
    with a2:
        st.markdown("##### 📤 Exportar Dados")
        
        # Preparar DataFrame
        df_export = pd.DataFrame([
            {
                "Nome": u.get("nome", ""),
                "Email": u.get("email", ""),
                "Tipo": u.get("tipo", ""),
                "Status": u.get("status", ""),
                "Setor": u.get("setor", ""),
                "Empresa": u.get("nome_empresa", ""),
                "Criado em": str(u.get("created_at", ""))[:10],
            }
            for u in todos
        ])
        
        # Exportar Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Usuários')
        
        st.download_button(
            "📊 Baixar Excel",
            buffer.getvalue(),
            "usuarios_starcheck.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        
        # Exportar CSV
        csv = df_export.to_csv(index=False)
        st.download_button(
            "📄 Baixar CSV",
            csv,
            "usuarios_starcheck.csv",
            mime="text/csv",
            use_container_width=True,
        )


def render_usuarios_panel():
    from user_management import (
        get_all_users,
        approve_user, reject_user, suspend_user, reactivate_user,
        get_notifications, mark_all_read, update_corban_config,
        get_pending_count, get_unread_count,
    )

    # ── KPIs ─────────────────────────────────────────────────────────────
    todos    = get_all_users()
    n_pend   = sum(1 for u in todos if u.get("status") == "pendente")
    n_aprov  = sum(1 for u in todos if u.get("status") == "aprovado")
    n_corban = sum(1 for u in todos if u.get("tipo") == "corban"    and u.get("status") == "aprovado")
    n_op     = sum(1 for u in todos if u.get("tipo") == "operador"  and u.get("status") == "aprovado")

    # ── Dashboard Completo ───────────────────────────────────────────────
    _render_dashboard(todos)

    st.divider()

    # ── Sub-abas estilizadas ─────────────────────────────────────────────
    # Customizar aparência das tabs
    tab_style = """
    <style>
    div[data-testid="stHorizontalBlock"] div[data-testid="stTabs"] {
        background: linear-gradient(90deg, #f8fafc 0%, #f1f5f9 100%);
        border-radius: 12px;
        padding: 0.5rem;
        margin-bottom: 1rem;
    }
    div[data-testid="stTabs"] button[role="tab"] {
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        padding: 0.85rem 1.75rem !important;
        border-radius: 10px !important;
        margin: 0 0.25rem !important;
        border: none !important;
        background: transparent !important;
        color: #64748b !important;
        transition: all 0.3s ease !important;
    }
    div[data-testid="stTabs"] button[role="tab"]:hover {
        background: rgba(102, 126, 234, 0.1) !important;
        color: #667eea !important;
    }
    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4) !important;
    }
    </style>
    """
    st.markdown(tab_style, unsafe_allow_html=True)
    
    # Tabs com badges de contagem
    tab_pendentes = f"Pendentes ({n_pend})" if n_pend > 0 else "Pendentes"
    tab_notifs = "Notificações"
    
    sub_pend, sub_todos, sub_notif = st.tabs([
        tab_pendentes,
        "Todos os Usuários",
        tab_notifs,
    ])

    # =========================================================================
    # ABA — PENDENTES
    # =========================================================================
    with sub_pend:
        pendentes = [u for u in todos if u.get("status") == "pendente"]
        
        # Header da aba com contador
        if n_pend > 0:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); 
                border-left: 4px solid #f59e0b; border-radius: 12px; padding: 1rem 1.25rem; margin-bottom: 1.5rem;">
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <span style="font-size: 1.5rem;">🟡</span>
                    <div>
                        <div style="font-weight: 700; color: #92400e; font-size: 1.1rem;">
                            {n_pend} solicitação{'' if n_pend == 1 else 'ões'} pendente{'' if n_pend == 1 else 's'}
                        </div>
                        <div style="font-size: 0.85rem; color: #a16207;">
                            Aguardando sua revisão e aprovação
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%); 
                border-left: 4px solid #10b981; border-radius: 12px; padding: 1rem 1.25rem; margin-bottom: 1.5rem;">
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <span style="font-size: 1.5rem;">✅</span>
                    <div>
                        <div style="font-weight: 700; color: #14532d; font-size: 1.1rem;">
                            Fila limpa!
                        </div>
                        <div style="font-size: 0.85rem; color: #166534;">
                            Nenhuma solicitação pendente no momento
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        for u in pendentes:
            with st.container():
                # Card moderno para cada pendente
                tipo_icon = "🤝" if u.get("tipo") == "corban" else "🏢" if u.get("tipo") == "operador" else "🔑"
                tipo_cor = "#7c3aed" if u.get("tipo") == "corban" else "#3b82f6" if u.get("tipo") == "operador" else "#10b981"
                
                st.markdown(f"""
                <div style="background: white; border-radius: 16px; padding: 1.25rem; 
                    box-shadow: 0 2px 12px rgba(0,0,0,0.06); border: 1px solid #e5e7eb; margin-bottom: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem;">
                        <div style="display: flex; gap: 1rem; flex: 1;">
                            <div style="width: 50px; height: 50px; background: {tipo_cor}20; border-radius: 12px;
                                display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                                <span style="font-size: 1.5rem;">{tipo_icon}</span>
                            </div>
                            <div style="flex: 1;">
                                <div style="font-weight: 700; color: #1f2937; font-size: 1.05rem; margin-bottom: 0.25rem;">
                                    {u.get('nome', '—')}
                                </div>
                                <div style="font-size: 0.9rem; color: #6b7280; margin-bottom: 0.5rem;">
                                    {u.get('email', '—')}
                                </div>
                                <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                                    <span style="background: #f3f4f6; color: #374151; padding: 0.25rem 0.75rem; 
                                        border-radius: 99px; font-size: 0.75rem; font-weight: 500;">
                                        {u.get('setor', '—')}
                                    </span>
                                    <span style="background: {tipo_cor}20; color: {tipo_cor}; padding: 0.25rem 0.75rem; 
                                        border-radius: 99px; font-size: 0.75rem; font-weight: 600;">
                                        {u.get('tipo', '—').upper()}
                                    </span>
                                    <span style="background: #fef3c7; color: #92400e; padding: 0.25rem 0.75rem; 
                                        border-radius: 99px; font-size: 0.75rem; font-weight: 500;">
                                        {str(u.get('created_at', ''))[:10]}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Ações no formato Streamlit (abaixo do card)
                uid = u.get("user_id", "")
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    tipo_aprovacao = st.selectbox(
                        "Tipo",
                        options=["corban", "operador", "admin"],
                        index=0 if u.get("tipo") == "corban" else 1,
                        key=f"tipo_sel_{uid}",
                        format_func=lambda x: {"corban": "🤝 CORBAN", "operador": "🏢 Operador", "admin": "🔑 Admin"}[x],
                        label_visibility="collapsed",
                    )
                
                with col2:
                    if st.button("✅ Aprovar", key=f"aprov_{uid}", use_container_width=True, type="primary"):
                        nome_emp = ""
                        cor_prim = "#7C3AED"
                        if tipo_aprovacao == "corban":
                            nome_emp = st.session_state.get(f"nemp_{uid}", "")
                            cor_prim = st.session_state.get(f"cor_{uid}", "#7C3AED")
                        
                        ok = approve_user(
                            user_id=uid, tipo=tipo_aprovacao,
                            admin_user_id=None,
                            nome_empresa=nome_emp,
                            cor_primaria=cor_prim,
                            notas="",
                        )
                        if ok:
                            st.success(f"✅ {u.get('nome', '')} aprovado!")
                            st.rerun()
                        else:
                            st.error("Erro ao aprovar.")
                
                with col3:
                    if st.button("❌ Rejeitar", key=f"rej_{uid}", use_container_width=True):
                        ok = reject_user(uid, admin_user_id=None, notas="")
                        if ok:
                            st.warning(f"{u.get('nome', '')} rejeitado.")
                            st.rerun()
                
                # Campos adicionais para CORBAN
                if tipo_aprovacao == "corban":
                    col_emp, col_cor = st.columns(2)
                    with col_emp:
                        st.text_input("Nome da empresa", key=f"nemp_{uid}", placeholder="ex: Star Crédito Ltda")
                    with col_cor:
                        st.color_picker("Cor da marca", "#7C3AED", key=f"cor_{uid}")
                
                st.markdown("<br>", unsafe_allow_html=True)

    # =========================================================================
    # ABA — TODOS OS USUÁRIOS
    # =========================================================================
    with sub_todos:
        # Header estilizado
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #ede9fe 0%, #ddd6fe 100%); 
            border-left: 4px solid #7c3aed; border-radius: 12px; padding: 1.25rem; margin-bottom: 1.5rem;">
            <div style="display: flex; align-items: center; gap: 0.75rem;">
                <span style="font-size: 1.75rem;">👥</span>
                <div>
                    <div style="font-weight: 700; color: #4c1d95; font-size: 1.15rem;">
                        Gerenciamento de Usuários
                    </div>
                    <div style="font-size: 0.9rem; color: #6d28d9;">
                        {len(todos)} usuários cadastrados no sistema
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Filtros modernos em container
        filtros_container = st.container()
        with filtros_container:
            col_f1, col_f2, col_f3, col_f4 = st.columns([1.5, 1.5, 2.5, 1])
            
            with col_f1:
                filtro_status = st.selectbox(
                    "📊 Status",
                    ["todos", "aprovado", "pendente", "rejeitado", "suspenso"],
                    key="ftodo_st",
                    format_func=lambda x: {"todos": "Todos", "aprovado": "✅ Aprovados", 
                                          "pendente": "🟡 Pendentes", "rejeitado": "❌ Rejeitados",
                                          "suspenso": "🔵 Suspensos"}[x],
                )
            
            with col_f2:
                filtro_tipo = st.selectbox(
                    "👤 Tipo",
                    ["todos", "corban", "operador", "admin"],
                    key="ftodo_tp",
                    format_func=lambda x: {"todos": "Todos", "corban": "🤝 CORBANs", 
                                          "operador": "🏢 Operadores", "admin": "🔑 Admins"}[x],
                )
            
            with col_f3:
                busca = st.text_input("🔍 Buscar", key="ftodo_bsc", 
                                     placeholder="Nome ou email do usuário...")
            
            with col_f4:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if st.button("🔄 Limpar", use_container_width=True, type="secondary"):
                    st.session_state["ftodo_st"] = "todos"
                    st.session_state["ftodo_tp"] = "todos"
                    st.session_state["ftodo_bsc"] = ""
                    st.rerun()

        # Contador de resultados
        filtrados = [
            u for u in todos
            if (filtro_status == "todos" or u.get("status") == filtro_status)
            and (filtro_tipo  == "todos" or u.get("tipo")   == filtro_tipo)
            and (not busca or busca.lower() in (u.get("nome", "") + u.get("email", "")).lower())
        ]
        
        # Badge de contagem - construir texto dinamicamente
        user_text = f"usuário{'s' if len(filtrados) != 1 else ''} encontrado{'s' if len(filtrados) != 1 else ''}"
        if len(filtrados) != len(todos):
            user_text += f" de {len(todos)} total"
        
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 0.5rem; margin: 1rem 0;">
            <span style="background: #7c3aed; color: white; padding: 0.35rem 0.85rem; 
                border-radius: 99px; font-size: 0.8rem; font-weight: 600;">
                {len(filtrados)}
            </span>
            <span style="color: #6b7280; font-size: 0.9rem;">
                {user_text}
            </span>
        </div>
        """, unsafe_allow_html=True)

        # Lista de usuários em cards modernos
        for u in filtrados:
            uid    = u.get("user_id", "")
            nome   = u.get("nome", "—")
            email  = u.get("email", "—")
            tipo   = u.get("tipo", "—")
            status = u.get("status", "—")
            criado = str(u.get("created_at", ""))[:10]
            ne     = u.get("nome_empresa", "")
            cor    = u.get("cor_primaria", "#7C3AED")
            
            # Cores e ícones
            status_config = {
                "aprovado": ("#10b981", "#dcfce7", "🟢"),
                "pendente": ("#f59e0b", "#fef3c7", "🟡"),
                "rejeitado": ("#ef4444", "#fee2e2", "🔴"),
                "suspenso": ("#3b82f6", "#dbeafe", "🔵"),
            }
            status_cor, status_bg, status_icon = status_config.get(status, ("#6b7280", "#f3f4f6", "⚪"))
            
            tipo_icons = {"corban": "🤝", "operador": "🏢", "admin": "🔑"}
            tipo_icon = tipo_icons.get(tipo, "👤")
            
            # Card moderno em expander
            with st.expander(
                f"{tipo_icon} {nome}",
                expanded=False,
            ):
                # Construir HTML do card dinamicamente
                card_html = f'''<div style="background: #fafafa; border-radius: 12px; padding: 1.25rem; margin-bottom: 1rem;">
                    <div style="display: flex; gap: 1rem; align-items: flex-start;">
                        <div style="width: 64px; height: 64px; background: linear-gradient(135deg, {cor}30 0%, {cor}10 100%); 
                            border-radius: 16px; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                            <span style="font-size: 2rem;">{tipo_icon}</span>
                        </div>
                        <div style="flex: 1;">
                            <div style="font-weight: 700; color: #1f2937; font-size: 1.1rem; margin-bottom: 0.35rem;">
                                {nome}
                            </div>
                            <div style="font-size: 0.9rem; color: #6b7280; margin-bottom: 0.6rem;">
                                {email}
                            </div>
                            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                                <span style="background: {status_bg}; color: {status_cor}; padding: 0.3rem 0.9rem; 
                                    border-radius: 99px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase;">
                                    {status_icon} {status}
                                </span>
                                <span style="background: #ede9fe; color: #6d28d9; padding: 0.3rem 0.9rem; 
                                    border-radius: 99px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase;">
                                    {tipo.upper()}
                                </span>
                                <span style="background: #f3f4f6; color: #4b5563; padding: 0.3rem 0.9rem; 
                                    border-radius: 99px; font-size: 0.75rem; font-weight: 500;">
                                    📅 {criado}
                                </span>
                            </div>
                        </div>
                    </div>'''
                
                # Adicionar empresa se existir
                if ne:
                    card_html += f'''<div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #e5e7eb;">
                        <div style="display: flex; align-items: center; gap: 0.75rem;">
                            <span style="font-size: 0.85rem; color: #6b7280;"><b>Empresa:</b> {ne}</span>
                            <div style="width: 24px; height: 24px; background: {cor}; border-radius: 6px; 
                                border: 2px solid #e5e7eb; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"></div>
                        </div>
                    </div>'''
                
                # Adicionar setor se existir
                if u.get('setor'):
                    card_html += f'''<div style="margin-top: 0.75rem; font-size: 0.85rem; color: #6b7280;">
                        <b>Setor:</b> {u.get('setor', '—')}
                    </div>'''
                
                # Adicionar notas se existirem
                if u.get('notas_admin'):
                    card_html += f'''<div style="margin-top: 0.75rem; padding: 0.5rem; background: #f3f4f6; border-radius: 8px;">
                        <span style="font-size: 0.8rem; color: #4b5563;">📝 {u.get('notas_admin')}</span>
                    </div>'''
                
                # Fechar div principal
                card_html += '</div>'
                
                st.markdown(card_html, unsafe_allow_html=True)
                
                # Ações em grid moderno
                acao_cols = st.columns([1, 1, 1])
                
                with acao_cols[0]:
                    if status == "aprovado":
                        if st.button("🔒 Suspender", key=f"susp_{uid}", use_container_width=True):
                            if suspend_user(uid):
                                st.warning(f"{nome} suspenso.")
                                st.rerun()

                    elif status == "suspenso":
                        if st.button("🔓 Reativar", key=f"reat_{uid}", use_container_width=True, type="primary"):
                            if reactivate_user(uid):
                                st.success(f"{nome} reativado.")
                                st.rerun()

                    elif status in ("pendente", "rejeitado"):
                        tipo_novo = st.selectbox(
                            "Tipo", ["corban", "operador", "admin"],
                            key=f"tnovo_{uid}",
                            format_func=lambda x: {"corban": "🤝 CORBAN", "operador": "🏢 Operador", "admin": "🔑 Admin"}[x],
                        )
                        ne_edit, cor_edit = ne, cor
                        if tipo_novo == "corban":
                            ne_edit = st.text_input("Empresa", value=ne, key=f"ne_edit_{uid}")
                            cor_edit = st.color_picker("Cor", cor if cor.startswith("#") else "#7C3AED", key=f"cor_edit_{uid}")
                        if st.button("✅ Aprovar", key=f"aprov2_{uid}", use_container_width=True, type="primary"):
                            if approve_user(uid, tipo_novo, None, ne_edit, cor_edit):
                                st.success(f"{nome} aprovado!")
                                st.rerun()
                
                with acao_cols[1]:
                    if status == "aprovado" and tipo == "corban":
                        st.markdown("<div style='font-size: 0.85rem; color: #6b7280; margin-bottom: 0.5rem;'><b>⚙️ White-label</b></div>", unsafe_allow_html=True)
                        ne_up = st.text_input("Empresa", value=ne, key=f"ne_up_{uid}", label_visibility="collapsed")
                        cor_up = st.color_picker("Cor", cor if cor.startswith("#") else "#7C3AED", key=f"cu_{uid}")
                        if st.button("💾 Salvar", key=f"sv_{uid}", use_container_width=True):
                            if update_corban_config(uid, ne_up, cor_up, ""):
                                st.success("Salvo!")
                                st.rerun()
                
                with acao_cols[2]:
                    st.markdown("<div style='font-size: 0.85rem; color: #6b7280; margin-bottom: 0.5rem;'><b>🔑 Senha</b></div>", unsafe_allow_html=True)
                    nova_pw = st.text_input("Nova", type="password", placeholder="6+ chars", key=f"pw1_{uid}")
                    conf_pw = st.text_input("Confirmar", type="password", placeholder="Repita", key=f"pw2_{uid}")
                    if st.button("🔄 Alterar", key=f"pw_btn_{uid}", use_container_width=True):
                        if not nova_pw:
                            st.warning("Digite a senha.")
                        elif nova_pw != conf_pw:
                            st.error("Não coincidem.")
                        else:
                            ok, msg = _alterar_senha_usuario(uid, nova_pw)
                            if ok:
                                st.success("✅ Alterada!")
                            else:
                                st.error(f"❌ {msg}")
            
            # Divisor sutil entre cards
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # =========================================================================
    # ABA — NOTIFICAÇÕES
    # =========================================================================
    with sub_notif:
        notifs = get_notifications(40)
        nao_lidas = sum(1 for n in notifs if not n.get("lida"))
        
        # Header moderno
        if nao_lidas > 0:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); 
                border-left: 4px solid #f59e0b; border-radius: 12px; padding: 1rem 1.25rem; margin-bottom: 1.5rem;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="display: flex; align-items: center; gap: 0.75rem;">
                        <span style="font-size: 1.5rem;">🔔</span>
                        <div>
                            <div style="font-weight: 700; color: #92400e; font-size: 1.1rem;">
                                {nao_lidas} notificação{'' if nao_lidas == 1 else 'ões'} não lida{'' if nao_lidas == 1 else 's'}
                            </div>
                            <div style="font-size: 0.85rem; color: #a16207;">
                                Você tem {nao_lidas} mensagen{'s' if nao_lidas != 1 else ''} aguardando leitura
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%); 
                border-left: 4px solid #10b981; border-radius: 12px; padding: 1rem 1.25rem; margin-bottom: 1.5rem;">
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <span style="font-size: 1.5rem;">✅</span>
                    <div>
                        <div style="font-weight: 700; color: #14532d; font-size: 1.1rem;">
                            Tudo em ordem!
                        </div>
                        <div style="font-size: 0.85rem; color: #166534;">
                            Nenhuma notificação pendente
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Botão marcar todas como lidas
        if nao_lidas > 0:
            col_btn, _ = st.columns([1, 3])
            with col_btn:
                if st.button("✔️ Marcar todas como lidas", use_container_width=True, type="primary"):
                    mark_all_read()
                    st.rerun()

        if not notifs:
            st.info("Nenhuma notificação no momento.")
        else:
            st.markdown(f"<div style='margin-bottom: 1rem; color: #6b7280; font-size: 0.9rem;'>📨 {len(notifs)} notificações no total</div>", unsafe_allow_html=True)
            
            for n in notifs:
                lida = n.get("lida", False)
                
                # Cores diferentes para lidas/não lidas
                if not lida:
                    # Não lida - destaque amarelo
                    bg = "linear-gradient(135deg, #fef3c7 0%, #fffbeb 100%)"
                    border = "#f59e0b"
                    icon = "🔔"
                    opacity = "1"
                    shadow = "0 4px 12px rgba(245, 158, 11, 0.15)"
                else:
                    # Lida - neutro
                    bg = "#f9fafb"
                    border = "#e5e7eb"
                    icon = "✓"
                    opacity = "0.7"
                    shadow = "0 2px 4px rgba(0,0,0,0.04)"
                
                ts = str(n.get("created_at", ""))[:16].replace("T", " ")
                
                st.markdown(f"""
                <div style="background: {bg}; border-left: 4px solid {border}; border-radius: 12px; 
                    padding: 1rem 1.25rem; margin-bottom: 0.75rem; box-shadow: {shadow}; opacity: {opacity};">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem;">
                        <div style="flex: 1;">
                            <div style="font-weight: 700; font-size: 0.95rem; color: #1f2937; margin-bottom: 0.35rem;">
                                {icon} {n.get('titulo', 'Notificação')}
                            </div>
                            <div style="font-size: 0.9rem; color: #4b5563; line-height: 1.5;">
                                {n.get('mensagem', '')}
                            </div>
                            <div style="margin-top: 0.6rem; font-size: 0.8rem; color: #6b7280; display: flex; align-items: center; gap: 0.35rem;">
                                <span>🕐</span> {ts}
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)


# ============================================================================
# PAINEL PRINCIPAL
# ============================================================================
def render_admin_panel():
    st.markdown("""
    <style>
    /* Header moderno */
    .admin-header-modern {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
        position: relative;
        overflow: hidden;
    }
    .admin-header-modern::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -20%;
        width: 300px;
        height: 300px;
        background: rgba(255,255,255,0.1);
        border-radius: 50%;
    }
    .admin-header-modern h1 {
        margin: 0;
        font-size: 2.2rem;
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    .admin-header-modern p {
        margin: 0.5rem 0 0;
        opacity: 0.9;
        font-size: 1rem;
    }
    
    /* Tabs estilizadas */
    div[data-testid="stTabs"] button[role="tab"] {
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        padding: 0.75rem 1.5rem !important;
        border-radius: 8px 8px 0 0 !important;
        transition: all 0.3s ease !important;
    }
    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3) !important;
    }
    div[data-testid="stTabs"] button[role="tab"]:hover {
        background: rgba(102, 126, 234, 0.1) !important;
    }
    
    /* Container cards */
    .admin-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        border: 1px solid #e5e7eb;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # Header moderno
    st.markdown("""
    <div class='admin-header-modern'>
        <h1>⚙️ Painel Administrativo</h1>
        <p>StarCheck · Gestão completa de usuários, permissões e acessos</p>
    </div>
    """, unsafe_allow_html=True)

    render_usuarios_panel()
