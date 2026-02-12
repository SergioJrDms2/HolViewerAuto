"""
auth_styles.py — Estilos CSS modernos para página de autenticação
Design que combina com a plataforma StarCheck
"""

import streamlit as st


def apply_auth_styles():
    """Aplica estilos CSS modernos que combinam com a plataforma."""
    st.markdown("""
        <style>
        /* ============================================ */
        /* FUNDO BRANCO LIMPO */
        /* ============================================ */
        .stApp {
            background: linear-gradient(135deg, #F8F9FA 0%, #FFFFFF 100%) !important;
        }
        
        /* Remove margens padrão */
        .main .block-container {
            padding-top: 1rem;
            padding-bottom: 2rem;
            max-width: 1400px;
        }
        
        /* ============================================ */
        /* INPUTS DE TEXTO - Estilo Moderno */
        /* ============================================ */
        
        /* Labels dos inputs */
        .stTextInput > label,
        .stTextInput label {
            color: #6B7280 !important;
            font-weight: 600 !important;
            font-size: 0.875rem !important;
            margin-bottom: 0.5rem !important;
            letter-spacing: -0.01em !important;
        }
        
        /* Campos de input */
        .stTextInput input {
            background-color: #FFFFFF !important;
            border: 1.5px solid #E5E7EB !important;
            border-radius: 0.75rem !important;
            padding: 0.875rem 1rem !important;
            font-size: 0.95rem !important;
            color: #111827 !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
        }
        
        .stTextInput input:focus {
            border-color: #8B5CF6 !important;
            box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1), 0 1px 2px rgba(0, 0, 0, 0.05) !important;
            outline: none !important;
        }
        
        .stTextInput input::placeholder {
            color: #9CA3AF !important;
        }
        
        /* ============================================ */
        /* BOTÕES - Gradiente Roxo Vibrante */
        /* ============================================ */
        
        .stButton button[kind="primary"],
        .stButton button {
            background: linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 0.75rem !important;
            padding: 0.875rem 1.5rem !important;
            font-weight: 700 !important;
            font-size: 0.95rem !important;
            box-shadow: 0 4px 14px rgba(139, 92, 246, 0.3) !important;
            transition: all 0.25s ease !important;
            width: 100% !important;
            letter-spacing: -0.01em !important;
        }
        
        .stButton button:hover {
            box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4) !important;
            transform: translateY(-2px) !important;
            background: linear-gradient(135deg, #7C3AED 0%, #6D28D9 100%) !important;
        }
        
        .stButton button:active {
            transform: translateY(0px) !important;
        }
        
        /* ============================================ */
        /* TABS - Estilo Minimalista */
        /* ============================================ */
        
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
            background: transparent;
            border-bottom: 2px solid #F3F4F6;
            padding-bottom: 0;
            margin-bottom: 2rem;
        }
        
        .stTabs [data-baseweb="tab"] {
            background-color: transparent;
            color: #9CA3AF;
            border-radius: 0;
            padding: 0.75rem 1.5rem;
            font-weight: 600;
            font-size: 0.95rem;
            border: none;
            border-bottom: 2px solid transparent;
            transition: all 0.2s ease;
        }
        
        .stTabs [data-baseweb="tab"]:hover {
            color: #8B5CF6;
            background-color: rgba(139, 92, 246, 0.05);
        }
        
        .stTabs [aria-selected="true"] {
            color: #8B5CF6 !important;
            background: transparent !important;
            border-bottom: 2px solid #8B5CF6 !important;
            box-shadow: none !important;
        }
        
        /* Remove borda inferior das tabs */
        .stTabs [data-baseweb="tab-border"] {
            display: none;
        }
        
        /* ============================================ */
        /* ALERTAS - Moderno e Clean */
        /* ============================================ */
        
        .stAlert {
            border-radius: 0.75rem !important;
            border-left-width: 3px !important;
            padding: 1rem 1.25rem !important;
            font-size: 0.9rem !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1) !important;
        }
        
        /* ============================================ */
        /* SPINNER DE LOADING */
        /* ============================================ */
        
        .stSpinner > div {
            border-top-color: #8B5CF6 !important;
        }
        
        /* ============================================ */
        /* REMOVER ELEMENTOS DESNECESSÁRIOS */
        /* ============================================ */
        
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* ============================================ */
        /* CUSTOMIZAÇÕES EXTRAS */
        /* ============================================ */
        
        /* Scrollbar customizada */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #F3F4F6;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #D1D5DB;
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #9CA3AF;
        }
        
        </style>
    """, unsafe_allow_html=True)
