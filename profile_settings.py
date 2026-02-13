"""
profile_settings.py — Configurações de Perfil do Usuário
Permite personalizar cor do tema e avatar + CRIAR GRADIENTES PERSONALIZADOS
"""

import streamlit as st

# ============================================================================
# TEMAS DE CORES PADRÃO (DISPONÍVEIS PARA TODOS)
# ============================================================================

TEMAS_PADRAO = {
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
    "🐱", "🐶", "🦊", "🐼", "🐨", "🦁", "🐯", "🦄", "🐰", "🐣", "🐸", "🐧", "🐙", "🐝",
    # Fantasia e Diversão
    "🦸", "🧙", "👻", "👾", "🤖", "👽", "🧜", "🧚",
    # Natureza e Comida (Vibe leve)
    "🍀", "🌸", "🌵", "🌈", "🍦", "🍩", "🍓", "🍕", "🥑",
    # Símbolos e Objetos
    "⭐", "🌟", "💫", "✨", "🔥", "💎", "🎯", "🚀", "🐍", "🪐", "🎨", "🎮", "🎸"
]

# ============================================================================
# FUNÇÕES PARA GRADIENTES PERSONALIZADOS
# ============================================================================

def hex_to_rgba(hex_color: str, alpha: float = 0.25) -> str:
    """Converte cor hexadecimal para rgba com transparência."""
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"


def criar_gradiente_css(cores: list) -> str:
    """
    Cria um gradiente CSS com 2 a 4 cores distribuídas uniformemente.
    
    Args:
        cores: Lista de cores em hexadecimal (2 a 4 cores)
    
    Returns:
        String CSS do gradiente linear
    """
    # Remove cores vazias/None
    cores = [c for c in cores if c]
    
    if len(cores) < 2:
        cores = [cores[0], cores[0]] if cores else ["#8B5CF6", "#7C3AED"]
    
    num_cores = len(cores)
    porcentagens = [i * (100 / (num_cores - 1)) for i in range(num_cores)]
    
    stops = [f"{cor} {pct:.0f}%" for cor, pct in zip(cores, porcentagens)]
    return f"linear-gradient(135deg, {', '.join(stops)})"


def carregar_gradientes_personalizados(user_id: str) -> dict:
    """Carrega gradientes personalizados do usuário do Supabase."""
    from auth import get_supabase_client
    
    try:
        supabase = get_supabase_client()
        response = supabase.table('custom_gradients').select('*').eq('user_id', user_id).execute()
        
        gradientes = {}
        if response.data:
            for grad in response.data:
                nome = grad.get('nome_gradiente')
                color_light = grad.get('color_light')
                color_dark = grad.get('color_dark')
                color3 = grad.get('color3')  # Terceira cor (opcional)
                color4 = grad.get('color4')  # Quarta cor (opcional)
                
                # Cria lista de cores (remove None/vazias)
                cores = [c for c in [color_light, color_dark, color3, color4] if c]
                
                gradientes[nome] = {
                    "gradient": criar_gradiente_css(cores),
                    "color_light": color_light,
                    "color_dark": color_dark,
                    "color3": color3,
                    "color4": color4,
                    "shadow": hex_to_rgba(cores[-1], 0.25),  # Usa a última cor para sombra
                    "custom": True,  # Flag para identificar que é personalizado
                    "id": grad.get('id')  # ID para poder deletar
                }
        
        return gradientes
        
    except Exception as e:
        print(f"Erro ao carregar gradientes personalizados: {e}")
        return {}


def salvar_gradiente_personalizado(user_id: str, nome: str, color_light: str, color_dark: str, color3: str = None, color4: str = None) -> tuple[bool, str]:
    """Salva um novo gradiente personalizado no Supabase com 2 a 4 cores."""
    from auth import get_supabase_client
    
    try:
        supabase = get_supabase_client()
        
        # Verifica se já existe um gradiente com esse nome para o usuário
        check = supabase.table('custom_gradients').select('*').eq('user_id', user_id).eq('nome_gradiente', nome).execute()
        
        if check.data:
            return False, "Você já tem um gradiente com esse nome. Escolha outro nome."
        
        # Salva o novo gradiente (color3 e color4 são opcionais)
        dados = {
            'user_id': user_id,
            'nome_gradiente': nome,
            'color_light': color_light,
            'color_dark': color_dark
        }
        
        # Adiciona cores opcionais se fornecidas
        if color3:
            dados['color3'] = color3
        if color4:
            dados['color4'] = color4
        
        supabase.table('custom_gradients').insert(dados).execute()
        
        num_cores = 2 + (1 if color3 else 0) + (1 if color4 else 0)
        return True, f"Gradiente personalizado com {num_cores} cores criado com sucesso! 🎨"
        
    except Exception as e:
        return False, f"Erro ao salvar gradiente: {str(e)}"


def deletar_gradiente_personalizado(gradient_id: int) -> tuple[bool, str]:
    """Deleta um gradiente personalizado do Supabase."""
    from auth import get_supabase_client
    
    try:
        supabase = get_supabase_client()
        supabase.table('custom_gradients').delete().eq('id', gradient_id).execute()
        return True, "Gradiente deletado com sucesso!"
        
    except Exception as e:
        return False, f"Erro ao deletar gradiente: {str(e)}"


def obter_todos_temas(user_id: str = None) -> dict:
    """
    Retorna todos os temas disponíveis: padrões + personalizados do usuário.
    Se user_id for None, retorna apenas temas padrão.
    """
    temas = TEMAS_PADRAO.copy()
    
    if user_id:
        gradientes_personalizados = carregar_gradientes_personalizados(user_id)
        temas.update(gradientes_personalizados)
    
    return temas


# Variável global TEMAS (para compatibilidade com código existente)
# Será atualizada dinamicamente quando o usuário estiver logado
TEMAS = TEMAS_PADRAO.copy()


# ============================================================================
# FUNÇÕES DE GERENCIAMENTO DE PREFERÊNCIAS
# ============================================================================

def carregar_preferencias():
    """Carrega as preferências do usuário do Supabase ou retorna padrões."""
    from auth import get_supabase_client
    
    if 'usuario' not in st.session_state:
        return {
            "tema": "Roxo Padrão",
            "avatar": "👤",
            "tema_config": TEMAS_PADRAO['Roxo Padrão']
        }
    
    try:
        supabase = get_supabase_client()
        user_id = st.session_state.usuario['id']
        
        response = supabase.table('user_preferences').select('*').eq('user_id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            prefs = response.data[0]
            tema_nome = prefs.get('tema', 'Roxo Padrão')
            avatar = prefs.get('avatar', '👤')
            
            # Verifica se o tema é um padrão ou personalizado
            tema_config = TEMAS_PADRAO.get(tema_nome)
            
            if not tema_config:
                # É um gradiente personalizado, busca na tabela custom_gradients
                gradientes_personalizados = carregar_gradientes_personalizados(user_id)
                tema_config = gradientes_personalizados.get(tema_nome, TEMAS_PADRAO['Roxo Padrão'])
            
            return {
                "tema": tema_nome,
                "avatar": avatar,
                "tema_config": tema_config
            }
    except Exception as e:
        pass
    
    return {
        "tema": "Roxo Padrão", 
        "avatar": "👤",
        "tema_config": TEMAS_PADRAO['Roxo Padrão']
    }


def salvar_preferencias(tema: str, avatar: str) -> tuple[bool, str]:
    """Salva as preferências do usuário no Supabase."""
    from auth import get_supabase_client

    if 'usuario' not in st.session_state:
        return False, "Usuário não autenticado"
    
    try:
        supabase = get_supabase_client()
        user_id = st.session_state.usuario['id']
        nome = st.session_state.usuario.get('nome', 'Usuário')
        setor = st.session_state.usuario.get('setor', 'N/A')
        email = st.session_state.usuario.get('email', '')
        
        dados = {
            'user_id': user_id,
            'tema': tema,
            'avatar': avatar,
            'nome': nome,
            'setor': setor,
            'email': email
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
    
    # Atualiza TEMAS global com gradientes personalizados do usuário
    global TEMAS
    if 'usuario' in st.session_state:
        user_id = st.session_state.usuario['id']
        TEMAS = obter_todos_temas(user_id)
    else:
        TEMAS = TEMAS_PADRAO.copy()
    
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
        }
        
        .avatar-selected {
            border: 3px solid #7C3AED !important;
            background: #F3F4F6 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("<h1 class='profile-header'>Configurações de Perfil</h1>", unsafe_allow_html=True)
    st.markdown("<p class='profile-subtitle'>Personalize sua experiência no StarCheck</p>", unsafe_allow_html=True)
    
    # Inicializa variáveis temporárias se não existirem
    if 'temp_tema' not in st.session_state:
        prefs = carregar_preferencias()
        st.session_state.temp_tema = prefs['tema']
    
    if 'temp_avatar' not in st.session_state:
        prefs = carregar_preferencias()
        st.session_state.temp_avatar = prefs['avatar']
    
    # ════════════════════════════════════════════════════════════════════
    # TABS: PERSONALIZAÇÃO | CRIAR GRADIENTE
    # ════════════════════════════════════════════════════════════════════
    tab_personalizar, tab_criar = st.tabs(["🎨 Personalizar", "✨ Criar Gradiente"])
    
    # ════════════════════════════════════════════════════════════════════
    # TAB: PERSONALIZAR (Código original)
    # ════════════════════════════════════════════════════════════════════
    with tab_personalizar:
        col1, col2 = st.columns([1.5, 1], gap="large")
        
        with col1:
            # ════════════════════════════════════════════════════════════════════
            # ESCOLHA DE TEMA - CARDS CLICÁVEIS
            # ════════════════════════════════════════════════════════════════════
            st.markdown("### Escolha seu Tema")
            st.markdown("<p style='color: #64748B; margin-bottom: 1.5rem;'>Clique no gradiente para selecioná-lo</p>", unsafe_allow_html=True)
            
            # Grid de temas (3 colunas)
            cols_tema = st.columns(3)
            
            for idx, (nome_tema, config) in enumerate(TEMAS.items()):
                with cols_tema[idx % 3]:
                    is_custom = config.get('custom', False)
                    selected = st.session_state.temp_tema == nome_tema
                    
                    # Indicadores visuais
                    check = "✓ " if selected else ""
                    badge = " 🎨" if is_custom else ""
                    border_color = "#7C3AED" if selected else "#E5E7EB"
                    border_width = "4px" if selected else "2px"
                    opacity = "0.9" if selected else "1"
                    
                    # HTML do card (não clicável, apenas visual)
                    st.markdown(f"""
                    <div style="
                        background: {config['gradient']};
                        border-radius: 0.75rem;
                        padding: 1.5rem 1rem;
                        border: {border_width} solid {border_color};
                        box-shadow: 0 2px 8px {config['shadow']};
                        min-height: 100px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        margin-bottom: 0.5rem;
                        opacity: {opacity};
                        transition: all 0.2s ease;
                        position: relative;
                    ">
                        <div style="
                            color: white;
                            font-weight: 700;
                            font-size: 0.95rem;
                            text-align: center;
                            text-shadow: 0 1px 3px rgba(0,0,0,0.3);
                        ">
                            {check}{nome_tema}{badge}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Botões de ação abaixo do card
                    if is_custom:
                        # Personalizado: selecionar + deletar
                        col_sel, col_del = st.columns([4, 1])
                        with col_sel:
                            if st.button(
                                "Selecionar" if not selected else "Selecionado",
                                key=f"sel_{idx}",
                                disabled=selected,
                                use_container_width=True,
                                type="primary" if selected else "secondary"
                            ):
                                st.session_state.temp_tema = nome_tema
                                st.rerun()
                        with col_del:
                            if st.button("🗑️", key=f"del_{idx}", use_container_width=True, help="Deletar"):
                                gradient_id = config.get('id')
                                sucesso, msg = deletar_gradiente_personalizado(gradient_id)
                                if sucesso:
                                    st.success(msg)
                                    if st.session_state.temp_tema == nome_tema:
                                        st.session_state.temp_tema = "Roxo Padrão"
                                    st.rerun()
                                else:
                                    st.error(msg)
                    else:
                        # Padrão: apenas selecionar
                        if st.button(
                            "Selecionar" if not selected else "Selecionado",
                            key=f"sel_{idx}",
                            disabled=selected,
                            use_container_width=True,
                            type="primary" if selected else "secondary"
                        ):
                            st.session_state.temp_tema = nome_tema
                            st.rerun()
                    
                    st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
            
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
            if st.button("💾 Salvar Preferências", use_container_width=True, type="primary", key="salvar_prefs"):
                sucesso, mensagem = salvar_preferencias(
                    st.session_state.temp_tema,
                    st.session_state.temp_avatar
                )
                
                if sucesso:
                    st.success(mensagem)
                    st.balloons()
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
    
    # ════════════════════════════════════════════════════════════════════
    # TAB: CRIAR GRADIENTE PERSONALIZADO
    # ════════════════════════════════════════════════════════════════════
    with tab_criar:
        st.markdown("### ✨ Crie seu Gradiente Personalizado")
        st.markdown("<p style='color: #64748B; margin-bottom: 2rem;'>Escolha de 2 até 4 cores e crie um gradiente único que só você terá!</p>", unsafe_allow_html=True)
        
        col_criar1, col_criar2 = st.columns([1.5, 1], gap="large")
        
        with col_criar1:
            # Inicializa cores no session_state se não existirem
            if 'preview_cor1' not in st.session_state:
                st.session_state.preview_cor1 = '#8B5CF6'
            if 'preview_cor2' not in st.session_state:
                st.session_state.preview_cor2 = '#7C3AED'
            if 'preview_cor3' not in st.session_state:
                st.session_state.preview_cor3 = None
            if 'preview_cor4' not in st.session_state:
                st.session_state.preview_cor4 = None
            if 'usar_cor3' not in st.session_state:
                st.session_state.usar_cor3 = False
            if 'usar_cor4' not in st.session_state:
                st.session_state.usar_cor4 = False
            
            # Seletor de número de cores
            st.markdown("#### 🎨 Número de Cores no Gradiente")
            num_cores = st.radio(
                "Escolha quantas cores usar:",
                options=[2, 3, 4],
                horizontal=True,
                help="Você pode criar gradientes com 2, 3 ou 4 cores"
            )
            
            st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
            st.markdown("#### 🎨 Escolha as Cores")
            
            # Sempre mostra as duas primeiras cores
            col_cor1, col_cor2 = st.columns(2)
            
            with col_cor1:
                cor_inicial = st.color_picker(
                    "🎨 Cor 1 (Inicial)",
                    value=st.session_state.preview_cor1,
                    help="Primeira cor do gradiente",
                    key="color_picker_1"
                )
                st.session_state.preview_cor1 = cor_inicial
            
            with col_cor2:
                cor_final = st.color_picker(
                    "🎨 Cor 2",
                    value=st.session_state.preview_cor2,
                    help="Segunda cor do gradiente",
                    key="color_picker_2"
                )
                st.session_state.preview_cor2 = cor_final
            
            # Mostra cor 3 se selecionado 3 ou 4 cores
            if num_cores >= 3:
                st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
                col_cor3, col_cor4 = st.columns(2)
                
                with col_cor3:
                    if st.session_state.preview_cor3 is None:
                        st.session_state.preview_cor3 = '#EC4899'
                    
                    cor3 = st.color_picker(
                        "🎨 Cor 3",
                        value=st.session_state.preview_cor3,
                        help="Terceira cor do gradiente",
                        key="color_picker_3"
                    )
                    st.session_state.preview_cor3 = cor3
                
                # Mostra cor 4 se selecionado 4 cores
                if num_cores == 4:
                    with col_cor4:
                        if st.session_state.preview_cor4 is None:
                            st.session_state.preview_cor4 = '#F97316'
                        
                        cor4 = st.color_picker(
                            "🎨 Cor 4 (Final)",
                            value=st.session_state.preview_cor4,
                            help="Quarta cor do gradiente",
                            key="color_picker_4"
                        )
                        st.session_state.preview_cor4 = cor4
                else:
                    st.session_state.preview_cor4 = None
            else:
                st.session_state.preview_cor3 = None
                st.session_state.preview_cor4 = None
            
            st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
            
            # Formulário apenas com nome e botão de criar
            with st.form("form_criar_gradiente", clear_on_submit=True):
                nome_gradiente = st.text_input(
                    "🏷️ Nome do Gradiente",
                    placeholder="Ex: Meu Azul Favorito, Sunset Vibes...",
                    max_chars=30
                )
                
                st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
                
                submit_criar = st.form_submit_button(
                    "✨ Criar Gradiente",
                    use_container_width=True,
                    type="primary"
                )
                
                if submit_criar:
                    if not nome_gradiente or len(nome_gradiente.strip()) < 3:
                        st.error("⚠️ O nome deve ter pelo menos 3 caracteres.")
                    elif nome_gradiente in TEMAS_PADRAO:
                        st.error("⚠️ Esse nome já está sendo usado por um tema padrão. Escolha outro.")
                    elif 'usuario' not in st.session_state:
                        st.error("⚠️ Você precisa estar logado para criar gradientes.")
                    else:
                        user_id = st.session_state.usuario['id']
                        
                        # Prepara as cores baseado na seleção
                        cor3_salvar = st.session_state.preview_cor3 if num_cores >= 3 else None
                        cor4_salvar = st.session_state.preview_cor4 if num_cores == 4 else None
                        
                        sucesso, msg = salvar_gradiente_personalizado(
                            user_id,
                            nome_gradiente.strip(),
                            st.session_state.preview_cor1,
                            st.session_state.preview_cor2,
                            cor3_salvar,
                            cor4_salvar
                        )
                        
                        if sucesso:
                            st.success(msg)
                            st.balloons()
                            import time
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(msg)
        
        with col_criar2:
            # Preview do gradiente sendo criado
            st.markdown("### Preview em Tempo Real")
            
            # Cria lista de cores para o preview
            cores_preview = [st.session_state.preview_cor1, st.session_state.preview_cor2]
            if num_cores >= 3 and st.session_state.preview_cor3:
                cores_preview.append(st.session_state.preview_cor3)
            if num_cores == 4 and st.session_state.preview_cor4:
                cores_preview.append(st.session_state.preview_cor4)
            
            gradient_preview = criar_gradiente_css(cores_preview)
            shadow_preview = hex_to_rgba(cores_preview[-1], 0.25)
            
            nome = st.session_state.usuario.get('nome', 'Usuário') if 'usuario' in st.session_state else 'Usuário'
            setor = st.session_state.usuario.get('setor', 'N/A') if 'usuario' in st.session_state else 'N/A'
            
            st.markdown(f"""
                <div style="
                    background: {gradient_preview}; 
                    border-radius: 0.75rem; 
                    padding: 1.5rem; 
                    box-shadow: 0 4px 12px {shadow_preview};
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
            
            st.info("💡 **Dica**: Com 2 cores, experimente cores complementares. Com 3-4 cores, crie transições suaves usando tons intermediários ou faça gradientes ousados com cores contrastantes!")
    
    # ════════════════════════════════════════════════════════════════════
    # SEÇÃO DE USUÁRIOS DA PLATAFORMA (full width abaixo do layout)
    # ════════════════════════════════════════════════════════════════════
    st.markdown("<hr style='margin: 3rem 0 2rem 0; border: none; height: 1px; background: #E2E8F0;'>", unsafe_allow_html=True)
    
    st.markdown("### 👥 Usuários da Plataforma")
    st.markdown("<p style='color: #64748B; margin-bottom: 1.5rem;'>Veja quem está usando o StarCheck e como personalizaram seus perfis</p>", unsafe_allow_html=True)
    
    # Buscar todos os usuários com preferências
    from auth import get_supabase_client
    
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('user_preferences').select('*').execute()
        
        if response.data and len(response.data) > 0:
            num_cols = 4
            cols = st.columns(num_cols)
            
            for idx, user_pref in enumerate(response.data):
                with cols[idx % num_cols]:
                    tema_nome = user_pref.get('tema', 'Roxo Padrão')
                    avatar = user_pref.get('avatar', '👤')
                    nome = user_pref.get('nome', 'Usuário')
                    setor = user_pref.get('setor', 'N/A')
                    user_id_display = user_pref.get('user_id', '')
                    
                    # Busca o tema (pode ser padrão ou personalizado)
                    tema_config = TEMAS_PADRAO.get(tema_nome)
                    display_nome = tema_nome
                    
                    # Se não encontrou nos padrões, busca nos gradientes personalizados desse usuário
                    if not tema_config and user_id_display:
                        gradientes_user = carregar_gradientes_personalizados(user_id_display)
                        tema_config = gradientes_user.get(tema_nome)
                        if tema_config:
                            display_nome = f"{tema_nome} 🎨"
                    
                    # Se ainda não encontrou, usa padrão como fallback
                    if not tema_config:
                        tema_config = TEMAS_PADRAO['Roxo Padrão']
                        display_nome = "Tema Personalizado 🎨"
                    
                    # Card compacto do usuário
                    st.markdown(f"""
                        <div style="
                            background: {tema_config['gradient']}; 
                            border-radius: 0.75rem; 
                            padding: 1.25rem; 
                            box-shadow: 0 2px 8px {tema_config['shadow']};
                            text-align: center;
                            min-height: 160px;
                            display: flex;
                            flex-direction: column;
                            justify-content: center;
                        ">
                            <div style="
                                width: 50px; 
                                height: 50px; 
                                background: rgba(255, 255, 255, 0.25); 
                                border-radius: 50%; 
                                display: flex; 
                                align-items: center; 
                                justify-content: center; 
                                font-size: 1.8rem; 
                                margin: 0 auto 0.75rem auto;
                                border: 2px solid rgba(255, 255, 255, 0.3);
                            ">
                                {avatar}
                            </div>
                            <div style="
                                font-weight: 600; 
                                color: white; 
                                font-size: 0.9rem; 
                                margin-bottom: 0.25rem;
                                white-space: nowrap;
                                overflow: hidden;
                                text-overflow: ellipsis;
                            ">
                                {nome}
                            </div>
                            <div style="
                                font-size: 0.75rem; 
                                color: rgba(255, 255, 255, 0.85);
                                margin-bottom: 0.5rem;
                            ">
                                {setor}
                            </div>
                            <div style="
                                font-size: 0.7rem; 
                                color: rgba(255, 255, 255, 0.7);
                                background: rgba(255, 255, 255, 0.15);
                                padding: 0.25rem 0.5rem;
                                border-radius: 0.5rem;
                                display: inline-block;
                                margin: 0 auto;
                            ">
                                {display_nome}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
            
        else:
            st.info("Nenhum usuário personalizou seu perfil ainda. Seja o primeiro!")
            
    except Exception as e:
        st.warning("Não foi possível carregar a lista de usuários no momento.")
