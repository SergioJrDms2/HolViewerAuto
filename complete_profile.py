"""
complete_profile.py - Modal/Card para usuários completarem o perfil
Aparece quando usuário não tem nome/setor cadastrado
"""

import streamlit as st
from auth import get_supabase_client
from profile_settings import TEMAS

def verificar_perfil_completo() -> bool:
    """Verifica se o usuário tem perfil completo (nome e setor)."""
    if 'usuario' not in st.session_state:
        return True
    
    try:
        supabase = get_supabase_client()
        user_id = st.session_state.usuario['id']
        
        response = supabase.table('user_preferences').select('*').eq('user_id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            pref = response.data[0]
            nome = pref.get('nome', '')
            setor = pref.get('setor', '')
            
            # Verifica se tem dados válidos (não vazio, não "Usuário", não "N/A")
            nome_valido = nome and nome != 'Usuário' and len(nome.strip()) > 0
            setor_valido = setor and setor != 'N/A' and len(setor.strip()) > 0
            
            return nome_valido and setor_valido
        
        return False
        
    except Exception as e:
        print(f"Erro ao verificar perfil: {str(e)}")
        return False


def render_complete_profile_modal():
    """Renderiza modal/banner para completar perfil."""
    
    if verificar_perfil_completo():
        return  # Perfil já está completo
    
    # Banner chamativo no topo
    st.markdown("""
        <div style='
            background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
            padding: 1rem 1.5rem;
            border-radius: 0.75rem;
            margin-bottom: 1.5rem;
            border: 2px solid #FBBF24;
            box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
        '>
            <div style='display: flex; align-items: center; gap: 1rem;'>
                <div style='font-size: 2rem;'>⚠️</div>
                <div>
                    <div style='font-weight: 700; color: white; font-size: 1.1rem; margin-bottom: 0.25rem;'>
                        Complete seu Perfil
                    </div>
                    <div style='color: rgba(255, 255, 255, 0.95); font-size: 0.9rem;'>
                        Adicione seu nome e setor para que outros usuários possam te identificar!
                    </div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Formulário compacto
    with st.expander("✏️ Completar Agora", expanded=True):
        with st.form("complete_profile_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                nome_input = st.text_input(
                    "👤 Seu Nome",
                    placeholder="Ex: João Silva",
                    help="Como você quer ser chamado na plataforma"
                )
            
            with col2:
                setor_input = st.text_input(
                    "🏢 Seu Setor",
                    placeholder="Ex: Comercial, TI, Crédito",
                    help="Área ou departamento onde você trabalha"
                )
            
            submit = st.form_submit_button("💾 Salvar e Continuar", use_container_width=True, type="primary")
            
            if submit:
                if not nome_input or len(nome_input.strip()) < 3:
                    st.error("⚠️ Por favor, insira seu nome (mínimo 3 caracteres)")
                elif not setor_input or len(setor_input.strip()) < 2:
                    st.error("⚠️ Por favor, insira seu setor")
                else:
                    # Salvar dados
                    try:
                        supabase = get_supabase_client()
                        user_id = st.session_state.usuario['id']
                        email = st.session_state.usuario.get('email', '')
                        
                        # Busca preferências existentes
                        pref_response = supabase.table('user_preferences').select('*').eq('user_id', user_id).execute()
                        
                        if pref_response.data and len(pref_response.data) > 0:
                            # Atualiza mantendo tema e avatar
                            pref = pref_response.data[0]
                            dados = {
                                'user_id': user_id,
                                'nome': nome_input.strip(),
                                'setor': setor_input.strip(),
                                'email': email,
                                'tema': pref.get('tema', 'Roxo Padrão'),
                                'avatar': pref.get('avatar', '👤')
                            }
                        else:
                            # Cria novo
                            dados = {
                                'user_id': user_id,
                                'nome': nome_input.strip(),
                                'setor': setor_input.strip(),
                                'email': email,
                                'tema': 'Roxo Padrão',
                                'avatar': '👤'
                            }
                        
                        supabase.table('user_preferences').upsert(dados, on_conflict='user_id').execute()
                        
                        # Atualiza session state
                        st.session_state.usuario['nome'] = nome_input.strip()
                        st.session_state.usuario['setor'] = setor_input.strip()
                        
                        st.success("✅ Perfil atualizado com sucesso!")
                        st.balloons()
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Erro ao salvar: {str(e)}")


# Para usar no app.py ou main.py:
# 
# if verificar_sessao():
#     render_complete_profile_modal()
#     # resto do app...
