#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SERVIDOR IDEALISTA PARA N8N
Endpoint HTTP para scraping de particulares en toda España
Compatible con N8N HTTP Request Node
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Diccionario de ciudades disponibles para scraping
CIUDADES_ESPANA = {
    'madrid': 'https://www.idealista.com/venta-viviendas/madrid-madrid/con-particulares/',
    'barcelona': 'https://www.idealista.com/venta-viviendas/barcelona-barcelona/con-particulares/',
    'valencia': 'https://www.idealista.com/venta-viviendas/valencia-valencia/con-particulares/',
    'sevilla': 'https://www.idealista.com/venta-viviendas/sevilla-sevilla/con-particulares/',
    'zaragoza': 'https://www.idealista.com/venta-viviendas/zaragoza-zaragoza/con-particulares/',
    'malaga': 'https://www.idealista.com/venta-viviendas/malaga-malaga/con-particulares/',
    'bilbao': 'https://www.idealista.com/venta-viviendas/bilbao/con-particulares/',
    'alicante': 'https://www.idealista.com/venta-viviendas/alicante-alicante/con-particulares/',
}

# URL por defecto (Madrid)
IDEALISTA_BASE_URL = CIUDADES_ESPANA['madrid']
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9',
    'Connection': 'keep-alive',
}

def build_search_url(base_url: str, page: int = 1) -> str:
    """Construye URL de búsqueda para una ciudad y página"""
    if page <= 1:
        return base_url
    return f"{base_url}pagina-{page}.htm"    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as resp:
        html = resp.read().decode("utf-8", errors="ignore")

    soup = BeautifulSoup(html, "html.parser")

    listings = []
    for article in soup.find_all("article", class_="item"):
        seller_type = "Particular"
        extra_info = article.select_one(".item-extra-info, .item-subtitle")
        if extra_info:
            extra_text = extra_info.get_text(strip=True)
            if re.search(r"agencia|inmobiliaria", extra_text, re.I):
                seller_type = "Agencia"

        title_el = article.select_one("a.item-link")
        price_el = article.select_one(".item-price span, span.item-price")
        details_els = article.select("span.item-detail")
        location_el = article.select_one(".item-location")
        date_el = article.select_one(".item-date")

        url_rel = title_el["href"] if title_el and title_el.has_attr("href") else None
        if url_rel and not url_rel.startswith("http"):
            url_abs = urllib.parse.urljoin("https://www.idealista.com", url_rel)
        else:
            url_abs = url_rel

        id_match = re.search(r"/inmueble/(\d+)/", url_abs or "")
        prop_id = id_match.group(1) if id_match else None

        price_raw = price_el.get_text(strip=True) if price_el else ""
        price_num = re.sub(r"[^\d]", "", price_raw) or "0"

        hab = 0
        ban = 0
        metros = 0
        for d in details_els:
            txt = d.get_text(" ", strip=True)
            m_hab = re.search(r"(\d+)\s*habs?", txt, re.I)
            m_ban = re.search(r"(\d+)\s*bañ", txt, re.I)
            m_m2 = re.search(r"(\d+)\s*m²?", txt, re.I)
            if m_hab:
                hab = int(m_hab.group(1))
            if m_ban:
                ban = int(m_ban.group(1))
            if m_m2:
                metros = int(m_m2.group(1))

        location = location_el.get_text(" ", strip=True) if location_el else ""
        fecha_pub = date_el.get_text(strip=True) if date_el else None

        listings.append({
            "id": prop_id,
            "titulo": title_el.get_text(strip=True) if title_el else "",
            "precio": price_num,
            "habitaciones": hab,
            "banos": ban,
            "metros": metros,
            "ubicacion": location,
            "tipo_vendedor": seller_type,
            "fecha_publicacion": fecha_pub,
            "url": url_abs,
        })

    listings = [l for l in listings if l["tipo_vendedor"].lower() == "particular"]
    logger.info(f"Encontradas {len(listings)} propiedades particulares en página {page}")
    return listings

def fetch_realista_data(pages: int = 1):
    resultados = []
    for p in range(1, pages + 1):
        try:
            page_data = scrape_idealista_page(p)
            resultados.extend(page_data)
        except Exception as e:
            logger.error(f"Error scrapendo página {p}: {e}")
            break
    return resultados

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'service': 'Idealista Scraper API'
    }), 200

@app.route('/api/idealista/espana/particulares', methods=['GET'])
@app.route('/api/idealista/madrid/particulares', methods=['GET'])  # Alias para compatibilidad
@app.route('/api/idealista/<city>/particulares', methods=['GET'])  # Endpoint dinámico
                city = request.args.get('city', city).lower()
                    
                base_url = CIUDADES_ESPANA.get(city, CIUDADES_ESPANA['madrid'])
        city_name = city.capitalize()
        
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        habitaciones = request.args.get('habitaciones')
        pages_to_scrape = int(request.args.get('pages_to_scrape', 1))

        data = fetch_realista_data(pages=pages_to_scrape)

        filtered = data
        if min_price > 0:
            filtered = [p for p in filtered if int(p['precio']) >= min_price]
        if max_price < 10000000:
            filtered = [p for p in filtered if int(p['precio']) <= max_price]
        if location:
            filtered = [p for p in filtered if location in (p['ubicacion'] or '').lower()]
        if habitaciones:
            hab = int(habitaciones)
            filtered = [p for p in filtered if p['habitaciones'] == hab]

        total = len(filtered)
        start = (page - 1) * limit
        end = start + limit
        results = filtered[start:end]

        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'location': city_name,            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'total_pages': (total + limit - 1) // limit,
                'has_next': end < total
            },
            'data': results,
            'count': len(results)
        }), 200

    except Exception as e:
        logger.error(f"Error en endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
138
