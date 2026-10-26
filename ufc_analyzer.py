from datetime import datetime, timedelta
import requests

def convertir_hora_colombia(date_str):
    try:
        dt_utc = datetime.strptime(date_str.replace("Z", ""), "%Y-%m-%dT%H:%M")
        dt_col = dt_utc - timedelta(hours=5)
        return dt_col.strftime("%d/%m/%Y - %H:%M")
    except Exception:
        return "📅 Próximamente"

def extraer_record_peleador(fighter_data):
    """Extrae el récord real de victorias y derrotas del atleta desde la API de ESPN."""
    try:
        records = fighter_data.get("records", [])
        if records:
            summary = records[0].get("summary", "0-0")
            partes = summary.replace("W", "").replace("L", "").replace("D", "").split("-")
            if len(partes) >= 2:
                wins = int(partes[0])
                losses = int(partes[1])
                draws = int(partes[2]) if len(partes) > 2 else 0
                total = wins + losses + draws
                win_pct = (wins / total) if total > 0 else 0.500
                return wins, losses, win_pct
    except Exception:
        pass
    return 0, 0, 0.500

def analizar_cartelera_ufc():
    print("🥊 Escaneando cartelera completa de UFC (Motor Estadístico Real)...", flush=True)
    analisis_lista = []
    picks_disponibles = []
    picks_altisimos = []
    combates_procesados = set()

    base_date = datetime.now()
    fechas = [(base_date + timedelta(days=i)).strftime('%Y%m%d') for i in range(10)]

    for fecha in fechas:
        url = f"https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard?dates={fecha}"
        try:
            response = requests.get(url, timeout=4.0)
            if response.status_code == 200:
                data = response.json()
                events = data.get("events", [])

                for event in events:
                    event_title = event.get("name", "UFC Event")
                    competitions = event.get("competitions", [])

                    for competition in competitions:
                        comp_id = competition.get("id")
                        if not comp_id or comp_id in combates_procesados: 
                            continue
                        combates_procesados.add(comp_id)

                        try:
                            status_type = competition.get("status", {}).get("type", {}).get("name", "")
                            valid_statuses = ["STATUS_SCHEDULED", "STATUS_PRE", "STATUS_IN_PROGRESS", "STATUS_FINAL", "STATUS_FULL_TIME"]
                            if status_type not in valid_statuses: 
                                continue
                            
                            is_final = status_type in ["STATUS_FINAL", "STATUS_FULL_TIME"]
                            fecha_hora_col = convertir_hora_colombia(competition.get("date", event.get("date", "")))

                            teams = competition.get("competitors", [])
                            if len(teams) < 2: 
                                continue

                            f1_data = teams[0]
                            f2_data = teams[1]
                            
                            f1_athlete = f1_data.get("athlete", {})
                            f2_athlete = f2_data.get("athlete", {})
                            
                            f1_name = f1_athlete.get("displayName", "Peleador 1")
                            f2_name = f2_athlete.get("displayName", "Peleador 2")

                            # Extracción de estadísticas reales de récord
                            w1, l1, wp1 = extraer_record_peleador(f1_data)
                            w2, l2, wp2 = extraer_record_peleador(f2_data)

                            # Modelo cuantitativo basado en rendimiento real y diferencial de victorias
                            diff_wp = wp1 - wp2
                            prob_f1_win = 50.0 + (diff_wp * 35.0)  # Ponderación basada en el delta de efectividad real
                            
                            # Ajuste por volumen de experiencia (total de peleas registradas)
                            total_peleas_1 = w1 + l1
                            total_peleas_2 = w2 + l2
                            if total_peleas_1 > total_peleas_2:
                                prob_f1_win += 2.0
                            elif total_peleas_2 > total_peleas_1:
                                prob_f1_win -= 2.0

                            prob_f1_win = max(15.0, min(85.0, prob_f1_win))
                            p_win_1 = round(prob_f1_win, 1)
                            p_win_2 = round(100.0 - p_win_1, 1)

                            estado_win_1 = "pendiente"
                            estado_win_2 = "pendiente"
                            
                            if is_final:
                                estado_win_1 = "acertado" if f1_data.get("winner", False) else "fallado"
                                estado_win_2 = "acertado" if f2_data.get("winner", False) else "fallado"

                            if p_win_1 >= 72.0:
                                picks_altisimos.append({
                                    "partido": f"{f1_name} vs {f2_name}", "liga": f"UFC ({event_title})", "mercado": f"Gana {f1_name}", "prob": p_win_1, "fecha": fecha_hora_col, "estado_pick": estado_win_1, "marcador": "Finalizado" if is_final else "Pendiente"
                                })
                            elif p_win_2 >= 72.0:
                                picks_altisimos.append({
                                    "partido": f"{f1_name} vs {f2_name}", "liga": f"UFC ({event_title})", "mercado": f"Gana {f2_name}", "prob": p_win_2, "fecha": fecha_hora_col, "estado_pick": estado_win_2, "marcador": "Finalizado" if is_final else "Pendiente"
                                })

                            picks_disponibles.append({
                                "partido": f"{f1_name} vs {f2_name}", "home": f1_name, "away": f2_name, 
                                "p_win_h": p_win_1, "p_win_a": p_win_2, "fecha": fecha_hora_col, "is_final": is_final,
                                "estado_win_1": estado_win_1, "estado_win_2": estado_win_2
                            })

                            favorito = f1_name if p_win_1 > p_win_2 else f2_name
                            marcador_str = f"🏆 **Combate Finalizado**\n" if is_final else (f"⏱ **En Progreso**\n" if status_type == "STATUS_IN_PROGRESS" else "")

                            mensaje = (
                                f"🥊 **ANÁLISIS COMBATE UFC (ESTADÍSTICO)**\n\n"
                                f"🏟 **{f1_name} ({w1}-{l1}) vs. {f2_name} ({w2}-{l2})**\n"
                                f"🏆 *{event_title}*\n"
                                f"⏰ **Fecha/Hora (Col):** {fecha_hora_col}\n"
                                f"{marcador_str}\n"
                                f"📈 **Moneyline (Ganador - Basado en Récord):**\n"
                                f"• **Probabilidad {f1_name}:** {p_win_1}%\n"
                                f"• **Probabilidad {f2_name}:** {p_win_2}%\n\n"
                                f"💡 **Sugerencia de Pick:** Gana {favorito}"
                            )

                            analisis_lista.append({"tipo": "partido", "partido": f"{f1_name} vs {f2_name}", "mensaje": mensaje, "is_final": is_final})
                        except Exception:
                            continue
        except Exception:
            continue

    analisis_lista = sorted(analisis_lista, key=lambda x: x.get("is_final", False))
    picks_altisimos = sorted(picks_altisimos, key=lambda x: x["prob"], reverse=True)

    if len(picks_disponibles) >= 2:
        por_ganador = sorted(picks_disponibles, key=lambda x: max(x["p_win_h"], x["p_win_a"]), reverse=True)
        p1, p2 = por_ganador[0], por_ganador[1] if len(por_ganador) > 1 else por_ganador[0]

        est_p1 = p1["estado_win_1"] if p1["p_win_h"] > p1["p_win_a"] else p1["estado_win_2"]
        badge_p1 = " ✅" if est_p1 == "acertado" else (" ❌" if est_p1 == "fallado" else " ⏳")
        
        est_p2 = p2["estado_win_1"] if p2["p_win_h"] > p2["p_win_a"] else p2["estado_win_2"]
        badge_p2 = " ✅" if est_p2 == "acertado" else (" ❌" if est_p2 == "fallado" else " ⏳")

        resumen_parleys = (
            "🌟 **SELECCIÓN VIP UFC: OCTÁGONO ESTADÍSTICO** 🌟\n\n"
            "🔴 **PARLEY PRINCIPAL (Cuota Alta)**\n"
            f"• **{p1['partido']}** | Gana {p1['home'] if p1['p_win_h'] > p1['p_win_a'] else p1['away']} (Prob: {max(p1['p_win_h'], p1['p_win_a'])}%){badge_p1}\n"
            f"• **{p2['partido']}** | Gana {p2['home'] if p2['p_win_h'] > p2['p_win_a'] else p2['away']} (Prob: {max(p2['p_win_h'], p2['p_win_a'])}%){badge_p2}\n"
        )
        analisis_lista.insert(0, {"tipo": "parley", "partido": "🔥 TICKET ESPECIAL UFC", "mensaje": resumen_parleys})

    return {"partidos": analisis_lista, "picks_vip": picks_altisimos, "raw_picks": picks_disponibles}
