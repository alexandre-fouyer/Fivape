import requests
import re
import json
import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from requests.auth import HTTPBasicAuth
import openai
import html
from bs4 import BeautifulSoup

class PrestashopSEORewriter:
    def __init__(self, prestashop_url: str, prestashop_key: str, openai_api_key: str):
        """
        Initialise le système de réécriture SEO complète pour PrestaShop
        Conformité FIVAPE + Optimisation SEO avancée
        """
        self.prestashop_url = prestashop_url.rstrip('/')
        self.prestashop_key = prestashop_key
        
        # Configuration OpenAI
        openai.api_key = openai_api_key
        self.openai_client = openai
        
        # Stockage des résultats
        self.results = {
            'metadata': {
                'date': datetime.now().isoformat(),
                'url': prestashop_url,
                'total_products_analyzed': 0,
                'total_categories_analyzed': 0,
                'total_manufacturers_analyzed': 0,
                'items_rewritten': 0,
                'seo_improvements': 0
            },
            'products': [],
            'categories': [],
            'manufacturers': [],
            'errors': []
        }

    def extract_and_preserve_html(self, html_content: str) -> Tuple[str, Dict]:
        """
        Extrait le texte tout en préservant la structure HTML, images et liens
        """
        if not html_content:
            return "", {}
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Préserver les images
            images = []
            for img in soup.find_all('img'):
                images.append({
                    'src': img.get('src', ''),
                    'alt': img.get('alt', ''),
                    'title': img.get('title', '')
                })
            
            # Préserver les liens
            links = []
            for link in soup.find_all('a'):
                links.append({
                    'href': link.get('href', ''),
                    'text': link.get_text(),
                    'title': link.get('title', '')
                })
            
            # Structure HTML
            structure = {
                'images': images,
                'links': links,
                'has_lists': bool(soup.find_all(['ul', 'ol'])),
                'has_headings': bool(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])),
                'original_html': html_content
            }
            
            # Texte pour analyse
            text = soup.get_text(separator=' ', strip=True)
            
            return text, structure
            
        except Exception as e:
            return html_content, {'original_html': html_content}

    def rewrite_content_with_seo(self, content: str, field_type: str, item_name: str, 
                                 item_type: str, html_structure: Dict) -> Tuple[str, Dict]:
        """
        Réécrit complètement le contenu avec optimisation SEO et conformité FIVAPE
        """
        if not content or len(content.strip()) < 10:
            return content, {}
        
        # Vérifier et préserver "Le Vapoteur Discount"
        has_vapoteur_discount = "Le Vapoteur Discount" in content or "le vapoteur discount" in content.lower()
        
        # SPECIAL : Préserver le prix dans les Meta Description
        price_prefix = ""
        if field_type == "Meta description":
            # Chercher le pattern "Prix : X,XX € |"
            price_match = re.match(r'(Prix\s*:\s*[\d,]+\s*€\s*\|\s*)', content)
            if price_match:
                price_prefix = price_match.group(1)
                # Enlever le prix du contenu à réécrire
                content = content[len(price_prefix):].strip()
        
        # Déterminer la longueur cible selon le type de champ
        length_targets = {
            'Description courte': '50-100 mots',
            'Description': '200-400 mots',
            'Meta description': '140-150 caractères' if not price_prefix else '100-120 caractères',
            'Meta titre': '50-60 caractères'
        }
        
        target_length = length_targets.get(field_type, '100-200 mots')
        
        try:
            # Instructions spéciales
            brand_instruction = ""
            if has_vapoteur_discount:
                brand_instruction = """
IMPORTANT : Si le texte contient "Le Vapoteur Discount" - CONSERVE EXACTEMENT cette mention avec cette orthographe."""
            
            price_instruction = ""
            if price_prefix:
                price_instruction = f"""
TRÈS IMPORTANT : Le texte commence par "{price_prefix}" - NE PAS l'inclure dans ta réécriture, je l'ajouterai moi-même."""
            
            prompt = f"""Tu es un expert SEO ET un spécialiste de la conformité réglementaire pour les produits de vapotage.

CONTEXTE LÉGAL FIVAPE (Avril 2024) :
- Directive européenne 2014/40/UE et Code de la Santé Publique
- Interdiction TOTALE des termes promotionnels et subjectifs
- Uniquement des informations factuelles et techniques

PRODUIT : {item_name}
TYPE : {item_type}
CHAMP : {field_type}
LONGUEUR CIBLE : {target_length}

CONTENU À RÉÉCRIRE (sans le prix si présent) :
{content}

{brand_instruction}
{price_instruction}

MISSION : Réécrire ce contenu en respectant STRICTEMENT :

1. SUPPRIMER tous les termes de ce type : délicieux, savoureux, gourmand, excellent, parfait, bonheur, plaisir, intense, etc.
2. GARDER uniquement les informations factuelles
3. Si c'est une Meta Description, rester TRÈS concis ({target_length})
4. Si c'est un Meta titre, être court et percutant ({target_length})
5. Préserver les informations techniques : compatibilité, résistances, formats

Fournis UNIQUEMENT le texte réécrit, sans le prix, sans commentaires."""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Expert SEO vapotage. Rédaction factuelle conforme FIVAPE."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            rewritten_content = response.choices[0].message.content.strip()
            
            # Nettoyer les marqueurs de code
            if '```' in rewritten_content:
                lines = rewritten_content.split('\n')
                cleaned_lines = []
                in_code_block = False
                for line in lines:
                    if '```' in line:
                        in_code_block = not in_code_block
                    elif not in_code_block:
                        cleaned_lines.append(line)
                rewritten_content = '\n'.join(cleaned_lines).strip()
            
            # Réajouter le prix au début si c'était une Meta Description
            if price_prefix:
                rewritten_content = price_prefix + rewritten_content
            
            # Ajouter des balises HTML si c'est une description et qu'il n'y en a pas
            if field_type in ['Description courte', 'Description'] and '<' not in rewritten_content:
                # Diviser en paragraphes si le texte est long
                paragraphs = rewritten_content.split('. ')
                if len(paragraphs) > 3:
                    # Créer des paragraphes HTML
                    html_paragraphs = []
                    current_p = []
                    for i, sentence in enumerate(paragraphs):
                        current_p.append(sentence + ('.' if not sentence.endswith('.') else ''))
                        if (i + 1) % 3 == 0 or i == len(paragraphs) - 1:
                            html_paragraphs.append('<p>' + ' '.join(current_p) + '</p>')
                            current_p = []
                    rewritten_content = '\n'.join(html_paragraphs)
                else:
                    rewritten_content = '<p>' + rewritten_content + '</p>'
            
            # Statistiques avec calcul correct du nombre de mots
            rewritten_word_count = len(rewritten_content.split())
            original_word_count = len((content + price_prefix if price_prefix else content).split())
            
            stats = {
                'original_length': len(content + price_prefix if price_prefix else content),
                'new_length': len(rewritten_content),
                'original_word_count': original_word_count,
                'new_word_count': rewritten_word_count,
                'html_preserved': bool(re.search(r'<[^>]+>', rewritten_content)),
                'keywords_integrated': self.count_keywords(rewritten_content),
                'price_preserved': bool(price_prefix),
                'brand_preserved': "Le Vapoteur Discount" in rewritten_content if has_vapoteur_discount else None
            }
            
            return rewritten_content, stats
            
        except Exception as e:
            print(f"[ERREUR] Réécriture: {e}")
            # En cas d'erreur, retourner l'original avec le prix si présent
            return (price_prefix + content) if price_prefix else content, {}

    def count_keywords(self, text: str) -> Dict[str, int]:
        """Compte les mots-clés SEO importants dans le texte"""
        keywords = {
            'e-liquide': len(re.findall(r'e-liquide', text, re.IGNORECASE)),
            'vapotage': len(re.findall(r'vapotage', text, re.IGNORECASE)),
            'cigarette électronique': len(re.findall(r'cigarette électronique', text, re.IGNORECASE)),
            'vape': len(re.findall(r'vape', text, re.IGNORECASE)),
            'nicotine': len(re.findall(r'nicotine', text, re.IGNORECASE))
        }
        return keywords

    def extract_content(self, field_data) -> str:
        """Extrait le contenu d'un champ PrestaShop"""
        content = ""
        
        if isinstance(field_data, dict):
            if 'language' in field_data:
                languages = field_data.get('language', [])
                if isinstance(languages, list):
                    content = languages[0].get('value', '') if languages else ''
                elif isinstance(languages, dict):
                    content = languages.get('value', '')
            else:
                content = field_data.get('value', str(field_data))
        elif isinstance(field_data, list):
            content = field_data[0] if field_data else ''
        else:
            content = str(field_data) if field_data else ''
        
        return content

    def process_item(self, item: Dict, item_type: str, fields_to_process: Dict) -> Dict:
        """Traite un élément (produit, catégorie ou marque)"""
        item_id = item.get('id')
        
        # Extraire le nom
        name_content = self.extract_content(item.get('name', ''))
        name_text = re.sub(r'<[^>]+>', '', name_content)
        item_name = name_text[:100] if name_text else f"{item_type} {item_id}"
        
        result = {
            'id': item_id,
            'name': item_name,
            'type': item_type,
            'has_been_rewritten': False,
            'rewrites': [],
            'seo_stats': {
                'fields_rewritten': 0,
                'total_keywords_added': 0,
                'html_structure_improved': 0
            }
        }
        
        # IMPORTANT : Filtrer les champs à NE PAS modifier
        fields_to_skip = []
        if item_type == 'product':
            # Pour les produits, on ne touche PAS au nom seulement
            fields_to_skip = ['name']
        
        for field, field_name in fields_to_process.items():
            # SKIP les champs protégés
            if field in fields_to_skip:
                continue
                
            if field in item:
                original_content = self.extract_content(item[field])
                
                if original_content and len(original_content.strip()) > 5:
                    # Extraire et préserver la structure HTML
                    text_content, html_structure = self.extract_and_preserve_html(original_content)
                    
                    # Réécrire avec SEO
                    rewritten_content, stats = self.rewrite_content_with_seo(
                        original_content,  # Passer le contenu original complet
                        field_name, 
                        item_name, 
                        item_type, 
                        html_structure
                    )
                    
                    if rewritten_content != original_content:
                        result['has_been_rewritten'] = True
                        result['seo_stats']['fields_rewritten'] += 1
                        
                        # Compter les mots-clés ajoutés
                        if stats.get('keywords_integrated'):
                            total_keywords = sum(stats['keywords_integrated'].values())
                            result['seo_stats']['total_keywords_added'] += total_keywords
                        
                        # Extraire le texte sans HTML pour la visualisation
                        original_text_only = re.sub(r'<[^>]+>', '', original_content)
                        rewritten_text_only = re.sub(r'<[^>]+>', '', rewritten_content)
                        
                        rewrite_data = {
                            'field': field,
                            'field_name': field_name,
                            'original_content': original_content,
                            'rewritten_content': rewritten_content,
                            'original_text_only': original_text_only,
                            'rewritten_text_only': rewritten_text_only,
                            'stats': stats,
                            'keywords': stats.get('keywords_integrated', {})
                        }
                        
                        result['rewrites'].append(rewrite_data)
        
        return result

    def get_products(self, limit: Optional[int] = None) -> List[Dict]:
        """Récupère les produits depuis PrestaShop"""
        try:
            url = f"{self.prestashop_url}/api/products"
            params = {'display': '[id]', 'output_format': 'JSON'}
            if limit:
                params['limit'] = str(limit)
            
            response = requests.get(
                url,
                auth=HTTPBasicAuth(self.prestashop_key, ''),
                params=params,
                verify=True
            )
            
            if response.status_code != 200:
                return []
            
            product_ids = response.json().get('products', [])
            if limit:
                product_ids = product_ids[:limit]
            
            products = []
            for product_data in product_ids:
                product_id = product_data.get('id')
                detail_url = f"{self.prestashop_url}/api/products/{product_id}"
                detail_response = requests.get(
                    detail_url,
                    auth=HTTPBasicAuth(self.prestashop_key, ''),
                    params={'output_format': 'JSON'},
                    verify=True
                )
                
                if detail_response.status_code == 200:
                    product = detail_response.json().get('product', {})
                    products.append(product)
            
            return products
            
        except Exception as e:
            print(f"[ERREUR] Récupération produits: {e}")
            return []

    def get_categories(self, limit: Optional[int] = None) -> List[Dict]:
        """Récupère les catégories depuis PrestaShop"""
        try:
            url = f"{self.prestashop_url}/api/categories"
            params = {'display': '[id]', 'output_format': 'JSON'}
            if limit:
                params['limit'] = str(limit)
            
            response = requests.get(
                url,
                auth=HTTPBasicAuth(self.prestashop_key, ''),
                params=params,
                verify=True
            )
            
            if response.status_code != 200:
                return []
            
            category_ids = response.json().get('categories', [])
            if limit:
                category_ids = category_ids[:limit]
            
            categories = []
            for cat_data in category_ids:
                category_id = cat_data.get('id')
                detail_url = f"{self.prestashop_url}/api/categories/{category_id}"
                detail_response = requests.get(
                    detail_url,
                    auth=HTTPBasicAuth(self.prestashop_key, ''),
                    params={'output_format': 'JSON'},
                    verify=True
                )
                
                if detail_response.status_code == 200:
                    category = detail_response.json().get('category', {})
                    categories.append(category)
            
            return categories
            
        except Exception as e:
            print(f"[ERREUR] Récupération catégories: {e}")
            return []

    def get_manufacturers(self, limit: Optional[int] = None) -> List[Dict]:
        """Récupère les marques depuis PrestaShop"""
        try:
            url = f"{self.prestashop_url}/api/manufacturers"
            params = {'display': '[id]', 'output_format': 'JSON'}
            if limit:
                params['limit'] = str(limit)
            
            response = requests.get(
                url,
                auth=HTTPBasicAuth(self.prestashop_key, ''),
                params=params,
                verify=True
            )
            
            if response.status_code != 200:
                return []
            
            manufacturer_ids = response.json().get('manufacturers', [])
            if limit:
                manufacturer_ids = manufacturer_ids[:limit]
            
            manufacturers = []
            for man_data in manufacturer_ids:
                manufacturer_id = man_data.get('id')
                detail_url = f"{self.prestashop_url}/api/manufacturers/{manufacturer_id}"
                detail_response = requests.get(
                    detail_url,
                    auth=HTTPBasicAuth(self.prestashop_key, ''),
                    params={'output_format': 'JSON'},
                    verify=True
                )
                
                if detail_response.status_code == 200:
                    manufacturer = detail_response.json().get('manufacturer', {})
                    manufacturers.append(manufacturer)
            
            return manufacturers
            
        except Exception as e:
            print(f"[ERREUR] Récupération marques: {e}")
            return []

    def run_with_params(self, element_type: str, nb_items: int, progress_callback=None):
        """Version adaptée pour Streamlit sans input utilisateur"""
        
        if nb_items == 0:
            nb_items = None
        
        # Mapping des types
        type_map = {
            "Produits": "1",
            "Catégories": "2",
            "Marques": "3",
            "Tout": "4"
        }
        
        choice = type_map.get(element_type, "1")
        
        # Traitement selon le choix
        if choice in ['1', '4']:  # Produits
            products = self.get_products(nb_items)
            if products:
                self.results['metadata']['total_products_analyzed'] = len(products)
                
                fields = {
                    'name': 'Nom du produit',
                    'description_short': 'Description courte',
                    'meta_title': 'Meta titre',
                    'meta_description': 'Meta description'
                }
                
                for i, product in enumerate(products, 1):
                    if progress_callback:
                        progress_callback(i, len(products), f"Produit {i}/{len(products)}")
                    
                    result = self.process_item(product, 'product', fields)
                    self.results['products'].append(result)
                    
                    if result['has_been_rewritten']:
                        self.results['metadata']['items_rewritten'] += 1
                    
                    time.sleep(0.5)  # Pause pour l'API
        
        if choice in ['2', '4']:  # Catégories
            categories = self.get_categories(nb_items)
            if categories:
                self.results['metadata']['total_categories_analyzed'] = len(categories)
                
                fields = {
                    'name': 'Nom de la catégorie',
                    'description': 'Description',
                    'additional_description': 'Informations complémentaires',
                    'meta_title': 'Balise titre',
                    'meta_description': 'Meta description'
                }
                
                for category in categories:
                    result = self.process_item(category, 'category', fields)
                    self.results['categories'].append(result)
                    
                    if result['has_been_rewritten']:
                        self.results['metadata']['items_rewritten'] += 1
        
        if choice in ['3', '4']:  # Marques
            manufacturers = self.get_manufacturers(nb_items)
            if manufacturers:
                self.results['metadata']['total_manufacturers_analyzed'] = len(manufacturers)
                
                fields = {
                    'name': 'Nom',
                    'short_description': 'Résumé',
                    'description': 'Description',
                    'meta_title': 'Balise titre',
                    'meta_description': 'Meta description'
                }
                
                for manufacturer in manufacturers:
                    result = self.process_item(manufacturer, 'manufacturer', fields)
                    self.results['manufacturers'].append(result)
                    
                    if result['has_been_rewritten']:
                        self.results['metadata']['items_rewritten'] += 1
        
        return self.results

    def run_with_specific_ids(self, element_type: str, specific_ids: List[int], progress_callback=None):
        """Version pour traiter des IDs spécifiques"""
        
        # Mapping des types
        type_map = {
            "Produits": "products",
            "Catégories": "categories",
            "Marques": "manufacturers"
        }
        
        item_type = type_map.get(element_type, "products")
        
        # Récupérer les éléments par IDs
        if item_type == "products":
            items = []
            for i, product_id in enumerate(specific_ids, 1):
                if progress_callback:
                    progress_callback(i, len(specific_ids), f"Récupération produit {product_id}")
                
                try:
                    detail_url = f"{self.prestashop_url}/api/products/{product_id}"
                    detail_response = requests.get(
                        detail_url,
                        auth=HTTPBasicAuth(self.prestashop_key, ''),
                        params={'output_format': 'JSON'},
                        verify=True
                    )
                    
                    if detail_response.status_code == 200:
                        product = detail_response.json().get('product', {})
                        items.append(product)
                except:
                    continue
            
            if items:
                self.results['metadata']['total_products_analyzed'] = len(items)
                
                fields = {
                    'name': 'Nom du produit',
                    'description_short': 'Description courte',
                    'meta_title': 'Meta titre',
                    'meta_description': 'Meta description'
                }
                
                for i, product in enumerate(items, 1):
                    if progress_callback:
                        progress_callback(i, len(items), f"Traitement produit {product.get('id')}")
                    
                    result = self.process_item(product, 'product', fields)
                    self.results['products'].append(result)
                    
                    if result['has_been_rewritten']:
                        self.results['metadata']['items_rewritten'] += 1
                    
                    time.sleep(0.5)  # Pause pour l'API
        
        elif item_type == "categories":
            items = []
            for i, category_id in enumerate(specific_ids, 1):
                if progress_callback:
                    progress_callback(i, len(specific_ids), f"Récupération catégorie {category_id}")
                
                try:
                    detail_url = f"{self.prestashop_url}/api/categories/{category_id}"
                    detail_response = requests.get(
                        detail_url,
                        auth=HTTPBasicAuth(self.prestashop_key, ''),
                        params={'output_format': 'JSON'},
                        verify=True
                    )
                    
                    if detail_response.status_code == 200:
                        category = detail_response.json().get('category', {})
                        items.append(category)
                except:
                    continue
            
            if items:
                self.results['metadata']['total_categories_analyzed'] = len(items)
                
                fields = {
                    'name': 'Nom de la catégorie',
                    'description': 'Description',
                    'additional_description': 'Informations complémentaires',
                    'meta_title': 'Balise titre',
                    'meta_description': 'Meta description'
                }
                
                for category in items:
                    result = self.process_item(category, 'category', fields)
                    self.results['categories'].append(result)
                    
                    if result['has_been_rewritten']:
                        self.results['metadata']['items_rewritten'] += 1
        
        elif item_type == "manufacturers":
            items = []
            for i, manufacturer_id in enumerate(specific_ids, 1):
                if progress_callback:
                    progress_callback(i, len(specific_ids), f"Récupération marque {manufacturer_id}")
                
                try:
                    detail_url = f"{self.prestashop_url}/api/manufacturers/{manufacturer_id}"
                    detail_response = requests.get(
                        detail_url,
                        auth=HTTPBasicAuth(self.prestashop_key, ''),
                        params={'output_format': 'JSON'},
                        verify=True
                    )
                    
                    if detail_response.status_code == 200:
                        manufacturer = detail_response.json().get('manufacturer', {})
                        items.append(manufacturer)
                except:
                    continue
            
            if items:
                self.results['metadata']['total_manufacturers_analyzed'] = len(items)
                
                fields = {
                    'name': 'Nom',
                    'short_description': 'Résumé',
                    'description': 'Description',
                    'meta_title': 'Balise titre',
                    'meta_description': 'Meta description'
                }
                
                for manufacturer in items:
                    result = self.process_item(manufacturer, 'manufacturer', fields)
                    self.results['manufacturers'].append(result)
                    
                    if result['has_been_rewritten']:
                        self.results['metadata']['items_rewritten'] += 1
        
        return self.results