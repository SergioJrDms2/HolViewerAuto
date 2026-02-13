"""
sidebar.py — Sidebar redesenhada do Analisador de Holerite
Design branco com gradiente roxo claro para combinar com a plataforma
COM INTEGRAÇÃO DAS INFORMAÇÕES DO USUÁRIO E CONFIGURAÇÕES DE PERFIL

USO no main.py:
    from sidebar import render_sidebar
    from auth import render_user_info_sidebar

    # No início do main(), após autenticação:
    prefeitura_selecionada, modo = render_sidebar(PREFEITURAS, NOSSOS_PRODUTOS, CARTOES_CONHECIDOS, CARTOES_NAO_COMPRADOS)
"""

import streamlit as st
from auth import render_auth_page, render_user_info_sidebar
from admin import load_cartoes
import base64
import os

PREFEITURAS_COM_MARGEM = [
    'POA', 'MARINGA', 'SOROCABA', 'COTIA', 'EMBU', 'HORTOLANDIA', 'BAURU',
    'TABOAO_SERRA', 'SALTO', 'TUPA', 'ITAITUBA', 'BARCARENA', 'CAMPOS_JORDAO',
    'RIBEIRAO_PRETO', 'PONTA_GROSSA', 'CAMARA_DEPUTADOS', 'BELTERRA',
    'SAO_JOSE_RIO_PRETO', 'VINHEDO', 'MONTE_ALEGRE_SE', 'REDENCAO', 'CUIABA',
    'ALEGO', 'GOVERNO_GOIAS'
]


def render_sidebar(PREFEITURAS, NOSSOS_PRODUTOS=None, CARTOES_CONHECIDOS=None, CARTOES_NAO_COMPRADOS=None):
    """
    Renderiza a sidebar completa e retorna (prefeitura_selecionada, modo).
    Os parâmetros de cartões são mantidos por compatibilidade, mas as listas
    são sempre carregadas diretamente do Supabase via load_cartoes().
    """
    # Busca sempre do Supabase — garante dados atualizados para todos os usuários
    NOSSOS_PRODUTOS       = load_cartoes("nossos_produtos")
    CARTOES_CONHECIDOS    = load_cartoes("cartoes_conhecidos")
    CARTOES_NAO_COMPRADOS = load_cartoes("cartoes_nao_comprados")

    # INICIALIZA O MODO ATUAL NO SESSION STATE (se não existir)
    if 'modo_atual' not in st.session_state:
        st.session_state['modo_atual'] = 'Análise Individual'

    with st.sidebar:

        # ── CSS exclusivo da sidebar ──────────────────────────────────────
        st.markdown("""
        <style>
        /* Fundo branco com gradiente roxo claro */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #FFFFFF 0%, #F8F7FF 30%, #F0EBFF 70%, #E9DEFF 100%) !important;
            padding-top: 0 !important;
        }

        /* Remove padding extra do container interno */
        [data-testid="stSidebar"] > div:first-child {
            padding-top: 0 !important;
        }

        /* Texto geral em roxo escuro */
        [data-testid="stSidebar"] * {
            color: #2D1B69;
        }

        /* Selectbox */
        [data-testid="stSidebar"] .stSelectbox > div > div {
            background-color: #FFFFFF !important;
            border: 2px solid #DDD6FE !important;
            border-radius: 0.75rem !important;
            color: #2D1B69 !important;
            box-shadow: 0 2px 8px rgba(139, 92, 246, 0.08);
            transition: all 0.3s ease;
        }
        [data-testid="stSidebar"] .stSelectbox > div > div:hover {
            border-color: #A78BFA !important;
            box-shadow: 0 4px 12px rgba(139, 92, 246, 0.15);
        }
        [data-testid="stSidebar"] .stSelectbox svg { 
            fill: #7C3AED !important; 
        }
        [data-testid="stSidebar"] .stSelectbox label {
            color: #6D28D9 !important;
            font-weight: 600;
        }

        /* Radio buttons */
        [data-testid="stSidebar"] .stRadio > label {
            color: #6D28D9 !important;
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
            background: #FFFFFF;
            border: 2px solid #E9DEFF;
            border-radius: 0.75rem;
            padding: 0.65rem 0.9rem;
            margin-bottom: 0.4rem;
            transition: all 0.25s ease;
            color: #2D1B69 !important;
            font-weight: 500;
            box-shadow: 0 1px 3px rgba(139, 92, 246, 0.05);
        }
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {
            background: #F5F3FF;
            border-color: #A78BFA;
            transform: translateX(3px);
            box-shadow: 0 4px 12px rgba(139, 92, 246, 0.12);
        }
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label[data-checked="true"] {
            background: linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%);
            border-color: #7C3AED;
            color: white !important;
            font-weight: 600;
            box-shadow: 0 4px 16px rgba(124, 58, 237, 0.3);
        }

        /* Botões (incluindo logout) */
        [data-testid="stSidebar"] .stButton > button {
            background: linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 0.65rem !important;
            padding: 0.6rem 1rem !important;
            font-weight: 600 !important;
            font-size: 0.85rem !important;
            box-shadow: 0 2px 8px rgba(124, 58, 237, 0.25) !important;
            transition: all 0.25s ease !important;
            width: 100% !important;
        }
        [data-testid="stSidebar"] .stButton > button:hover {
            box-shadow: 0 4px 14px rgba(124, 58, 237, 0.35) !important;
            transform: translateY(-1px) !important;
        }

        /* Expanders */
        [data-testid="stSidebar"] .streamlit-expanderHeader {
            background: #FFFFFF !important;
            border: 2px solid #E9DEFF !important;
            border-radius: 0.75rem !important;
            color: #2D1B69 !important;
            font-weight: 600;
            transition: all 0.25s ease;
            box-shadow: 0 1px 3px rgba(139, 92, 246, 0.05);
        }
        [data-testid="stSidebar"] .streamlit-expanderHeader:hover {
            border-color: #A78BFA !important;
            background: #F9FAFB !important;
            box-shadow: 0 3px 10px rgba(139, 92, 246, 0.1);
        }
        [data-testid="stSidebar"] .streamlit-expanderContent {
            background: #FDFCFE !important;
            border: 2px solid #E9DEFF !important;
            border-top: none !important;
            border-radius: 0 0 0.75rem 0.75rem !important;
            padding: 0.75rem !important;
        }

        /* Info box */
        [data-testid="stSidebar"] .stAlert {
            background: linear-gradient(135deg, #F5F3FF 0%, #EDE9FE 100%) !important;
            border: 2px solid #C4B5FD !important;
            border-radius: 0.85rem !important;
            color: #5B21B6 !important;
            box-shadow: 0 2px 8px rgba(139, 92, 246, 0.1);
        }
        [data-testid="stSidebar"] .stAlert svg {
            fill: #7C3AED !important;
        }

        /* Scrollbar personalizada */
        [data-testid="stSidebar"]::-webkit-scrollbar {
            width: 8px;
        }
        [data-testid="stSidebar"]::-webkit-scrollbar-track {
            background: rgba(233, 222, 255, 0.3);
            border-radius: 10px;
        }
        [data-testid="stSidebar"]::-webkit-scrollbar-thumb {
            background: linear-gradient(180deg, #A78BFA 0%, #8B5CF6 100%);
            border-radius: 10px;
        }
        [data-testid="stSidebar"]::-webkit-scrollbar-thumb:hover {
            background: linear-gradient(180deg, #8B5CF6 0%, #7C3AED 100%);
        }
        </style>
        """, unsafe_allow_html=True)

        # ── Logo ──────────────────────────────────────────────────────────
        st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)

        def get_img_as_base64(file_path):
            with open(file_path, "rb") as f:
                data = f.read()
            return base64.b64encode(data).decode()

        # Ajuste o caminho se necessário
        image_path = "assets/LogoStarcheck.png" 

        try:
            img_base64 = get_img_as_base64(image_path)
            img_src = f"data:image/png;base64,{img_base64}"
        except Exception:
            img_src = "" 

        st.markdown(f"""
            <div style='text-align: center; margin-bottom: 1.8rem;'>
                <img src='{img_src}' alt='StarCheck Logo' style='width: 200px; height: auto;' />
            </div>
        """, unsafe_allow_html=True)

        # ── Info do Usuário ───────────────────────────────────────────────
        render_user_info_sidebar()

        # ── Prefeitura ────────────────────────────────────────────────────
        st.markdown("""
            <div style='
                display: flex; 
                align-items: center; 
                gap: 0.5rem;
                margin-bottom: 0.6rem;
            '>
                <span style='font-size: 1.1rem;'>📍</span>
                <p style='
                    font-size: 0.75rem; 
                    font-weight: 700; 
                    text-transform: uppercase; 
                    letter-spacing: 0.8px; 
                    color: #6D28D9; 
                    margin: 0;
                '>Prefeitura</p>
            </div>
        """, unsafe_allow_html=True)

        prefeitura_selecionada = st.selectbox(
            "Prefeitura",
            options=list(PREFEITURAS.keys()),
            format_func=lambda x: PREFEITURAS[x]['nome'],
            help="Escolha a prefeitura do holerite para análise correta",
            label_visibility="collapsed"
        )

        # ── Divisor ───────────────────────────────────────────────────────
        st.markdown("<hr style='border: none; height: 2px; background: linear-gradient(90deg, transparent 0%, #DDD6FE 50%, transparent 100%); margin: 1.5rem 0;'>", unsafe_allow_html=True)

        # ── Modo ──────────────────────────────────────────────────────────
        st.markdown("""
            <div style='
                display: flex; 
                align-items: center; 
                gap: 0.5rem;
                margin-bottom: 0.6rem;
            '>
                <span style='font-size: 1.1rem;'>⚙️</span>
                <p style='
                    font-size: 0.75rem; 
                    font-weight: 700; 
                    text-transform: uppercase; 
                    letter-spacing: 0.8px; 
                    color: #6D28D9; 
                    margin: 0;
                '>Selecione o Modo</p>
            </div>
        """, unsafe_allow_html=True)

        # Opções de modo SEM Perfil (Perfil é controlado separadamente)
        opcoes_modo = ["Análise Individual", "Análise em Lote", "Feedback"]
        
        # Determina o índice atual baseado no modo_atual do session_state
        # Se o modo_atual for "Perfil", mantem a seleção anterior do radio
        if st.session_state['modo_atual'] in opcoes_modo:
            index_atual = opcoes_modo.index(st.session_state['modo_atual'])
        else:
            # Se estiver em Perfil ou outro modo, mantém a última seleção válida
            # ou usa a primeira opção como padrão
            index_atual = 0
        
        # Renderiza o radio button
        modo_selecionado_radio = st.radio(
            "Selecione o Modo",
            opcoes_modo,
            index=index_atual,
            help="Escolha entre analisar um único PDF, múltiplos PDFs ou enviar feedback",
            label_visibility="collapsed",
            key="radio_modo"
        )
        
        # Atualiza o modo_atual baseado no radio button (a não ser que esteja em Perfil)
        # Se o usuário mudou o radio button, isso significa que ele quer sair do Perfil
        if st.session_state['modo_atual'] == 'Perfil' and modo_selecionado_radio != st.session_state.get('ultimo_modo_radio'):
            # Usuário clicou em um modo diferente, sai do Perfil
            st.session_state['modo_atual'] = modo_selecionado_radio
        elif st.session_state['modo_atual'] != 'Perfil':
            # Não está em Perfil, então atualiza normalmente
            st.session_state['modo_atual'] = modo_selecionado_radio
        
        # Salva a última seleção do radio para detectar mudanças
        st.session_state['ultimo_modo_radio'] = modo_selecionado_radio
        
        # Retorna o modo atual (que pode ser Perfil ou o modo do radio)
        modo = st.session_state['modo_atual']

        # ── Divisor ───────────────────────────────────────────────────────
        st.markdown("<hr style='border: none; height: 2px; background: linear-gradient(90deg, transparent 0%, #DDD6FE 50%, transparent 100%); margin: 1.5rem 0;'>", unsafe_allow_html=True)

        # ── Nossos Produtos ───────────────────────────────────────────────
        st.markdown("""
            <div style='
                display: flex; 
                align-items: center; 
                gap: 0.5rem;
                margin-bottom: 0.6rem;
            '>
                <span style='font-size: 1.1rem;'>✅</span>
                <p style='
                    font-size: 0.75rem; 
                    font-weight: 700; 
                    text-transform: uppercase; 
                    letter-spacing: 0.8px; 
                    color: #6D28D9; 
                    margin: 0;
                '>Nossos Produtos</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.expander("Ver lista completa", expanded=False):
            for produto in NOSSOS_PRODUTOS:
                st.markdown(f"""
                    <div style='
                        padding: 0.5rem 0.6rem; 
                        font-size: 0.88rem; 
                        font-weight: 500; 
                        color: #2D1B69; 
                        border-bottom: 1px solid #E9DEFF;
                        display: flex;
                        align-items: center;
                        gap: 0.5rem;
                    '>
                        <span style='color: #8B5CF6;'>⭐</span> {produto}
                    </div>
                """, unsafe_allow_html=True)

        st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)

        # ── Cartões Concorrentes ──────────────────────────────────────────
        st.markdown("""
            <div style='
                display: flex; 
                align-items: center; 
                gap: 0.5rem;
                margin-bottom: 0.6rem;
            '>
                <span style='font-size: 1.1rem;'>🎯</span>
                <p style='
                    font-size: 0.75rem; 
                    font-weight: 700; 
                    text-transform: uppercase; 
                    letter-spacing: 0.8px; 
                    color: #6D28D9; 
                    margin: 0;
                '>Cartões Concorrentes</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.expander("Ver lista completa", expanded=False):
            cols = st.columns(2)
            for idx, cartao in enumerate(CARTOES_CONHECIDOS):
                with cols[idx % 2]:
                    st.markdown(f"""
                        <div style='
                            padding: 0.3rem 0; 
                            font-size: 0.82rem; 
                            color: #4C1D95;
                            font-weight: 500;
                        '>• {cartao}</div>
                    """, unsafe_allow_html=True)

        st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)

        # ── Cartões Que Não Compramos ─────────────────────────────────────
        st.markdown("""
            <div style='
                display: flex; 
                align-items: center; 
                gap: 0.5rem;
                margin-bottom: 0.6rem;
            '>
                <span style='font-size: 1.1rem;'>🚫</span>
                <p style='
                    font-size: 0.75rem; 
                    font-weight: 700; 
                    text-transform: uppercase; 
                    letter-spacing: 0.8px; 
                    color: #6D28D9; 
                    margin: 0;
                '>Cartões Que Não Compramos</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.expander("Ver lista completa", expanded=False):
            cols = st.columns(2)
            for idx, cartao in enumerate(CARTOES_NAO_COMPRADOS):
                with cols[idx % 2]:
                    st.markdown(f"""
                        <div style='
                            padding: 0.3rem 0; 
                            font-size: 0.82rem; 
                            color: #4C1D95;
                            font-weight: 500;
                        '>• {cartao}</div>
                    """, unsafe_allow_html=True)

        # ── Divisor ───────────────────────────────────────────────────────
        st.markdown("<hr style='border: none; height: 2px; background: linear-gradient(90deg, transparent 0%, #DDD6FE 50%, transparent 100%); margin: 1.5rem 0;'>", unsafe_allow_html=True)

        # ── Dica ──────────────────────────────────────────────────────────
        st.info("💡 Você pode fazer upload de múltiplos PDFs de uma vez no modo de análise em lote.", icon="ℹ️")

        # ── Versão ────────────────────────────────────────────────────────
        st.markdown("""
            <div style='
                text-align: center; 
                margin-top: 2rem; 
                padding-top: 1.25rem; 
                border-top: 2px solid #E9DEFF;
            '>
                <span style='
                    font-size: 0.72rem; 
                    color: #A78BFA; 
                    letter-spacing: 0.8px;
                    font-weight: 600;
                '>v2.1 · StarCheck</span> 
            </div>
        """, unsafe_allow_html=True)

    return prefeitura_selecionada, modo
