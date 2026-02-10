"""
Analisador de Holerite - Aplicação Streamlit
Sistema de Identificação de Oportunidades de Compra de Dívida

Para executar:
streamlit run app.py
"""

import streamlit as st
import re
import io
from typing import List, Dict
import PyPDF2
import pdfplumber
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List
import re as _re
import unicodedata

# ============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================================

st.set_page_config(
    page_title="Analisador de Holerite",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded" 
)

# ============================================================================
# CSS CUSTOMIZADO
# ============================================================================

# ============================================================================
# CSS CUSTOMIZADO - TEMA ROXO MODERNO (ATUALIZADO)
# ============================================================================

st.markdown("""
    <style>
        /* Importação da Fonte Inter */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        /* --- GLOBAL --- */
        * {
            font-family: 'Inter', sans-serif;
        }
        
        .stApp {
            background-color: #FFFFFF;
        }

        /* --- SIDEBAR CUSTOMIZADA --- */
        [data-testid="stSidebar"] {
            background-color: #F8FAFC; /* Fundo cinza muito suave */
            border-right: 1px solid #E2E8F0; /* Divisória sutil */
            padding-top: 2rem;
        }
        
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            color: #4C1D95; /* Roxo escuro para títulos na sidebar */
            font-weight: 700;
        }
        
        /* Inputs na Sidebar (Selectbox, Text Input) */
        [data-testid="stSidebar"] .stSelectbox > div > div {
            background-color: #FFFFFF;
            border: 1px solid #CBD5E1;
            border-radius: 0.5rem;
            color: #334155;
        }

        /* --- CABEÇALHO --- */
        .main-header {
            font-size: 3rem;
            font-weight: 800;
            background: linear-gradient(135deg, #7C3AED 0%, #4C1D95 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            margin-bottom: 0.5rem;
            letter-spacing: -1px;
            padding-bottom: 10px;
        }
        
        .main-subtitle {
            text-align: center;
            font-size: 1.1rem;
            color: #64748B;
            margin-bottom: 3rem;
            font-weight: 400;
        }
        
        /* --- FILE UPLOADER COM HOVER DISCRETO --- */
        [data-testid="stFileUploader"] {
            padding: 2rem;
            border-radius: 1rem;
            background-color: #FFFFFF;
            border: 2px dashed #E2E8F0; /* Borda cinza padrão */
            transition: all 0.3s ease-in-out;
            cursor: pointer;
        }
        
        /* Efeito Hover Roxo */
        [data-testid="stFileUploader"]:hover {
            border-color: #8B5CF6; /* Roxo médio */
            background-color: #F5F3FF; /* Roxo muito claro (Lilás) */
        }
        
        [data-testid="stFileUploader"] section {
            background-color: transparent !important; /* Garante que o fundo do hover funcione */
        }

        /* --- CARDS DE MÉTRICAS --- */
        .metric-card {
            background: #FFFFFF;
            padding: 1.5rem;
            border-radius: 1rem;
            border: 1px solid #F1F5F9;
            border-left: 5px solid #7C3AED;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            margin-bottom: 1rem;
        }
        
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(124, 58, 237, 0.1);
        }
        
        /* --- CAIXAS DE STATUS (TONS PASTÉIS) --- */
        .success-box, .warning-box, .info-box, .error-box {
            padding: 1rem;
            border-radius: 0.75rem;
            margin: 1rem 0;
            font-weight: 500;
        }
        
        .success-box { background-color: #ECFDF5; border-left: 4px solid #10B981; color: #065F46; }
        .warning-box { background-color: #FFFBEB; border-left: 4px solid #F59E0B; color: #92400E; }
        .info-box    { background-color: #EFF6FF; border-left: 4px solid #3B82F6; color: #1E40AF; }
        .error-box   { background-color: #FEF2F2; border-left: 4px solid #EF4444; color: #991B1B; }
        
        /* --- BOTÕES --- */
        .stButton > button {
            background: linear-gradient(135deg, #7C3AED 0%, #6D28D9 100%);
            color: white;
            border: none;
            border-radius: 0.75rem;
            padding: 0.75rem 1.5rem;
            font-weight: 600;
            box-shadow: 0 4px 6px rgba(124, 58, 237, 0.25);
            transition: all 0.3s ease;
            width: 100%;
        }
        
        .stButton > button:hover {
            box-shadow: 0 6px 12px rgba(124, 58, 237, 0.35);
            transform: translateY(-1px);
        }

        /* --- HEADERS DE SEÇÃO --- */
        .section-header {
            font-size: 1.5rem;
            font-weight: 700;
            color: #334155;
            margin-top: 2rem;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
        }
        
        /* --- RODAPÉ --- */
        .footer-text {
            text-align: center;
            color: #94A3B8;
            padding: 3rem 0;
            font-size: 0.875rem;
            border-top: 1px solid #F1F5F9;
            margin-top: 3rem;
        }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# BASE DE DADOS DE CARTÕES CONHECIDOS
# ============================================================================

# Nossos produtos/contratos
NOSSOS_PRODUTOS = [
    "STARCARD",
    "ANTICIPAY",
    "STARBANK",
    "UASPREV"
]

# Cartões de terceiros (concorrentes)
CARTOES_CONHECIDOS = [
    "NIO",
    "DAYCOVAL",
    "BMG",
    "PAN",
    "MEUCASHCARD",
    "PINE",
    "BRADESCO",
    "SANTANDER / OLÉ",
    "BIG CARD",
    "DAYC",
    "IND",
    "PANAMERICANO",
    "MASTER",
    "CREDCESTA SAQUE"
]

CARTOES_NAO_COMPRADOS = [
    "CREDCESTA COMPRA", 
    "QISTA",
    "PIX CARD",
    "C CONSIG",
    "CAPITAL",
    "MAXIMA",
    "FY DIGITAL",
    "CLICKBANK",
    "PIXCARD",
    "VEMCARD"
]

CARTOES_DESCONHECIDOS = [
    "CREDIFIN - CARTAO SAQUE",
    "FY DIGITAL"
]

# Lista completa para busca
TODOS_CARTOES = NOSSOS_PRODUTOS + CARTOES_CONHECIDOS

# ============================================================================
# FUNÇÕES DE EXTRAÇÃO DE TEXTO
# ============================================================================

@st.cache_data
def extrair_texto_pdf_pypdf2(arquivo_bytes: bytes) -> str:
    """Extrai texto do PDF usando PyPDF2"""
    texto_completo = ""
    try:
        pdf_file = io.BytesIO(arquivo_bytes)
        leitor = PyPDF2.PdfReader(pdf_file)
        for pagina in leitor.pages:
            texto_completo += pagina.extract_text() + "\n"
    except Exception as e:
        st.error(f"Erro ao extrair com PyPDF2: {e}")
    return texto_completo

@st.cache_data
def extrair_texto_pdf_pdfplumber(arquivo_bytes: bytes) -> str:
    """Extrai texto do PDF usando pdfplumber"""
    texto_completo = ""
    try:
        pdf_file = io.BytesIO(arquivo_bytes)
        with pdfplumber.open(pdf_file) as pdf:
            for pagina in pdf.pages:
                texto = pagina.extract_text()
                if texto:
                    texto_completo += texto + "\n"
    except Exception as e:
        st.error(f"Erro ao extrair com pdfplumber: {e}")
    return texto_completo

def extrair_texto_pdf(arquivo_bytes: bytes) -> str:
    """Tenta extrair texto usando ambos os métodos"""
    texto = extrair_texto_pdf_pdfplumber(arquivo_bytes)
    if not texto.strip():
        texto = extrair_texto_pdf_pypdf2(arquivo_bytes)
    return texto

# ============================================================================
# FUNÇÕES DE ANÁLISE
# ============================================================================

def normalizar_texto(texto: str) -> str:
    """Normaliza o texto removendo acentos e convertendo para maiúsculas"""
    texto = texto.upper()
    acentos = {
        'Á': 'A', 'À': 'A', 'Ã': 'A', 'Â': 'A',
        'É': 'E', 'Ê': 'E',
        'Í': 'I',
        'Ó': 'O', 'Õ': 'O', 'Ô': 'O',
        'Ú': 'U',
        'Ç': 'C'
    }
    for acentuado, sem_acento in acentos.items():
        texto = texto.replace(acentuado, sem_acento)
    return texto

def extrair_regime_contrato(texto: str) -> str:
    """Identifica o regime de contrato do servidor"""
    texto_normalizado = normalizar_texto(texto)
    
    if "ESTATUTARIO" in texto_normalizado or "ESTATUARIO" in texto_normalizado or "EFETIVO " in texto_normalizado or "EFETIVOS " in texto_normalizado or "EFETIVO-HORISTA" in texto_normalizado:
        return "ESTATUTÁRIO"
    elif "CLT" in texto_normalizado:
        return "CELETISTA"
    elif "C.L.T." in texto_normalizado:
        return "CELETISTA"
    elif "COMISSIONADO" in texto_normalizado:
        return "COMISSIONADO"
    elif "COMISSAO" in texto_normalizado:
        return "COMISSIONADO"
    elif "TEMPORARIO" in texto_normalizado or "TEMPORÁRIO" in texto_normalizado or "Contrato Temporario" in texto_normalizado:
        return "TEMPORÁRIO"
    elif "CONTRATADO" in texto_normalizado: 
        return "CONTRATADO"
    else:
        return "NÃO IDENTIFICADO"

# ============================================================================
# CONFIGURAÇÃO DE PREFEITURAS
# ============================================================================

# Adicionar Bauru na configuração de prefeituras (linha ~186)
PREFEITURAS = {
    'POA': {
        'nome': 'Prefeitura de Poá - SP',
        'descricao': 'Cidade: Poá - São Paulo'
    },
    'MARINGA': {
        'nome': 'Prefeitura de Maringá - PR',
        'descricao': 'Cidade: Maringá - Paraná'
    },
    'SOROCABA': {
        'nome': 'Prefeitura de Sorocaba - SP',
        'descricao': 'Cidade: Sorocaba - São Paulo'
    },
    'COTIA': {
        'nome': 'Prefeitura de Cotia - SP',
        'descricao': 'Cidade: Cotia - São Paulo'
    },
    'IMPERATRIZ': {
        'nome': 'Prefeitura de Imperatriz - MA',
        'descricao': 'Cidade: Imperatriz - Maranhão'
    },
    'EMBU': {
        'nome': 'Prefeitura de Embu das Artes - SP',
        'descricao': 'Cidade: Embu das Artes - São Paulo'
    },
    'HORTOLANDIA': {
        'nome': 'Prefeitura de Hortolândia - SP',
        'descricao': 'Cidade: Hortolândia - São Paulo'
    },
    'BAURU': {
        'nome': 'Prefeitura de Bauru - SP',
        'descricao': 'Cidade: Bauru - São Paulo'
    },
    'UBERABA': {
        'nome': 'Prefeitura de Uberaba - MG',
        'descricao': 'Cidade: Uberaba - Minas Gerais'
    },
    'LAGO_VERDE': {  
        'nome': 'Prefeitura de Lago Verde - MA',
        'descricao': 'Cidade: Lago Verde - Maranhão'
    },
    'TABOAO_SERRA': { 
        'nome': 'Prefeitura de Taboão da Serra - SP',
        'descricao': 'Cidade: Taboão da Serra - São Paulo'
    },
    'SALTO': {
        'nome': 'Prefeitura de Salto - SP',
        'descricao': 'Cidade: Salto - São Paulo'
    },
    'TUPA': {
        'nome': 'Prefeitura de Tupã - SP',
        'descricao': 'Cidade: Tupã - São Paulo'
    },
    'ITAITUBA': {
        'nome': 'Prefeitura de Itaituba - PA',
        'descricao': 'Cidade: Itaituba - Pará'
    },
    'BARCARENA': {
        'nome': 'Prefeitura de Barcarena - PA',
        'descricao': 'Cidade: Barcarena - Pará'
    },
    'CAMPOS_JORDAO': {
        'nome': 'Prefeitura de Campos do Jordão - SP',
        'descricao': 'Cidade: Campos do Jordão - São Paulo'
    },
    'RIBEIRAO_PRETO': {
        'nome': 'Prefeitura de Ribeirão Preto - SP',
        'descricao': 'Cidade: Ribeirão Preto - São Paulo'
    },
    'PONTA_GROSSA': {
        'nome': 'Prefeitura de Ponta Grossa - PR',
        'descricao': 'Cidade: Ponta Grossa - Paraná'
    },
    'CAMARA_DEPUTADOS': {
        'nome': 'Câmara dos Deputados',
        'descricao': 'Câmara dos Deputados - Brasília/DF'
    },
    'BELTERRA': {
        'nome': 'Prefeitura de Belterra - PA',
        'descricao': 'Cidade: Belterra - Pará'
    },
    'SAO_JOSE_RIO_PRETO': {
        'nome': 'Prefeitura de São José do Rio Preto - SP',
        'descricao': 'Cidade: São José do Rio Preto - São Paulo'
    },
    'VINHEDO': { 
        'nome': 'Prefeitura de Vinhedo - SP',
        'descricao': 'Cidade: Vinhedo - São Paulo'
    },
    'MONTE_ALEGRE_SE': {
        'nome': 'Prefeitura de Monte Alegre de Sergipe - SE',
        'descricao': 'Cidade: Monte Alegre de Sergipe - Sergipe'
    },
    'REDENCAO': {  
        'nome': 'Prefeitura de Redenção - PA',
        'descricao': 'Cidade: Redenção - Pará'
    },
    'CUIABA': { 
        'nome': 'Prefeitura de Cuiabá - MT',
        'descricao': 'Cidade: Cuiabá - Mato Grosso'
    },
    'ALEGO': {
        'nome': 'Assembleia Legislativa do Estado de Goiás - ALEGO',
        'descricao': 'Assembleia Legislativa - Goiás'
    },
    'GOVERNO_GOIAS': {
        'nome': 'Governo do Estado de Goiás',
        'descricao': 'Estado de Goiás'
    },
    
}

# ============================================================================
# FUNÇÕES ESPECÍFICAS POR PREFEITURA - GOVERNO DE GOIÁS
# ============================================================================

def extrair_informacoes_governo_goias(texto: str) -> Dict:
    """
    Extrai informações específicas do Governo de Goiás
    Estrutura: Vínculo (matrícula) / Nome / Rendimentos / Descontos / Líquido
    """
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
    }
    
    linhas = texto.split('\n')
    
    # ============================================================
    # EXTRAÇÃO DE MATRÍCULA (campo "Vínculo")
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        if 'VINCULO' in linha_norm or 'VÍNCULO' in linha_norm:
            # Formato: 588578, 625195 (6 dígitos)
            match = re.search(r'(\d{6})', linha)
            if match:
                info['matricula'] = match.group(1)
            elif i + 1 < len(linhas):
                match = re.search(r'(\d{6})', linhas[i + 1])
                if match:
                    info['matricula'] = match.group(1)
    
    # ============================================================
    # EXTRAÇÃO DE NOME
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        if 'NOME' in linha_norm and 'NOME ORGAO' not in linha_norm:
            if i + 1 < len(linhas):
                nome_candidato = linhas[i + 1].strip()
                # Remove possíveis códigos/datas
                nome_candidato = re.sub(r'\d{3}\.\d{3}\.\d{3}-\d{2}', '', nome_candidato)
                nome_candidato = re.sub(r'\d{2}/\d{2}/\d{4}', '', nome_candidato)
                nome_candidato = nome_candidato.strip()
                
                if len(nome_candidato) > 3 and not nome_candidato.isdigit():
                    info['nome'] = nome_candidato
                    break
    
    # ============================================================
    # EXTRAÇÃO DE VALORES FINANCEIROS
    # ============================================================
    
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        
        # Busca linha com "Valor FGTS | Rendimentos | Descontos | Líquido"
        if 'VALOR FGTS' in linha_norm and 'RENDIMENTOS' in linha_norm and 'DESCONTOS' in linha_norm and 'LIQUIDO' in linha_norm:
            # Próxima linha tem os valores
            if i + 1 < len(linhas):
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linhas[i + 1])
                if len(valores) >= 3:
                    # valores[0] = Valor FGTS (ignorar)
                    # valores[1] = Rendimentos
                    # valores[2] = Descontos
                    # valores[3] = Líquido (se existir)
                    info['vencimentos_total'] = float(valores[1].replace('.', '').replace(',', '.'))
                    info['descontos_total'] = float(valores[2].replace('.', '').replace(',', '.'))
                    if len(valores) >= 4:
                        info['liquido'] = float(valores[3].replace('.', '').replace(',', '.'))
        
        # Estratégia alternativa: buscar separadamente
        if not info['vencimentos_total']:
            if 'RENDIMENTOS' in linha_norm and 'DESCONTOS' not in linha_norm and 'LIQUIDO' not in linha_norm and 'VALOR FGTS' not in linha_norm:
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
                if valores:
                    info['vencimentos_total'] = float(valores[-1].replace('.', '').replace(',', '.'))
        
        if not info['descontos_total']:
            if 'DESCONTOS' in linha_norm and 'RENDIMENTOS' not in linha_norm and 'LIQUIDO' not in linha_norm and 'VALOR FGTS' not in linha_norm:
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
                if valores:
                    info['descontos_total'] = float(valores[-1].replace('.', '').replace(',', '.'))
        
        if not info['liquido']:
            if 'LIQUIDO' in linha_norm and 'VALOR LIMITE' not in linha_norm and 'RENDIMENTOS' not in linha_norm and 'DESCONTOS' not in linha_norm:
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
                if valores:
                    info['liquido'] = float(valores[-1].replace('.', '').replace(',', '.'))
    
    # Calcular líquido se não foi encontrado
    if info['liquido'] == 0.0 and info['vencimentos_total'] > 0:
        info['liquido'] = info['vencimentos_total'] - info['descontos_total']
    
    return info


def extrair_salario_bruto_governo_goias(texto: str) -> float:
    """
    Extrai o valor do salário base do Governo de Goiás
    Busca por "VENCIMENTO" (código 100061)
    """
    linhas = texto.split('\n')
    
    # Prioridade 1: Buscar código "100061 VENCIMENTO"
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if re.match(r'^\s*100061\s+VENCIMENTO', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    # Prioridade 2: Buscar "VENCIMENTO" em qualquer posição
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'VENCIMENTO' in linha_norm and 'DESCONTO' not in linha_norm and 'PROVENTOS' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    return 0.0


def extrair_vencimentos_fixos_governo_goias(texto: str) -> Dict:
    """
    Extrai vencimentos do Governo de Goiás da coluna de Proventos
    Estrutura: Código | Descrição | QTDE | VALOR
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'adicional_tempo_servico': 0.0,
        'gratificacao': 0.0,
        'hora_ativ_extra_classe': 0.0,
        'aula_suplementar': 0.0,
        'vale_alimentacao': 0.0,
        'sexta_parte': 0.0,
        'horas_extras': 0.0,
        'insalubridade': 0.0,
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # VENCIMENTO (código 100061)
        if re.match(r'^\s*100061\s+VENCIMENTO', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['vencimento_base'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # GRATIFICAÇÃO
        if 'GRAT' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['gratificacao'] += valor
                vencimentos_fixos['total'] += valor
            continue

    return vencimentos_fixos


# ============================================================================
# FUNÇÕES ESPECÍFICAS POR PREFEITURA - ALEGO
# ============================================================================

def extrair_informacoes_alego(texto: str) -> Dict:
    """
    Extrai informações específicas de ALEGO
    Estrutura: Matrícula / Nome / Proventos / Descontos / Líquido
    """
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
    }
    
    linhas = texto.split('\n')
    
    # ============================================================
    # EXTRAÇÃO DE MATRÍCULA
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        if 'MATRICULA' in linha_norm:
            # Formato: 503895838
            match = re.search(r'(\d{9})', linha)
            if match:
                info['matricula'] = match.group(1)
            elif i + 1 < len(linhas):
                match = re.search(r'(\d{9})', linhas[i + 1])
                if match:
                    info['matricula'] = match.group(1)
    
    # ============================================================
    # EXTRAÇÃO DE NOME
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        # Procura por linha com nome completo (antes de MATRICULA)
        if 'MATRICULA' in linha_norm and i > 0:
            # Nome está algumas linhas acima
            for j in range(max(0, i-5), i):
                nome_candidato = linhas[j].strip()
                # Remove datas, números de CPF e outros padrões
                nome_candidato = re.sub(r'\d{2}/\d{2}/\d{4}', '', nome_candidato)
                nome_candidato = re.sub(r'\d{3}\.\d{3}\.\d{3}-\d{2}', '', nome_candidato)
                nome_candidato = re.sub(r'CNPJ.*$', '', nome_candidato, flags=re.IGNORECASE)
                nome_candidato = re.sub(r'DATA DE EMISSAO.*$', '', nome_candidato, flags=re.IGNORECASE)
                nome_candidato = nome_candidato.strip()
                
                # Verifica se é um nome válido (mais de 2 palavras, sem números)
                if (len(nome_candidato.split()) >= 2 and 
                    not re.search(r'\d', nome_candidato) and
                    len(nome_candidato) > 10):
                    info['nome'] = nome_candidato
                    break
            if info['nome']:
                break
    
    # ============================================================
    # EXTRAÇÃO DE VALORES FINANCEIROS
    # ============================================================
    
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        
        # Busca "Proventos" (total)
        if linha_norm.strip().startswith('PROVENTOS') and 'DESCONTOS' in linha_norm and 'LIQUIDO' in linha_norm:
            # Próxima linha tem os valores
            if i + 1 < len(linhas):
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linhas[i + 1])
                if len(valores) >= 3:
                    info['vencimentos_total'] = float(valores[0].replace('.', '').replace(',', '.'))
                    info['descontos_total'] = float(valores[1].replace('.', '').replace(',', '.'))
                    info['liquido'] = float(valores[2].replace('.', '').replace(',', '.'))
    
    # Calcular líquido se não foi encontrado
    if info['liquido'] == 0.0 and info['vencimentos_total'] > 0:
        info['liquido'] = info['vencimentos_total'] - info['descontos_total']
    
    return info


def extrair_salario_bruto_alego(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque de ALEGO
    Busca por "VENCIMENTOS" (código 110)
    """
    linhas = texto.split('\n')
    
    # Prioridade 1: Buscar código "110 VENCIMENTOS"
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if re.match(r'^\s*110\s+VENCIMENTOS', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    # Prioridade 2: Buscar "VENCIMENTOS" em qualquer posição
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'VENCIMENTOS' in linha_norm and 'DESCONTO' not in linha_norm and 'PROVENTOS' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    return 0.0


def extrair_vencimentos_fixos_alego(texto: str) -> Dict:
    """
    Extrai vencimentos de ALEGO da coluna de Proventos
    Estrutura: Cód. | Descrição | Parcela Inicial | Parcela Final | Quantidade | Proventos | Descontos
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'adicional_tempo_servico': 0.0,
        'gratificacao': 0.0,
        'hora_ativ_extra_classe': 0.0,
        'aula_suplementar': 0.0,
        'vale_alimentacao': 0.0,
        'sexta_parte': 0.0,
        'horas_extras': 0.0,
        'insalubridade': 0.0,
        'auxilio_alimentacao': 0.0,
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # VENCIMENTOS (código 110)
        if re.match(r'^\s*110\s+VENCIMENTOS', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['vencimento_base'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # AUXÍLIO-ALIMENTAÇÃO (código 332)
        if 'AUXILIO-ALIMENTACAO' in linha_norm or 'AUXILIO ALIMENTACAO' in linha_norm or re.match(r'^\s*332\s+', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['auxilio_alimentacao'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # GRATIFICAÇÃO
        if 'GRAT' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['gratificacao'] += valor
                vencimentos_fixos['total'] += valor
            continue

    return vencimentos_fixos

# ============================================================================
# FUNÇÕES ESPECÍFICAS POR PREFEITURA - CUIABÁ
# ============================================================================

def extrair_informacoes_cuiaba(texto: str) -> Dict:
    """
    Extrai informações específicas de Cuiabá - MT
    Estrutura: Nome / Matrícula / Vencimentos / Descontos / Líquido
    """
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
    }
    
    linhas = texto.split('\n')
    
    # ============================================================
    # EXTRAÇÃO DE NOME
    # ============================================================

    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        if 'NOME' in linha_norm:
            nome_candidato = linhas[i + 1].strip()
            match = re.sub(r'\s+\d{7}.*$', '', nome_candidato)
            if match:
                info['nome'] = match
                break
            elif i + 1 < len(linhas):
                match = re.search(r'(\d{7})', linhas[i + 1])
                if match:
                    info['nome'] = match
                    break

    
    # ============================================================
    # EXTRAÇÃO DE MATRÍCULA
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        if 'MATRICULA' in linha_norm:
            # Formato: 4011069 (7 dígitos)
            match = re.search(r'(\d{7})', linha)
            if match:
                info['matricula'] = match.group(1)
                break
            elif i + 1 < len(linhas):
                match = re.search(r'(\d{7})', linhas[i + 1])
                if match:
                    info['matricula'] = match.group(1)
                    break
    
    # ============================================================
    # EXTRAÇÃO DE VALORES FINANCEIROS
    # ============================================================
    
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        
        # Busca "Total de Vencimentos"
        if 'TOTAL DE VENCIMENTOS' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                info['vencimentos_total'] = float(valores[-1].replace('.', '').replace(',', '.'))
        
        # Busca "Total de Descontos"
        if 'TOTAL DE DESCONTOS' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                info['descontos_total'] = float(valores[-1].replace('.', '').replace(',', '.'))
        
        # Busca "Valor Líquido" ou "Valor Liquido"
        if 'VALOR LIQUIDO' in linha_norm or 'VALOR LÍQUIDO' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                info['liquido'] = float(valores[-1].replace('.', '').replace(',', '.'))
    
    # Estratégia alternativa: buscar na linha de rodapé
    if info['liquido'] == 0.0:
        for linha in linhas[-10:]:  # Últimas 10 linhas
            if re.search(r'\d{1,3}(?:\.\d{3})*,\d{2}\s+\d{1,3}(?:\.\d{3})*,\d{2}\s+\d{1,3}(?:\.\d{3})*,\d{2}', linha):
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
                if len(valores) >= 3:
                    info['vencimentos_total'] = float(valores[0].replace('.', '').replace(',', '.'))
                    info['descontos_total'] = float(valores[1].replace('.', '').replace(',', '.'))
                    info['liquido'] = float(valores[2].replace('.', '').replace(',', '.'))
                    break
    
    # Calcular líquido se não foi encontrado
    if info['liquido'] == 0.0 and info['vencimentos_total'] > 0:
        info['liquido'] = info['vencimentos_total'] - info['descontos_total']
    
    return info


def extrair_salario_bruto_cuiaba(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque de CUIABÁ
    Busca por "VENCIMENTO - PROFISSIONAL" (código 4727)
    """
    linhas = texto.split('\n')
    
    # Prioridade 1: Buscar código "4727 VENCIMENTO - PROFISSIONAL"
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if re.match(r'^\s*4727\s+VENCIMENTO', linha_norm) or 'VENCIMENTO - PROFISSIONAL' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    # Prioridade 2: Buscar qualquer "VENCIMENTO" em coluna de vencimentos
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'VENCIMENTO' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    return 0.0


def extrair_vencimentos_fixos_cuiaba(texto: str) -> Dict:
    """
    Extrai vencimentos de CUIABÁ da coluna de Vencimentos
    Estrutura: Código | Descrição | C/D | Referência | Parcela | Quantidade | Base de Cálculo | Vencimentos | Descontos
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'adicional_tempo_servico': 0.0,
        'gratificacao': 0.0,
        'hora_ativ_extra_classe': 0.0,
        'aula_suplementar': 0.0,
        'vale_alimentacao': 0.0,
        'sexta_parte': 0.0,
        'horas_extras': 0.0,
        'insalubridade': 0.0,
        'grat_desempenho': 0.0,  # Específico de Cuiabá
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # VENCIMENTO/SUBSÍDIO (códigos 4727, 6463, etc.)
        if (re.match(r'^\s*(4727|6463)\s+', linha_norm) or 
            'VENCIMENTO - PROFISSIONAL' in linha_norm or 
            'SUBSIDIO - PROFESSOR' in linha_norm or
            'SUBSIDIO - PROF' in linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['vencimento_base'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # ADIC. INSALUBRIDADE (código 1220)
        if 'ADIC. INSALUBRIDADE' in linha_norm or 'ADICIONAL INSALUBRIDADE' in linha_norm or re.match(r'^\s*1220\s+', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['insalubridade'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # GRAT. DESEMPENHO - PCCS (código 1231)
        if 'GRAT. DESEMPENHO' in linha_norm or 'GRATIFICACAO DESEMPENHO' in linha_norm or re.match(r'^\s*1231\s+', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['grat_desempenho'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # GRATIFICAÇÃO (qualquer outra)
        if 'GRAT' in linha_norm and 'DESCONTO' not in linha_norm and 'DESEMPENHO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['gratificacao'] += valor
                vencimentos_fixos['total'] += valor
            continue

        # ADICIONAL POR TEMPO DE SERVIÇO
        if any(termo in linha_norm for termo in ['ADICIONAL TEMPO', 'TEMPO DE SERVICO', 'TEMPO SERVICO', 'QUINQUENIO', 'ANUENIO']):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['adicional_tempo_servico'] += valor
                vencimentos_fixos['total'] += valor
            continue

        # SEXTA PARTE
        if 'SEXTA PARTE' in linha_norm or '6A PARTE' in linha_norm or '6 PARTE' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['sexta_parte'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # NÃO INCLUIR proventos indenizatórios/variáveis:
        # - DIARIAS, AJUDA-DE-CUSTO, SALARIO-FAMILIA, AUXILIO-NATALIDADE
        # - AUXILIO-FUNERAL, ADICIONAL DE FERIAS
        # Estes já são naturalmente excluídos por não terem match nos padrões acima

    return vencimentos_fixos


# ============================================================================
# FUNÇÕES ESPECÍFICAS POR PREFEITURA - REDENÇÃO
# ============================================================================

def extrair_informacoes_redencao(texto: str) -> Dict:
    """
    Extrai informações específicas de Redenção - PA
    Estrutura: Matrícula / Nome / Vencimentos / Descontos / Líquido
    """
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
    }
    
    linhas = texto.split('\n')
    
    # ============================================================
    # EXTRAÇÃO DE MATRÍCULA E NOME (mesma linha)
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        # Procura por matrícula de 6 dígitos seguida de nome
        # Formato: "110338 KLEBIANNY KELLY ROCHA LEAO"
        if re.match(r'^\d{6}\s+[A-Z]', linha):
            match = re.search(r'^(\d{6})\s+([A-Z][A-Z\s]+?)(?:\s+-\s+|\s+CPF:|$)', linha)
            if match:
                info['matricula'] = match.group(1)
                nome_candidato = match.group(2).strip()
                # Remove possíveis códigos do final
                nome_candidato = re.sub(r'\s+-\s+.*$', '', nome_candidato)
                if len(nome_candidato) > 3:
                    info['nome'] = nome_candidato
                    break
    
    # ============================================================
    # EXTRAÇÃO DE VALORES FINANCEIROS
    # ============================================================
    
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        
        # Busca linha com os valores totais (penúltima ou última linha da tabela)
        # Formato: "3.433,57 238,81" ou "Líquido >>> 3.194,76"
        if 'LIQUIDO' in linha_norm and '>>>' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                info['liquido'] = float(valores[-1].replace('.', '').replace(',', '.'))
        
        # Busca linha anterior ao "Líquido >>>" que tem vencimentos e descontos
        if i > 0:
            linha_anterior = linhas[i-1]
            if 'LIQUIDO' in linha_norm and '>>>' in linha_norm:
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha_anterior)
                if len(valores) >= 2:
                    info['vencimentos_total'] = float(valores[0].replace('.', '').replace(',', '.'))
                    info['descontos_total'] = float(valores[1].replace('.', '').replace(',', '.'))
    
    # Estratégia alternativa: buscar pelos rótulos específicos
    if info['liquido'] == 0.0:
        for i, linha in enumerate(linhas):
            # Busca formato "SERVIDOR,IMPRIMA SUA CEDULA" (linha de separação antes dos totais)
            if 'SERVIDOR' in linha and 'IMPRIMA' in linha:
                # Valores estão 1-2 linhas acima
                for j in range(max(0, i-3), i):
                    valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linhas[j])
                    if len(valores) >= 2:
                        info['vencimentos_total'] = float(valores[0].replace('.', '').replace(',', '.'))
                        info['descontos_total'] = float(valores[1].replace('.', '').replace(',', '.'))
                        break
    
    # Calcular líquido se não foi encontrado
    if info['liquido'] == 0.0 and info['vencimentos_total'] > 0:
        info['liquido'] = info['vencimentos_total'] - info['descontos_total']
    
    return info


def extrair_salario_bruto_redencao(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque de REDENÇÃO
    Busca por "VENCIMENTO" (código 001)
    """
    linhas = texto.split('\n')
    
    # Prioridade 1: Buscar código "001 VENCIMENTO"
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if re.match(r'^\s*001\s+VENCIMENTO', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    # Prioridade 2: Buscar "Salário Base:" no rodapé
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        if 'SALARIO BASE' in linha_norm and ':' in linha_norm:
            match = re.search(r'SALARIO BASE\s*:\s*(\d{1,3}(?:\.\d{3})*,\d{2})', linha_norm)
            if match:
                valor_str = match.group(1).replace('.', '').replace(',', '.')
                return float(valor_str)
    
    return 0.0


def extrair_vencimentos_fixos_redencao(texto: str) -> Dict:
    """
    Extrai vencimentos de REDENÇÃO da coluna de Vencimentos
    Estrutura: Cod. | Descrição | Referência | Vencimentos | Descontos
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'adicional_tempo_servico': 0.0,
        'gratificacao': 0.0,
        'hora_ativ_extra_classe': 0.0,
        'aula_suplementar': 0.0,
        'vale_alimentacao': 0.0,
        'sexta_parte': 0.0,
        'horas_extras': 0.0,
        'insalubridade': 0.0,
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # VENCIMENTO (código 001)
        if re.match(r'^\s*001\s+VENCIMENTO', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['vencimento_base'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # HORAS EXTRAS (código 012) - NÃO INCLUIR: não é provento fixo/permanente
        # Mantido para compatibilidade mas não soma no total
        if 'HORAS EXTRAS' in linha_norm or re.match(r'^\s*012\s+', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['horas_extras'] = valor
                # NÃO adiciona ao total: vencimentos_fixos['total'] += valor
            continue

        # GRATIFICAÇÃO
        if 'GRAT' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['gratificacao'] += valor
                vencimentos_fixos['total'] += valor
            continue

        # ADICIONAL POR TEMPO DE SERVIÇO
        if any(termo in linha_norm for termo in ['ADICIONAL TEMPO', 'TEMPO DE SERVICO', 'TEMPO SERVICO', 'QUINQUENIO', 'ANUENIO']):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['adicional_tempo_servico'] += valor
                vencimentos_fixos['total'] += valor
            continue

        # SEXTA PARTE
        if 'SEXTA PARTE' in linha_norm or '6A PARTE' in linha_norm or '6 PARTE' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['sexta_parte'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # INSALUBRIDADE (se for fixa)
        if 'INSALUBR' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['insalubridade'] = valor
                vencimentos_fixos['total'] += valor
            continue
        

    return vencimentos_fixos

# ============================================================================
# FUNÇÕES ESPECÍFICAS POR PREFEITURA - MONTE ALEGRE DE SERGIPE
# ============================================================================

def extrair_informacoes_monte_alegre_se(texto: str) -> Dict:
    """
    Extrai informações específicas de Monte Alegre de Sergipe - SE
    Estrutura: Funcionário: [matrícula] [NOME] / Proventos / Descontos / Total Líquido
    IMPORTANTE: Formato numérico americano (1,518.00)
    """
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
    }
    
    linhas = texto.split('\n')
    
    # ============================================================
    # EXTRAÇÃO DE MATRÍCULA E NOME (mesma linha)
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        # Procura por "Funcionário:" seguido de número e nome
        # Formato: "Funcionário: 3086 GEOVANE DOS SANTOS ARAGAO"
        if 'FUNCIONARIO' in linha_norm:
            # Tenta na mesma linha
            match = re.search(r'FUNCIONARIO\s*:\s*(\d{4,6})\s+([A-Z][A-Z\s]+?)(?:\s+REF\.|\s+CODIGO|$)', linha_norm)
            if match:
                info['matricula'] = match.group(1)
                info['nome'] = match.group(2).strip()
                break
            # Tenta próxima linha
            elif i + 1 < len(linhas):
                proxima_linha = linhas[i + 1].strip()
                match = re.search(r'^(\d{4,6})\s+([A-Z][A-Z\s]+)', proxima_linha)
                if match:
                    info['matricula'] = match.group(1)
                    nome_candidato = match.group(2).strip()
                    # Remove possíveis códigos ou labels do final
                    nome_candidato = re.sub(r'\s+(?:REF\.|CODIGO|DESCRICAO).*$', '', nome_candidato, flags=re.IGNORECASE)
                    if len(nome_candidato) > 3:
                        info['nome'] = nome_candidato
                        break
    
    # ============================================================
    # EXTRAÇÃO DE VALORES FINANCEIROS - FORMATO AMERICANO
    # ============================================================
    
    # Regex para formato americano
    regex_americano = r'\d{1,3}(?:,\d{3})*\.\d{2}|\d+\.\d{2}'
    
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        
        # Busca "Totais:" no rodapé (linha com resumo de proventos e descontos)
        if linha_norm.strip().startswith('TOTAIS:') or 'TOTAIS:' in linha_norm:
            # Os valores estão na mesma linha ou próxima (formato: Totais: 1,518.00 113.85)
            valores = re.findall(regex_americano, linha)
            if len(valores) >= 2:
                info['vencimentos_total'] = float(valores[0].replace(',', ''))
                info['descontos_total'] = float(valores[1].replace(',', ''))
            # Se não achou na mesma linha, tenta próxima
            elif i + 1 < len(linhas):
                valores = re.findall(regex_americano, linhas[i + 1])
                if len(valores) >= 2:
                    info['vencimentos_total'] = float(valores[0].replace(',', ''))
                    info['descontos_total'] = float(valores[1].replace(',', ''))
        
        # Busca "Total Liquído a Receber:" (com ou sem acento)
        if 'TOTAL LIQUIDO' in linha_norm or 'TOTAL LÍQUIDO' in linha_norm:
            valores = re.findall(regex_americano, linha)
            if valores:
                info['liquido'] = float(valores[-1].replace(',', ''))
            # Tenta próxima linha se não achou
            elif i + 1 < len(linhas):
                valores = re.findall(regex_americano, linhas[i + 1])
                if valores:
                    info['liquido'] = float(valores[-1].replace(',', ''))
    
    # Calcular líquido se não foi encontrado
    if info['liquido'] == 0.0 and info['vencimentos_total'] > 0:
        info['liquido'] = info['vencimentos_total'] - info['descontos_total']
    
    return info


def extrair_salario_bruto_monte_alegre_se(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque de MONTE ALEGRE DE SERGIPE
    Busca por "VENCIMENTOS" (código 1) ou "Salário Base:" no rodapé
    IMPORTANTE: Formato numérico americano (1,518.00)
    """
    linhas = texto.split('\n')
    
    # Prioridade 1: Buscar "Salário Base:" no rodapé (formato: Salário Base: 1,518.00)
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'SALARIO BASE' in linha_norm and ':' in linha_norm:
            # Extrai o valor após os dois pontos (formato americano)
            match = re.search(r'SALARIO BASE\s*:\s*(\d{1,3}(?:,\d{3})*\.\d{2})', linha_norm)
            if match:
                valor_str = match.group(1).replace(',', '')  # Remove vírgula de milhar
                return float(valor_str)
    
    # Prioridade 2: Buscar código "1 VENCIMENTOS" na tabela
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if re.match(r'^\s*1\s+VENCIMENTOS', linha_norm):
            valor = extrair_valores_vencimento_monte_alegre_se(linha)
            if valor > 0:
                return valor
    
    # Prioridade 3: Buscar "VENCIMENTOS" em qualquer posição
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if linha_norm.strip().startswith('VENCIMENTOS') and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento_monte_alegre_se(linha)
            if valor > 0:
                return valor
    
    return 0.0


def extrair_vencimentos_fixos_monte_alegre_se(texto: str) -> Dict:
    """
    Extrai vencimentos de MONTE ALEGRE DE SERGIPE da coluna de Proventos
    
    Para Monte Alegre SE, considerar TODOS os proventos de natureza permanente/fixa
    conforme lista oficial de vencimentos da prefeitura
    
    Estrutura: Código | Descrição | Referência | Proventos | Descontos
    IMPORTANTE: Formato numérico americano (1,518.00)
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'adicional_tempo_servico': 0.0,
        'gratificacao': 0.0,
        'hora_ativ_extra_classe': 0.0,
        'aula_suplementar': 0.0,
        'vale_alimentacao': 0.0,
        'sexta_parte': 0.0,
        'horas_extras': 0.0,
        'insalubridade': 0.0,
        'trienio': 0.0,
        'titulacao': 0.0,
        'subsidios': 0.0,
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # VENCIMENTOS (código 1) - Vencimento base
        if re.match(r'^\s*1\s+VENCIMENTOS', linha_norm):
            valor = extrair_valores_vencimento_monte_alegre_se(linha)
            if valor > 0:
                vencimentos_fixos['vencimento_base'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # INSALUBRIDADE (10, 20, etc)
        if 'INSALUBR' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento_monte_alegre_se(linha)
            if valor > 0:
                vencimentos_fixos['insalubridade'] += valor
                vencimentos_fixos['total'] += valor
            continue

        # LEI Nº 21/2001/ART.60/VERBA DE REPRESENTACAO
        if 'VERBA DE REPRESENTACAO' in linha_norm or ('LEI' in linha_norm and '21/2001' in linha_norm):
            valor = extrair_valores_vencimento_monte_alegre_se(linha)
            if valor > 0:
                vencimentos_fixos['outros_fixos'].append(('VERBA REPRESENTACAO', valor))
                vencimentos_fixos['total'] += valor
            continue

        # PPB (Prêmio por Produtividade)
        if re.match(r'^\s*PPB', linha_norm) and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento_monte_alegre_se(linha)
            if valor > 0:
                vencimentos_fixos['outros_fixos'].append(('PPB', valor))
                vencimentos_fixos['total'] += valor
            continue

        # REGENCIA DE CLASSE
        if 'REGENCIA DE CLASSE' in linha_norm or 'REGENCIA' in linha_norm:
            valor = extrair_valores_vencimento_monte_alegre_se(linha)
            if valor > 0:
                vencimentos_fixos['outros_fixos'].append(('REGENCIA CLASSE', valor))
                vencimentos_fixos['total'] += valor
            continue

        # SUBSIDIOS
        if 'SUBSIDIO' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento_monte_alegre_se(linha)
            if valor > 0:
                vencimentos_fixos['subsidios'] += valor
                vencimentos_fixos['total'] += valor
            continue

        # TITULACAO
        if 'TITULACAO' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento_monte_alegre_se(linha)
            if valor > 0:
                vencimentos_fixos['titulacao'] += valor
                vencimentos_fixos['total'] += valor
            continue

        # TRIENIO (inclui CESSAO, AVERBADO)
        if 'TRIENIO' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento_monte_alegre_se(linha)
            if valor > 0:
                vencimentos_fixos['trienio'] += valor
                vencimentos_fixos['total'] += valor
            continue

        # 1/3 DE FERIAS
        if ('1/3' in linha_norm or 'TERCO' in linha_norm) and 'FERIAS' in linha_norm:
            valor = extrair_valores_vencimento_monte_alegre_se(linha)
            if valor > 0:
                vencimentos_fixos['outros_fixos'].append(('1/3 FERIAS', valor))
                vencimentos_fixos['total'] += valor
            continue

        # ADICIONAL DE 1/3
        if 'ADICIONAL DE 1/3' in linha_norm or 'ADICIONAL 1/3' in linha_norm:
            valor = extrair_valores_vencimento_monte_alegre_se(linha)
            if valor > 0:
                vencimentos_fixos['adicional_tempo_servico'] += valor
                vencimentos_fixos['total'] += valor
            continue

        # AMPLIACAO DE CARGA HORARIA
        if 'AMPLIACAO' in linha_norm and 'CARGA' in linha_norm:
            valor = extrair_valores_vencimento_monte_alegre_se(linha)
            if valor > 0:
                vencimentos_fixos['outros_fixos'].append(('AMPLIACAO CARGA', valor))
                vencimentos_fixos['total'] += valor
            continue

        # CESSAO
        if 'CESSAO' in linha_norm and 'DESCONTO' not in linha_norm and 'GRAT' not in linha_norm:
            valor = extrair_valores_vencimento_monte_alegre_se(linha)
            if valor > 0:
                vencimentos_fixos['outros_fixos'].append(('CESSAO', valor))
                vencimentos_fixos['total'] += valor
            continue

        # GRATIFICAÇÕES (todas as variações)
        if 'GRAT' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento_monte_alegre_se(linha)
            if valor > 0:
                vencimentos_fixos['gratificacao'] += valor
                vencimentos_fixos['total'] += valor
            continue

        # PLANTOES
        if 'PLANTAO' in linha_norm or 'PLANTOES' in linha_norm:
            valor = extrair_valores_vencimento_monte_alegre_se(linha)
            if valor > 0:
                vencimentos_fixos['outros_fixos'].append(('PLANTOES', valor))
                vencimentos_fixos['total'] += valor
            continue

    return vencimentos_fixos

def extrair_valores_vencimento_monte_alegre_se(linha: str) -> float:
    """
    Extrai valores de PROVENTOS de MONTE ALEGRE DE SERGIPE
    Formato americano: 1,518.00 (vírgula = milhar, ponto = decimal)
    
    Estrutura: Código | Descrição | Referência | Proventos
    Exemplo: "1 VENCIMENTOS 30.00 1,518.00"
    
    SEMPRE pega o ÚLTIMO valor (coluna Proventos)
    """
    # Regex para formato americano: 1,518.00 ou 518.00 ou 18.00
    valores = re.findall(r'\d{1,3}(?:,\d{3})*\.\d{2}|\d+\.\d{2}', linha)
    
    if valores:
        # ÚLTIMO valor = coluna de Proventos
        valor_str = valores[-1].replace(',', '')  # Remove vírgula de milhar
        return float(valor_str)
    return 0.0

def extrair_valores_desconto_monte_alegre_se(linha: str) -> float:
    """
    Extrai valores de DESCONTOS de MONTE ALEGRE DE SERGIPE
    Formato americano: 113.85 (ponto = decimal)
    
    Estrutura: Código | Descrição | Referência | Descontos
    Exemplo: "5 I.N.S.S. 7.50 113.85"
    
    SEMPRE pega o ÚLTIMO valor (coluna Descontos)
    """
    # Regex para formato americano
    valores = re.findall(r'\d{1,3}(?:,\d{3})*\.\d{2}|\d+\.\d{2}', linha)
    
    if valores:
        # ÚLTIMO valor = coluna de Descontos
        valor_str = valores[-1].replace(',', '')  # Remove vírgula de milhar
        return float(valor_str)
    return 0.0

def extrair_descontos_obrigatorios_monte_alegre_se(texto: str) -> Dict:
    """
    Extrai apenas os descontos OBRIGATÓRIOS de MONTE ALEGRE DE SERGIPE
    (INSS, IRRF, Previdência) da coluna de DESCONTOS
    
    IMPORTANTE: Usa função específica para formato americano
    """
    linhas = texto.split('\n')
    
    descontos_obrigatorios = {
        'inss': 0.0,
        'irrf': 0.0,
        'previdencia': 0.0,
        'total': 0.0
    }
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        # INSS
        if 'I.N.S.S' in linha_norm or 'INSS' in linha_norm:
            valor = extrair_valores_desconto_monte_alegre_se(linha)  # FUNÇÃO ESPECÍFICA
            if valor > 0:
                descontos_obrigatorios['inss'] = valor
                descontos_obrigatorios['total'] += valor
        
        # IRRF
        elif 'IRRF' in linha_norm or 'I.R.R.F' in linha_norm or 'IMPOSTO DE RENDA' in linha_norm or 'IR ' in linha_norm:
            valor = extrair_valores_desconto_monte_alegre_se(linha)  # FUNÇÃO ESPECÍFICA
            if valor > 0:
                descontos_obrigatorios['irrf'] = valor
                descontos_obrigatorios['total'] += valor
        
        # Previdência
        elif any(palavra in linha_norm for palavra in ['PREVIDENCIA', 'RPPS', 'IPSM', 'FUNPREV']):
            valor = extrair_valores_desconto_monte_alegre_se(linha)  # FUNÇÃO ESPECÍFICA
            if valor > 0:
                descontos_obrigatorios['previdencia'] = valor
                descontos_obrigatorios['total'] += valor
    
    return descontos_obrigatorios

# ============================================================================
# FUNÇÕES ESPECÍFICAS POR PREFEITURA - VINHEDO
# ============================================================================

def extrair_informacoes_vinhedo(texto: str) -> Dict:
    """
    Extrai informações específicas de Vinhedo - SP
    Estrutura: Funcionário / CPF / Banco / Vencimentos / Descontos / Líquido
    """
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
    }
    
    linhas = texto.split('\n')
    
    # ============================================================
    # EXTRAÇÃO DE MATRÍCULA E NOME
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        # Procura por "Funcionário" seguido de matrícula e nome
        if 'FUNCIONARIO' in linha_norm:
            # Próxima linha tem formato: "3685 CRISTIANE REGINA MARCONDES"
            if i + 1 < len(linhas):
                proxima_linha = linhas[i + 1].strip()
                match = re.search(r'^(\d{4,6})\s+([A-Z][A-Z\s]+)', proxima_linha)
                if match:
                    info['matricula'] = match.group(1)
                    nome_candidato = match.group(2).strip()
                    if len(nome_candidato) > 3:
                        info['nome'] = nome_candidato
                        break
    
    money_re = r'(\d{1,3}(?:[.\s]\d{3})*,\d{2}|\d+,\d{2})'

    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha).lower().replace('\xa0', ' ')

        # Busca "Vencimentos" no rodapé
        if 'vencimentos' in linha_norm and 'descontos' not in linha_norm and 'liq' not in linha_norm:
            valores = re.findall(money_re, linha)
            if not valores and i + 1 < len(linhas):
                valores = re.findall(money_re, linhas[i + 1])
            if valores:
                info['vencimentos_total'] = float(valores[-1].replace('.', '').replace(' ', '').replace(',', '.'))

        # Busca "Descontos" no rodapé
        if 'descontos' in linha_norm and 'vencimentos' not in linha_norm and 'liq' not in linha_norm:
            valores = re.findall(money_re, linha)
            if not valores and i + 1 < len(linhas):
                valores = re.findall(money_re, linhas[i + 1])
            if valores:
                info['descontos_total'] = float(valores[-1].replace('.', '').replace(' ', '').replace(',', '.'))

        # Busca "Líquido" (aceita variações com/sem acento ou quebras)
        if 'liq' in linha_norm:  # pega "liquido", "líquido", "liq uid o", etc.
            valores = re.findall(money_re, linha)
            if not valores and i + 1 < len(linhas):
                valores = re.findall(money_re, linhas[i + 1])
            if valores:
                info['liquido'] = float(valores[-1].replace('.', '').replace(' ', '').replace(',', '.'))

    # Calcular líquido se não foi encontrado
    if info.get('liquido', 0.0) == 0.0 and info.get('vencimentos_total', 0.0) > 0:
        info['liquido'] = round(info['vencimentos_total'] - info.get('descontos_total', 0.0), 2)
    
    return info


def extrair_salario_bruto_vinhedo(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque de VINHEDO
    Busca por "SALARIO BASE" (código 30)
    """
    linhas = texto.split('\n')
    
    # Prioridade 1: Buscar "SALARIO BASE" com código 30
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if re.match(r'^\s*30\s+SALARIO BASE', linha_norm) or 'SALARIO BASE' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    return 0.0


def extrair_vencimentos_fixos_vinhedo(texto: str) -> Dict:
    """
    Extrai vencimentos de VINHEDO da coluna de VENCIMENTOS
    
    Para Vinhedo, a base de cálculo é a TOTALIDADE dos vencimentos, proventos e pensões
    conforme especificação: "70% da totalidade dos vencimentos, proventos e pensões"
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'adicional_tempo_servico': 0.0,
        'gratificacao': 0.0,
        'hora_ativ_extra_classe': 0.0,
        'aula_suplementar': 0.0,
        'vale_alimentacao': 0.0,
        'sexta_parte': 0.0,
        'horas_extras': 0.0,
        'insalubridade': 0.0,
        'aux_transporte': 0.0,
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # SALARIO BASE (código 30) - já incluído no salario_base, não duplicar
        if re.match(r'^\s*30\s+SALARIO BASE', linha_norm):
            continue

        # AUX TRANSPORTE (código 2495)
        if 'AUX TRANSPORTE' in linha_norm or re.match(r'^\s*2495\s+', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['aux_transporte'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # GRATIFICAÇÃO
        if 'GRAT' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['gratificacao'] += valor
                vencimentos_fixos['total'] += valor
            continue
        
        # Adicional de Tempo de Serviço
        if 'ADICIONAL TEMPO' in linha_norm or 'ADIC' in linha_norm and 'TEMPO' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['adicional_tempo_servico'] = valor
                vencimentos_fixos['total'] += valor
            continue
        
        # Sexta Parte
        if 'SEXTA PARTE' in linha_norm or '1/6' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['sexta_parte'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # Horas Extras
        if 'HORA EXTRA' in linha_norm or 'H.E' in linha_norm or 'H. EXTRA' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['horas_extras'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # Insalubridade
        if 'INSALUB' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['insalubridade'] = valor
                vencimentos_fixos['total'] += valor
            continue

    return vencimentos_fixos


# ============================================================================
# FUNÇÕES ESPECÍFICAS POR PREFEITURA - SÃO JOSÉ DO RIO PRETO
# ============================================================================

def extrair_informacoes_sao_jose_rio_preto(texto: str) -> Dict:
    """
    Extrai informações específicas de São José do Rio Preto - SP
    Estrutura: Matrícula / Nome / Vencimentos / Descontos / Líquido
    """
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
    }
    
    linhas = texto.split('\n')
    
    # ============================================================
    # EXTRAÇÃO DE MATRÍCULA
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        if 'MATRICULA' in linha_norm:
            # Formato: 75155
            match = re.search(r'(\d{5})', linha)
            if match:
                info['matricula'] = match.group(1)
            elif i + 1 < len(linhas):
                match = re.search(r'(\d{5})', linhas[i + 1])
                if match:
                    info['matricula'] = match.group(1)
    
    # ============================================================
    # EXTRAÇÃO DE NOME
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        if 'NOME' in linha_norm and i + 1 < len(linhas):
            proxima_linha = linhas[i + 1].strip()
            # Remove matrícula do início
            nome_candidato = re.sub(r'^\d{5}\s*', '', proxima_linha)
            # Remove data de admissão do final
            nome_candidato = re.sub(r'\s*\d{2}/\d{2}/\d{4}.*$', '', nome_candidato)
            
            if len(nome_candidato) > 3 and not nome_candidato.isdigit():
                info['nome'] = nome_candidato.strip()
                break
    
    # ============================================================
    # EXTRAÇÃO DE VALORES FINANCEIROS
    # ============================================================
    
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        
        # Busca "Total de Vencimentos"
        if 'TOTAL DE VENCIMENTOS' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                # Remove "R$" se presente
                valor_str = valores[-1].replace('.', '').replace(',', '.')
                info['vencimentos_total'] = float(valor_str)
        
        # Busca "Total de Descontos"
        if 'TOTAL DE DESCONTOS' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                valor_str = valores[-1].replace('.', '').replace(',', '.')
                info['descontos_total'] = float(valor_str)
        
        # Busca "Valor Liquido"
        if 'VALOR LIQUIDO' in linha_norm or 'VALOR LÍQUIDO' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                valor_str = valores[-1].replace('.', '').replace(',', '.')
                info['liquido'] = float(valor_str)
    
    # Calcular líquido se não foi encontrado
    if info['liquido'] == 0.0 and info['vencimentos_total'] > 0:
        info['liquido'] = info['vencimentos_total'] - info['descontos_total']
    
    return info


def extrair_salario_bruto_sao_jose_rio_preto(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque de SÃO JOSÉ DO RIO PRETO
    Busca por "VENCIMENTO" (código 1)
    """
    linhas = texto.split('\n')
    
    # Prioridade 1: Buscar código "1 VENCIMENTO"
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if re.match(r'^\s*1\s+VENCIMENTO', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    # Prioridade 2: Buscar "VENCIMENTO" em qualquer posição
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if linha_norm.strip().startswith('VENCIMENTO') or 'VENCIMENTO' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    return 0.0


def extrair_vencimentos_fixos_sao_jose_rio_preto(texto: str) -> Dict:
    """
    Extrai vencimentos de SÃO JOSÉ DO RIO PRETO da coluna de VENCIMENTO
    
    Para o cálculo de margem de São José do Rio Preto, considera-se:
    - VENCIMENTO
    - ADIC. FIXO (Adicional Fixo)
    - GRAT. FIXA (Gratificação Fixa)
    
    IMPORTANTE: Auxílio Saúde NÃO entra no cálculo de margem.
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'adicional_fixo': 0.0,
        'gratificacao_fixa': 0.0,
        'adicional_tempo_servico': 0.0,
        'gratificacao': 0.0,
        'hora_ativ_extra_classe': 0.0,
        'aula_suplementar': 0.0,
        'vale_alimentacao': 0.0,
        'sexta_parte': 0.0,
        'horas_extras': 0.0,
        'insalubridade': 0.0,
        'auxilio_saude': 0.0,  # Não entra no cálculo de margem
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # VENCIMENTO (código 1)
        if re.match(r'^\s*1\s+VENCIMENTO', linha_norm) or (re.match(r'^\s*1\s+', linha_norm) and 'VENCIMENTO' in linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['vencimento_base'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # ADIC. FIXO (Adicional Fixo)
        if 'ADIC. FIXO' in linha_norm or 'ADICIONAL FIXO' in linha_norm or 'ADIC FIXO' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['adicional_fixo'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # GRAT. FIXA (Gratificação Fixa)
        if 'GRAT. FIXA' in linha_norm or 'GRATIFICACAO FIXA' in linha_norm or 'GRAT FIXA' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['gratificacao_fixa'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # AUXILIO SAUDE - NÃO entra no cálculo de margem (apenas para registro)
        if 'AUXILIO SAUDE' in linha_norm or re.match(r'^\s*1371\s+', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['auxilio_saude'] = valor
                # NÃO adiciona ao total!
            continue

    return vencimentos_fixos

# ============================================================================
# FUNÇÕES ESPECÍFICAS POR PREFEITURA - BELTERRA
# ============================================================================

def extrair_informacoes_belterra(texto: str) -> Dict:
    """
    Extrai informações específicas de Belterra - PA
    Estrutura: Matrícula / Nome / Vencimentos / Descontos / Líquido
    """
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
    }
    
    linhas = texto.split('\n')
    
    # ============================================================
    # EXTRAÇÃO DE MATRÍCULA
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        if 'MATRICULA' in linha_norm:
            # Formato: 2053-1
            match = re.search(r'(\d{4}-\d)', linha)
            if match:
                info['matricula'] = match.group(1)
            elif i + 1 < len(linhas):
                match = re.search(r'(\d{4}-\d)', linhas[i + 1])
                if match:
                    info['matricula'] = match.group(1)
    
    # ============================================================
    # EXTRAÇÃO DE NOME
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        if 'NOME' in linha_norm and i + 1 < len(linhas):
            proxima_linha = linhas[i + 1].strip()
            # Remove matrícula do início (formato: 2053-1)
            nome_candidato = re.sub(r'^\d{4}-\d\s*', '', proxima_linha)
            # Remove informações adicionais do final
            nome_candidato = re.sub(r'\s+\d{2}/\d{2}/\d{4}.*$', '', nome_candidato)
            
            if len(nome_candidato) > 3 and not nome_candidato.isdigit():
                info['nome'] = nome_candidato.strip()
                break
    
    # ============================================================
    # EXTRAÇÃO DE VALORES FINANCEIROS
    # ============================================================
    
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        
        # Busca "Total de Vencimentos"
        if 'TOTAL DE VENCIMENTOS' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                info['vencimentos_total'] = float(valores[-1].replace('.', '').replace(',', '.'))
        
        # Busca "Total de Descontos"
        if 'TOTAL DE DESCONTOS' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                info['descontos_total'] = float(valores[-1].replace('.', '').replace(',', '.'))
        
        # Busca "Valor Liquido"
        if 'VALOR LIQUIDO' in linha_norm or 'VALOR LÍQUIDO' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                info['liquido'] = float(valores[-1].replace('.', '').replace(',', '.'))
    
    # Calcular líquido se não foi encontrado
    if info['liquido'] == 0.0 and info['vencimentos_total'] > 0:
        info['liquido'] = info['vencimentos_total'] - info['descontos_total']
    
    return info


def extrair_salario_bruto_belterra(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque de BELTERRA
    Busca por "SALARIO BASE" (código 001)
    """
    linhas = texto.split('\n')
    
    # Prioridade 1: Buscar código "001 SALARIO BASE"
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if re.match(r'^\s*001\s+SALARIO BASE', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    # Prioridade 2: Buscar "SALARIO BASE" em qualquer posição
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'SALARIO BASE' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    return 0.0


def extrair_vencimentos_fixos_belterra(texto: str) -> Dict:
    """
    Extrai vencimentos de BELTERRA da coluna de VENCIMENTOS
    
    Para o cálculo de margem de Belterra, considera-se:
    - Salário
    - Adicional por tempo de serviço
    - Enfermagem
    - Gratificação por títulos
    - Sexta parte
    - Gratificações fixas
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'adicional_tempo_servico': 0.0,
        'gratificacao': 0.0,
        'hora_ativ_extra_classe': 0.0,
        'aula_suplementar': 0.0,
        'vale_alimentacao': 0.0,
        'sexta_parte': 0.0,
        'horas_extras': 0.0,
        'insalubridade': 0.0,
        'trienio': 0.0,
        'enfermagem': 0.0,
        'gratificacao_titulos': 0.0,
        'gratificacoes_fixas': 0.0,
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # SALARIO BASE (código 001)
        if re.match(r'^\s*001\s+SALARIO', linha_norm) or 'SALARIO BASE' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['vencimento_base'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # ADICIONAL POR TEMPO DE SERVIÇO
        if 'ADICIONAL TEMPO' in linha_norm or 'ADICIONAL POR TEMPO' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['adicional_tempo_servico'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # ENFERMAGEM
        if 'ENFERMAGEM' in linha_norm or 'ADIC ENFERMAGEM' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['enfermagem'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # GRATIFICAÇÃO POR TÍTULOS
        if 'GRATIFICACAO POR TITULO' in linha_norm or 'GRATIF. TITULO' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['gratificacao_titulos'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # SEXTA PARTE
        if 'SEXTA PARTE' in linha_norm or '6A PARTE' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['sexta_parte'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # GRATIFICAÇÃO DE FUNÇÃO ou outras gratificações fixas
        if 'GRATIFICACAO DE FUNCAO' in linha_norm or 'GRATIFICACAO FIXA' in linha_norm or re.match(r'^\s*268\s+', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['gratificacao'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # TRIÊNIO (também considerado como provento permanente)
        if 'TRIENIO' in linha_norm or re.match(r'^\s*356\s+', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['trienio'] = valor
                vencimentos_fixos['total'] += valor
            continue

    return vencimentos_fixos

# ============================================================================
# FUNÇÕES ESPECÍFICAS POR PREFEITURA - CÂMARA DOS DEPUTADOS
# ============================================================================

def extrair_informacoes_camara_deputados(texto: str) -> Dict:
    """
    Extrai informações específicas da Câmara dos Deputados
    Estrutura: Ponto / Nome / CPF / Banco / Vencimentos / Descontos / Líquido
    """
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
    }
    
    linhas = texto.split('\n')
    
    # ============================================================
    # EXTRAÇÃO DE MATRÍCULA (PONTO)
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        if 'PONTO' in linha_norm:
            # Próxima linha tem o número do ponto
            if i + 1 < len(linhas):
                match = re.search(r'(\d{6})', linhas[i + 1])
                if match:
                    info['matricula'] = match.group(1)
    
    # ============================================================
    # EXTRAÇÃO DE NOME
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        if 'NOME' in linha_norm and i + 1 < len(linhas):
            proxima_linha = linhas[i + 1].strip()
            # Remove possíveis números/CPF
            nome_candidato = re.sub(r'\d+', '', proxima_linha).strip()
            if len(nome_candidato) > 3:
                info['nome'] = nome_candidato
                break
    
    # ============================================================
    # EXTRAÇÃO DE VALORES FINANCEIROS
    # ============================================================
    
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        
        # Busca linha com cabeçalho "Bruto | Desconto | Valor Líquido"
        if 'BRUTO' in linha_norm and 'DESCONTO' in linha_norm and 'VALOR LIQUIDO' in linha_norm:
            # Próxima linha tem os valores
            if i + 1 < len(linhas):
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linhas[i + 1])
                if len(valores) >= 3:
                    # Formato: [bruto, desconto, líquido]
                    info['vencimentos_total'] = float(valores[0].replace('.', '').replace(',', '.'))
                    info['descontos_total'] = float(valores[1].replace('.', '').replace(',', '.'))
                    info['liquido'] = float(valores[2].replace('.', '').replace(',', '.'))
                    break
    
    # Estratégia alternativa: buscar separadamente
    if info['liquido'] == 0.0:
        for i, linha in enumerate(linhas):
            linha_norm = normalizar_texto(linha)
            
            # Busca "Bruto"
            if 'BRUTO' in linha_norm and 'DESCONTO' not in linha_norm:
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
                if valores:
                    info['vencimentos_total'] = float(valores[-1].replace('.', '').replace(',', '.'))
            
            # Busca "Desconto"
            if 'DESCONTO' in linha_norm and 'BRUTO' not in linha_norm:
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
                if valores:
                    info['descontos_total'] = float(valores[-1].replace('.', '').replace(',', '.'))
            
            # Busca "Valor Liquido"
            if 'VALOR LIQUIDO' in linha_norm or 'VALOR LÍQUIDO' in linha_norm:
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
                if valores:
                    info['liquido'] = float(valores[-1].replace('.', '').replace(',', '.'))
    
    # Calcular líquido se ainda não foi encontrado
    if info['liquido'] == 0.0 and info['vencimentos_total'] > 0:
        info['liquido'] = info['vencimentos_total'] - info['descontos_total']
    
    return info


def extrair_salario_bruto_camara_deputados(texto: str) -> float:
    """
    Extrai o valor do salário base da Câmara dos Deputados
    Busca por "VENCIMENTO" (código 30)
    """
    linhas = texto.split('\n')
    
    # Prioridade 1: Buscar código "30 VENCIMENTO"
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if re.match(r'^\s*30\s+VENCIMENTO', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    # Prioridade 2: Buscar "VENCIMENTO" em qualquer posição
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'VENCIMENTO' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    return 0.0


def extrair_vencimentos_fixos_camara_deputados(texto: str) -> Dict:
    """
    Extrai vencimentos da Câmara dos Deputados da coluna de VENCIMENTOS
    
    IMPORTANTE: Para o cálculo de margem da Câmara dos Deputados,
    considera-se APENAS o VENCIMENTO (código 30) como provento permanente.
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'adicional_tempo_servico': 0.0,
        'gratificacao': 0.0,
        'hora_ativ_extra_classe': 0.0,
        'aula_suplementar': 0.0,
        'vale_alimentacao': 0.0,
        'sexta_parte': 0.0,
        'horas_extras': 0.0,
        'insalubridade': 0.0,
        'sessoes_noturnas': 0.0,
        'auxilio_alimentacao': 0.0,
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # VENCIMENTO (código 30)
        # Este é o ÚNICO provento permanente considerado para margem na Câmara dos Deputados
        if re.match(r'^\s*30\s+VENCIMENTO', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['vencimento_base'] = valor
                vencimentos_fixos['total'] += valor
            continue

    return vencimentos_fixos

# ============================================================================
# FUNÇÕES ESPECÍFICAS POR PREFEITURA - PONTA GROSSA
# ============================================================================

def extrair_informacoes_ponta_grossa(texto: str) -> Dict:
    """
    Extrai informações específicas de Ponta Grossa - PR
    Estrutura: CADASTRO / NOME / CARGO / VENCIMENTOS / DESCONTOS / LÍQUIDO
    """
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
    }
    
    linhas = texto.split('\n')
    
    # ============================================================
    # EXTRAÇÃO DE MATRÍCULA (CADASTRO)
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        if 'CADASTRO' in linha_norm:
            # Formato: 32925
            match = re.search(r'(\d{5})', linha)
            if match:
                info['matricula'] = match.group(1)
            elif i + 1 < len(linhas):
                match = re.search(r'(\d{5})', linhas[i + 1])
                if match:
                    info['matricula'] = match.group(1)
    
    # ============================================================
    # EXTRAÇÃO DE NOME
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        if 'NOME' in linha_norm:
            # Nome vem na próxima linha após o cabeçalho
            if i + 1 < len(linhas):
                proxima_linha = linhas[i + 1].strip()
                # Remove matrícula do início
                nome_candidato = re.sub(r'^\d{5}\s*', '', proxima_linha)
                # Remove data de admissão do final (formato: 22/10/2024)
                nome_candidato = re.sub(r'\s*\d{2}/\d{2}/\d{4}.*$', '', nome_candidato)
                
                if len(nome_candidato) > 3 and not nome_candidato.isdigit():
                    info['nome'] = nome_candidato.strip()
                    break
    
    # ============================================================
    # EXTRAÇÃO DE VALORES FINANCEIROS
    # ============================================================
    
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        
        # Busca "TOTAL DE VENCIMENTOS" e pega valor da mesma linha ou linha seguinte
        if 'TOTAL DE VENCIMENTOS' in linha_norm:
            # Tenta na mesma linha primeiro
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                # Pega o valor que vem após "TOTAL DE VENCIMENTOS"
                # Se houver múltiplos valores, pega o penúltimo ou último
                if len(valores) >= 2:
                    info['vencimentos_total'] = float(valores[-2].replace('.', '').replace(',', '.'))
                else:
                    info['vencimentos_total'] = float(valores[-1].replace('.', '').replace(',', '.'))
            elif i + 1 < len(linhas):
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linhas[i + 1])
                if valores and len(valores) >= 4:
                    # Na linha de valores: salario_base, salario_contr, faixa_irrf, vencimentos, descontos
                    info['vencimentos_total'] = float(valores[3].replace('.', '').replace(',', '.'))
                    if len(valores) >= 5:
                        info['descontos_total'] = float(valores[4].replace('.', '').replace(',', '.'))
        
        # Busca "TOTAL DE DESCONTOS" (caso não tenha sido capturado acima)
        if not info['descontos_total'] and 'TOTAL DE DESCONTOS' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                info['descontos_total'] = float(valores[-1].replace('.', '').replace(',', '.'))
            elif i + 1 < len(linhas):
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linhas[i + 1])
                if valores:
                    info['descontos_total'] = float(valores[-1].replace('.', '').replace(',', '.'))
        
        # Busca "VALOR LIQUIDO" - o valor está na linha ANTERIOR ao rótulo
        if 'VALOR LIQUIDO' in linha_norm or 'VALOR LÍQUIDO' in linha_norm:
            # Tenta na mesma linha primeiro
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                info['liquido'] = float(valores[-1].replace('.', '').replace(',', '.'))
            # Se não encontrou, busca na linha ANTERIOR (onde estão os valores numéricos)
            elif i > 0:
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linhas[i - 1])
                if valores:
                    # O valor líquido é o último valor da linha anterior
                    info['liquido'] = float(valores[-1].replace('.', '').replace(',', '.'))
    
    # Estratégia alternativa: Procurar linha com BASE CALCULO IRRF
    if info['liquido'] == 0.0:
        for i, linha in enumerate(linhas):
            linha_norm = normalizar_texto(linha)
            if 'BASE CALCULO IRRF' in linha_norm or 'BASE CÁLCULO IRRF' in linha_norm:
                # Valores estão na linha anterior
                if i > 0:
                    valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linhas[i - 1])
                    if valores and len(valores) >= 4:
                        # Último valor é o líquido
                        info['liquido'] = float(valores[-1].replace('.', '').replace(',', '.'))
                        break
    
    # Calcular líquido se não foi encontrado
    if info['liquido'] == 0.0 and info['vencimentos_total'] > 0:
        info['liquido'] = info['vencimentos_total'] - info['descontos_total']
    
    return info


def extrair_salario_bruto_ponta_grossa(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque de PONTA GROSSA
    Busca por "Salario" (código 001)
    """
    linhas = texto.split('\n')
    
    # Prioridade 1: Buscar "001 Salario"
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if re.match(r'^\s*001\s+SALARIO', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    # Prioridade 2: Buscar "SALARIO" em qualquer posição
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'SALARIO' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    return 0.0


def extrair_vencimentos_fixos_ponta_grossa(texto: str) -> Dict:
    """
    Extrai vencimentos de PONTA GROSSA da coluna de VENCIMENTOS
    
    IMPORTANTE: Para o cálculo de margem de Ponta Grossa,
    considera-se APENAS o SALÁRIO BASE como provento permanente.
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'adicional_tempo_servico': 0.0,
        'gratificacao': 0.0,
        'hora_ativ_extra_classe': 0.0,
        'aula_suplementar': 0.0,
        'vale_alimentacao': 0.0,
        'sexta_parte': 0.0,
        'horas_extras': 0.0,
        'insalubridade': 0.0,
        'horas_intrajornadas': 0.0,
        'premio_assiduidade': 0.0,
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # SALARIO BASE - código 005 "Salario Cargo em Comissao"
        # Este é o ÚNICO provento permanente considerado para margem em Ponta Grossa
        if 'SALARIO CARGO EM COMISSAO' in linha_norm or re.match(r'^\s*005\s+', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['vencimento_base'] = valor
                vencimentos_fixos['total'] += valor
            continue

    return vencimentos_fixos

# ============================================================================
# FUNÇÕES ESPECÍFICAS POR PREFEITURA - RIBEIRÃO PRETO
# ============================================================================

def extrair_informacoes_ribeirao_preto(texto: str) -> Dict:
    """
    Extrai informações específicas de Ribeirão Preto - SP
    Estrutura: Matrícula / Nome / RG / CPF / Vencimentos / Descontos / Líquido
    """
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
    }
    
    linhas = texto.split('\n')
    
    # ============================================================
    # EXTRAÇÃO DE MATRÍCULA
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        if 'MATRICULA' in linha_norm:
            # Formato: 49592.01
            match = re.search(r'(\d{5}\.\d{2})', linha)
            if match:
                info['matricula'] = match.group(1)
            elif i + 1 < len(linhas):
                match = re.search(r'(\d{5}\.\d{2})', linhas[i + 1])
                if match:
                    info['matricula'] = match.group(1)
    
    # ============================================================
    # EXTRAÇÃO DE NOME
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        if 'NOME DO FUNCIONARIO' in linha_norm:
            # Nome vem na próxima linha após o cabeçalho
            if i + 1 < len(linhas):
                proxima_linha = linhas[i + 1].strip()
                # Remove matrícula do início (formato: 49592.01)
                nome_candidato = re.sub(r'^\d{5}\.\d{2}\s*', '', proxima_linha)
                # Remove data de admissão do final (formato: 01/09/2025)
                nome_candidato = re.sub(r'\s*\d{2}/\d{2}/\d{4}.*$', '', nome_candidato)
                # Remove palavra ADMISSAO se aparecer
                nome_candidato = re.sub(r'\s*ADMISSAO.*$', '', nome_candidato, flags=re.IGNORECASE)
                
                if len(nome_candidato) > 3 and not nome_candidato.isdigit():
                    info['nome'] = nome_candidato.strip()
                    break
    
    # ============================================================
    # EXTRAÇÃO DE VALORES FINANCEIROS
    # ============================================================
    
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        
        # Busca "Total Vencimentos"
        if 'TOTAL VENCIMENTOS' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                info['vencimentos_total'] = float(valores[-1].replace('.', '').replace(',', '.'))
        
        # Busca "Total Descontos"
        if 'TOTAL DESCONTOS' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                info['descontos_total'] = float(valores[-1].replace('.', '').replace(',', '.'))
        
        # Busca "Valor Liquido" ou "Valor Líquido"
        if 'VALOR LIQUIDO' in linha_norm or 'VALOR LÍQUIDO' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                info['liquido'] = float(valores[-1].replace('.', '').replace(',', '.'))
    
    # Calcular líquido se não foi encontrado
    if info['liquido'] == 0.0 and info['vencimentos_total'] > 0:
        info['liquido'] = info['vencimentos_total'] - info['descontos_total']
    
    return info


def extrair_salario_bruto_ribeirao_preto(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque de RIBEIRÃO PRETO
    Busca por "AULAS P.(TDA)" (código 7)
    """
    linhas = texto.split('\n')
    
    # Prioridade 1: Buscar "AULAS P.(TDA)" (vencimento base)
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'AULAS P.(TDA)' in linha_norm or 'AULAS P (TDA)' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    # Prioridade 2: Buscar "Salário Referência"
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        if 'SALARIO REFERENCIA' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                valor_str = valores[0].replace('.', '').replace(',', '.')
                return float(valor_str)
    
    return 0.0


def extrair_vencimentos_fixos_ribeirao_preto(texto: str) -> Dict:
    """
    Extrai vencimentos PERMANENTES de RIBEIRÃO PRETO conforme especificação.

    BASE DE CÁLCULO = SOMA DOS PROVENTOS DE NATUREZA PERMANENTE OU FIXAS
    deduzindo os consignados compulsórios.

    INCLUI APENAS (proventos permanentes/fixos):
    - cód. 7  - AULAS P.(TDA)      → Salário base permanente
    - cód. 8  - TDC (.PERMANENT)   → Adicional permanente
    - cód. 9  - TDI (.PERMANENT)   → Adicional permanente
    - Acréscimos e insalubridade quando permanentes
    - Todas as GRATIFICAÇÕES FIXAS

    EXCLUÍDOS (proventos eventuais/variáveis):
    - cód. 37  - AULAS E.(TDA)      → Eventuais
    - cód. 38  - TDC (.EVENTUAIS)   → Eventuais
    - cód. 39  - TDI (.EVENTUAIS)   → Eventuais
    - cód. 184 - AULA EXTRAORDIN    → Extras (variável)
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'tdc_permanente': 0.0,
        'tdi_permanente': 0.0,
        'insalubridade': 0.0,
        'gratificacao': 0.0,
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # cód. 7 — AULAS P.(TDA): Salário base permanente ✅
        if 'AULAS P.(TDA)' in linha_norm or 'AULAS P (TDA)' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['vencimento_base'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # cód. 8 — TDC (.PERMANENT): Adicional permanente ✅
        if 'TDC (.PERMANENT' in linha_norm or 'TDC (PERMANENT' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['tdc_permanente'] += valor
                vencimentos_fixos['total'] += valor
            continue

        # cód. 9 — TDI (.PERMANENT): Adicional permanente ✅
        if 'TDI (.PERMANENT' in linha_norm or 'TDI (PERMANENT' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['tdi_permanente'] += valor
                vencimentos_fixos['total'] += valor
            continue

        # INSALUBRIDADE permanente ✅
        if 'INSALUBR' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['insalubridade'] += valor
                vencimentos_fixos['total'] += valor
            continue

        # GRATIFICAÇÕES FIXAS ✅ (exceto eventuais/extras)
        if ('GRAT' in linha_norm and 'DESCONTO' not in linha_norm
                and 'EVENTUAL' not in linha_norm and 'EXTRA' not in linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['gratificacao'] += valor
                vencimentos_fixos['total'] += valor
            continue

        # ACRÉSCIMO permanente ✅
        if ('ACRESC' in linha_norm and 'DESCONTO' not in linha_norm
                and 'EVENTUAL' not in linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['outros_fixos'].append({
                    'descricao': linha.strip()[:30],
                    'valor': valor
                })
                vencimentos_fixos['total'] += valor
            continue

        # EXCLUÍDOS EXPLICITAMENTE — não somar ao total:
        # cód. 37 AULAS E.(TDA), cód. 38 TDC(.EVENTUAIS),
        # cód. 39 TDI(.EVENTUAIS), cód. 184 AULA EXTRAORDIN

    return vencimentos_fixos

# ============================================================================
# FUNÇÕES ESPECÍFICAS POR PREFEITURA - CAMPOS DO JORDÃO
# ============================================================================

def extrair_informacoes_campos_jordao(texto: str) -> Dict:
    """
    Extrai informações específicas de Campos do Jordão - SP
    Estrutura: Funcionário / Banco / Vencimentos / Descontos / Líquido
    """
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
    }
    
    linhas = texto.split('\n')
    
    # ============================================================
    # EXTRAÇÃO DE MATRÍCULA E NOME
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        # Procura por "Funcionario" seguido de matrícula e nome na próxima linha
        if 'FUNCIONARIO' in linha_norm:
            # Próxima linha tem formato: "8473 MARIA DALVA DA SILVA"
            if i + 1 < len(linhas):
                proxima_linha = linhas[i + 1].strip()
                match = re.search(r'^(\d{4,6})\s+([A-Z][A-Z\s]+)', proxima_linha)
                if match:
                    info['matricula'] = match.group(1)
                    nome_candidato = match.group(2).strip()
                    if len(nome_candidato) > 3:
                        info['nome'] = nome_candidato
                        break
    
    # ============================================================
    # EXTRAÇÃO DE VALORES FINANCEIROS
    # ============================================================
    
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        
        # Busca linha com "Salário Base | Vencimentos | Descontos | Líquido"
        if 'SALARIO BASE' in linha_norm and 'VENCIMENTOS' in linha_norm and 'DESCONTOS' in linha_norm and 'LIQUIDO' in linha_norm:
            # Próxima linha tem os valores: salário_base | vencimentos | descontos | líquido
            if i + 1 < len(linhas):
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linhas[i + 1])
                if len(valores) >= 4:
                    # valores[0] = salário base
                    # valores[1] = vencimentos total
                    # valores[2] = descontos total
                    # valores[3] = líquido
                    info['vencimentos_total'] = float(valores[1].replace('.', '').replace(',', '.'))
                    info['descontos_total'] = float(valores[2].replace('.', '').replace(',', '.'))
                    info['liquido'] = float(valores[3].replace('.', '').replace(',', '.'))
                    break
    
    # Estratégia alternativa: buscar separadamente se não encontrou na linha combinada
    if info['liquido'] == 0.0:
        for i, linha in enumerate(linhas):
            linha_norm = normalizar_texto(linha)
            
            # Busca "Vencimentos" 
            if 'VENCIMENTOS' in linha_norm and 'DESCONTOS' in linha_norm and 'LIQUIDO' in linha_norm:
                if i + 1 < len(linhas):
                    valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linhas[i + 1])
                    if len(valores) >= 3:
                        info['vencimentos_total'] = float(valores[0].replace('.', '').replace(',', '.'))
                        info['descontos_total'] = float(valores[1].replace('.', '').replace(',', '.'))
                        info['liquido'] = float(valores[2].replace('.', '').replace(',', '.'))
                        break
    
    # Calcular líquido se ainda não foi encontrado
    if info['liquido'] == 0.0 and info['vencimentos_total'] > 0:
        info['liquido'] = info['vencimentos_total'] - info['descontos_total']
    
    return info


def extrair_salario_bruto_campos_jordao(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque de CAMPOS DO JORDÃO
    Busca por "SALARIO" na coluna de vencimentos
    """
    linhas = texto.split('\n')
    
    # Prioridade 1: Buscar "SALARIO" como primeira linha de vencimento
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if linha_norm.strip().startswith('SALARIO') or 'VENCIMENTO' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    # Prioridade 2: Buscar "SALARIO BASE" 
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'SALARIO BASE' in linha_norm or 'SALARIO' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    return 0.0


def extrair_vencimentos_fixos_campos_jordao(texto: str) -> Dict:
    """
    Extrai vencimentos PERMANENTES de CAMPOS DO JORDÃO conforme especificação.

    BASE DE CÁLCULO = SOMA DOS PROVENTOS DE NATUREZA PERMANENTE OU FIXAS
    deduzindo os consignados compulsórios.

    INCLUI APENAS (proventos permanentes):
    - 30  - SALARIO
    - 1210 - ADICIONAL POR TEMPO (Adicional de Tempo de Serviço)
    - 1370 - SEXTA PARTE

    EXCLUÍDOS (não entram na base):
    - 190  - SALARIO FAMILIA (eventual/temporário)
    - 4900 - ABONO (eventual)
    - Horas extras, insalubridade, gratificações eventuais etc.
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'adicional_tempo_servico': 0.0,
        'sexta_parte': 0.0,
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # SALARIO (código 30) — provento permanente base
        # Exclui SALARIO FAMILIA (código 190) verificando ausência de 'FAMILIA'
        if re.search(r'^\s*30\s+SALARIO', linha_norm) or (
            'SALARIO' in linha_norm
            and 'FAMILIA' not in linha_norm
            and 'DESCONTO' not in linha_norm
            and re.match(r'^\s*30\b', linha_norm)
        ):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['vencimento_base'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # ADICIONAL POR TEMPO (código 1210)
        if re.search(r'^\s*1210\b', linha_norm) or (
            'ADICIONAL' in linha_norm and 'TEMPO' in linha_norm and 'DESCONTO' not in linha_norm
        ):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['adicional_tempo_servico'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # SEXTA PARTE (código 1370)
        if re.search(r'^\s*1370\b', linha_norm) or (
            'SEXTA PARTE' in linha_norm and 'DESCONTO' not in linha_norm
        ):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['sexta_parte'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # EXCLUÍDOS EXPLICITAMENTE — não somar ao total:
        # SALARIO FAMILIA (190), ABONO (4900), horas extras, insalubridade, etc.

    return vencimentos_fixos


# ============================================================================
# FUNÇÕES ESPECÍFICAS POR PREFEITURA - BARCARENA
# ============================================================================

def extrair_informacoes_barcarena(texto: str) -> Dict:
    """
    Extrai informações específicas de Barcarena - PA
    Estrutura: Matrícula / Nome / Vencimentos / Descontos / Líquido
    """
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
    }
    
    linhas = texto.split('\n')
    
    # ============================================================
    # EXTRAÇÃO DE MATRÍCULA
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        if 'MATRICULA' in linha_norm:
            # Formato: 8858-7/1
            match = re.search(r'(\d{4}-\d/\d)', linha)
            if match:
                info['matricula'] = match.group(1)
            elif i + 1 < len(linhas):
                match = re.search(r'(\d{4}-\d/\d)', linhas[i + 1])
                if match:
                    info['matricula'] = match.group(1)
    
    # ============================================================
    # EXTRAÇÃO DE NOME
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        if 'NOME:' in linha_norm or 'NOME :' in linha_norm:
            # Nome vem após "Nome:"
            match = re.search(r'NOME\s*:\s*([A-Z][A-Z\s]+?)(?:\s+SECRETARIA|\s+CARGO|$)', linha_norm)
            if match:
                info['nome'] = match.group(1).strip()
                break
            elif i + 1 < len(linhas):
                nome_candidato = linhas[i + 1].strip()
                # Remove possíveis rótulos
                nome_candidato = re.sub(r'^\s*(?:SECRETARIA|CARGO|ADMISSAO).*$', '', nome_candidato, flags=re.IGNORECASE)
                if len(nome_candidato) > 3 and not nome_candidato.isdigit():
                    info['nome'] = nome_candidato
                    break
    
    # ============================================================
    # EXTRAÇÃO DE VALORES FINANCEIROS
    # ============================================================
    
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        
        # Busca "Totais" (linha de soma de rendimentos e descontos)
        if linha_norm.strip() == 'TOTAIS' or 'TOTAIS' in linha_norm:
            # Próxima linha ou mesma linha pode ter os valores
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if len(valores) >= 2:
                info['vencimentos_total'] = float(valores[0].replace('.', '').replace(',', '.'))
                info['descontos_total'] = float(valores[1].replace('.', '').replace(',', '.'))
            elif i + 1 < len(linhas):
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linhas[i + 1])
                if len(valores) >= 2:
                    info['vencimentos_total'] = float(valores[0].replace('.', '').replace(',', '.'))
                    info['descontos_total'] = float(valores[1].replace('.', '').replace(',', '.'))
        
        # Busca "Valor Liquido" ou "Valor Líquido"
        if 'VALOR LIQUIDO' in linha_norm or 'VALOR LÍQUIDO' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                info['liquido'] = float(valores[-1].replace('.', '').replace(',', '.'))
            elif i + 1 < len(linhas):
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linhas[i + 1])
                if valores:
                    info['liquido'] = float(valores[0].replace('.', '').replace(',', '.'))
    
    # Calcular líquido se não foi encontrado
    if info['liquido'] == 0.0 and info['vencimentos_total'] > 0:
        info['liquido'] = info['vencimentos_total'] - info['descontos_total']
    
    return info


def extrair_salario_bruto_barcarena(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque de BARCARENA
    Busca por "SALARIO MENSAL" (código 2)
    """
    linhas = texto.split('\n')
    
    # Prioridade 1: Buscar código "2 Salário Mensal(Hrs)"
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if re.match(r'^\s*2\s+SALARIO MENSAL', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    # Prioridade 2: Buscar "SALARIO MENSAL" em qualquer posição
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'SALARIO MENSAL' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    return 0.0


def extrair_vencimentos_fixos_barcarena(texto: str) -> Dict:
    """
    Extrai vencimentos PERMANENTES/FIXOS de BARCARENA conforme especificação
    (Lei Complementar nº 002/94, de 01 de agosto de 1994)

    BASE DE CÁLCULO INCLUI APENAS:
    - Salário (Salário Mensal)
    - Adicional por tempo de serviço
    - Gratificações FIXAS (ex: Grat. Reg. de Classe, Grat. de Magistério)

    EXCLUÍDOS (não entram na base):
    - Substituição
    - Grat. por Prestação de Serviço Extraordinário
    - Grat. por Prestação de Serviço Noturno
    - Encargo de Professor/Auxiliar em Curso Oficialmente Instituído
    - Grat. por Exercício em Condições Insalubres, Perigosas ou Penosas
    - Grat. por Execução de Trabalho com Risco de Vida
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'adicional_tempo_servico': 0.0,
        'gratificacao': 0.0,
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # SALÁRIO MENSAL (código 1) — provento permanente base
        if 'SALARIO MENSAL' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['vencimento_base'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # ADICIONAL TEMPO DE SERVIÇO — permanente
        if 'ADIC TEMPO SERVICO' in linha_norm or 'ADICIONAL TEMPO SERVICO' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['adicional_tempo_servico'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # GRATIFICAÇÕES FIXAS (ex: Grat. Reg. de Classe, Grat. de Magistério)
        # EXCLUIR as variáveis: extraordinário, noturno, insalubridade, risco de vida, substituição
        if any(p in linha_norm for p in ['GRAT.REG.DE CLASSE', 'GRAT REG DE CLASSE',
                                          'GRAT.DE MAGISTERIO', 'GRAT DE MAGISTERIO']):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['gratificacao'] += valor
                vencimentos_fixos['total'] += valor
            continue

        # EXPLICITAMENTE EXCLUÍDOS — não somar ao total:
        # Serv. Extraordinário, Serv. Noturno, Insalubridade, Risco de Vida, Substituição, Encargos de Curso

    return vencimentos_fixos

# ============================================================================
# FUNÇÕES ESPECÍFICAS POR PREFEITURA - ITAITUBA
# ============================================================================

def extrair_informacoes_itaituba(texto: str) -> Dict:
    """
    Extrai informações específicas de Itaituba - PA
    Estrutura: Matrícula / Nome / Vencimentos / Descontos / Líquido
    """
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
    }
    
    linhas = texto.split('\n')
    
    # ============================================================
    # EXTRAÇÃO DE MATRÍCULA
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        if 'MATRICULA' in linha_norm and 'MATRICULA ANTERIOR' not in linha_norm:
            # Tenta extrair da mesma linha (formato: 164347-9)
            match = re.search(r'(\d{6}-\d)', linha)
            if match:
                info['matricula'] = match.group(1)
            # Tenta próxima linha
            elif i + 1 < len(linhas):
                match = re.search(r'(\d{6}-\d)', linhas[i + 1])
                if match:
                    info['matricula'] = match.group(1)
    
    # ============================================================
    # EXTRAÇÃO DE NOME
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        if 'NOME:' in linha_norm or 'NOME :' in linha_norm:
            # Nome vem após "Nome:"
            match = re.search(r'NOME\s*:\s*([A-Z][A-Z\s]+?)(?:\s+VINCULO|\s+ADMISSAO|$)', linha_norm)
            if match:
                info['nome'] = match.group(1).strip()
                break
            # Tenta próxima linha
            elif i + 1 < len(linhas):
                nome_candidato = linhas[i + 1].strip()
                # Remove possíveis rótulos
                nome_candidato = re.sub(r'^\s*(?:VINCULO|ADMISSAO|PISPASEP).*$', '', nome_candidato, flags=re.IGNORECASE)
                if len(nome_candidato) > 3 and not nome_candidato.isdigit():
                    info['nome'] = nome_candidato
                    break
    
    # ============================================================
    # EXTRAÇÃO DE VALORES FINANCEIROS
    # ============================================================
    
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        
        # Busca "Total de vencimentos"
        if 'TOTAL DE VENCIMENTOS' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                info['vencimentos_total'] = float(valores[-1].replace('.', '').replace(',', '.'))
            # Tenta próxima linha se não encontrou
            elif i + 1 < len(linhas):
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linhas[i + 1])
                if valores:
                    info['vencimentos_total'] = float(valores[0].replace('.', '').replace(',', '.'))
        
        # Busca "Total de descontos"
        if 'TOTAL DE DESCONTOS' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                info['descontos_total'] = float(valores[-1].replace('.', '').replace(',', '.'))
            # Tenta próxima linha se não encontrou
            elif i + 1 < len(linhas):
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linhas[i + 1])
                if valores:
                    info['descontos_total'] = float(valores[0].replace('.', '').replace(',', '.'))
        
        # Busca "Valor Liquido" ou "Valor Líquido"
        if 'VALOR LIQUIDO' in linha_norm or 'VALOR LÍQUIDO' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                info['liquido'] = float(valores[-1].replace('.', '').replace(',', '.'))
            # Tenta próxima linha se não encontrou
            elif i + 1 < len(linhas):
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linhas[i + 1])
                if valores:
                    info['liquido'] = float(valores[0].replace('.', '').replace(',', '.'))
    
    # Calcular líquido se não foi encontrado
    if info['liquido'] == 0.0 and info['vencimentos_total'] > 0:
        info['liquido'] = info['vencimentos_total'] - info['descontos_total']
    
    return info


def extrair_salario_bruto_itaituba(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque de ITAITUBA
    Busca por "SALARIO BASE" (código K1)
    """
    linhas = texto.split('\n')
    
    # Prioridade 1: Buscar código "K1 SALARIO BASE"
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if re.match(r'^\s*K1\s+SALARIO BASE', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    # Prioridade 2: Buscar "SALARIO BASE" em qualquer posição
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'SALARIO BASE' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    return 0.0


def extrair_vencimentos_fixos_itaituba(texto: str) -> Dict:
    """
    Extrai vencimentos PERMANENTES de ITAITUBA conforme especificação
    
    Considera apenas:
    - SALÁRIO
    - GRATIFICAÇÃO FIXA
    - ASSISTÊNCIA FINANCEIRA COMP
    - ADICIONAL NOTURNO
    - INSALUBRIDADE
    
    NÃO considera: Salário família
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'gratificacao': 0.0,
        'assistencia_financeira': 0.0,
        'adicional_noturno': 0.0,
        'insalubridade': 0.0,
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # SALARIO BASE (código K1)
        if re.match(r'^\s*K1\s+SALARIO BASE', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['vencimento_base'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # GRATIFICAÇÃO FIXA (apenas fixas, não esporádicas)
        if 'GRATIFICACAO' in linha_norm and 'FIXA' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['gratificacao'] = valor
                vencimentos_fixos['total'] += valor
            continue
        
        # GRATIFICAÇÃO genérica (considerar como fixa se não for explicitamente variável)
        if 'GRAT' in linha_norm and 'DESCONTO' not in linha_norm:
            # Excluir gratificações esporádicas conhecidas
            if not any(excluir in linha_norm for excluir in ['FERIAS', '13', 'EVENTUAL', 'EXTRA']):
                valor = extrair_valores_vencimento(linha)
                if valor > 0:
                    vencimentos_fixos['gratificacao'] = valor
                    vencimentos_fixos['total'] += valor
                continue

        # ASSISTÊNCIA FINANCEIRA COMP
        if ('ASSISTENCIA FINANCEIRA' in linha_norm or 'ASSIST. FINANCEIRA' in linha_norm or 
            'ASSIST FINANCEIRA' in linha_norm) and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['assistencia_financeira'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # ADICIONAL NOTURNO
        if ('ADICIONAL NOTURNO' in linha_norm or 'ADIC. NOTURNO' in linha_norm or 
            'ADIC NOTURNO' in linha_norm) and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['adicional_noturno'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # INSALUBRIDADE
        if 'INSALUBR' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['insalubridade'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # EXCLUIR EXPLICITAMENTE:
        # - Salário família (conforme observação da especificação)
        if 'SALARIO FAMILIA' in linha_norm or 'SAL. FAMILIA' in linha_norm:
            continue

    return vencimentos_fixos

# ============================================================================
# FUNÇÕES ESPECÍFICAS POR PREFEITURA - TUPÃ
# ============================================================================

def extrair_informacoes_tupa(texto: str) -> Dict:
    """
    Extrai informações específicas de Tupã - SP
    Estrutura: Matrícula / Nome / Vencimentos / Descontos / Líquido
    """
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
    }
    
    linhas = texto.split('\n')
    
    # ============================================================
    # EXTRAÇÃO DE MATRÍCULA E NOME
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        # Procura por "Matrícula" seguido do número e nome
        if 'MATRICULA' in linha_norm and i + 1 < len(linhas):
            # Próxima linha pode ter: "50245-4 Nome ROSICLEIA LUCIA..."
            proxima_linha = linhas[i + 1].strip()
            match = re.search(r'^(\d{4,6}-?\d?)\s+(.+?)(?:\s+PIS|\s+\d{10,}|$)', proxima_linha)
            if match:
                info['matricula'] = match.group(1)
                nome_candidato = match.group(2).strip()
                # Remove "Nome" se estiver no início
                nome_candidato = re.sub(r'^NOME\s+', '', nome_candidato, flags=re.IGNORECASE)
                if len(nome_candidato) > 3:
                    info['nome'] = nome_candidato
                    break
    
    # Estratégia alternativa se não encontrou
    if not info['matricula'] or not info['nome']:
        for i, linha in enumerate(linhas[:50]):
            # Procura padrão "número-número Nome NOME COMPLETO"
            match = re.search(r'^(\d{4,6}-\d)\s+(?:NOME\s+)?([A-Z][A-Z\s]+?)\s+(?:PIS|ADMISSAO|\d{10,})', linha)
            if match:
                info['matricula'] = match.group(1)
                info['nome'] = match.group(2).strip()
                break
    
    # ============================================================
    # EXTRAÇÃO DE VALORES FINANCEIROS
    # ============================================================
    
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        
        # Busca "Total de Vencimentos" e "Total de Descontos" na mesma estrutura
        if 'TOTAL DE VENCIMENTOS' in linha_norm and 'TOTAL DE DESCONTOS' in linha_norm:
            # Próxima linha deve ter os valores
            if i + 1 < len(linhas):
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linhas[i + 1])
                if len(valores) >= 2:
                    info['vencimentos_total'] = float(valores[0].replace('.', '').replace(',', '.'))
                    info['descontos_total'] = float(valores[1].replace('.', '').replace(',', '.'))
        
        # Busca "Valor Líquido"
        if 'VALOR LIQUIDO' in linha_norm or 'VALOR LÍQUIDO' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                info['liquido'] = float(valores[-1].replace('.', '').replace(',', '.'))
    
    # Calcular líquido se não foi encontrado
    if info['liquido'] == 0.0 and info['vencimentos_total'] > 0:
        info['liquido'] = info['vencimentos_total'] - info['descontos_total']
    
    return info


def extrair_salario_bruto_tupa(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque de TUPÃ
    Busca por "SALARIO BASE" (código 001)
    """
    linhas = texto.split('\n')
    
    # Prioridade 1: Buscar código "001 SALARIO BASE"
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if re.match(r'^\s*001\s+SALARIO BASE', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    # Prioridade 2: Buscar "SALARIO BASE" em qualquer posição
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'SALARIO BASE' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    return 0.0


def extrair_vencimentos_fixos_tupa(texto: str) -> Dict:
    """
    Extrai vencimentos PERMANENTES de TUPÃ conforme especificação
    
    Considera apenas: SALÁRIO BASE
    NÃO considera: Gratificações, Férias, Horas Extras, etc.
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # SALARIO BASE (código 001) - ÚNICO PROVENTO PERMANENTE
        if re.match(r'^\s*001\s+SALARIO BASE', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['vencimento_base'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # EXCLUIR EXPLICITAMENTE (não considerar como permanentes):
        # - Gratificações (todas)
        # - Férias (incluindo 1/3)
        # - Horas extras
        # - Afastamentos
        # - Qualquer outro provento variável

    return vencimentos_fixos

# ============================================================================
# FUNÇÕES ESPECÍFICAS POR PREFEITURA - SALTO
# ============================================================================

def extrair_informacoes_salto(texto: str) -> Dict:
    """
    Extrai informações específicas de Salto - SP
    Estrutura: Matrícula / Nome / Vencimentos / Descontos / Líquido
    """
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
    }
    
    linhas = texto.split('\n')
    
    # ============================================================
    # EXTRAÇÃO DE MATRÍCULA E NOME JUNTOS
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        # Procura por linha que começa com número de 5 dígitos seguido de nome
        # Formato: "10149 JAQUELINE APARECIDA STECCA"
        match = re.search(r'^(\d{5})\s+([A-Z][A-Z\s]+?)(?:\s+\d{5}|\s*$)', linha.strip())
        if match and not info['matricula']:
            info['matricula'] = match.group(1)
            nome_candidato = match.group(2).strip()
            # Remove possíveis números ou códigos do final
            nome_candidato = re.sub(r'\s+\d+$', '', nome_candidato)
            if len(nome_candidato) > 3 and not nome_candidato.isdigit():
                info['nome'] = nome_candidato
                break
    
    # Se não encontrou, tenta estratégia alternativa
    if not info['matricula'] or not info['nome']:
        for i, linha in enumerate(linhas[:50]):
            linha_norm = normalizar_texto(linha)
            
            if 'FUNCIONARIO' in linha_norm and i + 1 < len(linhas):
                proxima_linha = linhas[i + 1].strip()
                # Tenta extrair matrícula e nome da próxima linha
                match = re.search(r'^(\d{5})\s+(.+)', proxima_linha)
                if match:
                    if not info['matricula']:
                        info['matricula'] = match.group(1)
                    if not info['nome']:
                        nome_candidato = match.group(2).strip()
                        # Remove possíveis números do final
                        nome_candidato = re.sub(r'\s+\d{5}.*$', '', nome_candidato)
                        if len(nome_candidato) > 3:
                            info['nome'] = nome_candidato
                    break
    
    # ============================================================
    # EXTRAÇÃO DE VALORES FINANCEIROS
    # ============================================================
    
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        
        # Busca linha com "Salário Base" seguida de "Vencimentos Descontos Líquido"
        if 'SALARIO BASE' in linha_norm and 'VENCIMENTOS' in linha_norm and 'DESCONTOS' in linha_norm and 'LIQUIDO' in linha_norm:
            # Próxima linha tem os valores: valor_salario_base  vencimentos  descontos  liquido
            if i + 1 < len(linhas):
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linhas[i + 1])
                if len(valores) >= 3:
                    # Pega os últimos 3 valores (vencimentos, descontos, líquido)
                    info['vencimentos_total'] = float(valores[-3].replace('.', '').replace(',', '.'))
                    info['descontos_total'] = float(valores[-2].replace('.', '').replace(',', '.'))
                    info['liquido'] = float(valores[-1].replace('.', '').replace(',', '.'))
        
        # Alternativa: Buscar separadamente por cada campo
        if not info['vencimentos_total']:
            # Busca por linha que contém apenas "Vencimentos" como cabeçalho
            if linha_norm.strip() == 'VENCIMENTOS' or (linha_norm.startswith('VENCIMENTOS') and 'DESCONTOS' not in linha_norm):
                # Valor pode estar na mesma linha ou próxima
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
                if valores:
                    info['vencimentos_total'] = float(valores[0].replace('.', '').replace(',', '.'))
                elif i + 1 < len(linhas):
                    valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linhas[i + 1])
                    if valores:
                        info['vencimentos_total'] = float(valores[0].replace('.', '').replace(',', '.'))
        
        if not info['descontos_total']:
            # Busca por linha que contém apenas "Descontos" como cabeçalho
            if linha_norm.strip() == 'DESCONTOS' or (linha_norm.startswith('DESCONTOS') and 'VENCIMENTOS' not in linha_norm and 'LIQUIDO' not in linha_norm):
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
                if valores:
                    info['descontos_total'] = float(valores[0].replace('.', '').replace(',', '.'))
                elif i + 1 < len(linhas):
                    valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linhas[i + 1])
                    if valores:
                        info['descontos_total'] = float(valores[0].replace('.', '').replace(',', '.'))
        
        # Buscar especificamente "Líquido" (o valor final)
        if not info['liquido']:
            if linha_norm.strip() == 'LIQUIDO' or linha_norm.strip() == 'LÍQUIDO' or (linha_norm.startswith('LIQUIDO') and 'VENCIMENTOS' not in linha_norm and 'DESCONTOS' not in linha_norm):
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
                if valores:
                    # Pega o último valor da linha (que é o líquido)
                    info['liquido'] = float(valores[-1].replace('.', '').replace(',', '.'))
                elif i + 1 < len(linhas):
                    valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linhas[i + 1])
                    if valores:
                        info['liquido'] = float(valores[-1].replace('.', '').replace(',', '.'))
    
    # Calcular líquido se não foi encontrado
    if info['liquido'] == 0.0 and info['vencimentos_total'] > 0 and info['descontos_total'] > 0:
        info['liquido'] = info['vencimentos_total'] - info['descontos_total']
    
    return info


def extrair_salario_bruto_salto(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque de SALTO
    Busca por "SALARIO BASE" (código 10)
    """
    linhas = texto.split('\n')
    
    # Prioridade 1: Buscar código "10 SALARIO BASE"
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if re.match(r'^\s*10\s+SALARIO BASE', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    # Prioridade 2: Buscar "SALARIO BASE" em qualquer posição
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'SALARIO BASE' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    return 0.0


def extrair_vencimentos_fixos_salto(texto: str) -> Dict:
    """
    Extrai vencimentos PERMANENTES de SALTO conforme Art. 6º
    
    NÃO considera (conforme especificação):
    - diárias, salário função, ajuda de custo
    - adicional de horas extraordinárias
    - décimo terceiro salário
    - auxílio-natalidade, auxílio-funeral
    - um terço sobre férias
    - substituição de professor
    - acréscimo salarial em cargo comissionado
    - gratificação de aniversário
    - outros acréscimos esporádicos
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'adicional_tempo_servico': 0.0,
        'gratificacao': 0.0,
        'insalubridade': 0.0,
        'progressao_salarial': 0.0,
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # SALARIO BASE (código 10) - PERMANENTE
        if re.match(r'^\s*10\s+SALARIO BASE', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['vencimento_base'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # PROGRESSAO SALARIAL (código 1730) - PERMANENTE
        if 'PROGRESSAO SALARIAL' in linha_norm or re.match(r'^\s*1730\s+', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['progressao_salarial'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # ADICIONAL INSALUBRIDADE (código 660) - PERMANENTE
        if 'ADICIONAL INSALUBRIDADE' in linha_norm or re.match(r'^\s*660\s+', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['insalubridade'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # GRATIFICACAO - APENAS permanentes (evitar gratificações esporádicas)
        # Incluir apenas gratificações fixas como SUS
        if 'GRATIFICACAO SUS' in linha_norm or re.match(r'^\s*720\s+', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['gratificacao'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # EXCLUIR EXPLICITAMENTE (não considerar):
        # - Horas extras/extraordinárias
        # - 13º salário
        # - Férias (1/3)
        # - Salário função
        # - Diárias
        # - Substituição
        # - Gratificação aniversário
        # - Faltas abonadas (código 1510, 1880) - são esporádicas
        if any(excluir in linha_norm for excluir in [
            'HORA EXTRA', 'HORAS EXTRAS', 'ADICIONAL HORAS EXTRAORDINARIAS',
            '13 SALARIO', '13° SALARIO', 'DECIMO TERCEIRO',
            'FERIAS', '1/3 FERIAS', 'TERCO FERIAS',
            'SALARIO FUNCAO', 'FUNCAO',
            'DIARIA',
            'SUBSTITUICAO',
            'GRATIFICACAO ANIVERSARIO',
            'FALTA ABONADA', 'FALTAS ABONADAS',
            'AUXILIO NATALIDADE', 'AUXILIO FUNERAL',
            'AJUDA DE CUSTO',
            'GRATIFICACAO TRABALHO NOTURNO'  # código 1790 - pode ser variável
        ]):
            continue

    return vencimentos_fixos

# ============================================================================
# FUNÇÕES ESPECÍFICAS POR PREFEITURA - TABOÃO DA SERRA
# ============================================================================

def extrair_informacoes_taboao_serra(texto: str) -> Dict:
    """
    Extrai informações específicas de Taboão da Serra - SP
    Estrutura: Matrícula / Nome / Vencimentos / Descontos / Líquido
    """
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
    }
    
    linhas = texto.split('\n')
    
    # ============================================================
    # EXTRAÇÃO DE MATRÍCULA
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        if 'MATRICULA' in linha_norm:
            # Tenta extrair da mesma linha
            match = re.search(r'(\d{6})', linha)
            if match:
                info['matricula'] = match.group(1)
                break
            # Tenta próxima linha
            elif i + 1 < len(linhas):
                match = re.search(r'^(\d{6})', linhas[i + 1].strip())
                if match:
                    info['matricula'] = match.group(1)
                    break
    
    # ============================================================
    # EXTRAÇÃO DE NOME
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        if 'NOME' in linha_norm and i + 1 < len(linhas):
            nome_candidato = linhas[i + 1].strip()
            # Remove matrícula se estiver no início
            nome_candidato = re.sub(r'^\d{6}\s*', '', nome_candidato)
            if len(nome_candidato) > 3 and not nome_candidato.isdigit():
                info['nome'] = nome_candidato
                break
    
    # ============================================================
    # EXTRAÇÃO DE VALORES FINANCEIROS
    # ============================================================
    
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        
        # Busca "VENCIMENTOS" no rodapé (total)
        if linha_norm.strip().startswith('VENCIMENTOS') and 'DESCONTOS' in linha_norm:
            # Próxima linha tem os valores
            if i + 1 < len(linhas):
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linhas[i + 1])
                if len(valores) >= 2:
                    info['vencimentos_total'] = float(valores[0].replace('.', '').replace(',', '.'))
                    info['descontos_total'] = float(valores[1].replace('.', '').replace(',', '.'))
        
        # Busca "VALOR TOTAL LIQUIDO"
        if 'VALOR TOTAL LIQUIDO' in linha_norm or 'VALOR TOTAL LÍQUIDO' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                info['liquido'] = float(valores[-1].replace('.', '').replace(',', '.'))
    
    # Calcular líquido se não foi encontrado
    if info['liquido'] == 0.0 and info['vencimentos_total'] > 0:
        info['liquido'] = info['vencimentos_total'] - info['descontos_total']
    
    return info


def extrair_salario_bruto_taboao_serra(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque de TABOÃO DA SERRA
    Busca por "VENCIMENTOS" (código 0001)
    """
    linhas = texto.split('\n')
    
    # Prioridade 1: Buscar código "0001 VENCIMENTOS"
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if re.match(r'^\s*0001\s+VENCIMENTOS', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    # Prioridade 2: Buscar "VENCIMENTO BASE" no cabeçalho
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        if 'VENCIMENTO BASE' in linha_norm:
            if i + 1 < len(linhas):
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linhas[i + 1])
                if valores:
                    valor_str = valores[0].replace('.', '').replace(',', '.')
                    return float(valor_str)
    
    return 0.0


def extrair_vencimentos_fixos_taboao_serra(texto: str) -> Dict:
    """
    Extrai vencimentos de TABOÃO DA SERRA da coluna de VENCIMENTOS
    
    Conforme especificações de Taboão da Serra:
    - SOMA DOS PROVENTOS DE NATUREZA PERMANENTE OU FIXAS
    - Apenas SALÁRIO (código 0001 - VENCIMENTOS)
    - NÃO considerar outros proventos como insalubridade, abono, salário-família
    
    Estrutura: CÓDIGO | HISTÓRICO | REFERÊNCIA | VENCIMENTOS | DESCONTOS
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # VENCIMENTOS (código 0001) - ÚNICO PROVENTO PERMANENTE
        if re.match(r'^\s*0001\s+VENCIMENTOS', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['vencimento_base'] = valor
                vencimentos_fixos['total'] = valor  # Apenas salário base
            continue

    return vencimentos_fixos

# ============================================================================
# FUNÇÕES ESPECÍFICAS POR PREFEITURA - LAGO VERDE
# ============================================================================

def extrair_informacoes_lago_verde(texto: str) -> Dict:
    """
    Extrai informações específicas de Lago Verde - MA
    Estrutura: Matrícula / Nome / CPF / Proventos / Descontos / Líquido
    """
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
    }
    
    linhas = texto.split('\n')
    
    # ============================================================
    # EXTRAÇÃO DE MATRÍCULA
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        if 'MATRICULA' in linha_norm:
            # Tenta extrair da mesma linha
            match = re.search(r'(\d{7})', linha)
            if match:
                info['matricula'] = match.group(1)
                break
            # Tenta próxima linha
            elif i + 1 < len(linhas):
                match = re.search(r'^(\d{7})', linhas[i + 1].strip())
                if match:
                    info['matricula'] = match.group(1)
                    break
    
    # ============================================================
    # EXTRAÇÃO DE NOME
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        if 'NOME' in linha_norm and i + 1 < len(linhas):
            nome_candidato = linhas[i + 1].strip()
            # Remove matrícula se estiver no início
            nome_candidato = re.sub(r'^\d{7}\s*', '', nome_candidato)
            # Remove referência/data se estiver junto
            nome_candidato = re.sub(r'\s+PAGAMENTO\s+REFERENTE.*$', '', nome_candidato, flags=re.IGNORECASE)
            if len(nome_candidato) > 3 and not nome_candidato.isdigit():
                info['nome'] = nome_candidato
                break
    
    # ============================================================
    # EXTRAÇÃO DE VALORES FINANCEIROS
    # ============================================================
    
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        
        # Busca "PROVENTOS" (total)
        if 'PROVENTOS' in linha_norm and 'DESCONTOS' not in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                info['vencimentos_total'] = float(valores[-1].replace('.', '').replace(',', '.'))
        
        # Busca "DESCONTOS" (total)
        if 'DESCONTOS' in linha_norm and 'PROVENTOS' not in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                info['descontos_total'] = float(valores[-1].replace('.', '').replace(',', '.'))
        
        # Busca "LIQUIDO"
        if 'LIQUIDO' in linha_norm or 'LÍQUIDO' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                for valor in reversed(valores):
                    valor_float = float(valor.replace('.', '').replace(',', '.'))
                    if valor_float > 0:
                        info['liquido'] = valor_float
                        break
    
    # Calcular líquido se ainda não foi encontrado
    if info['liquido'] == 0.0 and info['vencimentos_total'] > 0:
        info['liquido'] = info['vencimentos_total'] - info['descontos_total']
    
    return info


def extrair_salario_bruto_lago_verde(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque de LAGO VERDE
    Busca por "SALARIO BASE" (código 1)
    """
    linhas = texto.split('\n')
    
    # Prioridade 1: Buscar "SALARIO BASE" com código 1
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if re.match(r'^\s*1\s+SALARIO BASE', linha_norm) or 'SALARIO BASE' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    return 0.0


def extrair_vencimentos_fixos_lago_verde(texto: str) -> Dict:
    """
    Extrai vencimentos de LAGO VERDE da coluna de Proventos
    
    Conforme especificações de Lago Verde:
    - SOMA DOS PROVENTOS DE NATUREZA PERMANENTE OU FIXAS
    - Códigos específicos conforme planilha
    
    Estrutura: CÓD. | DESCRIÇÃO | REF. | PROVENTOS | DESCONTOS
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'gratificacao_graduacao': 0.0,
        'quinquenio': 0.0,
        'adicional_noturno': 0.0,
        'adicional_insalubridade': 0.0,
        'gam': 0.0,
        'gratificacao_incentivo': 0.0,
        'salario_piso_enfermagem': 0.0,
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # SALÁRIO BASE (código 1)
        if re.match(r'^\s*1\s+SALARIO BASE', linha_norm) or (re.match(r'^\s*1\s+', linha_norm) and 'SALARIO BASE' in linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['vencimento_base'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # GRATIFIC. P/ GRADUAÇÃO (códigos 201, 202)
        if ('201' in linha_norm or '202' in linha_norm) and 'GRATIF' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['gratificacao_graduacao'] += valor
                vencimentos_fixos['total'] += valor
            continue

        # QUINQUÊNIO (código 204)
        if '204' in linha_norm or 'QUINQUENIO' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['quinquenio'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # ADICIONAL NOTURNO (código 208)
        if '208' in linha_norm or 'ADICIONAL NOTURNO' in linha_norm or 'AD. NOTURNO' in linha_norm or 'ADIC. NOTURNO' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['adicional_noturno'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # ADICIONAL INSALUBRIDADE (código 233)
        if '233' in linha_norm or 'ADICIONAL INSALUBRIDADE' in linha_norm or 'INSALUBRIDADE' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['adicional_insalubridade'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # GAM (código 278)
        if '278' in linha_norm or (re.match(r'^\s*278\s+', linha_norm) and 'GAM' in linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['gam'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # GRAT.INCENTIVO P/ DESEMPENHO 10% (código 279)
        if '279' in linha_norm or ('GRAT' in linha_norm and 'INCENTIVO' in linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['gratificacao_incentivo'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # SALÁRIO BASE PISO ENFERMAGEM (código 285)
        if '285' in linha_norm or ('SALARIO' in linha_norm and 'PISO' in linha_norm and 'ENFERMAGEM' in linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['salario_piso_enfermagem'] = valor
                vencimentos_fixos['total'] += valor
            continue

    return vencimentos_fixos


# ============================================================================
# FUNÇÕES ESPECÍFICAS POR PREFEITURA - UBERABA
# ============================================================================

def extrair_informacoes_uberaba(texto: str) -> Dict:
    """
    Extrai informações específicas de Uberaba
    Estrutura: Matrícula / Nome / Banco / Agência / Conta / Proventos / Descontos
    """
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
    }
    
    linhas = texto.split('\n')
    
    # ============================================================
    # EXTRAÇÃO DE MATRÍCULA
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        if 'MATRICULA' in linha_norm:
            # Tenta extrair da mesma linha
            match = re.search(r'(\d{5,7}(?:-\d)?)', linha)
            if match:
                info['matricula'] = match.group(1)
                break
            # Tenta próxima linha
            elif i + 1 < len(linhas):
                match = re.search(r'^(\d{5,7}(?:-\d)?)', linhas[i + 1].strip())
                if match:
                    info['matricula'] = match.group(1)
                    break
    
    # ============================================================
    # EXTRAÇÃO DE NOME
    # ============================================================
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        if 'NOME' in linha_norm and i + 1 < len(linhas):
            nome_candidato = linhas[i + 1].strip()
            # Remove matrícula se estiver no início
            nome_candidato = re.sub(r'^\d{5,7}(?:-\d)?\s*', '', nome_candidato)
            # Remove referência/data se estiver junto
            nome_candidato = re.sub(r'\s+\d{2}/\d{4}.*$', '', nome_candidato)
            if len(nome_candidato) > 3 and not nome_candidato.isdigit():
                info['nome'] = nome_candidato
                break
    
    # ============================================================
    # EXTRAÇÃO DE VALORES FINANCEIROS
    # ============================================================
    
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        
        # Busca "Total de proventos"
        if 'TOTAL DE PROVENTOS' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                info['vencimentos_total'] = float(valores[-1].replace('.', '').replace(',', '.'))
        
        # Busca "Total de descontos"
        if 'TOTAL DE DESCONTOS' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                info['descontos_total'] = float(valores[-1].replace('.', '').replace(',', '.'))
        
        # Busca "Valor liquido" - CORRIGIDO
        if 'VALOR LIQUIDO' in linha_norm or 'VALOR LÍQUIDO' in linha_norm:
            # Primeiro tenta na mesma linha
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                # Pega o último valor (ignora o 0,00)
                for valor in reversed(valores):
                    valor_float = float(valor.replace('.', '').replace(',', '.'))
                    if valor_float > 0:
                        info['liquido'] = valor_float
                        break
            
            # Se não encontrou ou valor é 0, busca na próxima linha
            if info['liquido'] == 0.0 and i + 1 < len(linhas):
                proxima_linha = linhas[i + 1]
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', proxima_linha)
                if valores:
                    # Pega o primeiro valor significativo
                    for valor in valores:
                        valor_float = float(valor.replace('.', '').replace(',', '.'))
                        if valor_float > 0:
                            info['liquido'] = valor_float
                            break
    
    # Estratégia alternativa: buscar linha que contém apenas um valor após "Valor líquido"
    if info['liquido'] == 0.0:
        for i, linha in enumerate(linhas):
            # Busca linha que tem apenas um número (o valor líquido)
            if i > 0:
                linha_anterior = normalizar_texto(linhas[i - 1])
                if 'VALOR LIQUIDO' in linha_anterior or 'VALOR LÍQUIDO' in linha_anterior:
                    # Esta linha deve ter o valor líquido
                    valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
                    if valores:
                        for valor in valores:
                            valor_float = float(valor.replace('.', '').replace(',', '.'))
                            if valor_float > 0:
                                info['liquido'] = valor_float
                                break
                    if info['liquido'] > 0:
                        break
    
    # Calcular líquido se ainda não foi encontrado
    if info['liquido'] == 0.0 and info['vencimentos_total'] > 0:
        info['liquido'] = info['vencimentos_total'] - info['descontos_total']
    
    return info


def extrair_salario_bruto_uberaba(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque de UBERABA
    Busca por "VENCIMENTO" (código 1-001)
    """
    linhas = texto.split('\n')
    
    # Prioridade 1: Buscar "VENCIMENTO" com código 1-001
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if re.match(r'^\s*1-001\s+VENCIMENTO', linha_norm) or 'VENCIMENTO' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    return 0.0


def extrair_vencimentos_fixos_uberaba(texto: str) -> Dict:
    """
    Extrai vencimentos de UBERABA da coluna de Proventos
    Estrutura: Código | Descrição | Quantidade | Proventos | Descontos
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'adicional_tempo_servico': 0.0,
        'gratificacao': 0.0,
        'hora_ativ_extra_classe': 0.0,
        'aula_suplementar': 0.0,
        'vale_alimentacao': 0.0,
        'sexta_parte': 0.0,
        'horas_extras': 0.0,
        'insalubridade': 0.0,
        'adicional_noturno': 0.0,
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # VENCIMENTO (código 1-001)
        if re.match(r'^\s*1-001\s+VENCIMENTO', linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['vencimento_base'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # ADICIONAL NOTURNO (código 1-032)
        if 'AD. NOTURNO' in linha_norm or 'ADICIONAL NOTURNO' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['adicional_noturno'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # GRATIFICAÇÃO
        if 'GRAT' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['gratificacao'] += valor
                vencimentos_fixos['total'] += valor
            continue

        # INSALUBRIDADE
        if 'INSALUBR' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['insalubridade'] = valor
                vencimentos_fixos['total'] += valor
            continue

    return vencimentos_fixos


# ============================================================================
# FUNÇÕES ESPECÍFICAS POR PREFEITURA - BAURU
# ============================================================================

def extrair_informacoes_bauru(texto: str) -> Dict:
    """
    Extrai informações específicas de Bauru
    Estrutura: Matrícula / Nome / CPF / Vencimentos / Descontos / Líquido
    """
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
    }
    
    linhas = texto.split('\n')
    
    # ============================================================
    # EXTRAÇÃO DE MATRÍCULA
    # ============================================================
    # Buscar linha que contém "Matricula" seguida do número
    for i, linha in enumerate(linhas[:50]):
        linha_norm = normalizar_texto(linha)
        
        # Padrão: "Matricula 30261" ou "Matricula: 30261"
        if 'MATRICULA' in linha_norm:
            # Tenta extrair da mesma linha
            match = re.search(r'MATRICULA\s*:?\s*(\d{4,6})', linha_norm)
            if match:
                info['matricula'] = match.group(1)
                break
            # Tenta próxima linha
            elif i + 1 < len(linhas):
                match = re.search(r'^(\d{4,6})', linhas[i + 1].strip())
                if match:
                    info['matricula'] = match.group(1)
                    break
    
    # Estratégia alternativa: buscar padrão "número Nome"
    if not info['matricula']:
        for linha in linhas[:30]:
            # Procura por linha começando com número de 4-6 dígitos seguido de nome
            match = re.search(r'^(\d{4,6})\s+([A-Z][A-Z\s]+)', linha)
            if match and len(match.group(2).split()) >= 2:
                info['matricula'] = match.group(1)
                info['nome'] = match.group(2).strip()
                break
    
    # ============================================================
    # EXTRAÇÃO DE NOME
    # ============================================================
    if not info['nome']:
        for i, linha in enumerate(linhas[:50]):
            linha_norm = normalizar_texto(linha)
            
            if 'NOME DO FUNCIONARIO' in linha_norm or 'NOME FUNCIONARIO' in linha_norm:
                # Tenta extrair da mesma linha após o rótulo
                match = re.search(r'(?:NOME\s+DO\s+)?FUNCIONARIO\s*:?\s*([A-Z][A-Z\s]+?)(?:\s+ADMISSAO|\s+CPF|\s+CONTA|$)', linha, re.IGNORECASE)
                if match:
                    nome_candidato = match.group(1).strip()
                    # Remove matrícula se estiver no início
                    nome_candidato = re.sub(r'^\d{4,6}\s*', '', nome_candidato)
                    if len(nome_candidato) > 3:
                        info['nome'] = nome_candidato
                        break
                
                # Tenta próxima linha
                if not info['nome'] and i + 1 < len(linhas):
                    nome_candidato = linhas[i + 1].strip()
                    # Remove matrícula se estiver no início
                    nome_candidato = re.sub(r'^\d{4,6}\s*', '', nome_candidato)
                    # Remove CPF se estiver junto
                    nome_candidato = re.sub(r'\s*\d{3}\.\d{3}\.\d{3}-\d{2}.*$', '', nome_candidato)
                    if len(nome_candidato) > 3 and not nome_candidato.isdigit():
                        info['nome'] = nome_candidato
                        break
    
    # ============================================================
    # EXTRAÇÃO DE VALORES FINANCEIROS
    # ============================================================
    
    # Buscar em tabela estruturada: "Data de Crédito | Total Vencimentos | Total Descontos | Valor Líquido"
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        
        # Procura pela linha de cabeçalho
        if 'DATA DE CREDITO' in linha_norm and 'TOTAL VENCIMENTOS' in linha_norm:
            # Próxima linha contém os valores
            if i + 1 < len(linhas):
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linhas[i + 1])
                if len(valores) >= 3:
                    info['vencimentos_total'] = float(valores[0].replace('.', '').replace(',', '.'))
                    info['descontos_total'] = float(valores[1].replace('.', '').replace(',', '.'))
                    info['liquido'] = float(valores[2].replace('.', '').replace(',', '.'))
                    break
        
        # Alternativa: buscar individualmente
        if not info['vencimentos_total'] and 'TOTAL VENCIMENTOS' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                info['vencimentos_total'] = float(valores[-1].replace('.', '').replace(',', '.'))
        
        if not info['descontos_total'] and 'TOTAL DESCONTOS' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                info['descontos_total'] = float(valores[-1].replace('.', '').replace(',', '.'))
        
        if not info['liquido'] and ('VALOR LIQUIDO' in linha_norm or 'VALOR LÍQUIDO' in linha_norm):
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                info['liquido'] = float(valores[-1].replace('.', '').replace(',', '.'))
    
    # Estratégia final: buscar padrão "Salário Referência | Base Previdência | Base IRRF | Base FGTS | Valor FGTS"
    # e logo abaixo os valores, depois vem os totais
    if not info['liquido']:
        for i, linha in enumerate(linhas):
            linha_norm = normalizar_texto(linha)
            if 'VALOR LIQUIDO' in linha_norm and 'BASE PREVIDENCIA' in linha_norm:
                # Procura nas próximas 5 linhas por 3 valores consecutivos
                for j in range(i + 1, min(i + 6, len(linhas))):
                    valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linhas[j])
                    if len(valores) >= 3:
                        info['vencimentos_total'] = float(valores[0].replace('.', '').replace(',', '.'))
                        info['descontos_total'] = float(valores[1].replace('.', '').replace(',', '.'))
                        info['liquido'] = float(valores[2].replace('.', '').replace(',', '.'))
                        break
                if info['liquido'] > 0:
                    break
    
    # Calcular líquido se não foi encontrado mas temos vencimentos e descontos
    if info['liquido'] == 0.0 and info['vencimentos_total'] > 0 and info['descontos_total'] > 0:
        info['liquido'] = info['vencimentos_total'] - info['descontos_total']
    
    return info

def extrair_salario_bruto_bauru(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque de BAURU.
    Usa extrair_valores_bauru (último valor) pois o campo Qtde.
    (ex: 30,000) confunde o extrator genérico.
    """
    linhas = texto.split('\n')

    # Prioridade 1: linha com código + SALARIO (ex: "1 SALARIO 30,000 1.755,09")
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if re.match(r'^\s*\d+\s+SALARIO\s+', linha_norm):
            valor = extrair_valores_bauru(linha)
            if valor > 0:
                return valor

    # Prioridade 2: qualquer linha com SALARIO sem ser desconto
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'SALARIO' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_bauru(linha)
            if valor > 0:
                return valor

    return 0.0

def extrair_vencimentos_fixos_bauru(texto: str) -> Dict:
    """
    Extrai vencimentos de BAURU da coluna de VENCIMENTOS.
    Usa extrair_valores_bauru (último valor) pois o campo Qtde.
    (ex: 30,000) confunde o extrator genérico.

    Proventos permanentes (base de cálculo):
    SALÁRIO BASE, BIENIO, SEXTA PARTE, VANT PESS VL,
    VANT PE L25/17, ATIV TRAB PEDAG
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'adicional_tempo_servico': 0.0,
        'sexta_parte': 0.0,
        'vantagens_pessoais': 0.0,
        'ativ_trab_pedag': 0.0,
        'horas_extras': 0.0,
        'insalubridade': 0.0,
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # SALÁRIO BASE (código 1)
        if re.match(r'^\s*\d+\s+SALARIO\s+', linha_norm):
            valor = extrair_valores_bauru(linha)
            if valor > 0:
                vencimentos_fixos['vencimento_base'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # BIENIO / TRIÊNIO / QUINQUÊNIO
        if 'BIENIO' in linha_norm or 'TRIENIO' in linha_norm or 'QUINQUENIO' in linha_norm:
            valor = extrair_valores_bauru(linha)
            if valor > 0:
                vencimentos_fixos['adicional_tempo_servico'] += valor
                vencimentos_fixos['total'] += valor
            continue

        # SEXTA PARTE
        if 'SEXTA PARTE' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_bauru(linha)
            if valor > 0:
                vencimentos_fixos['sexta_parte'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # VANT PESS VL / VANT PE L25/17 / VANTAG PESSOAL
        if ('VANT PESS' in linha_norm or 'VANT PE' in linha_norm or
                'VANTAG PESSOAL' in linha_norm or 'VANTAG PESS' in linha_norm) and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_bauru(linha)
            if valor > 0:
                vencimentos_fixos['vantagens_pessoais'] += valor
                vencimentos_fixos['total'] += valor
            continue

        # ATIV TRAB PEDAG
        if ('ATIV TRAB' in linha_norm or 'ATIVIDADE TRAB' in linha_norm or
                'ATIV. TRAB' in linha_norm) and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_bauru(linha)
            if valor > 0:
                vencimentos_fixos['ativ_trab_pedag'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # INSALUBRIDADE (captura para referência, fora da spec de Bauru)
        if 'INSALUBRIDADE' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_bauru(linha)
            if valor > 0:
                vencimentos_fixos['insalubridade'] = valor
            continue

        # ABONO (NÃO é provento permanente — NÃO soma no total)
        if 'ABONO' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_bauru(linha)
            if valor > 0:
                vencimentos_fixos['outros_fixos'].append({'descricao': 'ABONO', 'valor': valor})
            continue

    return vencimentos_fixos


# ============================================================================
# FUNÇÕES ESPECÍFICAS POR PREFEITURA - HORTOLÂNDIA
# ============================================================================

def extrair_informacoes_hortolandia(texto: str) -> Dict:
    """
    Extrai informações específicas de Hortolândia
    Estrutura: Matrícula / Nome / Proventos / Descontos / Líquido
    """
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
    }
    
    linhas = texto.split('\n')
    
    # Concatenar primeiras 100 linhas para busca no cabeçalho
    header_text = " ".join(linhas[:100])
    header_norm = normalizar_texto(header_text)
    
    # ============================================================
    # EXTRAÇÃO DE MATRÍCULA
    # ============================================================
    
    # Estratégia 1: Buscar "Matricula:" seguido de número
    match_matricula = re.search(r'MATRICULA\s*:?\s*(\d{7,9})', header_norm)
    if match_matricula:
        info['matricula'] = match_matricula.group(1)
    
    # Estratégia 2: Buscar em linhas individuais
    if not info['matricula']:
        for i, linha in enumerate(linhas[:50]):
            linha_norm = normalizar_texto(linha)
            if 'MATRICULA' in linha_norm:
                # Tenta extrair da mesma linha
                match = re.search(r'(\d{7,9})', linha)
                if match:
                    info['matricula'] = match.group(1)
                    break
                # Tenta próxima linha
                elif i + 1 < len(linhas):
                    match = re.search(r'(\d{7,9})', linhas[i + 1])
                    if match:
                        info['matricula'] = match.group(1)
                        break
    
    # ============================================================
    # EXTRAÇÃO DE NOME
    # ============================================================
    
    def _clean_line(s: str) -> str:
        if s is None:
            return ""
        s = s.replace('\ufeff', '').replace('\u200b', '').replace('\xa0', ' ')
        s = unicodedata.normalize('NFKC', s)
        s = _re.sub(r'\s+', ' ', s).strip()
        return s

    def _strip_after_labels(s: str) -> str:
        if not s:
            return ""
        s = _clean_line(s)
        s = _re.split(
            r'\b(?:MATR[IÍ]CULA|V[IÍ]NCULO|JORNADA|SITUA[ÇC][ÃA]O|LOTA[ÇC][ÃA]O|DATA\s+DE\s+ADMISS[ÃA]O|DATA|CARGO|CPF|PAGAMENTO|C[ÓO]DIGO)\b\s*:?',
            s,
            maxsplit=1,
            flags=_re.IGNORECASE,
        )[0]
        return _clean_line(s)

    # STOP WORDS que indicam NÃO-NOME (inclui 'data' e variações)
    _STOP_WORDS = {
        'municipio','município','demonstrativo','demonstrativo de pagamento',
        'folha','folha mensal','mês','mes','pagina','página','hora','pagamento',
        'banco','agência','agencia','conta','referência','referencia','vencimento',
        'vencimentos','descontos','proventos','valor','total','base','liquido',
        'lotação','lotacao','situação','situacao','matricula','matrícula','vínculo',
        'vinculo','cargo','cpf','usuário','usuario','referencia','lotaçao','data',
        'admiss','admissão','admissao','dependentes'
    }

    def _contains_stopword(s: str) -> bool:
        low = s.lower()
        for w in _STOP_WORDS:
            if _re.search(r'\b' + _re.escape(w) + r'\b', low):
                return True
        return False

    def _is_valid_name(s: str) -> bool:
        if not s:
            return False
        s = s.strip()
        # remove possíveis ":" ou "-" no final (ex: "Data de Admissão:")
        s = _re.sub(r'[:\-\–\—\–\s]+$', '', s).strip()
        # rejeita se tiver dígitos ou R$
        if _re.search(r'\d', s) or 'r$' in s.lower():
            return False
        # rejeita se conter qualquer stopword (inclui 'data' e 'admiss')
        if _contains_stopword(s):
            return False
        parts = s.split()
        # precisa ter pelo menos 2 palavras
        if len(parts) < 2:
            return False
        # pelo menos uma palavra com mais de 2 letras (evita "de", "do", "da" sozinhas)
        if not any(len(p) > 2 for p in parts):
            return False
        # comprimento médio das palavras razoável
        avg_len = sum(len(p) for p in parts) / len(parts)
        if avg_len < 2.5:
            return False
        # proporção de letras (evita linhas com muitos símbolos)
        letters = _re.sub(r'[^A-Za-zÀ-ÖØ-öø-ÿ]', '', s)
        if len(letters) / max(1, len(s)) < 0.55:
            return False
        # deve conter pelo menos uma vogal (evita siglas)
        if not _re.search(r'[aeiouáàâãéêíóôõúü]', s.lower()):
            return False
        return True

    def _normalize_name_candidate(s: str) -> str:
        if not s:
            return ""
        s = _clean_line(s)
        s = _strip_after_labels(s)
        s = _re.sub(r'[^A-Za-zÀ-ÖØ-öø-ÿ\s]', ' ', s)
        s = _re.sub(r'\s+', ' ', s).strip()
        return s

    # ===========================
    # EXTRAÇÃO DE NOME 
    # ===========================
    info['nome'] = ''

    for i, linha in enumerate(linhas[:200]):  # limita pro processamento
        raw = linha or ""
        ln = _clean_line(raw).lower()
        # detecta ocorrências do rótulo "nome" (cobre "Nome:", "NOME", "Nome :")
        if _re.search(r'\bnome\b', ln, flags=_re.IGNORECASE):
            # 1) tenta capturar conteúdo na mesma linha depois do token "nome"
            m = _re.search(r'\bnome\b[:\s\-–—]*(.+)$', raw, flags=_re.IGNORECASE)
            if m:
                candidate_same = _normalize_name_candidate(m.group(1))
                if candidate_same and _is_valid_name(candidate_same):
                    info['nome'] = candidate_same
                    break

            # 2) se não tiver na mesma linha, pegar a próxima linha não vazia válida
            j = i + 1
            while j < len(linhas):
                cand_raw = linhas[j]
                cand = _clean_line(cand_raw)
                if cand:
                    cand_stripped = _normalize_name_candidate(cand)
                    if cand_stripped and _is_valid_name(cand_stripped):
                        info['nome'] = cand_stripped
                        break

                    # rejeitar logo se contiver stopwords (ex: "Data de Admissão:")
                    if _contains_stopword(cand):
                        # pula essa e tenta até 2 linhas seguintes (alguns PDFs colocam rótulos entre)
                        # tenta pular até 2 linhas (configurável)
                        k = 1
                        found = False
                        while k <= 2 and j + k < len(linhas):
                            cand2 = _clean_line(linhas[j + k])
                            if cand2 and not _contains_stopword(cand2):
                                if _is_valid_name(cand2):
                                    info['nome'] = cand2
                                    found = True
                                break
                            k += 1
                        if found:
                            break
                        # se não encontrou nome nas próximas 2 linhas, não considera esta ocorrência de 'Nome'
                        break
                    # se não tiver stopwords, valida normal
                    if _is_valid_name(cand):
                        info['nome'] = cand
                    # independente de aceitar ou não, pára a busca após primeira linha útil
                    break
                j += 1

        if info['nome']:
            break

    if not info['nome']:
        header_raw = _clean_line(" ".join(linhas[:250]))
        nome_label = r'(?<!\w)N\s*O\s*M\s*E(?!\w)'
        matricula_label = r'(?<!\w)M\s*A\s*T\s*R\s*[IÍ]\s*C\s*U\s*L\s*A(?!\w)'

        patterns = [
            # Caso padrão: "Nome: <valor>" (mesmo se vier com outros rótulos em seguida)
            rf'{nome_label}\s*:?(.*?)(?=\s+\b(?:MATR[IÍ]CULA|{matricula_label}|V[IÍ]NCULO|JORNADA|SITUA[ÇC][ÃA]O|LOTA[ÇC][ÃA]O|DATA\s+DE\s+ADMISS[ÃA]O|DATA|CARGO|CPF|PAGAMENTO|C[ÓO]DIGO)\b\s*:|$)',
            # Matrícula e Nome na mesma linha/cabeçalho
            rf'(?:\bMATR[IÍ]CULA\b|{matricula_label})\s*:?[\s\-–—]*\d{{6,10}}\s+(?:{nome_label})\s*:?(.*?)(?=\s+\b(?:V[IÍ]NCULO|JORNADA|SITUA[ÇC][ÃA]O|LOTA[ÇC][ÃA]O|DATA\s+DE\s+ADMISS[ÃA]O|DATA|CARGO|CPF|PAGAMENTO|C[ÓO]DIGO)\b\s*:|$)',
            # Alguns PDFs perdem o rótulo "Nome" e deixam o nome logo após a matrícula
            rf'(?:\bMATR[IÍ]CULA\b|{matricula_label})\s*:?[\s\-–—]*\d{{6,10}}\s+(.+?)(?=\s+\b(?:V[IÍ]NCULO|JORNADA|SITUA[ÇC][ÃA]O|LOTA[ÇC][ÃA]O|DATA\s+DE\s+ADMISS[ÃA]O|DATA|CARGO|CPF|PAGAMENTO|C[ÓO]DIGO)\b\s*:|$)',
        ]

        for pat in patterns:
            m = _re.search(pat, header_raw, flags=_re.IGNORECASE)
            if not m:
                continue
            candidate = _normalize_name_candidate(m.group(1))
            if candidate and _is_valid_name(candidate):
                info['nome'] = candidate
                break
    
    # ============================================================
    # EXTRAÇÃO DE VALORES FINANCEIROS
    # ============================================================
    
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        
        # Busca por "Total de Proventos:"
        if 'TOTAL DE PROVENTOS' in linha_norm or 'TOTAL PROVENTOS' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                valor_str = valores[-1].replace('.', '').replace(',', '.')
                info['vencimentos_total'] = float(valor_str)
        
        # Busca por "Descontos:" ou "Total de Descontos"
        if ('DESCONTOS' in linha_norm or 'TOTAL DE DESCONTOS' in linha_norm) and 'PROVENTOS' not in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                valor_str = valores[-1].replace('.', '').replace(',', '.')
                info['descontos_total'] = float(valor_str)
        
        # Busca por "Valor Liquido:" ou "VALOR LIQUIDO"
        if 'VALOR LIQUIDO' in linha_norm or 'VALOR LÍQUIDO' in linha_norm or 'LIQUIDO' in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                valor_str = valores[-1].replace('.', '').replace(',', '.')
                info['liquido'] = float(valor_str)
    
    # ============================================================
    # ESTRATÉGIAS ALTERNATIVAS PARA LÍQUIDO
    # ============================================================
    
    # Estratégia 1: Buscar linha com "R$" após palavra "LIQUIDO"
    if info['liquido'] == 0.0:
        for i, linha in enumerate(linhas):
            if 'R$' in linha:
                linha_anterior = linhas[i-1] if i > 0 else ''
                if 'LIQUIDO' in normalizar_texto(linha_anterior) or 'LÍQUIDO' in normalizar_texto(linha_anterior):
                    valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
                    if valores:
                        valor_str = valores[-1].replace('.', '').replace(',', '.')
                        info['liquido'] = float(valor_str)
                        break
    
    # Estratégia 2: Calcular líquido se tiver proventos e descontos
    if info['liquido'] == 0.0 and info['vencimentos_total'] > 0 and info['descontos_total'] >= 0:
        info['liquido'] = info['vencimentos_total'] - info['descontos_total']
    
    return info

def extrair_salario_bruto_hortolandia(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque de HORTOLÂNDIA
    Busca por "VENCIMENTO" ou "VENC. COMISS." (código 1)
    """
    linhas = texto.split('\n')
    
    # Prioridade 1: Buscar "VENCIMENTO" ou "VENC. COMISS."
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if ('VENCIMENTO' in linha_norm or 'VENC. COMISS' in linha_norm or 'VENC COMISS' in linha_norm) and 'DESCONTO' not in linha_norm:
            # No holerite, o valor do vencimento aparece após a descrição
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    # Prioridade 2: Buscar linha com código "1" (primeira linha de proventos)
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        # Verifica se a linha começa com código numérico e contém "VENCIMENTO"
        if re.match(r'^\s*\d+\s+', linha) and 'VENCIMENTO' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    # Prioridade 3: Buscar qualquer "SALARIO" ou "REMUNERACAO"
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if ('SALARIO' in linha_norm or 'REMUNERACAO' in linha_norm) and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    return 0.0

def extrair_vencimentos_fixos_hortolandia(texto: str) -> Dict:
    """
    Extrai vencimentos de HORTOLÂNDIA da coluna de PROVENTOS
    Estrutura: Código | Descrição | Referência | Valor
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'adicional_tempo_servico': 0.0,
        'gratificacao': 0.0,
        'hora_ativ_extra_classe': 0.0,
        'aula_suplementar': 0.0,
        'vale_alimentacao': 0.0,
        'sexta_parte': 0.0,
        'horas_extras': 0.0,
        'insalubridade': 0.0,
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # VENCIMENTO BASE (código 1)
        if 'VENCIMENTO' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['vencimento_base'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # HORAS EXTRAS (código 4)
        if 'HORAS EXTRAS' in linha_norm or 'H EXTRAS' in linha_norm or 'H.EXTRAS' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['horas_extras'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # INSALUBRIDADE (código 38)
        if 'INSALUBRIDADE' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['insalubridade'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # ADICIONAL DE TEMPO
        if 'ADICIONAL' in linha_norm and 'TEMPO' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['adicional_tempo_servico'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # SEXTA PARTE
        if 'SEXTA PARTE' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['sexta_parte'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # GRATIFICAÇÃO
        if 'GRAT' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['gratificacao'] = valor
                vencimentos_fixos['total'] += valor
            continue

    return vencimentos_fixos


# ============================================================================
# FUNÇÕES ESPECÍFICAS POR PREFEITURA - EMBU DAS ARTES
# ============================================================================

def extrair_informacoes_embu(texto: str) -> Dict:
    """
    Extrai informações específicas de Embu das Artes
    Estrutura: Funcionário | Nome | CPF | Salário Base | Vencimentos | Descontos | Líquido
    """
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
    }
    
    linhas = texto.split('\n')
    
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        
        # Busca por "FUNCIONARIO" seguido de matrícula e nome
        if 'FUNCIONARIO' in linha_norm and i + 1 < len(linhas):
            # Próxima linha tem: "89036 MARCELO SOUZA DE AZEVEDO"
            proxima_linha = linhas[i + 1].strip()
            match = re.search(r'^(\d{4,6})\s+([A-ZÁÀÃÂÉÈÊÍÏÓÔÕÖÚÇÑ\s]+)', proxima_linha)
            if match:
                info['matricula'] = match.group(1)
                info['nome'] = match.group(2).strip()
        
        # Busca por "Vencimentos" e "Descontos" na linha de totais
        if 'VENCIMENTO BASE' in linha_norm and 'DESCONTOS' in linha_norm and 'LIQUIDO' in linha_norm:
            # Próxima linha tem os valores
            if i + 1 < len(linhas):
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linhas[i + 1])
                if len(valores) >= 3:
                    info['vencimentos_total'] = float(valores[0].replace('.', '').replace(',', '.'))
                    info['descontos_total'] = float(valores[1].replace('.', '').replace(',', '.'))
                    info['liquido'] = float(valores[2].replace('.', '').replace(',', '.'))
        
        # Alternativa: Buscar "Líquido" diretamente
        if 'VENCIMENTO BASE' in linha_norm and not info['liquido']:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                info['liquido'] = float(valores[-1].replace('.', '').replace(',', '.'))
    
    return info

# FUNÇÕES ESPECÍFICAS POR PREFEITURA - IMPERATRIZ
# ============================================================================

def extrair_informacoes_imperatriz(texto: str) -> Dict:
    """
    Extrai informações específicas de Imperatriz - MA
    Separa corretamente matrícula, nome e salário líquido
    Estrutura: CÓDIGO | DESCRIÇÃO | REF. | VANTAGEM | DESCONTO
    """
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
    }
    
    linhas = texto.split('\n')

    header_norm = " ".join(
        ln for ln in (normalizar_texto(l).strip() for l in linhas[:80])
        if ln
    )

    match_nome = re.search(
        r'\bNOME\s*:\s*([A-Z\s]+?)\s*(?:MATRICULA|CPF|SEC\.|UNID\.|CARGO|DT\.|DR\.|VINC\.|PIS|$)',
        header_norm
    )
    if match_nome:
        info['nome'] = match_nome.group(1).strip()

    match_matricula = re.search(
        r'\bMATRICULA\s*:\s*([0-9]{4,9}(?:-[0-9]{1,3}){0,2})',
        header_norm
    )
    if match_matricula:
        info['matricula'] = match_matricula.group(1).strip()
    
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        
        # Busca por "NOME" - extrai a linha seguinte
        if not info['nome'] and 'NOME' in linha_norm and ':' in linha:
            # Nome vem após "Nome :"
            match = re.search(r'NOME\s*:\s*(.+?)(?:MATRICULA|$)', linha_norm)
            if match:
                info['nome'] = match.group(1).strip()
            elif i + 1 < len(linhas):
                for j in range(i + 1, min(i + 6, len(linhas))):
                    nome_linha = linhas[j].strip()
                    nome_linha_norm = normalizar_texto(nome_linha)
                    if not nome_linha_norm:
                        continue
                    if nome_linha_norm in {'CODIGO', 'CÓDIGO'} or 'CODIGO' in nome_linha_norm:
                        break
                    if 'MATRICULA' in nome_linha_norm or 'CPF' in nome_linha_norm:
                        break
                    match = re.search(r'([A-ZÁÀÃÂÉÈÊÍÏÓÔÕÖÚÇÑ\s]+)', nome_linha)
                    if match:
                        info['nome'] = match.group(1).strip()
                        break
        
        # Busca por "MATRICULA" - formato com hífens (ex: 85462-4-2)
        if not info['matricula'] and 'MATRICULA' in linha_norm:
            match = re.search(r'(\d{4,9}(?:-\d{1,3}){1,2})', linha)
            if match:
                info['matricula'] = match.group(1)
            else:
                # Tenta formato sem hífens
                match = re.search(r'(\d{5,8})', linha)
                if match:
                    info['matricula'] = match.group(1)
        
        # Busca por "VANTAGEM" (total de vencimentos)
        if 'VANTAGEM' in linha_norm and 'DESCONTO' in linha_norm:
            # Linha com cabeçalho, pula
            continue
        
        # Busca totais no rodapé
        if i > 0 and '|' not in linha and len(linhas[i-1]) > 50:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if len(valores) >= 2:
                # Primeiro valor é vantagem, segundo é desconto
                info['vencimentos_total'] = float(valores[0].replace('.', '').replace(',', '.'))
                info['descontos_total'] = float(valores[1].replace('.', '').replace(',', '.'))
    
    # Estratégia 1: Buscar "LIQUIDO" ou "Liquido :"
    if info['liquido'] == 0.0:
        for linha in linhas:
            linha_norm = normalizar_texto(linha)
            if 'LIQUIDO' in linha_norm or 'LÍQUIDO' in linha_norm:
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
                if valores:
                    valor_str = valores[-1].replace('.', '').replace(',', '.')
                    info['liquido'] = float(valor_str)
                    break
    
    # Estratégia 2: Calcular como Vencimentos - Descontos
    if info['liquido'] == 0.0 and info['vencimentos_total'] > 0:
        info['liquido'] = info['vencimentos_total'] - info['descontos_total']
    
    return info


def extrair_salario_bruto_embu(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque de EMBU DAS ARTES
    Busca por "SALARIO BASE" (código 228 no exemplo)
    """
    linhas = texto.split('\n')
    
    # Buscar "SALARIO BASE"
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'VENCIMENTO BASE' in linha_norm or 'Salário Base' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    # # Fallback: Buscar primeiro vencimento significativo
    # for linha in linhas:
    #     linha_norm = normalizar_texto(linha)
    #     if 'VENCIMENTO BASE' in linha_norm:
    #         valor = extrair_valores_vencimento(linha)
    #         if valor > 0:
    #             return valor
    
    return 0.0

def extrair_salario_bruto_imperatriz(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque de IMPERATRIZ
    Busca por "VENCIMENTO CARGO COMISSIONADO" ou "REPRESENTACAO" na coluna VANTAGEM
    """
    linhas = texto.split('\n')
    
    # Prioridade 1: Buscar "VENCIMENTO CARGO COMISSIONADO"
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'VENCIMENTO CARGO' in linha_norm or 'VENCIMENTO CARGO COMISSIONADO' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    # Prioridade 2: Buscar "REPRESENTACAO"
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'REPRESENTACAO' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    # Prioridade 3: Buscar qualquer "VENCIMENTO"
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'VENCIMENTO' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    return 0.0

def extrair_vencimentos_fixos_embu(texto: str) -> Dict:
    """
    Extrai vencimentos de EMBU DAS ARTES da coluna de VENCIMENTOS
    Estrutura: Código | Descrição | Parcela | Referência | Valor
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'adicional_tempo_servico': 0.0,
        'gratificacao': 0.0,
        'hora_ativ_extra_classe': 0.0,
        'aula_suplementar': 0.0,
        'vale_alimentacao': 0.0,
        'sexta_parte': 0.0,
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # SALARIO BASE
        if 'SALARIO BASE' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['vencimento_base'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # ADICIONAL DE TEMPO
        if 'ADICIONAL' in linha_norm and 'TEMPO' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['adicional_tempo_servico'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # GRATIFICAÇÃO
        if 'GRAT' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['gratificacao'] = valor
                vencimentos_fixos['total'] += valor
            continue

    return vencimentos_fixos



def extrair_vencimentos_fixos_imperatriz(texto: str) -> Dict:
    """
    Extrai vencimentos de IMPERATRIZ da coluna VANTAGEM
    Estrutura: CÓDIGO | DESCRIÇÃO | REF. | VANTAGEM | DESCONTO
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'adicional_tempo_servico': 0.0,
        'gratificacao': 0.0,
        'hora_ativ_extra_classe': 0.0,
        'aula_suplementar': 0.0,
        'vale_alimentacao': 0.0,
        'sexta_parte': 0.0,
        'representacao': 0.0,  # Específico de Imperatriz
        'abono': 0.0,  # Específico de Imperatriz
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # VENCIMENTO CARGO COMISSIONADO
        if 'VENCIMENTO CARGO' in linha_norm or 'VENCIMENTO CARGO COMISSIONADO' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['vencimento_base'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # REPRESENTACAO
        if 'REPRESENTACAO' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['representacao'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # ABONO COMPLEMENTAR
        if 'ABONO' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['abono'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # ADICIONAL DE TEMPO
        if 'ADICIONAL' in linha_norm and 'TEMPO' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['adicional_tempo_servico'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # GRATIFICAÇÃO
        if 'GRAT' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['gratificacao'] = valor
                vencimentos_fixos['total'] += valor
            continue

    return vencimentos_fixos

# ============================================================================
# FUNÇÕES ESPECÍFICAS POR PREFEITURA - POÁ
# ============================================================================

def extrair_salario_bruto_poa(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque de POÁ
    Busca por "Vencimentos Estatutarios" ou similar na coluna de vencimentos
    """
    linhas = texto.split('\n')
    
    # Prioridade 1: Buscar linha "Vencimentos Estatutarios"
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'VENCIMENTOS ESTATUTARIOS' in linha_norm or 'VENCIMENTO ESTATUTARIO' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    # Prioridade 2: Buscar "VENCIMENTO BASE" no cabeçalho
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        if 'VENCIMENTO BASE' in linha_norm:
            if i + 1 < len(linhas):
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}', linhas[i + 1])
                if valores:
                    valor_str = valores[0].replace('.', '').replace(',', '.')
                    return float(valor_str)
    
    # Prioridade 3: Buscar "SALARIO BASE" ou apenas "SALARIO"
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'SALARIO BASE' in linha_norm or (linha_norm.strip().startswith('SALARIO') and 'DESCONTO' not in linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    return 0.0

def extrair_vencimentos_fixos_poa(texto: str) -> Dict:
    """
    Extrai vencimentos de POÁ da coluna de VENCIMENTOS
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'adicional_tempo_servico': 0.0,
        'gratificacao': 0.0,
        'hora_ativ_extra_classe': 0.0,
        'aula_suplementar': 0.0,
        'vale_alimentacao': 0.0,
        'sexta_parte': 0.0,
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # Adicional de Tempo de Serviço
        if 'ADICIONAL TEMPO' in linha_norm or 'ADICIONAL TEMPO SERVICO' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['adicional_tempo_servico'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # Gratificação
        if any(p in linha_norm for p in ['GRAT', 'GRAT.EXERC', 'FUNCao INCORPORADA']):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['gratificacao'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # Hora Ativ. Extra Classe
        if any(p in linha_norm for p in ['HORA ATIV', 'HORA ATIV.EXTRA', 'HORA ATIV. EXTRA']):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['hora_ativ_extra_classe'] = valor
                vencimentos_fixos['total'] += valor
            continue

    return vencimentos_fixos

def calcular_margem_sorocaba(texto: str, salario_base: float, vencimentos_fixos: Dict, 
                              descontos_obrigatorios: Dict, cartoes_encontrados: Dict) -> Dict:
    """
    Calcula margem consignável para SOROCABA seguindo as regras da planilha
    
    Regras SOROCABA (conforme print):
    - Base de Cálculo: Soma dos proventos de natureza permanente ou fixas, deduzindo os consignados compulsórios
    - Descontos/Proventos considerados: VENCIMENTO, ADIC. TEMPO SERVIÇO, IRRF, PREVIDÊNCIA
    - Obs: Não considerar Vale Alimentação ou Ticket Refeição como base de cálculo
    
    Percentuais:
    - Empréstimo: 35%
    - Cartão Consignado: 5%
    - Cartão Benefício: 5%
    
    TODOS os cartões contam: nossos, terceiros, não comprados e desconhecidos
    """
    
    # Base de cálculo: Vencimentos permanentes - Descontos compulsórios
    # IMPORTANTE: NÃO incluir Vale Alimentação
    salario_bruto = salario_base
    
    # Adiciona apenas vencimentos permanentes (exclui vale alimentação)
    vencimentos_permanentes = 0.0
    if vencimentos_fixos.get('adicional_tempo_servico', 0) > 0:
        vencimentos_permanentes += vencimentos_fixos['adicional_tempo_servico']
    if vencimentos_fixos.get('gratificacao', 0) > 0:
        vencimentos_permanentes += vencimentos_fixos['gratificacao']
    if vencimentos_fixos.get('hora_ativ_extra_classe', 0) > 0:
        vencimentos_permanentes += vencimentos_fixos['hora_ativ_extra_classe']
    if vencimentos_fixos.get('sexta_parte', 0) > 0:
        vencimentos_permanentes += vencimentos_fixos['sexta_parte']
    # NÃO incluir vale_alimentacao
    
    total_descontos_obrigatorios = descontos_obrigatorios.get('total', 0.0)
    
    base_calculo = salario_bruto + vencimentos_permanentes - total_descontos_obrigatorios
    
    # Percentuais de SOROCABA
    percentual_emprestimo = 0.35  # 35%
    percentual_cartao_consig = 0.10  # 10%
    percentual_cartao_beneficio = 0.05  # 5%
    
    # Extrai empréstimos e cartões do holerite
    linhas = texto.split('\n')
    emprestimos_atuais = 0.0
    
    # Separação de cartões por categoria
    cartoes_nossos = 0.0
    cartoes_terceiros = 0.0
    cartoes_nao_comprados = 0.0
    cartoes_desconhecidos = 0.0
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        # UASPREV conta como empréstimo
        if 'UASPREV' in linha_norm or 'Emprestimo STARCARD ANTICIPAY' in linha_norm:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
            continue
        
        # Verifica se é cartão
        eh_cartao = any(kw in linha_norm for kw in ['CARTAO', 'CRED ', 'CART.', 'CARTÃO'])
        
        if eh_cartao:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                # Classifica o cartão
                if any(produto in linha_norm for produto in ['STARCARD', 'ANTICIPAY', 'STARBANK', 'UASPREV']):
                    cartoes_nossos += valor
                elif any(cartao in linha_norm for cartao in CARTOES_NAO_COMPRADOS):
                    cartoes_nao_comprados += valor
                elif any(cartao in linha_norm for cartao in CARTOES_CONHECIDOS):
                    cartoes_terceiros += valor
                else:
                    cartoes_desconhecidos += valor
            continue
        
        # Empréstimos genéricos
        if any(termo in linha_norm for termo in ['EMPRESTIMO', 'CONSIGNADO', 'FINANCIAMENTO', 'EMPREST']):
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
    
    # Total de cartões
    total_cartoes = cartoes_nossos + cartoes_terceiros + cartoes_nao_comprados + cartoes_desconhecidos
    
    # Cálculo das margens
    margem_emprestimo_total = base_calculo * percentual_emprestimo
    margem_emprestimo_disponivel = margem_emprestimo_total - emprestimos_atuais
    
    # MARGEM DE CARTÃO CONSIGNADO (5%)
    margem_cartao_consig_total = base_calculo * percentual_cartao_consig
    margem_cartao_consig_disponivel = margem_cartao_consig_total - total_cartoes
    
    # MARGEM DE CARTÃO BENEFÍCIO (5%)
    margem_cartao_beneficio_total = base_calculo * percentual_cartao_beneficio
    margem_cartao_beneficio_disponivel = margem_cartao_beneficio_total - total_cartoes
    
    # Líquido recebido pelo cliente
    salario_bruto_total = salario_bruto + vencimentos_permanentes
    liquido_recebido = salario_bruto_total - total_descontos_obrigatorios - emprestimos_atuais - total_cartoes
    
    # Percentual de liquidez (mínimo 30%)
    percentual_liquidez = (liquido_recebido / salario_bruto_total * 100) if salario_bruto_total > 0 else 0
    
    # Validação de liquidez mínima
    aprovado_liquidez = percentual_liquidez >= 30.0
    
    return {
        'prefeitura': 'SOROCABA',
        'salario_bruto': salario_bruto_total,
        'base_calculo': base_calculo,
        'descontos_compulsorios': total_descontos_obrigatorios,
        'emprestimos_atuais': emprestimos_atuais,
        'cartoes_atuais': total_cartoes,
        
        # Detalhamento de cartões
        'cartoes_nossos': cartoes_nossos,
        'cartoes_terceiros': cartoes_terceiros,
        'cartoes_nao_comprados': cartoes_nao_comprados,
        'cartoes_desconhecidos': cartoes_desconhecidos,
        
        # Margens por tipo
        'emprestimo': {
            'percentual': percentual_emprestimo,
            'margem_total': margem_emprestimo_total,
            'comprometido': emprestimos_atuais,
            'disponivel': margem_emprestimo_disponivel
        },
        'cartao_consignado': {
            'percentual': percentual_cartao_consig,
            'margem_total': margem_cartao_consig_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_consig_disponivel
        },
        'cartao_beneficio': {
            'percentual': percentual_cartao_beneficio,
            'margem_total': margem_cartao_beneficio_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_beneficio_disponivel
        },
        
        # Liquidez
        'liquido_recebido': liquido_recebido,
        'percentual_liquidez': percentual_liquidez,
        'liquidez_minima': 30.0,
        'aprovado_liquidez': aprovado_liquidez,
        
        # Status geral
        'tem_margem_emprestimo': margem_emprestimo_disponivel > 0,
        'tem_margem_cartao': margem_cartao_consig_disponivel > 0 or margem_cartao_beneficio_disponivel > 0
    }

def calcular_margem_poa(texto: str, salario_base: float, vencimentos_fixos: Dict, 
                        descontos_obrigatorios: Dict, cartoes_encontrados: Dict) -> Dict:
    """
    Calcula margem consignável para POÁ seguindo as regras da planilha
    
    Regras POÁ (segunda linha da planilha dados.csv):
    - Empréstimo: 35%
    - Cartão Consignado: 15%
    - Cartão Benefício: 15%
    
    Fórmula: Base de Cálculo = Salário Bruto - Descontos Compulsórios
    
    TODOS os cartões contam: nossos, terceiros, não comprados e desconhecidos
    """
    
    # Base de cálculo: Vencimentos totais - Descontos obrigatórios
    salario_bruto = salario_base + vencimentos_fixos.get('total', 0.0)
    total_descontos_obrigatorios = descontos_obrigatorios.get('total', 0.0)
    
    base_calculo = salario_bruto - total_descontos_obrigatorios
    
    # Percentuais de POÁ (conforme planilha dados.csv - SEGUNDA LINHA)
    percentual_emprestimo = 0.35  # 35%
    percentual_cartao_consig = 0.15  # 15%
    percentual_cartao_beneficio = 0.15  # 15%
    
    # Extrai empréstimos e cartões do holerite
    linhas = texto.split('\n')
    emprestimos_atuais = 0.0
    
    # Separação de cartões por categoria (para detalhamento)
    cartoes_nossos = 0.0
    cartoes_terceiros = 0.0
    cartoes_nao_comprados = 0.0
    cartoes_desconhecidos = 0.0
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        # UASPREV conta como empréstimo
        if 'UASPREV' in linha_norm or 'Emprestimo STARCARD ANTICIPAY' in linha_norm:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
            continue
        
        # Verifica se é cartão (qualquer tipo)
        eh_cartao = any(kw in linha_norm for kw in ['CARTAO', 'CRED ', 'CART.'])
        
        if eh_cartao:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                # Classifica o cartão
                if any(produto in linha_norm for produto in ['STARCARD', 'ANTICIPAY', 'STARBANK']):
                    cartoes_nossos += valor
                elif any(cartao in linha_norm for cartao in CARTOES_NAO_COMPRADOS):
                    cartoes_nao_comprados += valor
                elif any(cartao in linha_norm for cartao in CARTOES_CONHECIDOS):
                    cartoes_terceiros += valor
                else:
                    # Cartão desconhecido (para estudar)
                    cartoes_desconhecidos += valor
            continue
        
        # Empréstimos genéricos (que não são cartões)
        if any(termo in linha_norm for termo in ['EMPRESTIMO', 'CONSIGNADO', 'FINANCIAMENTO', 'EMPREST']):
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
    
    # Total de cartões (TODOS contam: nossos + terceiros + não comprados + desconhecidos)
    total_cartoes = cartoes_nossos + cartoes_terceiros + cartoes_nao_comprados + cartoes_desconhecidos
    
    # Cálculo das margens
    margem_emprestimo_total = base_calculo * percentual_emprestimo
    margem_emprestimo_disponivel = margem_emprestimo_total - emprestimos_atuais
    
    # MARGEM DE CARTÃO CONSIGNADO (15%)
    margem_cartao_consig_total = base_calculo * percentual_cartao_consig
    margem_cartao_consig_disponivel = margem_cartao_consig_total - total_cartoes
    
    # MARGEM DE CARTÃO BENEFÍCIO (15%)
    margem_cartao_beneficio_total = base_calculo * percentual_cartao_beneficio
    # Cartão benefício compartilha o mesmo comprometimento (todos os cartões)
    margem_cartao_beneficio_disponivel = margem_cartao_beneficio_total - total_cartoes
    
    # Líquido recebido pelo cliente (conforme planilha)
    liquido_recebido = salario_bruto - total_descontos_obrigatorios - emprestimos_atuais - total_cartoes
    
    # Percentual de liquidez (mínimo 30% segundo planilha)
    percentual_liquidez = (liquido_recebido / salario_bruto * 100) if salario_bruto > 0 else 0
    
    # Validação de liquidez mínima
    aprovado_liquidez = percentual_liquidez >= 30.0
    
    return {
        'prefeitura': 'POA',
        'salario_bruto': salario_bruto,
        'base_calculo': base_calculo,
        'descontos_compulsorios': total_descontos_obrigatorios,
        'emprestimos_atuais': emprestimos_atuais,
        'cartoes_atuais': total_cartoes,
        
        # Detalhamento de cartões
        'cartoes_nossos': cartoes_nossos,
        'cartoes_terceiros': cartoes_terceiros,
        'cartoes_nao_comprados': cartoes_nao_comprados,
        'cartoes_desconhecidos': cartoes_desconhecidos,
        
        # Margens por tipo
        'emprestimo': {
            'percentual': percentual_emprestimo,
            'margem_total': margem_emprestimo_total,
            'comprometido': emprestimos_atuais,
            'disponivel': margem_emprestimo_disponivel
        },
        'cartao_consignado': {
            'percentual': percentual_cartao_consig,
            'margem_total': margem_cartao_consig_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_consig_disponivel
        },
        'cartao_beneficio': {
            'percentual': percentual_cartao_beneficio,
            'margem_total': margem_cartao_beneficio_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_beneficio_disponivel
        },
        
        # Liquidez
        'liquido_recebido': liquido_recebido,
        'percentual_liquidez': percentual_liquidez,
        'liquidez_minima': 30.0,
        'aprovado_liquidez': aprovado_liquidez,
        
        # Status geral
        'tem_margem_emprestimo': margem_emprestimo_disponivel > 0,
        'tem_margem_cartao': margem_cartao_consig_disponivel > 0 or margem_cartao_beneficio_disponivel > 0
    }

def calcular_margem_redencao(texto: str, salario_base: float, vencimentos_fixos: Dict, 
                            descontos_obrigatorios: Dict, cartoes_encontrados: Dict) -> Dict:
    """
    Calcula margem consignável para REDENÇÃO seguindo as regras especificadas
    
    Regras REDENÇÃO:
    - Base de Cálculo: Soma dos proventos de natureza permanente ou fixas, 
      deduzindo os consignados compulsórios
    - Proventos considerados: SALÁRIO + ADICIONAL TEMPO SERVIÇO + GRATIFICAÇÕES FIXAS
    - NÃO incluir: Horas extras (variável), Vale alimentação
    - Descontos compulsórios: INSS, IRRF, pensão alimentícia, etc.
    
    Percentuais estimados (confirmar com a prefeitura):
    - Empréstimo: 30%
    - Cartão Consignado: 5%
    - Cartão Benefício: 5%
    
    TODOS os cartões contam: nossos, terceiros, não comprados e desconhecidos
    """
    
    # Base de cálculo: Vencimentos permanentes/fixos - Descontos compulsórios
    # IMPORTANTE: NÃO incluir horas extras (variável) nem vale alimentação
    salario_bruto = salario_base
    
    # Adiciona apenas vencimentos permanentes/fixos
    vencimentos_permanentes = 0.0
    if vencimentos_fixos.get('adicional_tempo_servico', 0) > 0:
        vencimentos_permanentes += vencimentos_fixos['adicional_tempo_servico']
    if vencimentos_fixos.get('gratificacao', 0) > 0:
        vencimentos_permanentes += vencimentos_fixos['gratificacao']
    if vencimentos_fixos.get('sexta_parte', 0) > 0:
        vencimentos_permanentes += vencimentos_fixos['sexta_parte']
    if vencimentos_fixos.get('insalubridade', 0) > 0:
        vencimentos_permanentes += vencimentos_fixos['insalubridade']
    # NÃO incluir: horas_extras (variável), vale_alimentacao
    
    total_descontos_obrigatorios = descontos_obrigatorios.get('total', 0.0)
    
    base_calculo = salario_bruto + vencimentos_permanentes - total_descontos_obrigatorios
    
    # Percentuais de REDENÇÃO (ajustar se houver documentação oficial)
    percentual_emprestimo = 0.30  # 30%
    percentual_cartao_consig = 0.05  # 5%
    percentual_cartao_beneficio = 0.05  # 5%
    
    # Extrai empréstimos e cartões do holerite
    linhas = texto.split('\n')
    emprestimos_atuais = 0.0
    
    # Separação de cartões por categoria
    cartoes_nossos = 0.0
    cartoes_terceiros = 0.0
    cartoes_nao_comprados = 0.0
    cartoes_desconhecidos = 0.0
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        # Verifica se é cartão (qualquer tipo)
        eh_cartao = any(kw in linha_norm for kw in ['CARTAO', 'CRED ', 'CART.'])
        
        if eh_cartao:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                # Classifica o cartão
                if any(produto in linha_norm for produto in ['STARCARD', 'ANTICIPAY', 'STARBANK']):
                    cartoes_nossos += valor
                elif any(cartao in linha_norm for cartao in CARTOES_NAO_COMPRADOS):
                    cartoes_nao_comprados += valor
                elif any(cartao in linha_norm for cartao in CARTOES_CONHECIDOS):
                    cartoes_terceiros += valor
                else:
                    # Cartão desconhecido (para estudar)
                    cartoes_desconhecidos += valor
            continue
        
        # Empréstimos genéricos (que não são cartões)
        if any(termo in linha_norm for termo in ['EMPRESTIMO', 'CONSIGNADO', 'FINANCIAMENTO', 'EMPREST']):
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
    
    # Total de cartões (TODOS contam: nossos + terceiros + não comprados + desconhecidos)
    total_cartoes = cartoes_nossos + cartoes_terceiros + cartoes_nao_comprados + cartoes_desconhecidos
    
    # Cálculo das margens
    margem_emprestimo_total = base_calculo * percentual_emprestimo
    margem_emprestimo_disponivel = margem_emprestimo_total - emprestimos_atuais
    
    # MARGEM DE CARTÃO CONSIGNADO (5%)
    margem_cartao_consig_total = base_calculo * percentual_cartao_consig
    margem_cartao_consig_disponivel = margem_cartao_consig_total - total_cartoes
    
    # MARGEM DE CARTÃO BENEFÍCIO (5%)
    margem_cartao_beneficio_total = base_calculo * percentual_cartao_beneficio
    # Cartão benefício compartilha o mesmo comprometimento (todos os cartões)
    margem_cartao_beneficio_disponivel = margem_cartao_beneficio_total - total_cartoes
    
    # Líquido recebido pelo cliente
    liquido_recebido = salario_bruto + vencimentos_permanentes - total_descontos_obrigatorios - emprestimos_atuais - total_cartoes
    
    # Percentual de liquidez (mínimo 30%)
    percentual_liquidez = (liquido_recebido / (salario_bruto + vencimentos_permanentes) * 100) if (salario_bruto + vencimentos_permanentes) > 0 else 0
    
    # Validação de liquidez mínima
    aprovado_liquidez = percentual_liquidez >= 30.0
    
    return {
        'prefeitura': 'REDENCAO',
        'salario_bruto': salario_bruto + vencimentos_permanentes,
        'base_calculo': base_calculo,
        'descontos_compulsorios': total_descontos_obrigatorios,
        'emprestimos_atuais': emprestimos_atuais,
        'cartoes_atuais': total_cartoes,
        
        # Detalhamento de cartões
        'cartoes_nossos': cartoes_nossos,
        'cartoes_terceiros': cartoes_terceiros,
        'cartoes_nao_comprados': cartoes_nao_comprados,
        'cartoes_desconhecidos': cartoes_desconhecidos,
        
        # Margens por tipo
        'emprestimo': {
            'percentual': percentual_emprestimo,
            'margem_total': margem_emprestimo_total,
            'comprometido': emprestimos_atuais,
            'disponivel': margem_emprestimo_disponivel
        },
        'cartao_consignado': {
            'percentual': percentual_cartao_consig,
            'margem_total': margem_cartao_consig_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_consig_disponivel
        },
        'cartao_beneficio': {
            'percentual': percentual_cartao_beneficio,
            'margem_total': margem_cartao_beneficio_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_beneficio_disponivel
        },
        
        # Liquidez
        'liquido_recebido': liquido_recebido,
        'percentual_liquidez': percentual_liquidez,
        'liquidez_minima': 30.0,
        'aprovado_liquidez': aprovado_liquidez,
        
        # Status geral
        'tem_margem_emprestimo': margem_emprestimo_disponivel > 0,
        'tem_margem_cartao': margem_cartao_consig_disponivel > 0 or margem_cartao_beneficio_disponivel > 0
    }

def calcular_margem_cuiaba(texto: str, salario_base: float, vencimentos_fixos: Dict, 
                          descontos_obrigatorios: Dict, cartoes_encontrados: Dict) -> Dict:
    """
    Calcula margem consignável para CUIABÁ seguindo as regras especificadas
    
    Regras CUIABÁ (conforme legislação municipal):
    - Base de Cálculo: Remuneração líquida do servidor = soma de vencimentos com 
      os adicionais de caráter individual e demais vantagens permanentes, 
      subtraídas os descontos obrigatórios
    
    - NÃO INCLUIR (§3° - caráter eventual/indenizatório):
      I – diárias
      II – ajuda-de-custo
      III – indenização de despesa de transporte
      IV – salário-família
      V – auxílio-natalidade
      VI – auxílio-funeral
      VII – adicional de férias
      VIII – qualquer outro auxílio/adicional de caráter indenizatório
    
    - INCLUIR (proventos permanentes):
      * Subsídio/Vencimento base
      * Gratificações fixas
      * Insalubridade permanente
      * Adicional por tempo de serviço
    
    Percentuais estimados (confirmar com a prefeitura):
    - Empréstimo: 30%
    - Cartão Consignado: 5%
    - Cartão Benefício: 5%
    
    TODOS os cartões contam: nossos, terceiros, não comprados e desconhecidos
    """
    
    # Base de cálculo: Vencimentos permanentes - Descontos obrigatórios
    # IMPORTANTE: NÃO incluir diárias, auxílios indenizatórios, adicional de férias
    salario_bruto = salario_base
    
    # Adiciona apenas vencimentos permanentes (exclui indenizatórios/eventuais)
    vencimentos_permanentes = 0.0
    if vencimentos_fixos.get('adicional_tempo_servico', 0) > 0:
        vencimentos_permanentes += vencimentos_fixos['adicional_tempo_servico']
    if vencimentos_fixos.get('gratificacao', 0) > 0:
        vencimentos_permanentes += vencimentos_fixos['gratificacao']
    if vencimentos_fixos.get('grat_desempenho', 0) > 0:
        vencimentos_permanentes += vencimentos_fixos['grat_desempenho']
    if vencimentos_fixos.get('sexta_parte', 0) > 0:
        vencimentos_permanentes += vencimentos_fixos['sexta_parte']
    if vencimentos_fixos.get('insalubridade', 0) > 0:
        vencimentos_permanentes += vencimentos_fixos['insalubridade']
    # NÃO incluir: diárias, auxílios (natalidade, funeral, família), adicional de férias
    
    total_descontos_obrigatorios = descontos_obrigatorios.get('total', 0.0)
    
    base_calculo = salario_bruto + vencimentos_permanentes - total_descontos_obrigatorios
    
    # Percentuais de CUIABÁ (ajustar se houver documentação oficial)
    percentual_emprestimo = 0.30  # 30%
    percentual_cartao_consig = 0.05  # 5%
    percentual_cartao_beneficio = 0.05  # 5%
    
    # Extrai empréstimos e cartões do holerite
    linhas = texto.split('\n')
    emprestimos_atuais = 0.0
    
    # Separação de cartões por categoria
    cartoes_nossos = 0.0
    cartoes_terceiros = 0.0
    cartoes_nao_comprados = 0.0
    cartoes_desconhecidos = 0.0
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        # Verifica se é cartão (qualquer tipo)
        eh_cartao = any(kw in linha_norm for kw in ['CARTAO', 'CRED ', 'CART.', 'CREDCESTA'])
        
        if eh_cartao:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                # Classifica o cartão
                if any(produto in linha_norm for produto in ['STARCARD', 'ANTICIPAY', 'STARBANK']):
                    cartoes_nossos += valor
                elif any(cartao in linha_norm for cartao in CARTOES_NAO_COMPRADOS):
                    cartoes_nao_comprados += valor
                elif any(cartao in linha_norm for cartao in CARTOES_CONHECIDOS):
                    cartoes_terceiros += valor
                else:
                    # Cartão desconhecido (para estudar)
                    cartoes_desconhecidos += valor
            continue
        
        # Empréstimos genéricos (que não são cartões)
        # Incluir bancos: DAYCOVAL, Banco Industrial, Santander, Taormina, etc.
        if any(termo in linha_norm for termo in ['EMPRESTIMO', 'CONSIGNADO', 'FINANCIAMENTO', 'EMPREST',
                                                   'DAYCOVAL', 'BANCO INDUSTRIAL', 'SANTANDER', 'TAORMINA']):
            # Pular se já foi detectado como cartão
            if not eh_cartao:
                valor = extrair_valores_desconto(linha)
                if valor > 0:
                    emprestimos_atuais += valor
    
    # Total de cartões (TODOS contam: nossos + terceiros + não comprados + desconhecidos)
    total_cartoes = cartoes_nossos + cartoes_terceiros + cartoes_nao_comprados + cartoes_desconhecidos
    
    # Cálculo das margens
    margem_emprestimo_total = base_calculo * percentual_emprestimo
    margem_emprestimo_disponivel = margem_emprestimo_total - emprestimos_atuais
    
    # MARGEM DE CARTÃO CONSIGNADO (5%)
    margem_cartao_consig_total = base_calculo * percentual_cartao_consig
    margem_cartao_consig_disponivel = margem_cartao_consig_total - total_cartoes
    
    # MARGEM DE CARTÃO BENEFÍCIO (5%)
    margem_cartao_beneficio_total = base_calculo * percentual_cartao_beneficio
    # Cartão benefício compartilha o mesmo comprometimento (todos os cartões)
    margem_cartao_beneficio_disponivel = margem_cartao_beneficio_total - total_cartoes
    
    # Líquido recebido pelo cliente
    liquido_recebido = salario_bruto + vencimentos_permanentes - total_descontos_obrigatorios - emprestimos_atuais - total_cartoes
    
    # Percentual de liquidez (mínimo 30%)
    percentual_liquidez = (liquido_recebido / (salario_bruto + vencimentos_permanentes) * 100) if (salario_bruto + vencimentos_permanentes) > 0 else 0
    
    # Validação de liquidez mínima
    aprovado_liquidez = percentual_liquidez >= 30.0
    
    return {
        'prefeitura': 'CUIABA',
        'salario_bruto': salario_bruto + vencimentos_permanentes,
        'base_calculo': base_calculo,
        'descontos_compulsorios': total_descontos_obrigatorios,
        'emprestimos_atuais': emprestimos_atuais,
        'cartoes_atuais': total_cartoes,
        
        # Detalhamento de cartões
        'cartoes_nossos': cartoes_nossos,
        'cartoes_terceiros': cartoes_terceiros,
        'cartoes_nao_comprados': cartoes_nao_comprados,
        'cartoes_desconhecidos': cartoes_desconhecidos,
        
        # Margens por tipo
        'emprestimo': {
            'percentual': percentual_emprestimo,
            'margem_total': margem_emprestimo_total,
            'comprometido': emprestimos_atuais,
            'disponivel': margem_emprestimo_disponivel
        },
        'cartao_consignado': {
            'percentual': percentual_cartao_consig,
            'margem_total': margem_cartao_consig_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_consig_disponivel
        },
        'cartao_beneficio': {
            'percentual': percentual_cartao_beneficio,
            'margem_total': margem_cartao_beneficio_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_beneficio_disponivel
        },
        
        # Liquidez
        'liquido_recebido': liquido_recebido,
        'percentual_liquidez': percentual_liquidez,
        'liquidez_minima': 30.0,
        'aprovado_liquidez': aprovado_liquidez,
        
        # Status geral
        'tem_margem_emprestimo': margem_emprestimo_disponivel > 0,
        'tem_margem_cartao': margem_cartao_consig_disponivel > 0 or margem_cartao_beneficio_disponivel > 0
    }

def calcular_margem_vinhedo(texto: str, salario_base: float, vencimentos_fixos: Dict, 
                            descontos_obrigatorios: Dict, cartoes_encontrados: Dict) -> Dict:
    """
    Calcula margem consignável para VINHEDO seguindo as regras da especificação
    
    Regras VINHEDO:
    - Base de Cálculo: Totalidade dos vencimentos, proventos e pensões - Descontos compulsórios
    - Margem Total: 70% da base
    - Margem para Consignações Facultativas: 30% da base (empréstimos + cartões)
    
    Descontos Compulsórios:
    a) Previdência Social
    b) Pensões alimentícias
    c) IRPF
    d) Reposições e indenizações ao erário
    e) Imposto Sindical, Contribuições e Mensalidades Sindicais
    f) Vale Transporte
    g) Outros mandados judiciais ou por força de lei
    
    Percentuais (dentro do limite de 30% facultativo):
    - Empréstimo: 35% (da base, mas limitado a 30% somado com cartões)
    - Cartão Consignado: 15% (da base, mas limitado a 30% somado com empréstimo)
    - Cartão Benefício: 15% (da base, mas limitado a 30% somado com empréstimo)
    
    TODOS os cartões contam: nossos, terceiros, não comprados e desconhecidos
    """
    
    # Base de cálculo: TOTALIDADE dos vencimentos - Descontos obrigatórios
    salario_bruto = salario_base + vencimentos_fixos.get('total', 0.0)
    total_descontos_obrigatorios = descontos_obrigatorios.get('total', 0.0)
    
    base_calculo = salario_bruto - total_descontos_obrigatorios
    
    # Percentuais de VINHEDO (seguindo estrutura de Poá)
    # Nota: Estes percentuais são da base, mas o total não pode ultrapassar 30%
    percentual_emprestimo = 0.35  # 35%
    percentual_cartao_consig = 0.15  # 15%
    percentual_cartao_beneficio = 0.15  # 15%
    
    # Limite de consignações facultativas conforme especificação
    limite_consignacoes_facultativas = 0.30  # 30% da base
    margem_facultativa_total = base_calculo * limite_consignacoes_facultativas
    
    # Extrai empréstimos e cartões do holerite
    linhas = texto.split('\n')
    emprestimos_atuais = 0.0
    
    # Separação de cartões por categoria (para detalhamento)
    cartoes_nossos = 0.0
    cartoes_terceiros = 0.0
    cartoes_nao_comprados = 0.0
    cartoes_desconhecidos = 0.0
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        # Verifica se é cartão (qualquer tipo)
        eh_cartao = any(kw in linha_norm for kw in ['CARTAO', 'CRED ', 'CART.'])
        
        if eh_cartao:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                # Classifica o cartão
                if any(produto in linha_norm for produto in ['STARCARD', 'ANTICIPAY', 'STARBANK']):
                    cartoes_nossos += valor
                elif any(cartao in linha_norm for cartao in CARTOES_NAO_COMPRADOS):
                    cartoes_nao_comprados += valor
                elif any(cartao in linha_norm for cartao in CARTOES_CONHECIDOS):
                    cartoes_terceiros += valor
                else:
                    # Cartão desconhecido (para estudar)
                    cartoes_desconhecidos += valor
            continue
        
        # Empréstimos genéricos (que não são cartões)
        if any(termo in linha_norm for termo in ['EMPRESTIMO', 'CONSIGNADO', 'FINANCIAMENTO', 'EMPREST']):
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
    
    # Total de cartões (TODOS contam: nossos + terceiros + não comprados + desconhecidos)
    total_cartoes = cartoes_nossos + cartoes_terceiros + cartoes_nao_comprados + cartoes_desconhecidos
    
    # Total de consignações facultativas comprometidas
    total_consignacoes_facultativas_comprometidas = emprestimos_atuais + total_cartoes
    
    # Cálculo das margens
    margem_emprestimo_total = base_calculo * percentual_emprestimo
    margem_emprestimo_disponivel = margem_emprestimo_total - emprestimos_atuais
    
    # MARGEM DE CARTÃO CONSIGNADO (15%)
    margem_cartao_consig_total = base_calculo * percentual_cartao_consig
    margem_cartao_consig_disponivel = margem_cartao_consig_total - total_cartoes
    
    # MARGEM DE CARTÃO BENEFÍCIO (15%)
    margem_cartao_beneficio_total = base_calculo * percentual_cartao_beneficio
    # Cartão benefício compartilha o mesmo comprometimento (todos os cartões)
    margem_cartao_beneficio_disponivel = margem_cartao_beneficio_total - total_cartoes
    
    # AJUSTE: Verificar se o total de consignações facultativas ultrapassa 30%
    # Se ultrapassar, ajustar as margens disponíveis proporcionalmente
    if total_consignacoes_facultativas_comprometidas > margem_facultativa_total:
        # Já ultrapassou o limite de 30%, zerar margens disponíveis
        margem_emprestimo_disponivel = 0
        margem_cartao_consig_disponivel = 0
        margem_cartao_beneficio_disponivel = 0
    else:
        # Calcular quanto ainda pode ser usado dentro do limite de 30%
        saldo_facultativo = margem_facultativa_total - total_consignacoes_facultativas_comprometidas
        
        # Limitar as margens ao saldo facultativo disponível
        margem_emprestimo_disponivel = min(margem_emprestimo_disponivel, saldo_facultativo)
        margem_cartao_consig_disponivel = min(margem_cartao_consig_disponivel, saldo_facultativo)
        margem_cartao_beneficio_disponivel = min(margem_cartao_beneficio_disponivel, saldo_facultativo)
    
    # Líquido recebido pelo cliente
    liquido_recebido = salario_bruto - total_descontos_obrigatorios - emprestimos_atuais - total_cartoes
    
    # Percentual de liquidez (mínimo 30% - considerando margem total de 70%)
    # Se 70% pode ser consignado, sobra 30% de liquidez mínima
    percentual_liquidez = (liquido_recebido / salario_bruto * 100) if salario_bruto > 0 else 0
    
    # Validação de liquidez mínima
    aprovado_liquidez = percentual_liquidez >= 30.0
    
    return {
        'prefeitura': 'VINHEDO',
        'salario_bruto': salario_bruto,
        'base_calculo': base_calculo,
        'descontos_compulsorios': total_descontos_obrigatorios,
        'emprestimos_atuais': emprestimos_atuais,
        'cartoes_atuais': total_cartoes,
        
        # Detalhamento de cartões
        'cartoes_nossos': cartoes_nossos,
        'cartoes_terceiros': cartoes_terceiros,
        'cartoes_nao_comprados': cartoes_nao_comprados,
        'cartoes_desconhecidos': cartoes_desconhecidos,
        
        # Margens por tipo
        'emprestimo': {
            'percentual': percentual_emprestimo,
            'margem_total': margem_emprestimo_total,
            'comprometido': emprestimos_atuais,
            'disponivel': margem_emprestimo_disponivel
        },
        'cartao_consignado': {
            'percentual': percentual_cartao_consig,
            'margem_total': margem_cartao_consig_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_consig_disponivel
        },
        'cartao_beneficio': {
            'percentual': percentual_cartao_beneficio,
            'margem_total': margem_cartao_beneficio_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_beneficio_disponivel
        },
        
        # Liquidez
        'liquido_recebido': liquido_recebido,
        'percentual_liquidez': percentual_liquidez,
        'liquidez_minima': 30.0,
        'aprovado_liquidez': aprovado_liquidez,
        
        # Status geral
        'tem_margem_emprestimo': margem_emprestimo_disponivel > 0,
        'tem_margem_cartao': margem_cartao_consig_disponivel > 0 or margem_cartao_beneficio_disponivel > 0,
        
        # Informação adicional específica de Vinhedo
        'limite_consignacoes_facultativas': margem_facultativa_total,
        'total_consignacoes_facultativas': total_consignacoes_facultativas_comprometidas
    }

def calcular_margem_monte_alegre_se(texto: str, salario_base: float, vencimentos_fixos: Dict, 
                                     descontos_obrigatorios: Dict, cartoes_encontrados: Dict) -> Dict:
    """
    Calcula margem consignável para MONTE ALEGRE DE SERGIPE seguindo as regras da especificação
    
    Regras MONTE ALEGRE SE:
    - Base de Cálculo: Soma dos proventos de natureza permanente/fixa - Descontos compulsórios
    
    Descontos Compulsórios:
    - Contribuição previdenciária (RGPS ou RPPS)
    - Pensão alimentícia por ordem judicial
    - IRPF
    - Obrigações decorrentes de ordem judicial
    - Obrigações decorrentes de lei
    - Restituições e indenizações ao Erário
    - Plano de saúde
    - Plano odontológico
    - Pensão alimentícia voluntária
    - Previdência complementar
    - Planos Funerários
    
    Percentuais (padrão conservador):
    - Empréstimo: 35%
    - Cartão Consignado: 15%
    - Cartão Benefício: 15%
    
    TODOS os cartões contam: nossos, terceiros, não comprados e desconhecidos
    """
    
    # Base de cálculo: Soma dos proventos permanentes - Descontos obrigatórios
    salario_bruto = salario_base + vencimentos_fixos.get('total', 0.0)
    total_descontos_obrigatorios = descontos_obrigatorios.get('total', 0.0)
    
    base_calculo = salario_bruto - total_descontos_obrigatorios
    
    # Percentuais de MONTE ALEGRE SE (seguindo padrão conservador)
    percentual_emprestimo = 0.35  # 35%
    percentual_cartao_consig = 0.15  # 15%
    percentual_cartao_beneficio = 0.15  # 15%
    
    # Extrai empréstimos e cartões do holerite
    linhas = texto.split('\n')
    emprestimos_atuais = 0.0
    
    # Separação de cartões por categoria (para detalhamento)
    cartoes_nossos = 0.0
    cartoes_terceiros = 0.0
    cartoes_nao_comprados = 0.0
    cartoes_desconhecidos = 0.0
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        # Verifica se é cartão (qualquer tipo)
        eh_cartao = any(kw in linha_norm for kw in ['CARTAO', 'CRED ', 'CART.'])
        
        if eh_cartao:
            valor = extrair_valores_desconto_monte_alegre_se(linha)  # USA FUNÇÃO ESPECÍFICA
            if valor > 0:
                # Classifica o cartão
                if any(produto in linha_norm for produto in ['STARCARD', 'ANTICIPAY', 'STARBANK']):
                    cartoes_nossos += valor
                elif any(cartao in linha_norm for cartao in CARTOES_NAO_COMPRADOS):
                    cartoes_nao_comprados += valor
                elif any(cartao in linha_norm for cartao in CARTOES_CONHECIDOS):
                    cartoes_terceiros += valor
                else:
                    # Cartão desconhecido (para estudar)
                    cartoes_desconhecidos += valor
            continue
        
        # Empréstimos genéricos (que não são cartões)
        if any(termo in linha_norm for termo in ['EMPRESTIMO', 'CONSIGNADO', 'FINANCIAMENTO', 'EMPREST']):
            valor = extrair_valores_desconto_monte_alegre_se(linha)  # USA FUNÇÃO ESPECÍFICA
            if valor > 0:
                emprestimos_atuais += valor
    
    # Total de cartões (TODOS contam: nossos + terceiros + não comprados + desconhecidos)
    total_cartoes = cartoes_nossos + cartoes_terceiros + cartoes_nao_comprados + cartoes_desconhecidos
    
    # Cálculo das margens
    margem_emprestimo_total = base_calculo * percentual_emprestimo
    margem_emprestimo_disponivel = margem_emprestimo_total - emprestimos_atuais
    
    # MARGEM DE CARTÃO CONSIGNADO (15%)
    margem_cartao_consig_total = base_calculo * percentual_cartao_consig
    margem_cartao_consig_disponivel = margem_cartao_consig_total - total_cartoes
    
    # MARGEM DE CARTÃO BENEFÍCIO (15%)
    margem_cartao_beneficio_total = base_calculo * percentual_cartao_beneficio
    # Cartão benefício compartilha o mesmo comprometimento (todos os cartões)
    margem_cartao_beneficio_disponivel = margem_cartao_beneficio_total - total_cartoes
    
    # Líquido recebido pelo cliente
    liquido_recebido = salario_bruto - total_descontos_obrigatorios - emprestimos_atuais - total_cartoes
    
    # Percentual de liquidez (mínimo 30%)
    percentual_liquidez = (liquido_recebido / salario_bruto * 100) if salario_bruto > 0 else 0
    
    # Validação de liquidez mínima
    aprovado_liquidez = percentual_liquidez >= 30.0
    
    return {
        'prefeitura': 'MONTE_ALEGRE_SE',
        'salario_bruto': salario_bruto,
        'base_calculo': base_calculo,
        'descontos_compulsorios': total_descontos_obrigatorios,
        'emprestimos_atuais': emprestimos_atuais,
        'cartoes_atuais': total_cartoes,
        
        # Detalhamento de cartões
        'cartoes_nossos': cartoes_nossos,
        'cartoes_terceiros': cartoes_terceiros,
        'cartoes_nao_comprados': cartoes_nao_comprados,
        'cartoes_desconhecidos': cartoes_desconhecidos,
        
        # Margens por tipo
        'emprestimo': {
            'percentual': percentual_emprestimo,
            'margem_total': margem_emprestimo_total,
            'comprometido': emprestimos_atuais,
            'disponivel': margem_emprestimo_disponivel
        },
        'cartao_consignado': {
            'percentual': percentual_cartao_consig,
            'margem_total': margem_cartao_consig_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_consig_disponivel
        },
        'cartao_beneficio': {
            'percentual': percentual_cartao_beneficio,
            'margem_total': margem_cartao_beneficio_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_beneficio_disponivel
        },
        
        # Liquidez
        'liquido_recebido': liquido_recebido,
        'percentual_liquidez': percentual_liquidez,
        'liquidez_minima': 30.0,
        'aprovado_liquidez': aprovado_liquidez,
        
        # Status geral
        'tem_margem_emprestimo': margem_emprestimo_disponivel > 0,
        'tem_margem_cartao': margem_cartao_consig_disponivel > 0 or margem_cartao_beneficio_disponivel > 0
    }

def calcular_margem_sao_jose_rio_preto(texto: str, salario_base: float, vencimentos_fixos: Dict, 
                                        descontos_obrigatorios: Dict, cartoes_encontrados: Dict) -> Dict:
    """
    Calcula margem consignável para SÃO JOSÉ DO RIO PRETO seguindo as especificações
    
    Regras SÃO JOSÉ DO RIO PRETO:
    - Base de Cálculo: Soma dos proventos permanentes - Descontos Compulsórios
    - Proventos: VENCIMENTO + ADIC. FIXO + GRAT. FIXA
    - OBS: Auxílio Saúde NÃO entra no cálculo de margem
    - Descontos: Previdência (Própria + Geral), IRRF, Obrigações judiciais, 
                 Reposição ao erário, Contribuição sindical
    - Empréstimo: 35%
    - Cartão Consignado: 15%
    - Cartão Benefício: 15%
    
    TODOS os cartões contam: nossos, terceiros, não comprados e desconhecidos
    """
    
    # Base de cálculo: Salário base + Vencimentos permanentes - Descontos obrigatórios
    # IMPORTANTE: vencimentos_fixos já considera apenas proventos permanentes (sem Auxílio Saúde)
    salario_bruto = salario_base + vencimentos_fixos.get('total', 0.0)
    
    # Descontos compulsórios
    total_descontos_obrigatorios = descontos_obrigatorios.get('total', 0.0)
    
    base_calculo = salario_bruto - total_descontos_obrigatorios
    
    # Percentuais de SÃO JOSÉ DO RIO PRETO
    percentual_emprestimo = 0.35  # 35%
    percentual_cartao_consig = 0.15  # 15%
    percentual_cartao_beneficio = 0.15  # 15%
    
    # Extrai empréstimos e cartões do holerite
    linhas = texto.split('\n')
    emprestimos_atuais = 0.0
    
    # Separação de cartões por categoria (para detalhamento)
    cartoes_nossos = 0.0
    cartoes_terceiros = 0.0
    cartoes_nao_comprados = 0.0
    cartoes_desconhecidos = 0.0
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        # Verifica se é cartão (qualquer tipo)
        eh_cartao = any(kw in linha_norm for kw in ['CARTAO', 'CRED ', 'CART.'])
        
        if eh_cartao:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                # Classifica o cartão
                if any(produto in linha_norm for produto in ['STARCARD', 'ANTICIPAY', 'STARBANK']):
                    cartoes_nossos += valor
                elif any(cartao in linha_norm for cartao in CARTOES_NAO_COMPRADOS):
                    cartoes_nao_comprados += valor
                elif any(cartao in linha_norm for cartao in CARTOES_CONHECIDOS):
                    cartoes_terceiros += valor
                else:
                    # Cartão desconhecido (para estudar)
                    cartoes_desconhecidos += valor
            continue
        
        # Empréstimos genéricos (que não são cartões)
        if any(termo in linha_norm for termo in ['EMPRESTIMO', 'CONSIGNADO', 'FINANCIAMENTO', 'EMPREST']):
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
    
    # Total de cartões (TODOS contam: nossos + terceiros + não comprados + desconhecidos)
    total_cartoes = cartoes_nossos + cartoes_terceiros + cartoes_nao_comprados + cartoes_desconhecidos
    
    # Cálculo das margens
    margem_emprestimo_total = base_calculo * percentual_emprestimo
    margem_emprestimo_disponivel = margem_emprestimo_total - emprestimos_atuais
    
    # MARGEM DE CARTÃO CONSIGNADO (15%)
    margem_cartao_consig_total = base_calculo * percentual_cartao_consig
    margem_cartao_consig_disponivel = margem_cartao_consig_total - total_cartoes
    
    # MARGEM DE CARTÃO BENEFÍCIO (15%)
    margem_cartao_beneficio_total = base_calculo * percentual_cartao_beneficio
    # Cartão benefício compartilha o mesmo comprometimento (todos os cartões)
    margem_cartao_beneficio_disponivel = margem_cartao_beneficio_total - total_cartoes
    
    # Líquido recebido pelo cliente
    liquido_recebido = salario_bruto - total_descontos_obrigatorios - emprestimos_atuais - total_cartoes
    
    # Percentual de liquidez (mínimo 30%)
    percentual_liquidez = (liquido_recebido / salario_bruto * 100) if salario_bruto > 0 else 0
    
    # Validação de liquidez mínima
    aprovado_liquidez = percentual_liquidez >= 30.0
    
    return {
        'prefeitura': 'SAO_JOSE_RIO_PRETO',
        'salario_bruto': salario_bruto,
        'base_calculo': base_calculo,
        'descontos_compulsorios': total_descontos_obrigatorios,
        'emprestimos_atuais': emprestimos_atuais,
        'cartoes_atuais': total_cartoes,
        
        # Detalhamento de cartões
        'cartoes_nossos': cartoes_nossos,
        'cartoes_terceiros': cartoes_terceiros,
        'cartoes_nao_comprados': cartoes_nao_comprados,
        'cartoes_desconhecidos': cartoes_desconhecidos,
        
        # Margens por tipo
        'emprestimo': {
            'percentual': percentual_emprestimo,
            'margem_total': margem_emprestimo_total,
            'comprometido': emprestimos_atuais,
            'disponivel': margem_emprestimo_disponivel
        },
        'cartao_consignado': {
            'percentual': percentual_cartao_consig,
            'margem_total': margem_cartao_consig_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_consig_disponivel
        },
        'cartao_beneficio': {
            'percentual': percentual_cartao_beneficio,
            'margem_total': margem_cartao_beneficio_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_beneficio_disponivel
        },
        
        # Liquidez
        'liquido_recebido': liquido_recebido,
        'percentual_liquidez': percentual_liquidez,
        'liquidez_minima': 30.0,
        'aprovado_liquidez': aprovado_liquidez,
        
        # Status geral
        'tem_margem_emprestimo': margem_emprestimo_disponivel > 0,
        'tem_margem_cartao': margem_cartao_consig_disponivel > 0 or margem_cartao_beneficio_disponivel > 0
    }

def calcular_margem_ponta_grossa(texto: str, salario_base: float, vencimentos_fixos: Dict, 
                                  descontos_obrigatorios: Dict, cartoes_encontrados: Dict) -> Dict:
    """
    Calcula margem consignável para PONTA GROSSA seguindo as especificações
    
    Regras PONTA GROSSA:
    - Base de Cálculo: SALÁRIO BASE - Descontos Compulsórios (IRRF + PREVIDÊNCIA)
    - Empréstimo: 35%
    - Cartão Consignado: 15%
    - Cartão Benefício: 15%
    
    TODOS os cartões contam: nossos, terceiros, não comprados e desconhecidos
    """
    
    # Base de cálculo: Apenas Salário Base - Descontos obrigatórios
    # Conforme especificação: considera APENAS o salário base como provento permanente
    salario_bruto = salario_base
    
    # Descontos compulsórios (IRRF + PREVIDÊNCIA)
    total_descontos_obrigatorios = descontos_obrigatorios.get('total', 0.0)
    
    base_calculo = salario_bruto - total_descontos_obrigatorios
    
    # Percentuais de PONTA GROSSA (usando mesmos percentuais de POÁ)
    percentual_emprestimo = 0.35  # 35%
    percentual_cartao_consig = 0.15  # 15%
    percentual_cartao_beneficio = 0.15  # 15%
    
    # Extrai empréstimos e cartões do holerite
    linhas = texto.split('\n')
    emprestimos_atuais = 0.0
    
    # Separação de cartões por categoria (para detalhamento)
    cartoes_nossos = 0.0
    cartoes_terceiros = 0.0
    cartoes_nao_comprados = 0.0
    cartoes_desconhecidos = 0.0
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        # Verifica se é cartão (qualquer tipo)
        eh_cartao = any(kw in linha_norm for kw in ['CARTAO', 'CRED ', 'CART.'])
        
        if eh_cartao:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                # Classifica o cartão
                if any(produto in linha_norm for produto in ['STARCARD', 'ANTICIPAY', 'STARBANK']):
                    cartoes_nossos += valor
                elif any(cartao in linha_norm for cartao in CARTOES_NAO_COMPRADOS):
                    cartoes_nao_comprados += valor
                elif any(cartao in linha_norm for cartao in CARTOES_CONHECIDOS):
                    cartoes_terceiros += valor
                else:
                    # Cartão desconhecido (para estudar)
                    cartoes_desconhecidos += valor
            continue
        
        # Empréstimos genéricos (que não são cartões)
        if any(termo in linha_norm for termo in ['EMPRESTIMO', 'CONSIGNADO', 'FINANCIAMENTO', 'EMPREST']):
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
    
    # Total de cartões (TODOS contam: nossos + terceiros + não comprados + desconhecidos)
    total_cartoes = cartoes_nossos + cartoes_terceiros + cartoes_nao_comprados + cartoes_desconhecidos
    
    # Cálculo das margens
    margem_emprestimo_total = base_calculo * percentual_emprestimo
    margem_emprestimo_disponivel = margem_emprestimo_total - emprestimos_atuais
    
    # MARGEM DE CARTÃO CONSIGNADO (15%)
    margem_cartao_consig_total = base_calculo * percentual_cartao_consig
    margem_cartao_consig_disponivel = margem_cartao_consig_total - total_cartoes
    
    # MARGEM DE CARTÃO BENEFÍCIO (15%)
    margem_cartao_beneficio_total = base_calculo * percentual_cartao_beneficio
    # Cartão benefício compartilha o mesmo comprometimento (todos os cartões)
    margem_cartao_beneficio_disponivel = margem_cartao_beneficio_total - total_cartoes
    
    # Líquido recebido pelo cliente
    liquido_recebido = salario_bruto - total_descontos_obrigatorios - emprestimos_atuais - total_cartoes
    
    # Percentual de liquidez (mínimo 30%)
    percentual_liquidez = (liquido_recebido / salario_bruto * 100) if salario_bruto > 0 else 0
    
    # Validação de liquidez mínima
    aprovado_liquidez = percentual_liquidez >= 30.0
    
    return {
        'prefeitura': 'PONTA_GROSSA',
        'salario_bruto': salario_bruto,
        'base_calculo': base_calculo,
        'descontos_compulsorios': total_descontos_obrigatorios,
        'emprestimos_atuais': emprestimos_atuais,
        'cartoes_atuais': total_cartoes,
        
        # Detalhamento de cartões
        'cartoes_nossos': cartoes_nossos,
        'cartoes_terceiros': cartoes_terceiros,
        'cartoes_nao_comprados': cartoes_nao_comprados,
        'cartoes_desconhecidos': cartoes_desconhecidos,
        
        # Margens por tipo
        'emprestimo': {
            'percentual': percentual_emprestimo,
            'margem_total': margem_emprestimo_total,
            'comprometido': emprestimos_atuais,
            'disponivel': margem_emprestimo_disponivel
        },
        'cartao_consignado': {
            'percentual': percentual_cartao_consig,
            'margem_total': margem_cartao_consig_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_consig_disponivel
        },
        'cartao_beneficio': {
            'percentual': percentual_cartao_beneficio,
            'margem_total': margem_cartao_beneficio_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_beneficio_disponivel
        },
        
        # Liquidez
        'liquido_recebido': liquido_recebido,
        'percentual_liquidez': percentual_liquidez,
        'liquidez_minima': 30.0,
        'aprovado_liquidez': aprovado_liquidez,
        
        # Status geral
        'tem_margem_emprestimo': margem_emprestimo_disponivel > 0,
        'tem_margem_cartao': margem_cartao_consig_disponivel > 0 or margem_cartao_beneficio_disponivel > 0
    }

def calcular_margem_camara_deputados(texto: str, salario_base: float, vencimentos_fixos: Dict, 
                                      descontos_obrigatorios: Dict, cartoes_encontrados: Dict) -> Dict:
    """
    Calcula margem consignável para CÂMARA DOS DEPUTADOS seguindo as especificações
    
    Regras CÂMARA DOS DEPUTADOS:
    - Base de Cálculo: VENCIMENTO - Descontos Compulsórios (IRRF + INSS + Pensão alimentícia)
    - Empréstimo: 35%
    - Cartão Consignado: 15%
    - Cartão Benefício: 15%
    
    TODOS os cartões contam: nossos, terceiros, não comprados e desconhecidos
    """
    
    # Base de cálculo: Apenas Vencimento - Descontos obrigatórios
    # Conforme especificação: considera APENAS o vencimento como provento permanente
    salario_bruto = salario_base
    
    # Descontos compulsórios (IRRF + INSS + Pensão alimentícia)
    total_descontos_obrigatorios = descontos_obrigatorios.get('total', 0.0)
    
    base_calculo = salario_bruto - total_descontos_obrigatorios
    
    # Percentuais da CÂMARA DOS DEPUTADOS (usando mesmos percentuais de POÁ)
    percentual_emprestimo = 0.35  # 35%
    percentual_cartao_consig = 0.15  # 15%
    percentual_cartao_beneficio = 0.15  # 15%
    
    # Extrai empréstimos e cartões do holerite
    linhas = texto.split('\n')
    emprestimos_atuais = 0.0
    
    # Separação de cartões por categoria (para detalhamento)
    cartoes_nossos = 0.0
    cartoes_terceiros = 0.0
    cartoes_nao_comprados = 0.0
    cartoes_desconhecidos = 0.0
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        # Verifica se é cartão (qualquer tipo)
        eh_cartao = any(kw in linha_norm for kw in ['CARTAO', 'CRED ', 'CART.'])
        
        if eh_cartao:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                # Classifica o cartão
                if any(produto in linha_norm for produto in ['STARCARD', 'ANTICIPAY', 'STARBANK']):
                    cartoes_nossos += valor
                elif any(cartao in linha_norm for cartao in CARTOES_NAO_COMPRADOS):
                    cartoes_nao_comprados += valor
                elif any(cartao in linha_norm for cartao in CARTOES_CONHECIDOS):
                    cartoes_terceiros += valor
                else:
                    # Cartão desconhecido (para estudar)
                    cartoes_desconhecidos += valor
            continue
        
        # Empréstimos genéricos (que não são cartões)
        if any(termo in linha_norm for termo in ['EMPRESTIMO', 'CONSIGNADO', 'FINANCIAMENTO', 'EMPREST']):
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
    
    # Total de cartões (TODOS contam: nossos + terceiros + não comprados + desconhecidos)
    total_cartoes = cartoes_nossos + cartoes_terceiros + cartoes_nao_comprados + cartoes_desconhecidos
    
    # Cálculo das margens
    margem_emprestimo_total = base_calculo * percentual_emprestimo
    margem_emprestimo_disponivel = margem_emprestimo_total - emprestimos_atuais
    
    # MARGEM DE CARTÃO CONSIGNADO (15%)
    margem_cartao_consig_total = base_calculo * percentual_cartao_consig
    margem_cartao_consig_disponivel = margem_cartao_consig_total - total_cartoes
    
    # MARGEM DE CARTÃO BENEFÍCIO (15%)
    margem_cartao_beneficio_total = base_calculo * percentual_cartao_beneficio
    # Cartão benefício compartilha o mesmo comprometimento (todos os cartões)
    margem_cartao_beneficio_disponivel = margem_cartao_beneficio_total - total_cartoes
    
    # Líquido recebido pelo cliente
    liquido_recebido = salario_bruto - total_descontos_obrigatorios - emprestimos_atuais - total_cartoes
    
    # Percentual de liquidez (mínimo 30%)
    percentual_liquidez = (liquido_recebido / salario_bruto * 100) if salario_bruto > 0 else 0
    
    # Validação de liquidez mínima
    aprovado_liquidez = percentual_liquidez >= 30.0
    
    return {
        'prefeitura': 'CAMARA_DEPUTADOS',
        'salario_bruto': salario_bruto,
        'base_calculo': base_calculo,
        'descontos_compulsorios': total_descontos_obrigatorios,
        'emprestimos_atuais': emprestimos_atuais,
        'cartoes_atuais': total_cartoes,
        
        # Detalhamento de cartões
        'cartoes_nossos': cartoes_nossos,
        'cartoes_terceiros': cartoes_terceiros,
        'cartoes_nao_comprados': cartoes_nao_comprados,
        'cartoes_desconhecidos': cartoes_desconhecidos,
        
        # Margens por tipo
        'emprestimo': {
            'percentual': percentual_emprestimo,
            'margem_total': margem_emprestimo_total,
            'comprometido': emprestimos_atuais,
            'disponivel': margem_emprestimo_disponivel
        },
        'cartao_consignado': {
            'percentual': percentual_cartao_consig,
            'margem_total': margem_cartao_consig_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_consig_disponivel
        },
        'cartao_beneficio': {
            'percentual': percentual_cartao_beneficio,
            'margem_total': margem_cartao_beneficio_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_beneficio_disponivel
        },
        
        # Liquidez
        'liquido_recebido': liquido_recebido,
        'percentual_liquidez': percentual_liquidez,
        'liquidez_minima': 30.0,
        'aprovado_liquidez': aprovado_liquidez,
        
        # Status geral
        'tem_margem_emprestimo': margem_emprestimo_disponivel > 0,
        'tem_margem_cartao': margem_cartao_consig_disponivel > 0 or margem_cartao_beneficio_disponivel > 0
    }

def calcular_margem_belterra(texto: str, salario_base: float, vencimentos_fixos: Dict, 
                              descontos_obrigatorios: Dict, cartoes_encontrados: Dict) -> Dict:
    """
    Calcula margem consignável para BELTERRA seguindo as especificações
    
    Regras BELTERRA:
    - Base de Cálculo: Soma dos proventos permanentes - Descontos Compulsórios
    - Proventos: Salário, Adicional tempo serviço, Enfermagem, Gratificação títulos, 
                 Sexta parte, Gratificações fixas
    - Descontos: Previdência, IRRF, Pensão alimentícia, Reposição ao erário
    - Empréstimo: 35%
    - Cartão Consignado: 15%
    - Cartão Benefício: 15%
    
    TODOS os cartões contam: nossos, terceiros, não comprados e desconhecidos
    """
    
    # Base de cálculo: Salário base + Vencimentos permanentes - Descontos obrigatórios
    salario_bruto = salario_base + vencimentos_fixos.get('total', 0.0)
    
    # Descontos compulsórios (Previdência + IRRF + Pensão + Reposição ao erário)
    total_descontos_obrigatorios = descontos_obrigatorios.get('total', 0.0)
    
    base_calculo = salario_bruto - total_descontos_obrigatorios
    
    # Percentuais de BELTERRA
    percentual_emprestimo = 0.35  # 35%
    percentual_cartao_consig = 0.15  # 15%
    percentual_cartao_beneficio = 0.15  # 15%
    
    # Extrai empréstimos e cartões do holerite
    linhas = texto.split('\n')
    emprestimos_atuais = 0.0
    
    # Separação de cartões por categoria (para detalhamento)
    cartoes_nossos = 0.0
    cartoes_terceiros = 0.0
    cartoes_nao_comprados = 0.0
    cartoes_desconhecidos = 0.0
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        # Verifica se é cartão (qualquer tipo)
        eh_cartao = any(kw in linha_norm for kw in ['CARTAO', 'CRED ', 'CART.'])
        
        if eh_cartao:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                # Classifica o cartão
                if any(produto in linha_norm for produto in ['STARCARD', 'ANTICIPAY', 'STARBANK']):
                    cartoes_nossos += valor
                elif any(cartao in linha_norm for cartao in CARTOES_NAO_COMPRADOS):
                    cartoes_nao_comprados += valor
                elif any(cartao in linha_norm for cartao in CARTOES_CONHECIDOS):
                    cartoes_terceiros += valor
                else:
                    # Cartão desconhecido (para estudar)
                    cartoes_desconhecidos += valor
            continue
        
        # Empréstimos genéricos (que não são cartões)
        if any(termo in linha_norm for termo in ['EMPRESTIMO', 'CONSIGNADO', 'FINANCIAMENTO', 'EMPREST']):
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
    
    # Total de cartões (TODOS contam: nossos + terceiros + não comprados + desconhecidos)
    total_cartoes = cartoes_nossos + cartoes_terceiros + cartoes_nao_comprados + cartoes_desconhecidos
    
    # Cálculo das margens
    margem_emprestimo_total = base_calculo * percentual_emprestimo
    margem_emprestimo_disponivel = margem_emprestimo_total - emprestimos_atuais
    
    # MARGEM DE CARTÃO CONSIGNADO (15%)
    margem_cartao_consig_total = base_calculo * percentual_cartao_consig
    margem_cartao_consig_disponivel = margem_cartao_consig_total - total_cartoes
    
    # MARGEM DE CARTÃO BENEFÍCIO (15%)
    margem_cartao_beneficio_total = base_calculo * percentual_cartao_beneficio
    # Cartão benefício compartilha o mesmo comprometimento (todos os cartões)
    margem_cartao_beneficio_disponivel = margem_cartao_beneficio_total - total_cartoes
    
    # Líquido recebido pelo cliente
    liquido_recebido = salario_bruto - total_descontos_obrigatorios - emprestimos_atuais - total_cartoes
    
    # Percentual de liquidez (mínimo 30%)
    percentual_liquidez = (liquido_recebido / salario_bruto * 100) if salario_bruto > 0 else 0
    
    # Validação de liquidez mínima
    aprovado_liquidez = percentual_liquidez >= 30.0
    
    return {
        'prefeitura': 'BELTERRA',
        'salario_bruto': salario_bruto,
        'base_calculo': base_calculo,
        'descontos_compulsorios': total_descontos_obrigatorios,
        'emprestimos_atuais': emprestimos_atuais,
        'cartoes_atuais': total_cartoes,
        
        # Detalhamento de cartões
        'cartoes_nossos': cartoes_nossos,
        'cartoes_terceiros': cartoes_terceiros,
        'cartoes_nao_comprados': cartoes_nao_comprados,
        'cartoes_desconhecidos': cartoes_desconhecidos,
        
        # Margens por tipo
        'emprestimo': {
            'percentual': percentual_emprestimo,
            'margem_total': margem_emprestimo_total,
            'comprometido': emprestimos_atuais,
            'disponivel': margem_emprestimo_disponivel
        },
        'cartao_consignado': {
            'percentual': percentual_cartao_consig,
            'margem_total': margem_cartao_consig_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_consig_disponivel
        },
        'cartao_beneficio': {
            'percentual': percentual_cartao_beneficio,
            'margem_total': margem_cartao_beneficio_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_beneficio_disponivel
        },
        
        # Liquidez
        'liquido_recebido': liquido_recebido,
        'percentual_liquidez': percentual_liquidez,
        'liquidez_minima': 30.0,
        'aprovado_liquidez': aprovado_liquidez,
        
        # Status geral
        'tem_margem_emprestimo': margem_emprestimo_disponivel > 0,
        'tem_margem_cartao': margem_cartao_consig_disponivel > 0 or margem_cartao_beneficio_disponivel > 0
    }

def calcular_margem_campos_jordao(texto: str, salario_base: float, vencimentos_fixos: Dict,
                                   descontos_obrigatorios: Dict, cartoes_encontrados: Dict) -> Dict:
    """
    Calcula margem consignável para CAMPOS DO JORDÃO.

    BASE DE CÁLCULO:
      Soma dos proventos de natureza permanente ou fixas
      (cód. 30 SALARIO + cód. 1210 ADICIONAL POR TEMPO + cód. 1370 SEXTA PARTE)
      deduzindo os consignados compulsórios (INSS/RGPS, IRRF, etc.)

    Percentuais:
    - Empréstimo:         35%
    - Cartão Consignado:  15%
    - Cartão Benefício:   15%

    TODOS os cartões contam: nossos, terceiros, não comprados e desconhecidos.
    """

    # Base: vencimentos fixos (apenas os permanentes) - descontos obrigatórios
    # salario_base já está dentro de vencimentos_fixos['vencimento_base'],
    # mas somamos para garantir consistência com o padrão das demais prefeituras.
    salario_bruto = salario_base + vencimentos_fixos.get('total', 0.0)
    total_descontos_obrigatorios = descontos_obrigatorios.get('total', 0.0)

    base_calculo = salario_bruto - total_descontos_obrigatorios

    # Percentuais de CAMPOS DO JORDÃO
    percentual_emprestimo       = 0.35   # 35%
    percentual_cartao_consig    = 0.15   # 15%
    percentual_cartao_beneficio = 0.15   # 15%

    # Extrai empréstimos e cartões do holerite
    linhas = texto.split('\n')
    emprestimos_atuais = 0.0

    cartoes_nossos        = 0.0
    cartoes_terceiros     = 0.0
    cartoes_nao_comprados = 0.0
    cartoes_desconhecidos = 0.0

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # CRESSEM EMPRESTIMO conta como empréstimo consignado
        if 'CRESSEM EMPRESTIMO' in linha_norm or 'CRESSEM INTEGRALIZACAO' in linha_norm:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
            continue

        # UASPREV e similares também contam como empréstimo
        if 'UASPREV' in linha_norm or 'ANTICIPAY' in linha_norm:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
            continue

        # Verifica se é cartão (qualquer tipo)
        eh_cartao = any(kw in linha_norm for kw in ['CARTAO', 'CRED ', 'CART.'])

        if eh_cartao:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                if any(produto in linha_norm for produto in ['STARCARD', 'ANTICIPAY', 'STARBANK']):
                    cartoes_nossos += valor
                elif any(cartao in linha_norm for cartao in CARTOES_NAO_COMPRADOS):
                    cartoes_nao_comprados += valor
                elif any(cartao in linha_norm for cartao in CARTOES_CONHECIDOS):
                    cartoes_terceiros += valor
                else:
                    cartoes_desconhecidos += valor
            continue

        # Empréstimos genéricos (que não são cartões nem CRESSEM)
        if any(termo in linha_norm for termo in ['EMPRESTIMO', 'CONSIGNADO', 'FINANCIAMENTO', 'EMPREST']):
            if 'CRESSEM' not in linha_norm:
                valor = extrair_valores_desconto(linha)
                if valor > 0:
                    emprestimos_atuais += valor

    # Total de cartões (TODOS contam)
    total_cartoes = cartoes_nossos + cartoes_terceiros + cartoes_nao_comprados + cartoes_desconhecidos

    # Cálculo das margens
    margem_emprestimo_total      = base_calculo * percentual_emprestimo
    margem_emprestimo_disponivel = margem_emprestimo_total - emprestimos_atuais

    margem_cartao_consig_total      = base_calculo * percentual_cartao_consig
    margem_cartao_consig_disponivel = margem_cartao_consig_total - total_cartoes

    margem_cartao_beneficio_total      = base_calculo * percentual_cartao_beneficio
    margem_cartao_beneficio_disponivel = margem_cartao_beneficio_total - total_cartoes

    # Líquido e liquidez
    liquido_recebido    = salario_bruto - total_descontos_obrigatorios - emprestimos_atuais - total_cartoes
    percentual_liquidez = (liquido_recebido / salario_bruto * 100) if salario_bruto > 0 else 0
    aprovado_liquidez   = percentual_liquidez >= 30.0

    return {
        'prefeitura': 'CAMPOS_JORDAO',
        'salario_bruto': salario_bruto,
        'base_calculo': base_calculo,
        'descontos_compulsorios': total_descontos_obrigatorios,
        'emprestimos_atuais': emprestimos_atuais,
        'cartoes_atuais': total_cartoes,

        # Detalhamento de cartões
        'cartoes_nossos': cartoes_nossos,
        'cartoes_terceiros': cartoes_terceiros,
        'cartoes_nao_comprados': cartoes_nao_comprados,
        'cartoes_desconhecidos': cartoes_desconhecidos,

        # Margens por tipo
        'emprestimo': {
            'percentual': percentual_emprestimo,
            'margem_total': margem_emprestimo_total,
            'comprometido': emprestimos_atuais,
            'disponivel': margem_emprestimo_disponivel
        },
        'cartao_consignado': {
            'percentual': percentual_cartao_consig,
            'margem_total': margem_cartao_consig_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_consig_disponivel
        },
        'cartao_beneficio': {
            'percentual': percentual_cartao_beneficio,
            'margem_total': margem_cartao_beneficio_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_beneficio_disponivel
        },

        # Liquidez
        'liquido_recebido': liquido_recebido,
        'percentual_liquidez': percentual_liquidez,
        'liquidez_minima': 30.0,
        'aprovado_liquidez': aprovado_liquidez,

        # Status geral
        'tem_margem_emprestimo': margem_emprestimo_disponivel > 0,
        'tem_margem_cartao': margem_cartao_consig_disponivel > 0 or margem_cartao_beneficio_disponivel > 0
    }

def calcular_margem_salto(texto: str, salario_base: float, vencimentos_fixos: Dict, 
                         descontos_obrigatorios: Dict, cartoes_encontrados: Dict) -> Dict:
    """
    Calcula margem consignável para SALTO seguindo as regras da especificação
    
    Base de Cálculo: Proventos permanentes/fixos - Descontos compulsórios
    
    Percentuais SALTO (CONFIRMAR COM GESTOR):
    - Empréstimo: 35%
    - Cartão Consignado: 15%
    - Cartão Benefício: 15%
    
    TODOS os cartões contam: nossos, terceiros, não comprados e desconhecidos
    """
    
    # Base de cálculo: Salário Base + Vencimentos permanentes - Descontos compulsórios
    salario_bruto = salario_base + vencimentos_fixos.get('total', 0.0)
    total_descontos_obrigatorios = descontos_obrigatorios.get('total', 0.0)
    
    base_calculo = salario_bruto - total_descontos_obrigatorios
    
    # Percentuais de SALTO (CONFIRMAR VALORES CORRETOS COM A GESTORA)
    percentual_emprestimo = 0.35  # 35%
    percentual_cartao_consig = 0.15  # 15%
    percentual_cartao_beneficio = 0.15  # 15%
    
    # Extrai empréstimos e cartões do holerite
    linhas = texto.split('\n')
    emprestimos_atuais = 0.0
    
    # Separação de cartões por categoria
    cartoes_nossos = 0.0
    cartoes_terceiros = 0.0
    cartoes_nao_comprados = 0.0
    cartoes_desconhecidos = 0.0
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        # Verifica se é cartão (qualquer tipo)
        eh_cartao = any(kw in linha_norm for kw in ['CARTAO', 'CRED ', 'CART.'])
        
        if eh_cartao:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                # Classifica o cartão
                if any(produto in linha_norm for produto in ['STARCARD', 'ANTICIPAY', 'STARBANK']):
                    cartoes_nossos += valor
                elif any(cartao in linha_norm for cartao in CARTOES_NAO_COMPRADOS):
                    cartoes_nao_comprados += valor
                elif any(cartao in linha_norm for cartao in CARTOES_CONHECIDOS):
                    cartoes_terceiros += valor
                else:
                    # Cartão desconhecido
                    cartoes_desconhecidos += valor
            continue
        
        # Empréstimos genéricos (que não são cartões)
        if any(termo in linha_norm for termo in ['EMPRESTIMO', 'CONSIGNADO', 'FINANCIAMENTO', 'EMPREST']):
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
    
    # Total de cartões (TODOS contam)
    total_cartoes = cartoes_nossos + cartoes_terceiros + cartoes_nao_comprados + cartoes_desconhecidos
    
    # Cálculo das margens
    margem_emprestimo_total = base_calculo * percentual_emprestimo
    margem_emprestimo_disponivel = margem_emprestimo_total - emprestimos_atuais
    
    # MARGEM DE CARTÃO CONSIGNADO
    margem_cartao_consig_total = base_calculo * percentual_cartao_consig
    margem_cartao_consig_disponivel = margem_cartao_consig_total - total_cartoes
    
    # MARGEM DE CARTÃO BENEFÍCIO
    margem_cartao_beneficio_total = base_calculo * percentual_cartao_beneficio
    margem_cartao_beneficio_disponivel = margem_cartao_beneficio_total - total_cartoes
    
    # Líquido recebido pelo cliente
    liquido_recebido = salario_bruto - total_descontos_obrigatorios - emprestimos_atuais - total_cartoes
    
    # Percentual de liquidez (mínimo 30%)
    percentual_liquidez = (liquido_recebido / salario_bruto * 100) if salario_bruto > 0 else 0
    
    # Validação de liquidez mínima
    aprovado_liquidez = percentual_liquidez >= 30.0
    
    return {
        'prefeitura': 'SALTO',
        'salario_bruto': salario_bruto,
        'base_calculo': base_calculo,
        'descontos_compulsorios': total_descontos_obrigatorios,
        'emprestimos_atuais': emprestimos_atuais,
        'cartoes_atuais': total_cartoes,
        
        # Detalhamento de cartões
        'cartoes_nossos': cartoes_nossos,
        'cartoes_terceiros': cartoes_terceiros,
        'cartoes_nao_comprados': cartoes_nao_comprados,
        'cartoes_desconhecidos': cartoes_desconhecidos,
        
        # Margens por tipo
        'emprestimo': {
            'percentual': percentual_emprestimo,
            'margem_total': margem_emprestimo_total,
            'comprometido': emprestimos_atuais,
            'disponivel': margem_emprestimo_disponivel
        },
        'cartao_consignado': {
            'percentual': percentual_cartao_consig,
            'margem_total': margem_cartao_consig_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_consig_disponivel
        },
        'cartao_beneficio': {
            'percentual': percentual_cartao_beneficio,
            'margem_total': margem_cartao_beneficio_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_beneficio_disponivel
        },
        
        # Liquidez
        'liquido_recebido': liquido_recebido,
        'percentual_liquidez': percentual_liquidez,
        'liquidez_minima': 30.0,
        'aprovado_liquidez': aprovado_liquidez,
        
        # Status geral
        'tem_margem_emprestimo': margem_emprestimo_disponivel > 0,
        'tem_margem_cartao': margem_cartao_consig_disponivel > 0 or margem_cartao_beneficio_disponivel > 0
    }

def calcular_margem_ribeirao_preto(texto: str, salario_base: float, vencimentos_fixos: Dict,
                                    descontos_obrigatorios: Dict, cartoes_encontrados: Dict) -> Dict:
    """
    Calcula margem consignável para RIBEIRÃO PRETO.

    BASE DE CÁLCULO:
      Soma dos proventos de natureza permanente ou fixas
      (AULAS P.(TDA) + TDC/TDI permanentes + Insalubridade + Gratif. Fixas)
      deduzindo os consignados compulsórios (INSS, IRRF, Previdência, etc.)

    Percentuais (conforme campo "Marg." impresso no próprio holerite):
    - Empréstimo:         40%
    - Cartão Consignado:  10%
    - Cartão Benefício:   10%

    TODOS os cartões contam: nossos, terceiros, não comprados e desconhecidos.
    """

    # Base: vencimentos fixos (apenas permanentes) - descontos obrigatórios
    salario_bruto = salario_base + vencimentos_fixos.get('total', 0.0)
    total_descontos_obrigatorios = descontos_obrigatorios.get('total', 0.0)

    base_calculo = salario_bruto - total_descontos_obrigatorios

    # Percentuais de RIBEIRÃO PRETO (confirmados pelo próprio holerite)
    percentual_emprestimo       = 0.40   # 40%
    percentual_cartao_consig    = 0.10   # 10%
    percentual_cartao_beneficio = 0.10   # 10%

    # Extrai empréstimos e cartões do holerite
    linhas = texto.split('\n')
    emprestimos_atuais = 0.0

    cartoes_nossos        = 0.0
    cartoes_terceiros     = 0.0
    cartoes_nao_comprados = 0.0
    cartoes_desconhecidos = 0.0

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # UASPREV e similares contam como empréstimo
        if 'UASPREV' in linha_norm or 'ANTICIPAY' in linha_norm:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
            continue

        # Verifica se é cartão (qualquer tipo)
        eh_cartao = any(kw in linha_norm for kw in ['CARTAO', 'CRED ', 'CART.'])

        if eh_cartao:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                if any(produto in linha_norm for produto in ['STARCARD', 'ANTICIPAY', 'STARBANK']):
                    cartoes_nossos += valor
                elif any(cartao in linha_norm for cartao in CARTOES_NAO_COMPRADOS):
                    cartoes_nao_comprados += valor
                elif any(cartao in linha_norm for cartao in CARTOES_CONHECIDOS):
                    cartoes_terceiros += valor
                else:
                    cartoes_desconhecidos += valor
            continue

        # Empréstimos genéricos (que não são cartões)
        if any(termo in linha_norm for termo in ['EMPRESTIMO', 'CONSIGNADO', 'FINANCIAMENTO', 'EMPREST']):
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor

    # Total de cartões (TODOS contam)
    total_cartoes = cartoes_nossos + cartoes_terceiros + cartoes_nao_comprados + cartoes_desconhecidos

    # Cálculo das margens
    margem_emprestimo_total      = base_calculo * percentual_emprestimo
    margem_emprestimo_disponivel = margem_emprestimo_total - emprestimos_atuais

    margem_cartao_consig_total      = base_calculo * percentual_cartao_consig
    margem_cartao_consig_disponivel = margem_cartao_consig_total - total_cartoes

    margem_cartao_beneficio_total      = base_calculo * percentual_cartao_beneficio
    margem_cartao_beneficio_disponivel = margem_cartao_beneficio_total - total_cartoes

    # Líquido e liquidez
    liquido_recebido    = salario_bruto - total_descontos_obrigatorios - emprestimos_atuais - total_cartoes
    percentual_liquidez = (liquido_recebido / salario_bruto * 100) if salario_bruto > 0 else 0
    aprovado_liquidez   = percentual_liquidez >= 30.0

    return {
        'prefeitura': 'RIBEIRAO_PRETO',
        'salario_bruto': salario_bruto,
        'base_calculo': base_calculo,
        'descontos_compulsorios': total_descontos_obrigatorios,
        'emprestimos_atuais': emprestimos_atuais,
        'cartoes_atuais': total_cartoes,

        # Detalhamento de cartões
        'cartoes_nossos': cartoes_nossos,
        'cartoes_terceiros': cartoes_terceiros,
        'cartoes_nao_comprados': cartoes_nao_comprados,
        'cartoes_desconhecidos': cartoes_desconhecidos,

        # Margens por tipo
        'emprestimo': {
            'percentual': percentual_emprestimo,
            'margem_total': margem_emprestimo_total,
            'comprometido': emprestimos_atuais,
            'disponivel': margem_emprestimo_disponivel
        },
        'cartao_consignado': {
            'percentual': percentual_cartao_consig,
            'margem_total': margem_cartao_consig_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_consig_disponivel
        },
        'cartao_beneficio': {
            'percentual': percentual_cartao_beneficio,
            'margem_total': margem_cartao_beneficio_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_beneficio_disponivel
        },

        # Liquidez
        'liquido_recebido': liquido_recebido,
        'percentual_liquidez': percentual_liquidez,
        'liquidez_minima': 30.0,
        'aprovado_liquidez': aprovado_liquidez,

        # Status geral
        'tem_margem_emprestimo': margem_emprestimo_disponivel > 0,
        'tem_margem_cartao': margem_cartao_consig_disponivel > 0 or margem_cartao_beneficio_disponivel > 0
    }

def calcular_margem_barcarena(texto: str, salario_base: float, vencimentos_fixos: Dict,
                               descontos_obrigatorios: Dict, cartoes_encontrados: Dict) -> Dict:
    """
    Calcula margem consignável para BARCARENA seguindo as regras da
    Lei Complementar nº 002/94 de 01/08/1994.

    BASE DE CÁLCULO:
      Salário Mensal + Adicional Tempo de Serviço + Gratificações Fixas
      (-) Descontos compulsórios (INSS/RPPS, IRRF, Pensão judicial, etc.)

    Percentuais:
    - Empréstimo:         35%
    - Cartão Consignado:  15%
    - Cartão Benefício:   15%

    TODOS os cartões contam: nossos, terceiros, não comprados e desconhecidos.
    """

    # Base de cálculo: vencimentos fixos - descontos obrigatórios
    # (salario_base já está incluído em vencimentos_fixos['vencimento_base'],
    #  mas para garantir consistência somamos salario_base + restante de vencimentos_fixos)
    salario_bruto = salario_base + vencimentos_fixos.get('total', 0.0)
    total_descontos_obrigatorios = descontos_obrigatorios.get('total', 0.0)

    base_calculo = salario_bruto - total_descontos_obrigatorios

    # Percentuais de BARCARENA
    percentual_emprestimo       = 0.35   # 35%
    percentual_cartao_consig    = 0.15   # 15%
    percentual_cartao_beneficio = 0.15   # 15%

    # Extrai empréstimos e cartões do holerite
    linhas = texto.split('\n')
    emprestimos_atuais = 0.0

    cartoes_nossos       = 0.0
    cartoes_terceiros    = 0.0
    cartoes_nao_comprados = 0.0
    cartoes_desconhecidos = 0.0

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # UASPREV e similares contam como empréstimo
        if 'UASPREV' in linha_norm or 'ANTICIPAY' in linha_norm:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
            continue

        # Verifica se é cartão (qualquer tipo)
        eh_cartao = any(kw in linha_norm for kw in ['CARTAO', 'CRED ', 'CART.'])

        if eh_cartao:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                if any(produto in linha_norm for produto in ['STARCARD', 'ANTICIPAY', 'STARBANK']):
                    cartoes_nossos += valor
                elif any(cartao in linha_norm for cartao in CARTOES_NAO_COMPRADOS):
                    cartoes_nao_comprados += valor
                elif any(cartao in linha_norm for cartao in CARTOES_CONHECIDOS):
                    cartoes_terceiros += valor
                else:
                    cartoes_desconhecidos += valor
            continue

        # Empréstimos genéricos (que não são cartões)
        if any(termo in linha_norm for termo in ['EMPRESTIMO', 'CONSIGNADO', 'FINANCIAMENTO', 'EMPREST']):
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor

    # Total de cartões (TODOS contam)
    total_cartoes = cartoes_nossos + cartoes_terceiros + cartoes_nao_comprados + cartoes_desconhecidos

    # Cálculo das margens
    margem_emprestimo_total     = base_calculo * percentual_emprestimo
    margem_emprestimo_disponivel = margem_emprestimo_total - emprestimos_atuais

    margem_cartao_consig_total     = base_calculo * percentual_cartao_consig
    margem_cartao_consig_disponivel = margem_cartao_consig_total - total_cartoes

    margem_cartao_beneficio_total     = base_calculo * percentual_cartao_beneficio
    margem_cartao_beneficio_disponivel = margem_cartao_beneficio_total - total_cartoes

    # Líquido e liquidez
    liquido_recebido    = salario_bruto - total_descontos_obrigatorios - emprestimos_atuais - total_cartoes
    percentual_liquidez = (liquido_recebido / salario_bruto * 100) if salario_bruto > 0 else 0
    aprovado_liquidez   = percentual_liquidez >= 30.0

    return {
        'prefeitura': 'BARCARENA',
        'salario_bruto': salario_bruto,
        'base_calculo': base_calculo,
        'descontos_compulsorios': total_descontos_obrigatorios,
        'emprestimos_atuais': emprestimos_atuais,
        'cartoes_atuais': total_cartoes,

        # Detalhamento de cartões
        'cartoes_nossos': cartoes_nossos,
        'cartoes_terceiros': cartoes_terceiros,
        'cartoes_nao_comprados': cartoes_nao_comprados,
        'cartoes_desconhecidos': cartoes_desconhecidos,

        # Margens por tipo
        'emprestimo': {
            'percentual': percentual_emprestimo,
            'margem_total': margem_emprestimo_total,
            'comprometido': emprestimos_atuais,
            'disponivel': margem_emprestimo_disponivel
        },
        'cartao_consignado': {
            'percentual': percentual_cartao_consig,
            'margem_total': margem_cartao_consig_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_consig_disponivel
        },
        'cartao_beneficio': {
            'percentual': percentual_cartao_beneficio,
            'margem_total': margem_cartao_beneficio_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_beneficio_disponivel
        },

        # Liquidez
        'liquido_recebido': liquido_recebido,
        'percentual_liquidez': percentual_liquidez,
        'liquidez_minima': 30.0,
        'aprovado_liquidez': aprovado_liquidez,

        # Status geral
        'tem_margem_emprestimo': margem_emprestimo_disponivel > 0,
        'tem_margem_cartao': margem_cartao_consig_disponivel > 0 or margem_cartao_beneficio_disponivel > 0
    }

def calcular_margem_tupa(texto: str, salario_base: float, vencimentos_fixos: Dict, 
                        descontos_obrigatorios: Dict, cartoes_encontrados: Dict) -> Dict:
    """
    Calcula margem consignável para TUPÃ seguindo as regras da especificação
    
    Base de Cálculo: Proventos permanentes/fixos - Descontos compulsórios
    
    Proventos considerados: APENAS SALÁRIO BASE
    Descontos: IRRF e PREVIDÊNCIA
    
    Percentuais TUPÃ (padrão):
    - Empréstimo: 35%
    - Cartão Consignado: 15%
    - Cartão Benefício: 15%
    
    TODOS os cartões contam: nossos, terceiros, não comprados e desconhecidos
    """
    
    # Base de cálculo: Salário Base + Vencimentos permanentes - Descontos compulsórios
    salario_bruto = salario_base + vencimentos_fixos.get('total', 0.0)
    total_descontos_obrigatorios = descontos_obrigatorios.get('total', 0.0)
    
    base_calculo = salario_bruto - total_descontos_obrigatorios
    
    # Percentuais de TUPÃ
    percentual_emprestimo = 0.35  # 35%
    percentual_cartao_consig = 0.15  # 15%
    percentual_cartao_beneficio = 0.15  # 15%
    
    # Extrai empréstimos e cartões do holerite
    linhas = texto.split('\n')
    emprestimos_atuais = 0.0
    
    # Separação de cartões por categoria
    cartoes_nossos = 0.0
    cartoes_terceiros = 0.0
    cartoes_nao_comprados = 0.0
    cartoes_desconhecidos = 0.0
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        # Verifica se é cartão (qualquer tipo)
        eh_cartao = any(kw in linha_norm for kw in ['CARTAO', 'CRED ', 'CART.'])
        
        if eh_cartao:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                # Classifica o cartão
                if any(produto in linha_norm for produto in ['STARCARD', 'ANTICIPAY', 'STARBANK']):
                    cartoes_nossos += valor
                elif any(cartao in linha_norm for cartao in CARTOES_NAO_COMPRADOS):
                    cartoes_nao_comprados += valor
                elif any(cartao in linha_norm for cartao in CARTOES_CONHECIDOS):
                    cartoes_terceiros += valor
                else:
                    # Cartão desconhecido
                    cartoes_desconhecidos += valor
            continue
        
        # Empréstimos genéricos (que não são cartões)
        if any(termo in linha_norm for termo in ['EMPRESTIMO', 'EMPR.', 'CONSIGNADO', 'FINANCIAMENTO']):
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
    
    # Total de cartões (TODOS contam)
    total_cartoes = cartoes_nossos + cartoes_terceiros + cartoes_nao_comprados + cartoes_desconhecidos
    
    # Cálculo das margens
    margem_emprestimo_total = base_calculo * percentual_emprestimo
    margem_emprestimo_disponivel = margem_emprestimo_total - emprestimos_atuais
    
    # MARGEM DE CARTÃO CONSIGNADO
    margem_cartao_consig_total = base_calculo * percentual_cartao_consig
    margem_cartao_consig_disponivel = margem_cartao_consig_total - total_cartoes
    
    # MARGEM DE CARTÃO BENEFÍCIO
    margem_cartao_beneficio_total = base_calculo * percentual_cartao_beneficio
    margem_cartao_beneficio_disponivel = margem_cartao_beneficio_total - total_cartoes
    
    # Líquido recebido pelo cliente
    liquido_recebido = salario_bruto - total_descontos_obrigatorios - emprestimos_atuais - total_cartoes
    
    # Percentual de liquidez (mínimo 30%)
    percentual_liquidez = (liquido_recebido / salario_bruto * 100) if salario_bruto > 0 else 0
    
    # Validação de liquidez mínima
    aprovado_liquidez = percentual_liquidez >= 30.0
    
    return {
        'prefeitura': 'TUPA',
        'salario_bruto': salario_bruto,
        'base_calculo': base_calculo,
        'descontos_compulsorios': total_descontos_obrigatorios,
        'emprestimos_atuais': emprestimos_atuais,
        'cartoes_atuais': total_cartoes,
        
        # Detalhamento de cartões
        'cartoes_nossos': cartoes_nossos,
        'cartoes_terceiros': cartoes_terceiros,
        'cartoes_nao_comprados': cartoes_nao_comprados,
        'cartoes_desconhecidos': cartoes_desconhecidos,
        
        # Margens por tipo
        'emprestimo': {
            'percentual': percentual_emprestimo,
            'margem_total': margem_emprestimo_total,
            'comprometido': emprestimos_atuais,
            'disponivel': margem_emprestimo_disponivel
        },
        'cartao_consignado': {
            'percentual': percentual_cartao_consig,
            'margem_total': margem_cartao_consig_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_consig_disponivel
        },
        'cartao_beneficio': {
            'percentual': percentual_cartao_beneficio,
            'margem_total': margem_cartao_beneficio_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_beneficio_disponivel
        },
        
        # Liquidez
        'liquido_recebido': liquido_recebido,
        'percentual_liquidez': percentual_liquidez,
        'liquidez_minima': 30.0,
        'aprovado_liquidez': aprovado_liquidez,
        
        # Status geral
        'tem_margem_emprestimo': margem_emprestimo_disponivel > 0,
        'tem_margem_cartao': margem_cartao_consig_disponivel > 0 or margem_cartao_beneficio_disponivel > 0
    }

def calcular_margem_itaituba(texto: str, salario_base: float, vencimentos_fixos: Dict, 
                            descontos_obrigatorios: Dict, cartoes_encontrados: Dict) -> Dict:
    """
    Calcula margem consignável para ITAITUBA seguindo as regras da especificação
    
    Base de Cálculo: Proventos permanentes/fixos - Descontos compulsórios
    
    Proventos considerados:
    - SALÁRIO
    - GRATIFICAÇÃO FIXA
    - ASSISTÊNCIA FINANCEIRA COMP
    - ADICIONAL NOTURNO
    - INSALUBRIDADE
    
    NÃO considerar: Salário família
    
    Descontos compulsórios (Art. 4º):
    - Contribuição previdência social
    - Pensão alimentícia judicial
    - IRRF
    - Reposição/indenização ao erário
    - Outros descontos por lei/mandado judicial
    
    Percentuais ITAITUBA (padrão):
    - Empréstimo: 35%
    - Cartão Consignado: 15%
    - Cartão Benefício: 15%
    
    TODOS os cartões contam: nossos, terceiros, não comprados e desconhecidos
    """
    
    # Base de cálculo: Salário Base + Vencimentos permanentes - Descontos compulsórios
    salario_bruto = salario_base + vencimentos_fixos.get('total', 0.0)
    total_descontos_obrigatorios = descontos_obrigatorios.get('total', 0.0)
    
    base_calculo = salario_bruto - total_descontos_obrigatorios
    
    # Percentuais de ITAITUBA
    percentual_emprestimo = 0.35  # 35%
    percentual_cartao_consig = 0.15  # 15%
    percentual_cartao_beneficio = 0.15  # 15%
    
    # Extrai empréstimos e cartões do holerite
    linhas = texto.split('\n')
    emprestimos_atuais = 0.0
    
    # Separação de cartões por categoria
    cartoes_nossos = 0.0
    cartoes_terceiros = 0.0
    cartoes_nao_comprados = 0.0
    cartoes_desconhecidos = 0.0
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        # Verifica se é cartão (qualquer tipo)
        eh_cartao = any(kw in linha_norm for kw in ['CARTAO', 'CRED', 'CART.', 'SAQUE'])
        
        if eh_cartao:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                # Classifica o cartão
                if any(produto in linha_norm for produto in ['STARCARD', 'ANTICIPAY', 'STARBANK']):
                    cartoes_nossos += valor
                elif any(cartao in linha_norm for cartao in CARTOES_NAO_COMPRADOS):
                    cartoes_nao_comprados += valor
                elif any(cartao in linha_norm for cartao in CARTOES_CONHECIDOS):
                    cartoes_terceiros += valor
                else:
                    # Cartão desconhecido
                    cartoes_desconhecidos += valor
            continue
        
        # Empréstimos genéricos (que não são cartões)
        if any(termo in linha_norm for termo in ['EMPRESTIMO', 'EMPR.', 'CONSIGNADO', 'FINANCIAMENTO']):
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
    
    # Total de cartões (TODOS contam)
    total_cartoes = cartoes_nossos + cartoes_terceiros + cartoes_nao_comprados + cartoes_desconhecidos
    
    # Cálculo das margens
    margem_emprestimo_total = base_calculo * percentual_emprestimo
    margem_emprestimo_disponivel = margem_emprestimo_total - emprestimos_atuais
    
    # MARGEM DE CARTÃO CONSIGNADO
    margem_cartao_consig_total = base_calculo * percentual_cartao_consig
    margem_cartao_consig_disponivel = margem_cartao_consig_total - total_cartoes
    
    # MARGEM DE CARTÃO BENEFÍCIO
    margem_cartao_beneficio_total = base_calculo * percentual_cartao_beneficio
    margem_cartao_beneficio_disponivel = margem_cartao_beneficio_total - total_cartoes
    
    # Líquido recebido pelo cliente
    liquido_recebido = salario_bruto - total_descontos_obrigatorios - emprestimos_atuais - total_cartoes
    
    # Percentual de liquidez (mínimo 30%)
    percentual_liquidez = (liquido_recebido / salario_bruto * 100) if salario_bruto > 0 else 0
    
    # Validação de liquidez mínima
    aprovado_liquidez = percentual_liquidez >= 30.0
    
    return {
        'prefeitura': 'ITAITUBA',
        'salario_bruto': salario_bruto,
        'base_calculo': base_calculo,
        'descontos_compulsorios': total_descontos_obrigatorios,
        'emprestimos_atuais': emprestimos_atuais,
        'cartoes_atuais': total_cartoes,
        
        # Detalhamento de cartões
        'cartoes_nossos': cartoes_nossos,
        'cartoes_terceiros': cartoes_terceiros,
        'cartoes_nao_comprados': cartoes_nao_comprados,
        'cartoes_desconhecidos': cartoes_desconhecidos,
        
        # Margens por tipo
        'emprestimo': {
            'percentual': percentual_emprestimo,
            'margem_total': margem_emprestimo_total,
            'comprometido': emprestimos_atuais,
            'disponivel': margem_emprestimo_disponivel
        },
        'cartao_consignado': {
            'percentual': percentual_cartao_consig,
            'margem_total': margem_cartao_consig_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_consig_disponivel
        },
        'cartao_beneficio': {
            'percentual': percentual_cartao_beneficio,
            'margem_total': margem_cartao_beneficio_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_beneficio_disponivel
        },
        
        # Liquidez
        'liquido_recebido': liquido_recebido,
        'percentual_liquidez': percentual_liquidez,
        'liquidez_minima': 30.0,
        'aprovado_liquidez': aprovado_liquidez,
        
        # Status geral
        'tem_margem_emprestimo': margem_emprestimo_disponivel > 0,
        'tem_margem_cartao': margem_cartao_consig_disponivel > 0 or margem_cartao_beneficio_disponivel > 0
    }

def calcular_margem_taboao_serra(texto: str, salario_base: float, vencimentos_fixos: Dict, 
                                descontos_obrigatorios: Dict, cartoes_encontrados: Dict) -> Dict:
    """
    Calcula margem consignável para TABOÃO DA SERRA seguindo as regras da prefeitura
    
    Regras TABOÃO DA SERRA (conforme especificações):
    - Base de Cálculo: SOMA DOS PROVENTOS DE NATUREZA PERMANENTE OU FIXAS, 
      deduzindo os consignados compulsórios
    - Proventos considerados: APENAS SALÁRIO (código 0001)
    - Descontos: NÃO considerar Previdência e INSS
    - Servidor estatutário: Lic. motivo doença família podemos atuar
    
    Percentuais (padrão):
    - Empréstimo: 35%
    - Cartão Consignado: 15%
    - Cartão Benefício: 15%
    
    TODOS os cartões contam: nossos, terceiros, não comprados e desconhecidos
    """
    
    # Base de cálculo: Apenas salário base (sem adicionar outros vencimentos)
    # NÃO deduz Previdência/INSS conforme especificação
    salario_bruto = salario_base
    
    # Descontos compulsórios (EXCLUINDO Previdência e INSS)
    linhas = texto.split('\n')
    descontos_compulsorios_taboao = 0.0
    
    # Para Taboão da Serra: NÃO considerar Previdência e INSS
    # Apenas outros descontos obrigatórios (se houver)
    
    base_calculo = salario_bruto  # Sem dedução de Previdência/INSS
    
    # Percentuais de TABOÃO DA SERRA (padrão similar a POÁ)
    percentual_emprestimo = 0.35  # 35%
    percentual_cartao_consig = 0.15  # 15%
    percentual_cartao_beneficio = 0.15  # 15%
    
    # Extrai empréstimos e cartões do holerite
    emprestimos_atuais = 0.0
    
    # Separação de cartões por categoria
    cartoes_nossos = 0.0
    cartoes_terceiros = 0.0
    cartoes_nao_comprados = 0.0
    cartoes_desconhecidos = 0.0
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        # UASPREV conta como empréstimo
        if 'UASPREV' in linha_norm or 'Emprestimo STARCARD ANTICIPAY' in linha_norm:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
            continue
        
        # Verifica se é cartão (qualquer tipo)
        eh_cartao = any(kw in linha_norm for kw in ['CARTAO', 'CRED ', 'CART.', 'CARTÃO'])
        
        if eh_cartao:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                # Classifica o cartão
                if any(produto in linha_norm for produto in ['STARCARD', 'ANTICIPAY', 'STARBANK']):
                    cartoes_nossos += valor
                elif any(cartao in linha_norm for cartao in CARTOES_NAO_COMPRADOS):
                    cartoes_nao_comprados += valor
                elif any(cartao in linha_norm for cartao in CARTOES_CONHECIDOS):
                    cartoes_terceiros += valor
                else:
                    # Cartão desconhecido
                    cartoes_desconhecidos += valor
            continue
        
        # Empréstimos genéricos
        if any(termo in linha_norm for termo in ['EMPRESTIMO', 'CONSIGNADO', 'FINANCIAMENTO', 'EMPREST']):
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
    
    # Total de cartões
    total_cartoes = cartoes_nossos + cartoes_terceiros + cartoes_nao_comprados + cartoes_desconhecidos
    
    # Cálculo das margens
    margem_emprestimo_total = base_calculo * percentual_emprestimo
    margem_emprestimo_disponivel = margem_emprestimo_total - emprestimos_atuais
    
    # MARGEM DE CARTÃO CONSIGNADO (15%)
    margem_cartao_consig_total = base_calculo * percentual_cartao_consig
    margem_cartao_consig_disponivel = margem_cartao_consig_total - total_cartoes
    
    # MARGEM DE CARTÃO BENEFÍCIO (15%)
    margem_cartao_beneficio_total = base_calculo * percentual_cartao_beneficio
    margem_cartao_beneficio_disponivel = margem_cartao_beneficio_total - total_cartoes
    
    # Líquido recebido pelo cliente
    liquido_recebido = salario_bruto - descontos_compulsorios_taboao - emprestimos_atuais - total_cartoes
    
    # Percentual de liquidez (mínimo 30%)
    percentual_liquidez = (liquido_recebido / salario_bruto * 100) if salario_bruto > 0 else 0
    
    # Validação de liquidez mínima
    aprovado_liquidez = percentual_liquidez >= 30.0
    
    return {
        'prefeitura': 'TABOAO_SERRA',
        'salario_bruto': salario_bruto,
        'base_calculo': base_calculo,
        'descontos_compulsorios': descontos_compulsorios_taboao,
        'emprestimos_atuais': emprestimos_atuais,
        'cartoes_atuais': total_cartoes,
        
        # Detalhamento de cartões
        'cartoes_nossos': cartoes_nossos,
        'cartoes_terceiros': cartoes_terceiros,
        'cartoes_nao_comprados': cartoes_nao_comprados,
        'cartoes_desconhecidos': cartoes_desconhecidos,
        
        # Margens por tipo
        'emprestimo': {
            'percentual': percentual_emprestimo,
            'margem_total': margem_emprestimo_total,
            'comprometido': emprestimos_atuais,
            'disponivel': margem_emprestimo_disponivel
        },
        'cartao_consignado': {
            'percentual': percentual_cartao_consig,
            'margem_total': margem_cartao_consig_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_consig_disponivel
        },
        'cartao_beneficio': {
            'percentual': percentual_cartao_beneficio,
            'margem_total': margem_cartao_beneficio_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_beneficio_disponivel
        },
        
        # Liquidez
        'liquido_recebido': liquido_recebido,
        'percentual_liquidez': percentual_liquidez,
        'liquidez_minima': 30.0,
        'aprovado_liquidez': aprovado_liquidez,
        
        # Status geral
        'tem_margem_emprestimo': margem_emprestimo_disponivel > 0,
        'tem_margem_cartao': margem_cartao_consig_disponivel > 0 or margem_cartao_beneficio_disponivel > 0
    }

def calcular_margem_lago_verde(texto: str, salario_base: float, vencimentos_fixos: Dict, 
                              descontos_obrigatorios: Dict, cartoes_encontrados: Dict) -> Dict:
    """
    Calcula margem consignável para LAGO VERDE seguindo as regras da prefeitura
    
    Regras LAGO VERDE (conforme especificações):
    - Base de Cálculo: SOMA DOS PROVENTOS DE NATUREZA PERMANENTE OU FIXAS, 
      deduzindo os consignados compulsórios
    - Proventos considerados (códigos):
      * SALÁRIO BASE (1)
      * GRATIFIC. P/ GRADUAÇÃO (201, 202)
      * QUINQUÊNIO (204)
      * ADICIONAL NOTURNO (208)
      * ADICIONAL INSALUBRIDADE (233)
      * GAM (278)
      * GRAT.INCENTIVO P/ DESEMPENHO 10% (279)
      * SALÁRIO BASE PISO ENFERMAGEM (285)
    
    Percentuais:
    - Empréstimo: 35%
    - Cartão Consignado: 15%
    - Cartão Benefício: 15%
    
    TODOS os cartões contam: nossos, terceiros, não comprados e desconhecidos
    """
    
    # Base de cálculo: Vencimentos permanentes - Descontos obrigatórios
    salario_bruto = salario_base + vencimentos_fixos.get('total', 0.0)
    total_descontos_obrigatorios = descontos_obrigatorios.get('total', 0.0)
    
    base_calculo = salario_bruto - total_descontos_obrigatorios
    
    # Percentuais de LAGO VERDE (padrão similar a POÁ)
    percentual_emprestimo = 0.35  # 35%
    percentual_cartao_consig = 0.15  # 15%
    percentual_cartao_beneficio = 0.15  # 15%
    
    # Extrai empréstimos e cartões do holerite
    linhas = texto.split('\n')
    emprestimos_atuais = 0.0
    
    # Separação de cartões por categoria
    cartoes_nossos = 0.0
    cartoes_terceiros = 0.0
    cartoes_nao_comprados = 0.0
    cartoes_desconhecidos = 0.0
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        # UASPREV conta como empréstimo
        if 'UASPREV' in linha_norm or 'Emprestimo STARCARD ANTICIPAY' in linha_norm:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
            continue
        
        # Verifica se é cartão (qualquer tipo)
        eh_cartao = any(kw in linha_norm for kw in ['CARTAO', 'CRED ', 'CART.', 'CARTÃO'])
        
        if eh_cartao:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                # Classifica o cartão
                if any(produto in linha_norm for produto in ['STARCARD', 'ANTICIPAY', 'STARBANK']):
                    cartoes_nossos += valor
                elif any(cartao in linha_norm for cartao in CARTOES_NAO_COMPRADOS):
                    cartoes_nao_comprados += valor
                elif any(cartao in linha_norm for cartao in CARTOES_CONHECIDOS):
                    cartoes_terceiros += valor
                else:
                    # Cartão desconhecido
                    cartoes_desconhecidos += valor
            continue
        
        # Empréstimos genéricos
        if any(termo in linha_norm for termo in ['EMPRESTIMO', 'CONSIGNADO', 'FINANCIAMENTO', 'EMPREST']):
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
    
    # Total de cartões
    total_cartoes = cartoes_nossos + cartoes_terceiros + cartoes_nao_comprados + cartoes_desconhecidos
    
    # Cálculo das margens
    margem_emprestimo_total = base_calculo * percentual_emprestimo
    margem_emprestimo_disponivel = margem_emprestimo_total - emprestimos_atuais
    
    # MARGEM DE CARTÃO CONSIGNADO (15%)
    margem_cartao_consig_total = base_calculo * percentual_cartao_consig
    margem_cartao_consig_disponivel = margem_cartao_consig_total - total_cartoes
    
    # MARGEM DE CARTÃO BENEFÍCIO (15%)
    margem_cartao_beneficio_total = base_calculo * percentual_cartao_beneficio
    margem_cartao_beneficio_disponivel = margem_cartao_beneficio_total - total_cartoes
    
    # Líquido recebido pelo cliente
    liquido_recebido = salario_bruto - total_descontos_obrigatorios - emprestimos_atuais - total_cartoes
    
    # Percentual de liquidez (mínimo 30%)
    percentual_liquidez = (liquido_recebido / salario_bruto * 100) if salario_bruto > 0 else 0
    
    # Validação de liquidez mínima
    aprovado_liquidez = percentual_liquidez >= 30.0
    
    return {
        'prefeitura': 'LAGO_VERDE',
        'salario_bruto': salario_bruto,
        'base_calculo': base_calculo,
        'descontos_compulsorios': total_descontos_obrigatorios,
        'emprestimos_atuais': emprestimos_atuais,
        'cartoes_atuais': total_cartoes,
        
        # Detalhamento de cartões
        'cartoes_nossos': cartoes_nossos,
        'cartoes_terceiros': cartoes_terceiros,
        'cartoes_nao_comprados': cartoes_nao_comprados,
        'cartoes_desconhecidos': cartoes_desconhecidos,
        
        # Margens por tipo
        'emprestimo': {
            'percentual': percentual_emprestimo,
            'margem_total': margem_emprestimo_total,
            'comprometido': emprestimos_atuais,
            'disponivel': margem_emprestimo_disponivel
        },
        'cartao_consignado': {
            'percentual': percentual_cartao_consig,
            'margem_total': margem_cartao_consig_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_consig_disponivel
        },
        'cartao_beneficio': {
            'percentual': percentual_cartao_beneficio,
            'margem_total': margem_cartao_beneficio_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_beneficio_disponivel
        },
        
        # Liquidez
        'liquido_recebido': liquido_recebido,
        'percentual_liquidez': percentual_liquidez,
        'liquidez_minima': 30.0,
        'aprovado_liquidez': aprovado_liquidez,
        
        # Status geral
        'tem_margem_emprestimo': margem_emprestimo_disponivel > 0,
        'tem_margem_cartao': margem_cartao_consig_disponivel > 0 or margem_cartao_beneficio_disponivel > 0
    }

def calcular_margem_hortolandia(texto: str, salario_base: float, vencimentos_fixos: Dict,
                                  descontos_obrigatorios: Dict, cartoes_encontrados: Dict) -> Dict:
    """
    Calcula margem consignável para HORTOLÂNDIA seguindo as regras da prefeitura.

    Regras HORTOLÂNDIA:
    - Base de Cálculo: Soma dos proventos de natureza permanente ou fixas,
      deduzindo os consignados compulsórios (Art. 3°)
    - Proventos considerados: SALARIO, ADICIONAL POR TEMPO, SEXTA PARTE,
      GRAT. FIXA, INSALUBRIDADE
    - Descontos compulsórios: Previdência, IRRF, Pensão alimentícia judicial,
      Descontos por decisão judicial, Obrigações decorrentes de decisão judicial
      ou administrativa, Reposição e indenização ao erário

    Percentuais:
    - Empréstimo:          35%
    - Cartão Consignado:   15%
    - Cartão Benefício:    15%

    TODOS os cartões contam: nossos, terceiros, não comprados e desconhecidos.
    """

    # Base de cálculo: somente proventos permanentes/fixos conforme especificação.
    # NÃO inclui horas_extras (não é provento de natureza permanente).
    proventos_permanentes = (
        salario_base
        + vencimentos_fixos.get('adicional_tempo_servico', 0.0)
        + vencimentos_fixos.get('sexta_parte', 0.0)
        + vencimentos_fixos.get('gratificacao', 0.0)
        + vencimentos_fixos.get('insalubridade', 0.0)
    )

    total_descontos_obrigatorios = descontos_obrigatorios.get('total', 0.0)

    base_calculo = proventos_permanentes - total_descontos_obrigatorios

    # Percentuais de HORTOLÂNDIA
    percentual_emprestimo       = 0.35  # 35%
    percentual_cartao_consig    = 0.15  # 15%
    percentual_cartao_beneficio = 0.15  # 15%

    # Extrai empréstimos e cartões do holerite
    linhas = texto.split('\n')
    emprestimos_atuais   = 0.0
    cartoes_nossos       = 0.0
    cartoes_terceiros    = 0.0
    cartoes_nao_comprados = 0.0
    cartoes_desconhecidos = 0.0

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # UASPREV / ANTICIPAY conta como empréstimo
        if 'UASPREV' in linha_norm or 'EMPRESTIMO STARCARD ANTICIPAY' in linha_norm:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
            continue

        # Verifica se é cartão (qualquer tipo)
        eh_cartao = any(kw in linha_norm for kw in ['CARTAO', 'CRED ', 'CART.'])

        if eh_cartao:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                if any(produto in linha_norm for produto in ['STARCARD', 'ANTICIPAY', 'STARBANK']):
                    cartoes_nossos += valor
                elif any(cartao in linha_norm for cartao in CARTOES_NAO_COMPRADOS):
                    cartoes_nao_comprados += valor
                elif any(cartao in linha_norm for cartao in CARTOES_CONHECIDOS):
                    cartoes_terceiros += valor
                else:
                    cartoes_desconhecidos += valor
            continue

        # Empréstimos genéricos (que não são cartões)
        if any(termo in linha_norm for termo in ['EMPRESTIMO', 'CONSIGNADO', 'FINANCIAMENTO', 'EMPREST']):
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor

    # Total de cartões (TODOS contam)
    total_cartoes = cartoes_nossos + cartoes_terceiros + cartoes_nao_comprados + cartoes_desconhecidos

    # Cálculo das margens
    margem_emprestimo_total       = base_calculo * percentual_emprestimo
    margem_emprestimo_disponivel  = margem_emprestimo_total - emprestimos_atuais

    margem_cartao_consig_total       = base_calculo * percentual_cartao_consig
    margem_cartao_consig_disponivel  = margem_cartao_consig_total - total_cartoes

    margem_cartao_beneficio_total       = base_calculo * percentual_cartao_beneficio
    margem_cartao_beneficio_disponivel  = margem_cartao_beneficio_total - total_cartoes

    # Líquido recebido pelo servidor
    liquido_recebido = proventos_permanentes - total_descontos_obrigatorios - emprestimos_atuais - total_cartoes

    percentual_liquidez = (liquido_recebido / proventos_permanentes * 100) if proventos_permanentes > 0 else 0
    aprovado_liquidez   = percentual_liquidez >= 30.0

    return {
        'prefeitura': 'HORTOLANDIA',
        'salario_bruto': proventos_permanentes,
        'base_calculo': base_calculo,
        'descontos_compulsorios': total_descontos_obrigatorios,
        'emprestimos_atuais': emprestimos_atuais,
        'cartoes_atuais': total_cartoes,

        # Detalhamento de cartões
        'cartoes_nossos': cartoes_nossos,
        'cartoes_terceiros': cartoes_terceiros,
        'cartoes_nao_comprados': cartoes_nao_comprados,
        'cartoes_desconhecidos': cartoes_desconhecidos,

        # Margens por tipo
        'emprestimo': {
            'percentual': percentual_emprestimo,
            'margem_total': margem_emprestimo_total,
            'comprometido': emprestimos_atuais,
            'disponivel': margem_emprestimo_disponivel
        },
        'cartao_consignado': {
            'percentual': percentual_cartao_consig,
            'margem_total': margem_cartao_consig_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_consig_disponivel
        },
        'cartao_beneficio': {
            'percentual': percentual_cartao_beneficio,
            'margem_total': margem_cartao_beneficio_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_beneficio_disponivel
        },

        # Liquidez
        'liquido_recebido': liquido_recebido,
        'percentual_liquidez': percentual_liquidez,
        'liquidez_minima': 30.0,
        'aprovado_liquidez': aprovado_liquidez,

        # Status geral
        'tem_margem_emprestimo': margem_emprestimo_disponivel > 0,
        'tem_margem_cartao': margem_cartao_consig_disponivel > 0 or margem_cartao_beneficio_disponivel > 0
    }

def calcular_margem_bauru(texto: str, salario_base: float, vencimentos_fixos: Dict,
                           descontos_obrigatorios: Dict, cartoes_encontrados: Dict) -> Dict:
    """
    Calcula margem consignável para BAURU seguindo as regras da prefeitura.

    Proventos permanentes (base de cálculo):
    SALÁRIO BASE, BIENIO, SEXTA PARTE, VANT PESS VL,
    VANT PE L25/17, ATIV TRAB PEDAG

    Descontos compulsórios:
    IRRF, PREVIDÊNCIA, PLANO DE SAUDE

    Percentuais:
    - Empréstimo:          35%
    - Cartão Consignado:   15%
    - Cartão Benefício:    15%

    TODOS os cartões contam: nossos, terceiros, não comprados e desconhecidos.
    """

    # Proventos permanentes conforme especificação de Bauru
    proventos_permanentes = (
        salario_base
        + vencimentos_fixos.get('adicional_tempo_servico', 0.0)  # BIENIO
        + vencimentos_fixos.get('sexta_parte', 0.0)
        + vencimentos_fixos.get('vantagens_pessoais', 0.0)       # VANT PESS VL + VANT PE L25/17
        + vencimentos_fixos.get('ativ_trab_pedag', 0.0)
    )

    # Descontos compulsórios: IRRF + Previdência (globais) + Plano de Saúde (específico Bauru)
    plano_saude = 0.0
    linhas = texto.split('\n')
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if any(kw in linha_norm for kw in ['PL SAUDE', 'PLANO SAUDE', 'PLANO DE SAUDE', 'HAPVID']):
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                plano_saude += valor

    total_descontos_obrigatorios = descontos_obrigatorios.get('total', 0.0) + plano_saude

    base_calculo = proventos_permanentes - total_descontos_obrigatorios

    # Percentuais de BAURU
    percentual_emprestimo       = 0.35  # 35%
    percentual_cartao_consig    = 0.15  # 15%
    percentual_cartao_beneficio = 0.15  # 15%

    # Extrai empréstimos e cartões do holerite
    emprestimos_atuais    = 0.0
    cartoes_nossos        = 0.0
    cartoes_terceiros     = 0.0
    cartoes_nao_comprados = 0.0
    cartoes_desconhecidos = 0.0

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # UASPREV / ANTICIPAY conta como empréstimo
        if 'UASPREV' in linha_norm or 'EMPRESTIMO STARCARD ANTICIPAY' in linha_norm:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
            continue

        # Ignora linhas de Plano de Saúde já contabilizadas como desconto compulsório
        if any(kw in linha_norm for kw in ['PL SAUDE', 'PLANO SAUDE', 'PLANO DE SAUDE', 'HAPVID']):
            continue

        # Verifica se é cartão
        eh_cartao = any(kw in linha_norm for kw in ['CARTAO', 'CRED ', 'CART.'])

        if eh_cartao:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                if any(produto in linha_norm for produto in ['STARCARD', 'ANTICIPAY', 'STARBANK']):
                    cartoes_nossos += valor
                elif any(cartao in linha_norm for cartao in CARTOES_NAO_COMPRADOS):
                    cartoes_nao_comprados += valor
                elif any(cartao in linha_norm for cartao in CARTOES_CONHECIDOS):
                    cartoes_terceiros += valor
                else:
                    cartoes_desconhecidos += valor
            continue

        # Empréstimos genéricos (que não são cartões)
        if any(termo in linha_norm for termo in ['EMPRESTIMO', 'CONSIGNADO', 'FINANCIAMENTO', 'EMPREST']):
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor

    # Total de cartões (TODOS contam)
    total_cartoes = cartoes_nossos + cartoes_terceiros + cartoes_nao_comprados + cartoes_desconhecidos

    # Cálculo das margens
    margem_emprestimo_total      = base_calculo * percentual_emprestimo
    margem_emprestimo_disponivel = margem_emprestimo_total - emprestimos_atuais

    margem_cartao_consig_total      = base_calculo * percentual_cartao_consig
    margem_cartao_consig_disponivel = margem_cartao_consig_total - total_cartoes

    margem_cartao_beneficio_total      = base_calculo * percentual_cartao_beneficio
    margem_cartao_beneficio_disponivel = margem_cartao_beneficio_total - total_cartoes

    # Líquido recebido pelo servidor
    liquido_recebido = proventos_permanentes - total_descontos_obrigatorios - emprestimos_atuais - total_cartoes

    percentual_liquidez = (liquido_recebido / proventos_permanentes * 100) if proventos_permanentes > 0 else 0
    aprovado_liquidez   = percentual_liquidez >= 30.0

    return {
        'prefeitura': 'BAURU',
        'salario_bruto': proventos_permanentes,
        'base_calculo': base_calculo,
        'descontos_compulsorios': total_descontos_obrigatorios,
        'plano_saude': plano_saude,
        'emprestimos_atuais': emprestimos_atuais,
        'cartoes_atuais': total_cartoes,

        # Detalhamento de cartões
        'cartoes_nossos': cartoes_nossos,
        'cartoes_terceiros': cartoes_terceiros,
        'cartoes_nao_comprados': cartoes_nao_comprados,
        'cartoes_desconhecidos': cartoes_desconhecidos,

        # Margens por tipo
        'emprestimo': {
            'percentual': percentual_emprestimo,
            'margem_total': margem_emprestimo_total,
            'comprometido': emprestimos_atuais,
            'disponivel': margem_emprestimo_disponivel
        },
        'cartao_consignado': {
            'percentual': percentual_cartao_consig,
            'margem_total': margem_cartao_consig_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_consig_disponivel
        },
        'cartao_beneficio': {
            'percentual': percentual_cartao_beneficio,
            'margem_total': margem_cartao_beneficio_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_beneficio_disponivel
        },

        # Liquidez
        'liquido_recebido': liquido_recebido,
        'percentual_liquidez': percentual_liquidez,
        'liquidez_minima': 30.0,
        'aprovado_liquidez': aprovado_liquidez,

        # Status geral
        'tem_margem_emprestimo': margem_emprestimo_disponivel > 0,
        'tem_margem_cartao': margem_cartao_consig_disponivel > 0 or margem_cartao_beneficio_disponivel > 0
    }

def calcular_margem_embu(texto: str, salario_base: float, vencimentos_fixos: Dict, 
                         descontos_obrigatorios: Dict, cartoes_encontrados: Dict) -> Dict:
    """
    Calcula margem consignável para EMBU DAS ARTES seguindo as regras da planilha
    
    Regras EMBU DAS ARTES:
    - Base: Proventos de natureza permanente - Consignações compulsórias
    - Empréstimo: 35%
    - Cartão Consignado: 5%
    - Cartão Benefício: 5%
    
    TODOS os cartões contam: nossos, terceiros, não comprados e desconhecidos
    """
    
    # Base de cálculo: Vencimentos permanentes - Descontos obrigatórios
    salario_bruto = salario_base + vencimentos_fixos.get('total', 0.0)
    total_descontos_obrigatorios = descontos_obrigatorios.get('total', 0.0)
    
    base_calculo = salario_bruto - total_descontos_obrigatorios
    
    # Percentuais de EMBU
    percentual_emprestimo = 0.35  # 35%
    percentual_cartao_consig = 0.05  # 5%
    percentual_cartao_beneficio = 0.05  # 5%
    
    # Extrai empréstimos e cartões do holerite
    linhas = texto.split('\n')
    emprestimos_atuais = 0.0
    
    # Separação de cartões por categoria
    cartoes_nossos = 0.0
    cartoes_terceiros = 0.0
    cartoes_nao_comprados = 0.0
    cartoes_desconhecidos = 0.0
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        # UASPREV conta como empréstimo
        if 'UASPREV' in linha_norm or 'Emprestimo STARCARD ANTICIPAY' in linha_norm:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
            continue
        
        # Verifica se é cartão
        eh_cartao = any(kw in linha_norm for kw in ['CARTAO', 'CRED ', 'CART.', 'CARTÃO'])
        
        if eh_cartao:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                # Classifica o cartão
                if any(produto in linha_norm for produto in ['STARCARD', 'ANTICIPAY', 'STARBANK', 'UASPREV']):
                    cartoes_nossos += valor
                elif any(cartao in linha_norm for cartao in CARTOES_NAO_COMPRADOS):
                    cartoes_nao_comprados += valor
                elif any(cartao in linha_norm for cartao in CARTOES_CONHECIDOS):
                    cartoes_terceiros += valor
                else:
                    cartoes_desconhecidos += valor
            continue
        
        # Empréstimos genéricos
        if any(termo in linha_norm for termo in ['EMPRESTIMO', 'CONSIGNADO', 'FINANCIAMENTO', 'EMPREST']):
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
    
    # Total de cartões
    total_cartoes = cartoes_nossos + cartoes_terceiros + cartoes_nao_comprados + cartoes_desconhecidos
    
    # Cálculo das margens
    margem_emprestimo_total = base_calculo * percentual_emprestimo
    margem_emprestimo_disponivel = margem_emprestimo_total - emprestimos_atuais
    
    # MARGEM DE CARTÃO CONSIGNADO (5%)
    margem_cartao_consig_total = base_calculo * percentual_cartao_consig
    margem_cartao_consig_disponivel = margem_cartao_consig_total - total_cartoes
    
    # MARGEM DE CARTÃO BENEFÍCIO (5%)
    margem_cartao_beneficio_total = base_calculo * percentual_cartao_beneficio
    margem_cartao_beneficio_disponivel = margem_cartao_beneficio_total - total_cartoes
    
    # Líquido recebido pelo cliente
    liquido_recebido = salario_bruto - total_descontos_obrigatorios - emprestimos_atuais - total_cartoes
    
    # Percentual de liquidez (mínimo 30%)
    percentual_liquidez = (liquido_recebido / salario_bruto * 100) if salario_bruto > 0 else 0
    
    # Validação de liquidez mínima
    aprovado_liquidez = percentual_liquidez >= 30.0
    
    return {
        'prefeitura': 'EMBU',
        'salario_bruto': salario_bruto,
        'base_calculo': base_calculo,
        'descontos_compulsorios': total_descontos_obrigatorios,
        'emprestimos_atuais': emprestimos_atuais,
        'cartoes_atuais': total_cartoes,
        
        # Detalhamento de cartões
        'cartoes_nossos': cartoes_nossos,
        'cartoes_terceiros': cartoes_terceiros,
        'cartoes_nao_comprados': cartoes_nao_comprados,
        'cartoes_desconhecidos': cartoes_desconhecidos,
        
        # Margens por tipo
        'emprestimo': {
            'percentual': percentual_emprestimo,
            'margem_total': margem_emprestimo_total,
            'comprometido': emprestimos_atuais,
            'disponivel': margem_emprestimo_disponivel
        },
        'cartao_consignado': {
            'percentual': percentual_cartao_consig,
            'margem_total': margem_cartao_consig_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_consig_disponivel
        },
        'cartao_beneficio': {
            'percentual': percentual_cartao_beneficio,
            'margem_total': margem_cartao_beneficio_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_beneficio_disponivel
        },
        
        # Liquidez
        'liquido_recebido': liquido_recebido,
        'percentual_liquidez': percentual_liquidez,
        'liquidez_minima': 30.0,
        'aprovado_liquidez': aprovado_liquidez,
        
        # Status geral
        'tem_margem_emprestimo': margem_emprestimo_disponivel > 0,
        'tem_margem_cartao': margem_cartao_consig_disponivel > 0 or margem_cartao_beneficio_disponivel > 0
    }

def calcular_margem_cotia(texto: str, salario_base: float, vencimentos_fixos: Dict, 
                          descontos_obrigatorios: Dict, cartoes_encontrados: Dict) -> Dict:
    """
    Calcula margem consignável para COTIA seguindo as regras da planilha
    
    Regras COTIA:
    - Empréstimo: 35%
    - Cartão Consignado: 5%
    - Cartão Benefício: 0%
    
    Fórmula: Base de Cálculo = Salário Bruto - Descontos Compulsórios
    
    TODOS os cartões contam: nossos, terceiros, não comprados e desconhecidos
    """
    
    # Base de cálculo: Vencimentos totais - Descontos obrigatórios
    salario_bruto = salario_base + vencimentos_fixos.get('total', 0.0)
    total_descontos_obrigatorios = descontos_obrigatorios.get('total', 0.0)
    
    base_calculo = salario_bruto - total_descontos_obrigatorios
    
    # Percentuais de COTIA
    percentual_emprestimo = 0.35  # 35%
    percentual_cartao_consig = 0.05  # 5%
    percentual_cartao_beneficio = 0.0  # 0%
    
    # Extrai empréstimos e cartões do holerite
    linhas = texto.split('\n')
    emprestimos_atuais = 0.0
    
    # Separação de cartões por categoria
    cartoes_nossos = 0.0
    cartoes_terceiros = 0.0
    cartoes_nao_comprados = 0.0
    cartoes_desconhecidos = 0.0
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        if 'Emprestimo STARCARD ANTICIPAY' in linha_norm:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
            continue
        
        # Verifica se é cartão
        eh_cartao = any(kw in linha_norm for kw in ['CARTAO', 'CRED ', 'CART.', 'CARTÃO UASPREV'])
        
        if eh_cartao:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                # Classifica o cartão
                if any(produto in linha_norm for produto in ['STARCARD', 'ANTICIPAY', 'STARBANK', 'UASPREV', 'CARTÃO UASPREV']):
                    cartoes_nossos += valor
                elif any(cartao in linha_norm for cartao in CARTOES_NAO_COMPRADOS):
                    cartoes_nao_comprados += valor
                elif any(cartao in linha_norm for cartao in CARTOES_CONHECIDOS):
                    cartoes_terceiros += valor
                else:
                    cartoes_desconhecidos += valor
            continue
        
        # Empréstimos genéricos
        if any(termo in linha_norm for termo in ['EMPRESTIMO', 'CONSIGNADO', 'FINANCIAMENTO', 'EMPREST']):
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
    
    # Total de cartões
    total_cartoes = cartoes_nossos + cartoes_terceiros + cartoes_nao_comprados + cartoes_desconhecidos
    
    # Cálculo das margens
    margem_emprestimo_total = base_calculo * percentual_emprestimo
    margem_emprestimo_disponivel = margem_emprestimo_total - emprestimos_atuais
    
    # MARGEM DE CARTÃO CONSIGNADO (10%)
    margem_cartao_consig_total = base_calculo * percentual_cartao_consig
    margem_cartao_consig_disponivel = margem_cartao_consig_total - total_cartoes
    
    # MARGEM DE CARTÃO BENEFÍCIO (5%)
    margem_cartao_beneficio_total = base_calculo * percentual_cartao_beneficio
    margem_cartao_beneficio_disponivel = margem_cartao_beneficio_total - total_cartoes
    
    # Líquido recebido pelo cliente
    liquido_recebido = salario_bruto - total_descontos_obrigatorios - emprestimos_atuais - total_cartoes
    
    # Percentual de liquidez (mínimo 30%)
    percentual_liquidez = (liquido_recebido / salario_bruto * 100) if salario_bruto > 0 else 0
    
    # Validação de liquidez mínima
    aprovado_liquidez = percentual_liquidez >= 30.0
    
    return {
        'prefeitura': 'COTIA',
        'salario_bruto': salario_bruto,
        'base_calculo': base_calculo,
        'descontos_compulsorios': total_descontos_obrigatorios,
        'emprestimos_atuais': emprestimos_atuais,
        'cartoes_atuais': total_cartoes,
        
        # Detalhamento de cartões
        'cartoes_nossos': cartoes_nossos,
        'cartoes_terceiros': cartoes_terceiros,
        'cartoes_nao_comprados': cartoes_nao_comprados,
        'cartoes_desconhecidos': cartoes_desconhecidos,
        
        # Margens por tipo
        'emprestimo': {
            'percentual': percentual_emprestimo,
            'margem_total': margem_emprestimo_total,
            'comprometido': emprestimos_atuais,
            'disponivel': margem_emprestimo_disponivel
        },
        'cartao_consignado': {
            'percentual': percentual_cartao_consig,
            'margem_total': margem_cartao_consig_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_consig_disponivel
        },
        'cartao_beneficio': {
            'percentual': percentual_cartao_beneficio,
            'margem_total': margem_cartao_beneficio_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_beneficio_disponivel
        },
        
        # Liquidez
        'liquido_recebido': liquido_recebido,
        'percentual_liquidez': percentual_liquidez,
        'liquidez_minima': 30.0,
        'aprovado_liquidez': aprovado_liquidez,
        
        # Status geral
        'tem_margem_emprestimo': margem_emprestimo_disponivel > 0,
        'tem_margem_cartao': margem_cartao_consig_disponivel > 0 or margem_cartao_beneficio_disponivel > 0
    }

def calcular_margem_maringa(texto: str, salario_base: float, vencimentos_fixos: Dict, 
                            descontos_obrigatorios: Dict, cartoes_encontrados: Dict) -> Dict:
    """
    Calcula margem consignável para MARINGÁ seguindo as regras específicas
    
    Regras MARINGÁ:
    - Base de cálculo: APENAS Salário Base (não soma vencimentos fixos!)
    - Descontos compulsórios são subtraídos normalmente
    - Empréstimo: 35%
    - Cartão Consignado: 10%
    - Cartão Benefício: 0%
    
    TODOS os cartões contam: nossos, terceiros, não comprados e desconhecidos
    """
    
    # Percentuais de MARINGÁ (CONFIRMADOS)
    percentual_emprestimo = 0.35  # 35%
    percentual_cartao_consig = 0.10  # 10%
    percentual_cartao_beneficio = 0.0  # 0%
    
    # Base de cálculo MARINGÁ: APENAS Salário Base - Descontos Compulsórios
    # (NÃO soma vencimentos fixos como POA/Cotia)
    total_descontos_obrigatorios = descontos_obrigatorios.get('total', 0.0)
    base_calculo = salario_base - total_descontos_obrigatorios
    
    # Extrai empréstimos e cartões do holerite
    linhas = texto.split('\n')
    emprestimos_atuais = 0.0
    
    # Separação de cartões por categoria
    cartoes_nossos = 0.0
    cartoes_terceiros = 0.0
    cartoes_nao_comprados = 0.0
    cartoes_desconhecidos = 0.0
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        if 'Emprestimo STARCARD ANTICIPAY' in linha_norm:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
            continue
        
        # Verifica se é cartão
        eh_cartao = any(kw in linha_norm for kw in ['CARTAO', 'CRED ', 'CART.', 'CARTÃO'])
        
        if eh_cartao:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                # Classifica o cartão
                if any(produto in linha_norm for produto in ['STARCARD', 'ANTICIPAY', 'STARBANK', 'UASPREV']):
                    cartoes_nossos += valor
                elif any(cartao in linha_norm for cartao in CARTOES_NAO_COMPRADOS):
                    cartoes_nao_comprados += valor
                elif any(cartao in linha_norm for cartao in CARTOES_CONHECIDOS):
                    cartoes_terceiros += valor
                else:
                    cartoes_desconhecidos += valor
            continue
        
        # Empréstimos genéricos
        if any(termo in linha_norm for termo in ['EMPRESTIMO', 'CONSIGNADO', 'FINANCIAMENTO', 'EMPREST']):
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                emprestimos_atuais += valor
    
    # Total de cartões
    total_cartoes = cartoes_nossos + cartoes_terceiros + cartoes_nao_comprados + cartoes_desconhecidos
    
    # Cálculo das margens
    margem_emprestimo_total = base_calculo * percentual_emprestimo
    margem_emprestimo_disponivel = margem_emprestimo_total - emprestimos_atuais
    
    margem_cartao_consig_total = base_calculo * percentual_cartao_consig
    margem_cartao_consig_disponivel = margem_cartao_consig_total - total_cartoes
    
    margem_cartao_beneficio_total = base_calculo * percentual_cartao_beneficio
    margem_cartao_beneficio_disponivel = margem_cartao_beneficio_total - total_cartoes
    
    # Líquido recebido pelo cliente
    salario_bruto = salario_base  # Em Maringá, salário bruto = salário base
    liquido_recebido = salario_bruto - total_descontos_obrigatorios - emprestimos_atuais - total_cartoes
    
    # Percentual de liquidez (mínimo 30%)
    percentual_liquidez = (liquido_recebido / salario_bruto * 100) if salario_bruto > 0 else 0
    
    # Validação de liquidez mínima
    aprovado_liquidez = percentual_liquidez >= 30.0
    
    return {
        'prefeitura': 'MARINGA',
        'salario_bruto': salario_bruto,
        'base_calculo': base_calculo,
        'descontos_compulsorios': total_descontos_obrigatorios,
        'emprestimos_atuais': emprestimos_atuais,
        'cartoes_atuais': total_cartoes,
        
        # Detalhamento de cartões
        'cartoes_nossos': cartoes_nossos,
        'cartoes_terceiros': cartoes_terceiros,
        'cartoes_nao_comprados': cartoes_nao_comprados,
        'cartoes_desconhecidos': cartoes_desconhecidos,
        
        # Margens por tipo
        'emprestimo': {
            'percentual': percentual_emprestimo,
            'margem_total': margem_emprestimo_total,
            'comprometido': emprestimos_atuais,
            'disponivel': margem_emprestimo_disponivel
        },
        'cartao_consignado': {
            'percentual': percentual_cartao_consig,
            'margem_total': margem_cartao_consig_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_consig_disponivel
        },
        'cartao_beneficio': {
            'percentual': percentual_cartao_beneficio,
            'margem_total': margem_cartao_beneficio_total,
            'comprometido': total_cartoes,
            'disponivel': margem_cartao_beneficio_disponivel
        },
        
        # Liquidez
        'liquido_recebido': liquido_recebido,
        'percentual_liquidez': percentual_liquidez,
        'liquidez_minima': 30.0,
        'aprovado_liquidez': aprovado_liquidez,
        
        # Status geral
        'tem_margem_emprestimo': margem_emprestimo_disponivel > 0,
        'tem_margem_cartao': margem_cartao_consig_disponivel > 0 or margem_cartao_beneficio_disponivel > 0
    }

# ============================================================================
# FUNÇÕES ESPECÍFICAS POR PREFEITURA - MARINGÁ
# ============================================================================

def extrair_informacoes_maringa(texto: str) -> Dict:
    """
    Extrai informações específicas de Maringá
    Separa corretamente nome, matrícula e salário líquido
    """
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
    }
    
    linhas = texto.split('\n')
    
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        
        # Busca por "NOME" e extrai a próxima linha APENAS para o nome
        if 'NOME' in linha_norm and i + 1 < len(linhas):
            nome_linha = linhas[i + 1].strip()
            # Tenta extrair apenas o nome (sem números no início)
            match = re.search(r'([A-ZÁÀÃÂÉÈÊÍÏÓÔÕÖÚÇÑ\s]+)', nome_linha)
            if match:
                info['nome'] = match.group(1).strip()
        
        # Busca por "MATRICULA" - extrai APENAS o número
        if 'MATRICULA' in linha_norm:
            # Tenta extrair matrícula da mesma linha
            match = re.search(r'(\d{4,8})', linha)
            if match:
                info['matricula'] = match.group(1)
            # Se não encontrou, tenta próxima linha
            elif i + 1 < len(linhas):
                match = re.search(r'(\d{4,8})', linhas[i + 1])
                if match:
                    info['matricula'] = match.group(1)
        
        # Busca por VENCIMENTOS (total)
        if 'VENCIMENTOS' in linha_norm and 'DESCONTOS' not in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                valor_str = valores[-1].replace('.', '').replace(',', '.')
                info['vencimentos_total'] = float(valor_str)
        
        # Busca por DESCONTOS (total)
        if 'DESCONTOS' in linha_norm and 'VENCIMENTOS' not in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                valor_str = valores[-1].replace('.', '').replace(',', '.')
                info['descontos_total'] = float(valor_str)
    
    # Estratégia 1: Buscar "SALARIO NORMAL" como vencimento
    if info['liquido'] == 0.0:
        for linha in linhas:
            linha_norm = normalizar_texto(linha)
            if 'SALARIO NORMAL' in linha_norm:
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
                if valores:
                    valor_str = valores[-1].replace('.', '').replace(',', '.')
                    info['liquido'] = float(valor_str)
                    break
    
    # Estratégia 2: Buscar "SALARIO BASE" e pegar o primeiro valor abaixo
    if info['liquido'] == 0.0:
        for i, linha in enumerate(linhas):
            linha_norm = normalizar_texto(linha)
            if 'SALARIO BASE' in linha_norm:
                # Procura pelo próximo valor numérico nas linhas seguintes
                for j in range(i + 1, min(i + 5, len(linhas))):
                    valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linhas[j])
                    if valores:
                        valor_str = valores[0].replace('.', '').replace(',', '.')
                        info['liquido'] = float(valor_str)
                        break
                if info['liquido'] > 0.0:
                    break
    
    return info

def extrair_salario_bruto_maringa(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque de MARINGÁ
    Busca por "SALARIO NORMAL" na coluna de vencimentos
    """
    linhas = texto.split('\n')
    
    # Buscar "SALARIO NORMAL" no holerite de Maringá
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        if 'SALARIO NORMAL' in linha_norm:
            valor = extrair_valores_vencimento_maringa(linha)  # ← USA A FUNÇÃO ESPECÍFICA
            if valor > 0:
                return valor
    
    # Fallback: Buscar primeiro vencimento significativo
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'VENCIMENTOS' in linha_norm or 'REFERENCIA' in linha_norm:
            valor = extrair_valores_vencimento_maringa(linha)  # ← USA A FUNÇÃO ESPECÍFICA
            if valor > 0:
                return valor
    
    return 0.0

def extrair_vencimentos_fixos_maringa(texto: str) -> Dict:
    """
    Extrai vencimentos de MARINGÁ da coluna de VENCIMENTOS
    Estrutura: CÓD | DESCRIÇÃO | REFERÊNCIA | VENCIMENTOS | DESCONTOS
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'adicional_tempo_servico': 0.0,
        'gratificacao': 0.0,
        'hora_ativ_extra_classe': 0.0,
        'aula_suplementar': 0.0,
        'vale_alimentacao': 0.0,
        'sexta_parte': 0.0,
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # SALARIO NORMAL (vencimento base em Maringá)
        if 'SALARIO NORMAL' in linha_norm:
            valor = extrair_valores_vencimento_maringa(linha)  # ← USA A FUNÇÃO ESPECÍFICA
            if valor > 0:
                vencimentos_fixos['vencimento_base'] = valor
                vencimentos_fixos['total'] += valor
            continue



    return vencimentos_fixos

# ============================================================================
# FUNÇÕES ESPECÍFICAS POR PREFEITURA - SOROCABA
# ============================================================================

def extrair_informacoes_sorocaba(texto: str) -> Dict:
    """
    Extrai informações específicas de Sorocaba
    Separa corretamente matrícula, nome e salário líquido
    Estrutura: MATRÍCULA / NOME / VALOR TOTAL LÍQUIDO
    """
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
    }
    
    linhas = texto.split('\n')
    
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        
        # Busca por "MATRICULA" - extrai APENAS o número
        if 'MATRICULA' in linha_norm:
            match = re.search(r'(\d{4,8})', linha)
            if match:
                info['matricula'] = match.group(1)
            elif i + 1 < len(linhas):
                match = re.search(r'(\d{4,8})', linhas[i + 1])
                if match:
                    info['matricula'] = match.group(1)
        
        # Busca por "NOME" - extrai a próxima linha APENAS para o nome
        if 'NOME' in linha_norm and i + 1 < len(linhas):
            nome_linha = linhas[i + 1].strip()
            match = re.search(r'([A-ZÁÀÃÂÉÈÊÍÏÓÔÕÖÚÇÑ\s]+)', nome_linha)
            if match:
                info['nome'] = match.group(1).strip()
        
        # Busca por "VENCIMENTOS" (total)
        if 'VENCIMENTOS' in linha_norm and 'DESCONTOS' not in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                valor_str = valores[-1].replace('.', '').replace(',', '.')
                info['vencimentos_total'] = float(valor_str)
        
        # Busca por "DESCONTOS" (total)
        if 'DESCONTOS' in linha_norm and 'VENCIMENTOS' not in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                valor_str = valores[-1].replace('.', '').replace(',', '.')
                info['descontos_total'] = float(valor_str)
    
    # Estratégia 1: Buscar "VALOR TOTAL LIQUIDO" na linha
    if info['liquido'] == 0.0:
        for linha in linhas:
            linha_norm = normalizar_texto(linha)
            if 'VALOR TOTAL LIQUIDO' in linha_norm or 'VALOR TOTAL LÍQUIDO' in linha_norm:
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
                if valores:
                    valor_str = valores[-1].replace('.', '').replace(',', '.')
                    info['liquido'] = float(valor_str)
                    break
    
    # Estratégia 2: Buscar linha com "VENCIMENTO BASE" e pegar valor
    if info['liquido'] == 0.0:
        for i, linha in enumerate(linhas):
            linha_norm = normalizar_texto(linha)
            if 'VENCIMENTO BASE' in linha_norm or 'REMUNERACAO' in linha_norm:
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
                if valores:
                    valor_str = valores[-1].replace('.', '').replace(',', '.')
                    info['liquido'] = float(valor_str)
                    break
    
    return info

def extrair_salario_bruto_sorocaba(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque de SOROCABA
    Busca por "VENCIMENTO BASE" na coluna de vencimentos
    """
    linhas = texto.split('\n')
    
    # Buscar "VENCIMENTO BASE" ou similar
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'VENCIMENTO' in linha_norm or 'REMUNERACAO' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    # Fallback: Buscar primeiro vencimento significativo
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'VENCIMENTOS' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    return 0.0

def extrair_vencimentos_fixos_sorocaba(texto: str) -> Dict:
    """
    Extrai vencimentos de SOROCABA da coluna de VENCIMENTOS
    Estrutura: CÓD | DESCRIÇÃO | VENCIMENTOS | DESCONTOS
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'adicional_tempo_servico': 0.0,
        'adicional_insalubridade': 0.0,
        'gratificacao': 0.0,
        'hora_ativ_extra_classe': 0.0,
        'aula_suplementar': 0.0,
        'sexta_parte': 0.0,
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # VENCIMENTO BASE / REMUNERAÇÃO
        if 'VENCIMENTO' in linha_norm and 'BASE' in linha_norm or 'REMUNERACAO' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['vencimento_base'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # ADICIONAL DE TEMPO
        if 'ADIC.TEMPO SERVICO' in linha_norm and 'TEMPO' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['adicional_tempo_servico'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # ADICIONAL INSALUBRIDADE
        if 'ADIC. INSALUBRIDADE' in linha_norm and 'INSALUBRIDADE' in linha_norm and 'DESCONTO' not in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['adicional_insalubridade'] = valor
                vencimentos_fixos['total'] += valor
            continue

    return vencimentos_fixos

# ============================================================================
# FUNÇÕES ESPECÍFICAS POR PREFEITURA - COTIA
# ============================================================================

def extrair_informacoes_cotia(texto: str) -> Dict:
    """
    Extrai informações específicas de Cotia
    Separa corretamente nome, matrícula e salário líquido
    """
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
    }
    
    linhas = texto.split('\n')
    
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        
        # Busca por "FUNCIONARIO" e extrai a próxima linha
        if 'FUNCIONARIO' in linha_norm and i + 1 < len(linhas):
            nome_linha = linhas[i + 1].strip()
            match = re.search(r'([A-ZÁÀÃÂÉÈÊÍÏÓÔÕÖÚÇÑ\s]+)', nome_linha)
            if match:
                info['nome'] = match.group(1).strip()
        
        # Busca por "MATRICULA" ou "REFERENCIA"
        if 'FUNCIONARIO' in linha_norm:
            # tenta na linha seguinte (onde normalmente está "6571 NOME")
            if i + 1 < len(linhas):
                prox_linha = linhas[i + 1]
                match = re.search(r'^\s*(\d+)\s+[A-ZÁ-Ú]', prox_linha)
                if match:
                    info['matricula'] = match.group(1)
        
        # Busca por VENCIMENTOS (total)
        if 'VENCIMENTOS' in linha_norm and 'DESCONTOS' not in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                valor_str = valores[-1].replace('.', '').replace(',', '.')
                info['vencimentos_total'] = float(valor_str)
        
        # Busca por DESCONTOS (total)
        if 'DESCONTOS' in linha_norm and 'VENCIMENTOS' not in linha_norm:
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if valores:
                valor_str = valores[-1].replace('.', '').replace(',', '.')
                info['descontos_total'] = float(valor_str)
    
    # Estratégia 1: Buscar "LIQUIDO" na linha
    if info['liquido'] == 0.0:
        for linha in linhas:
            linha_norm = normalizar_texto(linha)
            if 'LIQUIDO' in linha_norm or 'LÍQUIDO' in linha_norm or 'SALARIO HORA' in linha_norm:
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
                if valores:
                    valor_str = valores[-1].replace('.', '').replace(',', '.')
                    info['liquido'] = float(valor_str)
                    break
    
    # Estratégia 2: Calcular como Vencimentos - Descontos
    if info['liquido'] == 0.0 and info['vencimentos_total'] > 0 and info['descontos_total'] >= 0:
        info['liquido'] = info['vencimentos_total'] - info['descontos_total']
    
    return info

def extrair_salario_bruto_cotia(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque de COTIA
    Busca por vencimento base ou similar
    """
    linhas = texto.split('\n')
    
    # Prioridade 1: Buscar "VENCIMENTO BASE"
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'VENCIMENTO BASE' in linha_norm or 'SALARIO BASE' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    # Prioridade 2: Buscar primeiro vencimento significativo
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'VENCIMENTOS' in linha_norm or 'SALARIO HORA' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    return 0.0

def extrair_vencimentos_fixos_cotia(texto: str) -> Dict:
    """
    Extrai vencimentos de COTIA da coluna de VENCIMENTOS
    Estrutura similar a POÁ
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'adicional_tempo_servico': 0.0,
        'gratificacao': 0.0,
        'hora_ativ_extra_classe': 0.0,
        'aula_suplementar': 0.0,
        'vale_alimentacao': 0.0,
        'sexta_parte': 0.0,
        'adicional_risco_vida': 0.0,
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)

        # Adicional de Tempo de Serviço (CORRIGIDO - adiciona "POR TEMPO")
        if ('ADICIONAL TEMPO' in linha_norm or 
            'ADICIONAL TEMPO SERVICO' in linha_norm or 
            'ADICIONAL POR TEMPO' in linha_norm or  # ← NOVO
            'ADICIONAL POR TEMPO DE SERVICO' in linha_norm):  # ← NOVO
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['adicional_tempo_servico'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # Gratificação
        if any(p in linha_norm for p in ['GRAT', 'GRAT.EXERC', 'FUNCao INCORPORADA']):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['gratificacao'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # Hora Ativ. Extra Classe
        if any(p in linha_norm for p in ['HORA ATIV', 'HORA ATIV.EXTRA', 'HORA ATIV. EXTRA']):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['hora_ativ_extra_classe'] = valor
                vencimentos_fixos['total'] += valor
            continue
        
        if any(p in linha_norm for p in ['ADICIONAL POR RISCO DE VIDA', 'RISCO DE VIDA']):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['adicional_risco_vida'] = valor
                vencimentos_fixos['total'] += valor
            continue

    return vencimentos_fixos

# ============================================================================
# FUNÇÕES GENÉRICAS (COMPARTILHADAS)
# ============================================================================

def identificar_cartoes_credito(texto: str) -> Dict[str, List[str]]:
    """Identifica cartões de crédito no texto (FILTRA RIGOROSAMENTE EMPRÉSTIMOS)"""
    texto_normalizado = normalizar_texto(texto)
    linhas = texto_normalizado.split('\n')
    
    TERMOS_EXCLUSAO = [
        'EMPRESTIMO', 'EMP ', ' EMP', 'CONSIGNADO', 
        'FINANCIAMENTO', 'CREDITO PESSOAL', 'CP ', 'CORRENTE',
        'DATA DE CREDITO',  
        'TOTAL VENCIMENTOS', 
        'TOTAL DESCONTOS',
        'VALOR LIQUIDO',
        'ORGAOS DE PROTECAO',
        'DIVERSOS CONTA',
        'DIVERSOS',
        'LANCADOS',
        'CAT',
        'VALOR LIMITE',
        'PIS/PASEP'
    ]

    cartoes_encontrados = {
        'nossos_contratos': [],
        'conhecidos': [],
        'nao_comprados': [],  
        'desconhecidos': []
    }
    
    # ---------------------------------------------------------
    # 1. Nossos Produtos (Com filtro de exclusão)
    # ---------------------------------------------------------
    for produto in NOSSOS_PRODUTOS:
        if produto in texto_normalizado:
            for linha in linhas:
                if produto in linha and any(kw in linha for kw in ['CARTAO', 'CRED ', 'ANTICIPAY', 'STARCARD', 'STARBANK', 'CARTAO UASPREV']):
                    if any(termo in linha for termo in TERMOS_EXCLUSAO):
                        continue
                    if linha.strip() not in cartoes_encontrados['nossos_contratos']:
                        cartoes_encontrados['nossos_contratos'].append(linha.strip())
    
    # ---------------------------------------------------------
    # 2. Cartões Conhecidos (Com filtro de exclusão)
    # ---------------------------------------------------------
    for cartao in CARTOES_CONHECIDOS:
        if cartao in texto_normalizado:
            for linha in linhas:
                if cartao in linha and any(kw in linha for kw in ['CARTAO', 'CRED ', 'CART.', 'CART']):
                    if any(termo in linha for termo in TERMOS_EXCLUSAO):
                        continue
                    if linha.strip() not in cartoes_encontrados['conhecidos']:
                        cartoes_encontrados['conhecidos'].append(linha.strip())
    
    # ---------------------------------------------------------
    # 2.5. Cartões Não Comprados (NOVA CATEGORIA)
    # ---------------------------------------------------------
    for cartao in CARTOES_NAO_COMPRADOS:
        if cartao in texto_normalizado:
            for linha in linhas:
                if cartao in linha and any(kw in linha for kw in ['CARTAO', 'CRED ', 'CART.', 'CART',  'FY DIGITAL']):
                    if any(termo in linha for termo in TERMOS_EXCLUSAO):
                        continue
                    if linha.strip() not in cartoes_encontrados['nao_comprados']:
                        cartoes_encontrados['nao_comprados'].append(linha.strip())
    
    # ---------------------------------------------------------
    # 3. Desconhecidos (Com filtro de exclusão)
    # ---------------------------------------------------------
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        if any(termo in linha_norm for termo in TERMOS_EXCLUSAO):
            continue

        tem_keyword_cartao = any(kw in linha_norm for kw in 
                                  ['CARTAO', 'CART ', 'CRED ', 'CREDITO','CART.'])
        
        if tem_keyword_cartao:
            eh_nosso = any(produto in linha_norm for produto in NOSSOS_PRODUTOS)
            eh_conhecido = any(cartao in linha_norm for cartao in CARTOES_CONHECIDOS)
            eh_nao_comprado = any(cartao in linha_norm for cartao in CARTOES_NAO_COMPRADOS)  # NOVA VALIDAÇÃO
            
            if not eh_nosso and not eh_conhecido and not eh_nao_comprado and linha.strip():
                if linha.strip() not in cartoes_encontrados['desconhecidos']:
                    cartoes_encontrados['desconhecidos'].append(linha.strip())
    
    return cartoes_encontrados

def extrair_informacoes_financeiras(texto: str) -> Dict:
    """Extrai informações financeiras do holerite"""
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': ''
    }
    
    linhas = texto.split('\n')
    
    for i, linha in enumerate(linhas):
        # Extrai matrícula - pode estar na mesma linha ou na linha anterior ao NOME
        if 'MATRICULA' in linha:
            # Tenta extrair da mesma linha
            match = re.search(r'(\d{6})', linha)
            if match:
                info['matricula'] = match.group(1)
            # Se não encontrou, tenta próxima linha
            elif i + 1 < len(linhas):
                match = re.search(r'(\d{6})', linhas[i + 1])
                if match:
                    info['matricula'] = match.group(1)
        
        # Extrai nome - vem depois de "NOME"
        if 'NOME' in linha and i + 1 < len(linhas):
            nome_completo = linhas[i + 1].strip()
            # Remove a matrícula do início do nome se estiver lá
            nome_limpo = re.sub(r'^\d{6}\s*', '', nome_completo).strip()
            info['nome'] = nome_limpo
        
        # Se não encontrou matrícula pelo MATRICULA, tenta buscar antes do NOME
        if not info['matricula'] and 'NOME' in linha and i > 0:
            # Procura a matrícula nas linhas anteriores
            for j in range(max(0, i - 3), i):
                match = re.search(r'(\d{6})', linhas[j])
                if match:
                    info['matricula'] = match.group(1)
                    break
        
        if 'VENCIMENTOS' in linha and 'DESCONTOS' not in linha:
            match = re.search(r'(\d+[.,]\d{2})', linha)
            if match:
                valor = match.group(1).replace('.', '').replace(',', '.')
                info['vencimentos_total'] = float(valor)
        
        if 'DESCONTOS' in linha and 'VENCIMENTOS' not in linha:
            match = re.search(r'(\d+[.,]\d{2})', linha)
            if match:
                valor = match.group(1).replace('.', '').replace(',', '.')
                info['descontos_total'] = float(valor)
        
        if 'LIQUIDO' in normalizar_texto(linha):
            match = re.search(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
            if match:
                valor = match.group().replace('.', '').replace(',', '.')
                info['liquido'] = float(valor)
    
    return info

# ============================================================================
# FUNÇÕES DE CÁLCULO DE MARGEM
# ============================================================================

def extrair_valores_linha(linha: str) -> float:
    """Extrai o último valor numérico de uma linha (coluna de descontos)"""
    valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}', linha)
    if valores:
        valor_str = valores[-1].replace('.', '').replace(',', '.')
        return float(valor_str)
    return 0.0

def extrair_valores_vencimento(linha: str) -> float:
    """
    Extrai o valor da coluna de VENCIMENTOS (penúltimo valor numérico)
    """
    valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}', linha)
    if len(valores) >= 2:
        valor_str = valores[-2].replace('.', '').replace(',', '.')
        return float(valor_str)
    elif len(valores) == 1:
        valor_str = valores[0].replace('.', '').replace(',', '.')
        return float(valor_str)
    return 0.0

def extrair_valores_desconto(linha: str) -> float:
    """
    Extrai o valor da coluna de DESCONTOS (último valor numérico)
    """
    valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}', linha)
    if valores:
        valor_str = valores[-1].replace('.', '').replace(',', '.')
        return float(valor_str)
    return 0.0

def extrair_valores_bauru(linha: str) -> float:
    """
    Para Bauru: estrutura Código | Descrição | Qtde. | Vencimentos/Descontos
    A Qtde. (ex: 30,000) confunde o extrator genérico pois o regex captura
    '30,00' de dentro de '30,000'. A solução é sempre pegar o ÚLTIMO valor.
    """
    valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}', linha)
    if valores:
        valor_str = valores[-1].replace('.', '').replace(',', '.')
        return float(valor_str)
    return 0.0

def extrair_valores_vencimento_maringa(linha: str) -> float:
    """
    Extrai o valor da coluna VENCIMENTOS para holerites de MARINGÁ
    
    Estrutura Maringá: CÓD | DESCRIÇÃO | REFERÊNCIA | VENCIMENTOS | DESCONTOS
    
    Exemplo: "1 SALARIO NORMAL 180,00 3.647,56"
    Deve pegar: 3.647,56 (não 180,00)
    """
    valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}', linha)
    
    # Se tem 3 ou mais valores: [referência, vencimento, desconto (opcional)]
    # Queremos o segundo valor (índice -2 se tem desconto, ou -1 se não tem)
    if len(valores) >= 3:
        # Pega o segundo valor (vencimentos)
        valor_str = valores[-2].replace('.', '').replace(',', '.')
        return float(valor_str)
    elif len(valores) == 2:
        # Se só tem 2 valores, o último é vencimentos
        valor_str = valores[-1].replace('.', '').replace(',', '.')
        return float(valor_str)
    elif len(valores) == 1:
        # Se só tem 1 valor, é esse mesmo
        valor_str = valores[0].replace('.', '').replace(',', '.')
        return float(valor_str)
    
    return 0.0

def extrair_valores_cartoes(texto: str, cartoes_encontrados: Dict) -> Dict:
    """
    Extrai os valores dos descontos de cartões identificados
    Usa a coluna de DESCONTOS
    """
    linhas = texto.split('\n')
    
    valores_cartoes = {
        'nossos_contratos': [],
        'conhecidos': [],
        'desconhecidos': [],
        'total': 0.0
    }
    
    # Processa nossos contratos
    for cartao_linha in cartoes_encontrados.get('nossos_contratos', []):
        cartao_norm = normalizar_texto(cartao_linha)
        for linha in linhas:
            linha_norm = normalizar_texto(linha)
            if cartao_norm in linha_norm:
                valor = extrair_valores_desconto(linha)
                if valor > 0:
                    valores_cartoes['nossos_contratos'].append({
                        'descricao': cartao_linha.strip(),
                        'valor': valor
                    })
                    valores_cartoes['total'] += valor
                    break
    
    # Processa cartões conhecidos
    for cartao_linha in cartoes_encontrados.get('conhecidos', []):
        cartao_norm = normalizar_texto(cartao_linha)
        for linha in linhas:
            linha_norm = normalizar_texto(linha)
            if cartao_norm in linha_norm:
                valor = extrair_valores_desconto(linha)
                if valor > 0:
                    valores_cartoes['conhecidos'].append({
                        'descricao': cartao_linha.strip(),
                        'valor': valor
                    })
                    valores_cartoes['total'] += valor
                    break
    
    # Processa cartões desconhecidos
    for cartao_linha in cartoes_encontrados.get('desconhecidos', []):
        cartao_norm = normalizar_texto(cartao_linha)
        for linha in linhas:
            linha_norm = normalizar_texto(linha)
            if cartao_norm in linha_norm:
                valor = extrair_valores_desconto(linha)
                if valor > 0:
                    valores_cartoes['desconhecidos'].append({
                        'descricao': cartao_linha.strip(),
                        'valor': valor
                    })
                    valores_cartoes['total'] += valor
                    break
    
    return valores_cartoes

def extrair_descontos_obrigatorios(texto: str) -> Dict:
    """
    Extrai apenas os descontos OBRIGATÓRIOS (INSS, IRRF, Previdência)
    da coluna de DESCONTOS
    """
    linhas = texto.split('\n')
    
    descontos_obrigatorios = {
        'inss': 0.0,
        'irrf': 0.0,
        'previdencia': 0.0,
        'total': 0.0
    }
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        # INSS
        if 'I.N.S.S' in linha_norm or 'INSS' in linha_norm:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                descontos_obrigatorios['inss'] = valor
                descontos_obrigatorios['total'] += valor
        
        # IRRF
        elif 'IRRF' in linha_norm or 'I.R.R.F' in linha_norm or 'IMPOSTO DE RENDA' in linha_norm or 'IR ' in linha_norm:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                descontos_obrigatorios['irrf'] = valor
                descontos_obrigatorios['total'] += valor
        
        # Previdência
        elif any(palavra in linha_norm for palavra in ['PREVIDENCIA', 'RPPS', 'IPSM', 'FUNPREV']):
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                descontos_obrigatorios['previdencia'] = valor
                descontos_obrigatorios['total'] += valor
    
    return descontos_obrigatorios

def extrair_descontos_fixos(texto: str) -> Dict:
    """Identifica e extrai valores de descontos fixos"""
    texto_normalizado = normalizar_texto(texto)
    linhas = texto.split('\n')
    
    descontos_fixos = {
        'inss': 0.0,
        'irrf': 0.0,
        'previdencia': 0.0,
        'pensao': 0.0,
        'plano_saude': 0.0,
        'vale_transporte': 0.0,
        'outros': []
    }
    
    keywords = {
        'inss': ['INSS', 'I.N.S.S', 'INSTITUTO NACIONAL'],
        'irrf': ['IRRF', 'I.R.R.F', 'IMPOSTO DE RENDA', 'IR FONTE', 'IMP RENDA'],
        'previdencia': ['PREV', 'PREVIDENCIA', 'RPPS', 'UASPREV', 'IPSM', 'FUNPREV'],
        'pensao': ['PENSAO', 'PENSÃO', 'ALIMENTICIA', 'ALIMENTÍCIA'],
        'plano_saude': ['PLANO', 'SAUDE', 'SAÚDE', 'ASSISTENCIA MEDICA', 'UNIMED', 'AMIL'],
        'vale_transporte': ['VALE TRANSPORTE', 'VT', 'V.TRANSPORTE', 'TRANSP']
    }
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        for categoria, palavras in keywords.items():
            if any(palavra in linha_norm for palavra in palavras):
                valor = extrair_valores_linha(linha)
                if valor > 0:
                    if categoria == 'inss':
                        descontos_fixos['inss'] += valor
                    elif categoria == 'irrf':
                        descontos_fixos['irrf'] += valor
                    elif categoria == 'previdencia':
                        descontos_fixos['previdencia'] += valor
                    elif categoria == 'pensao':
                        descontos_fixos['pensao'] += valor
                    elif categoria == 'plano_saude':
                        descontos_fixos['plano_saude'] += valor
                    elif categoria == 'vale_transporte':
                        descontos_fixos['vale_transporte'] += valor
                    
                    descontos_fixos['outros'].append({
                        'descricao': linha.strip(),
                        'valor': valor,
                        'categoria': categoria
                    })
                    break
    
    return descontos_fixos

# ============================================================================
# FUNÇÕES DE CÁLCULO DE MARGEM
# ============================================================================

def extrair_valores_linha(linha: str) -> float:
    """Extrai o último valor numérico de uma linha (coluna de descontos)"""
    valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}', linha)
    if valores:
        valor_str = valores[-1].replace('.', '').replace(',', '.')
        return float(valor_str)
    return 0.0

def extrair_salario_bruto(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque
    Busca por "Vencimentos Estatutarios" ou similar na coluna de vencimentos
    """
    linhas = texto.split('\n')
    
    # Prioridade 1: Buscar linha "Vencimentos Estatutarios"
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'VENCIMENTOS ESTATUTARIOS' in linha_norm or 'VENCIMENTO ESTATUTARIO' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    # Prioridade 2: Buscar "VENCIMENTO BASE" no cabeçalho
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        if 'VENCIMENTO BASE' in linha_norm:
            # Próxima linha pode ter os valores
            if i + 1 < len(linhas):
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}', linhas[i + 1])
                if valores:
                    valor_str = valores[0].replace('.', '').replace(',', '.')
                    return float(valor_str)
    
    # Prioridade 3: Buscar "SALARIO BASE" ou apenas "SALARIO"
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'SALARIO BASE' in linha_norm or (linha_norm.strip().startswith('SALARIO') and 'DESCONTO' not in linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    return 0.0



def extrair_vencimentos_fixos(texto: str) -> Dict:
    """
    Extrai vencimentos (Vencimento Base, Adicional Tempo, Gratificação,
    Hora Ativ. Extra Classe, Aula Suplementar, Vale Alimentação, 6ª parte, etc.)
    da coluna de VENCIMENTOS.

    Retorna um dict com chaves explícitas e uma lista 'outros_fixos' para itens
    não mapeados individualmente, além do 'total' (soma de todos os vencimentos encontrados).
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'adicional_tempo_servico': 0.0,
        'gratificacao': 0.0,               # ex: Grat.Exerc.Funcao Incorporada
        'hora_ativ_extra_classe': 0.0,
        'aula_suplementar': 0.0,
        'vale_alimentacao': 0.0,
        'sexta_parte': 0.0,
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)


        # Adicional de Tempo de Serviço
        if 'ADICIONAL TEMPO' in linha_norm or 'ADICIONAL TEMPO SERVICO' in linha_norm or 'ADICIONAL TEMPO SERVI' in linha_norm or 'Adicional Tempo Servico' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['adicional_tempo_servico'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # Gratificação / Grat. Exercício / Função Incorporada
        if any(p in linha_norm for p in ['GRAT', 'GRAT.EXERC', 'FUNCao INCORPORADA', 'GRAT.EXERC.FUNCAO', 'GRAT.EXERC.FUNCAO INCORPORADA']):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                # some holerites escrevem apenas "GRAT" — agregamos em 'gratificacao'
                vencimentos_fixos['gratificacao'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # Hora Ativ. Extra Classe (várias formas possíveis)
        if any(p in linha_norm for p in ['HORA ATIV', 'HORA ATIV.EXTRA', 'HORA ATIV. EXTRA', 'HORA ATIV.EXTRA CLASSE', 'HORA ATIV EXTRA CLASSE']):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['hora_ativ_extra_classe'] = valor
                vencimentos_fixos['total'] += valor
            continue


    return vencimentos_fixos

def extrair_descontos_obrigatorios(texto: str) -> Dict:
    """
    Extrai apenas os descontos OBRIGATÓRIOS (INSS, IRRF, Previdência)
    da coluna de DESCONTOS
    """
    linhas = texto.split('\n')
    
    descontos_obrigatorios = {
        'inss': 0.0,
        'irrf': 0.0,
        'previdencia': 0.0,
        'total': 0.0
    }
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        # INSS
        if 'I.N.S.S' in linha_norm or 'INSS' in linha_norm:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                descontos_obrigatorios['inss'] = valor
                descontos_obrigatorios['total'] += valor
        
        # IRRF
        elif 'IRRF' in linha_norm or 'I.R.R.F' in linha_norm or 'IMPOSTO DE RENDA' in linha_norm or 'IR ' in linha_norm:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                descontos_obrigatorios['irrf'] = valor
                descontos_obrigatorios['total'] += valor
        
        # Previdência
        elif any(palavra in linha_norm for palavra in ['PREVIDENCIA', 'RPPS', 'IPSM', 'FUNPREV']):
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                descontos_obrigatorios['previdencia'] = valor
                descontos_obrigatorios['total'] += valor
    
    return descontos_obrigatorios
    

def extrair_descontos_fixos(texto: str) -> Dict:
    """Identifica e extrai valores de descontos fixos"""
    texto_normalizado = normalizar_texto(texto)
    linhas = texto.split('\n')
    
    descontos_fixos = {
        'inss': 0.0,
        'irrf': 0.0,
        'previdencia': 0.0,
        'pensao': 0.0,
        'plano_saude': 0.0,
        'vale_transporte': 0.0,
        'outros': []
    }
    
    keywords = {
        'inss': ['INSS', 'I.N.S.S', 'INSTITUTO NACIONAL'],
        'irrf': ['IRRF', 'I.R.R.F', 'IMPOSTO DE RENDA', 'IR FONTE', 'IMP RENDA'],
        'previdencia': ['PREV', 'PREVIDENCIA', 'RPPS', 'UASPREV', 'IPSM', 'FUNPREV'],
        'pensao': ['PENSAO', 'PENSÃO', 'ALIMENTICIA', 'ALIMENTÍCIA'],
        'plano_saude': ['PLANO', 'SAUDE', 'SAÚDE', 'ASSISTENCIA MEDICA', 'UNIMED', 'AMIL'],
        'vale_transporte': ['VALE TRANSPORTE', 'VT', 'V.TRANSPORTE', 'TRANSP']
    }
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        for categoria, palavras in keywords.items():
            if any(palavra in linha_norm for palavra in palavras):
                valor = extrair_valores_linha(linha)
                if valor > 0:
                    if categoria == 'inss':
                        descontos_fixos['inss'] += valor
                    elif categoria == 'irrf':
                        descontos_fixos['irrf'] += valor
                    elif categoria == 'previdencia':
                        descontos_fixos['previdencia'] += valor
                    elif categoria == 'pensao':
                        descontos_fixos['pensao'] += valor
                    elif categoria == 'plano_saude':
                        descontos_fixos['plano_saude'] += valor
                    elif categoria == 'vale_transporte':
                        descontos_fixos['vale_transporte'] += valor
                    
                    descontos_fixos['outros'].append({
                        'descricao': linha.strip(),
                        'valor': valor,
                        'categoria': categoria
                    })
                    break
    
    return descontos_fixos

# ============================================================================
# FUNÇÕES DE CÁLCULO DE MARGEM
# ============================================================================

def extrair_valores_linha(linha: str) -> float:
    """Extrai o último valor numérico de uma linha (coluna de descontos)"""
    valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}', linha)
    if valores:
        valor_str = valores[-1].replace('.', '').replace(',', '.')
        return float(valor_str)
    return 0.0

def extrair_salario_bruto(texto: str) -> float:
    """
    Extrai o valor do salário base do contracheque
    Busca por "Vencimentos Estatutarios" ou similar na coluna de vencimentos
    """
    linhas = texto.split('\n')
    
    # Prioridade 1: Buscar linha "Vencimentos Estatutarios"
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'VENCIMENTOS ESTATUTARIOS' in linha_norm or 'VENCIMENTO ESTATUTARIO' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    # Prioridade 2: Buscar "VENCIMENTO BASE" no cabeçalho
    for i, linha in enumerate(linhas):
        linha_norm = normalizar_texto(linha)
        if 'VENCIMENTO BASE' in linha_norm:
            # Próxima linha pode ter os valores
            if i + 1 < len(linhas):
                valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}', linhas[i + 1])
                if valores:
                    valor_str = valores[0].replace('.', '').replace(',', '.')
                    return float(valor_str)
    
    # Prioridade 3: Buscar "SALARIO BASE" ou apenas "SALARIO"
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'SALARIO BASE' in linha_norm or (linha_norm.strip().startswith('SALARIO') and 'DESCONTO' not in linha_norm):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                return valor
    
    return 0.0



def extrair_vencimentos_fixos(texto: str) -> Dict:
    """
    Extrai vencimentos (Vencimento Base, Adicional Tempo, Gratificação,
    Hora Ativ. Extra Classe, Aula Suplementar, Vale Alimentação, 6ª parte, etc.)
    da coluna de VENCIMENTOS.

    Retorna um dict com chaves explícitas e uma lista 'outros_fixos' para itens
    não mapeados individualmente, além do 'total' (soma de todos os vencimentos encontrados).
    """
    linhas = texto.split('\n')

    vencimentos_fixos = {
        'vencimento_base': 0.0,
        'adicional_tempo_servico': 0.0,
        'gratificacao': 0.0,               # ex: Grat.Exerc.Funcao Incorporada
        'hora_ativ_extra_classe': 0.0,
        'aula_suplementar': 0.0,
        'vale_alimentacao': 0.0,
        'sexta_parte': 0.0,
        'outros_fixos': [],
        'total': 0.0
    }

    for linha in linhas:
        linha_norm = normalizar_texto(linha)


        # Adicional de Tempo de Serviço
        if 'ADICIONAL TEMPO' in linha_norm or 'ADICIONAL TEMPO SERVICO' in linha_norm or 'ADICIONAL TEMPO SERVI' in linha_norm or 'Adicional Tempo Servico' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['adicional_tempo_servico'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # Gratificação / Grat. Exercício / Função Incorporada
        if any(p in linha_norm for p in ['GRAT', 'GRAT.EXERC', 'FUNCao INCORPORADA', 'GRAT.EXERC.FUNCAO', 'GRAT.EXERC.FUNCAO INCORPORADA']):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                # some holerites escrevem apenas "GRAT" — agregamos em 'gratificacao'
                vencimentos_fixos['gratificacao'] = valor
                vencimentos_fixos['total'] += valor
            continue

        # Hora Ativ. Extra Classe (várias formas possíveis)
        if any(p in linha_norm for p in ['HORA ATIV', 'HORA ATIV.EXTRA', 'HORA ATIV. EXTRA', 'HORA ATIV.EXTRA CLASSE', 'HORA ATIV EXTRA CLASSE']):
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['hora_ativ_extra_classe'] = valor
                vencimentos_fixos['total'] += valor
            continue


    return vencimentos_fixos

def extrair_descontos_obrigatorios(texto: str) -> Dict:
    """
    Extrai apenas os descontos OBRIGATÓRIOS (INSS, IRRF, Previdência)
    da coluna de DESCONTOS
    """
    linhas = texto.split('\n')
    
    descontos_obrigatorios = {
        'inss': 0.0,
        'irrf': 0.0,
        'previdencia': 0.0,
        'total': 0.0
    }
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        # INSS
        if 'I.N.S.S' in linha_norm or 'INSS' in linha_norm:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                descontos_obrigatorios['inss'] = valor
                descontos_obrigatorios['total'] += valor
        
        # IRRF
        elif 'IRRF' in linha_norm or 'I.R.R.F' in linha_norm or 'IMPOSTO DE RENDA' in linha_norm or 'IR ' in linha_norm:
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                descontos_obrigatorios['irrf'] = valor
                descontos_obrigatorios['total'] += valor
        
        # Previdência
        elif any(palavra in linha_norm for palavra in ['PREVIDENCIA', 'RPPS', 'IPSM', 'FUNPREV']):
            valor = extrair_valores_desconto(linha)
            if valor > 0:
                descontos_obrigatorios['previdencia'] = valor
                descontos_obrigatorios['total'] += valor
    
    return descontos_obrigatorios
    

def extrair_descontos_fixos(texto: str) -> Dict:
    """Identifica e extrai valores de descontos fixos"""
    texto_normalizado = normalizar_texto(texto)
    linhas = texto.split('\n')
    
    descontos_fixos = {
        'inss': 0.0,
        'irrf': 0.0,
        'previdencia': 0.0,
        'pensao': 0.0,
        'plano_saude': 0.0,
        'vale_transporte': 0.0,
        'outros': []
    }
    
    keywords = {
        'inss': ['INSS', 'I.N.S.S', 'INSTITUTO NACIONAL'],
        'irrf': ['IRRF', 'I.R.R.F', 'IMPOSTO DE RENDA', 'IR FONTE', 'IMP RENDA'],
        'previdencia': ['PREV', 'PREVIDENCIA', 'RPPS', 'UASPREV', 'IPSM', 'FUNPREV'],
        'pensao': ['PENSAO', 'PENSÃO', 'ALIMENTICIA', 'ALIMENTÍCIA'],
        'plano_saude': ['PLANO', 'SAUDE', 'SAÚDE', 'ASSISTENCIA MEDICA', 'UNIMED', 'AMIL'],
        'vale_transporte': ['VALE TRANSPORTE', 'VT', 'V.TRANSPORTE', 'TRANSP']
    }
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        for categoria, palavras in keywords.items():
            if any(palavra in linha_norm for palavra in palavras):
                valor = extrair_valores_linha(linha)
                if valor > 0:
                    if categoria == 'inss':
                        descontos_fixos['inss'] += valor
                    elif categoria == 'irrf':
                        descontos_fixos['irrf'] += valor
                    elif categoria == 'previdencia':
                        descontos_fixos['previdencia'] += valor
                    elif categoria == 'pensao':
                        descontos_fixos['pensao'] += valor
                    elif categoria == 'plano_saude':
                        descontos_fixos['plano_saude'] += valor
                    elif categoria == 'vale_transporte':
                        descontos_fixos['vale_transporte'] += valor
                    
                    descontos_fixos['outros'].append({
                        'descricao': linha.strip(),
                        'valor': valor,
                        'categoria': categoria
                    })
                    break
    
    return descontos_fixos


def calcular_margem_disponivel(salario_base: float, vencimentos_fixos: Dict, 
                               descontos_obrigatorios: Dict, valores_cartoes: Dict, 
                               percentual_permitido: float = 0.15) -> Dict:
    """
    Calcula a margem disponível para CARTÃO usando a fórmula:
    Margem = (Salário Base + Vencimentos Fixos - Descontos Obrigatórios) × Percentual Permitido
    
    Com o holerite exemplo:
    - Salário Base: R$ 2.423,27
    - Vencimentos Fixos: R$ 605,82 + R$ 403,88 = R$ 1.009,70
    - Descontos Obrigatórios: R$ 305,36 + R$ 9,75 = R$ 315,11
    - Base: R$ 2.423,27 + R$ 1.009,70 - R$ 315,11 = R$ 3.117,86
    - Margem Total: R$ 3.117,86 × 10% = R$ 311,79
    """
    
    # Base de cálculo
    total_vencimentos_fixos = vencimentos_fixos.get('total', 0.0)
    total_descontos_obrigatorios = descontos_obrigatorios.get('total', 0.0)
    
    # Fórmula: (Salário Base + Vencimentos Fixos - Descontos Obrigatórios)
    base_calculo = salario_base + total_vencimentos_fixos - total_descontos_obrigatorios
    
    # Margem total permitida para cartão (10%)
    margem_total = base_calculo * percentual_permitido
    
    # Total já comprometido com cartões
    total_cartoes = valores_cartoes.get('total', 0.0)
    
    # Margem disponível
    margem_disponivel = margem_total - total_cartoes
    
    # Percentual utilizado
    percentual_utilizado = (total_cartoes / margem_total * 100) if margem_total > 0 else 0
    
    return {
        'salario_base': salario_base,
        'total_vencimentos_fixos': total_vencimentos_fixos,
        'total_descontos_obrigatorios': total_descontos_obrigatorios,
        'base_calculo': base_calculo,
        'percentual_permitido': percentual_permitido * 100,  # Para exibir em %
        'margem_total': margem_total,
        'total_cartoes': total_cartoes,
        'margem_disponivel': margem_disponivel,
        'percentual_utilizado': percentual_utilizado,
        'tem_margem': margem_disponivel > 0
    }
# Exemplo de uso integrado:
def analisar_contracheque(texto: str, cartoes_encontrados: Dict) -> Dict:
    """
    Função auxiliar que integra todas as extrações e cálculos
    """
    salario_bruto = extrair_salario_bruto(texto)
    descontos_fixos = extrair_descontos_fixos(texto)
    valores_cartoes = extrair_valores_cartoes(texto, cartoes_encontrados)
    margem = calcular_margem_disponivel(salario_bruto, descontos_fixos, valores_cartoes)
    
    return {
        'salario_bruto': salario_bruto,
        'descontos_fixos': descontos_fixos,
        'valores_cartoes': valores_cartoes,
        'margem': margem
    }


# ============================================================================
# FUNÇÕES WRAPPER POR PREFEITURA
# ============================================================================

def analisar_holerite_por_prefeitura(texto: str, prefeitura: str) -> Dict:
    """
    Seleciona as funções corretas baseado na prefeitura
    """
    if prefeitura == 'POA':
        salario_base = extrair_salario_bruto_poa(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_poa(texto)
    elif prefeitura == 'SOROCABA':
        salario_base = extrair_salario_bruto_sorocaba(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_sorocaba(texto)
    elif prefeitura == 'MARINGA':
        salario_base = extrair_salario_bruto_maringa(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_maringa(texto)
    elif prefeitura == 'COTIA':
        salario_base = extrair_salario_bruto_cotia(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_cotia(texto)
    elif prefeitura == 'IMPERATRIZ':
        salario_base = extrair_salario_bruto_imperatriz(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_imperatriz(texto)
    elif prefeitura == 'EMBU':
        salario_base = extrair_salario_bruto_embu(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_embu(texto)
    elif prefeitura == 'HORTOLANDIA':
        salario_base = extrair_salario_bruto_hortolandia(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_hortolandia(texto)
    elif prefeitura == 'BAURU':
        salario_base = extrair_salario_bruto_bauru(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_bauru(texto)
    elif prefeitura == 'UBERABA':
        salario_base = extrair_salario_bruto_uberaba(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_uberaba(texto)
    elif prefeitura == 'LAGO_VERDE':
        salario_base = extrair_salario_bruto_lago_verde(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_lago_verde(texto)
    elif prefeitura == 'TABOAO_SERRA': 
        salario_base = extrair_salario_bruto_taboao_serra(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_taboao_serra(texto)
    elif prefeitura == 'ITAITUBA':  
        salario_base = extrair_salario_bruto_itaituba(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_itaituba(texto)
    elif prefeitura == 'TUPA': 
        salario_base = extrair_salario_bruto_tupa(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_tupa(texto)
    elif prefeitura == 'BARCARENA':
        salario_base = extrair_salario_bruto_barcarena(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_barcarena(texto)
    elif prefeitura == 'SALTO':  
        salario_base = extrair_salario_bruto_salto(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_salto(texto)
    elif prefeitura == 'CAMPOS_JORDAO':
        salario_base = extrair_salario_bruto_campos_jordao(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_campos_jordao(texto)
    elif prefeitura == 'RIBEIRAO_PRETO':
        salario_base = extrair_salario_bruto_ribeirao_preto(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_ribeirao_preto(texto)
    elif prefeitura == 'PONTA_GROSSA':
        salario_base = extrair_salario_bruto_ponta_grossa(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_ponta_grossa(texto)
    elif prefeitura == 'CAMARA_DEPUTADOS':
        salario_base = extrair_salario_bruto_camara_deputados(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_camara_deputados(texto)
    elif prefeitura == 'BELTERRA':
        salario_base = extrair_salario_bruto_belterra(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_belterra(texto)
    elif prefeitura == 'SAO_JOSE_RIO_PRETO':
        salario_base = extrair_salario_bruto_sao_jose_rio_preto(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_sao_jose_rio_preto(texto)
    elif prefeitura == 'VINHEDO':
        salario_base = extrair_salario_bruto_vinhedo(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_vinhedo(texto)
    elif prefeitura == 'MONTE_ALEGRE_SE':
        salario_base = extrair_salario_bruto_monte_alegre_se(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_monte_alegre_se(texto)
        descontos_obrigatorios = extrair_descontos_obrigatorios_monte_alegre_se(texto)  # FUNÇÃO ESPECÍFICA
        
        return {
            'salario_base': salario_base,
            'vencimentos_fixos': vencimentos_fixos,
            'descontos_obrigatorios': descontos_obrigatorios
        }
    elif prefeitura == 'REDENCAO': 
        salario_base = extrair_salario_bruto_redencao(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_redencao(texto)
    elif prefeitura == 'CUIABA':  
        salario_base = extrair_salario_bruto_cuiaba(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_cuiaba(texto)
    elif prefeitura == 'GOVERNO_GOIAS':
        salario_base = extrair_salario_bruto_governo_goias(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_governo_goias(texto)
    elif prefeitura == 'ALEGO':
        salario_base = extrair_salario_bruto_alego(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_alego(texto)
    else:
        # Fallback para POÁ
        salario_base = extrair_salario_bruto_poa(texto)
        vencimentos_fixos = extrair_vencimentos_fixos_poa(texto)
    
    descontos_obrigatorios = extrair_descontos_obrigatorios(texto)
    
    return {
        'salario_base': salario_base,
        'vencimentos_fixos': vencimentos_fixos,
        'descontos_obrigatorios': descontos_obrigatorios
    }

# ============================================================================
# FUNÇÃO PRINCIPAL DE ANÁLISE (ADAPTADA)
# ============================================================================

def detectar_prefeitura_holerite(texto: str) -> str:
    """
    Detecta qual prefeitura o holerite pertence
    """
    texto_norm = normalizar_texto(texto)

    if ('ALEGO' in texto_norm or 
        '02.474.419/0001-00' in texto_norm or
        'ASSEMBLEIA LEGISLATIVA' in texto_norm and 'GOIAS' in texto_norm):
        return 'ALEGO' 

    if 'BARCARENA' in texto_norm or 'PREFEITURA MUNICIPAL DE BARCARENA' in texto_norm or '05.058.458/0001-15' in texto_norm:
        return 'BARCARENA'

    # Indicadores de Itaituba
    if 'ITAITUBA' in texto_norm or 'PREFEITURA MUNICIPAL DE ITAITUBA' in texto_norm or '05.138.730/0001-77' in texto_norm:
        return 'ITAITUBA'

    # Indicadores de Tupã
    if 'TUPA' in texto_norm or 'PREFEITURA MUNICIPAL DE TUPA' in texto_norm or '44.573.087/0001-61' in texto_norm:
        return 'TUPA'

    if 'MUNICIPIO DE SALTO' in texto_norm or 'SALTO' in texto_norm and 'FPJ1035' in texto_norm:
        return 'SALTO'
    
    # Indicadores de Uberaba
    if 'UBERABA' in texto_norm or 'PREFEITURA MUNICIPAL DE UBERABA' in texto_norm:
        return 'UBERABA'
    
    # Indicadores de Lago Verde
    if 'LAGO VERDE' in texto_norm or 'PREFEITURA MUNICIPAL DE LAGO VERDE' in texto_norm or '06.021.174/0001-17' in texto_norm:
        return 'LAGO_VERDE'
    
    # Indicadores de Taboão da Serra  # ← ADICIONAR ESTE BLOCO
    if 'TABOAO DA SERRA' in texto_norm or 'PREFEITURA MUNICIPAL DE TABOAO DA SERRA' in texto_norm or '46.523.122/0001-63' in texto_norm:
        return 'TABOAO_SERRA'
    
    # Indicadores de Bauru
    if 'BAURU' in texto_norm or 'PREF MUNIC DE BAURU' in texto_norm or '46.137.410/0001-80' in texto_norm:
        return 'BAURU'
    
    # Indicadores de Hortolândia
    if 'HORTOLANDIA' in texto_norm or 'HORTOLÂNDIA' in texto_norm or 'MUNICIPIO DE HORTOLANDIA' in texto_norm:
        return 'HORTOLANDIA'
    
    # Indicadores de Embu das Artes
    if 'EMBU DAS ARTES' in texto_norm or 'ESTANCIA TURISTICA DE EMBU' in texto_norm:
        return 'EMBU'
    
    # Indicadores de Imperatriz
    if 'IMPERATRIZ' in texto_norm:
        return 'IMPERATRIZ'
    
    # Indicadores de Maringá
    if 'MARINGA' in texto_norm or 'MARINGÁ' in texto_norm:
        return 'MARINGA'
    
    # Indicadores de Sorocaba
    if 'SOROCABA' in texto_norm:
        return 'SOROCABA'
    
    # Indicadores de Cotia
    if 'COTIA' in texto_norm:
        return 'COTIA'
    
    # Indicadores de Poá
    if 'POA' in texto_norm or 'POÁ' in texto_norm:
        return 'POA'
    
    # Verificar por estrutura do holerite
    if 'SALARIO NORMAL' in texto_norm:
        return 'MARINGA'
    
    if 'VENCIMENTOS ESTATUTARIOS' in texto_norm or 'VENCIMENTO ESTATUTARIO' in texto_norm:
        return 'POA'
    
    if 'VENCIMENTO CARGO COMISSIONADO' in texto_norm:
        return 'IMPERATRIZ'
    
    if 'CAMPOS DO JORDAO' in texto_norm or 'MUNICIPIO DE CAMPOS DO JORDAO' in texto_norm:
        return 'CAMPOS_JORDAO'
    
    # Indicadores de Ribeirão Preto
    if 'RIBEIRAO PRETO' in texto_norm or 'MUNICIPIO DE RIBEIRAO PRETO' in texto_norm or '56.024.581/0001-56' in texto_norm:
        return 'RIBEIRAO_PRETO'
    
    if 'PONTA GROSSA' in texto_norm or 'PREFEITURA MUNICIPAL DE PONTA GROSSA' in texto_norm or '76175884000187' in texto_norm:
        return 'PONTA_GROSSA'
    
    if 'CAMARA DOS DEPUTADOS' in texto_norm or 'SECRETARIO PARLAMENTAR' in texto_norm or 'DEMONSTRATIVO DE PAGAMENTO' in texto_norm and 'CAMARA' in texto_norm:
        return 'CAMARA_DEPUTADOS'

    # Indicadores de Belterra
    if 'BELTERRA' in texto_norm or 'PREFEITURA MUNICIPAL DE BELTERRA' in texto_norm or '01.614.112/0001-03' in texto_norm:
        return 'BELTERRA'

    if 'SAO JOSE DO RIO PRETO' in texto_norm or 'PREFEITURA MUNICIPAL DE SAO JOSE DO RIO PRETO' in texto_norm or '46.588.95/0001-40' in texto_norm or '46.588.950/0001-40' in texto_norm:
        return 'SAO_JOSE_RIO_PRETO'
    
    if 'VINHEDO' in texto_norm or 'PREFEITURA MUNICIPAL DE VINHEDO' in texto_norm:
        return 'VINHEDO'
    
    if ('MONTE ALEGRE DE SERGIPE' in texto_norm or 
        '13.113.287/0001-08' in texto_norm or 
        '11602838000171' in texto_norm or 
        'FUNDO MUN. DE SAUDE DE MONTE ALEGRE' in texto_norm):
        return 'MONTE_ALEGRE_SE' 

    if ('REDENCAO' in texto_norm or 
        '29.989.385/0001-43' in texto_norm or 
        'FUNDO DE MANUT E DESENV DA EDUC B. E DE VAL DOS PROFISS' in texto_norm or
        'www.redencao.pa.gov.br' in texto_norm):
        return 'REDENCAO'  

    if (('GOVERNO' in texto_norm and 'GOIAS' in texto_norm) or 
        'SECRETARIA DE ESTADO DA ADMINISTRACAO' in texto_norm or
        'SUPERINTENDENCIA DE SISTEMAS DE INFORMACAO' in texto_norm or
        'www.administracao.go.gov.br' in texto_norm or
        'folhapagamento.sistemas.go.gov.br' in texto_norm):
        return 'GOVERNO_GOIAS'

    if (('CUIABA' in texto_norm or 'CUIABÁ' in texto_norm) and 
        ('PREFEITURA' in texto_norm or 'CUIABA-PREV' in texto_norm or 
         'SECRETARIA MUNICIPAL' in texto_norm)):
        return 'CUIABA'

    
    return 'DESCONHECIDA'

def analisar_holerite_streamlit(arquivo_bytes: bytes, nome_arquivo: str, prefeitura: str) -> Dict:
    """Analisa um holerite e retorna os resultados"""
    texto = extrair_texto_pdf(arquivo_bytes)
    
    if not texto.strip():
        return None
    
    # REGIME ESPECÍFICO
    if prefeitura == 'BAURU':
        regime = 'INDEFINIDO'
    else:
        regime = extrair_regime_contrato(texto)
    
    # Usar função específica para cada prefeitura
    if prefeitura == 'MARINGA':
        info_financeira = extrair_informacoes_maringa(texto)
    elif prefeitura == 'SOROCABA':
        info_financeira = extrair_informacoes_sorocaba(texto)
    elif prefeitura == 'COTIA':
        info_financeira = extrair_informacoes_cotia(texto)
    elif prefeitura == 'IMPERATRIZ':
        info_financeira = extrair_informacoes_imperatriz(texto)
    elif prefeitura == 'EMBU':
        info_financeira = extrair_informacoes_embu(texto)
    elif prefeitura == 'HORTOLANDIA':
        info_financeira = extrair_informacoes_hortolandia(texto)
    elif prefeitura == 'BAURU':
        info_financeira = extrair_informacoes_bauru(texto)
    elif prefeitura == 'UBERABA':
        info_financeira = extrair_informacoes_uberaba(texto)
    elif prefeitura == 'LAGO_VERDE':
        info_financeira = extrair_informacoes_lago_verde(texto)
    elif prefeitura == 'TABOAO_SERRA':  
        info_financeira = extrair_informacoes_taboao_serra(texto)
    elif prefeitura == 'ITAITUBA': 
        info_financeira = extrair_informacoes_itaituba(texto)
    elif prefeitura == 'TUPA': 
        info_financeira = extrair_informacoes_tupa(texto)
    elif prefeitura == 'BARCARENA':
        info_financeira = extrair_informacoes_barcarena(texto)
    elif prefeitura == 'SALTO':  
        info_financeira = extrair_informacoes_salto(texto)
    elif prefeitura == 'CAMPOS_JORDAO':
        info_financeira = extrair_informacoes_campos_jordao(texto)
    elif prefeitura == 'RIBEIRAO_PRETO':
        info_financeira = extrair_informacoes_ribeirao_preto(texto)
    elif prefeitura == 'PONTA_GROSSA': 
        info_financeira = extrair_informacoes_ponta_grossa(texto)
    elif prefeitura == 'CAMARA_DEPUTADOS':
        info_financeira = extrair_informacoes_camara_deputados(texto)
    elif prefeitura == 'BELTERRA':
        info_financeira = extrair_informacoes_belterra(texto)
    elif prefeitura == 'SAO_JOSE_RIO_PRETO':
        info_financeira = extrair_informacoes_sao_jose_rio_preto(texto)
    elif prefeitura == 'VINHEDO': 
        info_financeira = extrair_informacoes_vinhedo(texto)
    elif prefeitura == 'MONTE_ALEGRE_SE':
        info_financeira = extrair_informacoes_monte_alegre_se(texto)
    elif prefeitura == 'REDENCAO':  
        info_financeira = extrair_informacoes_redencao(texto)
    elif prefeitura == 'CUIABA':  
        info_financeira = extrair_informacoes_cuiaba(texto)
    elif prefeitura == 'GOVERNO_GOIAS':
        info_financeira = extrair_informacoes_governo_goias(texto)
    elif prefeitura == 'ALEGO':
        info_financeira = extrair_informacoes_alego(texto)
    else:
        info_financeira = extrair_informacoes_financeiras(texto)
    
    cartoes = identificar_cartoes_credito(texto)
    
    # Extrai dados específicos da prefeitura
    dados_prefeitura = analisar_holerite_por_prefeitura(texto, prefeitura)
    
    salario_base = dados_prefeitura['salario_base']
    vencimentos_fixos = dados_prefeitura['vencimentos_fixos']
    descontos_obrigatorios = dados_prefeitura['descontos_obrigatorios']
    valores_cartoes = extrair_valores_cartoes(texto, cartoes)
    
    # Calcula margem disponível usando função específica da prefeitura
    if prefeitura == 'POA':
        margem = calcular_margem_poa(texto, salario_base, vencimentos_fixos, 
                                      descontos_obrigatorios, cartoes)
    elif prefeitura == 'COTIA':
        margem = calcular_margem_cotia(texto, salario_base, vencimentos_fixos, 
                                        descontos_obrigatorios, cartoes)
    elif prefeitura == 'MARINGA': 
        margem = calcular_margem_maringa(texto, salario_base, vencimentos_fixos, 
                                        descontos_obrigatorios, cartoes)
    elif prefeitura == 'SOROCABA':
        margem = calcular_margem_sorocaba(texto, salario_base, vencimentos_fixos, 
                                           descontos_obrigatorios, cartoes)
    elif prefeitura == 'EMBU':
        margem = calcular_margem_embu(texto, salario_base, vencimentos_fixos, 
                                     descontos_obrigatorios, cartoes)
    elif prefeitura == 'HORTOLANDIA': 
        margem = calcular_margem_hortolandia(texto, salario_base, vencimentos_fixos,
                                              descontos_obrigatorios, cartoes)
    elif prefeitura == 'BAURU':  
        margem = calcular_margem_bauru(texto, salario_base, vencimentos_fixos,
                                        descontos_obrigatorios, cartoes)
    elif prefeitura == 'LAGO_VERDE':
        margem = calcular_margem_lago_verde(texto, salario_base, vencimentos_fixos,
                                           descontos_obrigatorios, cartoes)
    elif prefeitura == 'TABOAO_SERRA':
        margem = calcular_margem_taboao_serra(texto, salario_base, vencimentos_fixos,
                                             descontos_obrigatorios, cartoes)
    elif prefeitura == 'SALTO':
        margem = calcular_margem_salto(texto, salario_base, vencimentos_fixos,
                                       descontos_obrigatorios, cartoes)
    elif prefeitura == 'TUPA':
        margem = calcular_margem_tupa(texto, salario_base, vencimentos_fixos,
                                      descontos_obrigatorios, cartoes)
    elif prefeitura == 'ITAITUBA':
        margem = calcular_margem_itaituba(texto, salario_base, vencimentos_fixos,
                                         descontos_obrigatorios, cartoes)
    elif prefeitura == 'BARCARENA':
        margem = calcular_margem_barcarena(texto, salario_base, vencimentos_fixos,
                                           descontos_obrigatorios, cartoes)
    elif prefeitura == 'CAMPOS_JORDAO':
        margem = calcular_margem_campos_jordao(texto, salario_base, vencimentos_fixos,
                                               descontos_obrigatorios, cartoes)
    elif prefeitura == 'RIBEIRAO_PRETO':
        margem = calcular_margem_ribeirao_preto(texto, salario_base, vencimentos_fixos,
                                                descontos_obrigatorios, cartoes)
    elif prefeitura == 'PONTA_GROSSA':
        margem = calcular_margem_ponta_grossa(texto, salario_base, vencimentos_fixos,
                                               descontos_obrigatorios, cartoes)
    elif prefeitura == 'CAMARA_DEPUTADOS':
        margem = calcular_margem_camara_deputados(texto, salario_base, vencimentos_fixos,
                                                   descontos_obrigatorios, cartoes)
    elif prefeitura == 'BELTERRA':
        margem = calcular_margem_belterra(texto, salario_base, vencimentos_fixos,
                                          descontos_obrigatorios, cartoes)
    elif prefeitura == 'SAO_JOSE_RIO_PRETO':
        margem = calcular_margem_sao_jose_rio_preto(texto, salario_base, vencimentos_fixos,
                                                     descontos_obrigatorios, cartoes)
    elif prefeitura == 'VINHEDO':
        margem = calcular_margem_vinhedo(texto, salario_base, vencimentos_fixos,
                                         descontos_obrigatorios, cartoes)
    elif prefeitura == 'MONTE_ALEGRE_SE':
        margem = calcular_margem_monte_alegre_se(texto, salario_base, vencimentos_fixos,
                                                  descontos_obrigatorios, cartoes)
    elif prefeitura == 'REDENCAO':
        margem = calcular_margem_redencao(texto, salario_base, vencimentos_fixos,
                                         descontos_obrigatorios, cartoes)
    elif prefeitura == 'CUIABA':
        margem = calcular_margem_cuiaba(texto, salario_base, vencimentos_fixos,
                                       descontos_obrigatorios, cartoes)
    else:
        # Outras prefeituras mantêm cálculo genérico (será removido quando implementarmos cada uma)
        valores_cartoes = extrair_valores_cartoes(texto, cartoes)
        margem = calcular_margem_disponivel(
            salario_base, 
            vencimentos_fixos,
            descontos_obrigatorios,
            valores_cartoes,
            percentual_permitido=0.15  
        )
    
    valores_cartoes = extrair_valores_cartoes(texto, cartoes)
    
    descontos_fixos_completos = extrair_descontos_fixos(texto)
    descontos_fixos_completos = extrair_descontos_fixos(texto)
    
    return {
        'arquivo': nome_arquivo,
        'prefeitura': prefeitura,
        'prefeitura_detectada': detectar_prefeitura_holerite(texto),
        'regime': regime,
        'info_financeira': info_financeira,
        'nossos_contratos': cartoes['nossos_contratos'],
        'cartoes_conhecidos': cartoes['conhecidos'],
        'cartoes_nao_comprados': cartoes['nao_comprados'],
        'cartoes_desconhecidos': cartoes['desconhecidos'],
        'descontos_fixos': descontos_fixos_completos,
        'descontos_obrigatorios': descontos_obrigatorios,
        'vencimentos_fixos': vencimentos_fixos,
        'valores_cartoes': valores_cartoes,
        'margem': margem,
        'texto_completo': texto
    }

def processar_multiplos_pdfs(arquivos_uploaded, prefeitura: str) -> pd.DataFrame:
    """Processa múltiplos PDFs e retorna DataFrame"""
    resultados = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, arquivo_uploaded in enumerate(arquivos_uploaded):
        progress = (idx + 1) / len(arquivos_uploaded)
        progress_bar.progress(progress)
        status_text.text(f"Processando {idx + 1}/{len(arquivos_uploaded)}: {arquivo_uploaded.name}")
        
        try:
            arquivo_bytes = arquivo_uploaded.read()
            resultado = analisar_holerite_streamlit(arquivo_bytes, arquivo_uploaded.name, prefeitura)
            
            if resultado:
                # VALIDAÇÃO: Verificar se a prefeitura detectada bate com a selecionada
                prefeitura_detectada = resultado.get('prefeitura_detectada', 'DESCONHECIDA')
                
                if prefeitura_detectada != prefeitura and prefeitura_detectada != 'DESCONHECIDA':
                    st.warning(
                        f"⚠️ **Arquivo Ignorado: {arquivo_uploaded.name}**\n\n"
                        f"Você selecionou: **{PREFEITURAS[prefeitura]['nome']}**\n\n"
                        f"Mas este holerite é de: **{PREFEITURAS.get(prefeitura_detectada, {}).get('nome', prefeitura_detectada)}**"
                    )
                    continue
                
                info = resultado['info_financeira']
                margem = resultado['margem']
                
                # Adiciona oportunidades conhecidas
                if resultado['cartoes_conhecidos']:
                    for cartao in resultado['cartoes_conhecidos']:
                        # Extrai margem disponível (compatível com POÁ e outras prefeituras)
                        if 'emprestimo' in margem:  # POÁ
                            margem_disp = margem['cartao_consignado']['disponivel']
                            margem_tot = margem['cartao_consignado']['margem_total']
                            total_cart = margem['cartao_consignado']['comprometido']
                            perc_util = (total_cart / margem_tot * 100) if margem_tot > 0 else 0
                        else:  # Outras prefeituras
                            margem_disp = margem.get('margem_disponivel', 0)
                            margem_tot = margem.get('margem_total', 0)
                            total_cart = margem.get('total_cartoes', 0)
                            perc_util = margem.get('percentual_utilizado', 0)
                        
                        resultados.append({
                            'arquivo': resultado['arquivo'],
                            'nome': info.get('nome', 'N/A'),
                            'matricula': info.get('matricula', 'N/A'),
                            'regime': resultado['regime'],
                            'vencimentos': info.get('vencimentos_total', 0),
                            'descontos': info.get('descontos_total', 0),
                            'liquido': info.get('liquido', 'N/A'),
                            'margem_disponivel': margem_disp,
                            'margem_total': margem_tot,
                            'total_cartoes': total_cart,
                            'percentual_utilizado': perc_util,
                            'tipo_oportunidade': 'CONHECIDA',
                            'descricao': cartao,
                            'status': '✅ OPORTUNIDADE CONFIRMADA'
                        })

                # Adiciona nossos contratos
                if resultado['nossos_contratos']:
                    for cartao in resultado['nossos_contratos']:
                        # Extrai margem disponível (compatível com POÁ e outras prefeituras)
                        if 'emprestimo' in margem:  # POÁ
                            margem_disp = margem['cartao_consignado']['disponivel']
                            margem_tot = margem['cartao_consignado']['margem_total']
                            total_cart = margem['cartao_consignado']['comprometido']
                            perc_util = (total_cart / margem_tot * 100) if margem_tot > 0 else 0
                        else:  # Outras prefeituras
                            margem_disp = margem.get('margem_disponivel', 0)
                            margem_tot = margem.get('margem_total', 0)
                            total_cart = margem.get('total_cartoes', 0)
                            perc_util = margem.get('percentual_utilizado', 0)
                        
                        resultados.append({
                            'arquivo': resultado['arquivo'],
                            'nome': info.get('nome', 'N/A'),
                            'matricula': info.get('matricula', 'N/A'),
                            'regime': resultado['regime'],
                            'vencimentos': info.get('vencimentos_total', 0),
                            'descontos': info.get('descontos_total', 0),
                            'liquido': info.get('liquido', 'N/A'),
                            'margem_disponivel': margem_disp,
                            'margem_total': margem_tot,
                            'total_cartoes': total_cart,
                            'percentual_utilizado': perc_util,
                            'tipo_oportunidade': 'NOSSOS CONTRATOS',
                            'descricao': cartao,
                            'status': '🏆 CLIENTE NOSSO'
                        })

                # Adiciona cartões não comprados (NOVA SEÇÃO)
                if resultado['cartoes_nao_comprados']:
                    for cartao in resultado['cartoes_nao_comprados']:
                        # Extrai margem disponível (compatível com POÁ e outras prefeituras)
                        if 'emprestimo' in margem:  # POÁ
                            margem_disp = margem['cartao_consignado']['disponivel']
                            margem_tot = margem['cartao_consignado']['margem_total']
                            total_cart = margem['cartao_consignado']['comprometido']
                            perc_util = (total_cart / margem_tot * 100) if margem_tot > 0 else 0
                        else:  # Outras prefeituras
                            margem_disp = margem.get('margem_disponivel', 0)
                            margem_tot = margem.get('margem_total', 0)
                            total_cart = margem.get('total_cartoes', 0)
                            perc_util = margem.get('percentual_utilizado', 0)
                        
                        resultados.append({
                            'arquivo': resultado['arquivo'],
                            'nome': info.get('nome', 'N/A'),
                            'matricula': info.get('matricula', 'N/A'),
                            'regime': resultado['regime'],
                            'vencimentos': info.get('vencimentos_total', 0),
                            'descontos': info.get('descontos_total', 0),
                            'liquido': info.get('liquido', 'N/A'),
                            'margem_disponivel': margem_disp,
                            'margem_total': margem_tot,
                            'total_cartoes': total_cart,
                            'percentual_utilizado': perc_util,
                            'tipo_oportunidade': 'NAO COMPRADO',
                            'descricao': cartao,
                            'status': '🚫 NÃO COMPRAMOS'
                        })
                
                # Adiciona cartões para estudar
                if resultado['cartoes_desconhecidos']:
                    for cartao in resultado['cartoes_desconhecidos']:
                        # Extrai margem disponível (compatível com POÁ e outras prefeituras)
                        if 'emprestimo' in margem:  # POÁ
                            margem_disp = margem['cartao_consignado']['disponivel']
                            margem_tot = margem['cartao_consignado']['margem_total']
                            total_cart = margem['cartao_consignado']['comprometido']
                            perc_util = (total_cart / margem_tot * 100) if margem_tot > 0 else 0
                        else:  # Outras prefeituras
                            margem_disp = margem.get('margem_disponivel', 0)
                            margem_tot = margem.get('margem_total', 0)
                            total_cart = margem.get('total_cartoes', 0)
                            perc_util = margem.get('percentual_utilizado', 0)
                        
                        resultados.append({
                            'arquivo': resultado['arquivo'],
                            'nome': info.get('nome', 'N/A'),
                            'matricula': info.get('matricula', 'N/A'),
                            'regime': resultado['regime'],
                            'vencimentos': info.get('vencimentos_total', 0),
                            'descontos': info.get('descontos_total', 0),
                            'liquido': info.get('liquido', 'N/A'),
                            'margem_disponivel': margem_disp,
                            'margem_total': margem_tot,
                            'total_cartoes': total_cart,
                            'percentual_utilizado': perc_util,
                            'tipo_oportunidade': 'PARA ESTUDAR',
                            'descricao': cartao,
                            'status': '⚠️ VERIFICAR'
                        })
                
                # Se não tem oportunidades
                if not resultado['cartoes_conhecidos'] and not resultado['cartoes_nao_comprados'] and not resultado['cartoes_desconhecidos']:
                    # Extrai margem disponível (compatível com POÁ e outras prefeituras)
                    if 'emprestimo' in margem:  # POÁ
                        margem_disp = margem['cartao_consignado']['disponivel']
                        margem_tot = margem['cartao_consignado']['margem_total']
                        total_cart = margem['cartao_consignado']['comprometido']
                        perc_util = (total_cart / margem_tot * 100) if margem_tot > 0 else 0
                    else:  # Outras prefeituras
                        margem_disp = margem.get('margem_disponivel', 0)
                        margem_tot = margem.get('margem_total', 0)
                        total_cart = margem.get('total_cartoes', 0)
                        perc_util = margem.get('percentual_utilizado', 0)
                    
                    resultados.append({
                        'arquivo': resultado['arquivo'],
                        'nome': info.get('nome', 'N/A'),
                        'matricula': info.get('matricula', 'N/A'),
                        'regime': resultado['regime'],
                        'vencimentos': info.get('vencimentos_total', 0),
                        'descontos': info.get('descontos_total', 0),
                        'liquido': info.get('liquido', 'N/A'),
                        'margem_disponivel': margem_disp,
                        'margem_total': margem_tot,
                        'total_cartoes': total_cart,
                        'percentual_utilizado': perc_util,
                        'tipo_oportunidade': 'NENHUMA',
                        'descricao': 'Sem oportunidades identificadas',
                        'status': 'ℹ️ SEM OPORTUNIDADE'
                    })
        
        except Exception as e:
            st.error(f"Erro ao processar {arquivo_uploaded.name}: {e}")
    
    progress_bar.empty()
    status_text.empty()
    
    return pd.DataFrame(resultados)
    

# ============================================================================
# INTERFACE STREAMLIT
# ============================================================================

def main():
    # Sidebar com seleção de prefeitura
    with st.sidebar:
        st.image("https://www.starbank.tec.br/wp-content/uploads/2024/04/cropped-1.png", width=500)
        st.markdown("---")

        # Lista de prefeituras com cálculo de margem implementado
        PREFEITURAS_COM_MARGEM = ['POA', 'MARINGA', 'SOROCABA', 'COTIA', 'EMBU', 'HORTOLANDIA', 'BAURU', 'TABOAO_SERRA', 'SALTO', 'TUPA', 'ITAITUBA', 'BARCARENA', 'CAMPOS_JORDAO', 'RIBEIRAO_PRETO', 'PONTA_GROSSA', 'CAMARA_DEPUTADOS', 'BELTERRA', 'SAO_JOSE_RIO_PRETO', 'VINHEDO', 'MONTE_ALEGRE_SE', 'REDENCAO', 'CUIABA']

        st.markdown("<h3 style='color: #1a3a52;'>Prefeitura</h3>", unsafe_allow_html=True)
        prefeitura_selecionada = st.selectbox(
            "Selecione a prefeitura",
            options=list(PREFEITURAS.keys()),
            format_func=lambda x: PREFEITURAS[x]['nome'],
            help="Escolha a prefeitura do holerite para análise correta",
            label_visibility="collapsed"
        )

        # Badge de prefeitura com margem
        if prefeitura_selecionada in PREFEITURAS_COM_MARGEM:
            st.markdown("""
                <div style='
                    display: inline-block;
                    background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
                    color: white;
                    padding: 0.35rem 0.75rem;
                    border-radius: 1rem;
                    font-size: 0.75rem;
                    font-weight: 600;
                    box-shadow: 0 2px 8px rgba(220, 38, 38, 0.25);
                    margin-top: -0.5rem;
                    margin-bottom: 0.5rem;
                    letter-spacing: 0.5px;
                '>
                    🏷️ Cálculo de Margem Disponível!
                </div>
            """, unsafe_allow_html=True)
        
        prefeitura_info = PREFEITURAS[prefeitura_selecionada]
        
        st.markdown("&nbsp;")

        modo = st.radio(
            "Selecione o Modo",
            ["Análise Individual", "Análise em Lote"],
            help="Escolha entre analisar um único PDF ou múltiplos PDFs",
        )
        
        st.markdown("---")
        st.markdown("<h3 style='color: #1a3a52;'>Nossos Produtos</h3>", unsafe_allow_html=True)
        with st.expander("Ver lista completa", expanded=False):
            for produto in NOSSOS_PRODUTOS:
                st.markdown(f"<div style='padding: 0.5rem; color: #1a3a52;'><strong>{produto}</strong></div>", unsafe_allow_html=True)
        
        st.markdown("<h3 style='color: #1a3a52; margin-top: 1.5rem;'>Cartões Concorrentes</h3>", unsafe_allow_html=True)
        with st.expander("Ver lista completa", expanded=False):
            cols = st.columns(2)
            for idx, cartao in enumerate(CARTOES_CONHECIDOS):
                with cols[idx % 2]:
                    st.markdown(f"<div style='padding: 0.25rem;'>{cartao}</div>", unsafe_allow_html=True)


        st.markdown("<h3 style='color: #1a3a52; margin-top: 1.5rem;'>Cartões Que Não Compramos</h3>", unsafe_allow_html=True)
        with st.expander("Ver lista completa", expanded=False):
            cols = st.columns(2)
            for idx, cartao in enumerate(CARTOES_NAO_COMPRADOS):
                with cols[idx % 2]:
                    st.markdown(f"<div style='padding: 0.25rem;'>{cartao}</div>", unsafe_allow_html=True)
        
        st.markdown("---")
        st.info("Você pode fazer upload de múltiplos PDFs de uma vez no modo de análise em lote.", icon="ℹ️")

    
    # Conteúdo principal
    if modo == "Análise Individual":
        st.markdown("<h2 class='section-header'>StarCheck - Análise Individual</h2>", unsafe_allow_html=True)
            # Adicione isso logo após os headers principais na sua função main()
        with st.expander("ℹ️ Como usar o sistema (Clique para expandir)", expanded=False):
            st.markdown("""
            1. **Upload**: Arraste seu arquivo PDF para a área de upload.
            2. **Processamento**: O sistema irá extrair automaticamente os dados (Holerite, Margem, etc.).
            3. **Análise**: Veja os cards coloridos com os resultados principais.
            4. **Exportação**: Se disponível, baixe o relatório final.
            """)
            st.markdown("""
                <div class="warning-box">
                    <h6 style="margin-top:0; color:#92400E;">⚠️ ATENÇÃO: FUNCIONALIDADE EM TESTES</h4>
                    <p style="margin-bottom:0;">
                        O cálculo automático de margem é uma estimativa e <strong>não deve ser considerado 100% preciso</strong>. 
                        <br>
                        Por favor, <strong>verifique sempre a margem real</strong> na gestora original antes de prosseguir com qualquer operação.
                    </p>
                </div>
            """, unsafe_allow_html=True)
        st.info(f"Prefeitura selecionada: **{PREFEITURAS[prefeitura_selecionada]['nome']}**", icon="📍")
        
        arquivo_upload = st.file_uploader(
            "Faça upload do PDF do holerite",
            type=['pdf'],
            help="Selecione um arquivo PDF para análise"
        )
        
        if arquivo_upload:
            if st.button("Analisar", type="primary", use_container_width=False):
                with st.spinner("Analisando holerite..."):
                    arquivo_bytes = arquivo_upload.read()
                    resultado = analisar_holerite_streamlit(arquivo_bytes, arquivo_upload.name, prefeitura_selecionada)
                    
                    if resultado:
                        st.session_state['resultado_individual'] = resultado
            
            if 'resultado_individual' in st.session_state:
                resultado = st.session_state['resultado_individual']
                
                # VALIDAÇÃO: Verificar se a prefeitura selecionada bate com o holerite
                prefeitura_detectada = resultado.get('prefeitura_detectada', 'DESCONHECIDA')
                
                if prefeitura_detectada != prefeitura_selecionada and prefeitura_detectada != 'DESCONHECIDA':
                    st.warning(
                        f"⚠️ **Aviso de Prefeitura**\n\n"
                        f"Você selecionou: **{PREFEITURAS[prefeitura_selecionada]['nome']}**\n\n"
                        f"Mas o holerite parece ser de: **{PREFEITURAS.get(prefeitura_detectada, {}).get('nome', prefeitura_detectada)}**\n\n"
                        f"Verifique se selecionou a prefeitura correta!"
                    )
                    st.stop()
                
                st.success("✅ Análise concluída com sucesso!")
                
                # Extrai a variável margem do resultado
                margem = resultado.get('margem', {})
                
                # Informações do servidor em cards modernos
                st.markdown("<h3 class='section-header'>Informações do Servidor</h3>", unsafe_allow_html=True)
                info = resultado['info_financeira']
                
                # Corrigir: Garantir que liquido é float antes de formatar
                liquido_valor = info.get('liquido', 0)
                if isinstance(liquido_valor, str):
                    try:
                        liquido_valor = float(liquido_valor.replace('.', '').replace(',', '.'))
                    except (ValueError, AttributeError):
                        liquido_valor = 0.0
                
                col1, col2, col3, col4 = st.columns(4, gap="xlarge")
                with col1:
                    nome_valor = (info.get('nome') or '').strip()
                    nome_exibicao = (nome_valor.split()[0][:11] if nome_valor else 'N/A')
                    st.metric("👤 Nome", nome_exibicao)
                
                with col2:
                    st.metric("🏛️ Regime", resultado['regime'])
                
                with col3:
                    st.metric("🆔 Matrícula", info.get('matricula', 'N/A'))
                
                with col4:
                    st.metric("💵 Líquido", f"R$ {liquido_valor:,.2f}")
                

                # Analise de margem - EM MANUTENÇÃO

                #st.markdown("<h3 class='section-header'>💰 Análise de Margem Consignável</h3>", unsafe_allow_html=True)
                
                if prefeitura_selecionada not in ['POA', 'COTIA', 'MARINGA', 'SOROCABA', 'EMBU', 'HORTOLANDIA', 'BAURU', 'TABOAO_SERRA', 'SALTO', 'TUPA', 'ITAITUBA', 'BARCARENA', 'CAMPOS_JORDAO', 'RIBEIRAO_PRETO', 'PONTA_GROSSA', 'CAMARA_DEPUTADOS', 'BELTERRA', 'SAO_JOSE_RIO_PRETO', 'VINHEDO', 'MONTE_ALEGRE_SE', 'REDENCAO', 'CUIABA']:
                    st.info("🔧 **Manutenção - Em Breve**\n\nO módulo de Calculo de Margem sendo construído para esta prefeitura e será disponibilizado em breve.")
                elif margem.get('base_calculo', 0) > 0:


                    emp = margem['emprestimo']
                    cc  = margem['cartao_consignado']

                    # --- CSS global para os cards ---
                    st.markdown("""
                    <style>
                    .card-row { display:flex; gap:1.5rem; flex-wrap:wrap; }
                    .card {
                    flex:1;
                    min-width:280px;
                    padding:1.25rem;
                    border-radius:12px;
                    border:1px solid rgba(0,0,0,0.06);
                    background:#fff;
                    box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
                    }
                    .card h4 { margin:0 0 0.75rem 0; font-size:1.05rem; }
                    .small { font-size:0.82rem; color:#7b7f86; margin:0; }
                    .value { font-weight:700; margin:0; font-size:1.5rem; }
                    .sep { border-top:1px solid #f0f2f5; padding-top:0.9rem; margin-top:0.9rem; }
                    .tag-blue { color:#1565c0; }
                    .tag-purple { color:#6a1b9a; }
                    .tag-orange { color:#f57c00; }
                    .green { color:#2e7d32; }
                    .red { color:#d32f2f; }
                    </style>
                    """, unsafe_allow_html=True)

                    # --- Layout com st.columns para garantir alinhamento ---
                    col1, col2 = st.columns([1,1], gap="large")

                    with col1:
                        st.markdown(f"""
                        <div class="card">
                        <h4>💵 Empréstimo</h4>

                        <div style="display:flex; justify-content:space-between; gap:1rem;">
                            <div>
                            <p class="small">Margem Total</p>
                            <p class="value tag-blue">R$ {emp['margem_total']:,.2f}</p>
                            </div>
                            <div>
                            <p class="small">Comprometido</p>
                            <p class="value tag-orange">R$ {emp['comprometido']:,.2f}</p>
                            </div>
                        </div>

                        <div class="sep">
                            <p class="small">Disponível</p>
                            <p class="value { 'green' if emp['disponivel']>0 else 'red' }">
                            R$ {emp['disponivel']:,.2f} {"✅" if emp['disponivel']>0 else "⚠️"}
                            </p>
                        </div>
                        </div>
                        """, unsafe_allow_html=True)

                    with col2:
                        st.markdown(f"""
                        <div class="card">
                        <h4>💳 Cartão Consignado</h4>

                        <div style="display:flex; justify-content:space-between; gap:1rem;">
                            <div>
                            <p class="small">Margem Total</p>
                            <p class="value tag-purple">R$ {cc['margem_total']:,.2f}</p>
                            </div>
                            <div>
                            <p class="small">Comprometido</p>
                            <p class="value tag-orange">R$ {cc['comprometido']:,.2f}</p>
                            </div>
                        </div>

                        <div class="sep">
                            <p class="small">Disponível</p>
                            <p class="value { 'green' if cc['disponivel']>0 else 'red' }">
                            R$ {cc['disponivel']:,.2f} {"✅" if cc['disponivel']>0 else "⚠️"}
                            </p>
                        </div>
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown("&nbsp;")

                    # Extrai variáveis do resultado armazenado
                    vencimentos_fixos = resultado.get('vencimentos_fixos', {})
                    descontos_obrigatorios = resultado.get('descontos_obrigatorios', {})

                    # --- Função auxiliar para criar linhas de extrato (Coloque antes do expander ou no início do arquivo) ---
                    def item_extrato(label, valor, cor="default", negrito=False, divisor=True):
                        cor_texto = "#374151"
                        cor_valor = "#111827"
                        if cor == "red": cor_valor = "#DC2626"
                        elif cor == "green": cor_valor = "#059669"
                        elif cor == "blue": cor_valor = "#4F46E5"
                        
                        weight = "700" if negrito else "400"
                        border = "border-bottom: 1px solid #F3F4F6;" if divisor else ""
                        
                        # IMPORTANTE: Tudo em uma linha ou sem indentação para evitar bug do Markdown
                        return f'<div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; {border} font-size: 0.9rem; font-family: sans-serif;"><span style="color: {cor_texto};">{label}</span><span style="color: {cor_valor}; font-weight: {weight};">R$ {valor:,.2f}</span></div>'

                    # --- Bloco do Expander Melhorado ---
                    with st.expander("📋 Ver Composição Detalhada", expanded=False):
    
                        # CSS para os Cards
                        st.markdown("""
                        <style>
                            .custom-card { background-color: #FFFFFF; padding: 15px; border-radius: 10px; border: 1px solid #E5E7EB; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 10px; }
                            .card-header { color: #6D28D9; font-size: 1rem; font-weight: 700; margin-bottom: 12px; border-bottom: 2px solid #F3F4F6; padding-bottom: 8px; text-transform: uppercase; letter-spacing: 0.05em; }
                            .section-label { font-size: 0.75rem; text-transform: uppercase; color: #9CA3AF; font-weight: 600; margin-top: 10px; margin-bottom: 5px; }
                        </style>
                        """, unsafe_allow_html=True)

                        c1, c2, c3 = st.columns(3, gap="medium")

                        # --- COLUNA 1: BASE ---
                        with c1:
                            # Montando HTML em uma única string sem indentação quebrada
                            html_c1 = '<div class="custom-card"><div class="card-header">💰 Base de Cálculo</div>'
                            html_c1 += item_extrato("Salário Bruto", margem['salario_bruto'], negrito=True)
                            
                            if vencimentos_fixos and vencimentos_fixos.get('total', 0) > 0:
                                html_c1 += '<div class="section-label">(+) Vencimentos Fixos</div>'
                                campos = {'vencimento_base': 'Vencimento Base', 'adicional_tempo_servico': 'Adic. Tempo', 'adicional_risco_vida': 'Adic. Risco Vida', 'gratificacao': 'Gratificação', 'adicional_insalubridade': 'Adic. Insalubridade', 'hora_ativ_extra_classe': 'H.A. Extra', 'vale_alimentacao': 'Vale Alim.', 'sexta_parte': 'Sexta Parte'}
                                for k, nome in campos.items():
                                    if vencimentos_fixos.get(k, 0) > 0:
                                        html_c1 += item_extrato(nome, vencimentos_fixos[k])
                                
                                if vencimentos_fixos.get('outros_fixos'):
                                    for item in vencimentos_fixos['outros_fixos']:
                                        html_c1 += item_extrato(item.get('descricao', 'Outro')[:20], item.get('valor', 0))

                            html_c1 += '<div class="section-label">(-) Descontos</div>'
                            html_c1 += item_extrato("Total Descontos", margem['descontos_compulsorios'], "red", divisor=False)
                            
                            html_c1 += '<div style="margin-top:10px; border-top: 1px dashed #ccc; padding-top:5px;">'
                            html_c1 += item_extrato("BASE CÁLCULO", margem['base_calculo'], "blue", negrito=True, divisor=False)
                            html_c1 += '</div></div>'
                            
                            st.markdown(html_c1, unsafe_allow_html=True)

                        # --- COLUNA 2: EMPRÉSTIMOS ---
                        with c2:
                            html_c2 = '<div class="custom-card"><div class="card-header">💵 Empréstimos</div>'
                            html_c2 += item_extrato("Permitido", margem['emprestimo']['margem_total'], "blue", negrito=True)
                            html_c2 += item_extrato("Comprometido", margem['emprestimo']['comprometido'], "red")
                            
                            if margem['emprestimo']['comprometido'] > 0:
                                html_c2 += '<div class="section-label">Contratos</div>'
                                linhas = resultado['texto_completo'].split('\n')
                                for linha in linhas:
                                    ln = normalizar_texto(linha)
                                    if ('EMPRESTIMO' in ln or 'CONSIGNADO' in ln) and not any(x in ln for x in ['TOTAL', 'BASE', 'MARGEM']):
                                        val = extrair_valores_desconto(linha)
                                        if val > 0:
                                            html_c2 += item_extrato(linha.strip()[:18]+"...", val)
                            
                            bg = "#ECFDF5" if margem['emprestimo']['disponivel'] > 0 else "#FEF2F2"
                            cor = "green" if margem['emprestimo']['disponivel'] > 0 else "red"
                            
                            html_c2 += f'<div style="margin-top:10px; background:{bg}; padding:8px; border-radius:6px;">'
                            html_c2 += item_extrato("DISPONÍVEL", margem['emprestimo']['disponivel'], cor, negrito=True, divisor=False)
                            html_c2 += '</div></div>'
                            
                            st.markdown(html_c2, unsafe_allow_html=True)

                        # --- COLUNA 3: CARTÕES ---
                        with c3:
                            html_c3 = '<div class="custom-card"><div class="card-header">💳 Cartões</div>'
                            html_c3 += item_extrato("Permitido", margem['cartao_consignado']['margem_total'], "blue", negrito=True)
                            html_c3 += item_extrato("Comprometido", margem['cartao_consignado']['comprometido'], "red")
                            
                            if margem['cartao_consignado']['comprometido'] > 0:
                                html_c3 += '<div class="section-label">Detalhamento</div>'
                                if margem.get('cartoes_nossos', 0) > 0: html_c3 += item_extrato("Nossos", margem['cartoes_nossos'])
                                if margem.get('cartoes_terceiros', 0) > 0: html_c3 += item_extrato("Terceiros", margem['cartoes_terceiros'])
                                if margem.get('cartoes_nao_comprados', 0) > 0: html_c3 += item_extrato("Não Comprados", margem['cartoes_nao_comprados'])
                                if margem.get('cartoes_desconhecidos', 0) > 0: html_c3 += item_extrato("Desconhecidos", margem['cartoes_desconhecidos'], "orange")

                            bg = "#ECFDF5" if margem['cartao_consignado']['disponivel'] > 0 else "#FEF2F2"
                            cor = "green" if margem['cartao_consignado']['disponivel'] > 0 else "red"
                            
                            html_c3 += f'<div style="margin-top:10px; background:{bg}; padding:8px; border-radius:6px;">'
                            html_c3 += item_extrato("DISPONÍVEL", margem['cartao_consignado']['disponivel'], cor, negrito=True, divisor=False)
                            html_c3 += '</div></div>'
                            
                            st.markdown(html_c3, unsafe_allow_html=True)

                st.markdown("<hr class='divider'>", unsafe_allow_html=True)
                
                
                # Nossos Contratos
                if resultado['nossos_contratos']:
                    st.markdown("<h3 class='section-header'>Nossos Contratos</h3>", unsafe_allow_html=True)
                    st.success(f"Este cliente já possui {len(resultado['nossos_contratos'])} contrato(s) conosco!")
                    
                    for i, contrato in enumerate(resultado['nossos_contratos'], 1):
                        st.markdown(f"""
                        <div style='
                            padding: 1rem;
                            background: linear-gradient(135deg, #e8f5e9 0%, #f1f8e9 100%);
                            border-left: 5px solid #2e7d32;
                            border-radius: 0.6rem;
                            margin: 0.75rem 0;
                            box-shadow: 0 2px 6px rgba(46, 125, 50, 0.1);
                        '>
                            <div style='display: flex; align-items: flex-start; gap: 1rem;'>
                                <div style='
                                    display: flex;
                                    align-items: center;
                                    justify-content: center;
                                    width: 32px;
                                    height: 32px;
                                    background: #2e7d32;
                                    color: white;
                                    border-radius: 50%;
                                    font-weight: 600;
                                    flex-shrink: 0;
                                '>{i}</div>
                                <div style='flex: 1;'>
                                    <p style='margin: 0; color: #1a3a52; font-weight: 600;'>{contrato}</p>
                                    <p style='margin: 0.25rem 0 0 0; color: #666; font-size: 0.85rem;'>Nosso Cartão - Verifique Refinanciamento</p>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
                
                # Oportunidades
                st.markdown("<h3 class='section-header'>Oportunidades Confirmadas</h3>", unsafe_allow_html=True)
                st.success(f"Total: {len(resultado['cartoes_conhecidos'])} oportunidade(s) identificada(s)")
                if resultado['cartoes_conhecidos']:
                    for i, cartao in enumerate(resultado['cartoes_conhecidos'], 1):
                        st.markdown(f"""
                        <div style='
                            padding: 1rem;
                            background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
                            border-left: 5px solid #1565c0;
                            border-radius: 0.6rem;
                            margin: 0.75rem 0;
                            box-shadow: 0 2px 6px rgba(21, 101, 192, 0.1);
                        '>
                            <div style='display: flex; align-items: flex-start; gap: 1rem;'>
                                <div style='
                                    display: flex;
                                    align-items: center;
                                    justify-content: center;
                                    width: 32px;
                                    height: 32px;
                                    background: #1565c0;
                                    color: white;
                                    border-radius: 50%;
                                    font-weight: 600;
                                    flex-shrink: 0;
                                '>{i}</div>
                                <div style='flex: 1;'>
                                    <p style='margin: 0; color: #1a3a52; font-weight: 600;'>{cartao}</p>
                                    <p style='margin: 0.25rem 0 0 0; color: #666; font-size: 0.85rem;'>Cartão Concorrente - Oportunidade de Compra de Divida</p>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                else:
                    st.info("Nenhuma oportunidade confirmada encontrada.")
                
                st.markdown("<hr class='divider'>", unsafe_allow_html=True)

                st.markdown("<h3 class='section-header'>Cartões Que Não Compramos</h3>", unsafe_allow_html=True)
                st.info(f"Total: {len(resultado['cartoes_nao_comprados'])} cartão(ões) que não compramos")
                if resultado['cartoes_nao_comprados']:
                    for i, cartao in enumerate(resultado['cartoes_nao_comprados'], 1):
                        st.markdown(f"""
                        <div style='
                            padding: 1rem;
                            background: linear-gradient(135deg, #fce4ec 0%, #f8bbd0 100%);
                            border-left: 5px solid #c2185b;
                            border-radius: 0.6rem;
                            margin: 0.75rem 0;
                            box-shadow: 0 2px 6px rgba(194, 24, 91, 0.1);
                        '>
                            <div style='display: flex; align-items: flex-start; gap: 1rem;'>
                                <div style='
                                    display: flex;
                                    align-items: center;
                                    justify-content: center;
                                    width: 32px;
                                    height: 32px;
                                    background: #c2185b;
                                    color: white;
                                    border-radius: 50%;
                                    font-weight: 600;
                                    flex-shrink: 0;
                                '>{i}</div>
                                <div style='flex: 1;'>
                                    <p style='margin: 0; color: #1a3a52; font-weight: 600;'>{cartao}</p>
                                    <p style='margin: 0.25rem 0 0 0; color: #666; font-size: 0.85rem;'>Cartão que não compramos</p>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.success("Não há cartões de instituições que não compramos.")
                
                st.markdown("<h3 class='section-header'>Itens para Estudar</h3>", unsafe_allow_html=True)
                st.warning(f"Total: {len(resultado['cartoes_desconhecidos'])} item(ns) aguardando análise")
                if resultado['cartoes_desconhecidos']:
                    for i, cartao in enumerate(resultado['cartoes_desconhecidos'], 1):
                        st.markdown(f"""
                        <div style='
                            padding: 1rem;
                            background: linear-gradient(135deg, #fff8e1 0%, #ffe0b2 100%);
                            border-left: 5px solid #f57f17;
                            border-radius: 0.6rem;
                            margin: 0.75rem 0;
                            box-shadow: 0 2px 6px rgba(245, 127, 23, 0.1);
                        '>
                            <div style='display: flex; align-items: flex-start; gap: 1rem;'>
                                <div style='
                                    display: flex;
                                    align-items: center;
                                    justify-content: center;
                                    width: 32px;
                                    height: 32px;
                                    background: #f57f17;
                                    color: white;
                                    border-radius: 50%;
                                    font-weight: 600;
                                    flex-shrink: 0;
                                '>{i}</div>
                                <div style='flex: 1;'>
                                    <p style='margin: 0; color: #1a3a52; font-weight: 600;'>{cartao}</p>
                                    <p style='margin: 0.25rem 0 0 0; color: #666; font-size: 0.85rem;'>Requer análise para confirmação</p>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.success("Todos os cartões estão na lista conhecida.")
    
    else:  # Análise em Lote
        st.markdown("<h2 class='section-header'>StarCheck - Análise em Lote</h2>", unsafe_allow_html=True)
        st.info(f"Prefeitura selecionada: **{PREFEITURAS[prefeitura_selecionada]['nome']}**", icon="📍")
        
        arquivos_upload = st.file_uploader(
            "Faça upload dos PDFs dos holerites",
            type=['pdf'],
            accept_multiple_files=True,
            help="Selecione múltiplos arquivos PDF para análise em lote"
        )
        
        if arquivos_upload:
            if st.button("Processar Todos", type="primary", use_container_width=False):
                with st.spinner("Processando arquivos..."):
                    df = processar_multiplos_pdfs(arquivos_upload, prefeitura_selecionada)
                    st.session_state['df_resultados'] = df
                    st.success(f"{len(arquivos_upload)} arquivo(s) processado(s) com sucesso!")
            
            if 'df_resultados' in st.session_state:
                df = st.session_state['df_resultados']
                
                if not df.empty:
                    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
                    
                    # Dashboard de Estatísticas
                    st.markdown("<h3 class='section-header'>Dashboard de Resultados</h3>", unsafe_allow_html=True)
                    
                    col1, col2, col3, col4 = st.columns(4, gap="small")
                    
                    with col1:
                        total_oportunidades = len(df[df['tipo_oportunidade'] == 'CONHECIDA'])
                        st.metric("Oportunidades", f"{total_oportunidades}", 
                                help="Total de oportunidades confirmadas")
                    
                    with col2:
                        total_estudar = len(df[df['tipo_oportunidade'] == 'PARA ESTUDAR'])
                        st.metric("Para Estudar", f"{total_estudar}",
                                help="Cartões fora da lista conhecida")
                    
                    with col3:
                        total_sem = len(df[df['tipo_oportunidade'] == 'NENHUMA'])
                        st.metric("Sem Oportunidade", f"{total_sem}",
                                help="Servidores sem oportunidades")
                    
                    with col4:
                        total_servidores = df['nome'].nunique()
                        st.metric("Servidores", f"{total_servidores}",
                                help="Total de servidores únicos")
                    
                    # with col5:
                    #     df_com_margem = df[df['margem_disponivel'].notna()]
                    #     if not df_com_margem.empty:
                    #         margem_por_servidor = df_com_margem.groupby('matricula')['margem_disponivel'].first()
                    #         media_margem = margem_por_servidor.mean()
                    #         st.metric("Margem Média", f"R$ {media_margem:,.0f}",
                    #                 help="Média de margem disponível")
                    #     else:
                    #         st.metric("Margem Média", "N/A",
                    #                 help="Não foi possível calcular")
                    
                    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
                    
                    # Gráficos
                    col1, col2 = st.columns(2, gap="large")
                    
                    with col1:
                        st.markdown("<h4 style='color: #1a3a52; margin-bottom: 1rem;'>Distribuição por Tipo</h4>", unsafe_allow_html=True)
                        tipo_counts = df['tipo_oportunidade'].value_counts()
                        fig_tipo = px.pie(
                            values=tipo_counts.values,
                            names=tipo_counts.index,
                            title="",
                            color_discrete_sequence=["#401c5c", "#6a3d7f", "#8a5fa0", "#b088c9"]
                        )
                        fig_tipo.update_layout(height=400, showlegend=True, font=dict(size=12))
                        st.plotly_chart(fig_tipo, use_container_width=True)
                    
                    with col2:
                        st.markdown("<h4 style='color: #1a3a52; margin-bottom: 1rem;'>Distribuição por Regime</h4>", unsafe_allow_html=True)
                        regime_counts = df['regime'].value_counts()
                        fig_regime = px.bar(
                            x=regime_counts.index,
                            y=regime_counts.values,
                            title="",
                            labels={'x': 'Regime', 'y': 'Quantidade'},
                            color=regime_counts.values,
                            color_continuous_scale='Purples',
                        )
                        fig_regime.update_layout(height=400, font=dict(size=12), showlegend=False)
                        st.plotly_chart(fig_regime, use_container_width=True)

                    
                    df_margem = df.groupby('matricula').agg({
                        'nome': 'first',
                        'margem_disponivel': 'first',
                        'margem_total': 'first',
                        'total_cartoes': 'first',
                        'percentual_utilizado': 'first'
                    }).reset_index()
                    
                    df_margem = df_margem[df_margem['margem_disponivel'].notna()]
                    
                    if not df_margem.empty:
   
                        
                        # Top 10 com melhor margem
                        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

                        st.markdown("<h3 class='section-header'>Top 10 Servidores com Melhor Margem</h3>", unsafe_allow_html=True)

                        st.info("Manutenção - Em Breve\n\nEste módulo está em manutenção e será disponibilizado em breve.", icon="⚙️")
                        
                    #     df_margem_positiva = df_margem[df_margem['margem_disponivel'] > 0]
                        
                    #     if not df_margem_positiva.empty:
                    #         top_margem = df_margem_positiva.nlargest(10, 'margem_disponivel')[
                    #             ['nome', 'matricula', 'margem_disponivel', 'margem_total', 'total_cartoes', 'percentual_utilizado']
                    #         ]
                            
                    #         st.dataframe(
                    #             top_margem,
                    #             column_config={
                    #                 "nome": "Nome",
                    #                 "matricula": "Matrícula",
                    #                 "margem_disponivel": st.column_config.NumberColumn(
                    #                     "Margem Disponível",
                    #                     format="R$ %.2f"
                    #                 ),
                    #                 "margem_total": st.column_config.NumberColumn(
                    #                     "Margem Total",
                    #                     format="R$ %.2f"
                    #                 ),
                    #                 "total_cartoes": st.column_config.NumberColumn(
                    #                     "Comprometido",
                    #                     format="R$ %.2f"
                    #                 ),
                    #                 "percentual_utilizado": st.column_config.NumberColumn(
                    #                     "% Utilizado",
                    #                     format="%.1f%%"
                    #                 )
                    #             },
                    #             hide_index=True,
                    #             use_container_width=True
                    #         )
                    #     else:
                    #         st.info("Nenhum servidor com margem disponível positiva.")
                    # else:
                    #     st.warning("⚠️ Não foi possível calcular margem para os holerites processados.")
                    
                    # Top 10 Oportunidades
                    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
                    st.markdown("<h3 class='section-header'>Top 10 Servidores com Mais Oportunidades</h3>", unsafe_allow_html=True)
                    oportunidades_df = df[df['tipo_oportunidade'] == 'CONHECIDA']
                    
                    if not oportunidades_df.empty:
                        top_servidores = oportunidades_df.groupby(['nome', 'matricula']).agg({
                            'descricao': 'count',
                            'liquido': 'first',
                            'regime': 'first'
                        }).rename(columns={'descricao': 'qtd_oportunidades'})
                        
                        top_servidores = top_servidores.sort_values('qtd_oportunidades', ascending=False).head(10)
                        top_servidores = top_servidores.reset_index()
                        
                        st.dataframe(
                            top_servidores,
                            column_config={
                                "nome": st.column_config.TextColumn("Nome", width="medium"),
                                "matricula": st.column_config.TextColumn("Matrícula", width="small"),
                                "qtd_oportunidades": st.column_config.NumberColumn(
                                    "Oportunidades",
                                    format="%d"
                                ),
                                "liquido": st.column_config.NumberColumn(
                                    "Líquido",
                                    format="R$ %.2f"
                                ),
                                "regime": st.column_config.TextColumn("Regime", width="small")
                            },
                            hide_index=True,
                            use_container_width=True
                        )
                    
                    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
                    
                    # Tabela completa
                    st.markdown("<h3 class='section-header'>Resultados Completos</h3>", unsafe_allow_html=True)
                    
                    # Filtros
                    col1, col2, col3 = st.columns(3, gap="medium")
                    
                    with col1:
                        filtro_tipo = st.multiselect(
                            "Filtrar por Tipo",
                            options=df['tipo_oportunidade'].unique(),
                            default=df['tipo_oportunidade'].unique()
                        )
                    
                    with col2:
                        filtro_regime = st.multiselect(
                            "Filtrar por Regime",
                            options=df['regime'].unique(),
                            default=df['regime'].unique()
                        )
                    
                    with col3:
                        busca = st.text_input("Buscar por nome")
                    
                    # Aplicar filtros
                    df_filtrado = df[
                        (df['tipo_oportunidade'].isin(filtro_tipo)) &
                        (df['regime'].isin(filtro_regime))
                    ]
                    
                    if busca:
                        df_filtrado = df_filtrado[
                            df_filtrado['nome'].str.contains(busca, case=False, na=False)
                        ]
                    
                    st.markdown(f"<p style='color: #666; font-size: 0.9rem; margin: 1rem 0;'><strong>Exibindo {len(df_filtrado)} resultado(s)</strong></p>", unsafe_allow_html=True)
                    
                    df_filtrado = df_filtrado.drop(
                        columns=["margem_disponivel", "margem_total", "total_cartoes", "percentual_utilizado", "vencimentos", "descontos"]
                    )
                    
                    st.dataframe(



                        df_filtrado,
                        column_config={
                            "arquivo": "Arquivo",
                            "nome": "Nome",
                            "matricula": "Matrícula",
                            "regime": "Regime",
                            "vencimentos": st.column_config.NumberColumn(
                                "Vencimentos",
                                format="R$ %.2f"
                            ),
                            "descontos": st.column_config.NumberColumn(
                                "Descontos",
                                format="R$ %.2f"
                            ),
                            "liquido": st.column_config.NumberColumn(
                                "Líquido",
                                format="R$ %.2f"
                            ),
                            "margem_disponivel": st.column_config.NumberColumn(
                                "Margem Disp.",
                                                               format="R$ %.2f",
                                help="Margem disponível para novos empréstimos"
                            ),
                            "margem_total": st.column_config.NumberColumn(
                                "Margem Total",
                                format="R$ %.2f",
                                help="30% dos descontos fixos"
                            ),
                            "total_cartoes": st.column_config.NumberColumn(
                                "Total Cartões",
                                format="R$ %.2f",
                                help="Total comprometido com cartões"
                            ),
                            "percentual_utilizado": st.column_config.NumberColumn(
                                "% Utilizado",
                                format="%.1f%%",
                                help="Percentual da margem já utilizada"
                            ),
                            "tipo_oportunidade": "Tipo",
                            "descricao": "Descrição",
                            "status": "Status"
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    # Exportar
                    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
                    st.markdown("<h3 class='section-header'>Exportar Resultados</h3>", unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2, gap="medium")
                    
                    with col1:
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            df_filtrado.to_excel(writer, index=False, sheet_name='Oportunidades')
                        buffer.seek(0)
                        
                        st.download_button(
                            label="Baixar Excel",
                            data=buffer,
                            file_name=f"oportunidades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    
                    with col2:
                        csv = df_filtrado.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="Baixar CSV",
                            data=csv,
                            file_name=f"oportunidades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )

    # Footer
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    st.markdown("""
        <div class='footer-text'>
            <p style='font-size: 1.1rem; font-weight: 600; color: #1a3a52; margin-bottom: 0.5rem;'>Analisador de Holerite</p>
            <p style='color: #999;'>v2.0 | Sistema de Análise de Oportunidades de Crédito</p>
            <p style='color: #bbb; font-size: 0.85rem; margin-top: 1rem;'>Desenvolvido para maximizar suas oportunidades</p>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
