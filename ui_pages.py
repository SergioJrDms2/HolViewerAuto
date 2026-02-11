"""
ui_pages.py — Design das Páginas de Análise
Aplica o mesmo padrão visual da página de Feedback
nas páginas de Análise Individual e Análise em Lote.

USO:
    from ui_pages import render_individual_header, render_lote_header

    # No bloco "Análise Individual" (substitui os st.markdown/st.info iniciais):
    render_individual_header(prefeitura_selecionada, PREFEITURAS)

    # No bloco "Análise em Lote" (substitui os st.markdown/st.info iniciais):
    render_lote_header(prefeitura_selecionada, PREFEITURAS)
"""

import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
# COMPONENTES REUTILIZÁVEIS
# ─────────────────────────────────────────────────────────────────────────────

def _banner(titulo: str, subtitulo: str, icone: str = "💳"):
    """Banner degradê roxo — igual ao da página de Feedback."""
    st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #4C1D95 0%, #7C3AED 60%, #8B5CF6 100%);
            border-radius: 1.25rem;
            padding: 2.5rem 2rem 2rem 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 8px 30px rgba(124, 58, 237, 0.25);
        ">
            <h1 style="color: white; font-size: 2rem; font-weight: 800; margin: 0 0 0.5rem 0; letter-spacing: -0.5px;">
                {icone} {titulo}
            </h1>
            <p style="color: #DDD6FE; font-size: 1.05rem; margin: 0; line-height: 1.6;">
                {subtitulo}
            </p>
        </div>
    """, unsafe_allow_html=True)


def _aviso_testes():
    """Box laranja de aviso — análise de margem em testes."""
    st.markdown("""
        <div style="
            background-color: #FFF7ED;
            border-left: 5px solid #F97316;
            border-radius: 0.75rem;
            padding: 1.25rem 1.5rem;
            margin-bottom: 1.5rem;
        ">
            <p style="font-size: 1rem; font-weight: 700; color: #9A3412; margin: 0 0 0.4rem 0;">
                ⚠️ Atenção: Cálculo de margem em fase de testes
            </p>
            <p style="font-size: 0.9rem; color: #7C2D12; margin: 0; line-height: 1.6;">
                Os valores de margem são uma <strong>estimativa automatizada</strong> e não devem 
                ser tratados como definitivos. Sempre <strong>confirme a margem real</strong> 
                diretamente na gestora antes de qualquer operação.
            </p>
        </div>
    """, unsafe_allow_html=True)


def _card_prefeitura(nome_prefeitura: str, tem_margem: bool):
    """Card informativo com nome da prefeitura selecionada."""
    badge = '<span style="background:linear-gradient(135deg,#dc2626,#b91c1c);color:white;font-size:0.7rem;font-weight:700;padding:0.2rem 0.6rem;border-radius:1rem;margin-left:0.75rem;vertical-align:middle;letter-spacing:0.3px;">🏷️ Margem Disponível</span>' if tem_margem else ""

    st.markdown(f'<div style="background:#F5F3FF;border:1px solid #DDD6FE;border-left:5px solid #7C3AED;border-radius:0.75rem;padding:1rem 1.5rem;margin-bottom:1.5rem;display:flex;align-items:center;"><span style="font-size:1.4rem;margin-right:0.75rem;">📍</span><div><span style="font-size:0.78rem;color:#7C3AED;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Prefeitura Selecionada</span><br><span style="font-size:1rem;font-weight:700;color:#1E1B4B;">{nome_prefeitura}</span>{badge}</div></div>', unsafe_allow_html=True)


def _tres_cards(dados: list):
    """
    Renderiza 3 cards de indicadores lado a lado.
    dados = lista de dicts: [{"icone", "titulo", "descricao", "bg", "border", "cor_titulo"}]
    """
    cols = st.columns(3)
    for col, item in zip(cols, dados):
        with col:
            st.markdown(f"""
                <div style="
                    background: {item['bg']};
                    border-radius: 1rem;
                    padding: 1.25rem;
                    text-align: center;
                    border: 1px solid {item['border']};
                    height: 100%;
                ">
                    <div style="font-size: 1.8rem;">{item['icone']}</div>
                    <div style="font-weight: 700; color: {item['cor_titulo']};
                                font-size: 0.95rem; margin-top: 0.4rem;">
                        {item['titulo']}
                    </div>
                    <div style="color: #64748B; font-size: 0.8rem; margin-top: 0.2rem;">
                        {item['descricao']}
                    </div>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)


def _como_usar_individual():
    """Expander 'Como usar' para análise individual."""
    with st.expander("ℹ️ Como usar — clique para expandir", expanded=False):
        st.markdown("""
        <div style="padding: 0.25rem 0;">
            <ol style="color: #374151; line-height: 2; font-size: 0.95rem; padding-left: 1.2rem;">
                <li><strong>Selecione a prefeitura</strong> correta na barra lateral.</li>
                <li><strong>Faça o upload</strong> do PDF do holerite na área abaixo.</li>
                <li>Clique em <strong>"Analisar"</strong> e aguarde o processamento.</li>
                <li>Veja os resultados: dados do servidor, margem e oportunidades.</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
        _aviso_testes()


def _como_usar_lote():
    """Expander 'Como usar' para análise em lote."""
    with st.expander("ℹ️ Como usar — clique para expandir", expanded=False):
        st.markdown("""
        <div style="padding: 0.25rem 0;">
            <ol style="color: #374151; line-height: 2; font-size: 0.95rem; padding-left: 1.2rem;">
                <li><strong>Selecione a prefeitura</strong> na barra lateral.</li>
                <li><strong>Faça upload de múltiplos PDFs</strong> de uma vez.</li>
                <li>Clique em <strong>"Processar Todos"</strong> para iniciar.</li>
                <li>Analise o dashboard consolidado e exporte os resultados.</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
        _aviso_testes()


# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÕES PÚBLICAS — chamadas no main.py
# ─────────────────────────────────────────────────────────────────────────────

PREFEITURAS_COM_MARGEM = [
    'POA', 'MARINGA', 'SOROCABA', 'COTIA', 'EMBU', 'HORTOLANDIA', 'BAURU',
    'TABOAO_SERRA', 'SALTO', 'TUPA', 'ITAITUBA', 'BARCARENA', 'CAMPOS_JORDAO',
    'RIBEIRAO_PRETO', 'PONTA_GROSSA', 'CAMARA_DEPUTADOS', 'BELTERRA',
    'SAO_JOSE_RIO_PRETO', 'VINHEDO', 'MONTE_ALEGRE_SE', 'REDENCAO', 'CUIABA',
    'ALEGO', 'GOVERNO_GOIAS'
]


def render_individual_header(prefeitura_selecionada: str, PREFEITURAS: dict):
    """
    Substitui o cabeçalho da página de Análise Individual.

    Chame assim no main.py, substituindo:
        st.markdown("<h2 class='section-header'>StarCheck - Análise Individual</h2>", ...)
        st.info(f"Prefeitura selecionada: ...")
    """
    _banner(
        titulo="Análise Individual",
        subtitulo="Faça o upload de um holerite em PDF e obtenha em segundos: dados do servidor, cálculo de margem e oportunidades de negócio.",
        icone="🔍"
    )

    _card_prefeitura(
        nome_prefeitura=PREFEITURAS[prefeitura_selecionada]['nome'],
        tem_margem=prefeitura_selecionada in PREFEITURAS_COM_MARGEM
    )

    _tres_cards([
        {
            "icone": "📄",
            "titulo": "Upload de PDF",
            "descricao": "Arraste ou selecione o holerite",
            "bg": "#F5F3FF",
            "border": "#DDD6FE",
            "cor_titulo": "#4C1D95",
        },
        {
            "icone": "⚡",
            "titulo": "Processamento Automático",
            "descricao": "Extração inteligente de dados",
            "bg": "#EFF6FF",
            "border": "#BFDBFE",
            "cor_titulo": "#1E3A5F",
        },
        {
            "icone": "💡",
            "titulo": "Oportunidades",
            "descricao": "Cartões e margem identificados",
            "bg": "#F0FDF4",
            "border": "#BBF7D0",
            "cor_titulo": "#14532D",
        },
    ])

    _como_usar_individual()


def render_lote_header(prefeitura_selecionada: str, PREFEITURAS: dict):
    """
    Substitui o cabeçalho da página de Análise em Lote.

    Chame assim no main.py, substituindo:
        st.markdown("<h2 class='section-header'>StarCheck - Análise em Lote</h2>", ...)
        st.info(f"Prefeitura selecionada: ...")
    """
    _banner(
        titulo="Análise em Lote",
        subtitulo="Processe dezenas de holerites de uma vez. Visualize o dashboard consolidado e exporte os resultados em Excel ou CSV.",
        icone="📦"
    )

    _card_prefeitura(
        nome_prefeitura=PREFEITURAS[prefeitura_selecionada]['nome'],
        tem_margem=prefeitura_selecionada in PREFEITURAS_COM_MARGEM
    )

    _tres_cards([
        {
            "icone": "📂",
            "titulo": "Múltiplos PDFs",
            "descricao": "Suba todos de uma vez",
            "bg": "#F5F3FF",
            "border": "#DDD6FE",
            "cor_titulo": "#4C1D95",
        },
        {
            "icone": "📊",
            "titulo": "Dashboard",
            "descricao": "Resultados consolidados",
            "bg": "#EFF6FF",
            "border": "#BFDBFE",
            "cor_titulo": "#1E3A5F",
        },
        {
            "icone": "⬇️",
            "titulo": "Exportação",
            "descricao": "Download em Excel ou CSV",
            "bg": "#F0FDF4",
            "border": "#BBF7D0",
            "cor_titulo": "#14532D",
        },
    ])

    _como_usar_lote()
