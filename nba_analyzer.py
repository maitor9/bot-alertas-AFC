from datetime import datetime, timedelta
import math
import requests
import concurrent.futures

LIGAS_BASKET_UNIVERSAL = [
    {"codigo": "nba", "nombre": "NBA", "sd_margin": 9.5, "sd_total": 12.0, "home_adv": 3.0, "base_def": 114.5},
    {"codigo": "wnba", "nombre": "WNBA", "sd_margin": 7.0, "sd_total": 9.0, "home_adv": 2.2, "base_def": 81.0},
    {"codigo": "mens-college-basketball", "nombre": "NCAA Masculino", "sd_margin": 10.0, "sd_total": 11.5, "home_adv": 3.5, "base_def": 73.0},
    {"codigo": "womens-college-basketball", "nombre": "NCAA Femenino", "sd_margin": 8.5, "sd_total": 10.5, "home_adv": 3.0, "base_def": 68.0},
    {"codigo": "euroleague", "nombre": "Euroliga", "sd_margin": 7.5, "sd_total": 10.0, "home_adv": 2.8, "base_def": 80.0},
    {"codigo": "fiba.champions", "nombre": "FIBA Champions League", "sd_margin": 8.0, "sd_total": 10.5, "home_adv": 2.5, "base_def": 78.0}
]

def normal_cdf(x, mu, sigma):
    try:
        return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2))))
    except:
        return 0.5

def calcular_cuotas(prob):
    try:
        if prob <= 1.0: prob = 1.0
        if prob >= 95.0: prob = 95.0
        decimal = round(100.0 / (prob * 1.05), 2)
        return f"{max(1.10, decimal)}"
    except:
        return "1.90"

def calcular_cuotas_valor(prob):
    try:
        if prob <= 1.0: prob = 1.0
        decimal = round(100.0 / (prob * 1.02), 2)
        return f"{max(1.75, decimal)}"
    except:
        return "2.20"

def extraer_estadisticas_equipo(team_data, base_def):
    puntos_favor = 0.0
    puntos_contra = 0.0
    win_pct = 0.500
    try:
        stats = team_data.get("statistics", [])
        for s in stats:
            name = s.get("name", "")
            val = float(s.get("value", 0))
            if name in ["avgPoints", "pointsPerGame", "avgPointsFor", "scoringAverage"]:
                puntos_favor = val
            elif name in ["avgPointsAllowed", "pointsAllowedPerGame", "avgPointsAgainst", "scoringAllowed"]:
                puntos_contra = val

        if puntos_favor == 0.0 and "stats" in team_data:
            for st in team_data.get("stats", []):
                name = st.get("name", "")
                val = float(st.get("value", 0))
                if name in ["avgPoints", "pointsPerGame", "avgPointsFor"]:
                    puntos_favor = val
                elif name in ["avgPointsAllowed", "pointsAllowedPerGame"]:
                    puntos_contra = val

        records = team_data.get("records", [])
        if not records and "record" in team_data:
            records = [team_data.get("record")]

        for rec in records:
            summary = rec.get("summary", "0-0")
            partes = summary.replace("W", "").replace("L", "").replace("T", "").split("-")
            if len(partes) >= 2:
                wins = int(partes[0])
                losses = int(partes[1])
                total = wins + losses
                if total > 0:
                    win_pct = wins / total
                    break
    except Exception:
        pass

    if puntos_favor == 0.0:
        puntos_favor = base_def + ((win_pct - 0.5) * 12.0)
    if puntos_contra == 0.0:
        puntos_contra = base_def - ((win_pct - 0.5) * 12.0)

    return float(puntos_favor), float(puntos_contra), float(win_pct)

def extraer_top_jugadores(competition, home_name, away_name):
    """Extrae líderes o jugadores destacados directamente de los atletas en la competencia."""
    try:
        leaders_info = []
        competitors = competition.get("competitors", [])
        for comp in competitors:
            t_name = comp.get("team", {}).get("shortDisplayName", "")
            leaders = comp.get("leaders", [])
            for cat in leaders:
                cat_name = cat.get("displayName", "")
                if cat_name in ["Points", "Puntos", "Scoring Leader"]:
                    top_list = cat.get("leaders", [])
                    if top_list:
                        player = top_list[0].get("athlete", {}).get("displayName", "")
                        val = top_list[0].get("displayValue", "")
                        if player:
                            leaders_info.append(f"{t_name}: {player} ({val} PTS)")
                            break
        if leaders_info:
            return " | ".join(leaders_info)
    except:
        pass
    return f"Estrellas en duela ({home_name} vs {away_name})"

def convertir_hora_colombia(date_str):
    try:
        dt_utc = datetime.strptime(date_str.replace("Z", ""), "%Y-%m-%dT%H:%M")
        dt_col = dt_utc - timedelta(hours=5)
        return dt_col.strftime("%d/%m/%Y - %H:%M")
    except Exception:
        return "📅 Próximamente"

def procesar_api_basket(liga, fecha):
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/{liga['codigo']}/scoreboard?dates={fecha}"
    try:
        response = requests.get(url, timeout=4.0)
        if response.status_code == 200:
            return liga, response.json()
    except:
        pass
    return liga, None

def analizar_partidos_nba():
    print("🏀 Escaneando cartelera Oficial NBA & Global (Motor Sabermétrico Avanzado)...", flush=True)
    analisis_lista = []
    picks_disponibles = []
    picks_vip_seguros = []
    picks_vip_valor = []
    eventos_procesados = set()

    hoy_str = datetime.now().strftime("%Y%m%d")
    manana_str = (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")
    fechas = [hoy_str, manana_str]

    tareas_url = [(liga, fecha) for liga in LIGAS_BASKET_UNIVERSAL for fecha in fechas]

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futuros = [executor.submit(procesar_api_basket, t[0], t[1]) for t in tareas_url]
        
        for futuro in concurrent.futures.as_completed(futuros):
            liga, data = futuro.result()
            if not data: continue
            
            events = data.get("events", [])
            for event in events:
                event_id = event.get("id")
                if not event_id or event_id in eventos_procesados: continue
                eventos_procesados.add(event_id)

                try:
                    competition = event.get("competitions", [{}])[0]
                    status_type = competition.get("status", {}).get("type", {}).get("name", "")
                    
                    valid_statuses = ["STATUS_SCHEDULED", "STATUS_PRE", "STATUS_IN_PROGRESS", "STATUS_HALFTIME", "STATUS_FINAL", "STATUS_FULL_TIME"]
                    if status_type not in valid_statuses: continue
                    is_final = status_type in ["STATUS_FINAL", "STATUS_FULL_TIME"]
                    fecha_hora_col = convertir_hora_colombia(event.get("date", ""))

                    teams = competition.get("competitors", [])
                    if len(teams) < 2: continue

                    home = next((t for t in teams if t.get("homeAway") == "home"), teams[0])
                    away = next((t for t in teams if t.get("homeAway") == "away"), teams[1])

                    home_name = home.get("team", {}).get("displayName", "Local")
                    away_name = away.get("team", {}).get("displayName", "Visita")
                    
                    def_base = liga["base_def"]
                    pf_h, pc_h, win_pct_h = extraer_estadisticas_equipo(home, def_base)
                    pf_a, pc_a, win_pct_a = extraer_estadisticas_equipo(away, def_base)

                    media_liga = (pf_h + pf_a + pc_h + pc_a) / 4.0
                    if media_liga == 0: media_liga = def_base

                    ataque_esperado_h = (pf_h * pc_a) / media_liga
                    defensa_esperada_h = (pc_h * pf_a) / media_liga
                    mu_home = (ataque_esperado_h + defensa_esperada_h) / 2.0 + (liga["home_adv"] / 2.0) + ((win_pct_h - 0.5) * 6.0)

                    ataque_esperado_a = (pf_a * pc_h) / media_liga
                    defensa_esperada_a = (pc_a * pf_h) / media_liga
                    mu_away = (ataque_esperado_a + defensa_esperada_a) / 2.0 - (liga["home_adv"] / 2.0) + ((win_pct_a - 0.5) * 6.0)

                    mu_total = round(mu_home + mu_away, 1)
                    mu_diff = round(mu_home - mu_away, 1)

                    prob_home_win = (1.0 - normal_cdf(0, mu_diff, liga["sd_margin"])) * 100.0
                    p_win_h = round(max(15.0, min(88.0, prob_home_win)), 1)
                    p_win_a = round(100.0 - p_win_h, 1)

                    linea_over_base = round(mu_total * 2) / 2.0
                    linea_under_base = linea_over_base
                    
                    p_over_base = round((1.0 - normal_cdf(linea_over_base, mu_total, liga["sd_total"])) * 100.0, 1)
                    p_under_base = round(normal_cdf(linea_under_base, mu_total, liga["sd_total"]) * 100.0, 1)

                    try:
                        home_score = int(home.get("score", "0"))
                        away_score = int(away.get("score", "0"))
                    except ValueError:
                        home_score, away_score = 0, 0
                    total_points = home_score + away_score

                    oportunidades_alta_confianza = []
                    candidatos_grid = []

                    prob_ml = max(p_win_h, p_win_a)
                    pick_val_ml = home_name if p_win_h >= p_win_a else away_name

                    if p_over_base >= 52.0:
                        picks_vip_valor.append({
                            "partido": f"{home_name} vs {away_name}", "liga": liga["nombre"],
                            "mercado": f"Over {linea_over_base} Pts", 
                            "justificacion": f"Ritmo y eficiencia proyectan {mu_total} pts totales. Valor en alta anotación.",
                            "prob": p_over_base, "cuota": calcular_cuotas_valor(p_over_base)
                        })
                        oportunidades_alta_confianza.append(f"• 💎 **Over {linea_over_base} Pts:** {p_over_base}% | Cuota: *{calcular_cuotas_valor(p_over_base)}* ⏳ (Valor: Ritmo Ofensivo)")
                    elif p_under_base >= 52.0:
                        picks_vip_valor.append({
                            "partido": f"{home_name} vs {away_name}", "liga": liga["nombre"],
                            "mercado": f"Under {linea_under_base} Pts", 
                            "justificacion": f"Defensas cerradas proyectan por debajo de {linea_under_base} pts.",
                            "prob": p_under_base, "cuota": calcular_cuotas_valor(p_under_base)
                        })
                        oportunidades_alta_confianza.append(f"• 💎 **Under {linea_under_base} Pts:** {p_under_base}% | Cuota: *{calcular_cuotas_valor(p_under_base)}* ⏳ (Valor: Solidez Defensiva)")

                    if prob_ml >= 60.0:
                        oportunidades_alta_confianza.append(f"• 🏀 **Gana {pick_val_ml} (ML):** {prob_ml}% | Cuota: *{calcular_cuotas(prob_ml)}* ⏳")
                        candidatos_grid.append({"mercado": f"Moneyline ({pick_val_ml})", "prob": prob_ml, "estado": "pendiente"})

                    if not oportunidades_alta_confianza:
                        candidatos_grid.append({"mercado": f"Over {linea_over_base} Pts", "prob": p_over_base, "estado": "pendiente"})
                        oportunidades_alta_confianza.append(f"• **Over {linea_over_base} Pts:** {p_over_base}% | Cuota: *{calcular_cuotas(p_over_base)}* ⏳")

                    if candidatos_grid:
                        mejor_grid = max(candidatos_grid, key=lambda x: x["prob"])
                        picks_disponibles.append({
                            "partido": f"{home_name} vs {away_name}", 
                            "home": home_name, 
                            "away": away_name,
                            "liga": liga["nombre"], 
                            "fecha": fecha_hora_col, 
                            "time": fecha_hora_col, 
                            "is_final": is_final,
                            "prob": mejor_grid["prob"], 
                            "mercado": mejor_grid["mercado"],
                            "estado_pick": mejor_grid["estado"]
                        })

                        if mejor_grid["prob"] >= 70.0:
                            picks_vip_seguros.append({
                                "partido": f"{home_name} vs {away_name}", "liga": liga["nombre"], 
                                "mercado": f"{mejor_grid['mercado']} (Cuota: {calcular_cuotas(mejor_grid['prob'])})", 
                                "prob": mejor_grid["prob"], "estado_pick": mejor_grid["estado"]
                            })

                    top_players_info = extraer_top_jugadores(competition, home_name, away_name)
                    marcador_str = f"🏆 **Marcador Final:** {home_score} - {away_score} (Total: {total_points})\n" if is_final else (f"⏱ **En Vivo:** {home_score} - {away_score}\n" if status_type == "STATUS_IN_PROGRESS" else "")
                    str_oportunidades = "\n".join(oportunidades_alta_confianza)

                    mensaje = (
                        f"🏀 **ANÁLISIS SABERMÉTRICO BASKETBALL**\n"
                        f"🏟 **{home_name} vs. {away_name}**\n"
                        f"🏆 *{liga['nombre']}* (Línea Base Proyectada: {mu_total} Pts)\n"
                        f"⏰ **Fecha/Hora (Col):** {fecha_hora_col}\n"
                        f"🔥 *Key Matchup / Estrellas:* {top_players_info}\n"
                        f"{marcador_str}\n"
                        f"🎯 **Oportunidades Estadísticas de Valor:**\n"
                        f"{str_oportunidades}"
                    )

                    analisis_lista.append({"tipo": "partido", "partido": f"{home_name} vs {away_name}", "mensaje": mensaje, "is_final": is_final})
                except Exception:
                    continue

    analisis_lista = sorted(analisis_lista, key=lambda x: x.get("is_final", False))
    picks_vip_seguros = sorted(picks_vip_seguros, key=lambda x: x["prob"], reverse=True)
    picks_vip_valor = sorted(picks_vip_valor, key=lambda x: x["prob"], reverse=True)

    resumen_parleys = "🌟 **SELECCIÓN VIP: PARLEYS NEURALES DE BASKETBALL** 🌟\n\n"

    if len(picks_vip_seguros) >= 2:
        p1_seguro, p2_seguro = picks_vip_seguros[0], picks_vip_seguros[1]
        b_p1 = " ✅" if p1_seguro["estado_pick"] == "acertado" else (" ❌" if p1_seguro["estado_pick"] == "fallado" else " ⏳")
        b_p2 = " ✅" if p2_seguro["estado_pick"] == "acertado" else (" ❌" if p2_seguro["estado_pick"] == "fallado" else " ⏳")

        resumen_parleys += (
            "🟢 **1. PARLEY RIESGO BAJO (Cuota Segura)**\n"
            f"• **{p1_seguro['partido']}** | {p1_seguro['mercado']} (Prob: {p1_seguro['prob']}%){b_p1}\n"
            f"• **{p2_seguro['partido']}** | {p2_seguro['mercado']} (Prob: {p2_seguro['prob']}%){b_p2}\n\n"
        )
        
    if len(picks_vip_valor) >= 1:
        resumen_parleys += "💎 **2. PARLEY ALTO VALOR (+EV / Contexto & Estadística)**\n"
        for p_val in picks_vip_valor[:2]:
            resumen_parleys += (
                f"• **{p_val['partido']}** | {p_val['mercado']}\n"
                f"  ↳ *Análisis:* {p_val['justificacion']} (Prob Real: {p_val['prob']}% | Cuota Aprox: {p_val['cuota']}) ⏳\n"
            )

    if len(picks_vip_seguros) >= 2 or len(picks_vip_valor) >= 1:
        analisis_lista.insert(0, {"tipo": "parley", "partido": "🔥 TICKET ESPECIAL DE BASKET IA", "mensaje": resumen_parleys})

    return {"partidos": analisis_lista, "picks_vip": picks_vip_seguros, "raw_picks": picks_disponibles}
