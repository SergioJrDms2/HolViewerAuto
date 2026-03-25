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

_CSS = """
<style>
/* ── Reset & base ────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

section[data-testid="stMain"] { font-family: 'Inter', sans-serif; }

/* ── Header hero ─────────────────────────────────────────────────── */
.crm-hero {
    background: linear-gradient(135deg, #3B0764 0%, #6D28D9 55%, #7C3AED 100%);
    border-radius: 1.4rem;
    padding: 2rem 2.25rem 1.85rem;
    margin-bottom: 1.75rem;
    box-shadow: 0 12px 40px rgba(109,40,217,.28);
    position: relative;
    overflow: hidden;
}
.crm-hero::before {
    content: '';
    position: absolute;
    top: -40px; right: -40px;
    width: 220px; height: 220px;
    background: rgba(255,255,255,.05);
    border-radius: 50%;
}
.crm-hero::after {
    content: '';
    position: absolute;
    bottom: -60px; left: -20px;
    width: 160px; height: 160px;
    background: rgba(255,255,255,.04);
    border-radius: 50%;
}
.crm-hero-eyebrow {
    font-size: .68rem; font-weight: 700; letter-spacing: .14em;
    color: rgba(255,255,255,.55); text-transform: uppercase;
    margin: 0 0 .5rem;
}
.crm-hero-title {
    color: #fff; font-size: 1.6rem; font-weight: 800;
    margin: 0 0 .45rem; letter-spacing: -.5px; line-height: 1.2;
}
.crm-hero-sub {
    color: rgba(255,255,255,.65); font-size: .86rem;
    margin: 0; line-height: 1.65;
}

/* ── Status bar ──────────────────────────────────────────────────── */
.crm-status-bar {
    display: flex; align-items: center; gap: .5rem;
    background: #F0FDF4;
    border: 1px solid #BBF7D0;
    border-radius: .65rem;
    padding: .5rem 1rem;
    font-size: .8rem; font-weight: 600; color: #166534;
    margin-bottom: 1.25rem;
}
.crm-status-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #22C55E;
    box-shadow: 0 0 0 3px rgba(34,197,94,.2);
    flex-shrink: 0;
}

/* ── Auth box ────────────────────────────────────────────────────── */
.crm-auth-wrap {
    background: linear-gradient(160deg, #F5F3FF 0%, #EDE9FE 100%);
    border: 1.5px solid #C4B5FD;
    border-radius: 1.25rem;
    padding: 3rem 2.25rem;
    text-align: center;
    max-width: 500px;
    margin: 2.5rem auto;
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
    transition: transform .15s, box-shadow .15s;
    letter-spacing: .02em;
}
.crm-auth-cta:hover {
    transform: translateY(-1px);
    box-shadow: 0 10px 28px rgba(124,58,237,.45);
}
.crm-auth-note {
    margin-top: 1.1rem; font-size: .7rem; color: #A78BFA;
}

/* ── Search card ─────────────────────────────────────────────────── */
.crm-search-wrap {
    background: #fff;
    border: 1.5px solid #E5E7EB;
    border-radius: 1.1rem;
    padding: 1.35rem 1.5rem 1.1rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 2px 10px rgba(0,0,0,.04);
}
.crm-search-label {
    font-size: .72rem; font-weight: 700; color: #7C3AED;
    text-transform: uppercase; letter-spacing: .1em;
    margin-bottom: .55rem;
}
.crm-search-hint {
    font-size: .76rem; color: #9CA3AF;
    margin-top: .55rem; display: flex; align-items: center; gap: .35rem;
}

/* ── Result meta ─────────────────────────────────────────────────── */
.crm-result-meta {
    display: flex; align-items: center; gap: .5rem;
    font-size: .8rem; color: #6B7280; font-weight: 500;
    margin-bottom: 1rem;
}
.crm-result-count {
    background: #7C3AED; color: #fff;
    font-size: .72rem; font-weight: 800;
    padding: .15rem .6rem; border-radius: 99px;
}

/* ── Deal card ────────────────────────────────────────────────────── */
.crm-deal-card {
    background: #fff;
    border: 1.5px solid #E5E7EB;
    border-radius: 1.1rem;
    margin-bottom: .9rem;
    overflow: hidden;
    box-shadow: 0 2px 10px rgba(0,0,0,.04);
    transition: box-shadow .2s;
}
.crm-deal-card:hover {
    box-shadow: 0 6px 24px rgba(109,40,217,.1);
}
.crm-deal-header {
    display: flex; align-items: center; gap: 1rem;
    padding: 1.1rem 1.4rem;
    border-bottom: 1px solid #F3F4F6;
    cursor: pointer;
    background: linear-gradient(135deg, #FAFAFA 0%, #F5F3FF 100%);
}
.crm-deal-avatar {
    width: 42px; height: 42px; border-radius: 50%;
    background: linear-gradient(135deg, #7C3AED, #4C1D95);
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem; color: #fff; flex-shrink: 0;
    font-weight: 700;
}
.crm-deal-name   { font-size: .95rem; font-weight: 700; color: #111827; margin: 0 0 .2rem; }
.crm-deal-sub    { font-size: .75rem; color: #9CA3AF; margin: 0; display: flex; gap: .55rem; flex-wrap: wrap; }
.crm-deal-badge  {
    margin-left: auto; flex-shrink: 0;
    background: #EDE9FE; color: #6D28D9;
    font-size: .67rem; font-weight: 700;
    padding: .22rem .65rem; border-radius: 99px;
    white-space: nowrap;
}
.crm-deal-body   { padding: 1.1rem 1.4rem; }

/* ── Expander override ────────────────────────────────────────────── */
[data-testid="stExpander"] summary {
    border-radius: .75rem !important;
    background: linear-gradient(135deg, #FAFAFA, #F5F3FF) !important;
    border: 1.5px solid #E5E7EB !important;
    border-left: 4px solid #7C3AED !important;
    padding: .9rem 1.2rem !important;
    margin-bottom: .45rem !important;
    font-weight: 700 !important;
    font-size: .92rem !important;
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

/* ── Info grid ────────────────────────────────────────────────────── */
.crm-info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
    gap: .55rem;
    margin: .5rem 0 .9rem;
}
.crm-info-tag {
    display: flex; align-items: flex-start; gap: .6rem;
    background: #fff; border: 1px solid #E5E7EB;
    border-radius: .6rem; padding: .6rem .85rem;
    transition: border-color .15s, box-shadow .15s;
}
.crm-info-tag:hover {
    border-color: #C4B5FD;
    box-shadow: 0 2px 8px rgba(109,40,217,.08);
}
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

/* ── Section label ────────────────────────────────────────────────── */
.crm-section-label {
    font-size: .65rem; font-weight: 800; color: #7C3AED;
    text-transform: uppercase; letter-spacing: .12em;
    display: flex; align-items: center; gap: .45rem;
    margin: 1.1rem 0 .5rem;
}
.crm-section-label::after {
    content: ''; flex: 1; height: 1.5px;
    background: linear-gradient(90deg, #DDD6FE, transparent);
}

/* ── Document list ────────────────────────────────────────────────── */
.crm-doc-item {
    display: flex; align-items: center; gap: .65rem;
    padding: .5rem .9rem;
    background: #F0FDF4; border: 1px solid #BBF7D0;
    border-radius: .55rem; margin-bottom: .35rem;
    font-size: .83rem; color: #065F46; font-weight: 600;
    transition: background .15s;
}
.crm-doc-item:hover { background: #DCFCE7; }
.crm-doc-meta { font-size: .7rem; color: #6EE7B7; margin-left: auto; flex-shrink: 0; }

/* ── Note items ───────────────────────────────────────────────────── */
.crm-note-item {
    background: #fff; border: 1px solid #E5E7EB;
    border-left: 3px solid #A78BFA;
    border-radius: 0 .6rem .6rem 0;
    padding: .75rem 1rem; margin-bottom: .42rem;
    font-size: .84rem; color: #374151; line-height: 1.65;
}
.crm-note-meta {
    font-size: .69rem; color: #9CA3AF;
    margin-top: .4rem; display: flex; gap: .55rem; flex-wrap: wrap;
    align-items: center;
}
.crm-note-tag {
    background: #EDE9FE; color: #7C3AED;
    padding: .07rem .48rem; border-radius: 99px;
    font-size: .63rem; font-weight: 800;
    text-transform: uppercase; letter-spacing: .06em;
}

/* ── Empty / none states ──────────────────────────────────────────── */
.crm-empty {
    text-align: center; padding: 3.5rem 1rem;
    color: #9CA3AF;
}
.crm-empty-icon { font-size: 2.75rem; margin-bottom: .75rem; }
.crm-empty-txt  { font-size: .95rem; color: #6B7280; font-weight: 600; }
.crm-empty-sub  { font-size: .82rem; color: #D1D5DB; margin-top: .45rem; }

.crm-none-tag {
    display: inline-block;
    background: #F9FAFB; color: #9CA3AF;
    font-size: .75rem; padding: .28rem .75rem;
    border-radius: .4rem; border: 1px solid #E5E7EB;
    margin-top: .1rem;
}

/* ── Rank badge (1º, 2º, 3º mais recente) ────────────────────────── */
.crm-rank {
    display: inline-flex; align-items: center; justify-content: center;
    width: 22px; height: 22px; border-radius: 50%;
    font-size: .65rem; font-weight: 800;
    flex-shrink: 0;
}
.crm-rank-1 { background: #FEF3C7; color: #92400E; }
.crm-rank-2 { background: #F3F4F6; color: #374151; }
.crm-rank-3 { background: #FEF2F2; color: #991B1B; }

/* ── Divider ─────────────────────────────────────────────────────── */
.crm-divider {
    height: 1px; background: linear-gradient(90deg, #EDE9FE, #E5E7EB, transparent);
    margin: 1rem 0;
}
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
# COMPONENTES REUTILIZÁVEIS
# ─────────────────────────────────────────────────────────────────────────────

def _banner(titulo: str, subtitulo: str, icone: str = "💳"):
    st.markdown(_CSS, unsafe_allow_html=True) 

    st.markdown(f"""
        <div class="crm-hero">
            <div class="crm-hero-title">{icone} {titulo}</div>
            <p class="crm-hero-sub">
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
        icone=""
    )

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
        icone=""
    )

    _como_usar_lote()
