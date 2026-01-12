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
    """Identifica cartões de crédito no texto"""
    texto_normalizado = normalizar_texto(texto)
    linhas = texto_normalizado.split('\n')
    
    cartoes_encontrados = {
        'nossos_contratos': [],  # Nova categoria
        'conhecidos': [],
        'desconhecidos': []
    }
    
    # Primeiro identifica nossos contratos
    for produto in NOSSOS_PRODUTOS:
        if produto in texto_normalizado:
            for linha in linhas:
                if produto in linha and any(kw in linha for kw in ['CARTAO', 'EMPRESTIMO', 'CRED', 'ANTICIPAY', 'STARCARD', 'STARBANK']):
                    if linha.strip() not in cartoes_encontrados['nossos_contratos']:
                        cartoes_encontrados['nossos_contratos'].append(linha.strip())
    
    # Depois identifica cartões de terceiros conhecidos
    for cartao in CARTOES_CONHECIDOS:
        if cartao in texto_normalizado:
            for linha in linhas:
                if cartao in linha and any(kw in linha for kw in ['CARTAO', 'EMPRESTIMO', 'CRED']):
                    if linha.strip() not in cartoes_encontrados['conhecidos']:
                        cartoes_encontrados['conhecidos'].append(linha.strip())
    
    # Por último, identifica cartões desconhecidos
    for linha in linhas:
        linha_norm = normalizar_texto(linha)
        tem_keyword_cartao = any(kw in linha_norm for kw in 
                                  ['CARTAO', 'CART ', 'CRED', 'CREDITO', 'CARD'])
        
        if tem_keyword_cartao:
            # Verifica se não é nosso produto
            eh_nosso = any(produto in linha_norm for produto in NOSSOS_PRODUTOS)
            # Verifica se não é de terceiros conhecido
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
        'cargo': '',
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
        
        if 'FUNCAO' in normalizar_texto(linha) or 'TIPO' in linha:
            info['cargo'] = linha.split()[-1] if linha.split() else ''
        
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
        
        if 'LIQUIDO' in normalizar_texto(linha) or 'LÍQUIDO' in linha:
            match = re.search(r'(\d+[.,]\d{2})', linha)
            if match:
                valor = match.group(1).replace('.', '').replace(',', '.')
                info['liquido'] = float(valor)
    
    return info

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
    cartoes = identificar_cartoes_credito(texto)
    
    return {
        'arquivo': nome_arquivo,
        'regime': regime,
        'info_financeira': info_financeira,
        'nossos_contratos': cartoes['nossos_contratos'],  # Nova categoria
        'cartoes_conhecidos': cartoes['conhecidos'],
        'cartoes_desconhecidos': cartoes['desconhecidos'],
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
                
                # Adiciona oportunidades conhecidas
                if resultado['cartoes_conhecidos']:
                    for cartao in resultado['cartoes_conhecidos']:
                        resultados.append({
                            'arquivo': resultado['arquivo'],
                            'nome': info.get('nome', 'N/A'),
                            'matricula': info.get('matricula', 'N/A'),
                            'cargo': info.get('cargo', 'N/A'),
                            'regime': resultado['regime'],
                            'vencimentos': info.get('vencimentos_total', 0),
                            'descontos': info.get('descontos_total', 0),
                            'liquido': info.get('liquido', 0),
                            'tipo_oportunidade': 'CONHECIDA',
                            'descricao': cartao,
                            'status': '✅ OPORTUNIDADE CONFIRMADA'
                        })
                
                # Adiciona cartões para estudar
                if resultado['cartoes_desconhecidos']:
                    for cartao in resultado['cartoes_desconhecidos']:
                        resultados.append({
                            'arquivo': resultado['arquivo'],
                            'nome': info.get('nome', 'N/A'),
                            'matricula': info.get('matricula', 'N/A'),
                            'cargo': info.get('cargo', 'N/A'),
                            'regime': resultado['regime'],
                            'vencimentos': info.get('vencimentos_total', 0),
                            'descontos': info.get('descontos_total', 0),
                            'liquido': info.get('liquido', 0),
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
                        'cargo': info.get('cargo', 'N/A'),
                        'regime': resultado['regime'],
                        'vencimentos': info.get('vencimentos_total', 0),
                        'descontos': info.get('descontos_total', 0),
                        'liquido': info.get('liquido', 0),
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
                    st.metric("Matrícula", info.get('matricula', 'N/A'))
                
                with col2:
                    st.metric("Cargo", info.get('cargo', 'N/A'))
                    st.metric("Regime", resultado['regime'])
                
                with col3:
                    st.metric("Vencimentos", f"R$ {info.get('vencimentos_total', 0):,.2f}")
                    st.metric("Líquido", f"R$ {info.get('liquido', 0):,.2f}")
                
                st.markdown("---")
                
                # Nossos Contratos (nova seção)
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
                        total_nossos = len(df[df['tipo_oportunidade'] == 'NOSSO CONTRATO'])
                        st.metric("🏆 Nossos Contratos", total_nossos, 
                                help="Clientes que já possuem contrato conosco")
                    
                    with col2:
                        total_oportunidades = len(df[df['tipo_oportunidade'] == 'CONHECIDA'])
                        st.metric("✅ Oportunidades", total_oportunidades, 
                                help="Total de oportunidades confirmadas")
                    
                    with col3:
                        total_estudar = len(df[df['tipo_oportunidade'] == 'PARA ESTUDAR'])
                        st.metric("⚠️ Para Estudar", total_estudar,
                                help="Cartões fora da lista conhecida")
                    
                    with col4:
                        total_sem = len(df[df['tipo_oportunidade'] == 'NENHUMA'])
                        st.metric("ℹ️ Sem Oportunidade", total_sem,
                                help="Servidores sem oportunidades")
                    
                    with col5:
                        total_servidores = df['nome'].nunique()
                        st.metric("👥 Servidores", total_servidores,
                                help="Total de servidores únicos")
                    
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
                    
                    # Lista de Nossos Clientes
                    st.markdown("---")
                    st.subheader("🏆 Nossos Clientes Identificados")
                    nossos_clientes_df = df[df['tipo_oportunidade'] == 'NOSSO CONTRATO']
                    
                    if not nossos_clientes_df.empty:
                        # Agrupa por cliente
                        clientes_agrupados = nossos_clientes_df.groupby(['nome', 'matricula']).agg({
                            'descricao': lambda x: '<br>'.join(x),
                            'liquido': 'first',
                            'regime': 'first'
                        }).reset_index()
                        
                        st.dataframe(
                            clientes_agrupados,
                            column_config={
                                "nome": "Nome",
                                "matricula": "Matrícula",
                                "descricao": st.column_config.TextColumn(
                                    "Contratos",
                                    width="large"
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
                        
                        st.success(f"✨ Total de {len(clientes_agrupados)} cliente(s) nosso(s) identificado(s)!")
                    else:
                        st.info("Nenhum cliente nosso identificado neste lote.")
                    
                    # Top 10 Servidores
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
                            "cargo": "Cargo",
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
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        # Excel - Todos os dados
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
                        # Excel - Apenas nossos clientes
                        nossos_df = df[df['tipo_oportunidade'] == 'NOSSO CONTRATO']
                        if not nossos_df.empty:
                            buffer_nossos = io.BytesIO()
                            with pd.ExcelWriter(buffer_nossos, engine='openpyxl') as writer:
                                nossos_df.to_excel(writer, index=False, sheet_name='Nossos Clientes')
                            buffer_nossos.seek(0)
                            
                            st.download_button(
                                label="🏆 Download Nossos Clientes",
                                data=buffer_nossos,
                                file_name=f"nossos_clientes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                        else:
                            st.button("🏆 Sem Clientes Nossos", disabled=True, use_container_width=True)
                    
                    with col3:
                        # CSV
                        csv = df_filtrado.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="📥 Download CSV",
                            data=csv,
                            file_name=f"oportunidades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    
                    with col4:
                        # JSON
                        json_data = df_filtrado.to_json(orient='records', indent=2)
                        st.download_button(
                            label="📥 Download JSON",
                            data=json_data,
                            file_name=f"oportunidades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json",
                            use_container_width=True
                        )

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #666; padding: 2rem;">
            <p>💳 <strong>Analisador de Holerite</strong> v1.0</p>
            <p>Sistema de Identificação de Oportunidades de Compra de Dívida</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
