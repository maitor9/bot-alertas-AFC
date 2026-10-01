import asyncio
import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# ==========================================
# ⚽ SCRAPER DE FÚTBOL EN VIVO
# ==========================================
async def extraer_futbol_en_vivo():
    partidos_candidatos = []
    print("⏳ Iniciando navegador para Fútbol...", flush=True)
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--single-process"
                ]
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                print("⏳ Navegando a Flashscore Fútbol...", flush=True)
                await page.goto("https://www.flashscore.es/", wait_until="domcontentloaded", timeout=20000)
            except Exception as e_goto:
                print(f"⚠️ Aviso en goto Fútbol: {e_goto}", flush=True)
                
            await asyncio.sleep(3)
            
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            eventos = soup.find_all("div", class_=re.compile("event__match"))

            for evento in eventos:
                try:
                    minuto_elem = evento.find("div", class_=re.compile("event__stage"))
                    local_elem = evento.find("div", class_=re.compile("event__homeParticipant"))
                    visita_elem = evento.find("div", class_=re.compile("event__awayParticipant"))
                    score_home = evento.find("div", class_=re.compile("event__score--home"))
                    score_away = evento.find("div", class_=re.compile("event__score--away"))

                    if not (minuto_elem and local_elem and visita_elem):
                        continue

                    minuto_txt = minuto_elem.text.strip().replace("'", "")
                    if not minuto_txt.isdigit():
                        continue

                    minuto = int(minuto_txt)
                    goles_h = int(score_home.text.strip()) if score_home and score_home.text.strip().isdigit() else 0
                    goles_a = int(score_away.text.strip()) if score_away and score_away.text.strip().isdigit() else 0

                    if 46 <= minuto <= 78 and (goles_h + goles_a) == 0:
                        partidos_candidatos.append({
                            "equipo_local": local_elem.text.strip(),
                            "equipo_visita": visita_elem.text.strip(),
                            "minuto": minuto,
                            "goles_local": goles_h,
                            "goles_visita": goles_a,
                            "liga": "En Vivo"
                        })
                except Exception:
                    continue

            await browser.close()
            print(f"✅ Extraídos {len(partidos_candidatos)} partidos de Fútbol.", flush=True)

    except Exception as e:
        print(f"⚠️ Error general en scraping de fútbol: {e}", flush=True)

    return partidos_candidatos


# ==========================================
# 🏀 SCRAPER DE BALONCESTO EN VIVO
# ==========================================
async def extraer_basket_en_vivo():
    partidos_candidatos = []
    print("⏳ Iniciando navegador para Basket...", flush=True)
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--single-process"
                ]
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                print("⏳ Navegando a Flashscore Basket...", flush=True)
                await page.goto("https://www.flashscore.es/baloncesto/", wait_until="domcontentloaded", timeout=20000)
            except Exception as e_goto:
                print(f"⚠️ Aviso en goto Basket: {e_goto}", flush=True)
                
            await asyncio.sleep(3)
            
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

                    etapa = etapa_elem.text.strip()
                    p_home = int(score_home.text.strip()) if score_home.text.strip().isdigit() else 0
                    p_away = int(score_away.text.strip()) if score_away.text.strip().isdigit() else 0

                    dif = abs(p_home - p_away)
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
                except Exception:
                    continue

            await browser.close()
            print(f"✅ Extraídos {len(partidos_candidatos)} partidos de Basket.", flush=True)

    except Exception as e:
        print(f"⚠️ Error general en scraping de basket: {e}", flush=True)

    return partidos_candidatos
