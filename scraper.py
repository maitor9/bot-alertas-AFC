import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        " (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "x-fsign": "SW90ZXN0",
    "Referer": "https://www.flashscore.es/",
}


# ==========================================
# ⚽ SCRAPER DE FÚTBOL EN VIVO (FEED DIRECTO)
# ==========================================
async def extraer_futbol_en_vivo():
  partidos_candidatos = []
  print("⏳ Consultando feed de Flashscore Fútbol...", flush=True)

  try:
    # Endpoint directo de partidos en directo (fútbol)
    url = "https://3.net.flashscore.es/2/x/feed/r_1_1"
    response = requests.get(url, headers=HEADERS, timeout=10)

    if response.status_code == 200:
      raw_data = response.text
      bloques = raw_data.split("~")

      partido_actual = {}
      for bloque in bloques:
        if "÷" not in bloque:
          continue
        clave, valor = bloque.split("÷", 1)

        if clave == "AA":  # ID de partido (inicio de un evento)
          if partido_actual:
            _procesar_partido_futbol(partido_actual, partidos_candidatos)
          partido_actual = {}
        elif clave == "CX":
          partido_actual["local"] = valor
        elif clave == "CY":
          partido_actual["visita"] = valor
        elif clave == "AG":
          partido_actual["goles_local"] = valor
        elif clave == "AH":
          partido_actual["goles_visita"] = valor
        elif clave == "AC":
          partido_actual["etapa"] = valor

      if partido_actual:
        _procesar_partido_futbol(partido_actual, partidos_candidatos)

      print(
          f"✅ Extraídos {len(partidos_candidatos)} partidos de Fútbol.",
          flush=True,
      )
    else:
      print(f"⚠️ Status code Fútbol: {response.status_code}", flush=True)

  except Exception as e:
    print(f"⚠️ Error en feed de fútbol: {e}", flush=True)

  return partidos_candidatos


def _procesar_partido_futbol(p, candidatos):
  try:
    etapa = p.get("etapa", "").replace("'", "").strip()
    if not etapa.isdigit():
      return

    minuto = int(etapa)
    goles_h = int(p.get("goles_local", 0))
    goles_a = int(p.get("goles_visita", 0))

    if 46 <= minuto <= 78 and (goles_h + goles_a) == 0:
      candidatos.append({
          "equipo_local": p.get("local", "Local"),
          "equipo_visita": p.get("visita", "Visita"),
          "minuto": minuto,
          "goles_local": goles_h,
          "goles_visita": goles_a,
          "liga": "En Vivo",
      })
  except Exception:
    pass


# ==========================================
# 🏀 SCRAPER DE BALONCESTO EN VIVO (FEED DIRECTO)
# ==========================================
async def extraer_basket_en_vivo():
  partidos_candidatos = []
  print("⏳ Consultando feed de Flashscore Basket...", flush=True)

  try:
    # Endpoint directo de partidos en directo (baloncesto)
    url = "https://3.net.flashscore.es/2/x/feed/r_3_1"
    response = requests.get(url, headers=HEADERS, timeout=10)

    if response.status_code == 200:
      raw_data = response.text
      bloques = raw_data.split("~")

      partido_actual = {}
      for bloque in bloques:
        if "÷" not in bloque:
          continue
        clave, valor = bloque.split("÷", 1)

        if clave == "AA":
          if partido_actual:
            _procesar_partido_basket(partido_actual, partidos_candidatos)
          partido_actual = {}
        elif clave == "CX":
          partido_actual["local"] = valor
        elif clave == "CY":
          partido_actual["visita"] = valor
        elif clave == "AG":
          partido_actual["p_home"] = valor
        elif clave == "AH":
          partido_actual["p_away"] = valor
        elif clave == "AC":
          partido_actual["etapa"] = valor

      if partido_actual:
        _procesar_partido_basket(partido_actual, partidos_candidatos)

      print(
          f"✅ Extraídos {len(partidos_candidatos)} partidos de Basket.",
          flush=True,
      )
    else:
      print(f"⚠️ Status code Basket: {response.status_code}", flush=True)

  except Exception as e:
    print(f"⚠️ Error en feed de basket: {e}", flush=True)

  return partidos_candidatos


def _procesar_partido_basket(p, candidatos):
  try:
    etapa = p.get("etapa", "").upper()
    p_home = int(p.get("p_home", 0))
    p_away = int(p.get("p_away", 0))

    dif = abs(p_home - p_away)
    es_q2_o_ht = any(
        term in etapa for term in ["Q2", "2º", "HT", "DESCANSO", "2ND"]
    )

    if es_q2_o_ht and dif >= 10:
      favorito = (
          p.get("local", "Local")
          if p_home < p_away
          else p.get("visita", "Visita")
      )
      candidatos.append({
          "local": p.get("local", "Local"),
          "visita": p.get("visita", "Visita"),
          "marcador": f"{p_home} - {p_away}",
          "periodo": etapa,
          "favorito": favorito,
          "diferencia": dif,
          "liga": "Liga Basket",
      })
  except Exception:
    pass
