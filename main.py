"""
Analisador de Holerite - Aplicação Streamlit
Sistema de Identificação de Oportunidades de Compra de Dívida
Versão 3.0 - Foco em Margem de Cartão

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
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# BASE DE DADOS DE CARTÕES CONHECIDOS
# ============================================================================

NOSSOS_PRODUTOS = [
    "STARCARD",
    "ANTICIPAY",
    "STARBANK"
]

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

def extrair_valores_linha(linha: str) -> float:
    """Extrai o último valor numérico de uma linha"""
    valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}', linha)
    if valores:
        valor_str = valores[-1].replace('.', '').replace(',', '.')
        return float(valor_str)
    return 0.0

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

def extrair_informacoes_financeiras(texto: str) -> Dict:
    """Extrai informações financeiras do holerite"""
    info = {
        'nome': '',
        'matricula': '',
        'vencimentos_total': 0.0,
        'descontos_total': 0.0,
        'liquido': 0.0
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

def extrair_salario_bruto(texto: str) -> float:
    """Extrai o valor do salário bruto do contracheque"""
    texto_normalizado = normalizar_texto(texto)
    linhas = texto.split('\n')
    
    # Prioridade 1: TOTAL DE VENCIMENTOS
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'TOTAL' in linha_norm and ('VENCIMENTO' in linha_norm or 'VENC' in linha_norm):
            if 'DESCONTO' not in linha_norm and 'DESC' not in linha_norm:
                valor = extrair_valores_linha(linha)
                if valor > 0:
                    return valor
    
    # Prioridade 2: Buscar por palavra-chave específica
    keywords_primarias = ['SALARIO BASE', 'SALÁRIO BASE', 'VENCIMENTO BASE', 'REMUNERACAO']
    
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        for keyword in keywords_primarias:
            if keyword in linha_norm:
                if 'DESCONTO' not in linha_norm:
                    valor = extrair_valores_linha(linha)
                    if valor > 0:
                        return valor
    
    # Prioridade 3: SUBSÍDIO
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        if 'SUBSIDIO' in linha_norm or 'SUBSÍDIO' in linha_norm:
            valor = extrair_valores_linha(linha)
            if valor > 0:
                return valor
    
    # Prioridade 4: Usar vencimentos_total
    info = extrair_informacoes_financeiras(texto)
    if info.get('vencimentos_total', 0) > 0:
        return info['vencimentos_total']
    
    return 0.0

def extrair_descontos_fixos(texto: str) -> Dict:
    """Identifica e extrai valores de descontos fixos obrigatórios"""
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

def identificar_cartoes_e_emprestimos(texto: str) -> Dict:
    """
    Identifica e SEPARA cartões de empréstimos
    Retorna dois grupos: cartões e empréstimos
    """
    texto_normalizado = normalizar_texto(texto)
    linhas = texto_normalizado.split('\n')
    
    # Termos que identificam EMPRÉSTIMOS (não cartões)
    TERMOS_EMPRESTIMO = [
        'EMPRESTIMO', 'EMP ', ' EMP', 'CONSIGNADO', 
        'FINANCIAMENTO', 'CREDITO PESSOAL', 'CP '
    ]
    
    resultado = {
        'cartoes': [],  # Apenas cartões
        'emprestimos': [],  # Apenas empréstimos
        'nossos_contratos': []
    }
    
    # Processar todas as linhas
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        
        # Verifica se é empréstimo
        eh_emprestimo = any(termo in linha_norm for termo in TERMOS_EMPRESTIMO)
        
        # Verifica se tem palavras de cartão
        tem_palavra_cartao = any(kw in linha_norm for kw in ['CARTAO', 'CART ', 'CRED', 'CART.'])
        
        # Verifica se é nosso produto
        eh_nosso = any(produto in linha_norm for produto in NOSSOS_PRODUTOS)
        
        # Verifica se é concorrente conhecido
        eh_concorrente = any(cartao in linha_norm for cartao in CARTOES_CONHECIDOS)
        
        # Classificação
        if eh_nosso:
            if not eh_emprestimo and tem_palavra_cartao:
                if linha.strip() not in resultado['nossos_contratos']:
                    resultado['nossos_contratos'].append(linha.strip())
        
        elif eh_emprestimo:
            # É empréstimo consignado
            if linha.strip() not in resultado['emprestimos']:
                resultado['emprestimos'].append(linha.strip())
        
        elif tem_palavra_cartao:
            # É cartão (nosso, concorrente ou desconhecido)
            if linha.strip() not in resultado['cartoes']:
                resultado['cartoes'].append(linha.strip())
    
    return resultado

def extrair_valores_consignaveis(texto: str, itens_identificados: Dict) -> Dict:
    """
    Extrai valores dos itens consignáveis identificados
    Separa em cartões e empréstimos
    """
    valores = {
        'cartoes': [],
        'emprestimos': [],
        'nossos_contratos': [],
        'total_cartoes': 0.0,
        'total_emprestimos': 0.0
    }
    
    # Processa nossos contratos
    for item in itens_identificados.get('nossos_contratos', []):
        valor = extrair_valores_linha(item)
        if valor > 0:
            valores['nossos_contratos'].append({
                'descricao': item.strip(),
                'valor': valor
            })
            valores['total_cartoes'] += valor
    
    # Processa cartões
    for item in itens_identificados.get('cartoes', []):
        valor = extrair_valores_linha(item)
        if valor > 0:
            valores['cartoes'].append({
                'descricao': item.strip(),
                'valor': valor
            })
            valores['total_cartoes'] += valor
    
    # Processa empréstimos
    for item in itens_identificados.get('emprestimos', []):
        valor = extrair_valores_linha(item)
        if valor > 0:
            valores['emprestimos'].append({
                'descricao': item.strip(),
                'valor': valor
            })
            valores['total_emprestimos'] += valor
    
    return valores

def calcular_margem_disponivel(salario_bruto: float, descontos_fixos: Dict, valores_consignaveis: Dict, salario_liquido_real: float = 0.0) -> Dict:
    """
    Calcula a margem disponível separando cartões de empréstimos
    
    Regra:
    - Base de Cálculo = Vencimentos - Descontos Obrigatórios
    - Margem Total = 45% da Base
    - Subdivisão: 35% empréstimo + 5% cartão crédito + 5% cartão benefício
    """
    
    # Soma descontos fixos
    total_descontos_fixos = (
        descontos_fixos['inss'] +
        descontos_fixos['irrf'] +
        descontos_fixos['previdencia'] +
        descontos_fixos['pensao'] +
        descontos_fixos['plano_saude'] +
        descontos_fixos['vale_transporte']
    )
    
    # Valores comprometidos
    total_cartoes_comprometido = valores_consignaveis['total_cartoes']
    total_emprestimos_comprometido = valores_consignaveis['total_emprestimos']
    
    # Base de cálculo
    if salario_liquido_real > 0:
        base_calculo = salario_liquido_real + total_cartoes_comprometido + total_emprestimos_comprometido
    else:
        base_calculo = salario_bruto - total_descontos_fixos
    
    # Margem Total = 45% da base
    margem_total = base_calculo * 0.45
    
    # Subdivisões
    margem_emprestimo_total = base_calculo * 0.35  # 35%
    margem_cartao_total = base_calculo * 0.10  # 10% (5% crédito + 5% benefício)
    margem_cartao_credito_total = base_calculo * 0.05  # 5%
    margem_cartao_beneficio_total = base_calculo * 0.05  # 5%
    
    # Margens disponíveis
    margem_emprestimo_disponivel = margem_emprestimo_total - total_emprestimos_comprometido
    margem_cartao_disponivel = margem_cartao_total - total_cartoes_comprometido
    
    return {
        'salario_bruto': salario_bruto,
        'total_descontos_fixos': total_descontos_fixos,
        'base_calculo': base_calculo,
        'salario_liquido': salario_liquido_real if salario_liquido_real > 0 else base_calculo - total_cartoes_comprometido - total_emprestimos_comprometido,
        
        # Margem de Empréstimo (35%)
        'margem_emprestimo_total': margem_emprestimo_total,
        'margem_emprestimo_comprometida': total_emprestimos_comprometido,
        'margem_emprestimo_disponivel': margem_emprestimo_disponivel,
        'percentual_emprestimo_utilizado': (total_emprestimos_comprometido / margem_emprestimo_total * 100) if margem_emprestimo_total > 0 else 0,
        
        # Margem de Cartão (10% = 5% + 5%)
        'margem_cartao_total': margem_cartao_total,
        'margem_cartao_credito_total': margem_cartao_credito_total,
        'margem_cartao_beneficio_total': margem_cartao_beneficio_total,
        'margem_cartao_comprometida': total_cartoes_comprometido,
        'margem_cartao_disponivel': margem_cartao_disponivel,
        'percentual_cartao_utilizado': (total_cartoes_comprometido / margem_cartao_total * 100) if margem_cartao_total > 0 else 0,
        
        # Total
        'margem_total': margem_total,
        'total_comprometido': total_cartoes_comprometido + total_emprestimos_comprometido,
        'margem_total_disponivel': margem_total - (total_cartoes_comprometido + total_emprestimos_comprometido),
        'percentual_total_utilizado': ((total_cartoes_comprometido + total_emprestimos_comprometido) / margem_total * 100) if margem_total > 0 else 0
    }

# ============================================================================
# FUNÇÃO PRINCIPAL DE ANÁLISE
# ============================================================================

def analisar_holerite_streamlit(arquivo_bytes: bytes, nome_arquivo: str) -> Dict:
    """Analisa um holerite e retorna os resultados"""
    texto = extrair_texto_pdf(arquivo_bytes)
    
    if not texto.strip():
        return None
    
    regime = extrair_regime_contrato(texto)
    info_financeira = extrair_informacoes_financeiras(texto)
    cartoes_emprestimos = identificar_cartoes_e_emprestimos(texto)
    descontos_fixos = extrair_descontos_fixos(texto)
    valores_consignaveis = extrair_valores_consignaveis(texto, cartoes_emprestimos)
    salario_bruto = extrair_salario_bruto(texto)
    
    salario_liquido_real = info_financeira.get('liquido', 0.0)
    
    if salario_bruto == 0.0 and info_financeira.get('vencimentos_total', 0) > 0:
        salario_bruto = info_financeira['vencimentos_total']
    
    margem = calcular_margem_disponivel(
        salario_bruto, 
        descontos_fixos, 
        valores_consignaveis,
        salario_liquido_real=salario_liquido_real
    )
    
    return {
        'arquivo': nome_arquivo,
        'regime': regime,
        'info_financeira': info_financeira,
        'cartoes': cartoes_emprestimos['cartoes'],
        'emprestimos': cartoes_emprestimos['emprestimos'],
        'nossos_contratos': cartoes_emprestimos['nossos_contratos'],
        'descontos_fixos': descontos_fixos,
        'valores_consignaveis': valores_consignaveis,
        'margem': margem,
        'texto_completo': texto
    }

# ============================================================================
# INTERFACE STREAMLIT
# ============================================================================

def main():
    st.markdown('<h1 class="main-header">💳 Analisador de Holerite</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #666;">Análise de Margem Consignável - Foco em Cartões</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/000000/bank-card-back-side.png", width=80)
        st.title("⚙️ Configurações")
        
        st.subheader("🏆 Nossos Produtos")
        with st.expander("Ver lista"):
            for produto in NOSSOS_PRODUTOS:
                st.text(f"⭐ {produto}")
        
        st.subheader("📋 Cartões Concorrentes")
        with st.expander("Ver lista"):
            for cartao in CARTOES_CONHECIDOS:
                st.text(f"✓ {cartao}")
    
    # Upload
    st.header("📄 Análise de Holerite")
    
    arquivo_upload = st.file_uploader(
        "Faça upload do PDF do holerite",
        type=['pdf'],
        help="Selecione um arquivo PDF para análise"
    )
    
    if arquivo_upload:
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
            
            # Análise de Margem - SIMPLIFICADA
            st.subheader("💰 Análise de Margem Consignável")
            margem = resultado.get('margem', {})
            
            # Box com resumo
            st.markdown("""
                <div style="background-color: #28a745; color: white; padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1rem;">
                    <h3 style="margin: 0; color: white;">📊 Resumo da Margem</h3>
                </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 💳 Margem de Cartão")
                st.metric(
                    "Margem Total (10%)",
                    f"R$ {margem.get('margem_cartao_total', 0):,.2f}",
                    help="5% cartão crédito + 5% cartão benefício"
                )
                st.metric(
                    "Já Comprometido",
                    f"R$ {margem.get('margem_cartao_comprometida', 0):,.2f}",
                    delta=f"-{margem.get('percentual_cartao_utilizado', 0):.1f}% usado",
                    delta_color="inverse"
                )
                st.metric(
                    "✨ MARGEM DISPONÍVEL",
                    f"R$ {margem.get('margem_cartao_disponivel', 0):,.2f}",
                    help="Margem que ainda pode ser utilizada para cartões"
                )
                
                # Detalhamento
                st.caption(f"└─ Cartão Crédito (5%): R$ {margem.get('margem_cartao_credito_total', 0):,.2f}")
                st.caption(f"└─ Cartão Benefício (5%): R$ {margem.get('margem_cartao_beneficio_total', 0):,.2f}")
            
            with col2:
                st.markdown("### 💵 Margem de Empréstimo")
                st.metric(
                    "Margem Total (35%)",
                    f"R$ {margem.get('margem_emprestimo_total', 0):,.2f}"
                )
                st.metric(
                    "Já Comprometido",
                    f"R$ {margem.get('margem_emprestimo_comprometida', 0):,.2f}",
                    delta=f"-{margem.get('percentual_emprestimo_utilizado', 0):.1f}% usado",
                    delta_color="inverse"
                )
                st.metric(
                    "✨ MARGEM DISPONÍVEL",
                    f"R$ {margem.get('margem_emprestimo_disponivel', 0):,.2f}"
                )
            
            # Barra de progresso para cartões
            st.markdown("---")
            st.markdown("**Utilização da Margem de Cartão:**")
            perc_cartao = min(margem.get('percentual_cartao_utilizado', 0), 100)
            st.progress(perc_cartao / 100)
            
            if perc_cartao <= 50:
                st.success(f"🟢 Ótima margem disponível - {perc_cartao:.1f}% utilizado")
            elif perc_cartao <= 80:
                st.warning(f"🟡 Margem moderada - {perc_cartao:.1f}% utilizado")
            else:
                st.error(f"🔴 Margem quase esgotada - {perc_cartao:.1f}% utilizado")
            
            # Detalhamento dos cartões identificados
            if resultado['valores_consignaveis']['cartoes'] or resultado['valores_consignaveis']['nossos_contratos']:
                with st.expander("💳 Ver cartões identificados"):
                    if resultado['valores_consignaveis']['nossos_contratos']:
                        st.markdown("**🏆 Nossos Contratos:**")
                        for item in resultado['valores_consignaveis']['nossos_contratos']:
                            st.write(f"- {item['descricao']}: R$ {item['valor']:,.2f}")
                    
                    if resultado['valores_consignaveis']['cartoes']:
                        st.markdown("**💳 Outros Cartões:**")
                        for item in resultado['valores_consignaveis']['cartoes']:
                            st.write(f"- {item['descricao']}: R$ {item['valor']:,.2f}")
            
            # Detalhamento dos empréstimos
            if resultado['valores_consignaveis']['emprestimos']:
                with st.expander("💵 Ver empréstimos identificados"):
                    for item in resultado['valores_consignaveis']['emprestimos']:
                        st.write(f"- {item['descricao']}: R$ {item['valor']:,.2f}")

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #666; padding: 2rem;">
            <p>💳 <strong>Analisador de Holerite</strong> v3.0</p>
            <p>Foco em Margem de Cartão Disponível</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
