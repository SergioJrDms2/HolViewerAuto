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

st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
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
    "STARBANK"
]

# Cartões de terceiros (concorrentes)
CARTOES_CONHECIDOS = [
    "NIO",
    "DAYCOVAL",
    "BMG",
    "PAN",
    "VEMCARD",
    "PIXCARD",
    "MEUCASHCARD",
    "PINE",
    "BRADESCO"
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
    
    if "ESTATUTARIO" in texto_normalizado or "ESTATUARIO" in texto_normalizado:
        return "ESTATUTÁRIO"
    elif "CLT" in texto_normalizado:
        return "CLT"
    elif "COMISSIONADO" in texto_normalizado:
        return "COMISSIONADO"
    elif "TEMPORARIO" in texto_normalizado or "TEMPORÁRIO" in texto_normalizado:
        return "TEMPORÁRIO"
    else:
        return "NÃO IDENTIFICADO"

def identificar_cartoes_credito(texto: str) -> Dict[str, List[str]]:
    """Identifica cartões de crédito no texto (FILTRA RIGOROSAMENTE EMPRÉSTIMOS)"""
    texto_normalizado = normalizar_texto(texto)
    linhas = texto_normalizado.split('\n')
    
    # Lista de termos que, se encontrados, invalidam a linha imediatamente
    # Adicionei espaços em " EMP " e "EMP " para evitar confundir com "EMPRESARIAL"
    TERMOS_EXCLUSAO = [
        'EMPRESTIMO', 'EMP ', ' EMP', 'CONSIGNADO', 
        'FINANCIAMENTO', 'CREDITO PESSOAL', 'CP '
    ]

    cartoes_encontrados = {
        'nossos_contratos': [],
        'conhecidos': [],
        'desconhecidos': []
    }
    
    # ---------------------------------------------------------
    # 1. Nossos Produtos (Com filtro de exclusão)
    # ---------------------------------------------------------
    for produto in NOSSOS_PRODUTOS:
        if produto in texto_normalizado:
            for linha in linhas:
                # Verifica se é produto nosso E se tem palavras de cartão
                if produto in linha and any(kw in linha for kw in ['CARTAO', 'CRED', 'ANTICIPAY', 'STARCARD', 'STARBANK']):
                    
                    # LOGICA NOVA: Se tiver termo de empréstimo, PULA esta linha
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
                if cartao in linha and any(kw in linha for kw in ['CARTAO', 'CRED', 'CART.', 'CART']):
                    
                    # LOGICA NOVA: Bloqueia empréstimos
                    if any(termo in linha for termo in TERMOS_EXCLUSAO):
                        continue

                    if linha.strip() not in cartoes_encontrados['conhecidos']:
                        cartoes_encontrados['conhecidos'].append(linha.strip())
    
    # ---------------------------------------------------------
    # 3. Desconhecidos (Com filtro de exclusão)
    # ---------------------------------------------------------
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        # Verifica se parece emprestimo ANTES de qualquer coisa
        if any(termo in linha_norm for termo in TERMOS_EXCLUSAO):
            continue

        tem_keyword_cartao = any(kw in linha_norm for kw in 
                                  ['CARTAO', 'CART ', 'CRED', 'CREDITO','CART.'])
        
        if tem_keyword_cartao:
            eh_nosso = any(produto in linha_norm for produto in NOSSOS_PRODUTOS)
            eh_conhecido = any(cartao in linha_norm for cartao in CARTOES_CONHECIDOS)
            
            if not eh_nosso and not eh_conhecido and linha.strip():
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
        if 'NOME' in linha and i + 1 < len(linhas):
            info['nome'] = linhas[i + 1].strip()
        
        if 'MATRICULA' in linha:
            match = re.search(r'(\d{6})', linha)
            if match:
                info['matricula'] = match.group(1)
        
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
    Extrai vencimentos fixos (adicionais de tempo de serviço, 6ª parte, etc.)
    da coluna de VENCIMENTOS
    """
    linhas = texto.split('\n')
    
    vencimentos_fixos = {
        'adicional_tempo_servico': 0.0,
        'sexta_parte': 0.0,
        'outros_fixos': [],
        'total': 0.0
    }
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        # Adicional de Tempo de Serviço
        if 'ADICIONAL TEMPO SERVICO' in linha_norm or 'ADICIONAL TEMPO' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['adicional_tempo_servico'] = valor
                vencimentos_fixos['total'] += valor
                
        
        # 6ª Parte
        elif '6A.PARTE' in linha_norm or '6A PARTE' in linha_norm or 'SEXTA PARTE' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['sexta_parte'] = valor
                vencimentos_fixos['total'] += valor

        elif 'AULA SUPLEMENTAR' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['outros_fixos'].append({
                    'descricao': linha.strip(),
                    'valor': valor
                })
                vencimentos_fixos['total'] += valor


        elif 'GRAT' in linha_norm and 'INCORPORADA' in linha_norm:
            valor = extrair_valores_vencimento(linha)
            if valor > 0:
                vencimentos_fixos['outros_fixos'].append({
                    'descricao': linha.strip(),
                    'valor': valor
                })
                vencimentos_fixos['total'] += valor

        
        # Outros vencimentos fixos comuns
        elif any(palavra in linha_norm for palavra in ['HORA ATIV', 'EXTRA CLASSE', 'ATIV.EXTRA' 'INSALUBRIDADE', 'PERICULOSIDADE', 'ADICIONAL NOTURNO']):
            # Garante que não é desconto
            if 'DESCONTO' not in linha_norm:
                valor = extrair_valores_vencimento(linha)
                if valor > 0:
                    vencimentos_fixos['outros_fixos'].append({
                        'descricao': linha.strip(),
                        'valor': valor
                    })
                    vencimentos_fixos['total'] += valor
    
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
        elif any(palavra in linha_norm for palavra in ['PREV', 'PREVIDENCIA', 'RPPS', 'UASPREV', 'IPSM', 'FUNPREV']):
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


def extrair_valores_vencimento(linha: str) -> float:
    """
    Extrai o valor da coluna de VENCIMENTOS (penúltimo valor numérico)
    """
    valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}', linha)
    if len(valores) >= 2:
        # Penúltimo valor é a coluna de vencimentos
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




def extrair_valores_cartoes(texto: str, cartoes_encontrados: Dict) -> Dict:
    """
    Extrai os valores dos descontos de cartões identificados
    Usa a coluna de DESCONTOS
    """
    valores_cartoes = {
        'nossos_contratos': [],
        'conhecidos': [],
        'desconhecidos': [],
        'total': 0.0
    }
    
    # Processa nossos contratos
    for cartao_linha in cartoes_encontrados.get('nossos_contratos', []):
        valor = extrair_valores_desconto(cartao_linha)
        if valor > 0:
            valores_cartoes['nossos_contratos'].append({
                'descricao': cartao_linha.strip(),
                'valor': valor
            })
            valores_cartoes['total'] += valor
    
    # Processa cartões conhecidos
    for cartao_linha in cartoes_encontrados.get('conhecidos', []):
        valor = extrair_valores_desconto(cartao_linha)
        if valor > 0:
            valores_cartoes['conhecidos'].append({
                'descricao': cartao_linha.strip(),
                'valor': valor
            })
            valores_cartoes['total'] += valor
    
    # Processa cartões desconhecidos
    for cartao_linha in cartoes_encontrados.get('desconhecidos', []):
        valor = extrair_valores_desconto(cartao_linha)
        if valor > 0:
            valores_cartoes['desconhecidos'].append({
                'descricao': cartao_linha.strip(),
                'valor': valor
            })
            valores_cartoes['total'] += valor
    
    return valores_cartoes


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
# FUNÇÃO PRINCIPAL DE ANÁLISE
# ============================================================================

def analisar_holerite_streamlit(arquivo_bytes: bytes, nome_arquivo: str) -> Dict:
    """Analisa um holerite e retorna os resultados - VERSÃO CORRIGIDA"""
    texto = extrair_texto_pdf(arquivo_bytes)
    
    if not texto.strip():
        return None
    
    regime = extrair_regime_contrato(texto)
    info_financeira = extrair_informacoes_financeiras(texto)
    cartoes = identificar_cartoes_credito(texto)
    
    # Extrai dados para cálculo de margem de CARTÃO
    salario_base = extrair_salario_bruto(texto)
    vencimentos_fixos = extrair_vencimentos_fixos(texto)
    descontos_obrigatorios = extrair_descontos_obrigatorios(texto)
    valores_cartoes = extrair_valores_cartoes(texto, cartoes)
    
    # Calcula margem disponível para cartão (10% do salário)
    margem = calcular_margem_disponivel(
        salario_base, 
        vencimentos_fixos,
        descontos_obrigatorios,
        valores_cartoes,
        percentual_permitido=0.15  # 10% para cartão
    )
    
    # Mantém os descontos fixos originais para exibição (se necessário)
    descontos_fixos_completos = extrair_descontos_fixos(texto)
    
    return {
        'arquivo': nome_arquivo,
        'regime': regime,
        'info_financeira': info_financeira,
        'nossos_contratos': cartoes['nossos_contratos'],
        'cartoes_conhecidos': cartoes['conhecidos'],
        'cartoes_desconhecidos': cartoes['desconhecidos'],
        'descontos_fixos': descontos_fixos_completos,
        'descontos_obrigatorios': descontos_obrigatorios,
        'vencimentos_fixos': vencimentos_fixos,
        'valores_cartoes': valores_cartoes,
        'margem': margem,
        'texto_completo': texto
    }

def processar_multiplos_pdfs(arquivos_uploaded) -> pd.DataFrame:
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
            resultado = analisar_holerite_streamlit(arquivo_bytes, arquivo_uploaded.name)
            
            if resultado:
                info = resultado['info_financeira']
                margem = resultado['margem']
                
                # Adiciona oportunidades conhecidas
                if resultado['cartoes_conhecidos']:
                    for cartao in resultado['cartoes_conhecidos']:
                        resultados.append({
                            'arquivo': resultado['arquivo'],
                            'nome': info.get('nome', 'N/A'),
                            'matricula': info.get('matricula', 'N/A'),
                            'regime': resultado['regime'],
                            'vencimentos': info.get('vencimentos_total', 0),
                            'descontos': info.get('descontos_total', 0),
                            'liquido': info.get('liquido', 'N/A'),
                            'margem_disponivel': margem['margem_disponivel'],
                            'margem_total': margem['margem_total'],
                            'total_cartoes': margem['total_cartoes'],
                            'percentual_utilizado': margem['percentual_utilizado'],
                            'tipo_oportunidade': 'CONHECIDA',
                            'descricao': cartao,
                            'status': '✅ OPORTUNIDADE CONFIRMADA'
                        })

                # Adiciona nossos contratos
                if resultado['nossos_contratos']:
                    for cartao in resultado['nossos_contratos']:
                        resultados.append({
                            'arquivo': resultado['arquivo'],
                            'nome': info.get('nome', 'N/A'),
                            'matricula': info.get('matricula', 'N/A'),
                            'regime': resultado['regime'],
                            'vencimentos': info.get('vencimentos_total', 0),
                            'descontos': info.get('descontos_total', 0),
                            'liquido': info.get('liquido', 'N/A'),
                            'margem_disponivel': margem['margem_disponivel'],
                            'margem_total': margem['margem_total'],
                            'total_cartoes': margem['total_cartoes'],
                            'percentual_utilizado': margem['percentual_utilizado'],
                            'tipo_oportunidade': 'NOSSOS CONTRATOS',
                            'descricao': cartao,
                            'status': '🏆 CLIENTE NOSSO'
                        })
                
                # Adiciona cartões para estudar
                if resultado['cartoes_desconhecidos']:
                    for cartao in resultado['cartoes_desconhecidos']:
                        resultados.append({
                            'arquivo': resultado['arquivo'],
                            'nome': info.get('nome', 'N/A'),
                            'matricula': info.get('matricula', 'N/A'),
                            'regime': resultado['regime'],
                            'vencimentos': info.get('vencimentos_total', 0),
                            'descontos': info.get('descontos_total', 0),
                            'liquido': info.get('liquido', 'N/A'),
                            'margem_disponivel': margem['margem_disponivel'],
                            'margem_total': margem['margem_total'],
                            'total_cartoes': margem['total_cartoes'],
                            'percentual_utilizado': margem['percentual_utilizado'],
                            'tipo_oportunidade': 'PARA ESTUDAR',
                            'descricao': cartao,
                            'status': '⚠️ VERIFICAR'
                        })
                
                # Se não tem oportunidades
                if not resultado['cartoes_conhecidos'] and not resultado['cartoes_desconhecidos']:
                    resultados.append({
                        'arquivo': resultado['arquivo'],
                        'nome': info.get('nome', 'N/A'),
                        'matricula': info.get('matricula', 'N/A'),
                        'regime': resultado['regime'],
                        'vencimentos': info.get('vencimentos_total', 0),
                        'descontos': info.get('descontos_total', 0),
                        'liquido': info.get('liquido', 'N/A'),
                        'margem_disponivel': margem['margem_disponivel'],
                        'margem_total': margem['margem_total'],
                        'total_cartoes': margem['total_cartoes'],
                        'percentual_utilizado': margem['percentual_utilizado'],
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
    # Header
    st.markdown('<h1 class="main-header">💳 Analisador de Holerite</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #666;">Sistema de Identificação de Oportunidades de Compra de Dívida</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/000000/bank-card-back-side.png", width=80)
        st.title("⚙️ Configurações")
        
        modo = st.radio(
            "Modo de Análise",
            ["📄 Análise Individual", "📊 Análise em Lote"],
            help="Escolha entre analisar um único PDF ou múltiplos PDFs"
        )
        
        st.markdown("---")
        
        st.subheader("🏆 Nossos Produtos")
        with st.expander("Ver lista"):
            for produto in NOSSOS_PRODUTOS:
                st.text(f"⭐ {produto}")
        
        st.subheader("📋 Cartões Concorrentes")
        with st.expander("Ver lista"):
            for cartao in CARTOES_CONHECIDOS:
                st.text(f"✓ {cartao}")
        
        st.markdown("---")
        
        st.info("💡 **Dica:** Você pode fazer upload de múltiplos PDFs de uma vez no modo de análise em lote!")
    
    # Conteúdo principal
    if modo == "📄 Análise Individual":
        st.header("📄 Análise Individual de Holerite")
        
        arquivo_upload = st.file_uploader(
            "Faça upload do PDF do holerite",
            type=['pdf'],
            help="Selecione um arquivo PDF para análise"
        )
        
        if arquivo_upload:
            col1, col2 = st.columns([3, 1])
            
            with col2:
                if st.button("🔍 Analisar", type="primary", use_container_width=True):
                    with st.spinner("Analisando holerite..."):
                        arquivo_bytes = arquivo_upload.read()
                        resultado = analisar_holerite_streamlit(arquivo_bytes, arquivo_upload.name)
                        
                        if resultado:
                            st.session_state['resultado_individual'] = resultado
            
            if 'resultado_individual' in st.session_state:
                resultado = st.session_state['resultado_individual']
                
                st.success("✅ Análise concluída com sucesso!")
                
                # Informações do servidor
                st.subheader("👤 Informações do Servidor")
                info = resultado['info_financeira']
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Nome", info.get('nome', 'N/A'))
                
                with col2:
                    st.metric("Regime", resultado['regime'])
                
                with col3:
                    st.metric("Líquido", f"R$ {info.get('liquido', 0):,.2f}")
                
                st.markdown("---")

                # Analise de margem
                st.subheader("💰 Análise de Margem para Cartão de Crédito")
                margem = resultado.get('margem', {})
                
                # CORREÇÃO: Verificar se há margem calculada usando as chaves corretas
                if margem.get('base_calculo', 0) > 0:
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric(
                            "Salário Base",
                            f"R$ {margem['salario_base']:,.2f}",
                            help="Vencimentos Estatutários"
                        )
                    
                    with col2:
                        st.metric(
                            "Base de Cálculo",
                            f"R$ {margem['base_calculo']:,.2f}",
                            help="Base + Vencimentos Fixos - Descontos Obrigatórios"
                        )
                    
                    with col3:
                        st.metric(
                            "Margem Total (10%)",
                            f"R$ {margem['margem_total']:,.2f}",
                            help="10% da base de cálculo para cartão"
                        )
                    
                    with col4:
                        margem_disp = margem['margem_disponivel']
                        delta_color = "normal" if margem_disp >= 0 else "inverse"
                        st.metric(
                            "Margem Disponível",
                            f"R$ {margem_disp:,.2f}",
                            delta=f"{margem['percentual_utilizado']:.1f}% utilizado",
                            delta_color=delta_color,
                            help="Margem disponível após descontar cartões atuais"
                        )
                    
                    # Informações complementares
                    st.markdown("---")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric(
                            "Vencimentos Fixos",
                            f"R$ {margem['total_vencimentos_fixos']:,.2f}",
                            help="Adicional Tempo + 6ª Parte + outros"
                        )
                    
                    with col2:
                        st.metric(
                            "Descontos Obrigatórios",
                            f"R$ {margem['total_descontos_obrigatorios']:,.2f}",
                            help="INSS + IRRF + Previdência"
                        )
                    
                    with col3:
                        st.metric(
                            "Comprometido com Cartões",
                            f"R$ {margem['total_cartoes']:,.2f}",
                            help="Total de descontos com cartões"
                        )
                    
                    # Barra de progresso
                    st.markdown("---")
                    st.markdown("**Utilização da Margem de Cartão:**")
                    percentual = min(margem['percentual_utilizado'], 100)
                    
                    if percentual <= 50:
                        cor = "🟢"
                        status_margem = "Ótima margem disponível"
                    elif percentual <= 80:
                        cor = "🟡"
                        status_margem = "Margem moderada"
                    elif percentual <= 100:
                        cor = "🟠"
                        status_margem = "Margem quase esgotada"
                    else:
                        cor = "🔴"
                        status_margem = "Margem excedida"
                    
                    st.progress(min(percentual / 100, 1.0))
                    st.caption(f"{cor} {status_margem} - {percentual:.1f}% da margem comprometida")
                    
                    # Detalhamento da composição da base
                    with st.expander("📋 Ver composição da base de cálculo"):
                        st.write("**Cálculo da Margem:**")
                        st.write(f"1. Salário Base: R$ {margem['salario_base']:,.2f}")
                        
                        vencimentos_fixos = resultado.get('vencimentos_fixos', {})
                        if vencimentos_fixos.get('adicional_tempo_servico', 0) > 0:
                            st.write(f"2. Adicional Tempo Serviço: + R$ {vencimentos_fixos['adicional_tempo_servico']:,.2f}")
                        if vencimentos_fixos.get('sexta_parte', 0) > 0:
                            st.write(f"3. 6ª Parte: + R$ {vencimentos_fixos['sexta_parte']:,.2f}")
                        
                        descontos_obrig = resultado.get('descontos_obrigatorios', {})
                        if descontos_obrig.get('inss', 0) > 0:
                            st.write(f"4. INSS: - R$ {descontos_obrig['inss']:,.2f}")
                        if descontos_obrig.get('irrf', 0) > 0:
                            st.write(f"5. IRRF: - R$ {descontos_obrig['irrf']:,.2f}")
                        if descontos_obrig.get('previdencia', 0) > 0:
                            st.write(f"6. Previdência: - R$ {descontos_obrig['previdencia']:,.2f}")
                        
                        st.write("---")
                        st.write(f"**Base de Cálculo: R$ {margem['base_calculo']:,.2f}**")
                        st.write(f"**Margem para Cartão (10%): R$ {margem['margem_total']:,.2f}**")
                    
                    # Detalhamento dos cartões
                    valores_cartoes = resultado.get('valores_cartoes', {})
                    if valores_cartoes.get('total', 0) > 0:
                        with st.expander("💳 Ver detalhamento dos cartões identificados"):
                            if valores_cartoes.get('nossos_contratos'):
                                st.write("**🏆 Nossos Contratos:**")
                                for item in valores_cartoes['nossos_contratos']:
                                    st.write(f"- {item['descricao']}: R$ {item['valor']:,.2f}")
                            
                            if valores_cartoes.get('conhecidos'):
                                st.write("**✅ Concorrentes:**")
                                for item in valores_cartoes['conhecidos']:
                                    st.write(f"- {item['descricao']}: R$ {item['valor']:,.2f}")
                            
                            if valores_cartoes.get('desconhecidos'):
                                st.write("**⚠️ Outros:**")
                                for item in valores_cartoes['desconhecidos']:
                                    st.write(f"- {item['descricao']}: R$ {item['valor']:,.2f}")
                else:
                    st.warning("⚠️ Não foi possível calcular a margem disponível. Verifique se o holerite contém informações completas de salário e descontos.")
                
                
                st.markdown("---")
                
                # Nossos Contratos
                if resultado['nossos_contratos']:
                    st.subheader("🏆 Nossos Contratos (Cliente Já É Nosso)")
                    for i, contrato in enumerate(resultado['nossos_contratos'], 1):
                        st.markdown(f"**{i}.** {contrato}")
                    st.info(f"✨ Este cliente já possui {len(resultado['nossos_contratos'])} contrato(s) conosco!")
                    st.markdown("---")
                
                # Oportunidades
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("✅ Oportunidades Confirmadas")
                    if resultado['cartoes_conhecidos']:
                        for i, cartao in enumerate(resultado['cartoes_conhecidos'], 1):
                            st.markdown(f"**{i}.** {cartao}")
                        st.success(f"Total: {len(resultado['cartoes_conhecidos'])} oportunidade(s)")
                    else:
                        st.info("Nenhuma oportunidade confirmada encontrada.")
                
                with col2:
                    st.subheader("⚠️ Itens para Estudar")
                    if resultado['cartoes_desconhecidos']:
                        for i, cartao in enumerate(resultado['cartoes_desconhecidos'], 1):
                            st.markdown(f"**{i}.** {cartao}")
                        st.warning(f"Total: {len(resultado['cartoes_desconhecidos'])} item(ns) para análise")
                    else:
                        st.success("Todos os cartões estão na lista conhecida.")
    
    else:  # Análise em Lote
        st.header("📊 Análise em Lote de Holerites")
        
        arquivos_upload = st.file_uploader(
            "Faça upload dos PDFs dos holerites",
            type=['pdf'],
            accept_multiple_files=True,
            help="Selecione múltiplos arquivos PDF para análise em lote"
        )
        
        if arquivos_upload:
            st.info(f"📁 {len(arquivos_upload)} arquivo(s) carregado(s)")
            
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                if st.button("🚀 Processar Todos", type="primary", use_container_width=True):
                    with st.spinner("Processando arquivos..."):
                        df = processar_multiplos_pdfs(arquivos_upload)
                        st.session_state['df_resultados'] = df
                        st.success(f"✅ {len(arquivos_upload)} arquivo(s) processado(s) com sucesso!")
            
            if 'df_resultados' in st.session_state:
                df = st.session_state['df_resultados']
                
                if not df.empty:
                    # Dashboard de Estatísticas
                    st.subheader("📊 Dashboard de Resultados")
                    
                    col1, col2, col3, col4, col5 = st.columns(5)
                    
                    with col1:
                        total_oportunidades = len(df[df['tipo_oportunidade'] == 'CONHECIDA'])
                        st.metric("✅ Oportunidades", total_oportunidades, 
                                help="Total de oportunidades confirmadas")
                    
                    with col2:
                        total_estudar = len(df[df['tipo_oportunidade'] == 'PARA ESTUDAR'])
                        st.metric("⚠️ Para Estudar", total_estudar,
                                help="Cartões fora da lista conhecida")
                    
                    with col3:
                        total_sem = len(df[df['tipo_oportunidade'] == 'NENHUMA'])
                        st.metric("ℹ️ Sem Oportunidade", total_sem,
                                help="Servidores sem oportunidades")
                    
                    with col4:
                        total_servidores = df['nome'].nunique()
                        st.metric("👥 Servidores", total_servidores,
                                help="Total de servidores únicos")
                    
                    with col5:
                        df_com_margem = df[df['margem_disponivel'].notna()]
                        if not df_com_margem.empty:
                            margem_por_servidor = df_com_margem.groupby('matricula')['margem_disponivel'].first()
                            media_margem = margem_por_servidor.mean()
                            st.metric("💰 Margem Média", f"R$ {media_margem:,.2f}",
                                    help="Média de margem disponível por servidor")
                        else:
                            st.metric("💰 Margem Média", "N/A",
                                    help="Não foi possível calcular")
                    
                    st.markdown("---")
                    
                    # Gráficos
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("📈 Distribuição por Tipo")
                        tipo_counts = df['tipo_oportunidade'].value_counts()
                        fig_tipo = px.pie(
                            values=tipo_counts.values,
                            names=tipo_counts.index,
                            title="Tipos de Oportunidade",
                            color_discrete_sequence=px.colors.qualitative.Set3
                        )
                        st.plotly_chart(fig_tipo, use_container_width=True)
                    
                    with col2:
                        st.subheader("📊 Distribuição por Regime")
                        regime_counts = df['regime'].value_counts()
                        fig_regime = px.bar(
                            x=regime_counts.index,
                            y=regime_counts.values,
                            title="Servidores por Regime",
                            labels={'x': 'Regime', 'y': 'Quantidade'},
                            color=regime_counts.values,
                            color_continuous_scale='Blues'
                        )
                        st.plotly_chart(fig_regime, use_container_width=True)
                    
                    # Análise de Margem
                    st.subheader("💰 Análise de Margem Disponível")
                    
                    df_margem = df.groupby('matricula').agg({
                        'nome': 'first',
                        'margem_disponivel': 'first',
                        'margem_total': 'first',
                        'total_cartoes': 'first',
                        'percentual_utilizado': 'first'
                    }).reset_index()
                    
                    df_margem = df_margem[df_margem['margem_disponivel'].notna()]
                    
                    if not df_margem.empty:
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            fig_hist_margem = px.histogram(
                                df_margem,
                                x='margem_disponivel',
                                nbins=20,
                                title="Distribuição de Margem Disponível",
                                labels={'margem_disponivel': 'Margem Disponível (R$)', 'count': 'Quantidade'},
                                color_discrete_sequence=['#1f77b4']
                            )
                            fig_hist_margem.add_vline(x=0, line_dash="dash", line_color="red", 
                                                     annotation_text="Zero", annotation_position="top")
                            st.plotly_chart(fig_hist_margem, use_container_width=True)
                        
                        with col2:
                            fig_scatter = px.scatter(
                                df_margem,
                                x='margem_total',
                                y='total_cartoes',
                                size='percentual_utilizado',
                                hover_data=['nome', 'margem_disponivel'],
                                title="Margem Total vs Comprometimento",
                                labels={
                                    'margem_total': 'Margem Total (R$)',
                                    'total_cartoes': 'Total Comprometido (R$)'
                                },
                                color='margem_disponivel',
                                color_continuous_scale='RdYlGn'
                            )
                            max_val = max(df_margem['margem_total'].max(), df_margem['total_cartoes'].max())
                            fig_scatter.add_trace(go.Scatter(
                                x=[0, max_val],
                                y=[0, max_val],
                                mode='lines',
                                line=dict(dash='dash', color='red'),
                                name='100% Utilização',
                                showlegend=True
                            ))
                            st.plotly_chart(fig_scatter, use_container_width=True)
                        
                        # Top 10 com melhor margem
                        st.markdown("---")
                        st.subheader("🌟 Top 10 Servidores com Melhor Margem Disponível")
                        
                        df_margem_positiva = df_margem[df_margem['margem_disponivel'] > 0]
                        
                        if not df_margem_positiva.empty:
                            top_margem = df_margem_positiva.nlargest(10, 'margem_disponivel')[
                                ['nome', 'matricula', 'margem_disponivel', 'margem_total', 'total_cartoes', 'percentual_utilizado']
                            ]
                            
                            st.dataframe(
                                top_margem,
                                column_config={
                                    "nome": "Nome",
                                    "matricula": "Matrícula",
                                    "margem_disponivel": st.column_config.NumberColumn(
                                        "Margem Disponível",
                                        format="R$ %.2f"
                                    ),
                                    "margem_total": st.column_config.NumberColumn(
                                        "Margem Total",
                                        format="R$ %.2f"
                                    ),
                                    "total_cartoes": st.column_config.NumberColumn(
                                        "Comprometido",
                                        format="R$ %.2f"
                                    ),
                                    "percentual_utilizado": st.column_config.NumberColumn(
                                        "% Utilizado",
                                        format="%.1f%%"
                                    )
                                },
                                hide_index=True,
                                use_container_width=True
                            )
                        else:
                            st.info("Nenhum servidor com margem disponível positiva.")
                    else:
                        st.warning("⚠️ Não foi possível calcular margem para os holerites processados.")
                    
                    # Top 10 Oportunidades
                    st.markdown("---")
                    st.subheader("🏆 Top 10 Servidores com Mais Oportunidades")
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
                                "nome": "Nome",
                                "matricula": "Matrícula",
                                "qtd_oportunidades": st.column_config.NumberColumn(
                                    "Oportunidades",
                                    format="%d 💳"
                                ),
                                "liquido": st.column_config.NumberColumn(
                                    "Líquido",
                                    format="R$ %.2f"
                                ),
                                "regime": "Regime"
                            },
                            hide_index=True,
                            use_container_width=True
                        )
                    
                    st.markdown("---")
                    
                    # Tabela completa
                    st.subheader("📋 Resultados Completos")
                    
                    # Filtros
                    col1, col2, col3 = st.columns(3)
                    
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
                        busca = st.text_input("🔍 Buscar por nome")
                    
                    # Aplicar filtros
                    df_filtrado = df[
                        (df['tipo_oportunidade'].isin(filtro_tipo)) &
                        (df['regime'].isin(filtro_regime))
                    ]
                    
                    if busca:
                        df_filtrado = df_filtrado[
                            df_filtrado['nome'].str.contains(busca, case=False, na=False)
                        ]
                    
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
                                "Margem Disponível",
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
                    st.markdown("---")
                    st.subheader("💾 Exportar Resultados")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            df_filtrado.to_excel(writer, index=False, sheet_name='Oportunidades')
                        buffer.seek(0)
                        
                        st.download_button(
                            label="📥 Download Excel (Todos)",
                            data=buffer,
                            file_name=f"oportunidades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    
                    with col2:
                        csv = df_filtrado.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="📥 Download CSV",
                            data=csv,
                            file_name=f"oportunidades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #666; padding: 2rem;">
            <p>💳 <strong>Analisador de Holerite</strong> v2.0</p>
            <p>Sistema de Identificação de Oportunidades de Compra de Dívida com Cálculo de Margem</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
