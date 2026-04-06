"""
validador_arquivos.py — Módulo de Validação e Renomeação de Documentos
Integração com StarCheck · Design consistente com a plataforma
"""

import streamlit as st
import os
import re
import json
import io
import base64
import zipfile
from datetime import datetime
from PIL import Image, ImageEnhance
from groq import Groq
import fitz  # PyMuPDF - para converter PDF em imagem sem depender do Poppler

# ================================================================
#  CONFIGURAÇÃO
# ================================================================

def _get_groq_key() -> str:
    """Obtém a chave da API Groq."""
    try:
        return "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"
    except Exception:
        return os.environ.get("GROQ_API_KEY", "")

MODELO = "meta-llama/llama-4-scout-17b-16e-instruct"

# ================================================================
#  PADRÃO DE NOMES — Banksoft
# ================================================================

MESES_PT = {
    "janeiro": "JAN", "fevereiro": "FEV", "março": "MAR", "marco": "MAR",
    "abril": "ABR", "maio": "MAI", "junho": "JUN",
    "julho": "JUL", "agosto": "AGO", "setembro": "SET",
    "outubro": "OUT", "novembro": "NOV", "dezembro": "DEZ",
    "jan": "JAN", "fev": "FEV", "mar": "MAR", "abr": "ABR",
    "mai": "MAI", "jun": "JUN", "jul": "JUL", "ago": "AGO",
    "set": "SET", "out": "OUT", "nov": "NOV", "dez": "DEZ",
}

CATEGORIAS_VALIDAS = [
    "DOCUMENTO_DE_IDENTIFICACAO",
    "DOCUMENTO_DE_IDENTIFICACAO_VERSO",
    "COMPROVANTE_DE_ENDERECO",
    "COMPLEMENTO_ENDERECO",
    "HOLERITE",
    "SELFIE",
    "DADOS_BANCARIOS",
    "RESERVA_MARGEM",
    "TOKEN",
    "DOCUMENTO_DESCONHECIDO",
]

PROMPT = """Você é um especialista em classificação de documentos brasileiros para o sistema Banksoft.

Analise a imagem com atenção e retorne um JSON com dois campos:

{
  "categoria": "<CATEGORIA>",
  "referencia": "<MES_ANO ou null>"
}

Categorias disponíveis (use exatamente como escrito):
- "DOCUMENTO_DE_IDENTIFICACAO"       → RG frente, CNH frente ou CNH verso
- "DOCUMENTO_DE_IDENTIFICACAO_VERSO" → RG verso (lado com impressão digital / assinatura)
- "COMPROVANTE_DE_ENDERECO"          → Conta de luz, água, gás, boleto, fatura com endereço
- "COMPLEMENTO_ENDERECO"             → Documento complementar de endereço
- "HOLERITE"                         → Holerite, contracheque ou demonstrativo de pagamento
- "SELFIE"                           → Foto do rosto da pessoa (selfie)
- "DADOS_BANCARIOS"                  → Extrato bancário, dados bancários, comprovante de conta
- "RESERVA_MARGEM"                   → Reserva de margem ou comprovante de margem
- "TOKEN"                            → Token de autorização
- "DOCUMENTO_DESCONHECIDO"           → Nenhum dos anteriores ou ilegível

Regras para o campo "referencia":
- Preencha APENAS quando a categoria for "HOLERITE"
- Formato: "MMM_AA" (ex: "JAN_26", "FEV_26", "MAR_26")
- Extraia o mês e ano de competência do documento (não a data de emissão)
- Se não conseguir identificar o mês/ano, use null
- Para todos os outros tipos, "referencia" deve ser null

Regras gerais:
- Retorne SOMENTE o JSON, sem texto antes ou depois, sem markdown, sem explicações
- RG verso tem impressão digital, assinatura e observações no verso — nunca confunda com frente
- CNH tem campos: categoria (A, B, AB...), validade, RENACH, DETRAN
- Holerite tem: salário bruto, líquido, INSS, FGTS, competência (mês/ano)
"""

# ================================================================
#  CSS CONSISTENTE COM A PLATAFORMA
# ================================================================

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

section[data-testid="stMain"] { font-family: 'Inter', sans-serif; }

/* ── Header hero ─────────────────────────────────────────────────── */
.validador-hero {
    background: linear-gradient(135deg, #3B0764 0%, #6D28D9 55%, #7C3AED 100%);
    border-radius: 1.4rem;
    padding: 2rem 2.25rem 1.85rem;
    margin-bottom: 1.75rem;
    box-shadow: 0 12px 40px rgba(109,40,217,.28);
    position: relative;
    overflow: hidden;
}
.validador-hero::before {
    content: '';
    position: absolute;
    top: -40px; right: -40px;
    width: 220px; height: 220px;
    background: rgba(255,255,255,.05);
    border-radius: 50%;
}
.validador-hero::after {
    content: '';
    position: absolute;
    bottom: -60px; left: -20px;
    width: 160px; height: 160px;
    background: rgba(255,255,255,.04);
    border-radius: 50%;
}
.validador-hero-title {
    color: #fff; font-size: 1.6rem; font-weight: 800;
    margin: 0 0 .45rem; letter-spacing: -.5px; line-height: 1.2;
}
.validador-hero-sub {
    color: rgba(255,255,255,.65); font-size: .86rem;
    margin: 0; line-height: 1.65;
}

/* ── Upload Card ──────────────────────────────────────────────────── */
.validador-upload-card {
    background: #fff;
    border: 1.5px solid #E5E7EB;
    border-radius: 1.1rem;
    padding: 1rem;
    box-shadow: 0 2px 10px rgba(0,0,0,.04);
}

/* ── Info Card ───────────────────────────────────────────────────── */
.validador-info-card {
    background: linear-gradient(160deg, #F5F3FF 0%, #EDE9FE 100%);
    border: 1.5px solid #C4B5FD;
    border-radius: 1.1rem;
    padding: 1rem;
}
.validador-info-title {
    font-size: .75rem; font-weight: 800; color: #6D28D9;
    text-transform: uppercase; letter-spacing: .1em;
}

/* ── Result Card ──────────────────────────────────────────────────── */
.validador-result-card {
    background: #fff;
    border: 1.5px solid #E5E7EB;
    border-radius: 1.1rem;
    margin-bottom: .9rem;
    overflow: hidden;
    box-shadow: 0 2px 10px rgba(0,0,0,.04);
    transition: box-shadow .2s, border-color .2s;
}
.validador-result-card:hover {
    box-shadow: 0 6px 24px rgba(109,40,217,.1);
    border-color: #C4B5FD;
}
.validador-result-header {
    display: flex; align-items: center; gap: 1rem;
    padding: 1.1rem 1.4rem;
    border-bottom: 1px solid #F3F4F6;
    background: linear-gradient(135deg, #FAFAFA 0%, #F5F3FF 100%);
}
.validador-result-icon {
    width: 42px; height: 42px; border-radius: 50%;
    background: linear-gradient(135deg, #7C3AED, #4C1D95);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.1rem; color: #fff; flex-shrink: 0;
}
.validador-result-name {
    font-size: .95rem; font-weight: 700; color: #111827; margin: 0 0 .2rem;
    flex: 1;
}
.validador-result-badge {
    background: #EDE9FE; color: #6D28D9;
    font-size: .67rem; font-weight: 700;
    padding: .22rem .65rem; border-radius: 99px;
    white-space: nowrap;
    text-transform: uppercase;
}
.validador-result-body {
    padding: 1.1rem 1.4rem;
}

/* ── Status badges ─────────────────────────────────────────────────── */
.badge-sucesso {
    background: #dcfce7;
    color: #166534;
    padding: 0.35rem 0.9rem;
    border-radius: 99px;
    font-size: 0.75rem;
    font-weight: 700;
}
.badge-erro {
    background: #fee2e2;
    color: #991b1b;
    padding: 0.35rem 0.9rem;
    border-radius: 99px;
    font-size: 0.75rem;
    font-weight: 700;
}
.badge-processando {
    background: #fef3c7;
    color: #92400e;
    padding: 0.35rem 0.9rem;
    border-radius: 99px;
    font-size: 0.75rem;
    font-weight: 700;
}

/* ── Metric Cards ────────────────────────────────────────────────── */
.validador-metric-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin-bottom: 1.5rem;
}
.validador-metric-card {
    background: #fff;
    border-radius: 1rem;
    padding: 1.25rem;
    text-align: center;
    border: 1px solid #E5E7EB;
    box-shadow: 0 2px 8px rgba(0,0,0,.04);
}
.validador-metric-value {
    font-size: 1.5rem; font-weight: 800; color: #7C3AED;
    margin-bottom: 0.25rem;
}
.validador-metric-label {
    font-size: 0.75rem; color: #6B7280; font-weight: 600;
}

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
}
[data-testid="stExpander"] summary:hover {
    box-shadow: 0 4px 16px rgba(109,40,217,.12) !important;
    border-color: #C4B5FD !important;
}

/* ── Categoria tag ────────────────────────────────────────────────── */
.categoria-tag {
    display: inline-flex; align-items: center; gap: .4rem;
    background: #F5F3FF; border: 1px solid #DDD6FE;
    border-radius: .6rem; padding: .4rem .85rem;
    font-size: .78rem; font-weight: 600; color: #6D28D9;
    margin-right: .5rem; margin-bottom: .5rem;
}

/* ── Tabela Compacta de Resultados ───────────────────────────────── */
.validador-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 0.85rem;
}
.validador-table th {
    background: linear-gradient(135deg, #F5F3FF 0%, #EDE9FE 100%);
    color: #6D28D9;
    font-weight: 700;
    padding: 0.75rem 1rem;
    text-align: left;
    border-bottom: 2px solid #C4B5FD;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.validador-table td {
    padding: 0.6rem 1rem;
    border-bottom: 1px solid #E5E7EB;
    vertical-align: middle;
}
.validador-table tr:hover td {
    background: #FAFAFA;
}
.validador-table tr.sucesso:hover td {
    background: #F0FDF4;
}
.validador-table tr.erro:hover td {
    background: #FEF2F2;
}
.validador-table .col-icone { width: 40px; text-align: center; }
.validador-table .col-arquivo { min-width: 180px; }
.validador-table .col-categoria { width: 140px; }
.validador-table .col-novo-nome { min-width: 200px; }
.validador-table .col-acao { width: 80px; text-align: center; }

.validador-arquivo-original {
    font-weight: 600;
    color: #374151;
    font-size: 0.8rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 180px;
}
.validador-novo-nome {
    font-weight: 700;
    color: #111827;
    font-size: 0.8rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}
.validador-badge-mini {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 99px;
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    white-space: nowrap;
}
.validador-badge-mini.sucesso {
    background: #dcfce7;
    color: #166534;
}
.validador-badge-mini.erro {
    background: #fee2e2;
    color: #991b1b;
}
.validador-badge-mini.aviso {
    background: #fef3c7;
    color: #92400e;
}
.validador-ref-tag {
    display: inline-block;
    background: #FEF3C7;
    color: #92400E;
    padding: 0.1rem 0.4rem;
    border-radius: 99px;
    font-size: 0.6rem;
    font-weight: 600;
    margin-left: 0.3rem;
}
.validador-pdf-tag {
    display: inline-block;
    background: #10B981;
    color: white;
    padding: 0.1rem 0.35rem;
    border-radius: 99px;
    font-size: 0.6rem;
    font-weight: 700;
}

/* ── Empty state ──────────────────────────────────────────────────── */
.validador-empty {
    text-align: center; padding: 3rem 1rem;
    color: #9CA3AF;
}
.validador-empty-icon { font-size: 3rem; margin-bottom: 1rem; }
.validador-empty-text { font-size: 1rem; color: #6B7280; font-weight: 600; }
</style>
"""

# ================================================================
#  IMAGEM
# ================================================================

def melhorar_imagem(img: Image.Image) -> Image.Image:
    """Melhora a qualidade da imagem para OCR."""
    img = img.convert("RGB")
    img = ImageEnhance.Contrast(img).enhance(1.5)
    img = ImageEnhance.Sharpness(img).enhance(2.0)
    return img

def imagem_para_base64(img: Image.Image) -> str:
    """Converte imagem PIL para base64."""
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=92)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

def carregar_imagem(uploaded_file) -> Image.Image:
    """Carrega imagem de um arquivo uploadado pelo Streamlit. Suporta JPG, PNG e PDF."""
    # Obtém o nome do arquivo para verificar a extensão
    nome_arquivo = uploaded_file.name.lower()
    
    # Se for PDF, converte para imagem usando PyMuPDF (fitz)
    if nome_arquivo.endswith('.pdf'):
        # Lê o conteúdo do arquivo
        pdf_bytes = uploaded_file.read()
        # Abre o PDF com PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if len(doc) == 0:
            raise ValueError("PDF vazio ou não foi possível abrir")
        
        # Renderiza a primeira página em alta resolução
        page = doc[0]
        mat = fitz.Matrix(2, 2)  # Escala 2x para melhor qualidade
        pix = page.get_pixmap(matrix=mat)
        
        # Converte para PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc.close()
    else:
        # Para JPG, PNG, etc. abre diretamente
        img = Image.open(uploaded_file)
    
    return melhorar_imagem(img)

def converter_para_pdf(img: Image.Image) -> bytes:
    """Converte imagem para PDF."""
    buffer = io.BytesIO()
    if img.mode in ('RGBA', 'LA', 'P'):
        img = img.convert('RGB')
    img.save(buffer, format="PDF", resolution=100.0)
    buffer.seek(0)
    return buffer.getvalue()

# ================================================================
#  CLASSIFICAÇÃO
# ================================================================

def classificar_imagem(img: Image.Image, client: Groq) -> dict:
    """
    Chama o Groq Vision e retorna dict com 'categoria' e 'referencia'.
    """
    b64 = imagem_para_base64(img)
    
    try:
        resposta = client.chat.completions.create(
            model=MODELO,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text",      "text": PROMPT},
                ],
            }],
            max_tokens=80,
            temperature=0,
        )
        
        raw = resposta.choices[0].message.content.strip()
        
        # Remove blocos markdown se o modelo retornar ```json ... ```
        raw = re.sub(r"```(?:json)?|```", "", raw).strip()
        
        try:
            resultado = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r'"categoria"\s*:\s*"([^"]+)"', raw)
            categoria = match.group(1).upper() if match else "DOCUMENTO_DESCONHECIDO"
            resultado = {"categoria": categoria, "referencia": None}
        
        # Valida categoria
        categoria = resultado.get("categoria", "").upper().strip()
        if categoria not in CATEGORIAS_VALIDAS:
            categoria = "DOCUMENTO_DESCONHECIDO"
        
        resultado["categoria"] = categoria
        return resultado
        
    except Exception as e:
        st.error(f"Erro na classificação: {e}")
        return {"categoria": "DOCUMENTO_DESCONHECIDO", "referencia": None}

def montar_nome_final(resultado: dict) -> str:
    """
    Constrói o nome do arquivo conforme padrão Banksoft (sem extensão).
    """
    categoria = resultado["categoria"]
    referencia = resultado.get("referencia")
    
    if categoria == "HOLERITE" and referencia:
        ref = str(referencia).upper().strip()
        for nome, abrev in MESES_PT.items():
            ref = ref.replace(nome.upper(), abrev)
        ref = re.sub(r"[^A-Z0-9_]", "_", ref).strip("_")
        nome_final = f"HOLERITE_{ref}"
    else:
        nome_final = categoria
    
    return nome_final

# ================================================================
#  RENDERIZAÇÃO DA PÁGINA
# ================================================================

def render_validador_page():
    """Renderiza a página de validação de arquivos."""
    
    # Aplica CSS
    st.markdown(_CSS, unsafe_allow_html=True)
    
    # Header Hero
    st.markdown("""
    <div class="validador-hero">
        <div class="validador-hero-title">Validador de Documentos</div>
        <p class="validador-hero-sub">
            Classificação automática de documentos com a Stella. Upload múltiplo, renomeação inteligente e conversão automática para PDF.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Inicializa session state
    if "arquivos_processados" not in st.session_state:
        st.session_state.arquivos_processados = []
    if "processando" not in st.session_state:
        st.session_state.processando = False
    
    # Verifica API key
    api_key = _get_groq_key()
    if not api_key or api_key == "sua-chave-aqui":
        st.error("⚠️ Chave da API Groq não configurada. Contate o administrador.")
        return
    
    # Expander "Como usar"
    with st.expander("ℹ️ Como usar — clique para expandir", expanded=False):
        st.markdown("""
        <div style="padding: 0.25rem 0;">
            <ol style="color: #374151; line-height: 2; font-size: 0.95rem; padding-left: 1.2rem;">
                <li><strong>Faça upload</strong> dos documentos (JPG, PNG, PDF).</li>
                <li>Clique em <strong>"Iniciar Classificação"</strong> para processar.</li>
                <li>A Stella identifica o tipo de cada documento automaticamente.</li>
                <li><strong>Baixe os arquivos renomeados</strong> em formato PDF padronizado.</li>
            </ol>
            <div style="background-color: #FFF7ED; border-left: 5px solid #F97316; border-radius: 0.75rem; padding: 1rem 1.25rem; margin-top: 1rem;">
                <p style="font-size: 0.9rem; color: #7C2D12; margin: 0;">
                    <strong>⚠️ Conversão automática:</strong> Todos os arquivos são convertidos para PDF durante o processamento.
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Layout em colunas
    col_upload, col_info = st.columns([2, 1])
    
    with col_upload:
        st.markdown("<div class='validador-upload-card'> <div style='font-size: 0.75rem; font-weight: 800; color: #7C3AED; text-transform: uppercase; letter-spacing: 0.1em;'>📤 Upload de Documentos</div> </div>", unsafe_allow_html=True)
        st.markdown("", unsafe_allow_html=True)
        
        uploaded_files = st.file_uploader(
            "Selecione os arquivos",
            type=["jpg", "jpeg", "png", "pdf"],
            accept_multiple_files=True,
            label_visibility="collapsed"
        )
        
        if uploaded_files:
            st.info(f"📦 {len(uploaded_files)} arquivo(s) selecionado(s)")
            
            cols = st.columns([3, 2])
            with cols[0]:
                if st.button("🚀 Iniciar Classificação", type="primary", use_container_width=True):
                    st.session_state.processando = True
                    st.session_state.arquivos_processados = []
                    st.rerun()
            with cols[1]:
                if st.button("🗑️ Limpar", type="secondary", use_container_width=True):
                    st.session_state.arquivos_processados = []
                    st.session_state.processando = False
                    st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col_info:
        st.markdown("<div class='validador-info-card'> <div class='validador-info-title'>📖 Categorias</div> </div> ", unsafe_allow_html=True)
        st.markdown("", unsafe_allow_html=True)
        
        categorias_resumo = [
            ("🆔", "ID Frente/Verso", "RG, CNH"),
            ("🏠", "Endereço", "Contas de serviços"),
            ("💰", "Holerite", "Contracheque"),
            ("🤳", "Selfie", "Foto do cliente"),
            ("🏦", "Bancário", "Extrato, dados"),
        ]
        
        for icone, nome, desc in categorias_resumo:
            st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0; border-bottom: 1px solid #E5E7EB;">
                <span style="font-size: 1.1rem;">{icone}</span>
                <div>
                    <div style="font-weight: 600; color: #111827; font-size: 0.8rem;">{nome}</div>
                    <div style="font-size: 0.7rem; color: #6B7280;">{desc}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Processamento
    if st.session_state.processando and uploaded_files:
        st.markdown("---")
        st.markdown("### 🔄 Processando documentos...")
        
        client = Groq(api_key=api_key)
        progress_bar = st.progress(0)
        
        arquivos_resultado = []
        
        for idx, uploaded_file in enumerate(uploaded_files):
            progress = (idx + 1) / len(uploaded_files)
            progress_bar.progress(progress, text=f"Processando {uploaded_file.name}...")
            
            try:
                img = carregar_imagem(uploaded_file)
                resultado = classificar_imagem(img, client)
                nome_base = montar_nome_final(resultado)
                novo_nome = f"{nome_base}.pdf"
                pdf_bytes = converter_para_pdf(img)
                
                arquivos_resultado.append({
                    "original": uploaded_file.name,
                    "novo_nome": novo_nome,
                    "nome_base": nome_base,
                    "categoria": resultado["categoria"],
                    "referencia": resultado.get("referencia"),
                    "pdf_bytes": pdf_bytes,
                    "sucesso": True
                })
                
            except Exception as e:
                arquivos_resultado.append({
                    "original": uploaded_file.name,
                    "novo_nome": f"ERRO_{uploaded_file.name}",
                    "nome_base": "ERRO",
                    "categoria": "ERRO",
                    "referencia": None,
                    "pdf_bytes": None,
                    "sucesso": False,
                    "erro": str(e)
                })
        
        progress_bar.empty()
        st.session_state.arquivos_processados = arquivos_resultado
        st.session_state.processando = False
        st.success("✅ Processamento concluído! Todos os arquivos foram convertidos para PDF.")
        st.rerun()
    
    # Exibe resultados
    if st.session_state.arquivos_processados:
        st.markdown("---")
        
        arquivos = st.session_state.arquivos_processados
        sucessos = sum(1 for a in arquivos if a["sucesso"])
        com_pdf = [a for a in arquivos if a.get("pdf_bytes")]
        
        st.markdown("### 📊 Resultados da Classificação")

        # Métricas compactas
        cols = st.columns(3)
        metricas = [
            (len(arquivos), "Total", "📦"),
            (sucessos, "Classificados", "✅"),
            (len(arquivos) - sucessos, "Erros", "❌"),
        ]
        for col, (valor, label, icone) in zip(cols, metricas):
            with col:
                st.metric(label=f"{icone} {label}", value=str(valor))
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Tabela compacta de resultados
        icones_categoria = {
            "DOCUMENTO_DE_IDENTIFICACAO": "🆔",
            "DOCUMENTO_DE_IDENTIFICACAO_VERSO": "🆔",
            "COMPROVANTE_DE_ENDERECO": "🏠",
            "COMPLEMENTO_ENDERECO": "🏠",
            "HOLERITE": "💰",
            "SELFIE": "🤳",
            "DADOS_BANCARIOS": "🏦",
            "RESERVA_MARGEM": "📋",
            "TOKEN": "🔑",
            "DOCUMENTO_DESCONHECIDO": "❓",
            "ERRO": "⚠️",
        }
        
        # Constrói HTML da tabela
        linhas_tabela = []
        for arquivo in arquivos:
            icone = icones_categoria.get(arquivo["categoria"], "📄")
            
            if arquivo["sucesso"]:
                if arquivo["categoria"] == "DOCUMENTO_DESCONHECIDO":
                    badge_class = "aviso"
                    badge_text = "Não Identificado"
                else:
                    badge_class = "sucesso"
                    badge_text = arquivo["categoria"].replace("_", " ")[:20]
                
                ref_tag = ""
                if arquivo.get("referencia"):
                    ref_tag = f'<span class="validador-ref-tag">{arquivo["referencia"]}</span>'
                
                status_cell = f'<span class="validador-badge-mini {badge_class}">{badge_text}</span>'
                novo_nome_cell = f'<div class="validador-novo-nome">{arquivo["novo_nome"]}<span class="validador-pdf-tag">PDF</span>{ref_tag}</div>'
                
                linhas_tabela.append({
                    "original": arquivo["original"],
                    "categoria": arquivo["categoria"],
                    "novo_nome": arquivo["novo_nome"],
                    "pdf_bytes": arquivo.get("pdf_bytes"),
                    "sucesso": True,
                    "html": f'''<tr class="sucesso">
                        <td class="col-icone">{icone}</td>
                        <td class="col-arquivo"><div class="validador-arquivo-original" title="{arquivo["original"]}">{arquivo["original"]}</div></td>
                        <td class="col-categoria">{status_cell}</td>
                        <td class="col-novo-nome">{novo_nome_cell}</td>
                    </tr>'''
                })
            else:
                status_cell = '<span class="validador-badge-mini erro">Erro</span>'
                erro_msg = arquivo.get('erro', 'Erro desconhecido')[:50]
                
                linhas_tabela.append({
                    "original": arquivo["original"],
                    "categoria": "ERRO",
                    "novo_nome": "",
                    "pdf_bytes": None,
                    "sucesso": False,
                    "html": f'''<tr class="erro">
                        <td class="col-icone">⚠️</td>
                        <td class="col-arquivo"><div class="validador-arquivo-original" title="{arquivo["original"]}">{arquivo["original"]}</div></td>
                        <td class="col-categoria">{status_cell}</td>
                        <td class="col-novo-nome" style="color: #DC2626; font-size: 0.75rem;">{erro_msg}</td>
                    </tr>'''
                })
        
        # Tabela compacta de resultados (HTML puro - mais enxuto)
        icones_categoria = {
            "DOCUMENTO_DE_IDENTIFICACAO": "🆔",
            "DOCUMENTO_DE_IDENTIFICACAO_VERSO": "🆔",
            "COMPROVANTE_DE_ENDERECO": "🏠",
            "COMPLEMENTO_ENDERECO": "🏠",
            "HOLERITE": "💰",
            "SELFIE": "🤳",
            "DADOS_BANCARIOS": "🏦",
            "RESERVA_MARGEM": "📋",
            "TOKEN": "🔑",
            "DOCUMENTO_DESCONHECIDO": "❓",
            "ERRO": "⚠️",
        }
        
        # Constrói linhas da tabela HTML
        linhas_html = []
        arquivos_com_download = []
        
        for idx, arquivo in enumerate(arquivos):
            icone = icones_categoria.get(arquivo["categoria"], "📄")
            
            if arquivo["sucesso"]:
                if arquivo["categoria"] == "DOCUMENTO_DESCONHECIDO":
                    badge_class = "aviso"
                    badge_text = "Não Identif."
                else:
                    badge_class = "sucesso"
                    badge_text = arquivo["categoria"].replace("_", " ")[:18]
                
                ref_tag = ""
                if arquivo.get("referencia"):
                    ref_tag = f'<span class="validador-ref-tag">{arquivo["referencia"]}</span>'
                
                nome_curto = arquivo["original"][:25] + "..." if len(arquivo["original"]) > 25 else arquivo["original"]
                novo_nome_curto = arquivo["novo_nome"][:30] + "..." if len(arquivo["novo_nome"]) > 30 else arquivo["novo_nome"]
                
                linhas_html.append(f'''<tr class="sucesso">
                    <td class="col-icone">{icone}</td>
                    <td class="col-arquivo" title="{arquivo['original']}">{nome_curto}</td>
                    <td class="col-categoria"><span class="validador-badge-mini {badge_class}">{badge_text}</span></td>
                    <td class="col-novo-nome"><div class="validador-novo-nome">{novo_nome_curto}<span class="validador-pdf-tag">PDF</span>{ref_tag}</div></td>
                </tr>''')
                
                if arquivo.get("pdf_bytes"):
                    arquivos_com_download.append({
                        "idx": idx,
                        "original": arquivo["original"],
                        "novo_nome": arquivo["novo_nome"],
                        "pdf_bytes": arquivo["pdf_bytes"]
                    })
            else:
                nome_curto = arquivo["original"][:25] + "..." if len(arquivo["original"]) > 25 else arquivo["original"]
                erro_curto = arquivo.get('erro', 'Erro')[:25]
                
                linhas_html.append(f'''<tr class="erro">
                    <td class="col-icone">⚠️</td>
                    <td class="col-arquivo" title="{arquivo['original']}">{nome_curto}</td>
                    <td class="col-categoria"><span class="validador-badge-mini erro">Erro</span></td>
                    <td class="col-novo-nome" style="color: #DC2626; font-size: 0.7rem;">{erro_curto}</td>
                </tr>''')
        
        # Tabela HTML pura (compacta)
        icones_categoria = {
            "DOCUMENTO_DE_IDENTIFICACAO": "🆔",
            "DOCUMENTO_DE_IDENTIFICACAO_VERSO": "🆔",
            "COMPROVANTE_DE_ENDERECO": "🏠",
            "COMPLEMENTO_ENDERECO": "🏠",
            "HOLERITE": "💰",
            "SELFIE": "🤳",
            "DADOS_BANCARIOS": "🏦",
            "RESERVA_MARGEM": "📋",
            "TOKEN": "🔑",
            "DOCUMENTO_DESCONHECIDO": "❓",
            "ERRO": "⚠️",
        }
        
        # Constrói tabela HTML com todas as colunas (incluindo Download placeholder)
        # Constrói tabela HTML com download via data URI (base64 embutido)
        linhas_html = []

        for idx, arquivo in enumerate(arquivos):
            icone = icones_categoria.get(arquivo["categoria"], "📄")

            if arquivo["sucesso"]:
                badge_class = "aviso" if arquivo["categoria"] == "DOCUMENTO_DESCONHECIDO" else "sucesso"
                badge_text = "Não Identif." if arquivo["categoria"] == "DOCUMENTO_DESCONHECIDO" else arquivo["categoria"].replace("_", " ")[:16]

                ref_tag = f'<span class="validador-ref-tag">{arquivo["referencia"]}</span>' if arquivo.get("referencia") else ""
                nome_curto = arquivo["original"][:22] + "..." if len(arquivo["original"]) > 22 else arquivo["original"]
                novo_nome_curto = arquivo["novo_nome"][:28] + "..." if len(arquivo["novo_nome"]) > 28 else arquivo["novo_nome"]

                if arquivo.get("pdf_bytes"):
                    b64_pdf = base64.b64encode(arquivo["pdf_bytes"]).decode("utf-8")
                    download_cell = f'''
                        <a href="data:application/pdf;base64,{b64_pdf}"
                           download="{arquivo["novo_nome"]}"
                           style="display:inline-flex; align-items:center; gap:0.3rem;
                                  background: linear-gradient(135deg,#7C3AED,#4C1D95);
                                  color:#fff; font-size:0.72rem; font-weight:700;
                                  padding:0.35rem 0.75rem; border-radius:99px;
                                  text-decoration:none; white-space:nowrap;
                                  box-shadow: 0 2px 6px rgba(109,40,217,.3);
                                  transition: opacity .15s;">
                            ⬇️ Baixar
                        </a>'''
                else:
                    download_cell = '<span style="color:#9CA3AF;">—</span>'

                linhas_html.append(f'''<tr>
                    <td style="text-align:center; padding:0.5rem 0.4rem; border-bottom:1px solid #F3F4F6;">{icone}</td>
                    <td style="padding:0.5rem 0.6rem; border-bottom:1px solid #F3F4F6; font-size:0.78rem; color:#374151; font-weight:600;" title="{arquivo['original']}">{nome_curto}</td>
                    <td style="padding:0.5rem 0.6rem; border-bottom:1px solid #F3F4F6; text-align:center;"><span class="validador-badge-mini {badge_class}">{badge_text}</span></td>
                    <td style="padding:0.5rem 0.6rem; border-bottom:1px solid #F3F4F6;"><div class="validador-novo-nome">{novo_nome_curto}<span class="validador-pdf-tag">PDF</span>{ref_tag}</div></td>
                    <td style="padding:0.5rem 0.6rem; border-bottom:1px solid #F3F4F6; text-align:center;">{download_cell}</td>
                </tr>''')

            else:
                nome_curto = arquivo["original"][:22] + "..." if len(arquivo["original"]) > 22 else arquivo["original"]
                erro_curto = arquivo.get('erro', 'Erro')[:25]
                linhas_html.append(f'''<tr>
                    <td style="text-align:center; padding:0.5rem 0.4rem; border-bottom:1px solid #F3F4F6;">⚠️</td>
                    <td style="padding:0.5rem 0.6rem; border-bottom:1px solid #F3F4F6; font-size:0.78rem; color:#374151;" title="{arquivo['original']}">{nome_curto}</td>
                    <td style="padding:0.5rem 0.6rem; border-bottom:1px solid #F3F4F6; text-align:center;"><span class="validador-badge-mini erro">Erro</span></td>
                    <td style="padding:0.5rem 0.6rem; border-bottom:1px solid #F3F4F6; color:#DC2626; font-size:0.72rem;">{erro_curto}</td>
                    <td style="padding:0.5rem 0.6rem; border-bottom:1px solid #F3F4F6; text-align:center;"><span style="color:#9CA3AF;">—</span></td>
                </tr>''')

        tabela_html = f'''
        <table style="width:100%; border-collapse:collapse; font-size:0.82rem; font-family:'Inter',sans-serif;">
            <thead>
                <tr style="background: linear-gradient(135deg, #F5F3FF 0%, #EDE9FE 100%);">
                    <th style="padding:0.55rem 0.4rem; width:40px; border-bottom:2px solid #C4B5FD;"></th>
                    <th style="padding:0.55rem 0.6rem; text-align:left; font-size:0.65rem; color:#6D28D9; text-transform:uppercase; letter-spacing:.06em; border-bottom:2px solid #C4B5FD;">Arquivo Original</th>
                    <th style="padding:0.55rem 0.6rem; width:130px; text-align:center; font-size:0.65rem; color:#6D28D9; text-transform:uppercase; letter-spacing:.06em; border-bottom:2px solid #C4B5FD;">Categoria</th>
                    <th style="padding:0.55rem 0.6rem; text-align:left; font-size:0.65rem; color:#6D28D9; text-transform:uppercase; letter-spacing:.06em; border-bottom:2px solid #C4B5FD;">Novo Nome</th>
                    <th style="padding:0.55rem 0.6rem; width:110px; text-align:center; font-size:0.65rem; color:#6D28D9; text-transform:uppercase; letter-spacing:.06em; border-bottom:2px solid #C4B5FD;">Download</th>
                </tr>
            </thead>
            <tbody>
                {''.join(linhas_html)}
            </tbody>
        </table>
        '''
        st.markdown(tabela_html, unsafe_allow_html=True)
        
    
        st.markdown("<br>", unsafe_allow_html=True)
        col_novo, col_baixar = st.columns(2)

        with col_novo:
            if st.button("🔄 Processar Novos Arquivos", type="secondary", use_container_width=True):
                st.session_state.arquivos_processados = []
                st.rerun()

        with col_baixar:
            if com_pdf:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for arquivo in com_pdf:
                        zip_file.writestr(arquivo["novo_nome"], arquivo["pdf_bytes"])
                zip_buffer.seek(0)
                st.download_button(
                    label=f"⬇️ Baixar Todos ({len(com_pdf)})",
                    data=zip_buffer.getvalue(),
                    file_name="documentos_classificados.zip",
                    mime="application/zip",
                    use_container_width=True,
                    type="primary"
                )
