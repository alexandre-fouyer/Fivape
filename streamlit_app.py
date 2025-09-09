import streamlit as st
import json
import time
from datetime import datetime
import os
import pandas as pd

# Import sécurisé du module
try:
    from prestashop_seo_rewriter import PrestashopSEORewriter
except ImportError:
    st.error("Le module prestashop_seo_rewriter n'est pas trouvé. Assurez-vous que le fichier est présent.")
    st.stop()

# Configuration de la page
st.set_page_config(
    page_title="SEO Rewriter - Le Vapoteur Discount",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé corrigé
st.markdown("""
<style>
    /* Enlever les contours rouges des boutons */
    .stButton > button {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
    }
    .stButton > button:hover {
        background-color: #45a049;
        border: none !important;
    }
    .stButton > button:focus {
        outline: none !important;
        box-shadow: none !important;
        border: none !important;
    }
    
    /* Style pour les zones de texte */
    .stTextArea textarea {
        background-color: white !important;
        color: black !important;
        border: 1px solid #ddd !important;
    }
    
    /* Métriques */
    div[data-testid="metric-container"] {
        background-color: #f0f2f6;
        border: 1px solid #dbdfe9;
        padding: 10px;
        border-radius: 10px;
        margin: 10px 0;
    }
    
    /* Expanders */
    .stExpander {
        border: 1px solid #dbdfe9;
        border-radius: 10px;
        margin: 10px 0;
    }
    
    /* Remove red borders from all inputs */
    .stTextInput > div > div > input {
        border-color: #ddd !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #4CAF50 !important;
        box-shadow: none !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialisation session state
if 'results' not in st.session_state:
    st.session_state.results = None
if 'validations' not in st.session_state:
    st.session_state.validations = {}
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'specific_ids' not in st.session_state:
    st.session_state.specific_ids = None
if 'nb_to_process' not in st.session_state:
    st.session_state.nb_to_process = 5

def get_api_keys():
    """Récupère les clés API de manière sécurisée"""
    try:
        # Production - Streamlit Secrets
        return {
            'prestashop': st.secrets["PRESTASHOP_API_KEY"],
            'openai': st.secrets["OPENAI_API_KEY"],
            'password': st.secrets.get("ADMIN_PASSWORD", "admin"),
            'url': st.secrets.get("PRESTASHOP_URL", "https://www.levapoteur-discount.fr")
        }
    except:
        # Développement local - Variables d'environnement
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            prestashop = os.getenv('PRESTASHOP_API_KEY')
            openai = os.getenv('OPENAI_API_KEY')
            
            if prestashop and openai:
                return {
                    'prestashop': prestashop,
                    'openai': openai,
                    'password': os.getenv('ADMIN_PASSWORD', 'admin'),
                    'url': os.getenv('PRESTASHOP_URL', 'https://www.levapoteur-discount.fr')
                }
        except:
            pass
        
        # Dernier recours - Saisie manuelle
        st.warning("⚠️ Clés API non configurées dans les secrets")
        with st.expander("Configuration manuelle (développement uniquement)"):
            col1, col2 = st.columns(2)
            with col1:
                prestashop = st.text_input("Clé API PrestaShop", type="password", key="manual_prestashop")
            with col2:
                openai = st.text_input("Clé API OpenAI", type="password", key="manual_openai")
            
            if prestashop and openai:
                return {
                    'prestashop': prestashop,
                    'openai': openai,
                    'password': 'admin',
                    'url': 'https://www.levapoteur-discount.fr'
                }
        
        return None

def parse_id_input(id_input):
    """Parse l'entrée des IDs (ex: '1,2,3' ou '1-10' ou '1-10,15,20-25')"""
    if not id_input:
        return []
    
    ids = []
    parts = id_input.replace(' ', '').split(',')
    
    for part in parts:
        if '-' in part:
            # Range d'IDs
            try:
                start, end = part.split('-')
                ids.extend(range(int(start), int(end) + 1))
            except:
                st.warning(f"Format invalide : {part}")
        else:
            # ID unique
            try:
                ids.append(int(part))
            except:
                st.warning(f"ID invalide : {part}")
    
    return list(set(ids))  # Enlever les doublons

# Header
st.title("🚀 Réécriture SEO PrestaShop - Conformité FIVAPE")
st.markdown("---")

# Sidebar pour configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Authentification
    if not st.session_state.authenticated:
        st.subheader("🔐 Connexion")
        password = st.text_input("Mot de passe", type="password", key="auth_password")
        
        if st.button("Se connecter", key="login_btn", type="primary"):
            api_keys = get_api_keys()
            if api_keys and password == api_keys.get('password', 'admin'):
                st.session_state.authenticated = True
                st.success("✅ Connecté avec succès!")
                st.rerun()
            else:
                st.error("❌ Mot de passe incorrect")
    
    else:
        st.success("✅ Connecté")
        
        if st.button("🚪 Déconnexion", key="logout_btn"):
            st.session_state.authenticated = False
            st.session_state.results = None
            st.session_state.validations = {}
            st.rerun()
        
        st.markdown("---")
        st.subheader("📋 Options de traitement")
        
        # Mode de sélection
        selection_mode = st.radio(
            "Mode de sélection",
            ["Par nombre", "Par IDs spécifiques"],
            key="selection_mode"
        )
        
        element_type = st.selectbox(
            "Type d'éléments à traiter",
            ["Produits", "Catégories", "Marques"],
            key="element_type"
        )
        
        if selection_mode == "Par nombre":
            nb_elements = st.number_input(
                "Nombre d'éléments",
                min_value=1,
                max_value=100,
                value=5,
                key="nb_elements",
                help="Nombre d'éléments à traiter (limité à 100)"
            )
            specific_ids = None
        else:
            st.markdown("### Saisir les IDs")
            st.caption("Formats acceptés : '1,2,3' ou '1-10' ou '1-10,15,20-25'")
            
            if element_type == "Produits":
                id_input = st.text_input(
                    "IDs des produits",
                    placeholder="Ex: 424,425,426 ou 424-430",
                    key="product_ids"
                )
            elif element_type == "Catégories":
                id_input = st.text_input(
                    "IDs des catégories",
                    placeholder="Ex: 1,2,3 ou 1-10",
                    key="category_ids"
                )
            else:
                id_input = st.text_input(
                    "IDs des marques",
                    placeholder="Ex: 1,2,3 ou 1-5",
                    key="manufacturer_ids"
                )
            
            specific_ids = parse_id_input(id_input)
            
            if specific_ids:
                st.info(f"📌 {len(specific_ids)} IDs sélectionnés : {', '.join(map(str, specific_ids[:10]))}{' ...' if len(specific_ids) > 10 else ''}")
            
            nb_elements = None
        
        st.markdown("---")
        
        # Bouton de lancement
        if not st.session_state.processing:
            if st.button("🚀 Lancer la réécriture", type="primary", key="launch_btn"):
                api_keys = get_api_keys()
                
                if not api_keys:
                    st.error("❌ Veuillez configurer les clés API")
                elif selection_mode == "Par IDs spécifiques" and not specific_ids:
                    st.error("❌ Veuillez saisir au moins un ID")
                else:
                    st.session_state.processing = True
                    st.session_state.specific_ids = specific_ids
                    st.session_state.nb_to_process = nb_elements
                    st.rerun()
        else:
            st.info("⏳ Traitement en cours...")
        
        # Statistiques dans la sidebar
        if st.session_state.results:
            st.markdown("---")
            st.subheader("📊 Statistiques")
            
            metadata = st.session_state.results['metadata']
            
            st.metric("Produits analysés", metadata.get('total_products_analyzed', 0))
            st.metric("Catégories analysées", metadata.get('total_categories_analyzed', 0))
            st.metric("Marques analysées", metadata.get('total_manufacturers_analyzed', 0))
            st.metric("Total réécrit", metadata.get('items_rewritten', 0))
            
            # Taux de validation
            validation_count = len(st.session_state.validations)
            if metadata.get('items_rewritten', 0) > 0:
                validation_rate = (validation_count / metadata['items_rewritten']) * 100
                st.metric("Taux de validation", f"{validation_rate:.1f}%")

# Zone principale
if st.session_state.authenticated:
    
    # Traitement en cours
    if st.session_state.processing:
        api_keys = get_api_keys()
        
        if not api_keys:
            st.error("❌ Les clés API ne sont pas configurées")
            st.session_state.processing = False
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                status_text.text("Initialisation...")
                
                # Créer l'instance du rewriter
                rewriter = PrestashopSEORewriter(
                    prestashop_url=api_keys['url'],
                    prestashop_key=api_keys['prestashop'],
                    openai_api_key=api_keys['openai']
                )
                
                # Callback pour la progression
                def update_progress(current, total, message):
                    if total > 0:
                        progress = current / total
                        progress_bar.progress(min(progress, 1.0))
                        status_text.text(f"{message} ({current}/{total})")
                
                # Initialiser results
                results = None
                
                # Lancer le traitement selon le mode
                if st.session_state.specific_ids:
                    # Mode IDs spécifiques
                    results = rewriter.run_with_specific_ids(
                        element_type=st.session_state.element_type,
                        specific_ids=st.session_state.specific_ids,
                        progress_callback=update_progress
                    )
                else:
                    # Mode par nombre
                    results = rewriter.run_with_params(
                        element_type=st.session_state.element_type,
                        nb_items=st.session_state.nb_to_process,
                        progress_callback=update_progress
                    )
                
                # Vérifier et stocker les résultats
                if results:
                    st.session_state.results = results
                    st.session_state.processing = False
                    
                    progress_bar.progress(1.0)
                    status_text.text("✅ Traitement terminé!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Aucun résultat retourné")
                    st.session_state.processing = False
                    
            except Exception as e:
                st.session_state.processing = False
                st.error(f"❌ Erreur lors du traitement : {str(e)}")
                st.info("Vérifiez vos clés API et votre connexion internet.")
    
    # Affichage des résultats
    elif st.session_state.results:
        
        # Tabs pour organisation
        tab1, tab2, tab3, tab4 = st.tabs(["📝 Résultats", "✅ Validation", "📊 Analyse", "💾 Export"])
        
        with tab1:
            st.subheader("📝 Résultats de la réécriture")
            
            # Filtres
            col1, col2, col3 = st.columns(3)
            with col1:
                show_type = st.selectbox("Afficher", ["Tout", "Produits", "Catégories", "Marques"])
            with col2:
                show_validated = st.checkbox("Uniquement les validés", value=False)
            with col3:
                search = st.text_input("🔍 Rechercher", placeholder="Nom du produit...")
            
            # Fonction d'affichage améliorée
            def display_items(items, item_type):
                for item in items:
                    if item.get('has_been_rewritten'):
                        # Appliquer les filtres
                        if search and search.lower() not in item['name'].lower():
                            continue
                        
                        item_key = f"{item_type}_{item['id']}"
                        is_validated = item_key in st.session_state.validations
                        
                        if show_validated and not is_validated:
                            continue
                        
                        # Créer un expander pour chaque item
                        icon = "✅" if is_validated else "📦" if item_type == "product" else "📁"
                        
                        with st.expander(
                            f"{icon} {item_type.capitalize()} {item['id']}: {item['name'][:60]}...", 
                            expanded=not is_validated
                        ):
                            # Statistiques de l'item
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Champs réécrits", item['seo_stats']['fields_rewritten'])
                            with col2:
                                st.metric("Mots-clés ajoutés", item['seo_stats']['total_keywords_added'])
                            with col3:
                                if is_validated:
                                    validation_info = st.session_state.validations[item_key]
                                    st.success(f"✅ Validé par {validation_info['validator']}")
                            
                            # Afficher chaque réécriture
                            for rewrite in item['rewrites']:
                                st.markdown(f"### {rewrite['field_name']}")
                                
                                # Statistiques du champ
                                if rewrite['field_name'] in ['Meta titre', 'Meta description']:
                                    metric_label = "caractères"
                                    original_metric = rewrite['stats'].get('original_length', 0)
                                    new_metric = rewrite['stats'].get('new_length', 0)
                                else:
                                    metric_label = "mots"
                                    original_metric = rewrite['stats'].get('original_word_count', 0)
                                    new_metric = rewrite['stats'].get('new_word_count', 0)
                                
                                st.info(f"📊 {original_metric} → {new_metric} {metric_label}")
                                
                                # Mots-clés
                                if rewrite.get('keywords'):
                                    keywords_text = " | ".join([
                                        f"{kw}: {count}x" 
                                        for kw, count in rewrite['keywords'].items() 
                                        if count > 0
                                    ])
                                    if keywords_text:
                                        st.caption(f"🔑 Mots-clés : {keywords_text}")
                                
                                # Comparaison avant/après avec style amélioré
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.markdown("**⌛ AVANT (Non conforme)**")
                                    # Zone de texte avec fond blanc et texte noir
                                    st.markdown(
                                        f"""<div style="background-color: white; color: black; padding: 10px; 
                                        border: 1px solid #ddd; border-radius: 5px; min-height: 100px;">
                                        {html.escape(rewrite['original_text_only'])}</div>""",
                                        unsafe_allow_html=True
                                    )
                                    
                                    if rewrite['field_name'] not in ['Meta titre', 'Meta description'] and rewrite.get('original_content'):
                                        with st.expander("Voir le HTML"):
                                            st.code(rewrite.get('original_content', ''), language='html')
                                
                                with col2:
                                    st.markdown("**✅ APRÈS (Optimisé SEO)**")
                                    # Zone de texte avec fond blanc et texte noir
                                    st.markdown(
                                        f"""<div style="background-color: white; color: black; padding: 10px; 
                                        border: 1px solid #ddd; border-radius: 5px; min-height: 100px;">
                                        {html.escape(rewrite['rewritten_text_only'])}</div>""",
                                        unsafe_allow_html=True
                                    )
                                    
                                    if rewrite['field_name'] not in ['Meta titre', 'Meta description'] and rewrite.get('rewritten_content'):
                                        with st.expander("Voir le HTML"):
                                            st.code(rewrite.get('rewritten_content', ''), language='html')
                            
                            # Bouton de validation
                            if not is_validated:
                                col1, col2, col3 = st.columns([1, 2, 1])
                                with col2:
                                    validator_name = st.text_input(
                                        "Votre nom pour validation",
                                        key=f"validator_{item['id']}"
                                    )
                                    if st.button(
                                        "✅ Valider cet élément",
                                        key=f"validate_{item['id']}",
                                        type="primary"
                                    ):
                                        if validator_name:
                                            st.session_state.validations[item_key] = {
                                                'validated': True,
                                                'timestamp': datetime.now().isoformat(),
                                                'validator': validator_name,
                                                'id': item['id'],
                                                'name': item['name'],
                                                'type': item_type
                                            }
                                            st.success("✅ Élément validé!")
                                            st.rerun()
                                        else:
                                            st.error("Veuillez entrer votre nom")
            
            # Import html pour escape
            import html
            
            # Afficher selon le filtre
            if show_type in ["Tout", "Produits"]:
                if st.session_state.results.get('products'):
                    st.markdown("#### 📦 Produits")
                    display_items(st.session_state.results['products'], 'product')
            
            if show_type in ["Tout", "Catégories"]:
                if st.session_state.results.get('categories'):
                    st.markdown("#### 📁 Catégories")
                    display_items(st.session_state.results['categories'], 'category')
            
            if show_type in ["Tout", "Marques"]:
                if st.session_state.results.get('manufacturers'):
                    st.markdown("#### 🏷️ Marques")
                    display_items(st.session_state.results['manufacturers'], 'manufacturer')
        
        with tab2:
            st.subheader("✅ Gestion des validations")
            
            if st.session_state.validations:
                # Statistiques de validation
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total validé", len(st.session_state.validations))
                with col2:
                    # Compter par type
                    types_count = {}
                    for v in st.session_state.validations.values():
                        t = v.get('type', 'unknown')
                        types_count[t] = types_count.get(t, 0) + 1
                    st.metric("Par type", ", ".join([f"{k}: {v}" for k, v in types_count.items()]))
                with col3:
                    # Validateurs uniques
                    validators = set([v.get('validator', '') for v in st.session_state.validations.values()])
                    st.metric("Validateurs", len(validators))
                
                st.markdown("---")
                
                # Tableau des validations
                if st.session_state.validations:
                    df_data = []
                    for key, validation in st.session_state.validations.items():
                        df_data.append({
                            'Type': validation.get('type', ''),
                            'ID': validation.get('id', ''),
                            'Nom': validation.get('name', '')[:50],
                            'Validateur': validation.get('validator', ''),
                            'Date': validation.get('timestamp', '')[:10]
                        })
                    
                    df = pd.DataFrame(df_data)
                    st.dataframe(df, use_container_width=True)
                    
                    # Actions
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        json_str = json.dumps(st.session_state.validations, indent=2, ensure_ascii=False)
                        st.download_button(
                            label="💾 Télécharger JSON",
                            data=json_str,
                            file_name=f"validations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )
                    
                    with col2:
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label="📊 Télécharger CSV",
                            data=csv,
                            file_name=f"validations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    
                    with col3:
                        if st.button("🗑️ Réinitialiser", key="reset_validations"):
                            st.session_state.validations = {}
                            st.success("Validations réinitialisées")
                            st.rerun()
            else:
                st.info("Aucune validation pour le moment. Validez des éléments dans l'onglet Résultats.")
        
        with tab3:
            st.subheader("📊 Analyse détaillée")
            
            if st.session_state.results:
                # Métriques globales
                st.markdown("### 🎯 Vue d'ensemble")
                
                col1, col2, col3, col4 = st.columns(4)
                
                metadata = st.session_state.results['metadata']
                
                with col1:
                    total_analyzed = (
                        metadata.get('total_products_analyzed', 0) +
                        metadata.get('total_categories_analyzed', 0) +
                        metadata.get('total_manufacturers_analyzed', 0)
                    )
                    st.metric("Total analysé", total_analyzed)
                
                with col2:
                    st.metric("Éléments réécrits", metadata.get('items_rewritten', 0))
                
                with col3:
                    validation_count = len(st.session_state.validations)
                    st.metric("Éléments validés", validation_count)
                
                with col4:
                    if metadata.get('items_rewritten', 0) > 0:
                        completion_rate = (validation_count / metadata['items_rewritten']) * 100
                        st.metric("Taux de complétion", f"{completion_rate:.1f}%")
                    else:
                        st.metric("Taux de complétion", "0%")
                
                # Graphique de progression
                st.markdown("### 📈 Progression de validation")
                
                progress_data = {
                    'Type': ['Produits', 'Catégories', 'Marques'],
                    'Analysés': [
                        metadata.get('total_products_analyzed', 0),
                        metadata.get('total_categories_analyzed', 0),
                        metadata.get('total_manufacturers_analyzed', 0)
                    ],
                    'Validés': [0, 0, 0]
                }
                
                # Compter les validations par type
                for validation in st.session_state.validations.values():
                    if validation.get('type') == 'product':
                        progress_data['Validés'][0] += 1
                    elif validation.get('type') == 'category':
                        progress_data['Validés'][1] += 1
                    elif validation.get('type') == 'manufacturer':
                        progress_data['Validés'][2] += 1
                
                df_progress = pd.DataFrame(progress_data)
                st.bar_chart(df_progress.set_index('Type'))
                
                # Analyse des mots-clés
                st.markdown("### 🔑 Analyse des mots-clés SEO")
                
                total_keywords = {}
                for product in st.session_state.results.get('products', []):
                    for rewrite in product.get('rewrites', []):
                        for keyword, count in rewrite.get('keywords', {}).items():
                            total_keywords[keyword] = total_keywords.get(keyword, 0) + count
                
                if total_keywords:
                    df_keywords = pd.DataFrame(
                        list(total_keywords.items()),
                        columns=['Mot-clé', 'Occurrences']
                    ).sort_values('Occurrences', ascending=False)
                    
                    st.bar_chart(df_keywords.set_index('Mot-clé'))
                else:
                    st.info("Aucun mot-clé SEO détecté")
        
        with tab4:
            st.subheader("💾 Export des données")
            
            # Export complet
            st.markdown("### 📦 Export complet")
            
            col1, col2 = st.columns(2)
            
            with col1:
                json_str = json.dumps(st.session_state.results, indent=2, ensure_ascii=False)
                st.download_button(
                    label="💾 Télécharger résultats JSON",
                    data=json_str,
                    file_name=f"resultats_complets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            
            with col2:
                # Export pour PrestaShop (validés uniquement)
                if st.session_state.validations:
                    validated_items = []
                    
                    for key, validation in st.session_state.validations.items():
                        item_type = validation.get('type')
                        item_id = validation.get('id')
                        
                        # Retrouver l'item complet
                        if item_type == 'product':
                            items = st.session_state.results.get('products', [])
                        elif item_type == 'category':
                            items = st.session_state.results.get('categories', [])
                        else:
                            items = st.session_state.results.get('manufacturers', [])
                        
                        for item in items:
                            if item['id'] == item_id:
                                validated_items.append({
                                    'type': item_type,
                                    'id': item_id,
                                    'name': item['name'],
                                    'rewrites': item['rewrites']
                                })
                                break
                    
                    export_data = {
                        'timestamp': datetime.now().isoformat(),
                        'validated_count': len(validated_items),
                        'items': validated_items
                    }
                    
                    json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
                    st.download_button(
                        label="💾 Export PrestaShop (validés)",
                        data=json_str,
                        file_name=f"prestashop_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
                else:
                    st.info("Aucun élément validé à exporter")
    
    else:
        # Aucun résultat
        st.info("👈 Configurez les options et lancez la réécriture depuis le menu latéral")
        
        # Guide d'utilisation
        with st.expander("📖 Guide d'utilisation"):
            st.markdown("""
            ### Comment utiliser l'application :
            
            1. **Connexion** : Entrez le mot de passe dans le menu latéral
            2. **Sélection** : 
               - **Par nombre** : Traite les X premiers éléments
               - **Par IDs** : Traite des IDs spécifiques (ex: 424,425 ou 424-430)
            3. **Lancement** : Cliquez sur "Lancer la réécriture"
            4. **Validation** : Examinez les résultats et validez les éléments conformes
            5. **Export** : Téléchargez les données validées pour PrestaShop
            
            ### Formats d'IDs acceptés :
            - IDs individuels : `424,425,426`
            - Plages d'IDs : `424-430`
            - Combinaison : `424-430,435,440-445`
            
            ### Conformité FIVAPE :
            - Suppression automatique des termes promotionnels
            - Conservation des informations techniques uniquement
            - Optimisation SEO avec mots-clés neutres
            """)

else:
    # Non authentifié
    st.info("🔐 Veuillez vous connecter dans le menu latéral pour accéder à l'application")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #888;'>
        SEO Rewriter v1.0 - Le Vapoteur Discount | 
        Conformité FIVAPE | 
        Optimisation SEO
    </div>
    """,
    unsafe_allow_html=True
)