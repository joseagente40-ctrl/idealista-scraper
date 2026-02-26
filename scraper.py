from playwright.async_api import async_playwright
import asyncio
from typing import List, Dict
import re
import random

class IdealitaScraper:
    def __init__(self):
        self.base_url = "https://www.idealista.com"
        # Lista de User-Agents reales para rotación
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15'
        ]
        # Lista de proxies públicos españoles (puedes añadir más)
        self.proxies = [
            None,  # Sin proxy para algunas requests
            # Añade aquí proxies si los tienes: 'http://proxy:port'
        ]
    
    def get_random_user_agent(self):
        return random.choice(self.user_agents)
    
    def get_random_proxy(self):
        return random.choice(self.proxies)
    
    async def scrape_idealista(self, ciudad: str, tipo_propiedad: str = "venta", max_resultados: int = 10) -> List[Dict]:
        async with async_playwright() as p:
            # Configuración avanzada del navegador
            user_agent = self.get_random_user_agent()
            proxy = self.get_random_proxy()
            
            launch_options = {
                'headless': True,
                'args': [
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    f'--user-agent={user_agent}'
                ]
            }
            
            # Añadir proxy si está disponible
            if proxy:
                launch_options['proxy'] = {'server': proxy}
            
            browser = await p.chromium.launch(**launch_options)
            
            # Crear contexto con headers realistas
            context = await browser.new_context(
                user_agent=user_agent,
                viewport={'width': 1920, 'height': 1080},
                locale='es-ES',
                timezone_id='Europe/Madrid',
                permissions=['geolocation'],
                geolocation={'latitude': 40.4168, 'longitude': -3.7038},  # Madrid
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Cache-Control': 'max-age=0'
                }
            )
            
            # Inyectar scripts anti-detección
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                window.chrome = {
                    runtime: {}
                };
                
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['es-ES', 'es', 'en-US', 'en']
                });
            """)
            
            page = await context.new_page()
            
            # Delay aleatorio antes de navegar (simular comportamiento humano)
            await asyncio.sleep(random.uniform(1, 3))
            
            url = f"{self.base_url}/{tipo_propiedad}-viviendas/{ciudad.lower()}/"
            
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                
                # Delay aleatorio después de cargar
                await asyncio.sleep(random.uniform(2, 4))
                
                # Scroll aleatorio para simular comportamiento humano
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 3)')
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                await page.wait_for_load_state('networkidle', timeout=15000)
            except Exception as e:
                print(f"Error navegando a {url}: {e}")
                await browser.close()
                return []
            
            propiedades = []
            
            try:
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
                        
                        # Extraer contacto si está disponible
                        if propiedad.get('url'):
                            contacto = await self.scrape_contact_data(context, propiedad['url'])
                            propiedad.update(contacto)
                        
                        propiedades.append(propiedad)
                        
                        # Delay aleatorio entre items
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                        
                    except Exception as e:
                        print(f"Error procesando propiedad {i}: {e}")
                        continue
            
            except Exception as e:
                print(f"Error obteniendo items: {e}")
            
            await browser.close()
            return propiedades
    
    async def scrape_contact_data(self, context, url: str) -> Dict:
        """Extrae teléfono y email de la página de detalle"""
        contacto = {'telefono': None, 'email': None}
        
        try:
            page = await context.new_page()
            await page.goto(url, wait_until='domcontentloaded', timeout=15000)
            await asyncio.sleep(random.uniform(1, 2))
            
            # Buscar teléfono
            phone_patterns = [
                r'\+?34\s?[6-9]\d{2}\s?\d{2}\s?\d{2}\s?\d{2}',
                r'[6-9]\d{2}\s?\d{2}\s?\d{2}\s?\d{2}'
            ]
            
            content = await page.content()
            for pattern in phone_patterns:
                match = re.search(pattern, content)
                if match:
                    contacto['telefono'] = match.group()
                    break
            
            # Buscar email
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            email_match = re.search(email_pattern, content)
            if email_match:
                contacto['email'] = email_match.group()
            
            await page.close()
        
        except Exception as e:
            print(f"Error extrayendo contacto de {url}: {e}")
        
        return contacto
