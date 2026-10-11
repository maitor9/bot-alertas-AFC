from datetime import datetime, timedelta
import math
import requests

LIGAS_NHL = [
    {"codigo": "nhl", "nombre": "NHL (Hockey sobre Hielo)", "base_total": 6.0, "sd_margin": 1.8, "sd_total": 2.0, "home_adv": 0.3}
]

def normal_cdf(x, mu, sigma):
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2))))

def extraer_win_pct(team_data):
    try:
        records = team_data.get("records", [])
        if records:
            summary = records[0].get("summary", "0-0-0")
            parts = summary.split("-")
            wins = int(parts[0])
            losses = int(parts[1])
            ot_losses = int(parts[2]) if len(parts) > 2 else 0
            total = wins + losses + ot_losses
            if total > 0: return (wins + (ot_losses * 0.5)) / total
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

def analizar_partidos_nhl():
    print("🏒 Escaneando cartelera de NHL...", flush=True)
    analisis_lista = []
    picks_disponibles = []
    picks_altisimos = []
    eventos_procesados = set()

    base_date = datetime.now() - timedelta(days=1)
    fechas = [(base_date + timedelta(days=i)).strftime('%Y%m%d') for i in range(3)]

    for liga in LIGAS_NHL:
        for fecha in fechas:
            url = f"https://site.api.espn.com/apis/site/v2/sports/hockey/{liga['codigo']}/scoreboard?dates={fecha}"
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
                            
                            valid_statuses = ["STATUS_SCHEDULED", "STATUS_PRE", "STATUS_IN_PROGRESS", "STATUS_FINAL", "STATUS_FULL_TIME"]
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
                            total_goals = home_score + away_score

                            diff_pct = win_pct_h - win_pct_a 
                            mu_diff = (diff_pct * 3.0) + liga["home_adv"]
                            
                            prob_home_win = (1.0 - normal_cdf(0, mu_diff, liga["sd_margin"])) * 100.0
                            p_win_h = round(prob_home_win, 1)
                            p_win_a = round(100.0 - p_win_h, 1)

                            # Puck Line estándar en hockey
                            handicap_str = f"{home_name} -1.5" if mu_diff > 0 else f"{away_name} -1.5"

                            ajuste_ofensivo = ((win_pct_h - 0.5) + (win_pct_a - 0.5)) * 2.5
                            mu_total = round(liga["base_total"] + ajuste_ofensivo, 1)
                            linea_sugerida = round(mu_total - 1.5, 1)
                            
                            prob_over = (1.0 - normal_cdf(linea_sugerida, mu_total, liga["sd_total"])) * 100.0
                            p_over_alt = round(prob_over, 1)

                            estado_win_h, estado_win_a, estado_over = "pendiente", "pendiente", "pendiente"
                            if is_final:
                                estado_win_h = "acertado" if home_score > away_score else "fallado"
                                estado_win_a = "acertado" if away_score > home_score else "fallado"
                                estado_over = "acertado" if total_goals > linea_sugerida else "fallado"

                            if p_win_h >= 75.0:
                                picks_altisimos.append({
                                    "partido": f"{home_name} vs {away_name}", "liga": liga["nombre"], "mercado": f"Gana {home_name}", "prob": p_win_h, "fecha": fecha_hora_col, "estado_pick": estado_win_h, "marcador": f"{home_score} - {away_score}"
                                })
                            elif p_win_a >= 75.0:
                                picks_altisimos.append({
                                    "partido": f"{home_name} vs {away_name}", "liga": liga["nombre"], "mercado": f"Gana {away_name}", "prob": p_win_a, "fecha": fecha_hora_col, "estado_pick": estado_win_a, "marcador": f"{home_score} - {away_score}"
                                })

                            if p_over_alt >= 75.0:
                                picks_altisimos.append({
                                    "partido": f"{home_name} vs {away_name}", "liga": liga["nombre"], "mercado": f"Más de {linea_sugerida} Goles", "prob": p_over_alt, "fecha": fecha_hora_col, "estado_pick": estado_over, "marcador": f"{total_goals} Goles"
                                })

                            picks_disponibles.append({
                                "partido": f"{home_name} vs {away_name}", "home": home_name, "away": away_name, "p_win_h": p_win_h, "p_win_a": p_win_a, "p_over": p_over_alt, "line": linea_sugerida, "fecha": fecha_hora_col, "is_final": is_final
                            })

                            favorito = home_name if p_win_h > 50 else away_name
                            opcion_parley = f"Gana {favorito}" if max(p_win_h, p_win_a) > p_over_alt else f"Over {linea_sugerida} Goles"

                            marcador_str = f"🏆 **Marcador Final:** {home_score} - {away_score} (Total: {total_goals})\n" if is_final else (f"⏱ **En Vivo:** {home_score} - {away_score}\n" if status_type == "STATUS_IN_PROGRESS" else "")

                            mensaje = (
                                f"🏒 **ANÁLISIS NHL PRO (GAUSS/POISSON)**\n\n"
                                f"🏟 **{home_name} vs. {away_name}**\n"
                                f"🏆 *{liga['nombre']}*\n"
                                f"⏰ **Fecha/Hora (Col):** {fecha_hora_col}\n"
                                f"{marcador_str}\n"
                                f"📈 **Moneyline & Puck Line:**\n"
                                f"• **Probabilidad {home_name}:** {p_win_h}%\n"
                                f"• **Probabilidad {away_name}:** {p_win_a}%\n"
                                f"• **Puck Line Sugerido:** {handicap_str}\n\n"
                                f"🔥 **Mercado de Goles (Over/Under):**\n"
                                f"• **Media Proyectada:** {mu_total} Goles\n"
                                f"• **Over {linea_sugerida} Goles:** {p_over_alt}% *(Probabilidad CDF)*\n\n"
                                f"💡 **Sugerencia de Pick:** {opcion_parley}"
                            )

                            analisis_lista.append({"tipo": "partido", "partido": f"{home_name} vs {away_name}", "mensaje": mensaje, "is_final": is_final})
                        except Exception:
                            continue
            except Exception:
                continue

    analisis_lista = sorted(analisis_lista, key=lambda x: x.get("is_final", False))
    picks_altisimos = sorted(picks_altisimos, key=lambda x: x["prob"], reverse=True)

    if len(picks_disponibles) >= 3:
        por_seguridad = sorted(picks_disponibles, key=lambda x: x["p_over"], reverse=True)
        por_ganador = sorted(picks_disponibles, key=lambda x: max(x["p_win_h"], x["p_win_a"]), reverse=True)
        p1, p2, p3 = por_seguridad[0], por_seguridad[1], por_ganador[0]

        resumen_parleys = (
            "🌟 **SELECCIÓN VIP NHL: ICE PRO IA** 🌟\n\n"
            "🟢 **1. PARLEY SEGURO**\n"
            f"• **{p1['partido']}** | Más de {p1['line']} Goles (Prob: {p1['p_over']}%)\n"
            f"• **{p2['partido']}** | Más de {p2['line']} Goles (Prob: {p2['p_over']}%)\n\n"
            "🟡 **2. PARLEY MEDIO**\n"
            f"• **{p3['partido']}** | Gana {p3['home'] if p3['p_win_h'] > p3['p_win_a'] else p3['away']} (Prob: {max(p3['p_win_h'], p3['p_win_a'])}%)\n"
        )
        analisis_lista.insert(0, {"tipo": "parley", "partido": "🔥 TICKET ESPECIAL NHL", "mensaje": resumen_parleys})

    return {"partidos": analisis_lista, "picks_vip": picks_altisimos}
