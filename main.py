"""
StarCheck — Analisador de Holerite com IA
Motor: Groq (Llama 4 Scout) | Assistente: Stella ✨
Cálculo de Margem Consignável integrado via IA
"""

from __future__ import annotations

import io as _io
from collections import Counter, defaultdict
from datetime import datetime

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, HRFlowable, Image as RLImage,
    KeepTogether, PageBreak, PageTemplate, Paragraph,
    Spacer, Table, TableStyle,
)

import io as _io
from collections import Counter, defaultdict
from datetime import datetime
from typing import List

import plotly.graph_objects as go
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    Image as RLImage,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

import streamlit as st
import re, io, json, os, base64
import pandas as pd
from datetime import datetime
from typing import Dict, List
import PyPDF2, pdfplumber
import plotly.express as px
from PIL import Image
from groq import Groq 
import re as _re
import streamlit.components.v1 as components
from crm_page import render_crm_page

from feedback_page import render_feedback_page
from ui_pages import render_individual_header, render_lote_header
from sidebar import render_sidebar
from auth import render_auth_page, render_user_info_sidebar
from profile_settings import render_profile_settings
from admin import render_admin_page, init_db, load_cartoes

# ============================================================================
# PORTFÓLIO — base de conhecimento da Stella
# ============================================================================
PORTFOLIO = """
PORTFÓLIO DE PRODUTOS — STARBANK GRUPO

1. EMPRÉSTIMO CONSIGNADO
   Crédito com parcelas descontadas direto em folha. Prazo: 12–120 meses. Taxas menores.
   Diferenciais: parcelas fixas, refinanciamento possível, liberação rápida.

2. CARTÃO CONSIGNADO
   Cartão de crédito vinculado à margem consignável. Desconto mínimo em folha. Saque disponível.
   Prazo: 12–120 meses renovável.

3. CARTÃO BENEFÍCIO
   Como o Cartão Consignado + benefícios extras: telemedicina, auxílio funeral, odontologia.
   Crédito + proteção em um único produto.

4. AUXÍLIO SERVIDOR
   Crédito de curto prazo. Prazo: 2 meses (renovação mensal possível).
   Ideal para emergências pontuais sem comprometer margem por longo prazo.

5. COMPRA DE DÍVIDA
   Assumimos dívida existente de cartão concorrente, reorganizamos com condições melhores.
   Pode liberar "troco". USE QUANDO: cliente tem cartão concorrente → tentar compra primeiro.

6. VALE CONSIGNADO
   Crédito de 1 parcela. Descontado no mês seguinte. Emergências rápidas.

7. AFILIADOS STAR / INDIQUE & GANHE
   Programas de indicação com bonificação. Para qualquer pessoa.

8. CREDIÁRIO STAR
   Compras em estabelecimentos parceiros. Público principal: lojistas.

FLUXO DE DECISÃO:
→ Tem cartão concorrente? → COMPRA DE DÍVIDA
→ Compra inviável? → EMPRÉSTIMO CONSIGNADO
→ Sem margem longa? → AUXÍLIO SERVIDOR ou VALE CONSIGNADO
→ Já é nosso cliente? → Verificar REFINANCIAMENTO
→ Sempre: oferecer CARTÃO CONSIGNADO ou CARTÃO BENEFÍCIO como produto adicional
"""

# ============================================================================
# CONFIGURAÇÃO DE MARGEM POR PREFEITURA
# ============================================================================

# Nome do provento no holerite é fixo e único?
#     → usa proventos_kw, deixa proventos_campos vazio

# Nome é ambíguo ou muito variável?
#     → usa proventos_campos, não coloca keyword correspondente


# Ao longo dessa revisão, chegamos a um padrão onde:

# proventos_kw virou a camada principal e mais confiável

# proventos_campos só sobrevive quando há um provento com nome muito ambíguo no holerite, onde o campo estruturado é mais seguro que uma keyword

# Na prática, nas prefeituras que revisamos, sempre optamos pela Opção A (só keywords) justamente porque os nomes dos proventos nos holerites são fixos e únicos o suficiente.

# O que faz sentido daqui pra frente
# Usar só proventos_kw como regra geral, e proventos_campos apenas como exceção explícita — como no caso de Bauru com vantagens_pessoais, onde o campo estruturado é mais confiável que tentar fazer keyword para "VANT PESS VL".

# O que não faz sentido é manter os dois preenchidos para o mesmo provento "para ter mais segurança" — porque na realidade isso não dá mais segurança, só duplica o valor.

PREFEITURAS_CONFIG = {

   "POA": {
       "emp": 0.35, "cc": 0.15, "cb": 0.15,
       "proventos_campos": [
           "adicional_tempo_servico",  # → lê vencimentos_fixos.adicional_tempo_servico
           "gratificacao",             # → lê vencimentos_fixos.gratificacao
       ],
       "proventos_kw": [
           # Apenas proventos SEM campo estruturado próprio
           "adicional por risco de vida", "adicional por riso de vida",
           "adicional local de exercicio"
           "bienio", "biênio", "vant pess", "vant pe",
       ],
       "descontos_campos": [
           "irrf",        # → lê descontos_obrigatorios.irrf
           "previdencia", # → lê descontos_obrigatorios.previdencia
       ],
       "descontos_kw": [
           # Apenas descontos SEM campo estruturado próprio
           "pensao aliment", "pensão aliment",
           "plano de saude", "plano saude",
       ],
   },

   "BAURU": {
       "emp": 0.35, "cc": 0.10, "cb": 0.00,
       "proventos_campos": [
           "sexta_parte",        # → lê vencimentos_fixos.sexta_parte
           "ativ_trab_pedag",    # → lê vencimentos_fixos.ativ_trab_pedag
           "vantagens_pessoais", # → lê vencimentos_fixos.vantagens_pessoais (VANT PESS VL)
       ],
       "proventos_kw": [
           # Apenas proventos SEM campo estruturado próprio
           "bienio", "biênio",   # → BIENIO
           "vant pe l",          # → VANT PE L25/17 (específico o suficiente para não bater em "vant pess")
       ],
       "descontos_campos": [
           "irrf",        # → lê descontos_obrigatorios.irrf
           "previdencia", # → lê descontos_obrigatorios.previdencia
       ],
       "descontos_kw": [
           # Apenas descontos SEM campo estruturado próprio
           "plano de saude", "plano saude",
           "pensao aliment", "pensão aliment",
       ],
   },

   "ARACATUBA": {
       "emp": 0.40, "cc": 0.10, "cb": 0.00,
       "proventos_campos": [],
       "proventos_kw": [
           # Descrições exatas do holerite
           "adicional por tempo de servico", "adicional por tempo",
           "insalubridade",
           "sexta parte",
       ],
       "descontos_campos": [
           "irrf",        # → lê descontos_obrigatorios.irrf
           "previdencia", # → lê descontos_obrigatorios.previdencia
       ],
       "descontos_kw": [
           "pensao aliment", "pensão aliment",
           "fundo de custeio", "fdo custeio", "f. custeio",
           "abatimento de teto", "abat. teto", "abat teto",
       ],
   },

   "CAMPOS_JORDAO": {
       "emp": 0.30, "cc": 0.10, "cb": 0.00,
       "proventos_campos": [],
       "proventos_kw": [
           # Descrições exatas do holerite (salário base é automático)
           "adicional por tempo",
           "sexta parte",
       ],
       "descontos_campos": [
           "irrf",        # → lê descontos_obrigatorios.irrf
           "previdencia", # → lê descontos_obrigatorios.previdencia
       ],
       "descontos_kw": [
           "assistencia medica", "plano de saude",
           "pensao aliment", "pensão aliment",
           "custeio de beneficio",
       ],
   },

   "HORTOLANDIA": {
       "emp": 0.30, "cc": 0.10, "cb": 0.30,
       "proventos_campos": [],
       "proventos_kw": [
           # Descrições exatas do holerite (salário base é automático)
           "adicional por tempo",
           "sexta parte",
           "grat. fixa", "gratificacao fixa", "gratificação fixa",
           "insalubridade",
       ],
       "descontos_campos": [
           "irrf",        # → lê descontos_obrigatorios.irrf
           "previdencia", # → lê descontos_obrigatorios.previdencia
       ],
       "descontos_kw": [
           "pensao aliment", "pensão aliment",
       ],
   },

   "PIRACICABA": {
       "emp": 0.00, "cc": 0.10, "cb": 0.00,
       "proventos_campos": [],
       "proventos_kw": [
           # Descrições exatas do holerite (salário é automático)
           "corporacao fg", "corporação fg",
           "sexta parte",
       ],
       "descontos_campos": [
           "irrf",  # → lê descontos_obrigatorios.irrf
       ],
       "descontos_kw": [
           # Nome exato do holerite — evita pegar qualquer "previdencia" genérica
           "previdencia proporcial",
           "pensao aliment", "pensão aliment",
       ],
   },

   "SALTO": {
       "emp": 0.35, "cc": 0.05, "cb": 0.00,
       "proventos_campos": [],
       "proventos_kw": [
           # Proventos permanentes/fixos (salário base é automático)
           "adicional por tempo", "adicional tempo",
           "sexta parte",
           "insalubridade",
           "quinquenio", "quinquênio",
           "trienio", "triênio",
           "bienio", "biênio",
           "representacao", "representação",
           "abono",
           "vantagem pessoal",
           "gratificacao", "gratificação",  # genérico — ver nota abaixo
       ],
       "descontos_campos": [
           "irrf",        # → lê descontos_obrigatorios.irrf
           "previdencia", # → lê descontos_obrigatorios.previdencia
       ],
       "descontos_kw": [
           "pensao aliment", "pensão aliment",
           "vale transporte",
           "imposto sindical",
           "contribuicao sindical", "contribuição sindical",
           "reposicao", "reposição",
           "indenizacao", "indenização",
       ],
   },

   "TUPA": {
       "emp": 0.30, "cc": 0.10, "cb": 0.00,
       "proventos_campos": [],
       "proventos_kw": [
           # Descrições exatas do holerite (salário base é automático)
           "adic. tempo de servico", "adicional tempo de servico", "adicional por tempo",
           "bienio", "biênio",
           "sexta parte",
       ],
       "descontos_campos": [
           "irrf",        # → lê descontos_obrigatorios.irrf
           "previdencia", # → lê descontos_obrigatorios.previdencia
       ],
       "descontos_kw": [
           "plano de saude", "plano saude",
           "pensao aliment", "pensão aliment",
       ],
   },

    "VINHEDO": {
        "emp": 0.30, "cc": 0.00, "cb": 0.00,
        "base_type": "bruto_sem_deducao",
        "proventos_campos": [],
        "proventos_kw": [],
        "descontos_campos": [],
        "descontos_kw": [],
    },

    "TABOAO_SERRA": {
        "emp": 0.35, "cc": 0.05, "cb": 0.00,
        "proventos_campos": [],
        "proventos_kw": [],
        "descontos_campos": ["irrf"],
        "descontos_kw": [],
    },

   "BARUERI": {
       "emp": 0.35, "cc": 0.00, "cb": 0.00,
       "proventos_campos": [],
       "proventos_kw": [
           # Vencimento Básico é automático como salariobase — NÃO entra aqui
           "trienio", "triênio",  # TRIÊNIO (adicional por tempo serviço)
       ],
       "descontos_campos": [
           "inss",   # → I.H.S.S.
           "irrf",   # → I.R.R.F.
       ],
       "descontos_kw": [
           # Descontos SEM campo estruturado próprio
           "ipresb",                            # IPRESB (previdência municipal)
           "vale transporte",                   # DESC. VALE TRANSPORTE
           "faltas",                            # FALTAS
           "licenca medica", "licença medica",  # LICENCA MEDICA
           "p.just", "p. just",                 # P. JUST. SAL. MIN. + SAL. FAM.
           "pensao just", "pensão just",        # PENSAO JUSTIÇA
           "pensao liq", "pensão liq",          # PENSAO LIQ. + S.F.
       ],
   },

   "EMBU": {
       "emp": 0.35, "cc": 0.05, "cb": 0.10,
       "proventos_campos": [],
       "proventos_kw": [
           # Vencimento Base é automático como salariobase — NÃO entra aqui
           "adicional tempo servico", "adicional tempo serviço",
           "horas estudo e pesquisa", "horas estudo", "hora estudo",
       ],
       "descontos_campos": [
           "irrf",  # → lê descontos_obrigatorios.irrf
       ],
       "descontos_kw": [
           # Previdência via keywords específicos do RPPS de Embu (sem campo genérico)
           "contrib previdenciaria", "contribuicao previdenciaria",
           "rpps", "ipsm", "funprev", "ipresb",
           # Outros descontos compulsórios
           "contribuicao sindical", "contribuição sindical",
           "pensao aliment", "pensão aliment",
       ],
   },

   "RIBEIRAO_PRETO": {
       "emp": 0.40, "cc": 0.10, "cb": 0.00,
       "proventos_campos": [],
       "proventos_kw": [
           # Salário é automático — NÃO entra aqui
           "adicional",       # ADICIONAL (captura todos os adicionais — intencional per roteiro)
           "acresc",          # ACRESC (acréscimos)
           "insalubridade",   # INSALUBRIDADE
           "grat.",           # GRATIFICAÇÕES FIXAS via abreviação (ex: GRAT. MAGISTÉRIO)
           "gratificac",      # GRATIFICAÇÕES por extenso (GRATIFICACAO, GRATIFICAÇÃO)
           "quinquenio", "quinquênio",
           "trienio", "triênio",
           "sexta parte",
       ],
       "descontos_campos": [
           "irrf",       # → lê descontos_obrigatorios.irrf
           "previdencia", # → lê descontos_obrigatorios.previdencia
       ],
       "descontos_kw": [
           "pensao aliment", "pensão aliment",  # específico para pensão alimentícia
           "indenizacao", "indenização",
           "restituicao", "restituição",
       ],
   },

   "SOROCABA": {
       "emp": 0.30, "cc": 0.00, "cb": 0.20,
       "proventos_campos": [],
       "proventos_kw": [
           # Descrições exatas do holerite (vencimento é automático)
           "adic. tempo servico", "adic. tempo serviço",
           "adicional tempo servico", "adicional por tempo",
           "insalubridade",
       ],
       "descontos_campos": [
           "irrf",        # → lê descontos_obrigatorios.irrf
           "previdencia", # → lê descontos_obrigatorios.previdencia
       ],
       "descontos_kw": [
           "pensao aliment", "pensão aliment",
           "plano de saude", "plano saude",
       ],
   },

   "SAO_JOSE_RIO_PRETO": {
       "emp": 0.35, "cc": 0.05, "cb": 0.00,
       "proventos_campos": [],
       "proventos_kw": [
           # Vencimento é automático — NÃO entra aqui
           "adic. fixo", "adicional fixo",         # ADIC. FIXO
           "grat. fixa", "gratificacao fixa",       # GRAT. FIXA
           "gratificação fixa",                     # variação com acento
       ],
       "descontos_campos": [
           "irrf",        # → lê descontos_obrigatorios.irrf
           "previdencia", # → lê descontos_obrigatorios.previdencia
       ],
       "descontos_kw": [
           "reposicao", "reposição",
           "indenizacao", "indenização",
           "contribuicao sindical", "contribuição sindical",
       ],
   },

   "VALINHOS": {
       "emp": 0.30, "cc": 0.00, "cb": 0.00,
       "proventos_campos": [],
       "proventos_kw": [
           # Descrições exatas do holerite (salário base é automático)
           "adic. t. servico", "adic. t. serviço",   # ADIC. T. SERVIÇO
           "adicional tempo", "adicional t. serv",    # variações possíveis
           "sexta parte",                             # SEXTA PARTE
           "lei 5801",                                # LEI 5801
           "adic. funcao", "adic funcao",             # ADIC. FUNÇÃO
           "adicional funcao", "adicional função",    # variações
           "funcao encorporada", "função encorporada",# FUNÇÃO ENCORPORADA
       ],
       "descontos_campos": [
           "irrf",        # → lê descontos_obrigatorios.irrf
           "previdencia", # → lê descontos_obrigatorios.previdencia
       ],
       "descontos_kw": [
           "pensao aliment", "pensão aliment",  # PENSÃO ALIMT.
       ],
   },

   "COTIA": {
       "emp": 0.35, "cc": 0.05, "cb": 0.00,
       "proventos_campos": [],
       "proventos_kw": [
           # Descrições exatas do holerite (salário base é automático)
           "gratificacao", "gratificação",                          # GRATIFICAÇÃO
           "adicional por riso de vida", "adicional por risco de vida", # ADICIONAL POR RISO DE VIDA
           "adicional por tempo de servico", "adicional por tempo", # ADICIONAL POR TEMPO DE SERVIÇO
           "adicional local de exercicio",                          # ADICIONAL LOCAL DE EXERCICIO
           "local de exercicio",                                    # variação abreviada
       ],
       "descontos_campos": [
           "irrf",        # → lê descontos_obrigatorios.irrf
           "previdencia", # → lê descontos_obrigatorios.previdencia
       ],
       "descontos_kw": [
           "pensao aliment", "pensão aliment",  # PENSÃO ALIMENTÍCIA
       ],
   },

    "MARINGA": {
        "emp": 0.35, "cc": 0.10, "cb": 0.00,
        "base_type": "apenas_base",
        "proventos_campos": [], "proventos_kw": [],
        "descontos_campos": ["inss","irrf","previdencia"], "descontos_kw": [],
    },
    "LAGO_VERDE": {
        "emp": 0.35, "cc": 0.15, "cb": 0.15,
        "proventos_campos": ["adicional_tempo_servico","gratificacao","sexta_parte","insalubridade"],
        "proventos_kw": [],
        "descontos_campos": ["inss","irrf","previdencia"], "descontos_kw": [],
    },
    "PONTA_GROSSA": {
        "emp": 0.35, "cc": 0.15, "cb": 0.15,
        "base_type": "apenas_base",
        "proventos_campos": [], "proventos_kw": [],
        "descontos_campos": ["inss","irrf","previdencia"], "descontos_kw": [],
    },
    "CAMARA_DEPUTADOS": {
        "emp": 0.35, "cc": 0.15, "cb": 0.15,
        "base_type": "apenas_base",
        "proventos_campos": [], "proventos_kw": [],
        "descontos_campos": ["inss","irrf","previdencia"], "descontos_kw": [],
    },
    "BELTERRA":       {"emp":0.35,"cc":0.15,"cb":0.15,"proventos_campos":["adicional_tempo_servico","gratificacao"],"proventos_kw":[],"descontos_campos":["inss","irrf","previdencia"],"descontos_kw":[]},
    "MONTE_ALEGRE_SE":{"emp":0.35,"cc":0.15,"cb":0.15,"proventos_campos":["adicional_tempo_servico","gratificacao"],"proventos_kw":[],"descontos_campos":["inss","irrf","previdencia"],"descontos_kw":[]},
    "REDENCAO":       {"emp":0.30,"cc":0.05,"cb":0.05,"proventos_campos":["adicional_tempo_servico","gratificacao"],"proventos_kw":[],"descontos_campos":["inss","irrf","previdencia"],"descontos_kw":[]},
    "CUIABA":         {"emp":0.30,"cc":0.05,"cb":0.05,"proventos_campos":["adicional_tempo_servico","gratificacao"],"proventos_kw":[],"descontos_campos":["inss","irrf","previdencia"],"descontos_kw":[]},
    "ALEGO":          {"emp":0.30,"cc":0.05,"cb":0.05,"proventos_campos":["adicional_tempo_servico","gratificacao"],"proventos_kw":[],"descontos_campos":["inss","irrf","previdencia"],"descontos_kw":[]},
    "GOVERNO_GOIAS":  {"emp":0.30,"cc":0.05,"cb":0.05,"base_type":"bruto_sem_deducao","proventos_campos":["adicional_tempo_servico","gratificacao"],"proventos_kw":[],"descontos_campos":[],"descontos_kw":[]},
    "IMPERATRIZ":     {"emp":0.35,"cc":0.05,"cb":0.05,"proventos_campos":["adicional_tempo_servico","gratificacao"],"proventos_kw":[],"descontos_campos":["inss","irrf","previdencia"],"descontos_kw":[]},
    "UBERABA":        {"emp":0.35,"cc":0.15,"cb":0.15,"proventos_campos":["adicional_tempo_servico","gratificacao"],"proventos_kw":[],"descontos_campos":["inss","irrf","previdencia"],"descontos_kw":[]},
    "ITAITUBA":       {"emp":0.35,"cc":0.15,"cb":0.15,"proventos_campos":["adicional_tempo_servico","gratificacao"],"proventos_kw":[],"descontos_campos":["inss","irrf","previdencia"],"descontos_kw":[]},
    "BARCARENA":      {"emp":0.35,"cc":0.15,"cb":0.15,"proventos_campos":["adicional_tempo_servico","gratificacao"],"proventos_kw":[],"descontos_campos":["inss","irrf","previdencia"],"descontos_kw":[]},
}

PREFEITURAS_KEYWORDS = {
    "POA":               ["poá","poa","prefeitura de poá","prefeitura poa"],
    "BAURU":             ["bauru","pref munic de bauru","prefeitura de bauru"],
    "ARACATUBA":         ["araçatuba","aracatuba","prefeitura de araçatuba"],
    "CAMPOS_JORDAO":     ["campos do jordão","campos do jordao","campos jordao"],
    "HORTOLANDIA":       ["hortolândia","hortolandia"],
    "PIRACICABA":        ["piracicaba","prefeitura de piracicaba"],
    "SALTO":             ["salto","municipio de salto","prefeitura de salto"],
    "TUPA":              ["tupã","tupa","prefeitura de tupã"],
    "VINHEDO":           ["vinhedo","prefeitura de vinhedo"],
    "TABOAO_SERRA":      ["taboão da serra","taboao da serra","taboão"],
    "BARUERI":           ["barueri","prefeitura de barueri"],
    "EMBU":              ["embu","embu das artes","prefeitura de embu"],
    "RIBEIRAO_PRETO":    ["ribeirão preto","ribeirao preto","pref ribeirao"],
    "SOROCABA":          ["sorocaba","prefeitura de sorocaba"],
    "SAO_JOSE_RIO_PRETO":["são josé do rio preto","sao jose do rio preto","rio preto","sjrp"],
    "VALINHOS":          ["valinhos","prefeitura de valinhos"],
    "COTIA":             ["cotia","prefeitura de cotia"],
    "MARINGA":           ["maringá","maringa","prefeitura de maringá"],
    "LAGO_VERDE":        ["lago verde"],
    "PONTA_GROSSA":      ["ponta grossa"],
    "CAMARA_DEPUTADOS":  ["câmara dos deputados","camara dos deputados"],
    "BELTERRA":          ["belterra"],
    "MONTE_ALEGRE_SE":   ["monte alegre de sergipe","monte alegre"],
    "REDENCAO":          ["redenção","redencao"],
    "CUIABA":            ["cuiabá","cuiaba"],
    "ALEGO":             ["alego","assembleia legislativa","assembleia de goiás"],
    "GOVERNO_GOIAS":     ["governo do estado de goiás","governo de goiás","governo goias"],
    "IMPERATRIZ":        ["imperatriz"],
    "UBERABA":           ["uberaba"],
    "ITAITUBA":          ["itaituba"],
    "BARCARENA":         ["barcarena"],
}

def detectar_prefeitura_key(prefeitura_str: str) -> str:
    if not prefeitura_str:
        return ""
    texto = prefeitura_str.lower()
    for key, keywords in PREFEITURAS_KEYWORDS.items():
        for kw in keywords:
            if kw in texto:
                return key
    return ""

# ============================================================================
# CÁLCULO DE MARGEM
# ============================================================================
def _abs_val(v) -> float:
    try: return abs(float(v or 0))
    except: return 0.0

import unicodedata as _ud

def _norm(s: str) -> str:
    return _ud.normalize("NFD", s.lower()).encode("ascii","ignore").decode()

def _kw_match(desc: str, keywords: list) -> bool:
    d = _norm(str(desc))
    return any(_norm(kw) in d for kw in keywords)

def _soma_raw_kw(raw_list: list, keywords: list) -> float:
    if not keywords: return 0.0
    return sum(_abs_val(i.get("valor",0)) for i in (raw_list or [])
               if _kw_match(i.get("descricao",""), keywords))

_CAMPOS_VF = {
    "adicional_tempo_servico", "gratificacao", "hora_ativ_extra_classe",
    "sexta_parte","insalubridade","grat_desempenho","adicional_noturno",
    "tdc_permanente","tdi_permanente","vantagens_pessoais","ativ_trab_pedag",
    "progressao_salarial","trienio","titulacao","subsidios","quinquenio",
    "representacao","abono","adicional_insalubridade","grat_graduacao",
    "assistencia_financeira","adicional_fixo","gratificacao_fixa",
}
_CAMPOS_DO = {"inss","irrf","previdencia"}


def calcular_margem_ia(dados: Dict) -> Dict:
    prefeitura_key = detectar_prefeitura_key(dados.get("prefeitura", ""))
    cfg = PREFEITURAS_CONFIG.get(prefeitura_key)
    if not cfg:
        return {
            "disponivel": False,
            "motivo": f"Prefeitura '{dados.get('prefeitura','')}' não mapeada — cálculo indisponível."
        }

    perc_emp  = cfg.get("emp", 0.0)
    perc_cc   = cfg.get("cc",  0.0)
    perc_cb   = cfg.get("cb",  0.0)
    base_type = cfg.get("base_type", "bruto_menos_descontos")

    sal_base      = _abs_val(dados.get("salario_base", 0.0))
    vf            = dados.get("vencimentos_fixos") or {}
    do            = dados.get("descontos_obrigatorios") or {}
    proventos_raw = dados.get("proventos_raw", []) or []
    descontos_raw = dados.get("descontos_raw", []) or []

    prov_campos = cfg.get("proventos_campos", [])
    prov_kw     = cfg.get("proventos_kw", [])
    desc_campos = cfg.get("descontos_campos", [])
    desc_kw     = cfg.get("descontos_kw", [])

    if base_type == "bruto_sem_deducao":
        base_proventos = _abs_val(dados.get("vencimentos_total", 0)) or sal_base
    elif base_type == "apenas_base":
        base_proventos = sal_base
    else:
        base_proventos = sal_base
        for campo in prov_campos:
            if campo in _CAMPOS_VF:
                base_proventos += _abs_val(vf.get(campo, 0))
        if prov_kw and proventos_raw:
            _KW_BASE = ["salario","salário","vencimento","vencimentos","remuneracao","subsidio"]
            for item in proventos_raw:
                desc = item.get("descricao","")
                val  = _abs_val(item.get("valor",0))
                if val <= 0: continue
                if _kw_match(desc, _KW_BASE): continue
                if _kw_match(desc, prov_kw):
                    base_proventos += val

    salario_bruto = base_proventos

    if base_type == "bruto_sem_deducao":
        deducoes = 0.0
    else:
        deducoes = 0.0
        for campo in desc_campos:
            if campo in _CAMPOS_DO:
                deducoes += _abs_val(do.get(campo, 0))
        if desc_kw and descontos_raw:
            deducoes += _soma_raw_kw(descontos_raw, desc_kw)

    base_calculo = base_proventos - deducoes
    if base_calculo <= 0:
        base_calculo = max(base_proventos, sal_base)

    cartoes     = dados.get("cartoes", []) or []
    emprestimos = dados.get("emprestimos", []) or []

    cartoes_nossos       = sum(_abs_val(c.get("valor",0)) for c in cartoes if c.get("tipo")=="nosso")
    cartoes_concorrentes = sum(_abs_val(c.get("valor",0)) for c in cartoes if c.get("tipo")=="concorrente")
    cartoes_nao_comp     = sum(_abs_val(c.get("valor",0)) for c in cartoes if c.get("tipo")=="nao_comprado")
    cartoes_desconhec    = sum(_abs_val(c.get("valor",0)) for c in cartoes if c.get("tipo")=="desconhecido")
    total_cartoes        = cartoes_nossos + cartoes_concorrentes + cartoes_nao_comp + cartoes_desconhec
    total_emprestimos    = sum(_abs_val(e.get("valor",0)) for e in emprestimos)

    marg_emp_total = base_calculo * perc_emp
    marg_cc_total  = base_calculo * perc_cc
    marg_cb_total  = base_calculo * perc_cb

    marg_emp_disp = marg_emp_total - total_emprestimos
    marg_cc_disp  = marg_cc_total  - total_cartoes
    marg_cb_disp  = marg_cb_total  - total_cartoes

    liquido_calc = base_proventos - deducoes - total_emprestimos - total_cartoes
    perc_liq     = (liquido_calc / base_proventos * 100) if base_proventos > 0 else 0

    return {
        "disponivel":             True,
        "prefeitura_key":         prefeitura_key,
        "base_type":              base_type,
        "salario_bruto":          salario_bruto,
        "base_calculo":           base_calculo,
        "descontos_compulsorios": deducoes,
        "total_emprestimos":      total_emprestimos,
        "total_cartoes":          total_cartoes,
        "cartoes_nossos":         cartoes_nossos,
        "cartoes_concorrentes":   cartoes_concorrentes,
        "cartoes_nao_comp":       cartoes_nao_comp,
        "cartoes_desconhec":      cartoes_desconhec,
        "emprestimo": {
            "percentual":   perc_emp,
            "margem_total": marg_emp_total,
            "comprometido": total_emprestimos,
            "disponivel":   marg_emp_disp,
        },
        "cartao_consignado": {
            "percentual":   perc_cc,
            "margem_total": marg_cc_total,
            "comprometido": total_cartoes,
            "disponivel":   marg_cc_disp,
        },
        "cartao_beneficio": {
            "percentual":   perc_cb,
            "margem_total": marg_cb_total,
            "comprometido": total_cartoes,
            "disponivel":   marg_cb_disp,
        },
        "liquido_calculado":   liquido_calc,
        "percentual_liquidez": perc_liq,
        "aprovado_liquidez":   perc_liq >= 30.0,
    }


# ============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================================
st.set_page_config(
    page_title="StarCheck - Analisador de Holerite",
    page_icon="assets/favicon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

* { font-family: 'Inter', sans-serif; }

.stApp { background-color: #FFFFFF; }

[data-testid="stSidebar"] {
    background-color: #F8FAFC;
    border-right: 1px solid #E2E8F0;
    padding-top: 2rem;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #4C1D95; font-weight: 700; }
[data-testid="stSidebar"] .stSelectbox > div > div {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 0.5rem;
    color: #334155;
}

.main-header {
    font-size: 3rem; font-weight: 800;
    background: linear-gradient(135deg, #7C3AED 0%, #4C1D95 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    text-align: center; margin-bottom: 0.5rem;
    letter-spacing: -1px; padding-bottom: 10px;
}
.main-subtitle {
    text-align: center; font-size: 1.1rem; color: #64748B;
    margin-bottom: 3rem; font-weight: 400;
}

[data-testid="stFileUploader"] {
    padding: 2rem; border-radius: 1rem;
    background-color: #FFFFFF; border: 2px dashed #E2E8F0;
    transition: all 0.3s ease-in-out; cursor: pointer;
}
[data-testid="stFileUploader"]:hover {
    border-color: #8B5CF6; background-color: #F5F3FF;
}
[data-testid="stFileUploader"] section { background-color: transparent !important; }

.metric-card {
    background: #FFFFFF; padding: 1.5rem; border-radius: 1rem;
    border: 1px solid #F1F5F9; border-left: 5px solid #7C3AED;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    transition: transform 0.2s ease, box-shadow 0.2s ease; margin-bottom: 1rem;
}
.metric-card:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(124,58,237,0.1); }

.success-box { background-color:#ECFDF5; border-left:4px solid #10B981; color:#065F46; padding:1rem; border-radius:.75rem; margin:1rem 0; font-weight:500; }
.warning-box { background-color:#FFFBEB; border-left:4px solid #F59E0B; color:#92400E; padding:1rem; border-radius:.75rem; margin:1rem 0; font-weight:500; }
.info-box    { background-color:#EFF6FF; border-left:4px solid #3B82F6; color:#1E40AF; padding:1rem; border-radius:.75rem; margin:1rem 0; font-weight:500; }
.error-box   { background-color:#FEF2F2; border-left:4px solid #EF4444; color:#991B1B; padding:1rem; border-radius:.75rem; margin:1rem 0; font-weight:500; }

.stButton > button {
    background: linear-gradient(135deg, #7C3AED 0%, #6D28D9 100%) !important;
    color: white !important; border: none !important; border-radius: .75rem !important;
    padding: .75rem 1.5rem !important; font-weight: 600 !important;
    box-shadow: 0 4px 6px rgba(124,58,237,0.25) !important;
    transition: all 0.3s ease !important; width: 100% !important;
}
.stButton > button:hover {
    box-shadow: 0 6px 12px rgba(124,58,237,0.35) !important;
    transform: translateY(-1px) !important;
}

.section-header {
    font-size: 1.5rem; font-weight: 700; color: #334155;
    margin-top: 2rem; margin-bottom: 1rem; padding-bottom: 0.5rem;
}
.section-title {
    font-size: 1.25rem; font-weight: 800; color: #1e1040;
    padding: .5rem 0 .6rem; margin: 1.5rem 0 .75rem;
    border-bottom: 3px solid #7C3AED; display: inline-block;
}
.badge-pref {
    display: inline-block;
    background: linear-gradient(135deg,#7C3AED,#4C1D95);
    color: white; font-size: .78rem; font-weight: 700;
    padding: .3rem .9rem; border-radius: 99px; margin-bottom: .75rem;
    letter-spacing: .04em; text-transform: uppercase;
}
hr.divider { border-color: #F1F5F9; margin: 2rem 0; }
.footer-text {
    text-align: center; color: #94A3B8; padding: 3rem 0;
    font-size: 0.875rem; border-top: 1px solid #F1F5F9; margin-top: 3rem;
}

.marg-row { display:flex; gap:1.25rem; flex-wrap:wrap; margin:1.25rem 0; }
.marg-card {
    flex:1; min-width:240px; padding:1.25rem;
    border-radius:12px; border:1px solid rgba(0,0,0,0.06);
    background:#fff; box-shadow: 0 4px 14px rgba(15,23,42,0.05);
}
.marg-card h5 { margin:0 0 .9rem 0; font-size:1rem; color:#1e1040; font-weight:700; }
.marg-row-inner { display:flex; justify-content:space-between; gap:1rem; }
.marg-col .marg-label { font-size:.75rem; color:#9ca3af; margin:0 0 .2rem; }
.marg-col .marg-val   { font-weight:700; font-size:1.3rem; margin:0; }
.marg-sep  { border-top:1px solid #f3f4f6; padding-top:.9rem; margin-top:.9rem; }
.green-val { color:#16a34a; }
.red-val   { color:#dc2626; }
.blue-val  { color:#1d4ed8; }
.orange-val{ color:#d97706; }

.stella-wrap {
    background: #FFFFFF;
    border-radius: 1rem;
    border: 1px solid #E5E7EB;
    box-shadow: 0 4px 24px rgba(124,58,237,.08);
    overflow: hidden;
    margin: 1.5rem 0;
}
.stella-header {
    display: flex; align-items: center; gap: .875rem;
    padding: 1rem 1.4rem;
    background: linear-gradient(135deg, #7C3AED 0%, #4C1D95 100%);
}
.stella-avatar {
    width: 38px; height: 38px; border-radius: 50%;
    background: rgba(255,255,255,.2);
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem; flex-shrink: 0;
    border: 1.5px solid rgba(255,255,255,.35);
}
.stella-name  { color: #FFFFFF; font-weight: 700; font-size: .95rem; line-height: 1.2; }
.stella-sub   { color: rgba(255,255,255,.65); font-size: .72rem; margin-top: .1rem; }
.stella-badge {
    margin-left: auto;
    background: rgba(255,255,255,.18);
    border: 1px solid rgba(255,255,255,.3);
    color: #fff; font-size: .63rem; font-weight: 700;
    letter-spacing: .07em; text-transform: uppercase;
    padding: .2rem .65rem; border-radius: 99px;
}
.stella-body {
    padding: 1.4rem 1.5rem;
    display: flex; flex-direction: column; gap: 1.25rem;
}
.stella-section-label {
    font-size: .67rem; font-weight: 700; letter-spacing: .1em;
    text-transform: uppercase; color: #7C3AED; margin-bottom: .4rem;
    display: flex; align-items: center; gap: .4rem;
}
.stella-section-label::after {
    content: ''; flex: 1; height: 1px; background: #EDE9FE;
}
.stella-text { font-size: .875rem; color: #374151; line-height: 1.7; margin: 0; }
.stella-highlight-box {
    background: #F5F3FF;
    border: 1px solid #DDD6FE;
    border-left: 4px solid #7C3AED;
    border-radius: 0 .5rem .5rem 0;
    padding: .8rem 1rem;
    font-size: .875rem; color: #4C1D95; font-weight: 600; line-height: 1.6;
}
.stella-combo-box {
    background: #FFF7ED;
    border: 1px solid #FED7AA;
    border-left: 4px solid #F97316;
    border-radius: 0 .5rem .5rem 0;
    padding: .8rem 1rem;
    font-size: .875rem; color: #9A3412; font-weight: 600; line-height: 1.6;
}
.stella-products { display: flex; flex-direction: column; gap: .5rem; }
.stella-product-card {
    display: flex; align-items: flex-start; gap: .75rem;
    background: #FAFAFA;
    border: 1px solid #E5E7EB;
    border-radius: .625rem; padding: .7rem .95rem;
    transition: border-color .15s, box-shadow .15s;
}
.stella-product-card:hover {
    border-color: #C4B5FD;
    box-shadow: 0 2px 8px rgba(124,58,237,.08);
}
.stella-product-num {
    width: 22px; height: 22px; flex-shrink: 0; border-radius: 50%;
    background: linear-gradient(135deg, #7C3AED, #6D28D9);
    color: #fff; font-size: .67rem; font-weight: 700;
    display: flex; align-items: center; justify-content: center;
    margin-top: .1rem;
}
.stella-product-name   { font-size: .82rem; font-weight: 700; color: #111827; margin: 0 0 .12rem; }
.stella-product-motivo { font-size: .78rem; color: #6B7280; line-height: 1.5; margin: 0; }
.stella-steps { display: flex; flex-direction: column; gap: .45rem; }
.stella-step  {
    display: flex; align-items: flex-start; gap: .7rem;
    font-size: .875rem; color: #374151; line-height: 1.6;
}
.stella-step-num {
    flex-shrink: 0; width: 20px; height: 20px; border-radius: 50%;
    background: #EDE9FE; color: #7C3AED;
    font-size: .67rem; font-weight: 700;
    display: flex; align-items: center; justify-content: center;
    margin-top: .22rem;
}
.stella-script {
    background: #F9FAFB;
    border-left: 3px solid #7C3AED;
    border-radius: 0 .5rem .5rem 0;
    padding: .8rem 1rem;
    font-size: .875rem; color: #374151;
    font-style: italic; line-height: 1.65;
}
.stella-script-wrap {
    background: #F0FDF4;
    border: 1px solid #BBF7D0;
    border-radius: .75rem;
    overflow: hidden;
}
.stella-script-label {
    display: flex; align-items: center; justify-content: space-between;
    padding: .55rem 1rem;
    background: #DCFCE7;
    border-bottom: 1px solid #BBF7D0;
    font-size: .68rem; font-weight: 700; letter-spacing: .08em;
    text-transform: uppercase; color: #166534;
}
.stella-script-copy-btn {
    background: #16A34A; color: white; border: none; border-radius: .35rem;
    font-size: .68rem; font-weight: 700; padding: .2rem .65rem; cursor: pointer;
    letter-spacing: .04em; transition: background .15s;
}
.stella-script-copy-btn:hover { background: #15803D; }
.stella-script-body {
    padding: .9rem 1.1rem;
    font-size: .875rem; color: #166534; line-height: 1.75;
    white-space: pre-line; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
.stella-wpp-badge {
    display: inline-flex; align-items: center; gap: .3rem;
    background: #DCFCE7; color: #15803D;
    font-size: .63rem; font-weight: 700; letter-spacing: .05em;
    padding: .15rem .55rem; border-radius: 99px;
    text-transform: uppercase;
}
.stella-profile-grid {
    display: grid; grid-template-columns: 1fr 1fr; gap: .6rem;
}
.stella-profile-tag {
    display: flex; align-items: flex-start; gap: .5rem;
    background: #FAFAFA; border: 1px solid #E5E7EB;
    border-radius: .5rem; padding: .55rem .75rem;
}
.stella-profile-icon { font-size: .9rem; flex-shrink: 0; margin-top: .05rem; }
.stella-profile-label { font-size: .65rem; color: #9CA3AF; font-weight: 600; text-transform: uppercase; letter-spacing: .06em; margin: 0 0 .15rem; }
.stella-profile-value { font-size: .82rem; color: #111827; font-weight: 500; margin: 0; line-height: 1.4; }
.stella-closing-grid { display: flex; flex-direction: column; gap: .5rem; }
.stella-closing-item {
    display: flex; align-items: flex-start; gap: .65rem;
    padding: .6rem .85rem;
    background: #F0FDF4; border: 1px solid #BBF7D0;
    border-radius: .5rem;
}
.stella-closing-num {
    flex-shrink: 0; width: 20px; height: 20px; border-radius: 50%;
    background: #16A34A; color: #fff; font-size: .65rem; font-weight: 700;
    display: flex; align-items: center; justify-content: center; margin-top: .1rem;
}
.stella-closing-text { font-size: .82rem; color: #166534; line-height: 1.55; margin: 0; }
.stella-alerts { display: flex; flex-direction: column; gap: .4rem; }
.stella-alert  {
    display: flex; align-items: flex-start; gap: .55rem;
    background: #FFFBEB;
    border: 1px solid #FDE68A;
    border-radius: .5rem; padding: .55rem .85rem;
    font-size: .8rem; color: #92400E; line-height: 1.55;
}
.stella-tip {
    background: #F0FDF4;
    border: 1px solid #BBF7D0;
    border-left: 4px solid #10B981;
    border-radius: 0 .5rem .5rem 0;
    padding: .8rem 1rem;
    font-size: .875rem; color: #065F46; line-height: 1.65;
}
.stella-tip-label {
    font-size: .65rem; font-weight: 700; letter-spacing: .1em;
    text-transform: uppercase; color: #059669; margin-bottom: .35rem;
}

.chat-container {
    background:#fff; border-radius:1.25rem;
    border:1px solid #ede9fe; box-shadow:0 8px 32px rgba(30,16,64,.12);
    overflow:hidden; margin:1.5rem 0;
}
.chat-header {
    background: linear-gradient(135deg,#1e1040,#2d1b6e);
    padding:1rem 1.25rem; display:flex; align-items:center; gap:.75rem;
}
.chat-body {
    padding:1rem; background:#faf8ff;
    min-height:120px; max-height:340px; overflow-y:auto;
    display:flex; flex-direction:column; gap:.5rem;
}
.msg-user {
    align-self:flex-end; background:#ede9fe; color:#1e1040;
    border-radius:1rem 1rem 0 1rem; padding:.6rem 1rem;
    font-size:.88rem; max-width:78%; line-height:1.5;
}
.msg-stella {
    align-self:flex-start;
    background: linear-gradient(135deg,#1e1040,#2d1b6e);
    color:#e2d9f3; border-radius:1rem 1rem 1rem 0;
    padding:.6rem 1rem; font-size:.88rem; max-width:82%; line-height:1.55;
}
.chat-empty { text-align:center; padding:1.5rem 1rem; color:#9ca3af; font-size:.85rem; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# CARTÕES
# ============================================================================
NOSSOS_PRODUTOS       = ["STARCARD","ANTICIPAY","STARBANK","UASPREV"]
CARTOES_CONHECIDOS    = ["NIO","DAYCOVAL","BMG","PAN","MEUCASHCARD","PINE",
                         "BRADESCO","SANTANDER","OLÉ","BIG CARD","DAYC","IND",
                         "PANAMERICANO","MASTER","CREDCESTA","BRCARD","BANCO ALFA","EAGLE"]
CARTOES_NAO_COMPRADOS = ["QISTA","PIX CARD","C CONSIG","CAPITAL","MAXIMA",
                         "FY DIGITAL","CLICKBANK","PIXCARD","VEMCARD"]

def refresh_cartoes_from_db():
    global NOSSOS_PRODUTOS, CARTOES_CONHECIDOS, CARTOES_NAO_COMPRADOS
    try:
        init_db()
        n  = load_cartoes("nossos_produtos")
        c  = load_cartoes("cartoes_conhecidos")
        nc = load_cartoes("cartoes_nao_comprados")
        if n or c:
            NOSSOS_PRODUTOS, CARTOES_CONHECIDOS, CARTOES_NAO_COMPRADOS = n, c, nc
    except Exception:
        pass

# ============================================================================
# EXTRAÇÃO DE TEXTO
# ============================================================================
@st.cache_data
def extrair_texto_pdf(bytes_: bytes) -> str:
    texto = ""
    try:
        with pdfplumber.open(io.BytesIO(bytes_)) as pdf:
            for p in pdf.pages:
                t = p.extract_text()
                if t: texto += t + "\n"
    except Exception: pass
    if not texto.strip():
        try:
            for p in PyPDF2.PdfReader(io.BytesIO(bytes_)).pages:
                texto += (p.extract_text() or "") + "\n"
        except Exception: pass
    return texto


def extrair_texto_imagem(bytes_: bytes) -> str:
    try:
        img = Image.open(io.BytesIO(bytes_))
        if img.mode != "RGB": img = img.convert("RGB")
        w, h = img.size
        if w > 1280: img = img.resize((1280, int(h*1280/w)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.standard_b64encode(buf.getvalue()).decode()
        client = Groq(api_key=_groq_key())
        r = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role":"user","content":[
                {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}"}},
                {"type":"text","text":(
                    "Extraia TODO o texto deste holerite brasileiro.\n"
                    "Valores em formato 12.371,38 | campo+valor na mesma linha | "
                    "preserve nome da prefeitura | transcreva linha a linha."
                )}
            ]}],
            max_tokens=4096, temperature=0
        )
        t = r.choices[0].message.content
        def fix(s):
            def sub(m):
                v = m.group(0)
                if "." in v and "," in v: v = v.replace(",","X").replace(".",",").replace("X",".")
                return v
            return re.sub(r"\d{1,3}(?:,\d{3})*\.\d{2}", sub, s)
        return fix(t)
    except Exception as e:
        st.error(f"Erro imagem: {e}"); return ""


def _groq_key() -> str:
    try: return "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"
    except Exception: return os.environ.get("GROQ_API_KEY","")

# ============================================================================
# ANÁLISE HOLERITE VIA IA
# ============================================================================
def analisar_holerite_ia(texto: str) -> Dict:
    key = _groq_key()
    if not key: return {"erro": "GROQ_API_KEY não configurada"}

    prompt = f"""Você é especialista em folha de pagamento brasileira.
Analise o holerite e retorne APENAS JSON válido (sem markdown).

NOSSOS PRODUTOS: {", ".join(NOSSOS_PRODUTOS)}
CARTÕES CONCORRENTES: {", ".join(CARTOES_CONHECIDOS)}
CARTÕES NÃO COMPRAMOS: {", ".join(CARTOES_NAO_COMPRADOS)}

HOLERITE:
{texto[:8000]}

JSON (valores como float sem ponto de milhar, ex: 12371.38):
{{
  "prefeitura": "nome completo do órgão",
  "nome": "NOME COMPLETO",
  "matricula": "número",
  "regime": "ESTATUTÁRIO|CELETISTA|COMISSIONADO|TEMPORÁRIO|CONTRATADO|NÃO IDENTIFICADO",
  "vencimentos_total": 0.00,
  "descontos_total": 0.00,
  "liquido": 0.00,
  "salario_base": 0.00,
  "descontos_obrigatorios": {{"inss":0.00,"irrf":0.00,"previdencia":0.00,"total":0.00}},
  "vencimentos_fixos": {{
    "vencimento_base":0.00,"adicional_tempo_servico":0.00,"gratificacao":0.00,
    "sexta_parte":0.00,"insalubridade":0.00,"hora_ativ_extra_classe":0.00,
    "horas_extras":0.00,"aula_suplementar":0.00,
    "outros_fixos":[],"total":0.00
  }},
  "proventos_raw": [
    {{"descricao":"texto exato do holerite","referencia":"referência/qtd ex: 150 ou 10%","valor":0.00}}
  ],
  "descontos_raw": [
    {{"descricao":"texto exato do holerite","referencia":"referência/qtd","valor":0.00}}
  ],
  "cartoes": [
    {{"descricao":"texto da linha","valor":0.00,
      "tipo":"nosso|concorrente|nao_comprado|desconhecido","instituicao":"nome"}}
  ],
  "emprestimos": [{{"descricao":"texto","valor":0.00}}]
}}

REGRAS CRÍTICAS — LEIA COM ATENÇÃO:

[VALORES] Todos os valores numéricos devem ser POSITIVOS (nunca negativos)

[REGIME] ESTATUTARIO/EFETIVO → ESTATUTÁRIO | CLT → CELETISTA

[DESCONTOS OBRIGATÓRIOS] descontos_obrigatorios contém SOMENTE: INSS, IRRF e Previdência.
  - inss = INSS / I.N.S.S
  - irrf = IRRF / Imposto de Renda / I.R.R.F
  - previdencia = Previdência Municipal/RPPS/IPSM/FUNPREV/COTIAPREV/COTIA-PREV/PREVIMUNICIPAL
  NÃO incluir: UASPREV (vai em emprestimos), cartões, plano de saúde, vale transporte.

[LISTAS BRUTAS PARA EXIBIÇÃO]
  proventos_raw = lista de TODOS os proventos do holerite com referência e valor exatos.
  descontos_raw = lista de TODOS os descontos do holerite com referência e valor exatos.

[CARTÕES] cartoes = linhas de desconto que sejam cartão de crédito consignado ou saque.
  Classificação tipo:
  - "nosso" se contém: {", ".join(NOSSOS_PRODUTOS)}
  - "nao_comprado" se contém: {", ".join(CARTOES_NAO_COMPRADOS[:5])}
  - "concorrente" se contém: {", ".join(CARTOES_CONHECIDOS[:6])}
  - "desconhecido" se for cartão mas não se encaixa acima

[EMPRÉSTIMOS] emprestimos = linhas de desconto que sejam empréstimo consignado.

[SALÁRIO BASE] salario_base = APENAS valor da rubrica principal: VENCIMENTO ESTATUTÁRIO / SALÁRIO BASE / SUBSÍDIO / VENCIMENTO BÁSICO

[VENCIMENTOS FIXOS]
  - vencimento_base = SEMPRE 0
  - horas_extras = SEMPRE 0
  - outros_fixos = proventos FIXOS/PERMANENTES sem campo próprio

- RETORNE SÓ O JSON
"""
    try:
        client = Groq(api_key=key)
        r = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role":"user","content":prompt}],
            max_tokens=2000, temperature=0
        )
        c = r.choices[0].message.content.strip()
        c = re.sub(r"^```json\s*","",c); c = re.sub(r"^```\s*","",c); c = re.sub(r"\s*```$","",c)
        s, e = c.find("{"), c.rfind("}")+1
        if s >= 0 and e > s: c = c[s:e]
        data = json.loads(c)

        def abs_fields(obj):
            if isinstance(obj, dict):
                return {k: (abs(v) if isinstance(v, (int,float)) and k not in ("total",) else abs_fields(v))
                        for k, v in obj.items()}
            if isinstance(obj, list):
                return [abs_fields(i) for i in obj]
            return obj
        data = abs_fields(data)

        _do_orig = {
            "inss":        abs(data.get("descontos_obrigatorios",{}).get("inss",0)),
            "irrf":        abs(data.get("descontos_obrigatorios",{}).get("irrf",0)),
            "previdencia": abs(data.get("descontos_obrigatorios",{}).get("previdencia",0)),
        }
        data["_descontos_originais"] = _do_orig

        for lst in ("proventos_raw", "descontos_raw"):
            data.setdefault(lst, [])
            for item in data[lst]:
                if "valor" in item:
                    item["valor"] = abs(item.get("valor", 0))

        _EMP_KW  = ["emprestimo","emprest","financiamento","delta global","bmp",
                    "credito pessoal","cp consig","cef","banco industrial","taormina",
                    "uasprev"]
        _CART_KW = ["cartao","cred ","cart.","saque","anticipay","starcard","starbank",
                    "panamericano car","daycoval cart","bmg cart","credcesta",
                    "meucashcard","big card","brcard","monetarie","credifin","pixcard"]
        _NOSSOS_CARTOES = ["starcard","anticipay","starbank"]
        _NOSSOS_EMP = ["uasprev"]

        novos_cartoes = []
        novos_emp     = []

        for item in list(data.get("cartoes", [])):
            desc = str(item.get("descricao","")).lower()
            eh_nosso_emp  = any(p in desc for p in _NOSSOS_EMP)
            eh_emp_generico = any(kw in desc for kw in _EMP_KW) and not any(kw in desc for kw in _CART_KW)
            if eh_nosso_emp or eh_emp_generico:
                novos_emp.append({"descricao":item.get("descricao",""),
                                  "valor":abs(item.get("valor",0))})
            else:
                novos_cartoes.append(item)

        for item in list(data.get("emprestimos", [])):
            desc = str(item.get("descricao","")).lower()
            eh_nosso_emp = any(p in desc for p in _NOSSOS_EMP)
            eh_cart = any(kw in desc for kw in _CART_KW)
            eh_nosso_cart = any(p in desc for p in _NOSSOS_CARTOES)
            if eh_nosso_cart or (eh_cart and not eh_nosso_emp):
                tipo = "nosso" if eh_nosso_cart else "desconhecido"
                for p in CARTOES_NAO_COMPRADOS:
                    if p.lower() in desc: tipo="nao_comprado"; break
                else:
                    for p in CARTOES_CONHECIDOS:
                        if p.lower() in desc: tipo="concorrente"; break
                novos_cartoes.append({"descricao":item.get("descricao",""),
                                      "valor":abs(item.get("valor",0)),
                                      "tipo":tipo,"instituicao":""})
            else:
                novos_emp.append(item)

        seen_c, seen_e = set(), set()
        data["cartoes"]     = [c for c in novos_cartoes
                               if str(c.get("descricao","")) not in seen_c
                               and not seen_c.add(str(c.get("descricao","")))]
        data["emprestimos"] = [e for e in novos_emp
                               if str(e.get("descricao","")) not in seen_e
                               and not seen_e.add(str(e.get("descricao","")))]

        do = data.get("descontos_obrigatorios", {})
        uasprev_em_emp = sum(abs(e.get("valor",0)) for e in data.get("emprestimos",[])
                             if "UASPREV" in str(e.get("descricao","")).upper())
        if uasprev_em_emp > 0 and abs(do.get("previdencia",0) - uasprev_em_emp) < 0.50:
            do["previdencia"] = 0.0
        do["total"] = do.get("inss",0) + do.get("irrf",0) + do.get("previdencia",0)
        data["descontos_obrigatorios"] = do

        vf = data.get("vencimentos_fixos", {})
        vf["vencimento_base"] = 0
        _perm_campos = ["adicional_tempo_servico","gratificacao","sexta_parte",
                        "insalubridade","hora_ativ_extra_classe","grat_desempenho",
                        "adicional_noturno","quinquenio","trienio","representacao",
                        "abono","progressao_salarial","titulacao"]
        _var_kw_prom = ["aula suplementar","hora extra","horas extras","ferias",
                        "férias","1/3","13 salario","decimo terceiro","diaria"]
        total_vf = sum(abs(vf.get(k,0)) for k in _perm_campos)
        for it in (vf.get("outros_fixos") or []):
            if not isinstance(it, dict): continue
            d4 = str(it.get("descricao","")).lower()
            v4 = abs(it.get("valor",0))
            if v4 > 0 and not any(kw in d4 for kw in _var_kw_prom):
                total_vf += v4
        vf["total"] = total_vf
        data["vencimentos_fixos"] = vf

        for item in data.get("cartoes",[]): item["valor"] = abs(item.get("valor",0))
        for item in data.get("emprestimos",[]): item["valor"] = abs(item.get("valor",0))

        return data
    except Exception as e:
        return {"erro": f"Erro IA: {e}"}


# ============================================================================
# STELLA — ESTRATÉGIA (v2)
# ============================================================================
def stella_estrategia(dados: Dict, margem: Dict = None) -> Dict:
    key = _groq_key()
    if not key:
        return {}

    margem = margem or {}
    marg_ok = margem.get("disponivel", False)

    if marg_ok:
        emp = margem.get("emprestimo", {})
        cc  = margem.get("cartao_consignado", {})
        cb  = margem.get("cartao_beneficio", {})
        marg_bloco = f"""
MARGEM CONSIGNÁVEL CALCULADA:
  Base de Cálculo:              R$ {margem.get('base_calculo', 0):.2f}
  Empréstimo — Total:           R$ {emp.get('margem_total', 0):.2f} ({int(emp.get('percentual', 0)*100)}%)
  Empréstimo — Comprometido:    R$ {emp.get('comprometido', 0):.2f}
  Empréstimo — DISPONÍVEL:      R$ {emp.get('disponivel', 0):.2f}  ← parcela máxima disponível
  Cartão Cons. — Total:         R$ {cc.get('margem_total', 0):.2f} ({int(cc.get('percentual', 0)*100)}%)
  Cartão Cons. — Comprometido:  R$ {cc.get('comprometido', 0):.2f}
  Cartão Cons. — DISPONÍVEL:    R$ {cc.get('disponivel', 0):.2f}
  Cartão Benef. — Total:        R$ {cb.get('margem_total', 0):.2f} ({int(cb.get('percentual', 0)*100)}%)
  Cartão Benef. — Comprometido: R$ {cb.get('comprometido', 0):.2f}
  Cartão Benef. — DISPONÍVEL:   R$ {cb.get('disponivel', 0):.2f}
  Cartões nossos:                R$ {margem.get('cartoes_nossos', 0):.2f}
  Cartões concorrentes:          R$ {margem.get('cartoes_concorrentes', 0):.2f}
  Cartões não compramos:         R$ {margem.get('cartoes_nao_comp', 0):.2f}
  Total empréstimos ativos:      R$ {margem.get('total_emprestimos', 0):.2f}
"""
    else:
        marg_bloco = "MARGEM: Não calculada para esta prefeitura — trabalhe com os dados brutos.\n"

    do = dados.get("descontos_obrigatorios") or {}
    regime = dados.get("regime", "NÃO IDENTIFICADO").upper()
    eh_efetivo   = any(r in regime for r in ["ESTATUTÁRIO", "EFETIVO", "ESTÁVEL"])
    eh_temporario = any(r in regime for r in ["TEMPORÁRIO", "COMISSIONADO", "CONTRATADO", "NÃO IDENTIFICADO"])

    cartoes      = dados.get("cartoes", [])
    emprestimos  = dados.get("emprestimos", [])
    concorrentes = [c for c in cartoes if c.get("tipo") == "concorrente"]
    nossos       = [c for c in cartoes if c.get("tipo") == "nosso"]
    nao_comp     = [c for c in cartoes if c.get("tipo") == "nao_comprado"]
    total_conc   = sum(abs(c.get("valor", 0)) for c in concorrentes)
    total_nossos = sum(abs(c.get("valor", 0)) for c in nossos)
    total_emp    = sum(abs(e.get("valor", 0)) for e in emprestimos)

    emp_disp = margem.get("emprestimo", {}).get("disponivel", 0) if marg_ok else 0
    cc_disp  = margem.get("cartao_consignado", {}).get("disponivel", 0) if marg_ok else 0
    cb_disp  = margem.get("cartao_beneficio", {}).get("disponivel", 0) if marg_ok else 0

    prompt = f"""Você é a Stella, a melhor vendedora e estrategista de crédito consignado do Starbank Grupo.
Você é mais inteligente que qualquer atendente humano — você CRUZA dados, pensa em combos de produtos,
calcula oportunidades reais e gera estratégias que o atendente nunca pensaria sozinho.

ESTILO OBRIGATÓRIO — VIÉS EDUCACIONAL:
Cada recomendação deve ter DUAS partes obrigatórias, sempre separadas por " — Por que: ":
  Parte 1 — O QUE fazer (ação concreta com valor real)
  Parte 2 — Por que isso faz sentido (lógica financeira simples, 1-2 frases, como se explicasse para alguém que nunca trabalhou com crédito)

O "Por que" deve ensinar o analista sobre o produto, não só justificar a venda.
Exemplos de bom "Por que":
  "Ofereça Compra de Dívida dos R$ X em cartões — Por que: na Compra de Dívida assumimos
   a dívida do concorrente e refinanciamos com condições melhores. O cliente troca uma parcela
   ruim por uma melhor, e a diferença entre o que ele devia lá e o que a gente libera aqui
   vai direto no bolso dele como dinheiro vivo (o troco)."
  "Simule empréstimo de até R$ X/mês — Por que: empréstimo consignado tem taxa menor que
   qualquer crédito pessoal porque o desconto sai direto da folha, o risco de calote para o
   banco é quase zero, e esse risco menor se traduz em parcela menor para o cliente."
  "A margem de cartão está negativa, não ofereça cartão agora — Por que: a lei limita quanto
   pode ser descontado em cartões como percentual do salário, e esse limite já foi ultrapassado.
   Oferecer mais cartão seria recusado na análise e constrangeria o cliente."

Este formato deve aparecer em: oportunidade_principal, motivo de cada produto, cada passo do plano.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PORTFÓLIO COMPLETO:
{PORTFOLIO}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DADOS DO CLIENTE:
  Prefeitura:    {dados.get("prefeitura", "N/A")}
  Nome:          {dados.get("nome", "N/A")}
  Regime:        {regime}
  Salário Base:  R$ {dados.get("salario_base", 0):.2f}
  Vencimentos:   R$ {dados.get("vencimentos_total", 0):.2f}
  Líquido:       R$ {dados.get("liquido", 0):.2f}
  INSS:          R$ {do.get("inss", 0):.2f}
  IRRF:          R$ {do.get("irrf", 0):.2f}
  Previdência:   R$ {do.get("previdencia", 0):.2f}

CONSIGNAÇÕES ATIVAS:
  Cartões concorrentes ({len(concorrentes)} itens, R$ {total_conc:.2f}/mês):
{chr(10).join(f"    • {c.get('descricao','')} = R$ {c.get('valor',0):.2f}" for c in concorrentes) or "    (nenhum)"}
  Nossos contratos ({len(nossos)} itens, R$ {total_nossos:.2f}/mês):
{chr(10).join(f"    • {c.get('descricao','')} = R$ {c.get('valor',0):.2f}" for c in nossos) or "    (nenhum)"}
  Cartões não compramos ({len(nao_comp)} itens):
{chr(10).join(f"    • {c.get('descricao','')} = R$ {c.get('valor',0):.2f}" for c in nao_comp) or "    (nenhum)"}
  Empréstimos ativos ({len(emprestimos)} itens, R$ {total_emp:.2f}/mês):
{chr(10).join(f"    • {e.get('descricao','')} = R$ {e.get('valor',0):.2f}" for e in emprestimos) or "    (nenhum)"}

{marg_bloco}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGRAS DE OURO — SIGA OBRIGATORIAMENTE:

[REGIME]
{"• ESTATUTÁRIO/EFETIVO: Pode usar TODOS os produtos. Margens maiores, prazos até 120 meses." if eh_efetivo else ""}
{"• TEMPORÁRIO/COMISSIONADO/CONTRATADO: SOMOS UM DOS ÚNICOS QUE FAZEMOS CRÉDITO PARA ESSE PERFIL. Use como diferencial absoluto. Produtos viáveis: AUXÍLIO SERVIDOR (2 meses, renovável) e VALE CONSIGNADO (1 parcela). NÃO oferecer empréstimo longo prazo nem cartão consignado padrão." if eh_temporario else ""}

[COMPRA DE DÍVIDA — REGRA DE OURO]
{"• Cliente tem R$ "+str(round(total_conc,2))+" em cartões concorrentes → SEMPRE inicie pela Compra de Dívida." if concorrentes else "• Sem cartões concorrentes — foco em empréstimo e cartão."}
• Na Compra de Dívida o cliente pode receber TROCO (dinheiro vivo) — mas NUNCA invente o valor do troco, pois dependeria do saldo devedor que não temos. Mencione apenas que "existe possibilidade de troco".
{"• COMBO PODEROSO: Compra de Dívida (R$ "+str(round(total_conc,2))+" de cartões) + Empréstimo (R$ "+str(round(emp_disp,2))+" disponível na margem) = cliente reorganiza dívidas E recebe dinheiro. É a venda dupla." if concorrentes and emp_disp > 50 else ""}

[MARGEM DISPONÍVEL POR PRODUTO — LEIA ANTES DE RECOMENDAR QUALQUER COISA]
  Empréstimo disponível:        R$ {emp_disp:.2f}  {"← TEM MARGEM, pode oferecer" if emp_disp > 0 else "← MARGEM LOTADA, NÃO oferecer empréstimo"}
  Cartão Consignado disponível: R$ {cc_disp:.2f}  {"← TEM MARGEM, pode oferecer" if cc_disp > 0 else "← MARGEM LOTADA, NÃO oferecer Cartão Consignado"}
  Cartão Benefício disponível:  R$ {cb_disp:.2f}  {"← TEM MARGEM, pode oferecer" if cb_disp > 0 else "← MARGEM LOTADA, NÃO oferecer Cartão Benefício"}

[REGRA ABSOLUTA DE MARGEM — NUNCA VIOLE]
• NUNCA recomende Empréstimo Consignado se emp_disp ≤ 0.
• NUNCA recomende Cartão Consignado se cc_disp ≤ 0 E não houver Compra de Dívida que libere margem.
• NUNCA recomende Cartão Benefício se cb_disp ≤ 0 E não houver Compra de Dívida que libere margem.
• EXCEÇÃO: Se houver Compra de Dívida viável, ela LIBERA margem de cartão → aí pode recomendar cartão DEPOIS da compra, explicando que a margem será liberada.
• Se todos os produtos têm margem ≤ 0 exceto Compra de Dívida → recomende SOMENTE a Compra de Dívida + o que ela viabiliza após a liberação.

[COMBOS INTELIGENTES — SÓ SE A MARGEM PERMITIR]
{"• COMBO DISPONÍVEL: Empréstimo (R$ "+str(round(emp_disp,2))+") + Cartão Cons. (R$ "+str(round(cc_disp,2))+") — ambos com margem positiva." if emp_disp > 0 and cc_disp > 0 else ""}
{"• Margem emp disponível > R$200 + cartão concorrente → Compra Dívida + Empréstimo (venda dupla)" if emp_disp > 200 and concorrentes else ""}
{"• Margem cc disponível > 0 + sem cartão nosso → Cartão Consignado ou Cartão Benefício" if cc_disp > 0 else ""}
{"• Margem lotada no cartão mas tem cartão concorrente → Compra de Dívida LIBERA margem E dá troco → depois ofereça cartão" if cc_disp <= 0 and concorrentes else ""}
• Nenhuma consignação + margem emp disponível → Empréstimo + Cartão Benefício (combo de entrada, SE ambos tiverem margem)
• Nosso contrato ativo + margem emp disponível → Refinanciamento para prazo maior libera margem mensal

[CÁLCULO DE PARCELA MÁXIMA]
• Parcela máx. empréstimo = R$ {emp_disp:.2f} {"(margem disponível)" if emp_disp > 0 else "(ZERO — não oferecer empréstimo direto)"}.
• Sempre cite este valor nos produtos que recomenda.
• Se emp_disp ≤ 0 → margem de empréstimo lotada, NÃO oferecer empréstimo consignado direto.

[PENSAMENTO CRIATIVO — OBRIGATÓRIO]
• IRRF alto = salário bruto alto = pode ter margem oculta não explorada.
• Muitos descontos + líquido baixo = cliente pressionado = precisa reorganizar = Compra de Dívida é a porta de entrada.
• Previdência alta + líquido baixo = produto de prazo curto (Auxílio Servidor, Vale Consignado) pesa menos.
• Cartão Consignado/Benefício: só recomende se a margem for positiva OU se a Compra de Dívida liberar essa margem — NUNCA recomende no vácuo.
• Se empréstimo nosso ativo → verifique refinanciamento para prazo maior, liberando margem.
• Cartões "não compramos" → cliente tem hábito de crédito consignado → fácil converter quando vencer, mencione no plano.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DADOS CALCULADOS PARA PERSONALIZAÇÃO:

  Primeiro nome do cliente: {(dados.get("nome","").split()[0].capitalize()) if dados.get("nome","") not in ("","N/A") else "servidor(a)"}
  Órgão/Prefeitura: {dados.get("prefeitura","").strip()}
  Total saindo em consignações na folha/mês: R$ {sum(abs(c.get("valor",0)) for c in cartoes) + sum(abs(e.get("valor",0)) for e in emprestimos):.2f}
  Cartões de outras instituições: {len([c for c in cartoes if c.get("tipo")=="concorrente"])} item(ns) — R$ {sum(abs(c.get("valor",0)) for c in cartoes if c.get("tipo")=="concorrente"):.2f}/mês total saindo na folha
  Margem de empréstimo disponível: R$ {emp_disp:.2f}
  Empréstimos ativos: {len(emprestimos)} contrato(s)

REGRA ABSOLUTA — TROCO:
Nunca calcule nem cite nenhum valor de troco. O troco depende do saldo devedor dos cartões,
que não temos — só temos a parcela mensal. Qualquer valor de troco seria INVENTADO.
Nos produtos_recomendados, mencione apenas que "pode liberar troco" sem valor algum.
Nos alertas e dica_fechamento: nunca cite R$ X de troco, diga apenas "possibilidade de troco".

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INSTRUÇÕES PARA CADA CAMPO DO JSON:

[resumo_cliente]
Escreva um RAIO-X financeiro analítico desta pessoa, não um resumo descritivo. Inclua:
- Regime e o que isso significa para elegibilidade de produtos
- Situação de margem produto a produto: livre, lotado, o que implica estrategicamente
- Leitura das consignações ativas: o que revelam sobre o comportamento financeiro e grau de comprometimento
- O ângulo de ataque mais forte com justificativa baseada nos números
- Um dado que chame atenção (ex: comprometimento alto, IRRF elevado, cartões de várias bandeiras, margem intocada)
Mínimo 4 frases. Seja analítico — não repita os dados, interprete-os.

[script_abertura]
Esta mensagem será COPIADA E COLADA no WhatsApp como PRIMEIRO CONTATO.
Objetivo: fazer o cliente PARAR o que está fazendo e RESPONDER.
Seja humano, direto, levemente intrigante — como um amigo que viu algo importante.

REGRAS META/WHATSAPP — OBRIGATÓRIAS:
- Sem links, URLs ou telefones
- Sem palavras de spam: "oferta", "promoção", "grátis", "clique", "acesse", "aproveite", "desconto", "exclusivo"
- Sem MAIÚSCULAS para ênfase — use *negrito* do WhatsApp apenas se necessário e com moderação
- Máximo 1 emoji, só se reforçar o tom (não decorativo)
- Tom de conversa real entre pessoas, não roteiro de call center

TÉCNICA: a mensagem deve criar um "loop aberto" na cabeça do cliente.
Ele precisa pensar "espera, o que encontraram sobre mim?" e sentir que PRECISA responder para fechar esse loop.
Para isso, seja específico o suficiente para parecer real, mas vago o suficiente para criar curiosidade.

ESTRUTURA OBRIGATÓRIA (5-7 linhas bem curtas, formatação mobile):
1. Saudação + primeiro nome + quem é (nome do analista = [nome], Starbank Grupo) — 1 linha só
2. Linha de contexto — mencione o órgão e algo NUMÉRICO ou ESPECÍFICO da situação dele que mostre que você realmente olhou (ex: quantidade de descontos na folha, valor aproximado saindo todo mês)
3. Linha de intriga — diga que identificou algo e que a maioria dos servidores não sabe que pode mudar
4. Consequência positiva vaga — o que isso pode significar para ele (sem dizer o produto)
5. Pergunta fechada simples — fácil de responder sim

PALAVRAS PROIBIDAS: "Empréstimo", "Cartão", "Crédito", "parcela", "taxa", "juros", "dívida", "reorganizar"
USE: "saindo na folha todo mês", "comprometido", "algo que pode mudar", "situação específica", "sobrar mais"

EXEMPLOS PARA CALIBRAR O TOM:

RUIM — genérico, parece disparo em massa:
"Oi Juscela! Aqui é a [nome] do Starbank. Você trabalha na Prefeitura de Tupã e pode ter condições especiais. Faz sentido eu te explicar?"

RUIM — corporativo demais:
"Analisei perfis de servidores da Prefeitura e vi que você tem comprometimentos que podem ser reorganizados."

BOM — específico, humano, loop aberto:
"Oi, Juscela!

Aqui é [nome], do Starbank Grupo.

Olhei os dados da sua folha e vi que sai um valor considerável todo mês em descontos — e encontrei uma situação que, pelo menos no seu caso, a maioria dos servidores nem sabe que existe.

Pode ser que sobre bem mais pra você no fim do mês do que está sobrando hoje.

Posso te contar em 2 minutos o que encontrei?"

ÓTIMO — gancho com número real, surpresa, urgência leve:
"Oi, Juscela!

Aqui é [nome], do Starbank.

Fiz uma análise aqui e vi que você tem R$ {sum(abs(c.get("valor",0)) for c in cartoes if c.get("tipo")=="concorrente"):.0f} saindo todo mês na sua folha em descontos de outras instituições.

Tem uma forma de manter esse mesmo desconto na folha, mas com uma condição bem melhor — e que ainda pode deixar um valor extra pra você.

Posso te explicar rapidinho como funciona?"

Use o exemplo ÓTIMO como base. Adapte para o perfil real com os dados calculados acima.
Escreva a mensagem FINAL pronta para copiar. Sem aspas, sem prefixo, sem explicação.
Use [nome] onde o analista vai inserir o nome dele.

[dica_fechamento]
Retorne exatamente 4 itens em lista. Use os FATOS ABAIXO — não invente nada além deles.
NUNCA cite valor de troco — diga apenas "possibilidade de troco".

FATOS REAIS DESTA SITUAÇÃO (use estes para construir cada argumento):
  • Líquido atual: R$ {dados.get("liquido", 0):.2f}/mês
  • Total saindo em consignações: R$ {sum(abs(c.get("valor",0)) for c in cartoes) + sum(abs(e.get("valor",0)) for e in emprestimos):.2f}/mês
  {"• Cartões concorrentes: " + ", ".join(f"{c.get('descricao','')} (R$ {c.get('valor',0):.2f}/mês)" for c in concorrentes) + f" — total R$ {total_conc:.2f}/mês saindo para outras instituições" if concorrentes else "• Sem cartões concorrentes identificados"}
  {"• Empréstimos ativos: " + ", ".join(f"{e.get('descricao','')} (R$ {e.get('valor',0):.2f}/mês)" for e in emprestimos) + f" — total R$ {total_emp:.2f}/mês" if emprestimos else "• Sem empréstimos ativos"}
  {"• Margem de empréstimo disponível: R$ " + f"{emp_disp:.2f} (pode usar para empréstimo consignado com parcela máxima de R$ {emp_disp:.2f})" if emp_disp > 0 else "• Margem de empréstimo: lotada"}
  {"• Nossos contratos ativos: " + ", ".join(f"{c.get('descricao','')}" for c in nossos) if nossos else "• Sem contratos nossos ativos — cliente novo para nós"}
  • Regime: {regime} {"— elegível para todos os produtos" if eh_efetivo else "— produtos limitados (Auxílio Servidor e Vale Consignado apenas)"}

MODELO PARA CADA ARGUMENTO — seja assim (específico, com dado real, ação clara):
  Item 1 (objeção mais provável + contorno com dado real deste cliente)
  Item 2 (gatilho emocional baseado na situação financeira real dele)
  Item 3 (diferencial Starbank mais relevante para este caso específico)
  Item 4 (argumento de fechamento — o mais forte, com o dado mais impactante disponível)

Escreva cada item como uma frase de argumentação direta, sem prefixo de categoria.
Exemplos do nível de especificidade esperado:
  "Se ele disser 'já tenho muitos descontos', mostre que a Compra de Dívida substitui os R$ {total_conc:.2f}/mês do {concorrentes[0].get('descricao','cartão concorrente') if concorrentes else 'cartão concorrente'} por uma condição nossa — o desconto na folha pode cair, não aumentar"
  "O gatilho certo é o controle: ele já paga R$ {sum(abs(c.get('valor',0)) for c in cartoes) + sum(abs(e.get('valor',0)) for e in emprestimos):.2f}/mês para outras instituições — a pergunta é se quer continuar assim ou ter isso num lugar só, com condições melhores"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMATO OBRIGATÓRIO PARA OS CAMPOS ABAIXO:
Cada campo que recomendar algo DEVE conter duas partes separadas por " — Por que: "
Exemplo: "Ofereça Compra de Dívida dos R$ 631/mês em cartões concorrentes — Por que: na Compra de Dívida assumimos a dívida do concorrente e refinanciamos com condições melhores; o cliente troca uma parcela ruim por uma melhor e a diferença vira dinheiro vivo pra ele."

GERE O JSON ABAIXO (sem markdown, sem texto fora do JSON):
{{
  "resumo_cliente": "raio-x analitico em 4+ frases — para cada observacao, explique O QUE o dado significa e POR QUE importa estrategicamente. Exemplo do formato: 'O IRRF de R$X indica salario bruto acima de R$Y, o que significa que a base de margem e maior que o liquido aparenta — ha mais espaco para credito do que parece a primeira vista.'",
  "oportunidade_principal": "O QUE: [acao + valor real] — Por que: [logica financeira simples explicando por que essa e a entrada certa para ESTE cliente, ensine o conceito]",
  "combo_recomendado": "se houver combo: O QUE: [combo com valores] — Por que funciona: [logica de por que os dois produtos juntos fazem sentido para o cliente]. String vazia se nao houver.",
  "produtos_recomendados": [
    {{"produto":"nome","motivo":"O QUE: [acao especifica com valor real] — Por que: [explicacao do produto e por que se encaixa neste caso, ensine o analista]. NUNCA invente valor de troco.","prioridade":1}},
    {{"produto":"nome","motivo":"O QUE: [acao] — Por que: [logica simples]","prioridade":2}},
    {{"produto":"nome","motivo":"O QUE: [acao] — Por que: [logica simples]","prioridade":3}}
  ],
  "plano_de_acao": [
    "Passo 1: [acao concreta com valor] — Por que comecar aqui: [logica da sequencia]",
    "Passo 2: [acao concreta] — O que isso destrava: [consequencia]",
    "Passo 3: [acao concreta]",
    "Passo 4: [acao concreta]"
  ],
  "alertas": [
    "alerta concreto se margem esta lotada ou se regime limita produtos ou se ha risco",
    "alerta se cartao concorrente e oportunidade urgente"
  ],
  "script_abertura": "mensagem final pronta para copiar — 4-6 linhas, primeiro nome do cliente, menciona o orgao, cria curiosidade, pergunta final, sem spam",
  "dica_fechamento": ["argumento 1 com valor real", "argumento 2 com objecao e contorno", "argumento 3 diferencial Starbank", "argumento 4 fechamento irresistivel"]
}}
RETORNE SO O JSON."""

    try:
        client = Groq(api_key=key)
        r = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2800,
            temperature=0.3,
        )
        c = r.choices[0].message.content.strip()
        c = re.sub(r"^```json\s*", "", c)
        c = re.sub(r"^```\s*", "", c)
        c = re.sub(r"\s*```$", "", c)
        s, e = c.find("{"), c.rfind("}") + 1
        if s >= 0 and e > s:
            c = c[s:e]
        result = json.loads(c)
        if isinstance(result.get("plano_de_acao"), str):
            result["plano_de_acao"] = [result["plano_de_acao"]]
        return result
    except Exception:
        return {}


# ============================================================================
# STELLA — CHAT (v2)
# ============================================================================
def stella_chat(pergunta: str, dados: Dict, historico: List, margem: Dict = None) -> str:
    key = _groq_key()
    if not key:
        return "API não configurada."

    margem    = margem or {}
    marg_ok   = margem.get("disponivel", False)
    do        = dados.get("descontos_obrigatorios") or {}
    regime    = dados.get("regime", "NÃO IDENTIFICADO").upper()
    eh_efetivo   = any(r in regime for r in ["ESTATUTÁRIO", "EFETIVO", "ESTÁVEL"])
    eh_temporario = any(r in regime for r in ["TEMPORÁRIO", "COMISSIONADO", "CONTRATADO", "NÃO IDENTIFICADO"])

    cartoes      = dados.get("cartoes", [])
    emprestimos  = dados.get("emprestimos", [])
    concorrentes = [c for c in cartoes if c.get("tipo") == "concorrente"]
    nossos       = [c for c in cartoes if c.get("tipo") == "nosso"]
    total_conc   = sum(abs(c.get("valor", 0)) for c in concorrentes)

    if marg_ok:
        emp = margem.get("emprestimo", {})
        cc  = margem.get("cartao_consignado", {})
        cb  = margem.get("cartao_beneficio", {})
        marg_bloco = f"""
MARGEM REAL CALCULADA:
  Base: R$ {margem.get('base_calculo', 0):.2f}
  Empréstimo disponível:        R$ {emp.get('disponivel', 0):.2f} (total R$ {emp.get('margem_total', 0):.2f}, comprometido R$ {emp.get('comprometido', 0):.2f})
  Cartão Consignado disponível: R$ {cc.get('disponivel', 0):.2f} (total R$ {cc.get('margem_total', 0):.2f}, comprometido R$ {cc.get('comprometido', 0):.2f})
  Cartão Benefício disponível:  R$ {cb.get('disponivel', 0):.2f} (total R$ {cb.get('margem_total', 0):.2f})
  Cartões concorrentes:          R$ {margem.get('cartoes_concorrentes', 0):.2f}
  Empréstimos ativos:            R$ {margem.get('total_emprestimos', 0):.2f}"""
    else:
        marg_bloco = "MARGEM: Não calculada para esta prefeitura — use dados brutos do holerite."

    system = f"""Você é a Stella, a estrategista de vendas mais inteligente do Starbank Grupo.
Você conhece TODOS os dados do holerite e da margem deste cliente. Responda de forma direta, prática
e com valores reais. Seja a vendedora que o atendente gostaria de ser — pense em combos, criatividade
e oportunidades que ele não enxergaria. Máximo 3 parágrafos curtos. Português brasileiro.

ESTILO OBRIGATÓRIO — VIÉS EDUCACIONAL:
Toda resposta deve ter duas camadas visíveis:
  1. O QUE fazer / qual é a situação (direto, com número real)
  2. POR QUE — explicação simples da lógica financeira, como se o analista nunca tivesse
     trabalhado com crédito consignado antes. Ensine, não só recomende.

Formato natural para usar nas respostas:
  "[Recomendação com valor real] — e o motivo é simples: [lógica em 1-2 frases acessíveis]."

Exemplos do nível de clareza esperado:
  "Comece pela Compra de Dívida dos R$ X em cartões concorrentes — o motivo é simples:
   na Compra de Dívida a gente assume a dívida de outra instituição e refinancia com
   condições melhores. O cliente deixa de pagar X/mês para o concorrente e passa a pagar
   menos pra gente, e a diferença entre o que ele devia lá e o que a gente libera aqui
   vai direto no bolso dele como dinheiro vivo (o 'troco'). Por isso é sempre a primeira oferta."

  "A margem de empréstimo ainda tem R$ X livre — isso significa que a lei permite descontar
   mais R$ X por mês da folha deste servidor sem problemas. É como se houvesse um 'espaço
   autorizado' na folha que pode ser convertido em crédito agora, com taxa bem menor do que
   qualquer empréstimo pessoal porque o risco de não pagar é quase zero (sai automático)."

  "Não recomendo o Cartão Consignado aqui porque a margem de cartão está negativa em R$ X —
   isso quer dizer que já está saindo mais do que o permitido na folha para cartões.
   Só faz sentido oferecer depois que a Compra de Dívida reorganizar e liberar esse espaço."

PORTFÓLIO: {PORTFOLIO}

━━━ DADOS DO CLIENTE ━━━
Nome: {dados.get("nome", "N/A")} | Regime: {regime}
Prefeitura: {dados.get("prefeitura", "N/A")}
Salário Base: R$ {dados.get("salario_base", 0):.2f} | Líquido: R$ {dados.get("liquido", 0):.2f}
Vencimentos: R$ {dados.get("vencimentos_total", 0):.2f}
INSS: R$ {do.get("inss", 0):.2f} | IRRF: R$ {do.get("irrf", 0):.2f} | Previdência: R$ {do.get("previdencia", 0):.2f}
CARTÕES: {json.dumps(dados.get("cartoes", []), ensure_ascii=False)}
EMPRÉSTIMOS: {json.dumps(dados.get("emprestimos", []), ensure_ascii=False)}
{marg_bloco}

━━━ REGRAS QUE VOCÊ DOMINA ━━━

REGIME:
{"• ESTATUTÁRIO → todos os produtos, prazos longos, margem maior." if eh_efetivo else ""}
{"• TEMPORÁRIO/COMISSIONADO → SOMOS UM DOS ÚNICOS que fazemos crédito para esse perfil. Use como diferencial. Produtos: Auxílio Servidor (2 meses) e Vale Consignado (1 parcela). NÃO oferecer empréstimo longo prazo." if eh_temporario else ""}

COMPRA DE DÍVIDA:
{"• Cliente tem R$ "+str(round(total_conc,2))+" em cartões concorrentes → SEMPRE inicie pela Compra de Dívida. O TROCO é dinheiro vivo para o cliente." if concorrentes else "• Sem cartões concorrentes — foco em empréstimo e cartão."}
{"• COMBO: Compra Dívida + Empréstimo com margem disponível = dinheiro duplo para o cliente." if concorrentes else ""}

PENSE FORA DA CAIXA (COM OS PÉS NO CHÃO):
• IRRF alto = salário bruto alto = margem possivelmente maior que parece.
• Muitos descontos = cliente pressionado = precisa reorganizar = Compra de Dívida é a porta de entrada.
• Previdência alta + líquido baixo = produto de prazo curto é mais digerível.
• Cartões "não compramos" = cliente tem hábito de crédito consignado = fácil converter.
• Nosso produto ativo = verifique refinanciamento para liberar margem e dar dinheiro de volta.

REGRA CRÍTICA DE MARGEM — NUNCA VIOLE:
• NUNCA sugira Cartão Consignado se a margem de cartão disponível for ≤ 0.
• NUNCA sugira Cartão Benefício se a margem de cartão disponível for ≤ 0.
• NUNCA sugira Empréstimo Consignado se a margem de empréstimo disponível for ≤ 0.
• EXCEÇÃO: Se houver Compra de Dívida viável, ela LIBERA margem de cartão → aí pode recomendar o cartão APÓS a compra, explicando que a margem será liberada."""

    msgs = [{"role": "system", "content": system}]
    for h in historico[-8:]:
        msgs.append({"role": h["role"], "content": h["content"]})
    msgs.append({"role": "user", "content": pergunta})

    try:
        client = Groq(api_key=key)
        r = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=msgs,
            max_tokens=800,
            temperature=0.45,
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        return f"Erro: {e}"


def stella_chat_lote(pergunta: str, lote_resultados: list, historico: list) -> str:
    """Chat contextualizado para análise em lote — responde sobre o grupo inteiro."""
    key = _groq_key()
    if not key: return "API não configurada."

    total        = len(lote_resultados)
    com_emp      = [r for r in lote_resultados if r.get("emp_disp",0) > 0]
    com_conc     = [r for r in lote_resultados if r.get("qt_concorrentes",0) > 0]
    com_nos      = [r for r in lote_resultados if r.get("qt_nossos",0) > 0]
    margem_total = sum(r.get("emp_disp",0) for r in com_emp)
    total_conc   = sum(r.get("total_concorrentes",0) for r in com_conc)

    from collections import Counter
    opps = Counter(r.get("oportunidade","") for r in lote_resultados)
    prefs = Counter(r.get("prefeitura","") for r in lote_resultados)

    top5 = sorted(lote_resultados, key=lambda r: r.get("emp_disp",0), reverse=True)[:5]
    top5_txt = "\n".join(
        f"  • {r.get('nome','')} ({r.get('prefeitura','')[:20]}) — "
        f"Emp. disp: R$ {r.get('emp_disp',0):.2f} | "
        f"Conc: {r.get('qt_concorrentes',0)} ({fmt(r.get('total_concorrentes',0))}/mês) | "
        f"{r.get('oportunidade','')}"
        for r in top5
    )
    todos_txt = "\n".join(
        f"  {i+1}. {r.get('nome','N/A')} | {r.get('prefeitura','')[:22]} | {r.get('regime','')[:12]} | "
        f"Líq: R${r.get('liquido',0):.2f} | EmpDisp: R${r.get('emp_disp',0):.2f} | "
        f"CartDisp: R${r.get('cc_disp',0):.2f} | "
        f"Conc: {r.get('qt_concorrentes',0)}x R${r.get('total_concorrentes',0):.2f}/mês | "
        f"Nossos: {r.get('qt_nossos',0)} | EmpAtivo: R${r.get('total_emprestimos',0):.2f}/mês | "
        f"Opp: {r.get('oportunidade','')}"
        for i, r in enumerate(lote_resultados)
    )

    intel = st.session_state.get("intel_mercado_payload", {})
    intel_bloco = (
        f"\nINTELIGÊNCIA DE MERCADO CALCULADA:\n{json.dumps(intel, ensure_ascii=False, indent=2)}\n"
        if intel else ""
    )

    system = f"""Você é a Stella, Chief Strategy Officer de crédito consignado do Starbank Grupo.
Você está respondendo ao CEO, ao gestor comercial ou à liderança sobre um LOTE de {total} servidores.
Seu papel aqui NÃO é operacional — você não orienta atendentes sobre como abordar clientes.
Você pensa em nível estratégico: market share, alocação de esforço comercial, ROI de campanha,
riscos de concentração, velocidade de conversão, vantagens competitivas e decisões de gestão.

Quando perguntarem sobre a aba "Inteligência de Mercado" ou sobre insights, gráficos ou análises
estratégicas do lote, use os dados abaixo para explicar, complementar e aprofundar a análise.
Seja a consultora que o CEO gostaria de ter — densa, direta, com números reais, sem rodeios.

ESTILO OBRIGATÓRIO:
- Responda como consultora sênior falando com C-level — direto, denso, sem rodeios
- Use dados reais para fundamentar cada afirmação com número
- Quando houver trade-offs ou riscos, nomeie-os explicitamente
- Máximo 3 parágrafos objetivos. Português brasileiro.

PORTFÓLIO: {PORTFOLIO}
{intel_bloco}
DADOS ESTRATÉGICOS DO LOTE:
  Total servidores analisados:       {total}
  Com margem de empréstimo livre:    {len(com_emp)} ({len(com_emp)/total*100:.0f}%) — R$ {margem_total:.2f} de capacidade instalada
  Com cartão concorrente ativo:      {len(com_conc)} servidores — R$ {total_conc:.2f}/mês vazando para concorrência
  Com nossos contratos ativos:       {len(com_nos)} servidores — base atual a defender
  Sem nenhuma consignação:           {total - len(com_nos) - len(com_conc)} servidores — mercado virgem

DISTRIBUIÇÃO DE OPORTUNIDADES (prioridade comercial):
{chr(10).join(f"  • {k}: {v} servidor(es)" for k,v in opps.most_common())}

PREFEITURAS PRESENTES NO LOTE:
{chr(10).join(f"  • {k}: {v} servidor(es)" for k,v in prefs.most_common())}

TOP 5 MAIORES OPORTUNIDADES INDIVIDUAIS:
{top5_txt}

LISTA COMPLETA DE SERVIDORES (ordenada por prioridade comercial):
{todos_txt}

CONTEXTO PARA DECISÕES GERENCIAIS:
- Ticket médio de empréstimo disponível: R$ {(margem_total / len(com_emp) if com_emp else 0):.2f} por servidor elegível
- % da base com concorrência ativa: {len(com_conc)/total*100:.0f}% — indica grau de disputa de mercado
- % da base exclusivamente nossa: {len(com_nos)/total*100:.0f}% — indica penetração e risco de churn"""

    msgs = [{"role":"system","content":system}]
    for h in historico[-8:]:
        msgs.append({"role":h["role"],"content":h["content"]})
    msgs.append({"role":"user","content":pergunta})

    try:
        client = Groq(api_key=key)
        r = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=msgs, max_tokens=800, temperature=0.4
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        return f"Erro: {e}"


# ============================================================================
# HELPERS DE FORMATAÇÃO
# ============================================================================
def fmt(v) -> str:
    try: return f"R$ {float(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")
    except: return "R$ 0,00"

def item_extrato(label, valor, cor="default", negrito=False, divisor=True) -> str:
    cores = {"red":"#DC2626","green":"#059669","blue":"#4F46E5","orange":"#D97706"}
    cv = cores.get(cor,"#111827"); w = "700" if negrito else "400"
    bd = "border-bottom:1px solid #F3F4F6;" if divisor else ""
    return (f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:6px 0;{bd}font-size:.9rem;font-family:sans-serif;">'
            f'<span style="color:#374151;">{label}</span>'
            f'<span style="color:{cv};font-weight:{w};">{fmt(valor)}</span></div>')

def opp_card(desc, sub, borda, bg1, bg2, n) -> str:
    return f"""<div style='padding:1rem;background:linear-gradient(135deg,{bg1},{bg2});
        border-left:5px solid {borda};border-radius:.6rem;margin:.75rem 0;
        box-shadow:0 2px 6px rgba(0,0,0,.05);'>
      <div style='display:flex;gap:.75rem;align-items:flex-start;'>
        <div style='width:28px;height:28px;background:{borda};color:white;
             border-radius:50%;display:flex;align-items:center;justify-content:center;
             font-size:.78rem;font-weight:700;flex-shrink:0;'>{n}</div>
        <div>
          <p style='margin:0;font-weight:600;color:#1a3a52;font-size:.88rem;'>{desc}</p>
          <p style='margin:.2rem 0 0;color:#555;font-size:.78rem;'>{sub}</p>
        </div>
      </div></div>"""

# ============================================================================
# RENDERIZA CARDS DE MARGEM
# ============================================================================
def render_margem_cards(margem: Dict, dados: Dict = None):
    if not margem.get("disponivel"):
        st.info(f"🔧 **Cálculo de Margem — Em Breve para esta prefeitura**\n\n"
                f"{margem.get('motivo','')}")
        return

    pkey = margem.get("prefeitura_key","")
    emp  = margem["emprestimo"]
    cc   = margem["cartao_consignado"]
    cb   = margem["cartao_beneficio"]

    def card_compact(titulo, icone, perc, marg_tot, comp, disp):
        disp_cls  = "green-val" if disp >= 0 else "red-val"
        disp_icon = "✅" if disp >= 0 else "⚠️"
        return f"""
        <div class="marg-card">
          <h5>{icone} {titulo}
            <span style="font-size:.72rem;color:#9ca3af;font-weight:400;">
              ({int(perc*100)}% da base)
            </span>
          </h5>
          <div class="marg-row-inner">
            <div class="marg-col">
              <p class="marg-label">Margem Total</p>
              <p class="marg-val blue-val">{fmt(marg_tot)}</p>
            </div>
            <div class="marg-col">
              <p class="marg-label">Comprometido</p>
              <p class="marg-val orange-val">{fmt(comp)}</p>
            </div>
          </div>
          <div class="marg-sep">
            <p class="marg-label">Disponível {disp_icon}</p>
            <p class="marg-val {disp_cls}">{fmt(disp)}</p>
          </div>
        </div>"""

    cards = card_compact("Empréstimo Consignado", "💵",
                         emp["percentual"], emp["margem_total"],
                         emp["comprometido"], emp["disponivel"])
    cards += card_compact("Cartão Consignado", "💳",
                          cc["percentual"], cc["margem_total"],
                          cc["comprometido"], cc["disponivel"])
    if cb["percentual"] > 0:
        cards += card_compact("Cartão Benefício", "🎁",
                              cb["percentual"], cb["margem_total"],
                              cb["comprometido"], cb["disponivel"])

    btype_labels = {
        "bruto_menos_descontos": "Bruto permanente − descontos compulsórios",
        "apenas_base":           "Apenas salário base − descontos compulsórios",
        "bruto_sem_deducao":     "Salário bruto (sem dedução de descontos)",
    }
    base_desc = btype_labels.get(margem.get("base_type",""), "")

    st.markdown(f"""
    <div style="background:#f8f7ff;border-radius:.75rem;padding:.85rem 1.1rem;
         margin-bottom:.75rem;border:1px solid #ede9fe;font-size:.82rem;">
      <strong style="color:#5b21b6;">📐 Base de Cálculo ({pkey}):</strong>
      <span style="color:#374151;"> {fmt(margem['base_calculo'])} — {base_desc}</span>
    </div>
    <div class="marg-row">{cards}</div>
    """, unsafe_allow_html=True)

    with st.expander("💰 Ver Composição Detalhada da Margem", expanded=False):
        col1, col2, col3 = st.columns(3, gap="medium")

        with col1:
            sal_bruto = margem.get("salario_bruto", 0)
            deducs    = margem.get("descontos_compulsorios", 0)
            base      = margem.get("base_calculo", 0)

            vf = (dados or {}).get("vencimentos_fixos", {}) if dados else {}
            pref_key   = margem.get("prefeitura_key", "")
            cfg_pref   = PREFEITURAS_CONFIG.get(pref_key, {})
            prov_campos_cfg = cfg_pref.get("proventos_campos", [])

            _CAMPO_LABEL = {
                "adicional_tempo_servico": "Adic. Tempo",
                "gratificacao": "Gratificação",
                "hora_ativ_extra_classe": "H.A. Extra Classe",
                "sexta_parte": "Sexta Parte",
                "insalubridade": "Insalubridade",
                "grat_desempenho": "Grat. Desempenho",
                "adicional_noturno": "Adic. Noturno",
                "quinquenio": "Quinquênio",
                "trienio": "Triênio",
                "representacao": "Representação",
                "abono": "Abono",
                "progressao_salarial": "Progressão Salarial",
                "titulacao": "Titulação",
                "ativ_trab_pedag": "Ativ. Trab. Pedag.",
                "vantagens_pessoais": "Vant. Pessoais",
                "adicional_fixo": "Adic. Fixo",
                "gratificacao_fixa": "Grat. Fixa",
            }

            html = ('<div style="background:#fff;padding:14px;border-radius:10px;'
                    'border:1px solid #E5E7EB;">'
                    '<div style="color:#6D28D9;font-weight:700;margin-bottom:10px;'
                    'border-bottom:2px solid #F3F4F6;padding-bottom:7px;">💰 BASE DE CÁLCULO</div>')

            html += item_extrato("Salário Bruto", sal_bruto, negrito=True)
            html += '<div style="font-size:.72rem;color:#9ca3af;padding:4px 0;">(+) VENCIMENTOS</div>'
            if vf and prov_campos_cfg:
                for campo in prov_campos_cfg:
                    v = _abs_val(vf.get(campo, 0))
                    lb = _CAMPO_LABEL.get(campo, campo.replace("_"," ").title())
                    if v > 0: html += item_extrato(lb, v)
            elif vf:
                for k, lb in [("adicional_tempo_servico","Adic. Tempo"),
                               ("gratificacao","Gratificação"),
                               ("hora_ativ_extra_classe","H.A. Extra Classe"),
                               ("sexta_parte","Sexta Parte"),
                               ("insalubridade","Insalubridade")]:
                    v = _abs_val(vf.get(k, 0))
                    if v > 0: html += item_extrato(lb, v)

            html += '<div style="font-size:.72rem;color:#9ca3af;padding:4px 0;">(-) DESCONTOS</div>'

            # Resolve fontes de desconto pelo config da prefeitura
            desc_campos_cfg = cfg_pref.get("descontos_campos", [])
            desc_kw_cfg     = cfg_pref.get("descontos_kw", [])
            _do_vals        = (dados or {}).get("descontos_obrigatorios", {}) if dados else {}
            _desc_raw       = (dados or {}).get("descontos_raw", []) if dados else []
            _CAMPO_DESC_LBL = {
                "inss": "INSS", "irrf": "IRRF", "previdencia": "Previdência",
            }
            
            # 1) Campos nomeados (inss / irrf / previdencia)
            shown_desc = False
            for campo in desc_campos_cfg:
                v  = _abs_val(_do_vals.get(campo, 0))
                lb = _CAMPO_DESC_LBL.get(campo, campo.replace("_", " ").title())
                if v > 0:
                    html += item_extrato(lb, v, "red")
                    shown_desc = True
            
            # 2) Matches por keyword no descontos_raw (plano de saúde, pensão, etc.)
            if desc_kw_cfg and _desc_raw:
                for _item in _desc_raw:
                    _dsc = _item.get("descricao", "")
                    _v   = _abs_val(_item.get("valor", 0))
                    if _v > 0 and _kw_match(_dsc, desc_kw_cfg):
                        html += item_extrato(str(_dsc)[:28], _v, "red")
                        shown_desc = True
            
            # Fallback: se nada foi exibido mas há dedução, mostra o total
            if not shown_desc and deducs > 0:
                html += item_extrato("Total Descontos", deducs, "red")
            
            html += item_extrato("BASE CÁLCULO", base, "blue", True, False)
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)

        with col2:
            emprestimos_lista = (dados or {}).get("emprestimos", []) if dados else []
            html = ('<div style="background:#fff;padding:14px;border-radius:10px;'
                    'border:1px solid #E5E7EB;">'
                    '<div style="color:#6D28D9;font-weight:700;margin-bottom:10px;'
                    'border-bottom:2px solid #F3F4F6;padding-bottom:7px;">💵 EMPRÉSTIMOS</div>')
            html += item_extrato("Permitido", emp["margem_total"], "blue", negrito=True)
            html += item_extrato("Comprometido", emp["comprometido"], "orange" if emp["comprometido"]>0 else "default")
            if emprestimos_lista:
                html += '<div style="font-size:.72rem;color:#9ca3af;padding:4px 0 2px;">CONTRATOS</div>'
                for e in emprestimos_lista:
                    desc = str(e.get("descricao",""))[:22]
                    html += item_extrato(desc, _abs_val(e.get("valor",0)), "red")
            bg  = "#ECFDF5" if emp["disponivel"] >= 0 else "#FEF2F2"
            cor = "green" if emp["disponivel"] >= 0 else "red"
            html += (f'<div style="margin-top:10px;background:{bg};padding:8px;border-radius:6px;">'
                     + item_extrato("DISPONÍVEL", emp["disponivel"], cor, True, False) + '</div>')
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)

        with col3:
            cartoes_lista = (dados or {}).get("cartoes", []) if dados else []
            html = ('<div style="background:#fff;padding:14px;border-radius:10px;'
                    'border:1px solid #E5E7EB;">'
                    '<div style="color:#6D28D9;font-weight:700;margin-bottom:10px;'
                    'border-bottom:2px solid #F3F4F6;padding-bottom:7px;">💳 CARTÕES</div>')
            html += item_extrato("Permitido", cc["margem_total"], "blue", negrito=True)
            html += item_extrato("Comprometido", cc["comprometido"], "orange" if cc["comprometido"]>0 else "default")
            if any([margem.get("cartoes_nossos",0), margem.get("cartoes_concorrentes",0),
                    margem.get("cartoes_nao_comp",0), margem.get("cartoes_desconhec",0)]):
                html += '<div style="font-size:.72rem;color:#9ca3af;padding:4px 0 2px;">DETALHAMENTO</div>'
                if margem.get("cartoes_nossos",0)>0:
                    html += item_extrato("Nossos",         margem["cartoes_nossos"])
                if margem.get("cartoes_concorrentes",0)>0:
                    html += item_extrato("Terceiros",      margem["cartoes_concorrentes"])
                if margem.get("cartoes_nao_comp",0)>0:
                    html += item_extrato("Não Comprados",  margem["cartoes_nao_comp"])
                if margem.get("cartoes_desconhec",0)>0:
                    html += item_extrato("Desconhecidos",  margem["cartoes_desconhec"])
            bg  = "#ECFDF5" if cc["disponivel"] >= 0 else "#FEF2F2"
            cor = "green" if cc["disponivel"] >= 0 else "red"
            html += (f'<div style="margin-top:10px;background:{bg};padding:8px;border-radius:6px;">'
                     + item_extrato("DISPONÍVEL", cc["disponivel"], cor, True, False) + '</div>')
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)


# ============================================================================
# PAINEL STELLA (v2 — com seção combo_recomendado)
# ============================================================================

def _parse_plano(plano_raw) -> list:
    if isinstance(plano_raw, list):
        return [str(s).strip(" '\"") for s in plano_raw if str(s).strip()]
    if not plano_raw:
        return []
    texto = str(plano_raw).strip()
    if texto.startswith("[") and texto.endswith("]"):
        try:
            import json
            parsed = json.loads(texto)
            if isinstance(parsed, list):
                return [str(s).strip() for s in parsed if str(s).strip()]
        except Exception:
            pass
        inner = texto[1:-1]
        parts = _re.split(r"',\s*'|',\s*\"|\"',\s*'|\",\s*\"", inner)
        return [p.strip(" '\"") for p in parts if p.strip(" '\"")]
    if _re.search(r"^\s*[-\d•*]", texto, _re.MULTILINE):
        linhas = texto.splitlines()
        return [_re.sub(r"^[\s\-\d•*.]+", "", l).strip() for l in linhas if l.strip()]
    return [texto]


def _section(label: str, content: str) -> str:
    return f"<div><div class='stella-section-label'>{label}</div>{content}</div>"


def render_stella_panel(dados: dict, estr: dict):
    if not estr:
        return

    prods   = estr.get("produtos_recomendados", [])
    alertas = estr.get("alertas", [])
    passos  = _parse_plano(estr.get("plano_de_acao", ""))
    combo   = estr.get("combo_recomendado", "")
    perfil  = estr.get("resumo_cliente", "")
    script  = estr.get("script_abertura", "")
    dica_itens = _parse_plano(estr.get("dica_fechamento", ""))

    prod_items = "".join(
        f"<div class='stella-product-card'>"
        f"<div class='stella-product-num'>{i}</div>"
        f"<div><p class='stella-product-name'>{p.get('produto','')}</p>"
        f"<p class='stella-product-motivo'>{p.get('motivo','')}</p></div>"
        f"</div>"
        for i, p in enumerate(prods, 1)
    )
    produtos_html = f"<div class='stella-products'>{prod_items}</div>"

    step_items = "".join(
        f"<div class='stella-step'><div class='stella-step-num'>{i}</div><span>{p}</span></div>"
        for i, p in enumerate(passos, 1)
    ) or "<div class='stella-step'><span style='color:#6b7280;'>—</span></div>"
    steps_html = f"<div class='stella-steps'>{step_items}</div>"

    combo_section = ""
    if combo and str(combo).strip():
        combo_section = _section(
            "🔥 Combo recomendado",
            f"<div class='stella-combo-box'>⚡ {combo}</div>"
        )

    regime   = dados.get("regime", "N/A")
    liquido  = dados.get("liquido", 0)
    sal_base = dados.get("salario_base", 0)
    nome_pref = dados.get("prefeitura", "N/A")

    perfil_html = f"<p class='stella-text' style='margin-bottom:.75rem;'>{perfil}</p>"

    tags = [
        ("🏛️", "Regime", regime),
        ("💰", "Líquido", fmt(liquido)),
        ("📌", "Salário Base", fmt(sal_base)),
        ("🏢", "Órgão", nome_pref[:30] if nome_pref else "N/A"),
    ]
    tags_html = "<div class='stella-profile-grid'>" + "".join(
        f"<div class='stella-profile-tag'>"
        f"<span class='stella-profile-icon'>{ic}</span>"
        f"<div><p class='stella-profile-label'>{lb}</p>"
        f"<p class='stella-profile-value'>{vl}</p></div>"
        f"</div>"
        for ic, lb, vl in tags
    ) + "</div>"

    perfil_section = _section(
        "👤 Raio-X do cliente",
        perfil_html + tags_html
    )

    script_section = ""
    if script and str(script).strip():
        script_js = (script
                     .replace("\\", "\\\\")
                     .replace("`", "\\`")
                     .replace("$", "\\$"))
        script_display = script.replace("\n", "<br>").replace("  ", "&nbsp;&nbsp;")
        copy_id = "stella-copy-btn"
        ta_id   = "stella-copy-ta"
        script_section = _section(
            "📱 Mensagem de abertura — WhatsApp",
            f"""<div class='stella-script-wrap'>
  <div class='stella-script-label'>
    <span>✅ Pronto para copiar e colar</span>
  </div>
  <textarea id='{ta_id}' style='position:absolute;left:-9999px;top:-9999px;opacity:0;width:1px;height:1px;'>{script}</textarea>
  <div class='stella-script-body'>{script_display}</div>
</div>"""
        )

    alerta_section = ""
    if alertas:
        alerta_items = "".join(
            f"<div class='stella-alert'><span>⚠</span><span>{a}</span></div>"
            for a in alertas
        )
        alerta_section = _section("⚠ Pontos de atenção",
                                   f"<div class='stella-alerts'>{alerta_items}</div>")

    dica_section = ""
    if dica_itens:
        items_html = "".join(
            f"<div class='stella-closing-item'>"
            f"<div class='stella-closing-num'>{i}</div>"
            f"<p class='stella-closing-text'>{item}</p>"
            f"</div>"
            for i, item in enumerate(dica_itens, 1)
        )
        dica_section = _section(
            "💡 Diferenciais para fechamento",
            f"<div class='stella-closing-grid'>{items_html}</div>"
        )

    html = (
        "<div class='stella-wrap'>"
          "<div class='stella-header'>"
            "<div class='stella-avatar'>✨</div>"
            "<div>"
              "<div class='stella-name'>Stella</div>"
              "<div class='stella-sub'>Assistente de Estratégia — Grupo Star</div>"
            "</div>"
            "<div class='stella-badge'>Análise Stella</div>"
          "</div>"
          "<div class='stella-body'>"
        + perfil_section
        + _section("🎯 Oportunidade principal",
                   f"<div class='stella-highlight-box'>{estr.get('oportunidade_principal','')}</div>")
        + combo_section
        + _section("📦 Produtos recomendados", produtos_html)
        + _section("🗺 Plano de ação",         steps_html)
        + script_section
        + alerta_section
        + dica_section
        + "</div></div>"
    )

    st.markdown("<div class='section-title'>✨ Stella — Estratégia de Vendas</div>",
                unsafe_allow_html=True)
    st.markdown(html, unsafe_allow_html=True)


# ============================================================================
# CHAT STELLA
# ============================================================================
def render_chat_stella(modo_lote=False, lote_resultados=None):
    import streamlit as st
    import streamlit.components.v1 as components
    import json as _json

    if modo_lote:
        if not lote_resultados:
            return
        dados = {}
    else:
        dados = st.session_state.get("resultado_individual", {})
        if not dados or "erro" in dados:
            return

    hist_key  = "chat_history_lote" if modo_lote else "chat_history"
    form_key  = "stella_chat_form_lote" if modo_lote else "stella_chat_form"
    input_key = "stella_hidden_input_lote" if modo_lote else "stella_hidden_input"

    if hist_key not in st.session_state:
        st.session_state[hist_key] = []

    with st.form(form_key, clear_on_submit=True):
        msg_hidden = st.text_input(
            "stella_hidden",
            key=input_key,
            label_visibility="collapsed"
        )
        submitted = st.form_submit_button("ok")

    if submitted and msg_hidden.strip():
        with st.spinner(""):
            if modo_lote:
                resp = stella_chat_lote(
                    msg_hidden,
                    lote_resultados,
                    st.session_state[hist_key]
                )
            else:
                margem_ss = st.session_state.get("margem_calculada", {})
                resp = stella_chat(
                    msg_hidden,
                    dados,
                    st.session_state[hist_key],
                    margem_ss
                )
        st.session_state[hist_key].append({"role": "user",      "content": msg_hidden})
        st.session_state[hist_key].append({"role": "assistant", "content": resp})
        st.rerun()
 
    st.markdown("""
    <style>
    div[data-testid="stForm"] {
        position:fixed !important; top:-9999px !important;
        left:-9999px !important; width:1px !important;
        height:1px !important; overflow:hidden !important; opacity:0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    msgs_json = _json.dumps(st.session_state[hist_key], ensure_ascii=False)
    has_msgs  = "true" if st.session_state[hist_key] else "false"

    placeholder_txt = "Pergunte sobre o lote..." if modo_lote else "Pergunte sobre este cliente..."

    _questions_individual = """[
        { cat:"🎯 Abordagem inicial", items:[
        "Como devo abordar este cliente pela primeira vez?",
        "Qual é o melhor script de abertura para este perfil?",
        "Como criar rapport rápido com este servidor?",
        ]},
        { cat:"💰 Produto e margem", items:[
        "Qual produto tem mais chance de fechar com este cliente?",
        "Tem margem disponível para empréstimo?",
        "Vale a pena oferecer Compra de Dívida aqui?",
        "Qual o valor máximo de parcela que posso oferecer?",
        "Devo priorizar Cartão Consignado ou Cartão Benefício?",
        ]},
        { cat:"🛡️ Objeções e contornos", items:[
        "Quais objeções este cliente provavelmente vai ter?",
        "Como contornar 'não preciso de crédito agora'?",
        "Como responder se ele disser que já tem muitos descontos?",
        "O que dizer se ele quiser pensar antes de decidir?",
        ]},
        { cat:"🔄 Refinanciamento e upgrade", items:[
        "Este cliente tem potencial para refinanciamento?",
        "Como apresentar o refinanciamento sem parecer que aumento a dívida?",
        "Posso oferecer um produto adicional além do que já tem?",
        ]},
        { cat:"📊 Análise estratégica", items:[
        "Como interpretar a situação financeira geral deste servidor?",
        "Este cliente é elegível para todos os nossos produtos?",
        "O que os cartões concorrentes nos dizem sobre o perfil dele?",
        ]},
        { cat:"✅ Fechamento", items:[
        "Qual a melhor dica de fechamento para este perfil?",
        "Como criar urgência sem pressionar o cliente?",
        "Qual benefício devo destacar para fechar mais rápido?",
        ]},
    ]"""

    _questions_lote = """[
        { cat:"📈 Visão executiva", items:[
        "Qual é o diagnóstico geral deste lote em 3 pontos?",
        "Onde está nossa maior oportunidade de receita neste grupo?",
        "Qual a nossa posição competitiva real nesta base?",
        "Qual o potencial máximo de receita mensal se convertermos bem este lote?",
        ]},
        { cat:"🎯 Priorização e alocação", items:[
        "Quais servidores devemos acionar primeiro e por quê?",
        "Como dividir o esforço da equipe entre concorrentes e mercado novo?",
        "Quais prefeituras têm melhor ROI para campanha agora?",
        "Tem algum segmento que não vale o esforço comercial?",
        ]},
        { cat:"⚔️ Inteligência competitiva", items:[
        "Qual concorrente está nos tomando mais mercado neste lote?",
        "Quanto estamos perdendo por mês para a concorrência?",
        "Temos vantagem de ticket ou os concorrentes estão melhor posicionados?",
        "O mercado está concentrado ou pulverizado entre concorrentes?",
        ]},
        { cat:"⚠️ Riscos e alertas", items:[
        "Quais são os principais riscos que a liderança precisa saber?",
        "Tem algum sinal de perda de base que devemos monitorar?",
        "Existem prefeituras com margem quase esgotada no grupo?",
        ]},
        { cat:"🚀 Decisões de campanha", items:[
        "Faz sentido montar uma campanha específica para este lote?",
        "Qual produto deve ser o carro-chefe desta campanha?",
        "Como medir o sucesso desta operação ao longo do tempo?",
        "Qual meta de conversão seria realista para este grupo?",
        ]},
        { cat:"📊 Análise de dados", items:[
        "O perfil salarial desta base é favorável para crédito consignado?",
        "Qual o ticket médio esperado se ativarmos a margem disponível?",
        "Como o mix de regimes impacta o portfólio que podemos oferecer?",
        ]},
    ]"""
 
    fab_html = f"""<!DOCTYPE html><html><body><script>
(function() {{
  var par  = window.parent;
  var pdoc = par.document;
  var HISTORY  = {msgs_json};
  var HAS_MSGS = {has_msgs};
 
  var old = pdoc.getElementById('sfab-root');
  if (old) old.remove();
  var oldSt = pdoc.getElementById('sfab-style');
  if (oldSt) oldSt.remove();
 
  var style = pdoc.createElement('style');
  style.id = 'sfab-style';
  style.textContent = `
    #sfab-btn {{
      position:fixed; bottom:28px; right:28px; z-index:999999;
      width:54px; height:54px; border-radius:50%;
      background:linear-gradient(135deg,#7C3AED,#4C1D95);
      border:none; cursor:pointer;
      box-shadow:0 4px 20px rgba(124,58,237,.4);
      font-size:1.35rem; color:white;
      display:flex; align-items:center; justify-content:center;
      transition:transform .2s, box-shadow .2s;
    }}
    #sfab-btn:hover {{ transform:scale(1.08); box-shadow:0 6px 28px rgba(124,58,237,.55); }}
    #sfab-dot {{
      position:absolute; top:2px; right:2px;
      width:12px; height:12px; border-radius:50%;
      background:#10B981; border:2px solid white;
    }}
    #sfab-panel {{
      position:fixed; bottom:94px; right:28px; z-index:999998;
      width:375px; max-height:560px;
      background:#FFFFFF;
      border-radius:1rem;
      border:1px solid #E5E7EB;
      box-shadow:0 8px 40px rgba(0,0,0,.13);
      display:none; flex-direction:column; overflow:hidden;
      font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
    }}
    #sfab-panel.open {{ display:flex; animation:sfabIn .18s ease; }}
    @keyframes sfabIn {{ from{{opacity:0;transform:translateY(10px)}} to{{opacity:1;transform:translateY(0)}} }}
    .sfab-hdr {{
      display:flex; align-items:center; gap:.75rem;
      padding:.875rem 1.1rem;
      background:linear-gradient(135deg,#7C3AED 0%,#4C1D95 100%);
      flex-shrink:0;
    }}
    .sfab-av {{
      width:34px; height:34px; border-radius:50%;
      background:rgba(255,255,255,.2);
      border:1.5px solid rgba(255,255,255,.35);
      display:flex; align-items:center; justify-content:center;
      font-size:.9rem; flex-shrink:0;
    }}
    .sfab-hdr-name {{ color:#fff; font-weight:700; font-size:.88rem; }}
    .sfab-hdr-sub  {{ color:rgba(255,255,255,.65); font-size:.7rem; margin-top:.08rem; }}
    .sfab-close {{
      margin-left:auto; background:rgba(255,255,255,.15);
      border:1px solid rgba(255,255,255,.25);
      color:#fff; font-size:.8rem; cursor:pointer;
      width:26px; height:26px; border-radius:50%;
      display:flex; align-items:center; justify-content:center;
      transition:background .15s; line-height:1;
    }}
    .sfab-close:hover {{ background:rgba(255,255,255,.28); }}
    #sfab-msgs {{
      flex:1; overflow-y:auto; padding:.875rem 1rem;
      display:flex; flex-direction:column; gap:.5rem;
      background:#F9FAFB;
      min-height:100px;
    }}
    #sfab-msgs::-webkit-scrollbar {{ width:3px; }}
    #sfab-msgs::-webkit-scrollbar-thumb {{ background:#DDD6FE; border-radius:2px; }}
    .sfab-empty {{
      text-align:center; padding:1.75rem .75rem;
      color:#9CA3AF; font-size:.82rem; line-height:1.65;
    }}
    .sfab-empty strong {{ color:#7C3AED; font-weight:600; }}
    .sfab-msg-u {{
      align-self:flex-end;
      background:#7C3AED;
      color:#fff;
      border-radius:.875rem .875rem 0 .875rem;
      padding:.5rem .875rem; font-size:.81rem;
      max-width:82%; line-height:1.55; word-break:break-word;
      box-shadow:0 1px 4px rgba(124,58,237,.25);
    }}
    .sfab-msg-s {{
      align-self:flex-start;
      background:#FFFFFF;
      border:1px solid #E5E7EB;
      color:#374151;
      border-radius:.875rem .875rem .875rem 0;
      padding:.6rem 1rem; font-size:.81rem;
      max-width:88%; line-height:1.65; word-break:break-word;
      box-shadow:0 1px 3px rgba(0,0,0,.05);
    }}
    .sfab-msg-s strong {{ color:#4C1D95; font-weight:700; }}
    .sfab-msg-s em     {{ color:#6D28D9; font-style:italic; }}
    .sfab-msg-s code {{
      background:#EDE9FE; color:#5B21B6;
      padding:.1rem .35rem; border-radius:.25rem;
      font-size:.78rem; font-family:monospace;
    }}
    .sfab-msg-s ul, .sfab-msg-s ol {{
      margin:.35rem 0 .35rem 1.1rem; padding:0;
    }}
    .sfab-msg-s li  {{ margin:.18rem 0; line-height:1.55; }}
    .sfab-msg-s .sfab-p {{ margin:.4rem 0; }}
    .sfab-msg-s .sfab-p:first-child {{ margin-top:0; }}
    .sfab-msg-s .sfab-p:last-child  {{ margin-bottom:0; }}
    .sfab-msg-s .sfab-h {{
      color:#4C1D95; font-weight:700; font-size:.85rem;
      margin:.5rem 0 .2rem; display:block;
    }}
    .sfab-msg-s hr {{
      border:none; border-top:1px solid #EDE9FE; margin:.5rem 0;
    }}
    .sfab-loading {{
      align-self:flex-start;
      background:#F3F4F6; border:1px solid #E5E7EB;
      color:#9CA3AF;
      border-radius:.875rem .875rem .875rem 0;
      padding:.5rem .875rem; font-size:.81rem;
      animation:sfabPulse 1.2s ease-in-out infinite;
    }}
    @keyframes sfabPulse {{ 0%,100%{{opacity:.4}} 50%{{opacity:1}} }}
    #sfab-qs-wrap {{
      flex-shrink:0;
      border-top:1px solid #F3F4F6;
      background:#FFFFFF;
    }}
    #sfab-qs-toggle {{
      width:100%; background:none; border:none; cursor:pointer;
      display:flex; align-items:center; justify-content:space-between;
      padding:.5rem 1rem;
      color:#7C3AED; font-size:.7rem; font-weight:700;
      letter-spacing:.07em; text-transform:uppercase;
      transition:background .15s; font-family:inherit;
    }}
    #sfab-qs-toggle:hover {{ background:#F5F3FF; }}
    #sfab-qs-arrow {{ font-size:.6rem; transition:transform .2s; display:inline-block; }}
    #sfab-qs-arrow.open {{ transform:rotate(180deg); }}
    #sfab-qs-list {{
      display:none; flex-direction:column;
      max-height:190px; overflow-y:auto;
      background:#FAFAFA;
      border-top:1px solid #F3F4F6;
    }}
    #sfab-qs-list.open {{ display:flex; }}
    #sfab-qs-list::-webkit-scrollbar {{ width:3px; }}
    #sfab-qs-list::-webkit-scrollbar-thumb {{ background:#DDD6FE; border-radius:2px; }}
    .sfab-qs-cat {{
      font-size:.62rem; font-weight:700; letter-spacing:.08em;
      text-transform:uppercase; color:#9CA3AF;
      padding:.5rem 1rem .2rem;
    }}
    .sfab-q {{
      display:flex; align-items:flex-start; gap:.5rem;
      padding:.38rem 1rem;
      cursor:pointer; border:none; background:none;
      width:100%; text-align:left; transition:background .12s;
    }}
    .sfab-q:hover {{ background:#EDE9FE; }}
    .sfab-q-icon {{ color:#7C3AED; font-size:.7rem; flex-shrink:0; margin-top:.1rem; }}
    .sfab-q-text {{ font-size:.78rem; color:#374151; line-height:1.45; font-family:inherit; }}
    .sfab-q:hover .sfab-q-text {{ color:#4C1D95; }}
    .sfab-footer {{
      display:flex; gap:.5rem; align-items:center;
      padding:.65rem 1rem;
      border-top:1px solid #E5E7EB;
      background:#FFFFFF;
      flex-shrink:0;
    }}
    #sfab-input {{
      flex:1;
      background:#F9FAFB;
      border:1px solid #E5E7EB;
      border-radius:.5rem;
      color:#111827; font-size:.82rem; font-family:inherit;
      padding:.45rem .75rem; outline:none;
      transition:border-color .15s, box-shadow .15s;
    }}
    #sfab-input::placeholder {{ color:#9CA3AF; }}
    #sfab-input:focus {{
      border-color:#7C3AED;
      box-shadow:0 0 0 3px rgba(124,58,237,.1);
      background:#fff;
    }}
    #sfab-send {{
      width:34px; height:34px; border-radius:50%; flex-shrink:0;
      background:linear-gradient(135deg,#7C3AED,#4C1D95);
      border:none; color:white; font-size:.8rem; cursor:pointer;
      display:flex; align-items:center; justify-content:center;
      transition:transform .15s, box-shadow .15s;
      box-shadow:0 2px 8px rgba(124,58,237,.3);
    }}
    #sfab-send:hover {{ transform:scale(1.1); box-shadow:0 3px 12px rgba(124,58,237,.45); }}
    #sfab-send:disabled {{ opacity:.4; cursor:not-allowed; transform:none; box-shadow:none; }}
  `;
  pdoc.head.appendChild(style);
 
  var QUESTIONS = {_questions_lote if modo_lote else _questions_individual};
 
  var root = pdoc.createElement('div');
  root.id  = 'sfab-root';
 
  var fabBtn = pdoc.createElement('button');
  fabBtn.id = 'sfab-btn'; fabBtn.title = 'Chat com a Stella';
  fabBtn.innerHTML = '✨' + (HAS_MSGS ? '<div id="sfab-dot"></div>' : '');
 
  var panel = pdoc.createElement('div');
  panel.id = 'sfab-panel';
 
  var hdr = pdoc.createElement('div');
  hdr.className = 'sfab-hdr';
  hdr.innerHTML = `
    <div class="sfab-av">✨</div>
    <div>
      <div class="sfab-hdr-name">Stella</div>
      <div class="sfab-hdr-sub">Assistente de Estratégia • Online</div>
    </div>
    <button class="sfab-close" id="sfab-close-btn">✕</button>
  `;
 
  var msgsEl = pdoc.createElement('div');
  msgsEl.id = 'sfab-msgs';
 
  var qsWrap = pdoc.createElement('div');
  qsWrap.id = 'sfab-qs-wrap';
  qsWrap.innerHTML = `
    <button id="sfab-qs-toggle">
      <span>💡 Perguntas estratégicas</span>
      <span id="sfab-qs-arrow">▼</span>
    </button>
    <div id="sfab-qs-list"></div>
  `;
 
  var footer = pdoc.createElement('div');
  footer.className = 'sfab-footer';
  footer.innerHTML = `
    <input id="sfab-input" type="text"
           placeholder="{placeholder_txt}" maxlength="500" />
    <button id="sfab-send" title="Enviar">➤</button>
  `;
 
  panel.appendChild(hdr);
  panel.appendChild(msgsEl);
  panel.appendChild(qsWrap);
  panel.appendChild(footer);
  root.appendChild(fabBtn);
  root.appendChild(panel);
  pdoc.body.appendChild(root);

  // ── MARKDOWN RENDERER ──────────────────────────────────────────────────────
  function mdToHtml(text) {{
    if (!text) return '';
    var lines = text.split('\\n');
    var html  = '';
    var inUl  = false, inOl = false;

    function closeList() {{
      if (inUl) {{ html += '</ul>'; inUl = false; }}
      if (inOl) {{ html += '</ol>'; inOl = false; }}
    }}

    function inlineFormat(s) {{
      s = s.replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>');
      s = s.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      s = s.replace(/\*(.*?)\*/g, '<em>$1</em>');
      s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
      s = s.replace(/ — /g, ' <span style="color:#9CA3AF;font-weight:400"> — </span> ');
      s = s.replace(/Por que:/g, '<strong style="color:#7C3AED">Por que:<\/strong>');
      return s;
    }}

    for (var i = 0; i < lines.length; i++) {{
      var line    = lines[i];
      var trimmed = line.trim();

      if (!trimmed) {{ closeList(); continue; }}

      if (/^---+$/.test(trimmed)) {{
        closeList(); html += '<hr>'; continue;
      }}

      var hMatch = trimmed.match(/^(#{{1,3}})\s+(.+)$/);
      if (hMatch) {{
        closeList();
        html += '<span class="sfab-h">' + inlineFormat(hMatch[2]) + '</span>';
        continue;
      }}

      var ulMatch = trimmed.match(/^[-*•]\s+(.+)$/);
      if (ulMatch) {{
        if (inOl) {{ html += '</ol>'; inOl = false; }}
        if (!inUl) {{ html += '<ul>'; inUl = true; }}
        html += '<li>' + inlineFormat(ulMatch[1]) + '</li>';
        continue;
      }}

      var olMatch = trimmed.match(/^\d+\.\s+(.+)$/);
      if (olMatch) {{
        if (inUl) {{ html += '</ul>'; inUl = false; }}
        if (!inOl) {{ html += '<ol>'; inOl = true; }}
        html += '<li>' + inlineFormat(olMatch[1]) + '</li>';
        continue;
      }}

      closeList();
      html += '<div class="sfab-p">' + inlineFormat(trimmed) + '</div>';
    }}

    closeList();
    return html;
  }}
  // ── FIM MARKDOWN RENDERER ──────────────────────────────────────────────────

  function renderMsgs() {{
    msgsEl.innerHTML = '';
    if (!HISTORY || HISTORY.length === 0) {{
      msgsEl.innerHTML = "<div class='sfab-empty'><strong>✨ Olá! Sou a Stella.</strong><br>Pergunte sobre este cliente ou escolha uma pergunta abaixo.</div>";
    }} else {{
      HISTORY.forEach(function(m) {{
        var d = pdoc.createElement('div');
        d.className = m.role === 'user' ? 'sfab-msg-u' : 'sfab-msg-s';
        if (m.role === 'assistant') {{
          d.innerHTML = mdToHtml(m.content);
        }} else {{
          d.textContent = m.content;
        }}
        msgsEl.appendChild(d);
      }});
      msgsEl.scrollTop = msgsEl.scrollHeight;
    }}
  }}
  renderMsgs();
 
  var qsList = pdoc.getElementById('sfab-qs-list');
  QUESTIONS.forEach(function(group) {{
    var cat = pdoc.createElement('div');
    cat.className = 'sfab-qs-cat';
    cat.textContent = group.cat;
    qsList.appendChild(cat);
    group.items.forEach(function(q) {{
      var b = pdoc.createElement('button');
      b.className = 'sfab-q';
      b.innerHTML = '<span class="sfab-q-icon">›</span><span class="sfab-q-text">' + q + '</span>';
      b.addEventListener('click', function() {{
        pdoc.getElementById('sfab-input').value = q;
        qsList.classList.remove('open');
        pdoc.getElementById('sfab-qs-arrow').classList.remove('open');
        par.sessionStorage.setItem('sfabQdOpen','0');
        sfabSend();
      }});
      qsList.appendChild(b);
    }});
  }});
 
  pdoc.getElementById('sfab-qs-toggle').addEventListener('click', function() {{
    qsList.classList.toggle('open');
    pdoc.getElementById('sfab-qs-arrow').classList.toggle('open');
    par.sessionStorage.setItem('sfabQdOpen', qsList.classList.contains('open') ? '1' : '0');
  }});
 
  function sfabToggle() {{
    var opening = !panel.classList.contains('open');
    panel.classList.toggle('open', opening);
    par.sessionStorage.setItem('sfabOpen', opening ? '1' : '0');
    if (opening) {{
      msgsEl.scrollTop = msgsEl.scrollHeight;
      setTimeout(function() {{ pdoc.getElementById('sfab-input').focus(); }}, 60);
    }}
  }}
  fabBtn.addEventListener('click', sfabToggle);
  pdoc.getElementById('sfab-close-btn').addEventListener('click', sfabToggle);
 
  function sfabSend() {{
    var inp = pdoc.getElementById('sfab-input');
    var val = (inp.value || '').trim();
    if (!val) return;
 
    var empty = msgsEl.querySelector('.sfab-empty');
    if (empty) empty.remove();
 
    var ub = pdoc.createElement('div');
    ub.className = 'sfab-msg-u'; ub.textContent = val;
    msgsEl.appendChild(ub);
 
    var lb = pdoc.createElement('div');
    lb.className = 'sfab-loading'; lb.textContent = 'Stella está pensando...';
    msgsEl.appendChild(lb);
    msgsEl.scrollTop = msgsEl.scrollHeight;
 
    inp.value = '';
    pdoc.getElementById('sfab-send').disabled = true;
 
    function tryBridge(n) {{
      var stBtn = pdoc.querySelector('[data-testid="stFormSubmitButton"] button');
      var stInp = null;
      if (stBtn) {{
        var formEl = stBtn.closest('[data-testid="stForm"]');
        if (formEl) stInp = formEl.querySelector('input[type="text"]');
      }}
      if (stInp && stBtn) {{
        var setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
        setter.call(stInp, val);
        stInp.dispatchEvent(new Event('input',  {{bubbles:true}}));
        stInp.dispatchEvent(new Event('change', {{bubbles:true}}));
        setTimeout(function() {{ stBtn.click(); }}, 120);
      }} else if (n > 0) {{
        setTimeout(function() {{ tryBridge(n-1); }}, 250);
      }}
    }}
    tryBridge(10);
  }}
 
  pdoc.getElementById('sfab-send').addEventListener('click', sfabSend);
  pdoc.getElementById('sfab-input').addEventListener('keydown', function(e) {{
    if (e.key === 'Enter') sfabSend();
  }});
 
  if (par.sessionStorage.getItem('sfabOpen') === '1') {{
    panel.classList.add('open');
    msgsEl.scrollTop = msgsEl.scrollHeight;
  }}
  if (par.sessionStorage.getItem('sfabQdOpen') === '1') {{
    qsList.classList.add('open');
    pdoc.getElementById('sfab-qs-arrow').classList.add('open');
  }}
 
}})();
</script></body></html>"""
 
    components.html(fab_html, height=0, scrolling=False)


# ============================================================================
# RENDERIZA RESULTADO PRINCIPAL
# ============================================================================
def render_resultado(dados: Dict):
    if "erro" in dados:
        st.error(f"❌ {dados['erro']}"); return

    prefeitura  = dados.get("prefeitura","Não identificada")
    nome        = dados.get("nome","N/A")
    matricula   = dados.get("matricula","N/A")
    regime      = dados.get("regime","NÃO IDENTIFICADO")
    liquido     = dados.get("liquido",0.0)
    venc_total  = dados.get("vencimentos_total",0.0)
    desc_total  = dados.get("descontos_total",0.0)
    sal_base    = dados.get("salario_base",0.0)
    cartoes     = dados.get("cartoes",[])
    emprestimos = dados.get("emprestimos",[])
    desc_obrig  = dados.get("descontos_obrigatorios",{})
    venc_fixos  = dados.get("vencimentos_fixos",{})

    st.markdown(f"<div class='badge-pref'>🏛️ {prefeitura}</div>", unsafe_allow_html=True)
    st.success("✅ Holerite analisado com sucesso pela Stella!")

    st.markdown("<h3 class='section-header'>Informações do Servidor</h3>", unsafe_allow_html=True)
    nome_curto = nome.split()[0][:14] if nome and nome!="N/A" else "N/A"
    c1,c2,c3,c4,c5 = st.columns(5, gap="medium")
    with c1: st.metric("👤 Nome",          nome_curto)
    with c2: st.metric("🏛️ Regime",        regime[:13]+"..." if len(regime)>13 else regime)
    with c3: st.metric("🆔 Matrícula",     matricula)
    with c4: st.metric("💵 Líquido",       fmt(liquido))
    with c5: st.metric("💰 Vencimentos",   fmt(venc_total))

    st.markdown("<h3 class='section-header'>📊 Margem Consignável</h3>", unsafe_allow_html=True)
    margem = calcular_margem_ia(dados)
    st.session_state["margem_calculada"] = margem
    render_margem_cards(margem, dados)

    _do_orig        = dados.get("_descontos_originais", desc_obrig)
    _proventos_raw  = dados.get("proventos_raw", [])
    _descontos_raw  = dados.get("descontos_raw", [])

    with st.expander("📋 Composição Financeira Detalhada", expanded=False):

        def _tabela_row(descricao, ref, valor, negrito=False, header=False, separador=False):
            bg      = "#F0EDFF" if header else "#FFFFFF"
            weight  = "700" if (negrito or header) else "400"
            cor_val = "#1D4ED8" if negrito else ("#374151" if header else "#DC2626")
            bord    = "border-top:2px solid #7C3AED;margin-top:4px;" if separador else ""
            val_str = fmt(valor) if isinstance(valor, (int, float)) and not header else str(valor)
            return (
                f'<div style="display:grid;grid-template-columns:1fr 55px 105px;'
                f'gap:2px;padding:5px 8px;background:{bg};{bord}font-size:.84rem;">'
                f'<span style="color:#374151;font-weight:{weight};">{descricao}</span>'
                f'<span style="color:#9ca3af;text-align:center;font-size:.78rem;">{ref}</span>'
                f'<span style="color:{cor_val};font-weight:{weight};text-align:right;">{val_str}</span>'
                f'</div>'
            )

        def _header_tabela(titulo, icone):
            return (
                f'<div style="background:linear-gradient(135deg,#ede9fe,#ddd6fe);'
                f'padding:9px 12px;border-radius:8px 8px 0 0;'
                f'border-bottom:2px solid #7C3AED;">'
                f'<span style="color:#4c1d95;font-weight:800;font-size:.9rem;">'
                f'{icone} {titulo}</span></div>'
            )

        def _wrap(inner):
            return (
                '<div style="background:#fff;border-radius:8px;'
                'border:1px solid #DDD6FE;overflow:hidden;">'
                + inner + '</div>'
            )

        col1, col2, col3 = st.columns(3, gap="medium")

        with col1:
            rows  = _header_tabela("PROVENTOS", "💰")
            rows += _tabela_row("DESCRIÇÃO", "REF.", "VALOR", header=True)
            if _proventos_raw:
                for item in _proventos_raw:
                    v = _abs_val(item.get("valor", 0))
                    if v > 0:
                        rows += _tabela_row(
                            str(item.get("descricao",""))[:32],
                            str(item.get("referencia",""))[:8],
                            v
                        )
            else:
                if sal_base > 0: rows += _tabela_row("Salário Base", "", sal_base, negrito=True)
                for k, lb in [("adicional_tempo_servico","Adic. Tempo"),
                               ("gratificacao","Gratificação"),
                               ("hora_ativ_extra_classe","Hora Ativ.Extra Classe"),
                               ("aula_suplementar","Aula Suplementar"),
                               ("sexta_parte","Sexta Parte"),
                               ("insalubridade","Insalubridade"),
                               ("horas_extras","Horas Extras")]:
                    v = _abs_val(venc_fixos.get(k, 0))
                    if v > 0: rows += _tabela_row(lb, "", v)
                for it in (venc_fixos.get("outros_fixos") or []):
                    if isinstance(it, dict):
                        v = _abs_val(it.get("valor", 0))
                        if v > 0: rows += _tabela_row(str(it.get("descricao",""))[:32], "", v)
            rows += _tabela_row("TOTAL PROVENTOS", "", venc_total, negrito=True, separador=True)
            st.markdown(_wrap(rows), unsafe_allow_html=True)

        _CONSIG_KW = [
            "cartao","cartão","cred ","cart.","saque","anticipay","starcard","starbank",
            "emprestimo","empréstimo","emprest","financiamento","delta global","bmp",
            "daycoval","panamericano","bmg","meucashcard","credcesta","monetarie",
            "pixcard","uasprev","cef","credifin","brcard","big card",
        ]
        def _eh_consig(desc):
            return any(kw in str(desc).lower() for kw in _CONSIG_KW)

        with col2:
            rows  = _header_tabela("DESCONTOS", "📉")
            rows += _tabela_row("DESCRIÇÃO", "REF.", "VALOR", header=True)
            total_desc_exibido = 0.0
            if _descontos_raw:
                for item in _descontos_raw:
                    v = _abs_val(item.get("valor", 0))
                    if v > 0 and not _eh_consig(item.get("descricao","")):
                        rows += _tabela_row(
                            str(item.get("descricao",""))[:32],
                            str(item.get("referencia",""))[:8],
                            v
                        )
                        total_desc_exibido += v
            else:
                inss_v = _abs_val(_do_orig.get("inss", 0))
                irrf_v = _abs_val(_do_orig.get("irrf", 0))
                prev_v = _abs_val(_do_orig.get("previdencia", 0))
                if inss_v > 0: rows += _tabela_row("INSS",        "", inss_v); total_desc_exibido += inss_v
                if irrf_v > 0: rows += _tabela_row("IRRF",        "", irrf_v); total_desc_exibido += irrf_v
                if prev_v > 0: rows += _tabela_row("Previdência", "", prev_v); total_desc_exibido += prev_v
            rows += _tabela_row("TOTAL DESCONTOS", "", total_desc_exibido, negrito=True, separador=True)
            st.markdown(_wrap(rows), unsafe_allow_html=True)

        def _get_ref(descricao, valor):
            for item in (_descontos_raw or []):
                if (abs(_abs_val(item.get("valor",0)) - valor) < 0.02 and
                        str(item.get("descricao","")).lower()[:12] == str(descricao).lower()[:12]):
                    return str(item.get("referencia",""))[:8]
            return ""

        with col3:
            rows   = _header_tabela("CONSIGNAÇÕES", "💳")
            rows  += _tabela_row("DESCRIÇÃO", "REF.", "VALOR", header=True)
            total_c = 0.0
            for c in cartoes:
                v = _abs_val(c.get("valor", 0))
                rows += _tabela_row(str(c.get("descricao",""))[:32], _get_ref(c.get("descricao",""), v), v)
                total_c += v
            for e in emprestimos:
                v = _abs_val(e.get("valor", 0))
                rows += _tabela_row(str(e.get("descricao",""))[:32], _get_ref(e.get("descricao",""), v), v)
                total_c += v
            if total_c > 0:
                rows += _tabela_row("TOTAL CONSIGNAÇÕES", "", total_c, negrito=True, separador=True)
            else:
                rows += _tabela_row("Nenhuma consignação", "", 0.0)
            st.markdown(_wrap(rows), unsafe_allow_html=True)

    nossos       = [c for c in cartoes if c.get("tipo")=="nosso"]
    concorrentes = [c for c in cartoes if c.get("tipo")=="concorrente"]
    nao_comp     = [c for c in cartoes if c.get("tipo")=="nao_comprado"]
    desconhec    = [c for c in cartoes if c.get("tipo")=="desconhecido"]

    todos_cartoes = nossos + concorrentes + nao_comp + desconhec

    st.markdown("<h3 class='section-header'>Consignações do Cliente</h3>", unsafe_allow_html=True)

    if not todos_cartoes:
        st.info("Nenhum cartão consignado identificado neste holerite.")
    else:
        partes = []
        if nossos:       partes.append(f"**{len(nossos)}** nosso(s)")
        if concorrentes: partes.append(f"**{len(concorrentes)}** concorrente(s)")
        if nao_comp:     partes.append(f"**{len(nao_comp)}** não compramos")
        if desconhec:    partes.append(f"**{len(desconhec)}** a verificar")
        st.info("Cartões encontrados: " + " · ".join(partes))

        i = 1
        for c in nossos:
            st.markdown(opp_card(
                c.get("descricao",""),
                f"Nosso produto ativo | {fmt(c.get('valor',0))} / mês — verificar refinanciamento",
                "#16a34a","#f0fdf4","#dcfce7", i), unsafe_allow_html=True)
            i += 1
        for c in concorrentes:
            st.markdown(opp_card(
                c.get("descricao",""),
                f"Concorrente — oportunidade de Compra de Dívida | {fmt(c.get('valor',0))} / mês",
                "#1565c0","#eff6ff","#dbeafe", i), unsafe_allow_html=True)
            i += 1
        for c in nao_comp:
            st.markdown(opp_card(
                c.get("descricao",""),
                f"Não operamos este cartão | {fmt(c.get('valor',0))} / mês",
                "#be185d","#fdf2f8","#fce7f3", i), unsafe_allow_html=True)
            i += 1
        for c in desconhec:
            st.markdown(opp_card(
                c.get("descricao",""),
                f"Instituição não identificada — verificar | {fmt(c.get('valor',0))} / mês",
                "#b45309","#fffbeb","#fef3c7", i), unsafe_allow_html=True)
            i += 1

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    render_stella_panel(dados, st.session_state.get("stella_estrategia",{}))

    render_chat_stella()



def render_resultado_sem_chat(dados: Dict):
    """render_resultado sem painel Stella e sem chat — usado nos expanders do lote."""
    if "erro" in dados:
        st.error(f"❌ {dados['erro']}"); return

    prefeitura  = dados.get("prefeitura","Não identificada")
    nome        = dados.get("nome","N/A")
    matricula   = dados.get("matricula","N/A")
    regime      = dados.get("regime","NÃO IDENTIFICADO")
    liquido     = dados.get("liquido",0.0)
    venc_total  = dados.get("vencimentos_total",0.0)
    sal_base    = dados.get("salario_base",0.0)
    cartoes     = dados.get("cartoes",[])
    emprestimos = dados.get("emprestimos",[])
    desc_obrig  = dados.get("descontos_obrigatorios",{})
    venc_fixos  = dados.get("vencimentos_fixos",{})

    st.markdown(f"<div class='badge-pref'>🏛️ {prefeitura}</div>", unsafe_allow_html=True)

    nome_curto = nome.split()[0][:14] if nome and nome!="N/A" else "N/A"
    c1,c2,c3,c4,c5 = st.columns(5, gap="medium")
    with c1: st.metric("👤 Nome",        nome_curto)
    with c2: st.metric("🏛️ Regime",      regime[:13]+"..." if len(regime)>13 else regime)
    with c3: st.metric("🆔 Matrícula",   matricula)
    with c4: st.metric("💵 Líquido",     fmt(liquido))
    with c5: st.metric("💰 Vencimentos", fmt(venc_total))

    st.markdown("<h3 class='section-header'>📊 Margem Consignável</h3>", unsafe_allow_html=True)
    margem = calcular_margem_ia(dados)
    render_margem_cards(margem, dados)

    _do_orig       = dados.get("_descontos_originais", desc_obrig)
    _proventos_raw = dados.get("proventos_raw", [])
    _descontos_raw = dados.get("descontos_raw", [])

    with st.expander("📋 Composição Financeira Detalhada", expanded=False):
        def _tabela_row(descricao, ref, valor, negrito=False, header=False, separador=False):
            bg      = "#F0EDFF" if header else "#FFFFFF"
            weight  = "700" if (negrito or header) else "400"
            cor_val = "#1D4ED8" if negrito else ("#374151" if header else "#DC2626")
            bord    = "border-top:2px solid #7C3AED;margin-top:4px;" if separador else ""
            val_str = fmt(valor) if isinstance(valor, (int, float)) and not header else str(valor)
            return (f'<div style="display:grid;grid-template-columns:1fr 55px 105px;'
                    f'gap:2px;padding:5px 8px;background:{bg};{bord}font-size:.84rem;">'
                    f'<span style="color:#374151;font-weight:{weight};">{descricao}</span>'
                    f'<span style="color:#9ca3af;text-align:center;font-size:.78rem;">{ref}</span>'
                    f'<span style="color:{cor_val};font-weight:{weight};text-align:right;">{val_str}</span>'
                    f'</div>')
        def _header_tabela(titulo, icone):
            return (f'<div style="background:linear-gradient(135deg,#ede9fe,#ddd6fe);'
                    f'padding:9px 12px;border-radius:8px 8px 0 0;border-bottom:2px solid #7C3AED;">'
                    f'<span style="color:#4c1d95;font-weight:800;font-size:.9rem;">{icone} {titulo}</span></div>')
        def _wrap(inner):
            return ('<div style="background:#fff;border-radius:8px;border:1px solid #DDD6FE;overflow:hidden;">'
                    + inner + '</div>')

        col1, col2, col3 = st.columns(3, gap="medium")
        with col1:
            rows  = _header_tabela("PROVENTOS", "💰")
            rows += _tabela_row("DESCRIÇÃO", "REF.", "VALOR", header=True)
            if _proventos_raw:
                for item in _proventos_raw:
                    v = _abs_val(item.get("valor", 0))
                    if v > 0:
                        rows += _tabela_row(str(item.get("descricao",""))[:32],
                                            str(item.get("referencia",""))[:8], v)
            else:
                if sal_base > 0: rows += _tabela_row("Salário Base", "", sal_base, negrito=True)
            rows += _tabela_row("TOTAL PROVENTOS", "", venc_total, negrito=True, separador=True)
            st.markdown(_wrap(rows), unsafe_allow_html=True)

        _CONSIG_KW = ["cartao","cartão","cred ","cart.","saque","anticipay","starcard","starbank",
                      "emprestimo","empréstimo","emprest","financiamento","delta global","bmp",
                      "daycoval","panamericano","bmg","meucashcard","credcesta","monetarie",
                      "pixcard","uasprev","cef","credifin","brcard","big card"]
        def _eh_consig(desc):
            return any(kw in str(desc).lower() for kw in _CONSIG_KW)

        with col2:
            rows  = _header_tabela("DESCONTOS", "📉")
            rows += _tabela_row("DESCRIÇÃO", "REF.", "VALOR", header=True)
            total_d = 0.0
            if _descontos_raw:
                for item in _descontos_raw:
                    v = _abs_val(item.get("valor", 0))
                    if v > 0 and not _eh_consig(item.get("descricao","")):
                        rows += _tabela_row(str(item.get("descricao",""))[:32],
                                            str(item.get("referencia",""))[:8], v)
                        total_d += v
            rows += _tabela_row("TOTAL DESCONTOS", "", total_d, negrito=True, separador=True)
            st.markdown(_wrap(rows), unsafe_allow_html=True)

        with col3:
            rows  = _header_tabela("CONSIGNAÇÕES", "💳")
            rows += _tabela_row("DESCRIÇÃO", "REF.", "VALOR", header=True)
            total_c = 0.0
            def _get_ref(d, v):
                for item in (_descontos_raw or []):
                    if (abs(_abs_val(item.get("valor",0))-v)<0.02 and
                            str(item.get("descricao","")).lower()[:12]==str(d).lower()[:12]):
                        return str(item.get("referencia",""))[:8]
                return ""
            for c in cartoes:
                v = _abs_val(c.get("valor",0))
                rows += _tabela_row(str(c.get("descricao",""))[:32], _get_ref(c.get("descricao",""),v), v)
                total_c += v
            for e in emprestimos:
                v = _abs_val(e.get("valor",0))
                rows += _tabela_row(str(e.get("descricao",""))[:32], _get_ref(e.get("descricao",""),v), v)
                total_c += v
            if total_c > 0:
                rows += _tabela_row("TOTAL CONSIGNAÇÕES", "", total_c, negrito=True, separador=True)
            else:
                rows += _tabela_row("Nenhuma consignação", "", 0.0)
            st.markdown(_wrap(rows), unsafe_allow_html=True)

    nossos       = [c for c in cartoes if c.get("tipo")=="nosso"]
    concorrentes = [c for c in cartoes if c.get("tipo")=="concorrente"]
    nao_comp     = [c for c in cartoes if c.get("tipo")=="nao_comprado"]
    desconhec    = [c for c in cartoes if c.get("tipo")=="desconhecido"]
    todos_cartoes = nossos + concorrentes + nao_comp + desconhec
    if todos_cartoes:
        partes = []
        if nossos:       partes.append(f"**{len(nossos)}** nosso(s)")
        if concorrentes: partes.append(f"**{len(concorrentes)}** concorrente(s)")
        if nao_comp:     partes.append(f"**{len(nao_comp)}** não compramos")
        if desconhec:    partes.append(f"**{len(desconhec)}** a verificar")
        st.info("Cartões: " + " · ".join(partes))
        i = 1
        for c in nossos:
            st.markdown(opp_card(c.get("descricao",""),
                f"Nosso produto | {fmt(c.get('valor',0))}/mês","#16a34a","#f0fdf4","#dcfce7",i), unsafe_allow_html=True); i+=1
        for c in concorrentes:
            st.markdown(opp_card(c.get("descricao",""),
                f"Concorrente — Compra de Dívida | {fmt(c.get('valor',0))}/mês","#1565c0","#eff6ff","#dbeafe",i), unsafe_allow_html=True); i+=1
        for c in nao_comp:
            st.markdown(opp_card(c.get("descricao",""),
                f"Não operamos | {fmt(c.get('valor',0))}/mês","#be185d","#fdf2f8","#fce7f3",i), unsafe_allow_html=True); i+=1
        for c in desconhec:
            st.markdown(opp_card(c.get("descricao",""),
                f"Verificar | {fmt(c.get('valor',0))}/mês","#b45309","#fffbeb","#fef3c7",i), unsafe_allow_html=True); i+=1


# ============================================================================
# ANÁLISE DE ARQUIVO
# ============================================================================
def analisar_arquivo(bytes_: bytes, nome: str) -> Dict:
    ext = nome.lower().rsplit(".",1)[-1]
    texto = (extrair_texto_imagem(bytes_) if ext in ("png","jpg","jpeg","webp","bmp","tiff","tif")
             else extrair_texto_pdf(bytes_))
    if not texto.strip(): return {"erro": "Não foi possível extrair texto do arquivo."}
    result = analisar_holerite_ia(texto)
    result["arquivo"] = nome
    result["texto_completo"] = texto
    return result


# ============================================================================
# LOTE
# ============================================================================
def processar_lote(arquivos) -> list:
    """
    Retorna lista de dicts — uma entrada por servidor, com:
    - dados completos do holerite
    - margem calculada
    - métricas de oportunidade
    - prioridade de abordagem
    """
    resultados = []
    pb   = st.progress(0)
    st_t = st.empty()

    for i, arq in enumerate(arquivos):
        pb.progress((i + 1) / len(arquivos))
        st_t.text(f"Processando {i+1}/{len(arquivos)}: {arq.name}")
        try:
            d = analisar_arquivo(arq.read(), arq.name)
            if "erro" in d:
                st.warning(f"⚠️ {arq.name}: {d['erro']}")
                continue

            margem      = calcular_margem_ia(d)
            marg_ok     = margem.get("disponivel", False)
            cartoes     = d.get("cartoes", []) or []
            emprestimos = d.get("emprestimos", []) or []

            concorrentes = [c for c in cartoes if c.get("tipo") == "concorrente"]
            nossos       = [c for c in cartoes if c.get("tipo") == "nosso"]
            nao_comp     = [c for c in cartoes if c.get("tipo") == "nao_comprado"]
            desconhec    = [c for c in cartoes if c.get("tipo") == "desconhecido"]

            emp_disp   = margem.get("emprestimo",{}).get("disponivel",0)   if marg_ok else 0
            cc_disp    = margem.get("cartao_consignado",{}).get("disponivel",0) if marg_ok else 0
            cb_disp    = margem.get("cartao_beneficio",{}).get("disponivel",0)  if marg_ok else 0
            emp_total  = margem.get("emprestimo",{}).get("margem_total",0)  if marg_ok else 0
            base_calc  = margem.get("base_calculo", 0) if marg_ok else 0

            total_conc   = sum(_abs_val(c.get("valor",0)) for c in concorrentes)
            total_nossos = sum(_abs_val(c.get("valor",0)) for c in nossos)
            total_emp    = sum(_abs_val(e.get("valor",0)) for e in emprestimos)
            total_cart   = sum(_abs_val(c.get("valor",0)) for c in cartoes)

            # ── Oportunidade principal e prioridade ─────────────────────────
            if concorrentes and emp_disp > 50:
                oportunidade = "🔥 Compra Dívida + Empréstimo"
                prioridade   = 1
            elif concorrentes and emp_disp > 0:
                oportunidade = "💳 Compra de Dívida"
                prioridade   = 2
            elif concorrentes:
                oportunidade = "💳 Compra de Dívida"
                prioridade   = 3
            elif emp_disp > 200:
                oportunidade = "💵 Empréstimo Disponível"
                prioridade   = 4
            elif nossos and emp_disp > 0:
                oportunidade = "🔄 Refinanciamento"
                prioridade   = 5
            elif emp_disp > 0:
                oportunidade = "💵 Margem Disponível"
                prioridade   = 6
            elif not marg_ok:
                oportunidade = "❓ Prefeitura Não Mapeada"
                prioridade   = 8
            else:
                oportunidade = "⛔ Margem Lotada"
                prioridade   = 9

            resultados.append({
                # Identificação
                "arquivo":          d.get("arquivo", ""),
                "prefeitura":       d.get("prefeitura", ""),
                "nome":             d.get("nome", ""),
                "matricula":        d.get("matricula", ""),
                "regime":           d.get("regime", ""),
                # Financeiro bruto
                "liquido":          _abs_val(d.get("liquido", 0)),
                "salario_base":     _abs_val(d.get("salario_base", 0)),
                "vencimentos":      _abs_val(d.get("vencimentos_total", 0)),
                # Margem calculada
                "base_calculo":     base_calc,
                "emp_disp":         emp_disp,
                "emp_total":        emp_total,
                "cc_disp":          cc_disp,
                "cb_disp":          cb_disp,
                # Consignações
                "total_emprestimos": total_emp,
                "total_cartoes":    total_cart,
                "total_concorrentes": total_conc,
                "qt_concorrentes":  len(concorrentes),
                "qt_nossos":        len(nossos),
                "qt_nao_comp":      len(nao_comp),
                "qt_desconhec":     len(desconhec),
                # Oportunidade
                "oportunidade":     oportunidade,
                "prioridade":       prioridade,
                "margem_ok":        marg_ok,
                # Objetos completos para expandir individualmente
                "_dados":           d,
                "_margem":          margem,
                "_concorrentes":    concorrentes,
                "_nossos":          nossos,
                "_emprestimos":     emprestimos,
            })

        except Exception as e:
            st.error(f"Erro {arq.name}: {e}")

    pb.empty()
    st_t.empty()
    # Ordena por prioridade, depois por emp_disp desc
    resultados.sort(key=lambda r: (r["prioridade"], -r["emp_disp"]))
    return resultados

def gerar_insights_ia_mercado(market_data: dict) -> list:
    """Gera insights estratégicos via IA com base nos dados agregados do lote."""
    key = _groq_key()
    if not key:
        return []

    prompt = f"""Você é a Stella, Chief Strategy Officer do Starbank Grupo — a mente estratégica mais afiada do mercado de crédito consignado.
Você acabou de receber os dados agregados de um lote de holerites analisados. Sua missão é gerar exatamente 6 insights estratégicos
que o CEO, o gestor comercial e a liderança vão querer imprimir e levar para a reunião de board.

DADOS DO LOTE:
{json.dumps(market_data, ensure_ascii=False, indent=2)}

PORTFÓLIO: {PORTFOLIO}

━━━ COMO PENSAR — LEIA ANTES DE ESCREVER ━━━

Você não está descrevendo os dados. Você está INTERPRETANDO o que eles significam para o negócio.
A diferença:
  ✗ "Temos 3 servidores com cartão concorrente totalizando R$ 450/mês"
  ✓ "R$ 450/mês saindo todo mês para o BMG representa uma receita recorrente que já deveria ser nossa —
     a cada mês sem ação, acumulamos R$ 450 de receita perdida. Em 12 meses, R$ 5.400 que financiamos
     para um concorrente sem nenhum custo de aquisição do nosso lado."

TIPOS DE INSIGHT QUE VOCÊ PODE (E DEVE) GERAR — escolha os mais relevantes para este lote:

1. RECEITA LATENTE — quanto dinheiro existe disponível se convertermos X% do potencial
2. CUSTO DA INAÇÃO — o que perdemos a cada mês que não agimos (receita que vai para concorrente, margem que expira)
3. CONCENTRAÇÃO DE RISCO — dependência de 1-2 prefeituras, regimes frágeis, carteiras que podem cair
4. EFEITO DOMINÓ — se convertermos o maior concorrente, quais outros produtos ficam viáveis em seguida
5. SEGMENTO OCULTO — perfil de servidor que ninguém está olhando mas tem margem intocada
6. VANTAGEM ASSIMÉTRICA — onde temos diferencial competitivo real que a concorrência não consegue replicar (ex: único a atender temporários)
7. BENCHMARK IMPLÍCITO — o que o ticket médio do concorrente nos diz sobre o posicionamento de preço deles vs o nosso
8. JANELA DE OPORTUNIDADE — situação que tem prazo (ex: cartão que vence, servidor prestes a se aposentar muda perfil de margem)
9. ALAVANCAGEM DE BASE — clientes nossos que ainda têm margem disponível = custo de aquisição zero, já confiam em nós
10. RISCO DE CHURN — sinais de que podemos perder clientes existentes para a concorrência

REGRAS ABSOLUTAS:
- Use APENAS os dados reais fornecidos — nunca invente números
- Cada insight deve ter uma CONCLUSÃO ACIONÁVEL clara: o que a liderança deve fazer com essa informação
- Seja específico: cite valores em R$, percentuais, nomes de instituições quando disponíveis
- Vá além do óbvio — insights que qualquer analista já veria não valem espaço
- Linguagem de board: densa, direta, sem eufemismos
- NUNCA cite valor de troco
- Máximo 5 linhas por texto — denso, não prolixo
- Retorne APENAS JSON válido, sem markdown, sem texto fora do JSON

JSON (exatamente 6 insights):
[
  {{"titulo": "título impactante de até 7 palavras", "texto": "insight denso com dado real + interpretação + conclusão acionável", "icone": "emoji relevante", "nivel": "critico"|"oportunidade"|"atencao"|"positivo"}},
  {{"titulo": "...", "texto": "...", "icone": "...", "nivel": "..."}},
  {{"titulo": "...", "texto": "...", "icone": "...", "nivel": "..."}},
  {{"titulo": "...", "texto": "...", "icone": "...", "nivel": "..."}},
  {{"titulo": "...", "texto": "...", "icone": "...", "nivel": "..."}},
  {{"titulo": "...", "texto": "...", "icone": "...", "nivel": "..."}}
]"""

    try:
        client = Groq(api_key=key)
        r = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1800,
            temperature=0.4,
        )
        c = r.choices[0].message.content.strip()
        c = re.sub(r"^```json\s*", "", c)
        c = re.sub(r"^```\s*", "", c)
        c = re.sub(r"\s*```$", "", c)
        s, e = c.find("["), c.rfind("]") + 1
        if s >= 0 and e > s:
            c = c[s:e]
        return json.loads(c)
    except Exception:
        return []

# ============================================================================
# GERADOR DE PDF — INTELIGÊNCIA DE MERCADO
# ============================================================================
"""
gerar_pdf_intel_v2 — Replicação fiel da aba "Inteligência de Mercado"
Mesmas cores, mesmos gráficos, mesma ordem da UI Streamlit.
"""

# ── Helpers ───────────────────────────────────────────────────────────────────
def _abs_val(v) -> float:
    try: return abs(float(v or 0))
    except: return 0.0

def fmt(v) -> str:
    try: return f"R$ {float(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")
    except: return "R$ 0,00"

# ── PALETA — idêntica ao app ──────────────────────────────────────────────────
COR_TIPO = {
    "nosso":       "#7c3aed",
    "concorrente": "#1d4ed8",
    "nao_comprado":"#be185d",
    "emprestimo":  "#d97706",
    "desconhecido":"#6b7280",
}
LABEL_TIPO = {
    "nosso":       "Starbank (Nossos)",
    "concorrente": "Concorrentes",
    "nao_comprado":"Não Compramos",
    "emprestimo":  "Empréstimos",
    "desconhecido":"Não Identificados",
}
COR_OPP = {
    "🔥 Compra Dívida + Empréstimo": "#d97706",
    "💳 Compra de Dívida":           "#1d4ed8",
    "💵 Empréstimo Disponível":      "#16a34a",
    "🔄 Refinanciamento":            "#7c3aed",
    "💵 Margem Disponível":          "#059669",
    "❓ Prefeitura Não Mapeada":     "#6b7280",
    "⛔ Margem Lotada":              "#dc2626",
}
COR_OPP_ESC = {
    "🔥 Compra Dívida + Empréstimo": "#92400e",
    "💳 Compra de Dívida":           "#1e3a8a",
    "💵 Empréstimo Disponível":      "#14532d",
    "🔄 Refinanciamento":            "#4c1d95",
    "💵 Margem Disponível":          "#065f46",
    "❓ Prefeitura Não Mapeada":     "#374151",
    "⛔ Margem Lotada":              "#991b1b",
}
COR_NIVEL = {
    "critico":      ("#fef2f2","#dc2626"),
    "oportunidade": ("#fef3c7","#d97706"),
    "atencao":      ("#eff6ff","#1d4ed8"),
    "positivo":     ("#f0fdf4","#16a34a"),
}
LABEL_NIVEL = {
    "critico":"CRÍTICO","oportunidade":"OPORTUNIDADE",
    "atencao":"ATENÇÃO","positivo":"POSITIVO",
}
ORDEM_FAIXAS = ["< R$2k","R$2k–3k","R$3k–5k","R$5k–8k","R$8k–12k","> R$12k"]
CORES_FAIXA  = ["#c4b5fd","#a78bfa","#8b5cf6","#7c3aed","#6d28d9","#5b21b6"]

W, H = A4

# ── Plotly → PNG ──────────────────────────────────────────────────────────────
def _fig_img(fig, w_cm=16, h_cm=7):
    w_px = int(w_cm / 2.54 * 96)
    h_px = int(h_cm / 2.54 * 96)
    try:
        data = fig.to_image(format="png", width=w_px, height=h_px, scale=2)
        return RLImage(_io.BytesIO(data), width=w_cm*cm, height=h_cm*cm, hAlign="CENTER")
    except Exception:
        return Paragraph("(gráfico indisponível)", _S("body"))

# ── Estilos ───────────────────────────────────────────────────────────────────
def _S(name, **kw): return ParagraphStyle(name, **kw)

ST = {
    "capa_tag":  _S("ct", fontSize=9,  fontName="Helvetica-Bold",
                    textColor=colors.HexColor("#C4B5FD"), leading=13),
    "capa_tit":  _S("cti",fontSize=28, fontName="Helvetica-Bold",
                    textColor=colors.white, leading=34),
    "capa_sub":  _S("csu",fontSize=12, fontName="Helvetica",
                    textColor=colors.HexColor("#DDD6FE"), leading=17),
    "capa_desc": _S("cde",fontSize=9,  fontName="Helvetica",
                    textColor=colors.HexColor("#C4B5FD"), leading=14),
    "sec":       _S("s",  fontSize=13, fontName="Helvetica-Bold",
                    textColor=colors.HexColor("#111827"), leading=18,
                    spaceBefore=8, spaceAfter=3),
    "subsec":    _S("ss", fontSize=10, fontName="Helvetica-Bold",
                    textColor=colors.HexColor("#374151"), leading=14,
                    spaceBefore=6, spaceAfter=2),
    "body":      _S("b",  fontSize=9,  fontName="Helvetica",
                    textColor=colors.HexColor("#374151"), leading=13),
    "caption":   _S("cap",fontSize=7.5,fontName="Helvetica",
                    textColor=colors.HexColor("#6b7280"), leading=11),
    "kpi_num":   _S("kn", fontSize=18, fontName="Helvetica-Bold",
                    textColor=colors.HexColor("#7c3aed"),
                    leading=22, alignment=TA_CENTER),
    "kpi_lbl":   _S("kl", fontSize=7.5,fontName="Helvetica",
                    textColor=colors.HexColor("#6b7280"),
                    leading=10, alignment=TA_CENTER),
    "kpi_dlt":   _S("kd", fontSize=7.5,fontName="Helvetica-Bold",
                    textColor=colors.HexColor("#16a34a"),
                    leading=10, alignment=TA_CENTER),
    "kpi_dlt_r": _S("kdr",fontSize=7.5,fontName="Helvetica-Bold",
                    textColor=colors.HexColor("#dc2626"),
                    leading=10, alignment=TA_CENTER),
    "th":        _S("th", fontSize=8,  fontName="Helvetica-Bold",
                    textColor=colors.white, leading=11, alignment=TA_CENTER),
    "th_l":      _S("thl",fontSize=8,  fontName="Helvetica-Bold",
                    textColor=colors.white, leading=11),
    "td":        _S("td", fontSize=8,  fontName="Helvetica",
                    textColor=colors.HexColor("#374151"), leading=11),
    "td_c":      _S("tdc",fontSize=8,  fontName="Helvetica",
                    textColor=colors.HexColor("#374151"), leading=11, alignment=TA_CENTER),
    "td_r":      _S("tdr",fontSize=8,  fontName="Helvetica",
                    textColor=colors.HexColor("#374151"), leading=11, alignment=TA_RIGHT),
    "td_b":      _S("tdb",fontSize=8,  fontName="Helvetica-Bold",
                    textColor=colors.HexColor("#111827"), leading=11),
    "ins_tit":   _S("it", fontSize=10, fontName="Helvetica-Bold",
                    textColor=colors.HexColor("#111827"), leading=14, spaceAfter=2),
    "ins_txt":   _S("itx",fontSize=9,  fontName="Helvetica",
                    textColor=colors.HexColor("#374151"), leading=13),
    "rodape":    _S("rod",fontSize=7,  fontName="Helvetica",
                    textColor=colors.HexColor("#9ca3af"), alignment=TA_CENTER),
}

# ── Tabela helper ─────────────────────────────────────────────────────────────
def _tbl(rows, fracs, hdr_color="#7c3aed", extra=None):
    usable = W - 3*cm
    t = Table(rows, colWidths=[usable*f for f in fracs], repeatRows=1)
    cmds = [
        ("BACKGROUND",    (0,0),(-1,0),  colors.HexColor(hdr_color)),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, colors.HexColor("#f9fafb")]),
        ("BOX",           (0,0),(-1,-1), 0.5, colors.HexColor("#e5e7eb")),
        ("INNERGRID",     (0,0),(-1,-1), 0.3, colors.HexColor("#e5e7eb")),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("RIGHTPADDING",  (0,0),(-1,-1), 6),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]
    if extra: cmds += extra
    t.setStyle(TableStyle(cmds))
    return t

# ── Decoradores de página ─────────────────────────────────────────────────────
def _draw_capa(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#4C1D95"))
    canvas.rect(0, 0, W, H, fill=True, stroke=False)
    canvas.setFillColor(colors.HexColor("#7C3AED"))
    canvas.rect(0, H*0.40, W, H*0.60, fill=True, stroke=False)
    canvas.setFillColor(colors.HexColor("#8B5CF6"))
    canvas.rect(0, H*0.70, W, H*0.30, fill=True, stroke=False)
    canvas.setFillColor(colors.HexColor("#6D28D9"))
    canvas.rect(0, 0, 8, H, fill=True, stroke=False)
    canvas.setFillColor(colors.HexColor("#6D28D930"))
    canvas.circle(W-80, H*0.76, 130, fill=True, stroke=False)
    canvas.setFillColor(colors.HexColor("#4C1D9525"))
    canvas.circle(W-40, H*0.70, 75, fill=True, stroke=False)
    canvas.setFillColor(colors.HexColor("#2E1065"))
    canvas.rect(0, 0, W, 22, fill=True, stroke=False)
    canvas.setFillColor(colors.HexColor("#A78BFA"))
    canvas.setFont("Helvetica", 7)
    canvas.drawString(1.5*cm, 7,
        f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}  ·  "
        "Starbank Grupo  ·  Confidencial — uso interno")
    canvas.restoreState()

def _draw_normal(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#4C1D95"))
    canvas.rect(0, H-26, W, 26, fill=True, stroke=False)
    canvas.setFillColor(colors.HexColor("#6D28D9"))
    canvas.rect(0, H-26, 5, 26, fill=True, stroke=False)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(1.3*cm, H-16, "StarCheck · Inteligência de Mercado")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(W-1.3*cm, H-16, datetime.now().strftime("%d/%m/%Y"))
    canvas.setFillColor(colors.HexColor("#f3f4f6"))
    canvas.rect(0, 0, W, 18, fill=True, stroke=False)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(W/2, 5,
        f"Starbank Grupo  ·  Página {canvas.getPageNumber()}  ·  Confidencial")
    canvas.restoreState()

# ── Seção header ──────────────────────────────────────────────────────────────
def _sec(titulo):
    return [
        Paragraph(titulo, ST["sec"]),
        HRFlowable(width="100%", thickness=1.5,
                   color=colors.HexColor("#e5e7eb"), spaceAfter=5),
    ]

# ═════════════════════════════════════════════════════════════════════════════
# FUNÇÃO PRINCIPAL
# ═════════════════════════════════════════════════════════════════════════════
def gerar_pdf_intel(resultados: list, insights_ia: list,
                    market_payload: dict,
                    NOSSOS_PRODUTOS: list = None) -> bytes:

    if NOSSOS_PRODUTOS is None:
        NOSSOS_PRODUTOS = ["STARCARD","ANTICIPAY","STARBANK","UASPREV"]

    buf = _io.BytesIO()
    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=0.8*cm, bottomMargin=1.2*cm,
    )
    f_capa   = Frame(0, 0, W, H, leftPadding=2.2*cm, rightPadding=2*cm,
                     topPadding=0, bottomPadding=2.8*cm, id="capa")
    f_normal = Frame(1.5*cm, 1.2*cm, W-3*cm, H-3.1*cm, id="normal")
    doc.addPageTemplates([
        PageTemplate(id="Capa",   frames=[f_capa],   onPage=_draw_capa),
        PageTemplate(id="Normal", frames=[f_normal], onPage=_draw_normal),
    ])

    # ── PRÉ-CÁLCULOS (espelho do tab_intel) ───────────────────────────────────
    total   = len(resultados)
    n_prefs = len(set(r.get("prefeitura","") for r in resultados))

    inst_data = defaultdict(lambda:{"contratos":0,"valor":0.0,"servidores":set(),"tipo":""})
    n_nos_ct=n_con_ct=n_nco_ct=n_emp_ct=n_des_ct=0
    vol_nos=vol_con=vol_nco=vol_emp=vol_des=0.0

    for idx_r, r in enumerate(resultados):
        d = r.get("_dados",{})
        for c in d.get("cartoes",[]):
            desc  = str(c.get("descricao","")).strip()
            tipo  = c.get("tipo","desconhecido")
            valor = _abs_val(c.get("valor",0))
            if not desc or valor<=0: continue
            inst_data[desc]["contratos"]   +=1
            inst_data[desc]["valor"]       +=valor
            inst_data[desc]["tipo"]         =tipo
            inst_data[desc]["servidores"].add(idx_r)
            if   tipo=="nosso":        n_nos_ct+=1; vol_nos+=valor
            elif tipo=="concorrente":  n_con_ct+=1; vol_con+=valor
            elif tipo=="nao_comprado": n_nco_ct+=1; vol_nco+=valor
            elif tipo=="desconhecido": n_des_ct+=1; vol_des+=valor
        for e in d.get("emprestimos",[]):
            desc  = str(e.get("descricao","")).strip()
            valor = _abs_val(e.get("valor",0))
            if not desc or valor<=0: continue
            tipo_e = ("nosso" if any(p.upper() in desc.upper() for p in NOSSOS_PRODUTOS)
                      else "emprestimo")
            inst_data[desc]["contratos"]   +=1
            inst_data[desc]["valor"]       +=valor
            inst_data[desc]["tipo"]         =tipo_e
            inst_data[desc]["servidores"].add(idx_r)
            if tipo_e=="nosso": n_nos_ct+=1; vol_nos+=valor
            else:               n_emp_ct+=1; vol_emp+=valor

    inst_list = sorted([
        {"desc":k,"contratos":v["contratos"],"valor":v["valor"],
         "servidores":len(v["servidores"]),"tipo":v["tipo"],
         "ticket":v["valor"]/v["contratos"] if v["contratos"]>0 else 0}
        for k,v in inst_data.items()
    ], key=lambda x:x["valor"], reverse=True)

    total_ct     = n_nos_ct+n_con_ct+n_nco_ct+n_emp_ct+n_des_ct
    total_consig = vol_nos+vol_con+vol_nco+vol_emp+vol_des
    pct_nosso    = (vol_nos/total_consig*100) if total_consig>0 else 0
    pct_conc     = (vol_con/total_consig*100) if total_consig>0 else 0
    com_nos      = [r for r in resultados if r.get("qt_nossos",0)>0]
    taxa_penet   = (len(com_nos)/total*100) if total>0 else 0

    sem_consig = [r for r in resultados
                  if r.get("total_cartoes",0)==0 and r.get("total_emprestimos",0)==0]
    so_nosso   = [r for r in resultados
                  if r.get("qt_nossos",0)>0  and r.get("qt_concorrentes",0)==0]
    so_conc    = [r for r in resultados
                  if r.get("qt_nossos",0)==0 and r.get("qt_concorrentes",0)>0]
    misto      = [r for r in resultados
                  if r.get("qt_nossos",0)>0  and r.get("qt_concorrentes",0)>0]
    marg_disp  = sum(r.get("emp_disp",0) for r in resultados if r.get("emp_disp",0)>0)

    def faixa(v):
        if v<2000: return "< R$2k"
        if v<3000: return "R$2k–3k"
        if v<5000: return "R$3k–5k"
        if v<8000: return "R$5k–8k"
        if v<12000:return "R$8k–12k"
        return "> R$12k"

    faixas  = Counter(faixa(r.get("salario_base",0)) for r in resultados)
    regimes = Counter(r.get("regime","N/A") for r in resultados)
    opps    = Counter(r.get("oportunidade","") for r in resultados)

    prod_freq = defaultdict(lambda:{"contratos":0,"valor":0.0})
    for r in resultados:
        d = r.get("_dados",{})
        for c in d.get("cartoes",[]):
            if c.get("tipo")!="nosso": continue
            desc = str(c.get("descricao","")).upper()
            m = next((p for p in NOSSOS_PRODUTOS if p.upper() in desc),"OUTROS")
            prod_freq[m]["contratos"]+=1
            prod_freq[m]["valor"]+=_abs_val(c.get("valor",0))
        for e in d.get("emprestimos",[]):
            desc = str(e.get("descricao","")).upper()
            m = next((p for p in NOSSOS_PRODUTOS if p.upper() in desc),None)
            if m:
                prod_freq[m]["contratos"]+=1
                prod_freq[m]["valor"]+=_abs_val(e.get("valor",0))

    pref_map = {}
    for r in resultados:
        p = r.get("prefeitura") or "Desconhecida"
        if p not in pref_map:
            pref_map[p] = dict(servidores=0,emp_disp=0.0,emp_total=0.0,
                               conc_total=0.0,qt_conc=0,qt_nossos=0,
                               liquido_total=0.0,qt_marg=0,qt_lot=0,qt_sem=0)
        v = pref_map[p]
        v["servidores"]   +=1
        v["emp_disp"]     +=max(r.get("emp_disp",0),0)
        v["emp_total"]    +=max(r.get("emp_total",0),0)
        v["conc_total"]   +=r.get("total_concorrentes",0)
        v["qt_conc"]      +=r.get("qt_concorrentes",0)
        v["qt_nossos"]    +=r.get("qt_nossos",0)
        v["liquido_total"]+=r.get("liquido",0)
        if not r.get("margem_ok"):   v["qt_sem"] +=1
        elif r.get("emp_disp",0)>0:  v["qt_marg"]+=1
        else:                         v["qt_lot"] +=1
    pref_sorted = sorted(pref_map.items(), key=lambda x:x[1]["emp_disp"], reverse=True)

    faixa_consig = defaultdict(lambda:{"total":0,"com":0})
    for r in resultados:
        f = faixa(r.get("salario_base",0))
        faixa_consig[f]["total"]+=1
        if r.get("total_cartoes",0)>0 or r.get("total_emprestimos",0)>0:
            faixa_consig[f]["com"]+=1

    # ── STORY ─────────────────────────────────────────────────────────────────
    story = []

    # ═══════════════════════════════════════════════════════════════════════════
    # CAPA
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 5.5*cm))
    story.append(Paragraph("STARCHECK · ANÁLISE ESTRATÉGICA", ST["capa_tag"]))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("Inteligência de Mercado", ST["capa_tit"]))
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(
        f"{total} servidores analisados  ·  {n_prefs} prefeitura(s)  ·  "
        f"{datetime.now().strftime('%B de %Y').capitalize()}",
        ST["capa_sub"]
    ))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(
        "Análise estratégica baseada nos holerites processados — market share, "
        "mapa competitivo, perfil de cliente e oportunidades para gestão e liderança.",
        ST["capa_desc"]
    ))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # 1. INDICADORES ESTRATÉGICOS  (6 st.metric)
    # ═══════════════════════════════════════════════════════════════════════════
    story += _sec("📌 Indicadores Estratégicos")

    def _mc(num, lbl, delta="", red=False):
        ds = ST["kpi_dlt_r"] if red else ST["kpi_dlt"]
        return [Paragraph(num, ST["kpi_num"]),
                Paragraph(lbl, ST["kpi_lbl"]),
                Paragraph(delta, ds) if delta else Paragraph("", ST["kpi_lbl"])]

    def _kpi_tbl(cells3):
        r_num   = [c[0] for c in cells3]
        r_lbl   = [c[1] for c in cells3]
        r_del   = [c[2] for c in cells3]
        usable  = W-3*cm
        t = Table([r_num, r_lbl, r_del], colWidths=[usable/3]*3)
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#F5F3FF")),
            ("BOX",           (0,0),(-1,-1), 1, colors.HexColor("#DDD6FE")),
            ("INNERGRID",     (0,0),(-1,-1), 0.5, colors.HexColor("#DDD6FE")),
            ("TOPPADDING",    (0,0),(-1,0),  10),
            ("BOTTOMPADDING", (0,0),(-1,0),  4),
            ("TOPPADDING",    (0,1),(-1,-1), 2),
            ("BOTTOMPADDING", (0,2),(-1,-1), 8),
            ("ALIGN",         (0,0),(-1,-1), "CENTER"),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ]))
        return t

    story.append(_kpi_tbl([
        _mc(fmt(total_consig),    "💰 Volume Consig./Mês",       f"{total_ct} contratos ativos"),
        _mc(fmt(vol_nos),         "🏆 Nossa Receita/Mês",        f"{pct_nosso:.1f}% do mercado"),
        _mc(fmt(vol_con),         "💳 Volume Concorrentes",      f"{pct_conc:.1f}% do mercado", red=True),
    ]))
    story.append(Spacer(1, 4))
    story.append(_kpi_tbl([
        _mc(f"{taxa_penet:.0f}%", "📈 Nossa Penetração",         f"{len(com_nos)}/{total} servidores"),
        _mc(str(len(so_conc)),    "🎯 Alvo Puro (sem nós)",      f"{len(so_conc)/total*100:.0f}% da base", red=True),
        _mc(str(len(sem_consig)), "🌱 Mercado Novo",              "Sem histórico de crédito"),
    ]))
    story.append(Spacer(1, 12))

    # ═══════════════════════════════════════════════════════════════════════════
    # 2. MARKET SHARE — duas pizzas (idêntico ao app)
    # ═══════════════════════════════════════════════════════════════════════════
    story += _sec("Market Share")

    ms_l=[]; ms_v=[]; ms_c=[]
    ct_l=[]; ct_v=[]; ct_c=[]
    vol_map = {"nosso":vol_nos,"concorrente":vol_con,"nao_comprado":vol_nco,
               "emprestimo":vol_emp,"desconhecido":vol_des}
    cnt_map = {"nosso":n_nos_ct,"concorrente":n_con_ct,"nao_comprado":n_nco_ct,
               "emprestimo":n_emp_ct,"desconhecido":n_des_ct}
    for tipo in ["nosso","concorrente","nao_comprado","emprestimo","desconhecido"]:
        if vol_map[tipo]>0:
            ms_l.append(LABEL_TIPO[tipo]); ms_v.append(vol_map[tipo])
            ms_c.append(COR_TIPO[tipo])
        if cnt_map[tipo]>0:
            ct_l.append(LABEL_TIPO[tipo]); ct_v.append(cnt_map[tipo])
            ct_c.append(COR_TIPO[tipo])

    fig_ms = make_subplots(
        rows=1, cols=2,
        specs=[[{"type":"pie"},{"type":"pie"}]],
        subplot_titles=["Por Volume Mensal (R$)", "Por Número de Contratos"],
    )
    if ms_v:
        fig_ms.add_trace(go.Pie(
            labels=ms_l, values=ms_v, marker_colors=ms_c, hole=0.5,
            textinfo="label+percent", textfont_size=10, showlegend=True,
        ), row=1, col=1)
    if ct_v:
        fig_ms.add_trace(go.Pie(
            labels=ct_l, values=ct_v, marker_colors=ct_c, hole=0.5,
            textinfo="label+percent", textfont_size=10, showlegend=False,
        ), row=1, col=2)
    fig_ms.update_layout(
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="sans-serif", size=10, color="#374151"),
        margin=dict(t=50, b=70, l=10, r=10),
        legend=dict(orientation="h", y=-0.18, font_size=10, x=0.5, xanchor="center"),
        height=360, width=900,
        annotations=list(fig_ms.layout.annotations) + [
            dict(text=f"<b>{fmt(total_consig)}</b><br>/mês",
                 x=0.21, y=0.5, showarrow=False, font_size=9, font_color="#374151"),
            dict(text=f"<b>{total_ct}</b><br>contratos",
                 x=0.79, y=0.5, showarrow=False, font_size=9, font_color="#374151"),
        ],
    )
    story.append(_fig_img(fig_ms, w_cm=16, h_cm=8.5))
    story.append(Spacer(1, 10))

    # ═══════════════════════════════════════════════════════════════════════════
    # 3. MAPA COMPETITIVO — bar horizontal (idêntico ao app)
    # ═══════════════════════════════════════════════════════════════════════════
    story += _sec("Mapa Competitivo — Instituições Presentes na Folha")

    top15 = inst_list[:15]
    if top15:
        fig_comp = go.Figure(go.Bar(
            y=[i["desc"][:24] for i in top15][::-1],
            x=[i["valor"]     for i in top15][::-1],
            orientation="h",
            marker_color=[COR_TIPO.get(i["tipo"],"#6b7280") for i in top15][::-1],
            text=[fmt(i["valor"]) for i in top15][::-1],
            textposition="outside", textfont=dict(size=9),
        ))
        fig_comp.update_layout(
            paper_bgcolor="white", plot_bgcolor="white",
            font=dict(family="sans-serif", size=10, color="#374151"),
            margin=dict(t=20, b=20, l=10, r=110),
            xaxis=dict(tickprefix="R$ ", gridcolor="#f3f4f6", tickfont_size=9),
            yaxis=dict(tickfont_size=9),
            showlegend=False,
            height=max(320, len(top15)*28+80), width=900,
        )
        story.append(_fig_img(fig_comp, w_cm=16, h_cm=max(8, len(top15)*0.75)))

    # legenda (igual ao app)
    leg = "  ".join(
        f'<font color="{cor}">■</font> <font size="8" color="#374151">{lbl}</font>'
        for cor, lbl in [("#7c3aed","Nossos"),("#1d4ed8","Concorrentes"),
                         ("#be185d","Não Compramos"),("#d97706","Empréstimos"),
                         ("#6b7280","Não Identificados")]
    )
    story.append(Spacer(1, 4))
    story.append(Paragraph(leg, _S("leg", fontSize=8, fontName="Helvetica", leading=12)))
    story.append(Spacer(1, 10))

    # Tabela detalhada (idêntica ao expander do app)
    story.append(Paragraph("Tabela Detalhada por Instituição", ST["subsec"]))
    tipo_lbl = {"nosso":"Nosso","concorrente":"Concorrente",
                "nao_comprado":"Não Compramos","emprestimo":"Empréstimo","desconhecido":"?"}
    tbl_hdr = [
        Paragraph("Instituição",  ST["th_l"]),
        Paragraph("Tipo",        ST["th"]),
        Paragraph("Vol./Mês",    ST["th"]),
        Paragraph("% Total",     ST["th"]),
        Paragraph("Contratos",   ST["th"]),
        Paragraph("Servidores",  ST["th"]),
        Paragraph("Ticket Médio",ST["th"]),
    ]
    tbl_rows = [tbl_hdr]
    for inst in inst_list:
        pct_t = inst["valor"]/total_consig*100 if total_consig>0 else 0
        cor   = COR_TIPO.get(inst["tipo"],"#6b7280")
        tbl_rows.append([
            Paragraph(inst["desc"][:30], ST["td_b"]),
            Paragraph(f'<font color="{cor}"><b>{tipo_lbl.get(inst["tipo"],"?")}</b></font>',
                      ST["td_c"]),
            Paragraph(fmt(inst["valor"]),    ST["td_r"]),
            Paragraph(f"{pct_t:.1f}%",       ST["td_c"]),
            Paragraph(str(inst["contratos"]),ST["td_c"]),
            Paragraph(str(inst["servidores"]),ST["td_c"]),
            Paragraph(fmt(inst["ticket"]),   ST["td_r"]),
        ])
    story.append(_tbl(tbl_rows, [0.30,0.14,0.16,0.10,0.10,0.10,0.10],
                      hdr_color="#1D4ED8"))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # 4. SEGMENTAÇÃO DE CLIENTES  (4 gráficos em 2 linhas × 2 cols)
    # ═══════════════════════════════════════════════════════════════════════════
    story += _sec("Segmentação da Base de Clientes")

    # Linha 1 — Perfil relacionamento (pie) + Faixa salarial (bar)
    story.append(Paragraph("Perfil de Relacionamento Consignado  ·  Faixa Salarial",
                            ST["subsec"]))
    seg_l=[]; seg_v=[]; seg_c=[]
    for lbl, grp, cor in [
        ("🌱 Sem Consignações",      sem_consig,"#059669"),
        ("🏆 Só Nossos Produtos",    so_nosso,  "#7c3aed"),
        ("🎯 Só Concorrentes",       so_conc,   "#1d4ed8"),
        ("🔀 Nossos + Concorrentes", misto,     "#d97706"),
    ]:
        if grp: seg_l.append(lbl); seg_v.append(len(grp)); seg_c.append(cor)
    outros = total-sum(seg_v)
    if outros>0: seg_l.append("❓ Outros"); seg_v.append(outros); seg_c.append("#9ca3af")
    fx_ord = [(f, faixas.get(f,0)) for f in ORDEM_FAIXAS if faixas.get(f,0)>0]

    fig_r1 = make_subplots(
        rows=1, cols=2,
        specs=[[{"type":"pie"},{"type":"bar"}]],
        subplot_titles=["Perfil de Relacionamento","Faixa Salarial (Salário Base)"],
        column_widths=[0.45, 0.55],
    )
    if seg_v:
        fig_r1.add_trace(go.Pie(
            labels=seg_l, values=seg_v, marker_colors=seg_c,
            hole=0.42, textinfo="value+percent", textfont_size=9, showlegend=True,
        ), row=1, col=1)
    if fx_ord:
        fig_r1.add_trace(go.Bar(
            x=[f[0] for f in fx_ord], y=[f[1] for f in fx_ord],
            marker_color=CORES_FAIXA[:len(fx_ord)],
            text=[f[1] for f in fx_ord], textposition="outside", textfont_size=10,
            showlegend=False,
        ), row=1, col=2)
    fig_r1.update_layout(
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="sans-serif", size=10),
        margin=dict(t=50, b=75, l=20, r=20),
        legend=dict(orientation="h", y=-0.25, font_size=9, x=0.22, xanchor="center"),
        height=340, width=900,
        yaxis2=dict(gridcolor="#f3f4f6", title="Servidores"),
    )
    story.append(_fig_img(fig_r1, w_cm=16, h_cm=8.5))
    story.append(Spacer(1, 10))

    # Linha 2 — Distribuição por regime + Taxa consignação por faixa
    story.append(Paragraph("Distribuição por Regime  ·  Taxa de Consignação por Faixa Salarial",
                            ST["subsec"]))
    reg_l = list(regimes.keys()); reg_v = list(regimes.values())
    fx_tc_l=[]; fx_tc_v=[]
    for f in ORDEM_FAIXAS:
        fc = faixa_consig.get(f,{})
        if fc.get("total",0)>0:
            fx_tc_l.append(f)
            fx_tc_v.append(round(fc["com"]/fc["total"]*100,1))

    fig_r2 = make_subplots(
        rows=1, cols=2,
        specs=[[{"type":"bar"},{"type":"bar"}]],
        subplot_titles=["Distribuição por Regime","Taxa de Consignação por Faixa (%)"],
        column_widths=[0.45, 0.55],
    )
    if reg_l:
        fig_r2.add_trace(go.Bar(
            x=reg_l, y=reg_v, marker_color="#7c3aed",
            text=reg_v, textposition="outside", textfont_size=10,
            showlegend=False,
        ), row=1, col=1)
    if fx_tc_l:
        fig_r2.add_trace(go.Bar(
            x=fx_tc_l, y=fx_tc_v,
            marker_color=["#f97316" if p>70 else "#7c3aed" if p>40 else "#a78bfa"
                          for p in fx_tc_v],
            text=[f"{p:.0f}%" for p in fx_tc_v],
            textposition="outside", textfont_size=10, showlegend=False,
        ), row=1, col=2)
    fig_r2.update_layout(
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="sans-serif", size=10),
        margin=dict(t=50, b=50, l=20, r=20),
        height=300, width=900,
        yaxis=dict(gridcolor="#f3f4f6"),
        yaxis2=dict(gridcolor="#f3f4f6", range=[0,120], title="%"),
    )
    story.append(_fig_img(fig_r2, w_cm=16, h_cm=7.5))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # 5. PENETRAÇÃO DOS NOSSOS PRODUTOS  (bar+scatter + funil)
    # ═══════════════════════════════════════════════════════════════════════════
    story += _sec("Penetração dos Nossos Produtos")
    story.append(Paragraph(
        "Presença por Produto (Volume e Contratos)  ·  Funil de Oportunidade de Mercado",
        ST["subsec"]
    ))

    p_names = list(prod_freq.keys())
    p_vals  = [prod_freq[p]["valor"]     for p in p_names]
    p_cts   = [prod_freq[p]["contratos"] for p in p_names]

    com_nos_n    = len(com_nos)
    sem_nos_conc = len([r for r in resultados
                        if r.get("qt_nossos",0)==0 and r.get("qt_concorrentes",0)>0])
    sem_nos_emp  = len([r for r in resultados
                        if r.get("qt_nossos",0)==0 and r.get("total_emprestimos",0)>0
                        and r.get("qt_concorrentes",0)==0])

    fig_pen = make_subplots(
        rows=1, cols=2,
        specs=[[{"secondary_y":True},{"type":"funnel"}]],
        subplot_titles=["Presença por Produto","Funil de Oportunidade de Mercado"],
        column_widths=[0.55, 0.45],
    )
    if p_names:
        fig_pen.add_trace(go.Bar(
            name="Volume R$/mês", x=p_names, y=p_vals, marker_color="#7c3aed",
            text=[fmt(v) for v in p_vals], textposition="outside", textfont_size=9,
            showlegend=True,
        ), row=1, col=1, secondary_y=False)
        fig_pen.add_trace(go.Scatter(
            name="Nº Contratos", x=p_names, y=p_cts, mode="markers+text",
            marker=dict(size=10, color="#f97316", symbol="diamond"),
            text=p_cts, textposition="top center", textfont_size=10, showlegend=True,
        ), row=1, col=1, secondary_y=True)
    fig_pen.add_trace(go.Funnel(
        y=["Total Servidores","Com Nossos Produtos","Alvo (só concorrente)",
           "Emp. sem nós","Mercado Novo"],
        x=[total, com_nos_n, sem_nos_conc, sem_nos_emp, len(sem_consig)],
        textinfo="value+percent initial",
        marker_color=["#4c1d95","#7c3aed","#1d4ed8","#d97706","#059669"],
        textfont_size=10, showlegend=False,
        connector=dict(line=dict(color="#e5e7eb", width=1.5)),
    ), row=1, col=2)
    fig_pen.update_layout(
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="sans-serif", size=10),
        margin=dict(t=60, b=70, l=20, r=20),
        legend=dict(orientation="h", y=-0.22, font_size=9),
        height=340, width=900,
    )
    fig_pen.update_yaxes(title_text="R$/mês", tickprefix="R$ ",
                         gridcolor="#f3f4f6", row=1, col=1, secondary_y=False)
    fig_pen.update_yaxes(title_text="Contratos", row=1, col=1,
                         secondary_y=True, showgrid=False)
    story.append(_fig_img(fig_pen, w_cm=16, h_cm=8.5))
    story.append(Spacer(1, 10))

    # Distribuição de oportunidades — bar horizontal (igual ao app)
    story += _sec("Distribuição de Oportunidades Identificadas")
    opp_sorted = opps.most_common()
    if opp_sorted:
        fig_opp = go.Figure(go.Bar(
            y=[o[0] for o in opp_sorted][::-1],
            x=[o[1] for o in opp_sorted][::-1],
            orientation="h",
            marker_color=[COR_OPP.get(o[0],"#6b7280") for o in opp_sorted][::-1],
            text=[o[1] for o in opp_sorted][::-1],
            textposition="outside", textfont_size=11,
        ))
        fig_opp.update_layout(
            paper_bgcolor="white", plot_bgcolor="white",
            font=dict(family="sans-serif", size=10),
            margin=dict(t=20, b=20, l=10, r=55),
            xaxis=dict(title="Servidores", gridcolor="#f3f4f6"),
            showlegend=False,
            height=max(220, len(opp_sorted)*40+80), width=900,
        )
        story.append(_fig_img(fig_opp, w_cm=16, h_cm=max(5.5, len(opp_sorted)*1.1)))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # 6. ANÁLISE POR PREFEITURA  (espelho do tab_pref)
    # ═══════════════════════════════════════════════════════════════════════════
    story += _sec("📊 Análise por Prefeitura")

    if pref_sorted:
        pnames = [p[:20] for p,_ in pref_sorted]
        pemp_d = [max(v["emp_disp"],0)               for _,v in pref_sorted]
        pemp_u = [max(v["emp_total"]-v["emp_disp"],0) for _,v in pref_sorted]
        pconc  = [v["conc_total"]                     for _,v in pref_sorted]
        p_disp = [v["qt_marg"]                        for _,v in pref_sorted]
        p_lot  = [v["qt_lot"]                         for _,v in pref_sorted]
        p_sem  = [v["qt_sem"]                         for _,v in pref_sorted]

        # Margem disponível vs comprometida — stacked (igual ao app)
        story.append(Paragraph("💰 Margem de Empréstimo: Disponível vs Utilizada", ST["subsec"]))
        fig_marg = go.Figure()
        fig_marg.add_bar(
            name="Já Comprometido", x=pnames, y=pemp_u, marker_color="#f97316",
            text=[fmt(u) if u>0 else "" for u in pemp_u],
            textposition="inside", textfont_color="white", textfont_size=9,
        )
        fig_marg.add_bar(
            name="Disponível", x=pnames, y=[max(d,0) for d in pemp_d],
            marker_color="#7c3aed",
            text=[fmt(d) if d>0 else "" for d in pemp_d],
            textposition="inside", textfont_color="white", textfont_size=9,
        )
        fig_marg.update_layout(
            barmode="stack", paper_bgcolor="white", plot_bgcolor="white",
            font=dict(family="sans-serif", size=10),
            margin=dict(t=20, b=55, l=20, r=20),
            legend=dict(orientation="h", y=-0.28, font_size=10),
            yaxis=dict(tickprefix="R$ ", gridcolor="#f3f4f6"),
            height=280, width=900,
        )
        story.append(_fig_img(fig_marg, w_cm=16, h_cm=7))
        story.append(Spacer(1, 6))

        # Concorrentes por prefeitura (igual ao app)
        story.append(Paragraph("💳 Cartões Concorrentes — Volume Mensal Saindo da Folha",
                                ST["subsec"]))
        fig_conc = go.Figure(go.Bar(
            name="Concorrentes R$/mês", x=pnames, y=pconc, marker_color="#1d4ed8",
            text=[fmt(c) if c>0 else "" for c in pconc],
            textposition="outside", textfont_size=9,
        ))
        fig_conc.update_layout(
            paper_bgcolor="white", plot_bgcolor="white",
            font=dict(family="sans-serif", size=10),
            margin=dict(t=20, b=50, l=20, r=20),
            yaxis=dict(tickprefix="R$ ", gridcolor="#f3f4f6"),
            showlegend=False, height=240, width=900,
        )
        story.append(_fig_img(fig_conc, w_cm=16, h_cm=6))
        story.append(Spacer(1, 6))

        # Oportunidades (pizza) + Status margem (stacked) — igual ao app
        story.append(Paragraph(
            "🎯 Distribuição de Oportunidades  ·  📊 Status de Margem por Prefeitura",
            ST["subsec"]
        ))
        opp_sorted_pref = opps.most_common()
        fig_2col = make_subplots(
            rows=1, cols=2,
            specs=[[{"type":"pie"},{"type":"bar"}]],
            subplot_titles=["Distribuição de Oportunidades",
                            "Status de Margem por Prefeitura"],
            column_widths=[0.45, 0.55],
        )
        if opp_sorted_pref:
            fig_2col.add_trace(go.Pie(
                labels=[o[0] for o in opp_sorted_pref],
                values=[o[1] for o in opp_sorted_pref],
                marker_colors=[COR_OPP.get(o[0],"#9ca3af") for o in opp_sorted_pref],
                hole=0.45, textinfo="value+percent", textfont_size=9, showlegend=True,
            ), row=1, col=1)
        for name, yvals, cor in [
            ("✅ Margem Disponível", p_disp, "#16a34a"),
            ("⛔ Margem Lotada",     p_lot,  "#dc2626"),
            ("❓ Sem Mapeamento",    p_sem,  "#9ca3af"),
        ]:
            fig_2col.add_trace(go.Bar(
                name=name, x=pnames, y=yvals, marker_color=cor, showlegend=True,
            ), row=1, col=2)
        fig_2col.update_layout(
            barmode="stack", paper_bgcolor="white", plot_bgcolor="white",
            font=dict(family="sans-serif", size=9),
            margin=dict(t=55, b=85, l=20, r=20),
            legend=dict(orientation="h", y=-0.35, font_size=9, x=0.5, xanchor="center"),
            height=330, width=900,
            yaxis2=dict(title="Servidores", gridcolor="#f3f4f6"),
        )
        story.append(_fig_img(fig_2col, w_cm=16, h_cm=8.5))
        story.append(Spacer(1, 8))

        # Tabela por prefeitura
        story.append(Paragraph("Métricas Consolidadas por Prefeitura", ST["subsec"]))
        p_hdr = [
            Paragraph("Prefeitura",   ST["th_l"]),
            Paragraph("Serv.",        ST["th"]),
            Paragraph("Emp. Disp.",   ST["th"]),
            Paragraph("Concorr./Mês",ST["th"]),
            Paragraph("Nossos",       ST["th"]),
            Paragraph("Liq. Médio",  ST["th"]),
            Paragraph("% Marg.",      ST["th"]),
        ]
        p_rows = [p_hdr]
        for pref,v in pref_sorted:
            ml  = v["liquido_total"]/v["servidores"] if v["servidores"] else 0
            pmd = v["qt_marg"]/v["servidores"]*100   if v["servidores"] else 0
            p_rows.append([
                Paragraph(pref[:28], ST["td_b"]),
                Paragraph(str(v["servidores"]), ST["td_c"]),
                Paragraph(fmt(v["emp_disp"]),   ST["td_r"]),
                Paragraph(fmt(v["conc_total"]), ST["td_r"]),
                Paragraph(str(v["qt_nossos"]),  ST["td_c"]),
                Paragraph(fmt(ml),              ST["td_r"]),
                Paragraph(f"{pmd:.0f}%",        ST["td_c"]),
            ])
        story.append(_tbl(p_rows, [0.31,0.09,0.15,0.15,0.09,0.13,0.08]))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # 7. INSIGHTS ESTRATÉGICOS (IA)  — idêntico ao app
    # ═══════════════════════════════════════════════════════════════════════════
    story += _sec("💡 Insights Estratégicos · Stella IA")

    if insights_ia:
        for ins in insights_ia:
            nivel = ins.get("nivel","atencao")
            bg_hex, borda_hex = COR_NIVEL.get(nivel,("#f9fafb","#6b7280"))
            label_n = LABEL_NIVEL.get(nivel, nivel.upper())
            icone  = ins.get("icone","💡")
            titulo = ins.get("titulo","")
            texto  = ins.get("texto","")
            bloco  = Table(
                [[Paragraph(
                    f'{icone}  <b>{titulo}</b>'
                    f'  <font size="7" color="{borda_hex}"> [{label_n}]</font>',
                    ST["ins_tit"])],
                 [Paragraph(texto, ST["ins_txt"])]],
                colWidths=[W-4.5*cm],
            )
            bloco.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor(bg_hex)),
                ("TOPPADDING",    (0,0),(-1,-1), 8),
                ("BOTTOMPADDING", (0,0),(-1,-1), 8),
                ("LEFTPADDING",   (0,0),(-1,-1), 12),
                ("RIGHTPADDING",  (0,0),(-1,-1), 10),
                ("BOX",           (0,0),(-1,-1), 0.5, colors.HexColor(borda_hex)),
                ("LINEAFTER",     (0,0),(0,-1),  4,   colors.HexColor(borda_hex)),
            ]))
            story.append(KeepTogether([bloco, Spacer(1,5)]))
    else:
        story.append(Paragraph("Insights não disponíveis.", ST["body"]))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # 8. RANKING DE OPORTUNIDADES  (espelho do tab_rank)
    # ═══════════════════════════════════════════════════════════════════════════
    story += _sec("🏆 Ranking de Oportunidades — Servidores")
    story.append(Paragraph(
        "Ordenado por prioridade comercial — do maior potencial de conversão ao menor urgência.",
        ST["body"]
    ))
    story.append(Spacer(1, 6))

    r_hdr = [
        Paragraph("#",           ST["th"]),
        Paragraph("Nome",        ST["th_l"]),
        Paragraph("Prefeitura",  ST["th_l"]),
        Paragraph("Regime",      ST["th"]),
        Paragraph("Emp. Disp.", ST["th"]),
        Paragraph("Concorr.",    ST["th"]),
        Paragraph("Cart. Disp.",ST["th"]),
        Paragraph("Oportunidade",ST["th_l"]),
    ]
    r_rows = [r_hdr]
    for idx, r in enumerate(resultados[:50], 1):
        opp_cor = COR_OPP_ESC.get(r.get("oportunidade",""),"#374151")
        conc_s  = fmt(r.get("total_concorrentes",0)) if r.get("qt_concorrentes",0)>0 else "—"
        emp_s   = fmt(r.get("emp_disp",0))           if r.get("emp_disp",0)>0        else "—"
        cc_s    = fmt(r.get("cc_disp",0))            if r.get("cc_disp",0)>0         else "—"
        r_rows.append([
            Paragraph(str(idx),                    ST["td_c"]),
            Paragraph(r.get("nome","")[:22],       ST["td_b"]),
            Paragraph(r.get("prefeitura","")[:20], ST["td"]),
            Paragraph(r.get("regime","")[:12],     ST["td_c"]),
            Paragraph(emp_s,  ST["td_r"]),
            Paragraph(conc_s, ST["td_r"]),
            Paragraph(cc_s,   ST["td_r"]),
            Paragraph(
                f'<font color="{opp_cor}"><b>{r.get("oportunidade","")}</b></font>',
                ST["td"]
            ),
        ])
    rt = Table(
        r_rows,
        colWidths=[(W-3*cm)*f for f in [0.04,0.18,0.16,0.10,0.11,0.11,0.11,0.19]],
        repeatRows=1,
    )
    rt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  colors.HexColor("#7c3aed")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, colors.HexColor("#f9fafb")]),
        ("BOX",           (0,0),(-1,-1), 0.5, colors.HexColor("#e5e7eb")),
        ("INNERGRID",     (0,0),(-1,-1), 0.3, colors.HexColor("#e5e7eb")),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 5),
        ("RIGHTPADDING",  (0,0),(-1,-1), 5),
        ("FONTSIZE",      (0,0),(-1,-1), 7.5),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(rt)

    if len(resultados)>50:
        story.append(Spacer(1,4))
        story.append(Paragraph(
            f"<i>Exibindo os 50 primeiros de {len(resultados)} servidores.</i>",
            ST["caption"]
        ))

    # ── rodapé ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.2*cm))
    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor("#e5e7eb")))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Relatório gerado pelo StarCheck · Starbank Grupo · "
        f"{datetime.now().strftime('%d/%m/%Y às %H:%M')} · Confidencial — uso interno.",
        ST["rodape"]
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()

def render_dashboard_lote(resultados: list):
    """Renderiza o dashboard inteligente da análise em lote."""
    if not resultados:
        st.warning("Nenhum holerite processado com sucesso.")
        return

    total   = len(resultados)
    com_emp = [r for r in resultados if r["emp_disp"] > 0]
    com_conc= [r for r in resultados if r["qt_concorrentes"] > 0]
    com_nos = [r for r in resultados if r["qt_nossos"] > 0]
    margem_total_disp = sum(r["emp_disp"] for r in com_emp)
    total_conc_mensal = sum(r["total_concorrentes"] for r in com_conc)

    # ── KPIs ────────────────────────────────────────────────────────────────
    st.markdown("<h3 class='section-header'>📊 Visão Geral do Lote</h3>", unsafe_allow_html=True)
    c1,c2,c3,c4,c5 = st.columns(5, gap="small")
    with c1: st.metric("👥 Servidores",            total)
    with c2: st.metric("💵 Com Margem Emp.",        len(com_emp),
                       delta=f"{len(com_emp)/total*100:.0f}% do lote" if total else None)
    with c3: st.metric("💳 Com Concorrente",        len(com_conc),
                       delta=fmt(total_conc_mensal) + "/mês")
    with c4: st.metric("🏆 Nossos Contratos",       len(com_nos))
    with c5: st.metric("💰 Margem Total Disponível", fmt(margem_total_disp))

    # ── Ranking de oportunidades ─────────────────────────────────────────────
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    st.markdown("<h3 class='section-header'>🎯 Ranking de Oportunidades</h3>", unsafe_allow_html=True)
    st.caption("Ordenado por prioridade de abordagem — do mais quente ao menos urgente.")

    # Tabs: Ranking / Por Prefeitura / Exportar
    tab_rank, tab_pref, tab_intel, tab_exp = st.tabs([
        "🏆 Ranking Individual", "🏛️ Por Prefeitura", "🔍 Inteligência de Mercado", "📥 Exportar"
    ])

    with tab_rank:
        # Filtros rápidos
        fc1, fc2, fc3 = st.columns([2,2,2])
        with fc1:
            filtro_opp = st.multiselect(
                "Oportunidade",
                options=sorted(set(r["oportunidade"] for r in resultados)),
                default=sorted(set(r["oportunidade"] for r in resultados)),
                key="lote_filtro_opp"
            )
        with fc2:
            filtro_pref = st.multiselect(
                "Prefeitura",
                options=sorted(set(r["prefeitura"] for r in resultados)),
                default=sorted(set(r["prefeitura"] for r in resultados)),
                key="lote_filtro_pref"
            )
        with fc3:
            busca = st.text_input("🔍 Buscar nome", key="lote_busca")

        filtrados = [r for r in resultados
                     if r["oportunidade"] in filtro_opp
                     and r["prefeitura"] in filtro_pref
                     and (not busca or busca.lower() in r["nome"].lower())]

        st.caption(f"Exibindo {len(filtrados)} de {total} servidores")

        # Paleta de cores por oportunidade
        _COR_OPP = {
            "🔥 Compra Dívida + Empréstimo": ("#fef3c7","#d97706","#92400e"),
            "💳 Compra de Dívida":           ("#dbeafe","#1d4ed8","#1e3a8a"),
            "💵 Empréstimo Disponível":      ("#dcfce7","#16a34a","#14532d"),
            "🔄 Refinanciamento":            ("#ede9fe","#7c3aed","#4c1d95"),
            "💵 Margem Disponível":          ("#f0fdf4","#059669","#065f46"),
            "❓ Prefeitura Não Mapeada":     ("#f3f4f6","#6b7280","#374151"),
            "⛔ Margem Lotada":              ("#fef2f2","#dc2626","#991b1b"),
        }

        for idx, r in enumerate(filtrados):
            bg, cor_borda, cor_txt = _COR_OPP.get(r["oportunidade"], ("#ffffff","#e5e7eb","#374151"))
            nome_curto = r["nome"].split()[0].capitalize() if r["nome"] else "N/A"
            emp_disp_str = fmt(r["emp_disp"]) if r["emp_disp"] > 0 else "—"
            cc_disp_str  = fmt(r["cc_disp"])  if r["cc_disp"]  > 0 else "—"

            # Tags de consignações
            tags = []
            if r["qt_concorrentes"] > 0:
                tags.append(f'<span style="background:#dbeafe;color:#1d4ed8;padding:.15rem .5rem;border-radius:99px;font-size:.7rem;font-weight:700;">'
                            f'💳 {r["qt_concorrentes"]} concorrente(s) · {fmt(r["total_concorrentes"])}/mês</span>')
            if r["qt_nossos"] > 0:
                tags.append(f'<span style="background:#dcfce7;color:#15803d;padding:.15rem .5rem;border-radius:99px;font-size:.7rem;font-weight:700;">'
                            f'🏆 {r["qt_nossos"]} nosso(s)</span>')
            if r["total_emprestimos"] > 0:
                tags.append(f'<span style="background:#fef3c7;color:#92400e;padding:.15rem .5rem;border-radius:99px;font-size:.7rem;font-weight:700;">'
                            f'🏦 Emp. {fmt(r["total_emprestimos"])}/mês</span>')
            tags_html = "&nbsp;".join(tags) if tags else '<span style="color:#9ca3af;font-size:.7rem;">Sem consignações</span>'

            card_html = f"""
<div style="background:{bg};border-left:4px solid {cor_borda};border-radius:.5rem;
     padding:.75rem 1rem;margin:.4rem 0;display:flex;align-items:center;gap:1rem;
     border:1px solid {cor_borda}40;">
  <div style="min-width:24px;height:24px;background:{cor_borda};color:white;
       border-radius:50%;display:flex;align-items:center;justify-content:center;
       font-size:.65rem;font-weight:800;flex-shrink:0;">{idx+1}</div>
  <div style="flex:1;min-width:0;">
    <div style="display:flex;align-items:center;gap:.75rem;flex-wrap:wrap;">
      <span style="font-weight:700;color:{cor_txt};font-size:.9rem;">{r["nome"]}</span>
      <span style="font-size:.7rem;color:#6b7280;background:#f3f4f6;padding:.1rem .45rem;border-radius:99px;">{r["prefeitura"][:25]}</span>
      <span style="font-size:.7rem;color:#6b7280;">{r["regime"][:15]}</span>
    </div>
    <div style="margin-top:.3rem;">{tags_html}</div>
  </div>
  <div style="display:flex;gap:1.5rem;flex-shrink:0;text-align:right;">
    <div>
      <div style="font-size:.62rem;color:#9ca3af;text-transform:uppercase;letter-spacing:.06em;">Emp. Disp.</div>
      <div style="font-weight:700;font-size:.88rem;color:{'#16a34a' if r['emp_disp']>0 else '#dc2626'};">{emp_disp_str}</div>
    </div>
    <div>
      <div style="font-size:.62rem;color:#9ca3af;text-transform:uppercase;letter-spacing:.06em;">Cart. Disp.</div>
      <div style="font-weight:700;font-size:.88rem;color:{'#1d4ed8' if r['cc_disp']>0 else '#dc2626'};">{cc_disp_str}</div>
    </div>
    <div>
      <div style="font-size:.62rem;color:#9ca3af;text-transform:uppercase;letter-spacing:.06em;">Líquido</div>
      <div style="font-weight:700;font-size:.88rem;color:#374151;">{fmt(r['liquido'])}</div>
    </div>
    <div style="min-width:160px;">
      <div style="font-size:.62rem;color:#9ca3af;text-transform:uppercase;letter-spacing:.06em;">Oportunidade</div>
      <div style="font-weight:700;font-size:.82rem;color:{cor_txt};">{r['oportunidade']}</div>
    </div>
  </div>
</div>"""
            st.markdown(card_html, unsafe_allow_html=True)

            # Expandir detalhes completos (igual à análise individual)
            with st.expander(f"🔍 Ver análise completa de {nome_curto}", expanded=False):
                render_resultado_sem_chat(r["_dados"])

    with tab_pref:
        import plotly.graph_objects as go

        # ── Agregar métricas por prefeitura ──────────────────────────────────
        pref_map: dict = {}
        for r in resultados:
            p = r["prefeitura"] or "Desconhecida"
            if p not in pref_map:
                pref_map[p] = {
                    "servidores": 0,
                    "emp_disp_total": 0.0,
                    "emp_total_permitido": 0.0,
                    "conc_total": 0.0,
                    "qt_conc": 0,
                    "qt_nossos": 0,
                    "qt_nao_comp": 0,
                    "liquido_total": 0.0,
                    "base_total": 0.0,
                    "qt_margem_disp": 0,
                    "qt_margem_lotada": 0,
                    "qt_sem_margem_info": 0,
                    "oportunidades": [],
                }
            v = pref_map[p]
            v["servidores"]          += 1
            v["emp_disp_total"]      += max(r["emp_disp"], 0)
            v["emp_total_permitido"] += max(r["emp_total"], 0)
            v["conc_total"]          += r["total_concorrentes"]
            v["qt_conc"]             += r["qt_concorrentes"]
            v["qt_nossos"]           += r["qt_nossos"]
            v["qt_nao_comp"]         += r["qt_nao_comp"]
            v["liquido_total"]       += r["liquido"]
            v["base_total"]          += r["base_calculo"]
            if not r["margem_ok"]:
                v["qt_sem_margem_info"] += 1
            elif r["emp_disp"] > 0:
                v["qt_margem_disp"]  += 1
            else:
                v["qt_margem_lotada"] += 1
            v["oportunidades"].append(r["oportunidade"])

        pref_sorted = sorted(pref_map.items(),
                             key=lambda x: x[1]["emp_disp_total"], reverse=True)
        if not pref_sorted:
            st.info("Nenhuma prefeitura identificada.")
        else:
            pnames = [p[:28] for p,_ in pref_sorted]
            pemp_d = [v["emp_disp_total"]      for _,v in pref_sorted]
            pemp_t = [v["emp_total_permitido"]  for _,v in pref_sorted]
            pconc  = [v["conc_total"]            for _,v in pref_sorted]
            pnosso = [v["qt_nossos"]             for _,v in pref_sorted]
            pserv  = [v["servidores"]            for _,v in pref_sorted]

            # ── Gráfico 1 — Margem disponível vs permitida (fácil ver quanto já foi usado) ──
            st.markdown("##### 💰 Margem de Empréstimo: Disponível vs Utilizada")
            fig1 = go.Figure()
            fig1.add_bar(
                name="Já Comprometido",
                x=pnames,
                y=[t - d for t, d in zip(pemp_t, pemp_d)],
                marker_color="#f97316",
                text=[fmt(t - d) for t, d in zip(pemp_t, pemp_d)],
                textposition="inside", textfont_color="white", textfont_size=10,
            )
            fig1.add_bar(
                name="Disponível",
                x=pnames,
                y=[max(d, 0) for d in pemp_d],
                marker_color="#7c3aed",
                text=[fmt(d) if d > 0 else "" for d in pemp_d],
                textposition="inside", textfont_color="white", textfont_size=10,
            )
            fig1.update_layout(
                barmode="stack", height=320,
                margin=dict(t=10, b=10, l=0, r=0),
                legend=dict(orientation="h", y=-0.22, font_size=11),
                plot_bgcolor="white", paper_bgcolor="white",
                yaxis=dict(tickprefix="R$ ", gridcolor="#f3f4f6", tickfont_size=11),
                xaxis=dict(tickfont_size=11),
            )
            st.plotly_chart(fig1, use_container_width=True)

            # ── Gráfico 2 — Oportunidade concorrente (quanto saindo p/ outras instituições) ──
            st.markdown("##### 💳 Cartões Concorrentes — Volume Mensal Saindo da Folha")
            fig2 = go.Figure()
            fig2.add_bar(
                name="Concorrentes R$/mês",
                x=pnames, y=pconc,
                marker_color="#1d4ed8",
                text=[fmt(c) if c > 0 else "" for c in pconc],
                textposition="outside", textfont_size=10,
            )
            fig2.update_layout(
                height=260,
                margin=dict(t=10, b=10, l=0, r=0),
                plot_bgcolor="white", paper_bgcolor="white",
                yaxis=dict(tickprefix="R$ ", gridcolor="#f3f4f6", tickfont_size=11),
                xaxis=dict(tickfont_size=11),
                showlegend=False,
            )
            st.plotly_chart(fig2, use_container_width=True)

            # ── Gráfico 3 — Pizza: distribuição de oportunidades ──
            col_pie1, col_pie2 = st.columns(2)
            with col_pie1:
                st.markdown("##### 🎯 Distribuição de Oportunidades")
                from collections import Counter
                todas_opp = [r["oportunidade"] for r in resultados]
                opp_count = Counter(todas_opp)
                _COR_PIE = {
                    "🔥 Compra Dívida + Empréstimo": "#d97706",
                    "💳 Compra de Dívida":           "#1d4ed8",
                    "💵 Empréstimo Disponível":      "#16a34a",
                    "🔄 Refinanciamento":            "#7c3aed",
                    "💵 Margem Disponível":          "#059669",
                    "❓ Prefeitura Não Mapeada":     "#6b7280",
                    "⛔ Margem Lotada":              "#dc2626",
                }
                cores_pie = [_COR_PIE.get(k, "#94a3b8") for k in opp_count.keys()]
                fig_pie = go.Figure(go.Pie(
                    labels=list(opp_count.keys()),
                    values=list(opp_count.values()),
                    marker_colors=cores_pie,
                    hole=0.45,
                    textinfo="value+percent",
                    textfont_size=11,
                ))
                fig_pie.update_layout(
                    height=280, margin=dict(t=10,b=10,l=0,r=0),
                    legend=dict(font_size=10, orientation="v"),
                    paper_bgcolor="white",
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            with col_pie2:
                st.markdown("##### 📊 Status de Margem por Prefeitura")
                # Stacked bar: margem disp / lotada / sem info
                p_disp  = [v["qt_margem_disp"]     for _,v in pref_sorted]
                p_lot   = [v["qt_margem_lotada"]    for _,v in pref_sorted]
                p_sem   = [v["qt_sem_margem_info"]  for _,v in pref_sorted]
                fig_st  = go.Figure()
                fig_st.add_bar(name="✅ Margem Disponível", x=pnames, y=p_disp,
                               marker_color="#16a34a")
                fig_st.add_bar(name="⛔ Margem Lotada",     x=pnames, y=p_lot,
                               marker_color="#dc2626")
                fig_st.add_bar(name="❓ Sem Mapeamento",    x=pnames, y=p_sem,
                               marker_color="#9ca3af")
                fig_st.update_layout(
                    barmode="stack", height=280,
                    margin=dict(t=10,b=10,l=0,r=0),
                    legend=dict(orientation="h", y=-0.3, font_size=10),
                    plot_bgcolor="white", paper_bgcolor="white",
                    yaxis=dict(title="Servidores", gridcolor="#f3f4f6", tickfont_size=10),
                    xaxis=dict(tickfont_size=10),
                )
                st.plotly_chart(fig_st, use_container_width=True)

            # ── Cards analíticos por prefeitura ──────────────────────────────
            st.markdown("<hr style='border-color:#f3f4f6;margin:1.5rem 0;'>",
                        unsafe_allow_html=True)
            st.markdown("##### 🏛️ Análise Detalhada por Prefeitura")

            for pref, v in pref_sorted:
                pct_disp  = v["qt_margem_disp"]  / v["servidores"] * 100 if v["servidores"] else 0
                pct_conc  = v["qt_conc"] / (v["servidores"] * max(v["qt_conc"] + 1, 1)) * 100
                ticket_medio = v["emp_disp_total"] / v["qt_margem_disp"] if v["qt_margem_disp"] else 0
                media_liq    = v["liquido_total"] / v["servidores"] if v["servidores"] else 0

                # Insight automático
                if v["qt_conc"] > 0 and v["emp_disp_total"] > 500:
                    insight_txt = f"🔥 Alto potencial: {v['qt_conc']} contrato(s) concorrente(s) + {fmt(v['emp_disp_total'])} de margem livre. Priorizar abordagem combinada."
                    insight_cor = "#92400e"; insight_bg = "#fef3c7"
                elif v["qt_conc"] > 0:
                    insight_txt = f"💳 {v['qt_conc']} contrato(s) concorrente(s) totalizando {fmt(v['conc_total'])}/mês — foco em Compra de Dívida."
                    insight_cor = "#1e3a8a"; insight_bg = "#dbeafe"
                elif v["emp_disp_total"] > 500:
                    insight_txt = f"💵 {fmt(v['emp_disp_total'])} de margem de empréstimo disponível — {v['qt_margem_disp']} servidor(es) elegíveis."
                    insight_cor = "#14532d"; insight_bg = "#dcfce7"
                elif v["qt_nossos"] > 0:
                    insight_txt = f"🔄 {v['qt_nossos']} contrato(s) nosso(s) ativo(s) — verificar refinanciamento."
                    insight_cor = "#4c1d95"; insight_bg = "#ede9fe"
                else:
                    insight_txt = "⛔ Margem comprometida ou prefeitura não mapeada. Abordar com produtos de curto prazo."
                    insight_cor = "#991b1b"; insight_bg = "#fef2f2"

                # Barra de progresso de aproveitamento
                pct_uso = (1 - v["emp_disp_total"] / v["emp_total_permitido"]) * 100 if v["emp_total_permitido"] > 0 else 100
                pct_uso = min(max(pct_uso, 0), 100)
                bar_fill = "#dc2626" if pct_uso > 80 else "#f97316" if pct_uso > 50 else "#16a34a"

                st.markdown(f"""
<div style="background:#fff;border:1px solid #e5e7eb;border-radius:.75rem;
     padding:1.1rem 1.25rem;margin:.6rem 0;
     box-shadow:0 2px 8px rgba(0,0,0,.04);">
  <div style="display:flex;align-items:center;justify-content:space-between;
       margin-bottom:.75rem;">
    <div>
      <span style="font-weight:800;color:#111827;font-size:.95rem;">{pref}</span>
      <span style="margin-left:.75rem;background:#f3f4f6;color:#6b7280;
           font-size:.7rem;padding:.15rem .55rem;border-radius:99px;font-weight:600;">
        {v['servidores']} servidor(es)
      </span>
    </div>
    <span style="font-size:.75rem;color:#6b7280;">
      Líquido médio: <strong style="color:#111827;">{fmt(media_liq)}</strong>
    </span>
  </div>

  <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:.75rem;
       margin-bottom:.85rem;">
    <div style="text-align:center;">
      <div style="font-size:.62rem;color:#9ca3af;text-transform:uppercase;
           letter-spacing:.07em;margin-bottom:.2rem;">Emp. Disponível</div>
      <div style="font-weight:800;font-size:1rem;
           color:{'#16a34a' if v['emp_disp_total']>0 else '#dc2626'};">
        {fmt(v["emp_disp_total"])}
      </div>
    </div>
    <div style="text-align:center;">
      <div style="font-size:.62rem;color:#9ca3af;text-transform:uppercase;
           letter-spacing:.07em;margin-bottom:.2rem;">Ticket Médio</div>
      <div style="font-weight:800;font-size:1rem;color:#7c3aed;">
        {fmt(ticket_medio) if ticket_medio else "—"}
      </div>
    </div>
    <div style="text-align:center;">
      <div style="font-size:.62rem;color:#9ca3af;text-transform:uppercase;
           letter-spacing:.07em;margin-bottom:.2rem;">Concorrentes</div>
      <div style="font-weight:800;font-size:1rem;color:#1d4ed8;">
        {v["qt_conc"]} · {fmt(v["conc_total"])}/mês
      </div>
    </div>
    <div style="text-align:center;">
      <div style="font-size:.62rem;color:#9ca3af;text-transform:uppercase;
           letter-spacing:.07em;margin-bottom:.2rem;">Nossos</div>
      <div style="font-weight:800;font-size:1rem;color:#059669;">
        {v["qt_nossos"]} contrato(s)
      </div>
    </div>
    <div style="text-align:center;">
      <div style="font-size:.62rem;color:#9ca3af;text-transform:uppercase;
           letter-spacing:.07em;margin-bottom:.2rem;">Com Margem</div>
      <div style="font-weight:800;font-size:1rem;color:#374151;">
        {v["qt_margem_disp"]}/{v["servidores"]} ({pct_disp:.0f}%)
      </div>
    </div>
  </div>

  <div style="margin-bottom:.7rem;">
    <div style="display:flex;justify-content:space-between;
         font-size:.68rem;color:#6b7280;margin-bottom:.25rem;">
      <span>Uso da margem de empréstimo</span>
      <span>{pct_uso:.0f}% comprometida</span>
    </div>
    <div style="height:6px;background:#f3f4f6;border-radius:99px;overflow:hidden;">
      <div style="height:100%;width:{pct_uso:.0f}%;background:{bar_fill};
           border-radius:99px;transition:width .4s;"></div>
    </div>
  </div>

  <div style="background:{insight_bg};border-left:3px solid {insight_cor};
       border-radius:0 .4rem .4rem 0;padding:.5rem .85rem;
       font-size:.8rem;color:{insight_cor};font-weight:600;">
    {insight_txt}
  </div>
</div>""", unsafe_allow_html=True)

    with tab_intel:
        from collections import defaultdict
        import plotly.graph_objects as go

        # ── COLETA E AGREGAÇÃO ───────────────────────────────────────────────────
        inst_data: dict = defaultdict(lambda: {
            "contratos": 0, "valor": 0.0, "servidores": set(), "tipo": ""
        })
        for idx_r, r in enumerate(resultados):
            d = r.get("_dados", {})
            for c in d.get("cartoes", []):
                desc  = str(c.get("descricao", "")).strip()
                tipo  = c.get("tipo", "desconhecido")
                valor = _abs_val(c.get("valor", 0))
                if not desc or valor <= 0: continue
                inst_data[desc]["contratos"]    += 1
                inst_data[desc]["valor"]        += valor
                inst_data[desc]["tipo"]          = tipo
                inst_data[desc]["servidores"].add(idx_r)
            for e in d.get("emprestimos", []):
                desc  = str(e.get("descricao", "")).strip()
                valor = _abs_val(e.get("valor", 0))
                if not desc or valor <= 0: continue
                tipo_emp = "nosso" if any(
                    p.upper() in desc.upper() for p in NOSSOS_PRODUTOS
                ) else "emprestimo"
                inst_data[desc]["contratos"]    += 1
                inst_data[desc]["valor"]        += valor
                inst_data[desc]["tipo"]          = tipo_emp
                inst_data[desc]["servidores"].add(idx_r)

        inst_list = sorted([
            {
                "desc":         k,
                "contratos":    v["contratos"],
                "valor":        v["valor"],
                "servidores":   len(v["servidores"]),
                "tipo":         v["tipo"],
                "ticket_medio": v["valor"] / v["contratos"] if v["contratos"] > 0 else 0,
            }
            for k, v in inst_data.items()
        ], key=lambda x: x["valor"], reverse=True)

        # Totais por tipo
        total_nosso_val  = sum(i["valor"] for i in inst_list if i["tipo"] == "nosso")
        total_conc_val   = sum(i["valor"] for i in inst_list if i["tipo"] == "concorrente")
        total_naocomp_val= sum(i["valor"] for i in inst_list if i["tipo"] == "nao_comprado")
        total_emp_val    = sum(i["valor"] for i in inst_list if i["tipo"] == "emprestimo")
        total_desc_val   = sum(i["valor"] for i in inst_list if i["tipo"] == "desconhecido")
        total_consig_val = total_nosso_val + total_conc_val + total_naocomp_val + total_emp_val + total_desc_val

        n_nossos_ct = sum(r["qt_nossos"]        for r in resultados)
        n_conc_ct   = sum(r["qt_concorrentes"]  for r in resultados)
        n_ncomp_ct  = sum(r["qt_nao_comp"]      for r in resultados)
        n_desc_ct   = sum(r["qt_desconhec"]     for r in resultados)
        n_emp_ct    = sum(len(r.get("_emprestimos", [])) for r in resultados)
        total_ct    = n_nossos_ct + n_conc_ct + n_ncomp_ct + n_desc_ct + n_emp_ct

        pct_nosso   = (total_nosso_val / total_consig_val * 100) if total_consig_val > 0 else 0
        pct_conc    = (total_conc_val  / total_consig_val * 100) if total_consig_val > 0 else 0

        sem_consig       = [r for r in resultados
                            if r["total_cartoes"] == 0 and r["total_emprestimos"] == 0]
        so_nosso         = [r for r in resultados
                            if r["qt_nossos"] > 0 and r["qt_concorrentes"] == 0]
        so_conc          = [r for r in resultados
                            if r["qt_nossos"] == 0 and r["qt_concorrentes"] > 0]
        misto            = [r for r in resultados
                            if r["qt_nossos"] > 0 and r["qt_concorrentes"] > 0]
        alvo_puro        = so_conc
        margem_disp_total= sum(r["emp_disp"] for r in resultados if r["emp_disp"] > 0)

        taxa_penet = (len([r for r in resultados if r["qt_nossos"] > 0]) / total * 100) if total > 0 else 0

        def faixa_sal(v):
            if v < 2000:  return "< R$2k"
            if v < 3000:  return "R$2k–3k"
            if v < 5000:  return "R$3k–5k"
            if v < 8000:  return "R$5k–8k"
            if v < 12000: return "R$8k–12k"
            return "> R$12k"

        _ORDEM_FAIXAS = ["< R$2k","R$2k–3k","R$3k–5k","R$5k–8k","R$8k–12k","> R$12k"]
        from collections import Counter
        faixas  = Counter(faixa_sal(r["salario_base"]) for r in resultados)
        regimes = Counter(r["regime"] for r in resultados)

        _COR_TIPO = {
            "nosso":       "#7c3aed",
            "concorrente": "#1d4ed8",
            "nao_comprado":"#be185d",
            "emprestimo":  "#d97706",
            "desconhecido":"#6b7280",
        }

        # ── HEADER ───────────────────────────────────────────────────────────────
        st.markdown("""
        <div style="background: linear-gradient(135deg, #4C1D95 0%, #7C3AED 60%, #8B5CF6 100%);
            border-radius: 1.25rem;
            padding: 2.5rem 2rem 2rem 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 8px 30px rgba(124, 58, 237, 0.25);">
        <h2 style="color: white;margin:0;font-size:1.35rem;">Inteligência de Mercado</h2>
        <p style="color: white;margin:.3rem 0 0;font-size:.83rem;">
            Análise estratégica baseada nos holerites processados — market share, 
            mapa competitivo, perfil de cliente e oportunidades para gestão e liderança.
        </p>
        </div>
        """, unsafe_allow_html=True)

        # ── KPIs ESTRATÉGICOS ─────────────────────────────────────────────────────
        st.markdown("##### 📌 Indicadores Estratégicos")
        k1,k2,k3,k4,k5,k6 = st.columns(6)
        with k1: st.metric("💰 Volume Consig./Mês",  fmt(total_consig_val),
                            help="Total mensal saindo em todas as consignações da folha")
        with k2: st.metric("🏆 Nossa Receita/Mês",   fmt(total_nosso_val),
                            delta=f"{pct_nosso:.1f}% do mercado")
        with k3: st.metric("💳 Volume Concorrentes", fmt(total_conc_val),
                            delta=f"{pct_conc:.1f}% do mercado", delta_color="inverse")
        with k4: st.metric("📈 Nossa Penetração",    f"{taxa_penet:.0f}%",
                            help="% de servidores com ao menos um produto nosso")
        with k5: st.metric("🎯 Alvo Puro (sem nós)", len(alvo_puro),
                            help="Servidores com só concorrente — máxima prioridade")
        with k6: st.metric("🌱 Mercado Novo",       len(sem_consig),
                            help="Sem nenhuma consignação ativa")

        st.markdown("<hr style='border-color:#f3f4f6;margin:1rem 0;'>", unsafe_allow_html=True)

        # ── MARKET SHARE ─────────────────────────────────────────────────────────
        st.markdown("##### Market Share")
        ms1, ms2 = st.columns(2)

        with ms1:
            st.markdown("**Por Volume Mensal (R$)**")
            if total_consig_val > 0:
                ms_l, ms_v, ms_c = [], [], []
                for label, val, cor in [
                    ("Starbank (Nossos)", total_nosso_val,   "#7c3aed"),
                    ("Concorrentes",      total_conc_val,    "#1d4ed8"),
                    ("Não Compramos",     total_naocomp_val, "#be185d"),
                    ("Empréstimos",       total_emp_val,     "#d97706"),
                    ("Não Identificados", total_desc_val,    "#6b7280"),
                ]:
                    if val > 0:
                        ms_l.append(label); ms_v.append(val); ms_c.append(cor)

                fig_ms = go.Figure(go.Pie(
                    labels=ms_l, values=ms_v, marker_colors=ms_c,
                    hole=0.5, textinfo="label+percent", textfont_size=10,
                    hovertemplate="%{label}<br>%{value:,.2f}/mês<br>%{percent}<extra></extra>",
                ))
                fig_ms.update_layout(
                    height=300, margin=dict(t=10,b=10,l=0,r=0),
                    legend=dict(font_size=9, orientation="h", y=-0.2),
                    paper_bgcolor="white",
                    annotations=[dict(
                        text=f"R${total_consig_val/1000:.1f}k<br>/mês",
                        x=0.5, y=0.5, showarrow=False,
                        font_size=11, font_color="#374151"
                    )]
                )
                st.plotly_chart(fig_ms, use_container_width=True)
            else:
                st.info("Nenhuma consignação identificada.")

        with ms2:
            st.markdown("**Por Número de Contratos**")
            if total_ct > 0:
                ct_l, ct_v, ct_c = [], [], []
                for label, val, cor in [
                    ("Starbank (Nossos)", n_nossos_ct, "#7c3aed"),
                    ("Concorrentes",      n_conc_ct,   "#1d4ed8"),
                    ("Não Compramos",     n_ncomp_ct,  "#be185d"),
                    ("Empréstimos",       n_emp_ct,    "#d97706"),
                    ("Não Identificados", n_desc_ct,   "#6b7280"),
                ]:
                    if val > 0:
                        ct_l.append(label); ct_v.append(val); ct_c.append(cor)

                fig_ct = go.Figure(go.Pie(
                    labels=ct_l, values=ct_v, marker_colors=ct_c,
                    hole=0.5, textinfo="label+percent", textfont_size=10,
                    hovertemplate="%{label}<br>%{value} contrato(s)<br>%{percent}<extra></extra>",
                ))
                fig_ct.update_layout(
                    height=300, margin=dict(t=10,b=10,l=0,r=0),
                    legend=dict(font_size=9, orientation="h", y=-0.2),
                    paper_bgcolor="white",
                    annotations=[dict(
                        text=f"{total_ct}<br>contratos",
                        x=0.5, y=0.5, showarrow=False,
                        font_size=11, font_color="#374151"
                    )]
                )
                st.plotly_chart(fig_ct, use_container_width=True)

        st.markdown("<hr style='border-color:#f3f4f6;margin:1rem 0;'>", unsafe_allow_html=True)

        # ── MAPA COMPETITIVO ──────────────────────────────────────────────────────
        st.markdown("##### Mapa Competitivo — Instituições Presentes na Folha")

        if inst_list:
            top15 = inst_list[:15]
            fig_comp = go.Figure(go.Bar(
                y=[i["desc"][:24] for i in top15][::-1],
                x=[i["valor"]     for i in top15][::-1],
                orientation="h",
                marker_color=[_COR_TIPO.get(i["tipo"],"#6b7280") for i in top15][::-1],
                text=[fmt(i["valor"]) for i in top15][::-1],
                textposition="outside",
                textfont_size=10,
            ))
            fig_comp.update_layout(
                height=max(300, len(top15)*32 + 80),
                margin=dict(t=10,b=10,l=0,r=90),
                plot_bgcolor="white", paper_bgcolor="white",
                xaxis=dict(tickprefix="R$ ", gridcolor="#f3f4f6", tickfont_size=10),
                yaxis=dict(tickfont_size=10),
                showlegend=False,
            )
            st.plotly_chart(fig_comp, use_container_width=True)

            # Legenda
            st.markdown("""
            <div style="display:flex;gap:1.25rem;flex-wrap:wrap;font-size:.74rem;margin-bottom:.75rem;">
            <span><span style="display:inline-block;width:10px;height:10px;background:#7c3aed;border-radius:2px;margin-right:4px;"></span>Nossos</span>
            <span><span style="display:inline-block;width:10px;height:10px;background:#1d4ed8;border-radius:2px;margin-right:4px;"></span>Concorrentes</span>
            <span><span style="display:inline-block;width:10px;height:10px;background:#be185d;border-radius:2px;margin-right:4px;"></span>Não Compramos</span>
            <span><span style="display:inline-block;width:10px;height:10px;background:#d97706;border-radius:2px;margin-right:4px;"></span>Empréstimos</span>
            <span><span style="display:inline-block;width:10px;height:10px;background:#6b7280;border-radius:2px;margin-right:4px;"></span>Não Identificados</span>
            </div>
            """, unsafe_allow_html=True)

            # Tabela detalhada
            with st.expander("📋 Ver tabela detalhada por instituição", expanded=False):
                header_html = (
                    '<div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr 1fr;'
                    'gap:4px;padding:7px 10px;background:#f8f7ff;border-radius:6px 6px 0 0;'
                    'font-size:.71rem;font-weight:700;color:#5b21b6;text-transform:uppercase;letter-spacing:.04em;">'
                    '<span>Instituição</span>'
                    '<span style="text-align:center;">Tipo</span>'
                    '<span style="text-align:right;">Vol./Mês</span>'
                    '<span style="text-align:center;">Contratos</span>'
                    '<span style="text-align:center;">Servidores</span>'
                    '<span style="text-align:right;">Ticket Médio</span>'
                    '</div>'
                )
                rows_html = ""
                tipo_label = {
                    "nosso":"Nosso","concorrente":"Concorrente",
                    "nao_comprado":"Não Compramos","emprestimo":"Empréstimo","desconhecido":"?"
                }
                for idx_i, inst in enumerate(inst_list):
                    bg  = "#fafafa" if idx_i % 2 == 0 else "#ffffff"
                    cor = _COR_TIPO.get(inst["tipo"],"#6b7280")
                    pct = (inst["valor"] / total_consig_val * 100) if total_consig_val > 0 else 0
                    rows_html += (
                        f'<div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr 1fr;'
                        f'gap:4px;padding:6px 10px;background:{bg};border-left:3px solid {cor};font-size:.81rem;">'
                        f'<span style="font-weight:600;color:#111827;">{inst["desc"][:30]}</span>'
                        f'<span style="text-align:center;"><span style="background:{cor}22;color:{cor};'
                        f'padding:.1rem .4rem;border-radius:99px;font-size:.68rem;font-weight:700;">'
                        f'{tipo_label.get(inst["tipo"],"?")}</span></span>'
                        f'<span style="text-align:right;color:#dc2626;font-weight:700;">{fmt(inst["valor"])}</span>'
                        f'<span style="text-align:center;color:#374151;">{inst["contratos"]}</span>'
                        f'<span style="text-align:center;color:#374151;">{inst["servidores"]}</span>'
                        f'<span style="text-align:right;color:#374151;">{fmt(inst["ticket_medio"])}</span>'
                        f'</div>'
                    )
                st.markdown(
                    f'<div style="border:1px solid #e5e7eb;border-radius:6px;overflow:hidden;">'
                    f'{header_html}{rows_html}</div>',
                    unsafe_allow_html=True
                )

        st.markdown("<hr style='border-color:#f3f4f6;margin:1rem 0;'>", unsafe_allow_html=True)

        # ── SEGMENTAÇÃO DE CLIENTES ───────────────────────────────────────────────
        st.markdown("##### Segmentação da Base de Clientes")
        seg1, seg2 = st.columns(2)

        with seg1:
            st.markdown("**Perfil de Relacionamento Consignado**")
            seg_l, seg_v, seg_c = [], [], []
            for label, grupo, cor in [
                ("🌱 Sem Consignações",      sem_consig, "#059669"),
                ("🏆 Só Nossos Produtos",    so_nosso,   "#7c3aed"),
                ("🎯 Só Concorrentes",       so_conc,    "#1d4ed8"),
                ("🔀 Nossos + Concorrentes", misto,      "#d97706"),
            ]:
                n = total - len(sem_consig) - len(so_nosso) - len(so_conc) - len(misto)
                if len(grupo) > 0:
                    seg_l.append(label); seg_v.append(len(grupo)); seg_c.append(cor)
            outros_n = total - len(sem_consig) - len(so_nosso) - len(so_conc) - len(misto)
            if outros_n > 0:
                seg_l.append("❓ Outros"); seg_v.append(outros_n); seg_c.append("#9ca3af")

            if sum(seg_v) > 0:
                fig_seg = go.Figure(go.Pie(
                    labels=seg_l, values=seg_v, marker_colors=seg_c,
                    hole=0.42, textinfo="label+value+percent", textfont_size=10,
                ))
                fig_seg.update_layout(
                    height=290, margin=dict(t=5,b=5,l=0,r=0),
                    legend=dict(font_size=9, orientation="h", y=-0.22),
                    paper_bgcolor="white",
                )
                st.plotly_chart(fig_seg, use_container_width=True)

        with seg2:
            st.markdown("**Distribuição por Faixa Salarial**")
            faixa_ord = [(f, faixas.get(f, 0)) for f in _ORDEM_FAIXAS if faixas.get(f, 0) > 0]
            if faixa_ord:
                fx_l = [f[0] for f in faixa_ord]
                fx_v = [f[1] for f in faixa_ord]
                _CORES_FAIXA = ["#c4b5fd","#a78bfa","#8b5cf6","#7c3aed","#6d28d9","#5b21b6"]
                fig_fx = go.Figure(go.Bar(
                    x=fx_l, y=fx_v,
                    marker_color=_CORES_FAIXA[:len(fx_l)],
                    text=fx_v, textposition="outside", textfont_size=11,
                ))
                fig_fx.update_layout(
                    height=290, margin=dict(t=10,b=10,l=0,r=0),
                    plot_bgcolor="white", paper_bgcolor="white",
                    yaxis=dict(title="Servidores", gridcolor="#f3f4f6"),
                    showlegend=False,
                )
                st.plotly_chart(fig_fx, use_container_width=True)

        seg3, seg4 = st.columns(2)

        with seg3:
            st.markdown("**Distribuição por Regime**")
            if regimes:
                reg_l = list(regimes.keys()); reg_v = list(regimes.values())
                fig_reg = go.Figure(go.Bar(
                    x=reg_l, y=reg_v, marker_color="#7c3aed",
                    text=reg_v, textposition="outside", textfont_size=11,
                ))
                fig_reg.update_layout(
                    height=220, margin=dict(t=5,b=5,l=0,r=0),
                    plot_bgcolor="white", paper_bgcolor="white",
                    yaxis=dict(gridcolor="#f3f4f6"), showlegend=False,
                )
                st.plotly_chart(fig_reg, use_container_width=True)

        with seg4:
            st.markdown("**Taxa de Consignação por Faixa Salarial**")
            faixa_consig: dict = defaultdict(lambda: {"total": 0, "com_consig": 0})
            for r in resultados:
                f = faixa_sal(r["salario_base"])
                faixa_consig[f]["total"] += 1
                if r["total_cartoes"] > 0 or r["total_emprestimos"] > 0:
                    faixa_consig[f]["com_consig"] += 1

            fx_tc_l, fx_tc_v = [], []
            for f in _ORDEM_FAIXAS:
                if faixa_consig.get(f, {}).get("total", 0) > 0:
                    fx_tc_l.append(f)
                    fx_tc_v.append(round(
                        faixa_consig[f]["com_consig"] / faixa_consig[f]["total"] * 100, 1
                    ))
            if fx_tc_l:
                fig_tc = go.Figure(go.Bar(
                    x=fx_tc_l, y=fx_tc_v,
                    marker_color=["#f97316" if p > 70 else "#7c3aed" if p > 40 else "#a78bfa"
                                for p in fx_tc_v],
                    text=[f"{p:.0f}%" for p in fx_tc_v],
                    textposition="outside", textfont_size=11,
                ))
                fig_tc.update_layout(
                    height=220, margin=dict(t=5,b=5,l=0,r=0),
                    plot_bgcolor="white", paper_bgcolor="white",
                    yaxis=dict(title="%", gridcolor="#f3f4f6", range=[0, 115]),
                    showlegend=False,
                )
                st.plotly_chart(fig_tc, use_container_width=True)

        st.markdown("<hr style='border-color:#f3f4f6;margin:1rem 0;'>", unsafe_allow_html=True)

        # ── ANÁLISE DE PENETRAÇÃO ─────────────────────────────────────────────────
        st.markdown("##### Penetração dos Nossos Produtos")
        pen1, pen2 = st.columns(2)

        with pen1:
            st.markdown("**Presença por Produto (Volume e Contratos)**")
            prod_freq: dict = defaultdict(lambda: {"contratos": 0, "valor": 0.0, "servidores": set()})
            for idx_r, r in enumerate(resultados):
                d = r.get("_dados", {})
                for c in d.get("cartoes", []):
                    if c.get("tipo") != "nosso": continue
                    desc = str(c.get("descricao","")).upper()
                    matched = next((p for p in NOSSOS_PRODUTOS if p.upper() in desc), "OUTROS")
                    prod_freq[matched]["contratos"] += 1
                    prod_freq[matched]["valor"]     += _abs_val(c.get("valor", 0))
                    prod_freq[matched]["servidores"].add(idx_r)
                for e in d.get("emprestimos", []):
                    desc = str(e.get("descricao","")).upper()
                    matched = next((p for p in NOSSOS_PRODUTOS if p.upper() in desc), None)
                    if matched:
                        prod_freq[matched]["contratos"] += 1
                        prod_freq[matched]["valor"]     += _abs_val(e.get("valor", 0))
                        prod_freq[matched]["servidores"].add(idx_r)

            if prod_freq:
                p_names = list(prod_freq.keys())
                p_vals  = [prod_freq[p]["valor"]     for p in p_names]
                p_cts   = [prod_freq[p]["contratos"] for p in p_names]
                fig_prod = go.Figure()
                fig_prod.add_bar(
                    name="Volume R$/mês", x=p_names, y=p_vals,
                    marker_color="#7c3aed", yaxis="y1",
                    text=[fmt(v) for v in p_vals],
                    textposition="outside", textfont_size=9,
                )
                fig_prod.add_scatter(
                    name="Nº Contratos", x=p_names, y=p_cts,
                    mode="markers+text",
                    marker=dict(size=10, color="#f97316"),
                    text=p_cts, textposition="top center", textfont_size=11,
                    yaxis="y2",
                )
                fig_prod.update_layout(
                    height=280, margin=dict(t=10,b=10,l=0,r=40),
                    plot_bgcolor="white", paper_bgcolor="white",
                    yaxis=dict(title="R$/mês", tickprefix="R$ ", gridcolor="#f3f4f6"),
                    yaxis2=dict(title="Contratos", overlaying="y", side="right", showgrid=False),
                    legend=dict(font_size=10, orientation="h", y=-0.22),
                )
                st.plotly_chart(fig_prod, use_container_width=True)
            else:
                st.info("Nenhum produto nosso identificado nos holerites.")

        with pen2:
            st.markdown("**Funil de Oportunidade de Mercado**")
            com_nos_total    = len([r for r in resultados if r["qt_nossos"] > 0])
            sem_nos_com_conc = len([r for r in resultados if r["qt_nossos"] == 0 and r["qt_concorrentes"] > 0])
            sem_nos_com_emp  = len([r for r in resultados if r["qt_nossos"] == 0 and r["total_emprestimos"] > 0 and r["qt_concorrentes"] == 0])

            fig_fun = go.Figure(go.Funnel(
                y=["Total Servidores","Com Nossos Produtos","Alvo (só concorrente)","Empréstimo (sem nós)","Mercado Novo"],
                x=[total, com_nos_total, sem_nos_com_conc, sem_nos_com_emp, len(sem_consig)],
                textinfo="value+percent initial",
                marker_color=["#4c1d95","#7c3aed","#1d4ed8","#d97706","#059669"],
                textfont_size=11,
            ))
            fig_fun.update_layout(
                height=280, margin=dict(t=10,b=10,l=0,r=0),
                paper_bgcolor="white",
            )
            st.plotly_chart(fig_fun, use_container_width=True)

        st.markdown("<hr style='border-color:#f3f4f6;margin:1rem 0;'>", unsafe_allow_html=True)

    # ── INSIGHTS ESTRATÉGICOS (IA) ────────────────────────────────────────────
        st.markdown("##### 💡 Insights Estratégicos")

        opps = Counter(r.get("oportunidade","") for r in resultados)

        # Monta payload para a IA — dados agregados já calculados acima
        market_payload = {
            "total_servidores": total,
            "volume_consignado_mensal": round(total_consig_val, 2),
            "nossa_receita_mensal": round(total_nosso_val, 2),
            "volume_concorrentes_mensal": round(total_conc_val, 2),
            "pct_market_share_nosso": round(pct_nosso, 1),
            "pct_market_share_conc": round(pct_conc, 1),
            "taxa_penetracao_pct": round(taxa_penet, 1),
            "servidores_com_nossos": len([r for r in resultados if r["qt_nossos"] > 0]),
            "servidores_so_concorrente": len(so_conc),
            "servidores_sem_consignacao": len(sem_consig),
            "servidores_misto": len(misto),
            "margem_emp_disponivel_total": round(margem_disp_total, 2),
            "ticket_medio_nosso": round((total_nosso_val / n_nossos_ct) if n_nossos_ct > 0 else 0, 2),
            "ticket_medio_concorrente": round((total_conc_val / n_conc_ct) if n_conc_ct > 0 else 0, 2),
            "total_contratos_nossos": n_nossos_ct,
            "total_contratos_concorrentes": n_conc_ct,
            "total_contratos_nao_comprados": n_ncomp_ct,
            "prefeituras": {p: {"servidores": v["servidores"], "emp_disp": round(v["emp_disp_total"],2),
                                "conc_total": round(v["conc_total"],2), "qt_conc": v["qt_conc"]}
                            for p, v in pref_map.items()},
            "top5_instituicoes_concorrentes": [
                {"nome": i["desc"], "contratos": i["contratos"],
                 "volume_mensal": round(i["valor"],2), "ticket_medio": round(i["ticket_medio"],2)}
                for i in inst_list if i["tipo"] == "concorrente"
            ][:5],
            "top5_nossas_instituicoes": [
                {"nome": i["desc"], "contratos": i["contratos"], "volume_mensal": round(i["valor"],2)}
                for i in inst_list if i["tipo"] == "nosso"
            ][:5],
            "distribuicao_regimes": dict(regimes.most_common()),
            "distribuicao_oportunidades": dict(opps.most_common()),
        }

        if "insights_ia_lote" not in st.session_state:
            with st.spinner("✨ Stella gerando insights estratégicos..."):
                st.session_state["insights_ia_lote"] = gerar_insights_ia_mercado(market_payload)
        insights_ia = st.session_state["insights_ia_lote"]

        _COR_NIVEL = {
            "critico":     ("#fef2f2", "#dc2626"),
            "oportunidade":("#fef3c7", "#d97706"),
            "atencao":     ("#eff6ff", "#1d4ed8"),
            "positivo":    ("#f0fdf4", "#16a34a"),
        }

        if insights_ia:
            for ins in insights_ia:
                nivel = ins.get("nivel", "atencao")
                bg, borda = _COR_NIVEL.get(nivel, ("#f9fafb", "#6b7280"))
                st.markdown(f"""
<div style="background:{bg};border-left:4px solid {borda};
    border-radius:0 .65rem .65rem 0;padding:.9rem 1.15rem;margin:.5rem 0;
    box-shadow:0 1px 4px rgba(0,0,0,.04);">
  <div style="display:flex;align-items:flex-start;gap:.65rem;">
    <span style="font-size:1.1rem;flex-shrink:0;margin-top:.05rem;">{ins.get('icone','💡')}</span>
    <div>
      <div style="font-weight:700;color:#111827;font-size:.88rem;margin-bottom:.2rem;">
        {ins.get('titulo','')}
      </div>
      <div style="font-size:.83rem;color:#374151;line-height:1.65;">
        {ins.get('texto','')}
      </div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)
        else:
            st.info("Não foi possível gerar insights estratégicos. Verifique a API.")

        # Salva market_payload no session_state para o chat da Stella usar
        st.session_state["intel_mercado_payload"] = market_payload

            # ── BOTÃO DOWNLOAD PDF ────────────────────────────────────────────────
        st.markdown("<hr style='border-color:#f3f4f6;margin:1.5rem 0;'>", unsafe_allow_html=True)
        st.markdown("##### 📄 Exportar Análise Completa")

        col_pdf1, col_pdf2 = st.columns([2, 3])
        with col_pdf1:
            with st.spinner("Preparando PDF..."):
                try:
                    pdf_bytes = gerar_pdf_intel(
                        resultados,
                        st.session_state.get("insights_ia_lote", []),
                        market_payload
                    )
                    st.download_button(
                        label="📥 Baixar Relatório em PDF",
                        data=pdf_bytes,
                        file_name=f"intel_mercado_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )
                except Exception as e:
                    st.error(f"Erro ao gerar PDF: {e}. Verifique se kaleido está instalado.")
        with col_pdf2:
            st.caption(
                "PDF completo com capa, KPIs executivos, market share, "
                "mapa competitivo, análise por prefeitura, insights estratégicos da Stella "
                "e ranking de oportunidades."
            )

    with tab_exp:
        st.markdown("#### Exportar dados completos")
        # Monta DataFrame para exportação (sem objetos internos)
        export_rows = []
        for r in resultados:
            row = {k:v for k,v in r.items() if not k.startswith("_")}
            # Lista cartões concorrentes como string
            row["cartoes_concorrentes"] = " | ".join(
                f"{c.get('descricao','')} ({fmt(c.get('valor',0))})"
                for c in r.get("_concorrentes",[])
            )
            row["nossos_contratos"] = " | ".join(
                f"{c.get('descricao','')} ({fmt(c.get('valor',0))})"
                for c in r.get("_nossos",[])
            )
            row["emprestimos_ativos"] = " | ".join(
                f"{e.get('descricao','')} ({fmt(e.get('valor',0))})"
                for e in r.get("_emprestimos",[])
            )
            export_rows.append(row)
        df_exp = pd.DataFrame(export_rows)

        st.dataframe(df_exp[[c for c in df_exp.columns if not c.startswith("_")]],
                     hide_index=True, use_container_width=True,
                     column_config={
                         "liquido":       st.column_config.NumberColumn("Líquido",     format="R$ %.2f"),
                         "emp_disp":      st.column_config.NumberColumn("Emp. Disp.",  format="R$ %.2f"),
                         "cc_disp":       st.column_config.NumberColumn("Cart. Disp.", format="R$ %.2f"),
                         "base_calculo":  st.column_config.NumberColumn("Base Cálc.",  format="R$ %.2f"),
                         "total_concorrentes": st.column_config.NumberColumn("Concorrentes/mês", format="R$ %.2f"),
                     })

        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as w:
                df_exp.to_excel(w, index=False)
            st.download_button("📥 Baixar Excel Completo", buf.getvalue(),
                f"lote_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                use_container_width=True)
        with c2:
            st.download_button("📥 Baixar CSV",
                df_exp.to_csv(index=False, encoding="utf-8-sig"),
                f"lote_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                use_container_width=True)

    # ── FAB Stella Lote ─────────────────────────────────────────────────────
    render_chat_stella(modo_lote=True, lote_resultados=resultados)

# ============================================================================
# POPUP DAYCOVAL
# ============================================================================
@st.dialog("⚠️ Aviso Importante")
def show_daycoval_warning():
    st.warning("**Não compramos mais o cartão Daycoval**")
    st.markdown("Por favor, desconsidere este cartão nas suas análises e operações.")
    if st.button("Entendi", use_container_width=True, type="primary"):
        st.rerun()


# ============================================================================
# CONFIGURAÇÃO DE PREFEITURAS
# ============================================================================
PREFEITURAS = {
    'POA':               {'nome': 'Prefeitura de Poá - SP',              'descricao': 'Cidade: Poá - São Paulo'},
    'MARINGA':           {'nome': 'Prefeitura de Maringá - PR',          'descricao': 'Cidade: Maringá - Paraná'},
    'SOROCABA':          {'nome': 'Prefeitura de Sorocaba - SP',         'descricao': 'Cidade: Sorocaba - São Paulo'},
    'COTIA':             {'nome': 'Prefeitura de Cotia - SP',            'descricao': 'Cidade: Cotia - São Paulo'},
    'IMPERATRIZ':        {'nome': 'Prefeitura de Imperatriz - MA',       'descricao': 'Cidade: Imperatriz - Maranhão'},
    'EMBU':              {'nome': 'Prefeitura de Embu das Artes - SP',   'descricao': 'Cidade: Embu das Artes - São Paulo'},
    'HORTOLANDIA':       {'nome': 'Prefeitura de Hortolândia - SP',      'descricao': 'Cidade: Hortolândia - São Paulo'},
    'BAURU':             {'nome': 'Prefeitura de Bauru - SP',            'descricao': 'Cidade: Bauru - São Paulo'},
    'UBERABA':           {'nome': 'Prefeitura de Uberaba - MG',          'descricao': 'Cidade: Uberaba - Minas Gerais'},
    'LAGO_VERDE':        {'nome': 'Prefeitura de Lago Verde - MA',       'descricao': 'Cidade: Lago Verde - Maranhão'},
    'TABOAO_SERRA':      {'nome': 'Prefeitura de Taboão da Serra - SP',  'descricao': 'Cidade: Taboão da Serra - São Paulo'},
    'SALTO':             {'nome': 'Prefeitura de Salto - SP',            'descricao': 'Cidade: Salto - São Paulo'},
    'TUPA':              {'nome': 'Prefeitura de Tupã - SP',             'descricao': 'Cidade: Tupã - São Paulo'},
    'ITAITUBA':          {'nome': 'Prefeitura de Itaituba - PA',         'descricao': 'Cidade: Itaituba - Pará'},
    'BARCARENA':         {'nome': 'Prefeitura de Barcarena - PA',        'descricao': 'Cidade: Barcarena - Pará'},
    'CAMPOS_JORDAO':     {'nome': 'Prefeitura de Campos do Jordão - SP', 'descricao': 'Cidade: Campos do Jordão - São Paulo'},
    'RIBEIRAO_PRETO':    {'nome': 'Prefeitura de Ribeirão Preto - SP',   'descricao': 'Cidade: Ribeirão Preto - São Paulo'},
    'PONTA_GROSSA':      {'nome': 'Prefeitura de Ponta Grossa - PR',     'descricao': 'Cidade: Ponta Grossa - Paraná'},
    'CAMARA_DEPUTADOS':  {'nome': 'Câmara dos Deputados',                'descricao': 'Câmara dos Deputados - Brasília/DF'},
    'BELTERRA':          {'nome': 'Prefeitura de Belterra - PA',         'descricao': 'Cidade: Belterra - Pará'},
    'SAO_JOSE_RIO_PRETO':{'nome': 'Prefeitura de São José do Rio Preto - SP', 'descricao': 'Cidade: São José do Rio Preto - São Paulo'},
    'VINHEDO':           {'nome': 'Prefeitura de Vinhedo - SP',          'descricao': 'Cidade: Vinhedo - São Paulo'},
    'MONTE_ALEGRE_SE':   {'nome': 'Prefeitura de Monte Alegre de Sergipe - SE', 'descricao': 'Cidade: Monte Alegre de Sergipe'},
    'REDENCAO':          {'nome': 'Prefeitura de Redenção - PA',         'descricao': 'Cidade: Redenção - Pará'},
    'CUIABA':            {'nome': 'Prefeitura de Cuiabá - MT',           'descricao': 'Cidade: Cuiabá - Mato Grosso'},
    'ALEGO':             {'nome': 'Assembleia Legislativa de Goiás - ALEGO', 'descricao': 'Assembleia Legislativa - Goiás'},
    'GOVERNO_GOIAS':     {'nome': 'Governo do Estado de Goiás',          'descricao': 'Estado de Goiás'},
}


# ============================================================================
# MAIN
# ============================================================================
def main():
    refresh_cartoes_from_db()

    if not render_auth_page():
        st.stop()

    # if "daycoval_warning_shown" not in st.session_state:
    #     st.session_state["daycoval_warning_shown"] = False
    # if not st.session_state["daycoval_warning_shown"]:
    #     show_daycoval_warning()
    #     st.session_state["daycoval_warning_shown"] = True

    prefeitura_selecionada, modo = render_sidebar(
        PREFEITURAS, NOSSOS_PRODUTOS, CARTOES_CONHECIDOS, CARTOES_NAO_COMPRADOS
    )

    # with st.sidebar:
    #     st.markdown("---")
    #     if st.button("⚙️ Painel Admin", use_container_width=True, key="btn_admin_panel",
    #                  help="Acesso ao painel administrativo (requer credenciais)"):
    #         st.session_state["show_admin_page"] = not st.session_state.get("show_admin_page",False)
    #         if st.session_state.get("show_admin_page") and not st.session_state.get("admin_logged_in"):
    #             st.session_state["admin_logged_in"] = False
    #         st.rerun()

    if st.session_state.get("show_admin_page",False):
        render_admin_page(); st.stop()

    if modo == "Análise Individual":
        render_individual_header(prefeitura_selecionada, PREFEITURAS)

        arquivo_upload = st.file_uploader(
            "Faça upload do PDF ou imagem do holerite",
            type=["pdf","png","jpg","jpeg","webp","bmp","tiff"],
            help="A IA detecta a prefeitura automaticamente e calcula a margem."
        )

        if arquivo_upload:
            if st.button("🔍 Analisar com a Stella", type="primary", use_container_width=False):
                st.session_state.pop("resultado_individual", None)
                st.session_state.pop("stella_estrategia",   None)
                st.session_state.pop("margem_calculada",    None)
                st.session_state["chat_history"] = []

                with st.spinner("🤖 Stella lendo o holerite..."):
                    dados = analisar_arquivo(arquivo_upload.read(), arquivo_upload.name)
                    st.session_state["resultado_individual"] = dados

                if "erro" not in dados:
                    with st.spinner("✨ Stella gerando estratégia de vendas..."):
                        margem_temp = calcular_margem_ia(dados)
                        st.session_state["margem_calculada"] = margem_temp
                        estr = stella_estrategia(dados, margem_temp)
                        st.session_state["stella_estrategia"] = estr

            if "resultado_individual" in st.session_state:
                render_resultado(st.session_state["resultado_individual"])

    elif modo == "Análise em Lote":
        render_lote_header(prefeitura_selecionada, PREFEITURAS)

        arquivos_upload = st.file_uploader(
            "Faça upload dos PDFs ou imagens dos holerites",
            type=["pdf","png","jpg","jpeg","webp","bmp","tiff"],
            accept_multiple_files=True
        )

        if arquivos_upload:
            if st.button("🚀 Processar Todos com a Stella", type="primary", use_container_width=False):
                for k in ("lote_resultados", "df_resultados", "chat_history_lote", "insights_ia_lote"):
                    st.session_state.pop(k, None)
                with st.spinner(f"Analisando {len(arquivos_upload)} holerite(s)..."):
                    resultados = processar_lote(arquivos_upload)
                    st.session_state["lote_resultados"] = resultados
                if isinstance(resultados, list) and len(resultados) > 0:
                    st.success(f"✅ {len(resultados)} servidor(es) processado(s) com sucesso!")
                else:
                    st.error("Nenhum holerite processado com sucesso.")

            lote_ss = st.session_state.get("lote_resultados")
            if isinstance(lote_ss, list) and len(lote_ss) > 0:
                render_dashboard_lote(lote_ss)


    elif modo == "Perfil":
        render_profile_settings()

    elif modo == "Feedback":
        render_feedback_page()

    elif modo == "Busca CRM":
        render_crm_page()


if __name__ == "__main__":
    main()
