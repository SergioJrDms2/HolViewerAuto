"""
profile_settings.py — Configurações de Perfil do Usuário
Permite personalizar cor do tema e avatar
"""

import streamlit as st

# ============================================================================
# TEMAS DE CORES DISPONÍVEIS
# ============================================================================

TEMAS = {
    "Roxo Padrão": {
        "gradient": "linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%)",
        "color_light": "#8B5CF6", "color_dark": "#7C3AED", "shadow": "rgba(139, 92, 246, 0.25)"
    },
    "Azul Oceano": {
        "gradient": "linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%)",
        "color_light": "#3B82F6", "color_dark": "#1D4ED8", "shadow": "rgba(59, 130, 246, 0.25)"
    },
    "Verde Menta": {
        "gradient": "linear-gradient(135deg, #10B981 0%, #059669 100%)",
        "color_light": "#10B981", "color_dark": "#059669", "shadow": "rgba(16, 185, 129, 0.25)"
    },
    "Rosa Flamingo": {
        "gradient": "linear-gradient(135deg, #EC4899 0%, #DB2777 100%)",
        "color_light": "#EC4899", "color_dark": "#DB2777", "shadow": "rgba(236, 72, 153, 0.25)"
    },
    "Laranja Vibrante": {
        "gradient": "linear-gradient(135deg, #F97316 0%, #EA580C 100%)",
        "color_light": "#F97316", "color_dark": "#EA580C", "shadow": "rgba(249, 115, 22, 0.25)"
    },
    "Ciano Elétrico": {
        "gradient": "linear-gradient(135deg, #06B6D4 0%, #0891B2 100%)",
        "color_light": "#06B6D4", "color_dark": "#0891B2", "shadow": "rgba(6, 182, 212, 0.25)"
    },
    "Vermelho Rubi": {
        "gradient": "linear-gradient(135deg, #EF4444 0%, #DC2626 100%)",
        "color_light": "#EF4444", "color_dark": "#DC2626", "shadow": "rgba(239, 68, 68, 0.25)"
    },
    "Índigo Profundo": {
        "gradient": "linear-gradient(135deg, #6366F1 0%, #4F46E5 100%)",
        "color_light": "#6366F1", "color_dark": "#4F46E5", "shadow": "rgba(99, 102, 241, 0.25)"
    },
    # --- NOVOS TEMAS ---
    "Lavanda Pastel": {
        "gradient": "linear-gradient(135deg, #DDD6FE 0%, #C4B5FD 100%)",
        "color_light": "#DDD6FE", "color_dark": "#A78BFA", "shadow": "rgba(167, 139, 250, 0.2)"
    },
    "Pôr do Sol": {
        "gradient": "linear-gradient(135deg, #F093FB 0%, #F5576C 100%)",
        "color_light": "#F093FB", "color_dark": "#F5576C", "shadow": "rgba(245, 87, 108, 0.25)"
    },
    "Floresta Negra": {
        "gradient": "linear-gradient(135deg, #111827 0%, #064E3B 100%)",
        "color_light": "#10B981", "color_dark": "#064E3B", "shadow": "rgba(6, 78, 59, 0.4)"
    },
    "Meia Noite": {
        "gradient": "linear-gradient(135deg, #0F172A 0%, #1E293B 100%)",
        "color_light": "#38BDF8", "color_dark": "#0F172A", "shadow": "rgba(15, 23, 42, 0.4)"
    },
    "Ouro Nobre": {
        "gradient": "linear-gradient(135deg, #FDE68A 0%, #D97706 100%)",
        "color_light": "#FDE68A", "color_dark": "#D97706", "shadow": "rgba(217, 119, 6, 0.25)"
    },
    "Sakura": {
        "gradient": "linear-gradient(135deg, #FBCFE8 0%, #F472B6 100%)",
        "color_light": "#FBCFE8", "color_dark": "#F472B6", "shadow": "rgba(244, 114, 182, 0.2)"
    },
    "Cyberpunk": {
        "gradient": "linear-gradient(135deg, #F0ABFC 0%, #A855F7 100%)",
        "color_light": "#F0ABFC", "color_dark": "#A855F7", "shadow": "rgba(168, 85, 247, 0.3)"
    },
    "Esmalte": {
        "gradient": "linear-gradient(135deg, #99F6E4 0%, #2D3748 100%)",
        "color_light": "#99F6E4", "color_dark": "#2D3748", "shadow": "rgba(45, 55, 72, 0.2)"
    }
}

AVATARES = [
    # Tradicionais e Profissionais
    "👤", "🧑‍💼", "👨‍💻", "👩‍💻", "👩‍🔬", "👨‍🎨", "🧑‍🚀",
    # Fofos e Animais
    "🐱", "🐶", "🦊", "🐼", "🐨", "🦁", "🐯", "🦄", "🐰", "🐣", "🐸", "🐧", "🐙", "🐝", "🦇",
    # Fantasia e Diversão
    "🦸", "🧙", "👻", "👾", "🤖", "👽", "🧜", "🧚",
    # Natureza e Comida (Vibe leve)
    "🍀", "🌸", "🌵", "🌈", "🍦", "🍩", "🍓", "🍕", "🥑",
    # Símbolos e Objetos
    "⭐", "🌟", "💫", "✨", "🔥", "💎", "🎯", "🚀", "🐍", "🪐", "🎨", "🎮", "🎸"
]

# ============================================================================
# FUNÇÕES DE GERENCIAMENTO DE PREFERÊNCIAS
# ============================================================================

def carregar_preferencias():
    # IMPORT LOCAL PARA EVITAR CIRCULAR IMPORT
    from auth import get_supabase_client
    
    """Carrega as preferências do usuário do Supabase ou retorna padrões."""
    if 'usuario' not in st.session_state:
        return {
            "tema": "Roxo Padrão",
            "avatar": "👤"
        }
    
    try:
        supabase = get_supabase_client()
        user_id = st.session_state.usuario['id']
        
        response = supabase.table('user_preferences').select('*').eq('user_id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            prefs = response.data[0]
            return {
                "tema": prefs.get('tema', 'Roxo Padrão'),
                "avatar": prefs.get('avatar', '👤')
            }
    except Exception as e:
        pass
    
    return {"tema": "Roxo Padrão", "avatar": "👤"}


def salvar_preferencias(tema: str, avatar: str) -> tuple[bool, str]:
    # IMPORT LOCAL PARA EVITAR CIRCULAR IMPORT - RESOLVE O ERRO 'NOT DEFINED'
    from auth import get_supabase_client

    """Salva as preferências do usuário no Supabase."""
    if 'usuario' not in st.session_state:
        return False, "Usuário não autenticado"
    
    try:
        supabase = get_supabase_client()
        user_id = st.session_state.usuario['id']
        
        dados = {
            'user_id': user_id,
            'tema': tema,
            'avatar': avatar
        }
        
        supabase.table('user_preferences').upsert(dados, on_conflict='user_id').execute()
        
        if 'preferencias' not in st.session_state:
            st.session_state.preferencias = {}
        
        st.session_state.preferencias['tema'] = tema
        st.session_state.preferencias['avatar'] = avatar
        
        return True, "Preferências salvas com sucesso!"
        
    except Exception as e:
        return False, f"Erro ao salvar: {str(e)}"


# ============================================================================
# INTERFACE DE CONFIGURAÇÕES DE PERFIL
# ============================================================================

def render_profile_settings():
    """Renderiza a página de configurações de perfil."""
    
    st.markdown("""
        <style>
        .profile-header {
            font-size: 2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #7C3AED 0%, #4C1D95 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }
        
        .profile-subtitle {
            color: #64748B;
            font-size: 1rem;
            margin-bottom: 2rem;
        }
        
        .theme-card {
            background: white;
            border-radius: 1rem;
            padding: 1.5rem;
            margin-bottom: 1rem;
            border: 2px solid #E2E8F0;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .theme-card:hover {
            border-color: #7C3AED;
            box-shadow: 0 4px 12px rgba(124, 58, 237, 0.15);
            transform: translateY(-2px);
        }
        
        .theme-card-selected {
            border-color: #7C3AED;
            background: linear-gradient(135deg, #F5F3FF 0%, #EDE9FE 100%);
            box-shadow: 0 4px 12px rgba(124, 58, 237, 0.2);
        }
        
        .avatar-option {
            font-size: 2.5rem;
            padding: 1rem;
            border-radius: 50%;
            background: white;
            border: 3px solid #E2E8F0;
            cursor: pointer;
            transition: all 0.3s ease;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 70px;
            height: 70px;
            margin: 0.5rem;
        }
        
        .avatar-option:hover {
            border-color: #7C3AED;
            transform: scale(1.1);
            box-shadow: 0 4px 12px rgba(124, 58, 237, 0.2);
        }
        
        .avatar-selected {
            border-color: #7C3AED;
            background: linear-gradient(135deg, #F5F3FF 0%, #EDE9FE 100%);
            box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3);
        }
        
        .preview-card {
            background: white;
            border-radius: 1rem;
            padding: 2rem;
            border: 2px solid #E2E8F0;
            text-align: center;
        }
        
        .save-button {
            background: linear-gradient(135deg, #7C3AED 0%, #6D28D9 100%);
            color: white;
            border: none;
            border-radius: 0.75rem;
            padding: 0.75rem 2rem;
            font-weight: 600;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
            width: 100%;
            margin-top: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<h1 class='profile-header'>Configurações de Perfil</h1>", unsafe_allow_html=True)
    st.markdown("<p class='profile-subtitle'>Personalize sua experiência no StarCheck</p>", unsafe_allow_html=True)
    
    # Carregar preferências atuais
    prefs = carregar_preferencias()
    
    # Inicializar state para seleção temporária
    if 'temp_tema' not in st.session_state:
        st.session_state.temp_tema = prefs['tema']
    if 'temp_avatar' not in st.session_state:
        st.session_state.temp_avatar = prefs['avatar']
    
    # Layout em colunas
    col1, col2 = st.columns([2, 1], gap="large")
    
    with col1:
        # ════════════════════════════════════════════════════════════════════
        # ESCOLHA DE TEMA
        # ════════════════════════════════════════════════════════════════════
        st.markdown("### 🎨 Escolha seu Tema de Cor")
        st.markdown("<p style='color: #64748B; margin-bottom: 1.5rem;'>Selecione a cor que mais combina com você</p>", unsafe_allow_html=True)
        
        # Criar grid de temas (2 colunas)
        cols = st.columns(2)
        for idx, (nome, config) in enumerate(TEMAS.items()):
            with cols[idx % 2]:
                selected_class = "theme-card-selected" if st.session_state.temp_tema == nome else ""
                
                if st.button(
                    f"{nome}",
                    key=f"tema_{nome}",
                    use_container_width=True
                ):
                    st.session_state.temp_tema = nome
                    st.rerun()
                
                # Mostrar preview da cor
                st.markdown(f"""
                    <div style='
                        height: 8px; 
                        background: {config["gradient"]}; 
                        border-radius: 4px; 
                        margin-top: -10px;
                        margin-bottom: 10px;
                    '></div>
                """, unsafe_allow_html=True)
        
        st.markdown("<hr style='margin: 2rem 0; border: none; height: 1px; background: #E2E8F0;'>", unsafe_allow_html=True)
        
        # ════════════════════════════════════════════════════════════════════
        # ESCOLHA DE AVATAR
        # ════════════════════════════════════════════════════════════════════
        st.markdown("### Escolha seu Avatar")
        st.markdown("<p style='color: #64748B; margin-bottom: 1.5rem;'>Selecione um emoji que te representa</p>", unsafe_allow_html=True)
        
        # Grid de avatares
        cols_avatar = st.columns(8)
        for idx, emoji in enumerate(AVATARES):
            with cols_avatar[idx % 8]:
                selected_class = "avatar-selected" if st.session_state.temp_avatar == emoji else ""
                
                if st.button(
                    emoji,
                    key=f"avatar_{emoji}",
                    help=f"Selecionar {emoji}"
                ):
                    st.session_state.temp_avatar = emoji
                    st.rerun()
    
    with col2:
        # ════════════════════════════════════════════════════════════════════
        # PREVIEW
        # ════════════════════════════════════════════════════════════════════
        st.markdown("### Preview")
        st.markdown("<p style='color: #64748B; margin-bottom: 1.5rem;'>Veja como ficará seu perfil</p>", unsafe_allow_html=True)
        
        tema_config = TEMAS[st.session_state.temp_tema]
        nome = st.session_state.usuario.get('nome', 'Usuário') if 'usuario' in st.session_state else 'Usuário'
        setor = st.session_state.usuario.get('setor', 'N/A') if 'usuario' in st.session_state else 'N/A'
        
        # Card de preview (igual ao da sidebar)
        st.markdown(f"""
            <div style="
                background: {tema_config['gradient']}; 
                border-radius: 0.75rem; 
                padding: 1.5rem; 
                box-shadow: 0 4px 12px {tema_config['shadow']};
                text-align: center;
            ">
                <div style="
                    width: 80px; 
                    height: 80px; 
                    background: rgba(255, 255, 255, 0.25); 
                    border-radius: 50%; 
                    display: flex; 
                    align-items: center; 
                    justify-content: center; 
                    font-size: 3rem; 
                    margin: 0 auto 1rem auto;
                    border: 3px solid rgba(255, 255, 255, 0.3);
                ">
                    {st.session_state.temp_avatar}
                </div>
                <div style="
                    font-weight: 700; 
                    color: white; 
                    font-size: 1.2rem; 
                    margin-bottom: 0.5rem;
                ">
                    {nome}
                </div>
                <div style="
                    font-size: 0.9rem; 
                    color: rgba(255, 255, 255, 0.9);
                ">
                    {setor}
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
        
        # Botão de salvar
        if st.button("💾 Salvar Preferências", use_container_width=True, type="primary"):
            sucesso, mensagem = salvar_preferencias(
                st.session_state.temp_tema,
                st.session_state.temp_avatar
            )
            
            if sucesso:
                st.success(mensagem)
                st.balloons()
                # Aguardar um pouco antes de recarregar
                import time
                time.sleep(1)
                st.rerun()
            else:
                st.error(mensagem)
        
        # Botão de reset
        if st.button("🔄 Restaurar Padrão", use_container_width=True):
            st.session_state.temp_tema = "Roxo Padrão"
            st.session_state.temp_avatar = "👤"
            st.rerun()
