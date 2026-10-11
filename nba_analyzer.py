from datetime import datetime, timedelta
import math
import requests

LIGAS_BASKET = [
    {"codigo": "nba", "nombre": "NBA", "base_total": 225.5, "sd_margin": 12.5, "sd_total": 15.0, "home_adv": 3.0},
    {"codigo": "wnba", "nombre": "WNBA", "base_total": 165.5, "sd_margin": 10.5, "sd_total": 12.0, "home_adv": 2.5},
    {"codigo": "mens-college-basketball", "nombre": "NCAA Masculino", "base_total": 145.5, "sd_margin": 11.5, "sd_total": 11.0, "home_adv": 3.5},
    {"codigo": "euroleague", "nombre": "Euroliga", "base_total": 160.5, "sd_margin": 10.0, "sd_total": 11.0, "home_adv": 3.0}
]

def normal_cdf(x, mu, sigma):
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2))))

def extraer_win_pct(team_data):
    try:
        records = team_data.get("records", [])
        if records:
            summary = records[0].get("summary", "0-0")
            wins, losses = map(int, summary.split("-")[:2])
            total = wins + losses
            if total > 0: return wins / total
    except Exception:
        pass
    return 0.500

def convertir_hora_colombia(date_str):
    try:
        dt_utc = datetime.strptime(date_str.replace("Z", ""), "%Y-%m-%dT%H:%M")
        dt_col = dt_utc - timedelta(hours=5)
        return dt_col.strftime("%d/%m/%Y - %H:%M")
    except Exception:
        return "📅 Próximamente"

def analizar_partidos_nba():
    print("🏀 Escaneando cartelera avanzada de Baloncesto (Filtros Pro y VIP > 75%)...", flush=True)
    analisis_lista = []
    picks_disponibles = []
    picks_altisimos = []
    eventos_procesados = set()

    hoy_str = datetime.now().strftime("%Y%m%d")
    manana_str = (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")
    fechas = [hoy_str, manana_str]

    for liga in LIGAS_BASKET:
        for fecha in fechas:
            url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/{liga['codigo']}/scoreboard?dates={fecha}"
            try:
                response = requests.get(url, timeout=3.5)
                if response.status_code == 200:
                    data = response.json()
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
                            
                            win_pct_h = extraer_win_pct(home)
                            win_pct_a = extraer_win_pct(away)

                            try:
                                home_score = int(home.get("score", "0"))
                                away_score = int(away.get("score", "0"))
                            except ValueError:
                                home_score, away_score = 0, 0
                            total_points = home_score + away_score

                            # Cálculos sabermétricos avanzados
                            diff_pct = win_pct_h - win_pct_a 
                            mu_diff = (diff_pct * 15.0) + liga["home_adv"]
                            
                            prob_home_win = (1.0 - normal_cdf(0, mu_diff, liga["sd_margin"])) * 100.0
                            p_win_h = round(prob_home_win, 1)
                            p_win_a = round(100.0 - p_win_h, 1)

                            # Hándicap / Spread profesional
                            valor_handicap = round(abs(mu_diff) * 2.0) / 2.0
                            if valor_handicap == 0: valor_handicap = 1.0
                            spread_sugerido = f"{home_name} -{valor_handicap}" if mu_diff > 0 else f"{away_name} -{valor_handicap}"
                            p_spread = round(min(92.0, 55.0 + (abs(mu_diff) * 3.5)), 1)

                            # Totales (Over/Under)
                            ajuste_ofensivo = ((win_pct_h - 0.5) + (win_pct_a - 0.5)) * 20.0
                            mu_total = round(liga["base_total"] + ajuste_ofensivo, 1)
                            linea_over = round(mu_total - 6.5, 1)
                            linea_under = round(mu_total + 6.5, 1)
                            
                            p_over = round((1.0 - normal_cdf(linea_over, mu_total, liga["sd_total"])) * 100.0, 1)
                            p_under = round(100.0 - p_over, 1)

                            oportunidades_pro = []

                            # --- FILTROS Y EVALUACIONES DE ESTADO (>= 65% para análisis general) ---
                            if p_win_h >= 65.0:
                                est = "acertado" if (home_score > away_score and is_final) else ("fallado" if is_final else "pendiente")
                                oportunidades_pro.append(f"• **Moneyline (Gana {home_name}):** {p_win_h}%" + (" ✅" if est=="acertado" else (" ❌" if est=="fallado" else " ⏳")))
                            elif p_win_a >= 65.0:
                                est = "acertado" if (away_score > home_score and is_final) else ("fallado" if is_final else "pendiente")
                                oportunidades_pro.append(f"• **Moneyline (Gana {away_name}):** {p_win_a}%" + (" ✅" if est=="acertado" else (" ❌" if est=="fallado" else " ⏳")))

                            if p_spread >= 65.0:
                                est = "acertado" if is_final and (abs(home_score - away_score) >= valor_handicap) else ("fallado" if is_final else "pendiente")
                                oportunidades_pro.append(f"• **Hándicap / Spread ({spread_sugerido}):** {p_spread}%" + (" ✅" if est=="acertado" else (" ❌" if est=="fallado" else " ⏳")))

                            if p_over >= 65.0:
                                est = "acertado" if (total_points > linea_over and is_final) else ("fallado" if is_final else "pendiente")
                                oportunidades_pro.append(f"• **Línea de Puntos (Over {linea_over}):** {p_over}%" + (" ✅" if est=="acertado" else (" ❌" if est=="fallado" else " ⏳")))

                            if p_under >= 65.0:
                                est = "acertado" if (total_points < linea_under and is_final) else ("fallado" if is_final else "pendiente")
                                oportunidades_pro.append(f"• **Línea de Puntos (Under {linea_under}):** {p_under}%" + (" ✅" if est=="acertado" else (" ❌" if est=="fallado" else " ⏳")))


                            # --- EXTRACCIÓN VIP MULTI-MERCADO (>= 75%) ---
                            if p_win_h >= 75.0:
                                picks_altisimos.append({
                                    "partido": f"{home_name} vs {away_name}", "liga": liga["nombre"], "mercado": f"Moneyline: Gana {home_name}", 
                                    "prob": p_win_h, "fecha": fecha_hora_col, 
                                    "estado_pick": "acertado" if (home_score > away_score and is_final) else ("fallado" if is_final else "pendiente"), 
                                    "marcador": f"{home_score} - {away_score}" if is_final else "Pendiente"
                                })
                            if p_win_a >= 75.0:
                                picks_altisimos.append({
                                    "partido": f"{home_name} vs {away_name}", "liga": liga["nombre"], "mercado": f"Moneyline: Gana {away_name}", 
                                    "prob": p_win_a, "fecha": fecha_hora_col, 
                                    "estado_pick": "acertado" if (away_score > home_score and is_final) else ("fallado" if is_final else "pendiente"), 
                                    "marcador": f"{home_score} - {away_score}" if is_final else "Pendiente"
                                })
                            if p_spread >= 75.0:
                                picks_altisimos.append({
                                    "partido": f"{home_name} vs {away_name}", "liga": liga["nombre"], "mercado": f"Hándicap: {spread_sugerido}", 
                                    "prob": p_spread, "fecha": fecha_hora_col, 
                                    "estado_pick": "acertado" if is_final and (abs(home_score - away_score) >= valor_handicap) else ("fallado" if is_final else "pendiente"), 
                                    "marcador": f"{home_score} - {away_score}" if is_final else "Pendiente"
                                })
                            if p_over >= 75.0:
                                picks_altisimos.append({
                                    "partido": f"{home_name} vs {away_name}", "liga": liga["nombre"], "mercado": f"Over {linea_over} Pts", 
                                    "prob": p_over, "fecha": fecha_hora_col, 
                                    "estado_pick": "acertado" if (total_points > linea_over and is_final) else ("fallado" if is_final else "pendiente"), 
                                    "marcador": f"{total_points} Pts" if is_final else "Pendiente"
                                })
                            if p_under >= 75.0:
                                picks_altisimos.append({
                                    "partido": f"{home_name} vs {away_name}", "liga": liga["nombre"], "mercado": f"Under {linea_under} Pts", 
                                    "prob": p_under, "fecha": fecha_hora_col, 
                                    "estado_pick": "acertado" if (total_points < linea_under and is_final) else ("fallado" if is_final else "pendiente"), 
                                    "marcador": f"{total_points} Pts" if is_final else "Pendiente"
                                })


                            estado_over = "acertado" if (total_points > linea_over and is_final) else ("fallado" if is_final else "pendiente")

                            picks_disponibles.append({
                                "partido": f"{home_name} vs {away_name}", "home": home_name, "away": away_name, 
                                "p_win_h": p_win_h, "p_win_a": p_win_a, "p_over": p_over, "line": linea_over, 
                                "fecha": fecha_hora_col, "is_final": is_final, "estado_over": estado_over
                            })

                            marcador_str = f"🏆 **Marcador Final:** {home_score} - {away_score} (Total: {total_points})\n" if is_final else (f"⏱ **En Vivo:** {home_score} - {away_score}\n" if status_type == "STATUS_IN_PROGRESS" else "")
                            str_oportunidades = "\n".join(oportunidades_pro) if oportunidades_pro else "• Ningún mercado de baloncesto supera el 65% de confianza."

                            mensaje = (
                                f"🏀 **ANÁLISIS PROFESIONAL BALONCESTO (TIPS)**\n\n"
                                f"🏟 **{home_name} vs. {away_name}**\n"
                                f"🏆 *{liga['nombre']}*\n"
                                f"⏰ **Fecha/Hora (Col):** {fecha_hora_col}\n"
                                f"{marcador_str}\n"
                                f"🎯 **Mercados Clave (> 65% Confianza):**\n"
                                f"{str_oportunidades}"
                            )

                            analisis_lista.append({"tipo": "partido", "partido": f"{home_name} vs {away_name}", "mensaje": mensaje, "is_final": is_final})
                        except Exception:
                            continue
            except Exception:
                continue

    analisis_lista = sorted(analisis_lista, key=lambda x: x.get("is_final", False))
    # ORDENAMIENTO ESTRICTAMENTE DESCENDENTE PARA LOS PICKS VIP (Mayor probabilidad primero)
    picks_altisimos = sorted(picks_altisimos, key=lambda x: x["prob"], reverse=True)

    if len(picks_disponibles) >= 3:
        por_seguridad = sorted(picks_disponibles, key=lambda x: x["p_over"], reverse=True)
        por_ganador = sorted(picks_disponibles, key=lambda x: max(x["p_win_h"], x["p_win_a"]), reverse=True)
        p1, p2, p3 = por_seguridad[0], por_seguridad[1], por_ganador[0]

        badge_p1 = " ✅" if p1["estado_over"] == "acertado" else (" ❌" if p1["estado_over"] == "fallado" else " ⏳")
        badge_p2 = " ✅" if p2["estado_over"] == "acertado" else (" ❌" if p2["estado_over"] == "fallado" else " ⏳")
        
        ganador_p3 = p3["home"] if p3["p_win_h"] > p3["p_win_a"] else p3["away"]
        badge_p3 = " ⏳"

        resumen_parleys = (
            "🌟 **SELECCIÓN VIP BASKET IA** 🌟\n\n"
            "🟢 **1. PARLEY SEGURO**\n"
            f"• **{p1['partido']}** | Más de {p1['line']} Pts (Prob: {p1['p_over']}%){badge_p1}\n"
            f"• **{p2['partido']}** | Más de {p2['line']} Pts (Prob: {p2['p_over']}%){badge_p2}\n\n"
            "🟡 **2. PARLEY MEDIO**\n"
            f"• **{p3['partido']}** | Gana {ganador_p3} (Prob: {max(p3['p_win_h'], p3['p_win_a'])}%){badge_p3}\n"
        )
        analisis_lista.insert(0, {"tipo": "parley", "partido": "🔥 TICKET ESPECIAL BASKET", "mensaje": resumen_parleys})

    return {"partidos": analisis_lista, "picks_vip": picks_altisimos, "raw_picks": picks_disponibles}
