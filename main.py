"""
StarCheck — Analisador de Holerite com IA
Motor: Groq (Llama 4 Scout) | Assistente: Stella ✨
Cálculo de Margem Consignável integrado via IA
"""

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

import tracking
import time as _time

from feedback_page import render_feedback_page
from ui_pages import render_individual_header, render_lote_header
from sidebar import render_sidebar
from auth import render_auth_page, render_user_info_sidebar
from profile_settings import render_profile_settings
from admin import render_admin_panel
from validador_arquivos import render_validador_page

# ============================================================================
# PORTFÓLIO — base de conhecimento da Stella
# ============================================================================
PORTFOLIO = """
PRODUTOS: Empréstimo Consig.(12-120m) | Cartão Consig. | Cartão Benefício(+telemedicina/odonto) | Auxílio Servidor(2m) | Compra Dívida(concorrente→troco) | Vale Consig.(1 parcela) | Afiliados | Crediário
FLUXO: cartão concorrente→COMPRA DÍVIDA | sem margem longa→AUXÍLIO/VALE | cliente nosso→REFINANCIAMENTO | sempre oferecer CARTÃO como adicional
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

    def _comprimir_texto_holerite(texto: str, limite: int = 4000) -> str:
        """Remove linhas vazias, espaços duplos e trunca."""
        linhas = [l.strip() for l in texto.splitlines() if l.strip()]
        comprimido = "\n".join(linhas)
        return comprimido[:limite]

    prompt = f"""Você é especialista em folha de pagamento brasileira.
Analise o holerite e retorne APENAS JSON válido (sem markdown).

NOSSOS PRODUTOS: {", ".join(NOSSOS_PRODUTOS)}
CARTÕES CONCORRENTES: {", ".join(CARTOES_CONHECIDOS)}
CARTÕES NÃO COMPRAMOS: {", ".join(CARTOES_NAO_COMPRADOS)}

HOLERITE:
{_comprimir_texto_holerite(texto)}

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
            max_tokens=1500, temperature=0
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
            max_tokens=2000,
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
    except Exception as e:
        import streamlit as st
        st.error(f"Stella — erro interno: {e}")
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
• EXCEÇÃO: Se houver Compra de Dívida viável, ela LIBERA margem de cartão → aí pode recomendar o cartão APÓS a compra, explicando que a margem será liberada.
• NUNCA fale sobre taxas ou valores liberados."""

    msgs = [{"role": "system", "content": system}]
    for h in historico[-4:]:
        msgs.append({"role": h["role"], "content": h["content"]})
    msgs.append({"role": "user", "content": pergunta})

    try:
        client = Groq(api_key=key)
        r = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=msgs,
            max_tokens=500,
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
            messages=msgs, max_tokens=500, temperature=0.4
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
    if estr is None:
        return   # nunca gerado — não exibe nada
    if not estr:  # {} = geração falhou
        st.warning("⚠️ Não foi possível gerar a estratégia. Tente novamente.")
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
                    msg_hidden, lote_resultados, st.session_state[hist_key]
                )
                tracking.track_stella_chat(                         # ← NOVO
                    msg_hidden, resp, "lote", None, ""              # ← NOVO
                )                                                   # ← NOVO
            else:
                margem_ss = st.session_state.get("margem_calculada", {})
                resp = stella_chat(msg_hidden, dados, st.session_state[hist_key], margem_ss)
                tracking.track_stella_chat(                         # ← NOVO
                    msg_hidden, resp, "individual",                  # ← NOVO
                    st.session_state.get("analise_id_atual"),        # ← NOVO
                    dados.get("prefeitura", "")                      # ← NOVO
                )                                                    # ← NOVO
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
      position:fixed; bottom:68px; right:28px; z-index:999999;
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
      position:fixed; bottom:130px; right:28px; z-index:999998;
      width:375px; max-height:600px;
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
    
        # ── Botão Stella ──────────────────────────────────────────────────────
        # Substitua o bloco do botão Stella em render_resultado por:

        if st.session_state.get("stella_estrategia") is None:
            # Ainda não foi tentado — mostra botão
            if st.button("✨ Gerar Estratégia com Stella", type="secondary", key="btn_stella_individual"):
                with st.spinner("✨ Stella pensando..."):
                    estr = stella_estrategia(dados, st.session_state.get("margem_calculada"))
                    # Usa sentinela distinta de None para indicar "já tentou"
                    st.session_state["stella_estrategia"] = estr if estr else {}
                    st.session_state["stella_estrategia_gerada"] = True
                    tracking.track_stella_estrategia(
                        dados, estr,
                        st.session_state.get("analise_id_atual"),
                        "individual"
                    )
                    st.rerun()
            st.info("Clique para gerar insights estratégicos com IA.")
        else:
            # Já foi gerado (com ou sem conteúdo) — renderiza painel
            render_stella_panel(dados, st.session_state.get("stella_estrategia"))

    # ── FAB Stella Individual ───────────────────────────────────────────────
    render_chat_stella(modo_lote=False)


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
            _bytes_lote = arq.read()                                            # ← NOVO
            d = analisar_arquivo(_bytes_lote, arq.name)
            if "erro" in d:
                st.warning(...)
                continue
            # Upload do holerite para Storage                                   ← NOVO
            _uid_lote = st.session_state.usuario.get("id", "") if 'usuario' in st.session_state else ""  # ← NOVO
            if _uid_lote:                                                       # ← NOVO
                _sp = tracking.upload_holerite(                                 # ← NOVO
                    _bytes_lote, arq.name, _uid_lote,                          # ← NOVO
                    d.get("prefeitura", ""), d.get("nome", "")                 # ← NOVO
                )                                                               # ← NOVO
                d["_storage_path"] = _sp                                        # ← NOVO (usado por _track_lote_itens)

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
            max_tokens=1200,
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
def gerar_pdf_intel(resultados: list, insights_ia: list, market_payload: dict) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (
        Paragraph, Spacer, Table, TableStyle,
        HRFlowable, KeepTogether, Image as RLImage, PageBreak
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate
    import plotly.graph_objects as go
    from collections import Counter, defaultdict
    import io as _io

    W, H = A4
    CW = W - 3 * cm  # usable content width for normal pages

    # ── PALETTE ──────────────────────────────────────────────────────────────
    C_PURPLE       = colors.HexColor("#7C3AED")
    C_PURPLE_DARK  = colors.HexColor("#4C1D95")
    C_PURPLE_MID   = colors.HexColor("#6D28D9")
    C_PURPLE_LIGHT = colors.HexColor("#EDE9FE")
    C_PURPLE_PALE  = colors.HexColor("#F5F3FF")
    C_VIOLET       = colors.HexColor("#8B5CF6")
    C_BLUE         = colors.HexColor("#1D4ED8")
    C_BLUE_LIGHT   = colors.HexColor("#DBEAFE")
    C_GREEN        = colors.HexColor("#16A34A")
    C_GREEN_LIGHT  = colors.HexColor("#DCFCE7")
    C_RED          = colors.HexColor("#DC2626")
    C_RED_LIGHT    = colors.HexColor("#FEF2F2")
    C_AMBER        = colors.HexColor("#D97706")
    C_AMBER_LIGHT  = colors.HexColor("#FEF3C7")
    C_PINK         = colors.HexColor("#BE185D")
    C_GRAY         = colors.HexColor("#6B7280")
    C_GRAY_DARK    = colors.HexColor("#374151")
    C_GRAY_DARKEST = colors.HexColor("#111827")
    C_GRAY_LIGHT   = colors.HexColor("#F9FAFB")
    C_BORDER       = colors.HexColor("#E5E7EB")
    C_BORDER_MED   = colors.HexColor("#D1D5DB")
    C_WHITE        = colors.white

    # ── TYPOGRAPHY ───────────────────────────────────────────────────────────
    def S(name, **kw):
        return ParagraphStyle(name, **kw)

    sH1    = S("H1",    fontSize=15, textColor=C_PURPLE_DARK, fontName="Helvetica-Bold",
                leading=19, spaceBefore=10, spaceAfter=4)
    sH2    = S("H2",    fontSize=11, textColor=C_GRAY_DARKEST, fontName="Helvetica-Bold",
                leading=14, spaceBefore=8, spaceAfter=3)
    sH3    = S("H3",    fontSize=9.5, textColor=C_GRAY_DARK, fontName="Helvetica-Bold",
                leading=13, spaceBefore=6, spaceAfter=2)
    sBody  = S("Body",  fontSize=8.5, textColor=C_GRAY_DARK, fontName="Helvetica",
                leading=13, spaceAfter=2)
    sSmall = S("Sml",   fontSize=7.5, textColor=C_GRAY, fontName="Helvetica", leading=10)
    sFoot  = S("Ft",    fontSize=7, textColor=C_GRAY, fontName="Helvetica",
                alignment=TA_CENTER)
    sTH    = S("TH",    fontSize=7.5, textColor=C_WHITE, fontName="Helvetica-Bold",
                leading=10, alignment=TA_CENTER)
    sTD    = S("TD",    fontSize=7.5, textColor=C_GRAY_DARK, fontName="Helvetica", leading=10)
    sTDC   = S("TDC",   fontSize=7.5, textColor=C_GRAY_DARK, fontName="Helvetica",
                leading=10, alignment=TA_CENTER)
    sKV    = S("KV",    fontSize=18, textColor=C_PURPLE, fontName="Helvetica-Bold",
                leading=22, alignment=TA_CENTER)
    sKL    = S("KL",    fontSize=6.5, textColor=C_GRAY, fontName="Helvetica",
                leading=9, alignment=TA_CENTER)
    sInsT  = S("InsT",  fontSize=9.5, textColor=C_GRAY_DARKEST, fontName="Helvetica-Bold",
                leading=13, spaceAfter=2)
    sInsB  = S("InsB",  fontSize=8.5, textColor=C_GRAY_DARK, fontName="Helvetica",
                leading=13)
    sChapL = S("ChpL",  fontSize=7, textColor=C_PURPLE, fontName="Helvetica-Bold",
                leading=9, alignment=TA_LEFT)

    buf = _io.BytesIO()

    # ── PAGE TEMPLATES ────────────────────────────────────────────────────────
    def _draw_cover(canvas, doc):
        canvas.saveState()
        # Deep purple background
        canvas.setFillColor(C_PURPLE_DARK)
        canvas.rect(0, 0, W, H, fill=True, stroke=False)
        # Lighter upper band
        canvas.setFillColor(C_PURPLE)
        canvas.rect(0, H * 0.40, W, H * 0.60, fill=True, stroke=False)
        # Subtle accent strip left
        canvas.setFillColor(C_PURPLE_MID)
        canvas.rect(0, 0, 7, H, fill=True, stroke=False)
        # Decorative circles (top right)
        canvas.setFillColor(colors.HexColor("#5B21B6"))
        canvas.circle(W - 2.5 * cm, H - 2 * cm, 3.8 * cm, fill=True, stroke=False)
        canvas.setFillColor(C_PURPLE_MID)
        canvas.circle(W - 2.5 * cm, H - 2 * cm, 2.8 * cm, fill=True, stroke=False)
        canvas.setFillColor(C_PURPLE)
        canvas.circle(W - 2.5 * cm, H - 2 * cm, 1.8 * cm, fill=True, stroke=False)
        # Bottom footer bar
        canvas.setFillColor(colors.HexColor("#2D1B69"))
        canvas.rect(0, 0, W, 2 * cm, fill=True, stroke=False)
        canvas.setFillColor(colors.HexColor("#A78BFA"))
        canvas.setFont("Helvetica", 7)
        canvas.drawString(1.8 * cm, 0.72 * cm,
                          f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
                          f"  ·  Starbank Grupo  ·  Documento confidencial — uso interno")
        canvas.restoreState()

    def _draw_normal(canvas, doc):
        canvas.saveState()
        pg = canvas.getPageNumber()
        # Top header bar
        canvas.setFillColor(C_PURPLE)
        canvas.rect(0, H - 26, W, 26, fill=True, stroke=False)
        canvas.setFillColor(C_WHITE)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(1.5 * cm, H - 16.5, "StarCheck  ·  Inteligência de Mercado")
        canvas.setFont("Helvetica", 7.5)
        canvas.drawRightString(W - 1.5 * cm, H - 16.5,
                               datetime.now().strftime("%d/%m/%Y"))
        # Bottom rule + page number
        canvas.setFillColor(C_BORDER)
        canvas.rect(1.5 * cm, 22, W - 3 * cm, 0.7, fill=True, stroke=False)
        canvas.setFillColor(C_GRAY)
        canvas.setFont("Helvetica", 7)
        canvas.drawCentredString(W / 2, 9, f"Página {pg}  ·  Starbank Grupo")
        canvas.restoreState()

    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=0.8 * cm,  bottomMargin=1.4 * cm,
    )
    f_cover  = Frame(0, 0, W, H,
                     leftPadding=2.6 * cm, rightPadding=2.2 * cm,
                     topPadding=0, bottomPadding=2.4 * cm, id="cover")
    f_normal = Frame(1.5 * cm, 1.4 * cm, CW, H - 4.0 * cm,
                     leftPadding=0, rightPadding=0,
                     topPadding=0, bottomPadding=0, id="normal")
    doc.addPageTemplates([
        PageTemplate(id="Cover",  frames=[f_cover],  onPage=_draw_cover),
        PageTemplate(id="Normal", frames=[f_normal], onPage=_draw_normal),
    ])

    story = []

    # ── HELPERS ───────────────────────────────────────────────────────────────
    def _F(v):
        """Format BRL value."""
        try:
            return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except:
            return "R$ 0,00"

    def _fig_to_img(fig, display_w_cm, px_w, px_h):
        """Export Plotly fig → RLImage preserving exact aspect ratio."""
        aspect = px_h / px_w
        dh = display_w_cm * aspect
        try:
            data = fig.to_image(format="png", scale=2, width=px_w, height=px_h)
            return RLImage(_io.BytesIO(data),
                           width=display_w_cm * cm,
                           height=dh * cm)
        except Exception:
            return None

    def _section(title):
        """Styled section header with divider."""
        return [
            Paragraph(title, sH1),
            HRFlowable(width="100%", thickness=2, color=C_PURPLE, spaceAfter=6),
        ]

    def _tbl(rows, col_fracs, hdr_color=None):
        """Build Table with standard styling."""
        hc  = hdr_color or C_PURPLE
        t   = Table(rows, colWidths=[f * CW for f in col_fracs])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), hc),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_GRAY_LIGHT]),
            ("BOX",           (0, 0), (-1, -1), 0.4, C_BORDER),
            ("INNERGRID",     (0, 0), (-1, -1), 0.25, C_BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ]))
        return t

    def _side_by_side(left_items, right_items, col_l=0.5, col_r=0.5):
        """Two-column layout helper."""
        t = Table([[left_items, right_items]],
                  colWidths=[col_l * CW, col_r * CW])
        t.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (0, -1),  6),
            ("RIGHTPADDING",  (1, 0), (1, -1),  0),
        ]))
        return t

    _TIPO_HEX = {
        "nosso":       "#7C3AED",
        "concorrente": "#1D4ED8",
        "nao_comprado":"#BE185D",
        "emprestimo":  "#D97706",
        "desconhecido":"#6B7280",
    }
    _NIVEL_COLORS = {
        "critico":     ("#FEF2F2", "#DC2626"),
        "oportunidade":("#FFFBEB", "#D97706"),
        "atencao":     ("#EFF6FF", "#1D4ED8"),
        "positivo":    ("#F0FDF4", "#16A34A"),
    }
    _NIVEL_LBL = {
        "critico":"CRÍTICO","oportunidade":"OPORTUNIDADE",
        "atencao":"ATENÇÃO","positivo":"POSITIVO"
    }

    # ── RE-COMPUTE ANALYTICS (mirrors the Streamlit tab) ─────────────────────
    total = len(resultados)
    mp    = market_payload

    # Institution-level aggregation
    inst_data: dict = defaultdict(lambda: {
        "contratos": 0, "valor": 0.0, "servidores": set(), "tipo": ""
    })
    for ri, r in enumerate(resultados):
        d = r.get("_dados", {})
        for c in d.get("cartoes", []):
            desc  = str(c.get("descricao", "")).strip()
            tipo  = c.get("tipo", "desconhecido")
            valor = _abs_val(c.get("valor", 0))
            if not desc or valor <= 0: continue
            inst_data[desc]["contratos"] += 1
            inst_data[desc]["valor"]     += valor
            inst_data[desc]["tipo"]       = tipo
            inst_data[desc]["servidores"].add(ri)
        for e in d.get("emprestimos", []):
            desc  = str(e.get("descricao", "")).strip()
            valor = _abs_val(e.get("valor", 0))
            if not desc or valor <= 0: continue
            te = ("nosso" if any(p.upper() in desc.upper() for p in NOSSOS_PRODUTOS)
                  else "emprestimo")
            inst_data[desc]["contratos"] += 1
            inst_data[desc]["valor"]     += valor
            inst_data[desc]["tipo"]       = te
            inst_data[desc]["servidores"].add(ri)

    inst_list = sorted([{
        "desc":        k,
        "contratos":   v["contratos"],
        "valor":       v["valor"],
        "servidores":  len(v["servidores"]),
        "tipo":        v["tipo"],
        "ticket_medio": v["valor"] / v["contratos"] if v["contratos"] else 0,
    } for k, v in inst_data.items()], key=lambda x: x["valor"], reverse=True)

    def _grp_val(tipo):
        return sum(i["valor"] for i in inst_list if i["tipo"] == tipo)
    def _grp_ct(tipo):
        return sum(i["contratos"] for i in inst_list if i["tipo"] == tipo)

    tv_nosso  = _grp_val("nosso");  ct_nosso  = _grp_ct("nosso")
    tv_conc   = _grp_val("concorrente"); ct_conc = _grp_ct("concorrente")
    tv_ncomp  = _grp_val("nao_comprado"); ct_ncomp = _grp_ct("nao_comprado")
    tv_emp    = _grp_val("emprestimo"); ct_emp = _grp_ct("emprestimo")
    tv_desc   = _grp_val("desconhecido"); ct_desc = _grp_ct("desconhecido")
    tv_total  = tv_nosso + tv_conc + tv_ncomp + tv_emp + tv_desc
    ct_total  = ct_nosso + ct_conc + ct_ncomp + ct_emp + ct_desc

    pct_nosso = (tv_nosso / tv_total * 100) if tv_total else 0
    pct_conc  = (tv_conc  / tv_total * 100) if tv_total else 0

    com_emp    = [r for r in resultados if r["emp_disp"] > 0]
    com_conc   = [r for r in resultados if r["qt_concorrentes"] > 0]
    com_nos    = [r for r in resultados if r["qt_nossos"] > 0]
    sem_consig = [r for r in resultados if r["total_cartoes"] == 0
                  and r["total_emprestimos"] == 0]
    so_nosso   = [r for r in resultados if r["qt_nossos"] > 0
                  and r["qt_concorrentes"] == 0]
    so_conc    = [r for r in resultados if r["qt_nossos"] == 0
                  and r["qt_concorrentes"] > 0]
    misto      = [r for r in resultados if r["qt_nossos"] > 0
                  and r["qt_concorrentes"] > 0]

    taxa_penet = (len(com_nos) / total * 100) if total else 0
    marg_disp  = sum(r["emp_disp"] for r in com_emp)

    def faixa_sal(v):
        if v < 2000:  return "< R$2k"
        if v < 3000:  return "R$2k–3k"
        if v < 5000:  return "R$3k–5k"
        if v < 8000:  return "R$5k–8k"
        if v < 12000: return "R$8k–12k"
        return "> R$12k"

    _FAIXAS_ORD = ["< R$2k","R$2k–3k","R$3k–5k","R$5k–8k","R$8k–12k","> R$12k"]
    faixas  = Counter(faixa_sal(r["salario_base"]) for r in resultados)
    regimes = Counter(r["regime"] for r in resultados)

    pref_map: dict = {}
    for r in resultados:
        p = r["prefeitura"] or "Desconhecida"
        if p not in pref_map:
            pref_map[p] = {"servidores":0,"emp_disp":0.0,"emp_total":0.0,
                           "conc_total":0.0,"qt_conc":0,"qt_nossos":0,
                           "liquido_total":0.0,"qt_marg_disp":0,"qt_marg_lot":0,
                           "qt_sem_info":0}
        v = pref_map[p]
        v["servidores"]   += 1
        v["emp_disp"]     += max(r["emp_disp"], 0)
        v["emp_total"]    += max(r["emp_total"], 0)
        v["conc_total"]   += r["total_concorrentes"]
        v["qt_conc"]      += r["qt_concorrentes"]
        v["qt_nossos"]    += r["qt_nossos"]
        v["liquido_total"]+= r["liquido"]
        if not r["margem_ok"]:
            v["qt_sem_info"]  += 1
        elif r["emp_disp"] > 0:
            v["qt_marg_disp"] += 1
        else:
            v["qt_marg_lot"]  += 1
    pref_sorted = sorted(pref_map.items(), key=lambda x: x[1]["emp_disp"], reverse=True)

    prod_freq: dict = defaultdict(lambda: {"contratos":0,"valor":0.0})
    for r in resultados:
        d = r.get("_dados", {})
        for c in d.get("cartoes", []):
            if c.get("tipo") != "nosso": continue
            desc = str(c.get("descricao","")).upper()
            m = next((p for p in NOSSOS_PRODUTOS if p.upper() in desc), "OUTROS")
            prod_freq[m]["contratos"] += 1
            prod_freq[m]["valor"]     += _abs_val(c.get("valor", 0))
        for e in d.get("emprestimos", []):
            desc = str(e.get("descricao","")).upper()
            m = next((p for p in NOSSOS_PRODUTOS if p.upper() in desc), None)
            if m:
                prod_freq[m]["contratos"] += 1
                prod_freq[m]["valor"]     += _abs_val(e.get("valor", 0))

    faixa_consig: dict = defaultdict(lambda: {"total":0,"com_consig":0})
    for r in resultados:
        f = faixa_sal(r["salario_base"])
        faixa_consig[f]["total"] += 1
        if r["total_cartoes"] > 0 or r["total_emprestimos"] > 0:
            faixa_consig[f]["com_consig"] += 1

    opps = Counter(r["oportunidade"] for r in resultados)

    # ── PLOTLY HELPERS ────────────────────────────────────────────────────────
    _PLY_BASE = dict(
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="Helvetica, Arial, sans-serif", size=10, color="#374151"),
    )
    _PIE_PALETTE  = ["#7C3AED","#1D4ED8","#BE185D","#D97706","#6B7280","#16A34A","#DC2626"]
    _PREF_COLORS  = ["#7C3AED","#6D28D9","#5B21B6","#4C1D95","#3B0764"]
    _BAR_GRADIENT = ["#C4B5FD","#A78BFA","#8B5CF6","#7C3AED","#6D28D9","#5B21B6"]

    def _pie(labels, values, colors_list, hole=0.48, ann_text="",
             show_legend=True, px=420, py=300):
        fig = go.Figure(go.Pie(
            labels=labels, values=values,
            marker_colors=colors_list,
            hole=hole,
            textinfo="percent",
            textfont=dict(size=9),
            hoverinfo="skip",
        ))
        ann = []
        if ann_text:
            ann = [dict(text=ann_text, x=0.37, y=0.5, showarrow=False,
                        font=dict(size=9, color="#374151"))]
        fig.update_layout(
            **_PLY_BASE,
            width=px, height=py,
            margin=dict(t=10, b=10, l=5, r=5),
            showlegend=show_legend,
            legend=dict(font=dict(size=8), orientation="v",
                        x=0.70, y=0.5, bgcolor="rgba(0,0,0,0)"),
            annotations=ann,
        )
        return fig

    def _hbar(y_labels, x_values, bar_colors, px=750, py=None):
        n  = len(y_labels)
        py = py or max(260, n * 26 + 50)
        fig = go.Figure(go.Bar(
            y=y_labels, x=x_values,
            orientation="h",
            marker_color=bar_colors,
            text=[_F(v) for v in x_values],
            textposition="outside",
            textfont=dict(size=8),
            cliponaxis=False,
        ))
        fig.update_layout(
            **_PLY_BASE,
            width=px, height=py,
            margin=dict(t=8, b=8, l=5, r=90),
            xaxis=dict(tickprefix="R$ ", gridcolor="#F3F4F6", tickfont=dict(size=8)),
            yaxis=dict(tickfont=dict(size=8.5)),
            showlegend=False,
        )
        return fig, py

    def _vbar(x_labels, y_values, bar_colors, px=420, py=260,
              yprefix="", suffix="", show_text=True, yrange=None):
        texts = [f"{v:.0f}{suffix}" if suffix else _F(v)
                 for v in y_values] if show_text else []
        fig = go.Figure(go.Bar(
            x=x_labels, y=y_values,
            marker_color=bar_colors,
            text=texts if show_text else None,
            textposition="outside",
            textfont=dict(size=9),
            cliponaxis=False,
        ))
        kw = {}
        if yrange: kw["range"] = yrange
        fig.update_layout(
            **_PLY_BASE,
            width=px, height=py,
            margin=dict(t=8, b=8, l=5, r=5),
            xaxis=dict(tickfont=dict(size=8)),
            yaxis=dict(gridcolor="#F3F4F6", tickfont=dict(size=8),
                       tickprefix=yprefix, **kw),
            showlegend=False,
        )
        return fig

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 1 — COVER
    # ══════════════════════════════════════════════════════════════════════════
    n_prefs = len(set(r["prefeitura"] for r in resultados))

    story.append(Spacer(1, 5.2 * cm))
    story.append(Paragraph(
        "INTELIGÊNCIA DE MERCADO",
        S("CT1", fontSize=28, textColor=C_WHITE, fontName="Helvetica-Bold",
          leading=33, alignment=TA_LEFT)
    ))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "Análise Estratégica de Crédito Consignado",
        S("CT2", fontSize=13, textColor=colors.HexColor("#C4B5FD"),
          fontName="Helvetica", leading=17, alignment=TA_LEFT)
    ))
    story.append(Spacer(1, 0.15 * cm))
    story.append(Paragraph(
        "StarCheck  ·  Starbank Grupo",
        S("CT3", fontSize=10, textColor=colors.HexColor("#A78BFA"),
          fontName="Helvetica-Bold", leading=14, alignment=TA_LEFT)
    ))
    story.append(Spacer(1, 1.8 * cm))

    # Cover stat boxes
    cov_nums = [str(total),    str(n_prefs),   str(len(com_emp)),    str(len(so_conc))]
    cov_labs = ["Servidores", "Prefeituras",  "Com Margem Livre",   "Alvo Puro"]
    cov_data = [
        [Paragraph(n, S(f"CN{i}", fontSize=20, textColor=C_WHITE,
                        fontName="Helvetica-Bold", alignment=TA_CENTER))
         for i, n in enumerate(cov_nums)],
        [Paragraph(l, S(f"CL{i}", fontSize=8, textColor=colors.HexColor("#C4B5FD"),
                        fontName="Helvetica", alignment=TA_CENTER))
         for i, l in enumerate(cov_labs)],
    ]
    box_w = (W - 5.4 * cm) / 4
    cov_tbl = Table(cov_data, colWidths=[box_w] * 4)
    cov_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#3B1580")),
        ("BOX",           (0, 0), (-1, -1), 1, colors.HexColor("#6D28D9")),
        ("INNERGRID",     (0, 0), (-1, -1), 0.5, colors.HexColor("#5B21B6")),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(cov_tbl)
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(
        datetime.now().strftime("%B de %Y").capitalize(),
        S("CD", fontSize=9, textColor=colors.HexColor("#8B5CF6"),
          fontName="Helvetica", alignment=TA_LEFT)
    ))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 2 — EXECUTIVE SUMMARY
    # ══════════════════════════════════════════════════════════════════════════
    story += _section("Sumário Executivo")

    # --- KPI grid (3 × 2) ---
    def _kpi_cell(value, label, bg_hex, val_color=None):
        vc = val_color or C_PURPLE
        return Table(
            [[Paragraph(str(value), S("kv", fontSize=18, textColor=vc,
                                       fontName="Helvetica-Bold", leading=22,
                                       alignment=TA_CENTER))],
             [Paragraph(label, S("kl", fontSize=7, textColor=C_GRAY,
                                  fontName="Helvetica", leading=9,
                                  alignment=TA_CENTER))]],
            colWidths=[CW / 3]
        )

    kpi_row1 = [
        [_kpi_cell(_F(mp.get("volume_consignado_mensal", 0)),
                   "Volume Consignado / Mês", "#EDE9FE"),
         _kpi_cell(_F(mp.get("nossa_receita_mensal", 0)),
                   "Nossa Receita / Mês", "#F0FDF4", C_GREEN),
         _kpi_cell(_F(mp.get("volume_concorrentes_mensal", 0)),
                   "Volume Concorrentes / Mês", "#FEF2F2", C_RED)],
    ]
    kpi_row2 = [
        [_kpi_cell(f"{pct_nosso:.1f}%".replace(".", ","),
                   "Market Share Nosso", "#EDE9FE"),
         _kpi_cell(f"{taxa_penet:.0f}%",
                   "Taxa de Penetração", "#EFF6FF", C_BLUE),
         _kpi_cell(str(len(so_conc)),
                   "Alvo Puro (só concorrente)", "#FFFBEB", C_AMBER)],
    ]
    kpi_row3 = [
        [_kpi_cell(_F(marg_disp),
                   "Margem Emp. Disponível Total", "#F5F3FF"),
         _kpi_cell(str(len(com_nos)),
                   "Com Produtos Nossos", "#F0FDF4", C_GREEN),
         _kpi_cell(str(len(sem_consig)),
                   "Mercado Novo (sem consig.)", "#F9FAFB", C_GRAY)],
    ]

    for kpi_row in [kpi_row1, kpi_row2, kpi_row3]:
        t = Table(kpi_row, colWidths=[CW / 3] * 3)
        t.setStyle(TableStyle([
            ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
            ("INNERGRID",     (0, 0), (-1, -1), 0.5, C_BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.3 * cm))

    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        f"Relatório consolidado com análise de <b>{total} servidores públicos</b> de "
        f"<b>{n_prefs} prefeitura(s)</b>. Volume total identificado em consignações: "
        f"<b>{_F(tv_total)}/mês</b> — "
        f"<b>{pct_nosso:.1f}%</b> conosco e "
        f"<b>{pct_conc:.1f}%</b> com concorrentes, equivalendo a "
        f"<b>{_F(tv_conc)}/mês</b> de receita recorrente a ser capturada.",
        sBody
    ))

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 3 — MARKET SHARE
    # ══════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story += _section("Market Share & Posicionamento Competitivo")

    if tv_total > 0:
        # Build labels/values/colors lists for both charts
        ms_lvc = [(l, v, c) for l, v, c in [
            ("Starbank (Nossos)", tv_nosso,  "#7C3AED"),
            ("Concorrentes",     tv_conc,   "#1D4ED8"),
            ("Não Compramos",    tv_ncomp,  "#BE185D"),
            ("Empréstimos",      tv_emp,    "#D97706"),
            ("Não Identificados",tv_desc,   "#6B7280"),
        ] if v > 0]
        ct_lvc = [(l, v, c) for l, v, c in [
            ("Starbank (Nossos)", ct_nosso,  "#7C3AED"),
            ("Concorrentes",     ct_conc,   "#1D4ED8"),
            ("Não Compramos",    ct_ncomp,  "#BE185D"),
            ("Empréstimos",      ct_emp,    "#D97706"),
            ("Não Identificados",ct_desc,   "#6B7280"),
        ] if v > 0]

        f_vol = _pie(
            [x[0] for x in ms_lvc], [x[1] for x in ms_lvc], [x[2] for x in ms_lvc],
            ann_text=f"R${tv_total/1000:.1f}k\n/mês", px=420, py=300
        )
        f_ct = _pie(
            [x[0] for x in ct_lvc], [x[1] for x in ct_lvc], [x[2] for x in ct_lvc],
            ann_text=f"{ct_total}\ncontratos", px=420, py=300
        )

        img_vol = _fig_to_img(f_vol, CW / 2 / cm - 0.4, 420, 300)
        img_ct  = _fig_to_img(f_ct,  CW / 2 / cm - 0.4, 420, 300)

        hdr_row = [
            [Paragraph("<b>Por Volume Mensal (R$)</b>", sH3)],
            [Paragraph("<b>Por Número de Contratos</b>", sH3)],
        ]
        img_row = [
            [img_vol or Paragraph("—", sSmall)],
            [img_ct  or Paragraph("—", sSmall)],
        ]
        pie_tbl = Table(hdr_row + [img_row[0] + img_row[1]],
                        colWidths=[CW / 2, CW / 2])
        # Simpler: just two-column table
        pie_tbl2 = Table(
            [[Paragraph("<b>Por Volume Mensal (R$)</b>", sH3),
              Paragraph("<b>Por Número de Contratos</b>", sH3)],
             [img_vol or Paragraph("—", sSmall),
              img_ct  or Paragraph("—", sSmall)]],
            colWidths=[CW / 2, CW / 2]
        )
        pie_tbl2.setStyle(TableStyle([
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ]))
        story.append(pie_tbl2)
        story.append(Spacer(1, 0.5 * cm))

    # Category breakdown table
    story.append(Paragraph("<b>Detalhamento por Categoria</b>", sH2))
    story.append(Spacer(1, 0.15 * cm))
    tipo_map_ord = [
        ("nosso",        "Starbank (Nossos)"),
        ("concorrente",  "Concorrentes"),
        ("nao_comprado", "Não Compramos"),
        ("emprestimo",   "Empréstimos"),
        ("desconhecido", "Não Identificados"),
    ]
    cat_hdr = [Paragraph(h, sTH) for h in
               ["Categoria","Volume/Mês","% do Total","Contratos","Ticket Médio"]]
    cat_rows = [cat_hdr]
    for tipo, lbl in tipo_map_ord:
        items = [i for i in inst_list if i["tipo"] == tipo]
        if not items: continue
        vol  = sum(i["valor"]     for i in items)
        cts  = sum(i["contratos"] for i in items)
        pct  = vol / tv_total * 100 if tv_total else 0
        tm   = vol / cts if cts else 0
        hex_ = _TIPO_HEX.get(tipo, "#6B7280")
        cat_rows.append([
            Paragraph(f'<font color="{hex_}"><b>{lbl}</b></font>', sTD),
            Paragraph(_F(vol),                                      sTDC),
            Paragraph(f"{pct:.1f}%".replace(".", ","),              sTDC),
            Paragraph(str(cts),                                     sTDC),
            Paragraph(_F(tm),                                       sTDC),
        ])
    story.append(_tbl(cat_rows, [0.35, 0.22, 0.15, 0.12, 0.16]))

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 4 — COMPETITIVE MAP
    # ══════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story += _section("Mapa Competitivo — Instituições Presentes na Folha")

    top15 = inst_list[:15]
    if top15:
        n_b   = len(top15)
        px_h  = max(260, n_b * 27 + 50)
        f_bar, _ = _hbar(
            y_labels  = [i["desc"][:26] for i in top15][::-1],
            x_values  = [i["valor"] for i in top15][::-1],
            bar_colors= [_TIPO_HEX.get(i["tipo"],"#6B7280") for i in top15][::-1],
            px=740, py=px_h
        )
        disp_h = CW / cm * (px_h / 740)
        img_bar = _fig_to_img(f_bar, CW / cm, 740, px_h)
        if img_bar:
            story.append(img_bar)

    # Legend strip
    story.append(Spacer(1, 0.25 * cm))
    leg_items = [
        (f'<font color="{_TIPO_HEX[t]}">■</font> {l}')
        for t, l in [("nosso","Nossos"),("concorrente","Concorrentes"),
                     ("nao_comprado","Não Compramos"),
                     ("emprestimo","Empréstimos"),("desconhecido","Não Identificados")]
    ]
    leg_row = [[Paragraph(it, S(f"LL{i}", fontSize=7, textColor=C_GRAY_DARK,
                                fontName="Helvetica", alignment=TA_CENTER))
                for i, it in enumerate(leg_items)]]
    leg_tbl = Table(leg_row, colWidths=[CW / 5] * 5)
    leg_tbl.setStyle(TableStyle([("ALIGN",(0,0),(-1,-1),"CENTER"),
                                  ("TOPPADDING",(0,0),(-1,-1),2)]))
    story.append(leg_tbl)
    story.append(Spacer(1, 0.5 * cm))

    # Top concorrentes + top nossos side by side
    conc_top8 = [i for i in inst_list if i["tipo"] == "concorrente"][:8]
    noss_top8 = [i for i in inst_list if i["tipo"] == "nosso"][:8]

    def _inst_table(rows_data, hdr_color):
        hdr = [Paragraph(h, sTH) for h in
               ["Instituição","Vol./Mês","Contr.","Ticket Médio"]]
        rows = [hdr]
        for inst in rows_data:
            rows.append([
                Paragraph(inst["desc"][:26], sTD),
                Paragraph(_F(inst["valor"]),             sTDC),
                Paragraph(str(inst["contratos"]),        sTDC),
                Paragraph(_F(inst["ticket_medio"]),      sTDC),
            ])
        return _tbl(rows, [0.44, 0.26, 0.12, 0.18], hdr_color=hdr_color)

    left_block  = []
    right_block = []
    if conc_top8:
        left_block.append(Paragraph("<b>Top Concorrentes</b>", sH3))
        left_block.append(Spacer(1, 0.1 * cm))
        left_block.append(_inst_table(conc_top8, C_BLUE))
    if noss_top8:
        right_block.append(Paragraph("<b>Nossos Produtos Ativos</b>", sH3))
        right_block.append(Spacer(1, 0.1 * cm))
        right_block.append(_inst_table(noss_top8, C_PURPLE))

    if left_block or right_block:
        story.append(_side_by_side(left_block or [Spacer(1, 0.1*cm)],
                                   right_block or [Spacer(1, 0.1*cm)]))

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 5 — CUSTOMER SEGMENTATION
    # ══════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story += _section("Segmentação da Base de Clientes")

    # --- Row A: Relationship profile (pie) + Salary distribution (bar) ---
    outros_n = max(0, total - len(sem_consig) - len(so_nosso) - len(so_conc) - len(misto))
    seg_lvc = [(l, len(g), c) for l, g, c in [
        ("🌱 Sem Consig.", sem_consig, "#059669"),
        ("🏆 Só Nossos",   so_nosso,   "#7C3AED"),
        ("🎯 Só Conc.",    so_conc,    "#1D4ED8"),
        ("🔀 Misto",       misto,      "#D97706"),
    ] if g]
    if outros_n > 0:
        seg_lvc.append(("❓ Outros", outros_n, "#9CA3AF"))

    f_seg = _pie([x[0] for x in seg_lvc], [x[1] for x in seg_lvc],
                 [x[2] for x in seg_lvc], ann_text=f"{total}\nserv.", px=380, py=280)

    faixa_ord = [(f, faixas.get(f, 0)) for f in _FAIXAS_ORD if faixas.get(f, 0) > 0]
    f_sal = _vbar(
        [x[0] for x in faixa_ord],
        [x[1] for x in faixa_ord],
        _BAR_GRADIENT[:len(faixa_ord)],
        px=380, py=280, show_text=True, yprefix=""
    )

    dw = CW / 2 / cm - 0.5
    img_seg = _fig_to_img(f_seg, dw, 380, 280)
    img_sal = _fig_to_img(f_sal, dw, 380, 280)

    row_A = Table(
        [[Paragraph("<b>Perfil de Relacionamento</b>", sH3),
          Paragraph("<b>Distribuição por Faixa Salarial</b>", sH3)],
         [img_seg or Paragraph("—", sSmall),
          img_sal or Paragraph("—", sSmall)]],
        colWidths=[CW / 2, CW / 2]
    )
    row_A.setStyle(TableStyle([
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
    ]))
    story.append(row_A)
    story.append(Spacer(1, 0.4 * cm))

    # --- Row B: Regime distribution (bar) + Consign rate by salary (bar) ---
    f_reg2 = _vbar(
       list(regimes.keys()), list(regimes.values()),
       ["#7C3AED"] * len(regimes),
       px=380, py=260
   )
    # Fix colors
    f_reg2 = _vbar(
        list(regimes.keys()), list(regimes.values()),
        ["#7C3AED"] * len(regimes),
        px=380, py=260
    )

    fx_tc_l, fx_tc_v = [], []
    for f_ in _FAIXAS_ORD:
        d_ = faixa_consig.get(f_, {})
        if d_.get("total", 0) > 0:
            fx_tc_l.append(f_)
            fx_tc_v.append(round(d_["com_consig"] / d_["total"] * 100, 1))
    f_tc = _vbar(
        fx_tc_l, fx_tc_v,
        ["#F97316" if p > 70 else "#7C3AED" if p > 40 else "#A78BFA"
         for p in fx_tc_v],
        px=380, py=260, show_text=True, suffix="%", yrange=[0, 120]
    )

    img_reg = _fig_to_img(f_reg2, dw, 380, 260)
    img_tc  = _fig_to_img(f_tc,   dw, 380, 260)

    row_B = Table(
        [[Paragraph("<b>Distribuição por Regime</b>", sH3),
          Paragraph("<b>Taxa de Consignação por Faixa Salarial</b>", sH3)],
         [img_reg or Paragraph("—", sSmall),
          img_tc  or Paragraph("—", sSmall)]],
        colWidths=[CW / 2, CW / 2]
    )
    row_B.setStyle(TableStyle([
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
    ]))
    story.append(row_B)

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 6 — PRODUCT PENETRATION + FUNNEL
    # ══════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story += _section("Penetração de Produtos & Funil de Oportunidades")

    # Product presence combo chart
    if prod_freq:
        p_names = list(prod_freq.keys())
        p_vals  = [prod_freq[p]["valor"]     for p in p_names]
        p_cts   = [prod_freq[p]["contratos"] for p in p_names]
        f_prod  = go.Figure()
        f_prod.add_bar(
            name="Volume R$/mês", x=p_names, y=p_vals,
            marker_color="#7C3AED", yaxis="y",
            text=[_F(v) for v in p_vals],
            textposition="outside", textfont=dict(size=8),
            cliponaxis=False,
        )
        f_prod.add_scatter(
            name="Nº Contratos", x=p_names, y=p_cts,
            mode="markers+text",
            marker=dict(size=9, color="#F97316"),
            text=p_cts, textposition="top center",
            textfont=dict(size=10, color="#F97316"), yaxis="y2",
        )
        f_prod.update_layout(
            **_PLY_BASE, width=380, height=270,
            margin=dict(t=10, b=30, l=5, r=5),
            yaxis=dict(tickprefix="R$ ", gridcolor="#F3F4F6"),
            yaxis2=dict(overlaying="y", side="right", showgrid=False),
            legend=dict(font=dict(size=8), orientation="h", y=-0.22),
            barmode="group",
        )
        img_prod = _fig_to_img(f_prod, dw, 380, 270)
    else:
        img_prod = None

    # Opportunity funnel
    com_nos_f    = len([r for r in resultados if r["qt_nossos"] > 0])
    sem_nos_conc = len([r for r in resultados if r["qt_nossos"] == 0
                        and r["qt_concorrentes"] > 0])
    sem_nos_emp  = len([r for r in resultados if r["qt_nossos"] == 0
                        and r["total_emprestimos"] > 0
                        and r["qt_concorrentes"] == 0])
    f_fun = go.Figure(go.Funnel(
        y=["Total Serv.","Com Nossos","Alvo (só conc.)","Emp. (sem nós)","Mercado Novo"],
        x=[total, com_nos_f, sem_nos_conc, sem_nos_emp, len(sem_consig)],
        textinfo="value+percent initial",
        marker=dict(color=["#4C1D95","#7C3AED","#1D4ED8","#D97706","#059669"]),
        textfont=dict(size=9),
    ))
    f_fun.update_layout(
        **_PLY_BASE, width=380, height=270,
        margin=dict(t=10, b=10, l=5, r=5),
    )
    img_fun = _fig_to_img(f_fun, dw, 380, 270)

    pen_tbl = Table(
        [[Paragraph("<b>Presença por Produto Nosso</b>", sH3),
          Paragraph("<b>Funil de Oportunidade</b>", sH3)],
         [img_prod or Paragraph("Nenhum produto identificado.", sSmall),
          img_fun  or Paragraph("—", sSmall)]],
        colWidths=[CW / 2, CW / 2]
    )
    pen_tbl.setStyle(TableStyle([
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
    ]))
    story.append(pen_tbl)

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 7 — PREFEITURA ANALYSIS
    # ══════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story += _section("Análise por Prefeitura")

    pnames  = [p[:20] for p, _ in pref_sorted]
    pemp_d  = [v["emp_disp"]  for _, v in pref_sorted]
    pemp_t  = [v["emp_total"] for _, v in pref_sorted]
    pconc   = [v["conc_total"] for _, v in pref_sorted]
    p_disp  = [v["qt_marg_disp"] for _, v in pref_sorted]
    p_lot   = [v["qt_marg_lot"]  for _, v in pref_sorted]
    p_sem   = [v["qt_sem_info"]  for _, v in pref_sorted]

    # Stacked bar: committed vs available
    f_p1 = go.Figure()
    f_p1.add_bar(
        name="Comprometido", x=pnames,
        y=[max(t - d, 0) for t, d in zip(pemp_t, pemp_d)],
        marker_color="#F97316",
    )
    f_p1.add_bar(
        name="Disponível", x=pnames,
        y=[max(d, 0) for d in pemp_d],
        marker_color="#7C3AED",
    )
    f_p1.update_layout(
        **_PLY_BASE, width=740, height=240,
        barmode="stack",
        margin=dict(t=8, b=8, l=5, r=5),
        legend=dict(font=dict(size=8), orientation="h", y=-0.3),
        yaxis=dict(tickprefix="R$ ", gridcolor="#F3F4F6", tickfont=dict(size=8)),
        xaxis=dict(tickfont=dict(size=8)),
    )

    # Concorrentes bar
    f_p2 = go.Figure(go.Bar(
        x=pnames, y=pconc, marker_color="#1D4ED8",
        text=[_F(c) if c > 0 else "" for c in pconc],
        textposition="outside", textfont=dict(size=8),
        cliponaxis=False,
    ))
    f_p2.update_layout(
        **_PLY_BASE, width=740, height=200,
        margin=dict(t=8, b=8, l=5, r=5),
        yaxis=dict(tickprefix="R$ ", gridcolor="#F3F4F6", tickfont=dict(size=8)),
        xaxis=dict(tickfont=dict(size=8)),
        showlegend=False,
    )

    # Status by prefeitura (stacked)
    f_p3 = go.Figure()
    f_p3.add_bar(name="✅ Com Margem",  x=pnames, y=p_disp, marker_color="#16A34A")
    f_p3.add_bar(name="⛔ Lotada",      x=pnames, y=p_lot,  marker_color="#DC2626")
    f_p3.add_bar(name="❓ Sem Mapeam.", x=pnames, y=p_sem,  marker_color="#9CA3AF")
    f_p3.update_layout(
        **_PLY_BASE, width=740, height=200,
        barmode="stack",
        margin=dict(t=8, b=8, l=5, r=5),
        legend=dict(font=dict(size=8), orientation="h", y=-0.35),
        yaxis=dict(title="Serv.", gridcolor="#F3F4F6", tickfont=dict(size=8)),
        xaxis=dict(tickfont=dict(size=8)),
    )

    img_p1 = _fig_to_img(f_p1, CW / cm, 740, 240)
    img_p2 = _fig_to_img(f_p2, CW / cm, 740, 200)
    img_p3 = _fig_to_img(f_p3, CW / cm, 740, 200)

    for title, img in [
        ("<b>Margem de Empréstimo: Comprometida vs Disponível</b>",   img_p1),
        ("<b>Cartões Concorrentes — Volume Mensal Saindo da Folha</b>", img_p2),
        ("<b>Status de Margem por Prefeitura</b>",                     img_p3),
    ]:
        if img:
            story.append(Paragraph(title, sH3))
            story.append(img)
            story.append(Spacer(1, 0.35 * cm))

    # Prefeitura detail table
    story.append(Spacer(1, 0.1 * cm))
    story.append(Paragraph("<b>Detalhamento por Prefeitura</b>", sH2))
    story.append(Spacer(1, 0.15 * cm))
    p_hdr = [Paragraph(h, sTH) for h in
             ["Prefeitura","Serv.","Emp. Disp.","Conc./Mês","Nossos","Liq. Médio"]]
    p_rows = [p_hdr]
    for pref, v in pref_sorted:
        liq_med = v["liquido_total"] / v["servidores"] if v["servidores"] else 0
        p_rows.append([
            Paragraph(pref[:28],         sTD),
            Paragraph(str(v["servidores"]), sTDC),
            Paragraph(_F(v["emp_disp"]),  sTDC),
            Paragraph(_F(v["conc_total"]),sTDC),
            Paragraph(str(v["qt_nossos"]),sTDC),
            Paragraph(_F(liq_med),        sTDC),
        ])
    story.append(_tbl(p_rows, [0.31,0.08,0.18,0.18,0.10,0.15]))

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 8 — AI STRATEGIC INSIGHTS
    # ══════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story += _section("Insights Estratégicos · Stella IA")
    story.append(Paragraph(
        "Análise gerada automaticamente pela Stella com base nos dados agregados "
        "deste lote. Cada insight inclui uma conclusão acionável para decisões "
        "de liderança e gestão comercial.",
        sBody
    ))
    story.append(Spacer(1, 0.5 * cm))

    if insights_ia:
        for ins in insights_ia:
            nivel    = ins.get("nivel", "atencao")
            bg_hex, brd_hex = _NIVEL_COLORS.get(nivel, ("#F9FAFB","#6B7280"))
            brd_rl   = colors.HexColor(brd_hex)
            bg_rl    = colors.HexColor(bg_hex)
            lbl_str  = _NIVEL_LBL.get(nivel, nivel.upper())
            icone    = ins.get("icone","💡")
            titulo   = ins.get("titulo","")
            texto    = ins.get("texto","")

            inner = Table(
                [[Paragraph(
                    f'{icone}  <b>{titulo}</b>'
                    f'  <font size="7" color="{brd_hex}"> [{lbl_str}]</font>',
                    sInsT),
                  Paragraph("", sSmall)],
                 [Paragraph(texto, sInsB), Paragraph("", sSmall)]],
                colWidths=[CW - 0.6 * cm, 0.6 * cm]
            )
            # Simpler single-cell approach
            content_block = [
                Paragraph(
                    f'{icone}  <b>{titulo}</b>'
                    f'  <font size="7" color="{brd_hex}"> [{lbl_str}]</font>',
                    sInsT
                ),
                Paragraph(texto, sInsB),
            ]
            card = Table([[content_block]], colWidths=[CW])
            card.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), bg_rl),
                ("TOPPADDING",    (0,0),(-1,-1), 9),
                ("BOTTOMPADDING", (0,0),(-1,-1), 9),
                ("LEFTPADDING",   (0,0),(-1,-1), 12),
                ("RIGHTPADDING",  (0,0),(-1,-1), 10),
                ("LINEAFTER",     (0,0),(0,-1),  4, brd_rl),
                ("LINEBEFORE",    (0,0),(0,-1),  0.5, brd_rl),
                ("LINEBELOW",     (0,-1),(-1,-1), 0.5, brd_rl),
                ("LINEABOVE",     (0,0),(-1,0),  0.5, brd_rl),
            ]))
            story.append(KeepTogether([card, Spacer(1, 0.3 * cm)]))
    else:
        story.append(Paragraph("Insights não disponíveis.", sSmall))

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 9+ — SERVER RANKING
    # ══════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story += _section("Ranking de Oportunidades — Servidores")
    story.append(Paragraph(
        "Ordenado por prioridade comercial — do maior potencial ao de menor urgência imediata.",
        sBody
    ))
    story.append(Spacer(1, 0.3 * cm))

    _OPP_COLORS = {
        "🔥 Compra Dívida + Empréstimo": "#92400E",
        "💳 Compra de Dívida":           "#1E3A8A",
        "💵 Empréstimo Disponível":      "#14532D",
        "🔄 Refinanciamento":            "#4C1D95",
        "💵 Margem Disponível":          "#065F46",
        "❓ Prefeitura Não Mapeada":     "#6B7280",
        "⛔ Margem Lotada":              "#991B1B",
    }
    r_hdr = [Paragraph(h, sTH) for h in
             ["#","Nome","Prefeitura","Regime","Emp. Disp.","Concorrentes","Oportunidade"]]
    r_rows = [r_hdr]
    for idx, r in enumerate(resultados[:50], 1):
        opp_c    = _OPP_COLORS.get(r["oportunidade"], "#374151")
        emp_s    = _F(r["emp_disp"]) if r["emp_disp"] > 0 else "—"
        conc_s   = _F(r["total_concorrentes"]) if r["qt_concorrentes"] > 0 else "—"
        bg_stripe = C_WHITE if idx % 2 else C_GRAY_LIGHT
        r_rows.append([
            Paragraph(str(idx),                                              sTDC),
            Paragraph(r["nome"][:22],                                        sTD),
            Paragraph(r["prefeitura"][:18],                                  sTD),
            Paragraph(r["regime"][:14],                                      sTD),
            Paragraph(emp_s,                                                 sTDC),
            Paragraph(conc_s,                                                sTDC),
            Paragraph(
                f'<font color="{opp_c}"><b>{r["oportunidade"]}</b></font>', sTD),
        ])

    rank_tbl = Table(r_rows, colWidths=[c * CW for c in
                                         [0.05,0.19,0.17,0.13,0.12,0.12,0.22]])
    rank_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), C_PURPLE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_GRAY_LIGHT]),
        ("BOX",           (0, 0), (-1, -1), 0.4, C_BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.25, C_BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ("FONTSIZE",      (0, 0), (-1, -1), 7.5),
    ]))
    story.append(rank_tbl)

    if len(resultados) > 50:
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph(
            f"<i>Exibindo 50 de {len(resultados)} servidores. "
            f"Use o dashboard para visualizar o lote completo.</i>",
            sSmall
        ))

    # ── FINAL NOTE ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.8 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        f"Relatório gerado pelo StarCheck · Starbank Grupo · "
        f"{datetime.now().strftime('%d/%m/%Y às %H:%M')} · "
        f"Documento confidencial — uso interno exclusivo.",
        sFoot
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
            if st.button("🔍 Gerar Insights Estratégicos com IA", type="secondary", key="btn_insights"):
                with st.spinner("✨ Stella gerando insights..."):
                    st.session_state["insights_ia_lote"] = gerar_insights_ia_mercado(market_payload)
                    st.rerun()
            else:
                st.info("Clique para gerar insights estratégicos com IA.")
        insights_ia = st.session_state.get("insights_ia_lote", [])

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

        # Salva market_payload no session_state para o chat da Stella usar
        st.session_state["intel_mercado_payload"] = market_payload

            # ── BOTÃO DOWNLOAD PDF ────────────────────────────────────────────────
        st.markdown("<hr style='border-color:#f3f4f6;margin:1.5rem 0;'>", unsafe_allow_html=True)

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
            if st.download_button("📥 Baixar Excel Completo", buf.getvalue(),
                f"lote_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                use_container_width=True):
                tracking.track_export("excel", "lote", "", len(resultados))    # ← NOVO
        with c2:
            if st.download_button("📥 Baixar CSV",
                df_exp.to_csv(index=False, encoding="utf-8-sig"),
                f"lote_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                use_container_width=True):
                tracking.track_export("csv", "lote", "", len(resultados))      # ← NOVO

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
# MAIN
# ============================================================================
def main():

    if not render_auth_page():
        st.stop()

    # ── Redirecionamento direto para admin ───────────────────────────────
    if st.session_state.get("is_admin_redirect"):
        # Limpar a flag e mostrar painel admin diretamente
        del st.session_state["is_admin_redirect"]
        st.session_state["show_admin_page"] = True

    # if "daycoval_warning_shown" not in st.session_state:
    prefeitura_selecionada, modo = render_sidebar(
        PREFEITURAS, NOSSOS_PRODUTOS, CARTOES_CONHECIDOS, CARTOES_NAO_COMPRADOS
    )

    # ── Painel Admin (acesso direto via login ou toggle no sidebar para não-admin) ──
    if st.session_state.get("show_admin_page", False):
        render_admin_panel(); st.stop()

    def file_uploader(label, type, help):
        return st.file_uploader(
            label,
            type=type,
            help=help
        )

    if modo == "Análise Individual":
        render_individual_header(prefeitura_selecionada, PREFEITURAS)

        arquivo_upload = file_uploader(
            "Faça upload do PDF ou imagem do holerite",
            ["pdf","png","jpg","jpeg","webp","bmp","tiff"],
            "A IA detecta a prefeitura automaticamente e calcula a margem."
        )

        if arquivo_upload:
            if st.button("🔍 Analisar com a Stella", type="primary", use_container_width=False):
                # Limpa estado anterior
                for k in ("resultado_individual", "stella_estrategia",
                        "stella_estrategia_gerada", "margem_calculada", "analise_id_atual"):
                    st.session_state.pop(k, None)
                st.session_state["chat_history"] = []

                with st.spinner("🤖 Stella lendo o holerite..."):
                    _t0 = _time.time()
                    _arq_bytes = arquivo_upload.read()
                    dados = analisar_arquivo(_arq_bytes, arquivo_upload.name)
                    _duracao_ms = int((_time.time() - _t0) * 1000)
                    st.session_state["resultado_individual"] = dados

                if "erro" not in dados:
                    margem_temp = calcular_margem_ia(dados)
                    st.session_state["margem_calculada"] = margem_temp
                    st.session_state["stella_estrategia"] = None   # só None no primeiro load

                    uid = st.session_state.usuario.get("id", "")
                    _spath = tracking.upload_holerite(
                        _arq_bytes, arquivo_upload.name, uid,
                        dados.get("prefeitura", ""), dados.get("nome", "")
                    )
                    _aid = tracking.track_analise_individual(
                        dados, margem_temp,
                        arquivo_upload.name, len(_arq_bytes),
                        _spath, _duracao_ms
                    )
                    st.session_state["analise_id_atual"] = _aid
                    tracking.track_holerite_salvo(
                        uid, arquivo_upload.name, _spath, len(_arq_bytes),
                        f"application/{'pdf' if arquivo_upload.name.lower().endswith('pdf') else 'image'}",
                        dados.get("prefeitura", ""), dados.get("nome", ""), _aid
                    )

            # Renderiza resultado se já foi analisado (persiste entre reruns)
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
                _t0_lote = _time.time()                                         # ← NOVO
                with st.spinner(f"Analisando {len(arquivos_upload)} holerite(s)..."):
                    resultados = processar_lote(arquivos_upload)
                    st.session_state["lote_resultados"] = resultados
                if isinstance(resultados, list) and len(resultados) > 0:
                    st.success(f"✅ {len(resultados)} servidor(es) processado(s) com sucesso!")
                    _dur_lote = int((_time.time() - _t0_lote) * 1000)          # ← NOVO
                    tracking.track_lote_sessao(resultados, _dur_lote)          # ← NOVO
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

    elif modo == "Validador de Documentos":
        render_validador_page()


if __name__ == "__main__":
    main()
