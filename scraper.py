import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Origin": "https://www.sofascore.com",
    "Referer": "https://www.sofascore.com/",
}

# ==========================================
# ⚽ SCRAPER DE FÚTBOL EN VIVO (SOFASCORE LIVE API)
# ==========================================
async def extraer_futbol_en_vivo():
    partidos_candidatos = []
    print("⏳ Consultando API en vivo de Sofascore...", flush=True)

    try:
        url = "https://api.sofascore.com/api/v1/sport/football/events/live"
        response = requests.get(url, headers=HEADERS, timeout=12)

        print(f"🔍 Status code Sofascore Live: {response.status_code}", flush=True)

        if response.status_code == 200:
            data = response.json()
            events = data.get("events", [])

            for event in events:
                try:
                    status = event.get("status", {})
                    # code 7 = 2do tiempo, code 6 = 1er tiempo, code 31 = descanso (HT)
                    code = status.get("code")
                    
                    # Queremos segunda mitad principalmente (code 7) o entretiempo (code 31)
                    if code not in [7, 31]:
                        continue

                    time_info = event.get("time", {})
                    minuto = time_info.get("played", 50)
                    if isinstance(minuto, str):
                        minuto = int(re.search(r'\d+', minuto).group()) if re.search(r'\d+', minuto) else 50

                    home_score = event.get("homeScore", {}).get("current", 0) or 0
                    away_score = event.get("awayScore", {}).get("current", 0) or 0

                    # Filtro base: Minuto 46 a 78 y marcador 0 - 0
                    if not (46 <= minuto <= 78 and (home_score + away_score) == 0):
                        continue

                    home_team = event.get("homeTeam", {})
                    away_team = event.get("awayTeam", {})
                    
                    home_name = home_team.get("name", "Local")
                    away_name = away_team.get("name", "Visita")
                    
                    tournament = event.get("tournament", {})
                    league = tournament.get("name", "Liga en Vivo")

                    # Consultar estadísticas detalladas del partido en tiempo real
                    event_id = event.get("id")
                    total_remates = 0
                    total_remates_puerta = 0
                    equipo_mas_activo = home_name

                    if event_id:
                        stats_url = f"https://api.sofascore.com/api/v1/event/{event_id}/statistics"
                        stats_res = requests.get(stats_url, headers=HEADERS, timeout=5)
                        if stats_res.status_code == 200:
                            stats_data = stats_res.json()
                            statistics = stats_data.get("statistics", [])
                            
                            for period in statistics:
                                if period.get("period") == "ALL":
                                    groups = period.get("groups", [])
                                    for group in groups:
                                        items = group.get("statisticsItems", [])
                                        for item in items:
                                            name = item.get("name", "")
                                            if name == "Total shots":
                                                home_shots = int(item.get("homeValue", 0) or 0)
                                                away_shots = int(item.get("awayValue", 0) or 0)
                                                total_remates = home_shots + away_shots
                                                equipo_mas_activo = home_name if home_shots >= away_shots else away_name
                                            elif name == "Shots on target":
                                                home_sot = int(item.get("homeValue", 0) or 0)
                                                away_sot = int(item.get("awayValue", 0) or 0)
                                                total_remates_puerta = home_sot + away_sot

                    # Criterio VIP AI (Remates totales >= 8 o Remates a puerta >= 4)
                    es_vip = (total_remates >= 8) or (total_remates_puerta >= 4)

                    partidos_candidatos.append({
                        "equipo_local": home_name,
                        "equipo_visita": away_name,
                        "minuto": minuto,
                        "goles_local": home_score,
                        "goles_visita": away_score,
                        "liga": league,
                        "remates": total_remates,
                        "remates_puerta": total_remates_puerta,
                        "presion": equipo_mas_activo,
                        "tipo": "VIP" if es_vip else "GLOBAL"
                    })

                except Exception:
                    continue

            print(f"✅ Extraídos {len(partidos_candidatos)} partidos de Sofascore.", flush=True)
        else:
            print(f"⚠️ Sofascore devolvió status: {response.status_code}", flush=True)

    except Exception as e:
        print(f"⚠️ Error consultando Sofascore: {e}", flush=True)

    return partidos_candidatos

async def extraer_basket_en_vivo():
    return []
