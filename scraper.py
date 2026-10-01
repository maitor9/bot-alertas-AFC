import asyncio
import os
import re
import subprocess
import sys
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


# Descarga/Instalación automática si falta el binario exacto en el contenedor
def asegurar_navegador():
  try:
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"], check=True
    )
  except Exception as e:
    print(f"⚠️ Error al asegurar binario de Playwright: {e}", flush=True)


asegurar_navegador()


# ==========================================
# ⚽ SCRAPER DE FÚTBOL EN VIVO
# ==========================================
async def extraer_futbol_en_vivo():
  partidos_candidatos = []

  async with async_playwright() as p:
    browser = await p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--single-process",
        ],
    )
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    )
    page = await context.new_page()

    try:
      await page.goto("https://www.flashscore.es/", timeout=35000)
      await page.wait_for_selector(".sportName", timeout=20000)

      content = await page.content()
      soup = BeautifulSoup(content, "html.parser")

      eventos = soup.find_all("div", class_=re.compile("event__match"))

      for evento in eventos:
        try:
          minuto_elem = evento.find("div", class_=re.compile("event__stage"))
          local_elem = evento.find(
              "div", class_=re.compile("event__homeParticipant")
          )
          visita_elem = evento.find(
              "div", class_=re.compile("event__awayParticipant")
          )
          score_home = evento.find(
              "div", class_=re.compile("event__score--home")
          )
          score_away = evento.find(
              "div", class_=re.compile("event__score--away")
          )

          if not (minuto_elem and local_elem and visita_elem):
            continue

          minuto_txt = minuto_elem.text.strip().replace("'", "")

          if not minuto_txt.isdigit():
            continue

          minuto = int(minuto_txt)
          goles_h = (
              int(score_home.text.strip())
              if score_home and score_home.text.strip().isdigit()
              else 0
          )
          goles_a = (
              int(score_away.text.strip())
              if score_away and score_away.text.strip().isdigit()
              else 0
          )

          if 46 <= minuto <= 78 and (goles_h + goles_a) == 0:
            partidos_candidatos.append({
                "equipo_local": local_elem.text.strip(),
                "equipo_visita": visita_elem.text.strip(),
                "minuto": minuto,
                "goles_local": goles_h,
                "goles_visita": goles_a,
                "liga": "En Vivo",
            })
        except Exception:
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
  partidos_candidatos = []

  async with async_playwright() as p:
    browser = await p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--single-process",
        ],
    )
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    )
    page = await context.new_page()

    try:
      await page.goto("https://www.flashscore.es/baloncesto/", timeout=35000)
      await page.wait_for_selector(".sportName", timeout=20000)

      content = await page.content()
      soup = BeautifulSoup(content, "html.parser")

      eventos = soup.find_all("div", class_=re.compile("event__match"))

      for evento in eventos:
        try:
          etapa_elem = evento.find("div", class_=re.compile("event__stage"))
          local_elem = evento.find(
              "div", class_=re.compile("event__homeParticipant")
          )
          visita_elem = evento.find(
              "div", class_=re.compile("event__awayParticipant")
          )
          score_home = evento.find(
              "div", class_=re.compile("event__score--home")
          )
          score_away = evento.find(
              "div", class_=re.compile("event__score--away")
          )

          if not (
              etapa_elem
              and local_elem
              and visita_elem
              and score_home
              and score_away
          ):
            continue

          etapa = etapa_elem.text.strip()
          p_home = (
              int(score_home.text.strip())
              if score_home.text.strip().isdigit()
              else 0
          )
          p_away = (
              int(score_away.text.strip())
              if score_away.text.strip().isdigit()
              else 0
          )

          dif = abs(p_home - p_away)
          es_q2_o_ht = any(
              term in etapa.upper() for term in ["Q2", "2º", "HT", "DESCANSO"]
          )

          if es_q2_o_ht and dif >= 10:
            favorito = (
                local_elem.text.strip()
                if p_home < p_away
                else visita_elem.text.strip()
            )
            partidos_candidatos.append({
                "local": local_elem.text.strip(),
                "visita": visita_elem.text.strip(),
                "marcador": f"{p_home} - {p_away}",
                "periodo": etapa,
                "favorito": favorito,
                "diferencia": dif,
                "liga": "Liga Basket",
            })
        except Exception:
          continue
    except Exception as e:
      print(f"⚠️ Error en scraping de basket: {e}", flush=True)
    finally:
      await browser.close()

  return partidos_candidatos
