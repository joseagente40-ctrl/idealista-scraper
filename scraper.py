from playwright.async_api import async_playwright
import asyncio
from typing import List, Dict
import re

class IdealitaScraper:
    def __init__(self):
        self.base_url = "https://www.idealista.com"
    
    async def scrape_idealista(self, ciudad: str, tipo_propiedad: str = "venta", max_resultados: int = 10) -> List[Dict]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=TruTrue,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-dev-shm-usage'
                    ]))
            page = await browser.new_page()
            
            url = f"{self.base_url}/{tipo_propiedad}-viviendas/{ciudad.lower()}/"
            await page.goto(url)
            await page.wait_for_load_state('networkidle')
            
            propiedades = []
            
            items = await page.query_selector_all('article.item')
            
            for i, item in enumerate(items[:max_resultados]):
                try:
                    propiedad = {}
                    
                    titulo_elem = await item.query_selector('a.item-link')
                    if titulo_elem:
                        propiedad['titulo'] = await titulo_elem.inner_text()
                        propiedad['url'] = await titulo_elem.get_attribute('href')
                        if propiedad['url'] and not propiedad['url'].startswith('http'):
                            propiedad['url'] = self.base_url + propiedad['url']
                    
                    precio_elem = await item.query_selector('span.item-price')
                    if precio_elem:
                        precio_text = await precio_elem.inner_text()
                        propiedad['precio'] = precio_text.strip()
                    
                    descripcion_elem = await item.query_selector('div.item-detail-char')
                    if descripcion_elem:
                        propiedad['descripcion'] = await descripcion_elem.inner_text()
                    
                    ubicacion_elem = await item.query_selector('div.item-link .item-detail')
                    if ubicacion_elem:
                        propiedad['ubicacion'] = await ubicacion_elem.inner_text()
                    
                    propiedad['ciudad'] = ciudad
                    propiedad['tipo_propiedad'] = tipo_propiedad
                    
                    telefono_elem = await item.query_selector('span.icon-phone')
                    if telefono_elem:
                        telefono_text = await telefono_elem.get_attribute('onclick')
                        if telefono_text:
                            tel_match = re.search(r'\d{9}', telefono_text)
                            if tel_match:
                                propiedad['telefono'] = tel_match.group(0)
                    
                    propiedades.append(propiedad)
                    
                except Exception as e:
                    print(f"Error procesando propiedad {i}: {str(e)}")
                    continue
            
            await browser.close()
            return propiedades
