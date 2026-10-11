from datetime import datetime, timedelta
import math
import requests

def poisson(k, lmbda):
    try:
        return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)
    except:
        return 0

def extraer_win_pct(team_data):
    try:
        records = team_data.get("records", [])
        if records:
            summary = records[0].get("summary", "0-0-0")
            parts = summary.split("-")
            wins = int(parts[0])
            draws = int(parts[1]) if len(parts) > 1 else 0
            losses = int(parts[2]) if len(parts) > 2 else 0
            total = wins + draws + losses
            if total > 0: return wins / total
    except Exception:
        pass
    return 0.35

def convertir_hora_colombia(date_str):
    try:
        dt_utc = datetime.strptime(date_str.replace("Z", ""), "%Y-%m-%dT%H:%M")
        dt_col = dt_utc - timedelta(hours=5)
        return dt_col.strftime("%d/%m/%Y - %H:%M")
    except Exception:
        return "📅 Próximamente"

def analizar_partidos_futbol_prematch():
    print("⚽ Escaneando cartelera de Fútbol (Hoy y Mañana)...", flush=True)
    analisis_lista = []
    picks_disponibles = []
    picks_vip = []
    eventos_procesados = set()

    # Escanear HOY y MAÑANA exclusivamente
    hoy_str = datetime.now().strftime("%Y%m%d")
    manana_str = (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")
    fechas = [hoy_str, manana_str]
    
    # Ligas de ESPN
    ligas_futbol = ["eng.1", "esp.1", "ita.1", "ger.1", "fra.1", "uefa.champions", "uefa.europa", "col.1"]

    for liga in ligas_futbol:
        for fecha in fechas:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga}/scoreboard?dates={fecha}"
            try:
                response = requests.get(url, timeout=3.5)
                if response.status_code == 200:
                    data = response.json()
                    events = data.get("events", [])
                    liga_nombre = data.get("leagues", [{}])[0].get("name", "Fútbol")

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
                            
                            win_pct_h = extraer_win_pct(home)
                            win_pct_a = extraer_win_pct(away)

                            # Proyecciones de goles base
                            lambda_h = 1.3 + (win_pct_h * 1.2) + 0.3 # Ventaja local
                            lambda_a = 1.1 + (win_pct_a * 1.2)
                            
                            prob_0_h, prob_1_h = poisson(0, lambda_h), poisson(1, lambda_h)
                            prob_0_a, prob_1_a = poisson(0, lambda_a), poisson(1, lambda_a)
                            
                            p_btts = round((1 - prob_0_h) * (1 - prob_0_a) * 100, 1)
                            p_over_15 = round((1 - (prob_0_h * prob_0_a) - (prob_0_h * prob_1_a) - (prob_1_h * prob_0_a)) * 100, 1)
                            p_over_25 = round((p_over_15 * 0.65), 1) 
                            
                            p_win_h = round((1 - prob_0_h - prob_1_h + 0.1) * 100, 1)
                            p_win_a = round((1 - prob_0_a - prob_1_a + 0.05) * 100, 1)
                            p_win_h = min(85.0, p_win_h)
                            p_win_a = min(85.0, p_win_a)
                            p_draw = round(100.0 - p_win_h - p_win_a, 1)
                            
                            try:
                                home_score = int(home.get("score", "0"))
                                away_score = int(away.get("score", "0"))
                            except ValueError:
                                home_score, away_score = 0, 0
                                
                            total_goals = home_score + away_score
                            btts_real = (home_score > 0 and away_score > 0)
                            
                            estado_win_h, estado_win_a, estado_btts = "pendiente", "pendiente", "pendiente"
                            estado_over_15, estado_over_25 = "pendiente", "pendiente"
                            
                            if is_final:
                                estado_win_h = "acertado" if home_score > away_score else "fallado"
                                estado_win_a = "acertado" if away_score > home_score else "fallado"
                                estado_btts = "acertado" if btts_real else "fallado"
                                estado_over_15 = "acertado" if total_goals > 1.5 else "fallado"
                                estado_over_25 = "acertado" if total_goals > 2.5 else "fallado"

                            picks_disponibles.append({
                                "partido": f"{home_name} vs {away_name}", "home": home_name, "away": away_name,
                                "p_win_h": p_win_h, "p_win_a": p_win_a, "p_btts": p_btts, "p_over_15": p_over_15, "p_over_25": p_over_25,
                                "estado_win_h": estado_win_h, "estado_win_a": estado_win_a, "estado_btts": estado_btts,
                                "estado_over_15": estado_over_15, "estado_over_25": estado_over_25, "is_final": is_final,
                                "liga": liga_nombre, "fecha": fecha_hora_col, "home_score": home_score, "away_score": away_score,
                                "prob": max(p_win_h, p_win_a, p_over_15), "mercado": "Gana Local" if p_win_h > p_over_15 else "Más de 1.5 Goles",
                                "estado_pick": estado_win_h if p_win_h > p_over_15 else estado_over_15
                            })
                            
                            if p_over_15 >= 75.0:
                                picks_vip.append({
                                    "partido": f"{home_name} vs {away_name}", "liga": liga_nombre, "mercado": "Más de 1.5 Goles", 
                                    "prob": p_over_15, "fecha": fecha_hora_col, "estado_pick": estado_over_15, 
                                    "marcador": f"{home_score} - {away_score}" if is_final else "Pendiente"
                                })

                            marcador_str = f"🏆 **Marcador Final:** {home_score} - {away_score}\n" if is_final else (f"⏱ **En Vivo:** {home_score} - {away_score}\n" if status_type == "STATUS_IN_PROGRESS" else "")

                            mensaje = (
                                f"⚽ **ANÁLISIS FÚTBOL PRO (POISSON)**\n\n"
                                f"🏟 **{home_name} vs. {away_name}**\n"
                                f"🏆 *{liga_nombre}*\n"
                                f"⏰ **Fecha/Hora (Col):** {fecha_hora_col}\n"
                                f"{marcador_str}\n"
                                f"📈 **Mercado Principal:**\n"
                                f"• **Local ({home_name}):** {p_win_h}%\n"
                                f"• **Empate:** {p_draw}%\n"
                                f"• **Visita ({away_name}):** {p_win_a}%\n\n"
                                f"🔥 **Goles y BTTS:**\n"
                                f"• **Más de 1.5 Goles:** {p_over_15}%\n"
                                f"• **Ambos Marcan (Sí):** {p_btts}%\n"
                            )

                            analisis_lista.append({"tipo": "partido", "partido": f"{home_name} vs {away_name}", "mensaje": mensaje, "is_final": is_final})
                        except Exception:
                            continue
            except Exception:
                continue

    analisis_lista = sorted(analisis_lista, key=lambda x: x.get("is_final", False))
    picks_vip = sorted(picks_vip, key=lambda x: x["prob"], reverse=True)

    if len(picks_disponibles) >= 4:
        por_seguridad = sorted(picks_disponibles, key=lambda x: x["p_over_15"], reverse=True)
        por_goles = sorted(picks_disponibles, key=lambda x: x["p_over_25"], reverse=True)
        por_ganador = sorted(picks_disponibles, key=lambda x: max(x["p_win_h"], x["p_win_a"]), reverse=True)
        por_btts = sorted(picks_disponibles, key=lambda x: x["p_btts"], reverse=True)

        p1_bajo = por_seguridad[0]
        p2_bajo = por_seguridad[1]
        
        p1_medio = por_goles[0]
        p2_medio = por_ganador[0]
        
        p1_alto = por_btts[0]
        p2_alto = por_ganador[1]

        # Validaciones de checks (✅ / ❌ / ⏳)
        badge_p1_bajo = " ✅" if p1_bajo["estado_over_15"] == "acertado" else (" ❌" if p1_bajo["estado_over_15"] == "fallado" else " ⏳")
        badge_p2_bajo = " ✅" if p2_bajo["estado_over_15"] == "acertado" else (" ❌" if p2_bajo["estado_over_15"] == "fallado" else " ⏳")
        
        badge_p1_medio = " ✅" if p1_medio["estado_over_25"] == "acertado" else (" ❌" if p1_medio["estado_over_25"] == "fallado" else " ⏳")
        ganador_p2_medio = p2_medio["home"] if p2_medio["p_win_h"] > p2_medio["p_win_a"] else p2_medio["away"]
        est_p2_medio = p2_medio["estado_win_h"] if p2_medio["p_win_h"] > p2_medio["p_win_a"] else p2_medio["estado_win_a"]
        badge_p2_medio = " ✅" if est_p2_medio == "acertado" else (" ❌" if est_p2_medio == "fallado" else " ⏳")
        
        badge_p1_alto = " ✅" if p1_alto["estado_btts"] == "acertado" else (" ❌" if p1_alto["estado_btts"] == "fallado" else " ⏳")
        ganador_p2_alto = p2_alto["home"] if p2_alto["p_win_h"] > p2_alto["p_win_a"] else p2_alto["away"]
        est_p2_alto = p2_alto["estado_win_h"] if p2_alto["p_win_h"] > p2_alto["p_win_a"] else p2_alto["estado_win_a"]
        badge_p2_alto = " ✅" if (est_p2_alto == "acertado" and p2_alto["estado_over_15"] == "acertado") else (" ❌" if (est_p2_alto == "fallado" or p2_alto["estado_over_15"] == "fallado") else " ⏳")

        resumen_parleys = (
            "🌟 **SELECCIÓN VIP: PARLEYS INTELIGENTES DE LA JORNADA** 🌟\n\n"
            "🟢 **1. PARLEY RIESGO BAJO (Cuota Segura)**\n"
            f"• **{p1_bajo['partido']}** | Mercado: Más de 1.5 Goles (Prob: {p1_bajo['p_over_15']}%){badge_p1_bajo}\n"
            f"• **{p2_bajo['partido']}** | Mercado: Más de 1.5 Goles (Prob: {p2_bajo['p_over_15']}%){badge_p2_bajo}\n\n"
            "🟡 **2. PARLEY RIESGO MEDIO (Cuota Promedio)**\n"
            f"• **{p1_medio['partido']}** | Mercado: Más de 2.5 Goles (Prob: {p1_medio['p_over_25']}%){badge_p1_medio}\n"
            f"• **{p2_medio['partido']}** | Mercado: Gana {ganador_p2_medio} (Prob: {max(p2_medio['p_win_h'], p2_medio['p_win_a'])}%){badge_p2_medio}\n\n"
            "🔴 **3. PARLEY RIESGO ALTO (Cuota Alta)**\n"
            f"• **{p1_alto['partido']}** | Mercado: Ambos Marcan (BTTS Sí) (Prob: {p1_alto['p_btts']}%){badge_p1_alto}\n"
            f"• **{p2_alto['partido']}** | Mercado: Gana {ganador_p2_alto} + Over 1.5 Goles{badge_p2_alto}\n"
        )
        analisis_lista.insert(0, {"tipo": "parley", "partido": "🔥 TICKET ESPECIAL DE PARLEYS IA", "mensaje": resumen_parleys})

    return {"partidos": analisis_lista, "picks_vip": picks_vip, "raw_picks": picks_disponibles}
