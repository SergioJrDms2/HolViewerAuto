"""
Página de Feedback - Analisador de Holerite
Envia sugestões e feedbacks diretamente para o Google Sheets.

Dependências extras necessárias:
    pip install gspread google-auth

Configuração do Streamlit Secrets (.streamlit/secrets.toml):

"""

import streamlit as st
import gspread
from google.oauth2 import service_account
from datetime import datetime
import re


# ============================================================================
# CONEXÃO COM GOOGLE SHEETS
# ============================================================================

def get_google_sheets_client():
    """Retorna um cliente autenticado do gspread via Service Account."""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes,
    )
    return gspread.authorize(credentials)


def salvar_feedback_no_sheets(dados: dict) -> bool:
    """
    Salva os dados do formulário no Google Sheets.
    Retorna True se bem-sucedido, False caso contrário.
    
    CORREÇÃO: Agora garante que SEMPRE adiciona uma nova linha ao final,
    sem nunca substituir feedbacks anteriores.
    """
    try:
        client = get_google_sheets_client()
        spreadsheet_id = st.secrets["sheets"]["spreadsheet_id"]
        worksheet_name = st.secrets["sheets"].get("worksheet_name", "Feedbacks")

        sheet = client.open_by_key(spreadsheet_id).worksheet(worksheet_name)

        # Define o cabeçalho esperado
        cabecalho = [
            "Data/Hora", "Nome", "Email", "Setor", "Tipo de Feedback",
            "Prioridade", "Mensagem", "Permite Contato", "Versão/Área do Sistema"
        ]
        
        # Verifica se o cabeçalho existe na linha 1
        primeira_linha = sheet.row_values(1)
        if not primeira_linha or primeira_linha == ['']:
            # Se não existe cabeçalho, adiciona na linha 1
            sheet.update('A1', [cabecalho])
        
        # CORREÇÃO PRINCIPAL: Encontra a próxima linha vazia de forma explícita
        # Pega todas as células da coluna A (Data/Hora)
        coluna_a = sheet.col_values(1)
        
        # A próxima linha vazia é o tamanho da lista + 1
        proxima_linha = len(coluna_a) + 1
        
        # Monta a linha de dados
        linha = [
            dados["data_hora"],
            dados["nome"],
            dados["email"],
            dados["setor"],
            dados["tipo_feedback"],
            dados["prioridade"],
            dados["mensagem"],
            "Sim" if dados["permite_contato"] else "Não",
            dados["area_sistema"],
        ]
        
        # MÉTODO 1: Atualiza diretamente na próxima linha disponível
        # Isso garante que NUNCA substitui uma linha existente
        range_name = f'A{proxima_linha}'
        sheet.update(range_name, [linha])
        
        return True

    except Exception as e:
        st.error(f"❌ Erro ao salvar no Google Sheets: {e}")
        return False


# ============================================================================
# VALIDAÇÕES
# ============================================================================

def validar_email(email: str) -> bool:
    padrao = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(padrao, email.strip()))


# ============================================================================
# PÁGINA DE FEEDBACK
# ============================================================================

def render_feedback_page():
    """Renderiza a página completa de envio de feedback."""

    # ---------- Banner de apresentação ----------
    st.markdown("""
        <div style="
            background: linear-gradient(135deg, #4C1D95 0%, #7C3AED 60%, #8B5CF6 100%);
            border-radius: 1.25rem;
            padding: 2.5rem 2rem 2rem 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 8px 30px rgba(124, 58, 237, 0.25);
        ">
            <h1 style="color: white; font-size: 2rem; font-weight: 800; margin: 0 0 0.5rem 0; letter-spacing: -0.5px;">
                💬 Central de Feedback
            </h1>
            <p style="color: #DDD6FE; font-size: 1.05rem; margin: 0; line-height: 1.6;">
                Sua opinião é o que nos move. Use este espaço para nos ajudar a evoluir.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # ---------- Aviso de seriedade ----------
    st.markdown("""
        <div style="
            background-color: #FFF7ED;
            border-left: 5px solid #F97316;
            border-radius: 0.75rem;
            padding: 1.25rem 1.5rem;
            margin-bottom: 2rem;
        ">
            <p style="font-size: 1rem; font-weight: 700; color: #9A3412; margin: 0 0 0.4rem 0;">
                ⚠️ Atenção: Este canal é exclusivo para feedback construtivo
            </p>
            <p style="font-size: 0.9rem; color: #7C2D12; margin: 0; line-height: 1.6;">
                Este formulário tem como objetivo a <strong>melhoria contínua</strong> da plataforma. 
                Por favor, descreva com clareza e objetividade o que você identificou — seja um problema, 
                uma sugestão ou uma melhoria. Feedbacks vagos ou sem informações suficientes não poderão 
                ser priorizados pela nossa equipe de Customer Experience. <strong>Cada envio é registrado e analisado.</strong>
            </p>
        </div>
    """, unsafe_allow_html=True)

    # ---------- Indicadores de impacto ----------
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
            <div style="background:#F5F3FF; border-radius:1rem; padding:1.25rem; text-align:center; border:1px solid #DDD6FE;">
                <div style="font-size:1.8rem;">📋</div>
                <div style="font-weight:700; color:#4C1D95; font-size:0.95rem; margin-top:0.4rem;">Registrado</div>
                <div style="color:#7C3AED; font-size:0.7rem;">Todo feedback é direcionado para nossa equipe de Customer Experience</div>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
            <div style="background:#F0FDF4; border-radius:1rem; padding:1.25rem; text-align:center; border:1px solid #BBF7D0;">
                <div style="font-size:1.8rem;">🔍</div>
                <div style="font-weight:700; color:#14532D; font-size:0.95rem; margin-top:0.4rem;">Analisado</div>
                <div style="color:#16A34A; font-size:0.7rem;;">Nossa equipe revisa todos os envios</div>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
            <div style="background:#EFF6FF; border-radius:1rem; padding:1.25rem; text-align:center; border:1px solid #BFDBFE;">
                <div style="font-size:1.8rem;">🚀</div>
                <div style="font-weight:700; color:#1E3A5F; font-size:0.95rem; margin-top:0.4rem;">Implementado</div>
                <div style="color:#2563EB; font-size:0.7rem;;">Boas ideias viram features reais</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)

    # ---------- Formulário ----------
    st.markdown("""
        <h3 style="color: #334155; font-weight: 700; margin-bottom: 1.5rem; font-size: 1.3rem;">
            📝 Preencha o formulário abaixo
        </h3>
    """, unsafe_allow_html=True)

    with st.form("formulario_feedback", clear_on_submit=True):

        col_a, col_b = st.columns(2, gap="medium")

        with col_a:
            nome = st.text_input(
                "👤 Nome completo *",
                placeholder="Ex: João da Silva",
                help="Seu nome completo para identificação"
            )

        with col_b:
            email = st.text_input(
                "📧 E-mail *",
                placeholder="Ex: joao.silva@empresa.com.br",
                help="Usaremos apenas para retornar dúvidas, se necessário"
            )

        col_c, col_d = st.columns(2, gap="medium")

        with col_c:
            setor = st.text_input(
                "🏢 Setor / Departamento *",
                placeholder="Ex: Crédito, Comercial, TI...",
                help="Setor onde você trabalha"
            )

        with col_d:
            tipo_feedback = st.selectbox(
                "📌 Tipo de Feedback *",
                options=[
                    "Selecione...",
                    "🐛 Bug / Problema",
                    "💡 Sugestão de Melhoria",
                    "✨ Nova Funcionalidade",
                    "📊 Problema com Dados / Cálculo",
                    "⚡ Lentidão / Performance",
                    "🎨 Usabilidade / Interface",
                    "👍 Elogio",
                    "🔧 Outro",
                ],
                help="Classifique seu feedback para facilitar o triaging"
            )

        col_e, col_f = st.columns(2, gap="medium")

        with col_e:
            area_sistema = st.selectbox(
                "🖥️ Área do Sistema Afetada",
                options=[
                    "Não se aplica / Geral",
                    "Análise Individual de Holerite",
                    "Análise em Lote",
                    "Cálculo de Margem",
                    "Exportação (Excel / CSV)",
                    "Identificação de Prefeitura",
                    "Interface / Visual",
                    "Outra",
                ],
                help="Qual parte da plataforma você está referenciando?"
            )

        with col_f:
            prioridade = st.select_slider(
                "🎯 Prioridade percebida",
                options=["Baixa", "Média", "Alta", "Crítica"],
                value="Média",
                help="Qual a urgência desse problema/sugestão para o seu trabalho?"
            )

        mensagem = st.text_area(
            "💬 Descrição detalhada *",
            placeholder=(
                "Descreva com o máximo de detalhes possível:\n"
                "• O que aconteceu (ou o que falta)?\n"
                "• Qual prefeitura / arquivo estava sendo usado?\n"
                "• Qual era o resultado esperado vs. o que aconteceu?\n"
                "• Passos para reproduzir o problema (se for um bug)"
            ),
            height=180,
            help="Quanto mais detalhes, mais rápido conseguimos resolver!"
        )

        permite_contato = st.checkbox(
            "✅ Autorizo a equipe a entrar em contato comigo para esclarecer detalhes sobre este feedback",
            value=True
        )

        st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)

        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            enviado = st.form_submit_button(
                "🚀 Enviar Feedback",
                use_container_width=True,
                type="primary"
            )

    # ---------- Processamento do envio ----------
    if enviado:
        erros = []

        if not nome.strip():
            erros.append("Nome é obrigatório.")
        if not email.strip():
            erros.append("E-mail é obrigatório.")
        elif not validar_email(email):
            erros.append("E-mail inválido. Verifique o formato.")
        if not setor.strip():
            erros.append("Setor é obrigatório.")
        if tipo_feedback == "Selecione...":
            erros.append("Selecione o tipo de feedback.")
        if not mensagem.strip() or len(mensagem.strip()) < 20:
            erros.append("A descrição deve ter pelo menos 20 caracteres.")

        if erros:
            for erro in erros:
                st.error(f"⚠️ {erro}")
        else:
            dados = {
                "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "nome": nome.strip(),
                "email": email.strip().lower(),
                "setor": setor.strip(),
                "tipo_feedback": tipo_feedback,
                "prioridade": prioridade,
                "mensagem": mensagem.strip(),
                "permite_contato": permite_contato,
                "area_sistema": area_sistema,
            }

            with st.spinner("Enviando seu feedback..."):
                sucesso = salvar_feedback_no_sheets(dados)

            if sucesso:
                st.balloons()
                st.markdown("""
                    <div style="
                        background: linear-gradient(135deg, #ECFDF5, #F0FDF4);
                        border: 2px solid #10B981;
                        border-radius: 1rem;
                        padding: 1.5rem 2rem;
                        margin-top: 1rem;
                        text-align: center;
                    ">
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">🎉</div>
                        <h3 style="color: #065F46; margin: 0 0 0.5rem 0;">Feedback enviado com sucesso!</h3>
                        <p style="color: #047857; margin: 0; font-size: 0.95rem;">
                            Obrigado pela sua contribuição! Nosso time irá analisar e considerar sua sugestão 
                            no próximo ciclo de melhorias da plataforma.
                        </p>
                    </div>
                """, unsafe_allow_html=True)

    # ---------- Rodapé da página ----------
    st.markdown("""
        <div style="
            margin-top: 3rem;
            padding-top: 1.5rem;
            text-align: center;
            color: #94A3B8;
            font-size: 0.85rem;
        ">
            <p>Todos os feedbacks são armazenados com segurança e revisados periodicamente.</p>
            <p style="margin: 0;">Dúvidas urgentes? Entre em contato diretamente com o time de Customer Experience.</p>
        </div>
    """, unsafe_allow_html=True)
