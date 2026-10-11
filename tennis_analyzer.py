from datetime import datetime, timedelta
import math
import requests

def normal_cdf(x, mu, sigma):
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2))))

def convertir_hora_colombia(date_str):
    try:
        dt_utc = datetime.strptime(date_str.replace("Z", ""), "%Y-%m-%dT%H:%M")
        dt_col = dt_utc - timedelta(hours=5)
        return dt_col.strftime("%d/%m/%Y - %H:%M")
    except Exception:
        return "📅 Próximamente"

def analizar_partidos_tennis():
    print("🎾 Iniciando escaneo de Fuerza Bruta (Múltiples endpoints y fechas)...", flush=True)
    analisis_lista = []
    picks_disponibles = []
    picks_altisimos = []
    eventos_procesados = set()

    # Generamos 4 días (Ayer, Hoy, Mañana, Pasado)
    base_date = datetime.now() - timedelta(days=1)
    fechas_individuales = [(base_date + timedelta(days=i)).strftime('%Y%m%d') for i in range(4)]

    # Exploramos todas las nomenclaturas que ESPN usa para tenis
    rutas_ligas = [
        {"codigo": "atp", "nombre": "ATP Tour", "base_games": 22.5, "sd_games": 3.5},
        {"codigo": "wta", "nombre": "WTA Tour", "base_games": 21.5, "sd_games": 3.5},
        {"codigo": "mens-tennis", "nombre": "ATP Tour (Mens)", "base_games": 22.5, "sd_games": 3.5},
        {"codigo": "womens-tennis", "nombre": "WTA Tour (Womens)", "base_games": 21.5, "sd_games": 3.5}
    ]

    for liga in rutas_ligas:
        for fecha in fechas_individuales:
            url = f"https://site.api.espn.com/apis/site/v2/sports/tennis/{liga['codigo']}/scoreboard?dates={fecha}"
            try:
                # Timeout corto (2.5s) para escanear las 16 combinaciones rápidamente
                response = requests.get(url, timeout=2.5)
                if response.status_code == 200:
                    data = response.json()
                    events = data.get("events", [])

                    for event in events:
                        event_id = event.get("id")
                        if not event_id or event_id in eventos_procesados: 
                            continue
                        eventos_procesados.add(event_id)

                        try:
                            competition = event.get("competitions", [{}])[0]
                            status_type = competition.get("status", {}).get("type", {}).get("name", "")
                            
                            valid_statuses = [
                                "STATUS_SCHEDULED", "STATUS_PRE", "STATUS_IN_PROGRESS", 
                                "STATUS_FINAL", "STATUS_FULL_TIME", "STATUS_DELAYED"
                            ]
                            
                            if status_type not in valid_statuses: 
                                continue
                                
                            is_final = status_type in ["STATUS_FINAL", "STATUS_FULL_TIME"]
                            fecha_hora_col = convertir_hora_colombia(event.get("date", ""))

                            teams = competition.get("competitors", [])
                            if len(teams) < 2: 
                                continue

                            p1_data = teams[0]
                            p2_data = teams[1]
                            p1_name = p1_data.get("athlete", {}).get("displayName", "Jugador 1")
                            p2_name = p2_data.get("athlete", {}).get("displayName", "Jugador 2")

                            # Sumar juegos de todos los sets
                            p1_games = sum([int(p.get("score", 0)) for p in p1_data.get("linescores", [])])
                            p2_games = sum([int(p.get("score", 0)) for p in p2_data.get("linescores", [])])
                            total_games = p1_games + p2_games

                            # Simulador de Eficiencia (Hash-based)
                            hash_1 = sum([ord(c) for c in p1_name])
                            hash_2 = sum([ord(c) for c in p2_name])
                            diff_hash = (hash_1 % 20) - (hash_2 % 20)
                            
                            prob_p1_win = 50.0 + (diff_hash * 2.0)
                            prob_p1_win = max(15.0, min(85.0, prob_p1_win))
                            p_win_1 = round(prob_p1_win, 1)
                            p_win_2 = round(100.0 - p_win_1, 1)

                            mu_total = round(liga["base_games"] - (abs(diff_hash) * 0.15), 1)
                            linea_sugerida = round(mu_total - 2.5, 1)
                            
                            prob_over = (1.0 - normal_cdf(linea_sugerida, mu_total, liga["sd_games"])) * 100.0
                            p_over_alt = round(prob_over, 1)

                            estado_win_1 = "pendiente"
                            estado_win_2 = "pendiente"
                            estado_over = "pendiente"
                            
                            if is_final:
                                estado_win_1 = "acertado" if p1_data.get("winner", False) else "fallado"
                                estado_win_2 = "acertado" if p2_data.get("winner", False) else "fallado"
                                estado_over = "acertado" if total_games > linea_sugerida else "fallado"

                            if p_win_1 >= 75.0:
                                picks_altisimos.append({
                                    "partido": f"{p1_name} vs {p2_name}",
                                    "liga": liga["nombre"],
                                    "mercado": f"Gana {p1_name}",
                                    "prob": p_win_1,
                                    "fecha": fecha_hora_col,
                                    "estado_pick": estado_win_1,
                                    "marcador": f"{p1_games} - {p2_games} (Juegos)"
                                })
                            elif p_win_2 >= 75.0:
                                picks_altisimos.append({
                                    "partido": f"{p1_name} vs {p2_name}",
                                    "liga": liga["nombre"],
                                    "mercado": f"Gana {p2_name}",
                                    "prob": p_win_2,
                                    "fecha": fecha_hora_col,
                                    "estado_pick": estado_win_2,
                                    "marcador": f"{p1_games} - {p2_games} (Juegos)"
                                })

                            if p_over_alt >= 75.0:
                                picks_altisimos.append({
                                    "partido": f"{p1_name} vs {p2_name}",
                                    "liga": liga["nombre"],
                                    "mercado": f"Más de {linea_sugerida} Juegos",
                                    "prob": p_over_alt,
                                    "fecha": fecha_hora_col,
                                    "estado_pick": estado_over,
                                    "marcador": f"{total_games} Juegos"
                                })

                            picks_disponibles.append({
                                "partido": f"{p1_name} vs {p2_name}",
                                "home": p1_name,
                                "away": p2_name,
                                "p_win_h": p_win_1,
                                "p_win_a": p_win_2,
                                "p_over": p_over_alt,
                                "line": linea_sugerida,
                                "fecha": fecha_hora_col,
                                "is_final": is_final
                            })

                            favorito = p1_name if p_win_1 > 50 else p2_name
                            opcion_parley = f"Gana {favorito}" if max(p_win_1, p_win_2) > p_over_alt else f"Over {linea_sugerida} Juegos"

                            if is_final:
                                marcador_str = f"🏆 **Juegos Finales:** {p1_games} - {p2_games} (Total: {total_games})\n"
                            elif status_type == "STATUS_IN_PROGRESS":
                                marcador_str = f"⏱ **En Vivo (Juegos):** {p1_games} - {p2_games}\n"
                            else:
                                marcador_str = ""

                            mensaje = (
                                f"🎾 **ANÁLISIS TENIS PRO (ATP/WTA)**\n\n"
                                f"🏟 **{p1_name} vs. {p2_name}**\n"
                                f"🏆 *{liga['nombre']}*\n"
                                f"⏰ **Fecha/Hora (Col):** {fecha_hora_col}\n"
                                f"{marcador_str}\n"
                                f"📈 **Moneyline (Ganador):**\n"
                                f"• **Probabilidad {p1_name}:** {p_win_1}%\n"
                                f"• **Probabilidad {p2_name}:** {p_win_2}%\n\n"
                                f"🔥 **Mercado de Juegos Totales:**\n"
                                f"• **Media Proyectada:** {mu_total} Juegos\n"
                                f"• **Over {linea_sugerida} Juegos:** {p_over_alt}% *(Probabilidad)*\n\n"
                                f"💡 **Sugerencia de Pick:** {opcion_parley}"
                            )

                            analisis_lista.append({
                                "tipo": "partido",
                                "partido": f"{p1_name} vs {p2_name}",
                                "mensaje": mensaje,
                                "is_final": is_final
                            })
                        except Exception:
                            continue
            except Exception:
                continue

    analisis_lista = sorted(analisis_lista, key=lambda x: x.get("is_final", False))
    picks_altisimos = sorted(picks_altisimos, key=lambda x: x["prob"], reverse=True)

    if len(picks_disponibles) >= 3:
        por_seguridad = sorted(picks_disponibles, key=lambda x: x["p_over"], reverse=True)
        por_ganador = sorted(picks_disponibles, key=lambda x: max(x["p_win_h"], x["p_win_a"]), reverse=True)
        
        p1 = por_seguridad[0]
        p2 = por_seguridad[1] if len(por_seguridad) > 1 else por_seguridad[0]
        p3 = por_ganador[0]

        resumen_parleys = (
            "🌟 **SELECCIÓN VIP TENIS: GRAND SLAM IA** 🌟\n\n"
            "🟢 **1. PARLEY SEGURO**\n"
            f"• **{p1['partido']}** | Más de {p1['line']} Juegos (Prob: {p1['p_over']}%)\n"
            f"• **{p2['partido']}** | Más de {p2['line']} Juegos (Prob: {p2['p_over']}%)\n\n"
            "🟡 **2. PARLEY MEDIO**\n"
            f"• **{p3['partido']}** | Gana {p3['home'] if p3['p_win_h'] > p3['p_win_a'] else p3['away']} (Prob: {max(p3['p_win_h'], p3['p_win_a'])}%)\n"
        )
        
        analisis_lista.insert(0, {
            "tipo": "parley",
            "partido": "🔥 TICKET ESPECIAL TENIS",
            "mensaje": resumen_parleys
        })

    return {"partidos": analisis_lista, "picks_vip": picks_altisimos}
