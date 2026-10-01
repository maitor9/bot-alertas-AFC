import asyncio
import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# ==========================================
# ⚽ SCRAPER DE FÚTBOL EN VIVO
# ==========================================
async def extraer_futbol_en_vivo():
    """
    Extrae los partidos de fútbol en vivo que están 0-0 en la ventana del min 46' al 78'.
    """
    partidos_candidatos = []
    
    async with async_playwright() as p:
        # Lanzamos un navegador Chromium en modo sin interfaz (Headless)
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Navegamos a la sección en vivo de Flashscore / Sofascore
            await page.goto("https://www.flashscore.es/", timeout=30000)
            
            # Esperamos a que los elementos del marcador carguen en el DOM
            await page.wait_for_selector(".sportName", timeout=15000)
            
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # Buscamos los bloques de partidos
            eventos = soup.find_all("div", class_=re.compile("event__match"))
            
            for evento in eventos:
                try:
                    # Extracción de minutuje y marcador
                    minuto_elem = evento.find("div", class_=re.compile("event__stage"))
                    local_elem = evento.find("div", class_=re.compile("event__homeParticipant"))
                    visita_elem = evento.find("div", class_=re.compile("event__awayParticipant"))
                    score_home = evento.find("div", class_=re.compile("event__score--home"))
                    score_away = evento.find("div", class_=re.compile("event__score--away"))
                    
                    if not (minuto_elem and local_elem and visita_elem):
                        continue
                        
                    minuto_txt = minuto_elem.text.strip().replace("'", "")
                    
                    # Verificamos si es un número válido (minuto)
                    if not minuto_txt.isdigit():
                        continue
                        
                    minuto = int(minuto_txt)
                    goles_h = int(score_home.text.strip()) if score_home and score_home.text.strip().isdigit() else 0
                    goles_a = int(score_away.text.strip()) if score_away and score_away.text.strip().isdigit() else 0
                    
                    # Aplicamos las Reglas de Filtro: 0-0 entre Min 46 y Min 78
                    if 46 <= minuto <= 78 and (goles_h + goles_a) == 0:
                        partidos_candidatos.append({
                            "equipo_local": local_elem.text.strip(),
                            "equipo_visita": visita_elem.text.strip(),
                            "minuto": minuto,
                            "goles_local": goles_h,
                            "goles_visita": goles_a,
                            "liga": "En Vivo"
                        })
                except Exception as e_item:
                    continue

        except Exception as e:
            print(f"⚠️ Error en scraping de fútbol: {e}", flush=True)
        finally:
            await browser.close()
            
    return partidos_candidatos


# ==========================================
# 🏀 SCRAPER DE BALONCESTO EN VIVO
# ==========================================
async def extraer_basket_en_vivo():
    """
    Extrae los partidos de baloncesto en vivo en Q2 o HT con diferencia de 10+ puntos.
    """
    partidos_candidatos = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto("https://www.flashscore.es/baloncesto/", timeout=30000)
            await page.wait_for_selector(".sportName", timeout=15000)
            
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            eventos = soup.find_all("div", class_=re.compile("event__match"))
            
            for evento in eventos:
                try:
                    etapa_elem = evento.find("div", class_=re.compile("event__stage"))
                    local_elem = evento.find("div", class_=re.compile("event__homeParticipant"))
                    visita_elem = evento.find("div", class_=re.compile("event__awayParticipant"))
                    score_home = evento.find("div", class_=re.compile("event__score--home"))
                    score_away = evento.find("div", class_=re.compile("event__score--away"))
                    
                    if not (etapa_elem and local_elem and visita_elem and score_home and score_away):
                        continue
                        
                    etapa = etapa_elem.text.strip() # Ej: "2º Cuarto", "Descanso", "Q2", "HT"
                    p_home = int(score_home.text.strip()) if score_home.text.strip().isdigit() else 0
                    p_away = int(score_away.text.strip()) if score_away.text.strip().isdigit() else 0
                    
                    dif = abs(p_home - p_away)
                    
                    # Filtro de Momento (Q2 o HT) y Diferencia de 10+ Puntos
                    es_q2_o_ht = any(term in etapa.upper() for term in ["Q2", "2º", "HT", "DESCANSO"])
                    
                    if es_q2_o_ht and dif >= 10:
                        favorito = local_elem.text.strip() if p_home < p_away else visita_elem.text.strip()
                        partidos_candidatos.append({
                            "local": local_elem.text.strip(),
                            "visita": visita_elem.text.strip(),
                            "marcador": f"{p_home} - {p_away}",
                            "periodo": etapa,
                            "favorito": favorito,
                            "diferencia": dif,
                            "liga": "Liga Basket"
                        })
                except Exception as e_item:
                    continue
        except Exception as e:
            print(f"⚠️ Error en scraping de basket: {e}", flush=True)
        finally:
            await browser.close()
            
    return partidos_candidatos
