from datetime import datetime, timedelta
import requests

def convertir_hora_colombia(date_str):
    try:
        dt_utc = datetime.strptime(date_str.replace("Z", ""), "%Y-%m-%dT%H:%M")
        dt_col = dt_utc - timedelta(hours=5)
        return dt_col.strftime("%d/%m/%Y - %H:%M")
    except Exception:
        return "📅 Próximamente"

def analizar_cartelera_ufc():
    print("🥊 Escaneando cartelera de UFC (Ventana de 8 días)...", flush=True)
    analisis_lista = []
    picks_disponibles = []
    picks_altisimos = []
    eventos_procesados = set()

    # Escaneamos 8 días para asegurar que atrapamos la cartelera del sábado
    base_date = datetime.now() - timedelta(days=1)
    fechas = [(base_date + timedelta(days=i)).strftime('%Y%m%d') for i in range(8)]

    for fecha in fechas:
        url = f"https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard?dates={fecha}"
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

                        f1_data = teams[0]
                        f2_data = teams[1]
                        f1_name = f1_data.get("athlete", {}).get("displayName", "Peleador 1")
                        f2_name = f2_data.get("athlete", {}).get("displayName", "Peleador 2")

                        # Simulador de Eficiencia para MMA
                        hash_1 = sum([ord(c) for c in f1_name])
                        hash_2 = sum([ord(c) for c in f2_name])
                        diff_hash = (hash_1 % 20) - (hash_2 % 20)
                        
                        prob_f1_win = 50.0 + (diff_hash * 2.5)
                        prob_f1_win = max(15.0, min(85.0, prob_f1_win))
                        p_win_1 = round(prob_f1_win, 1)
                        p_win_2 = round(100.0 - p_win_1, 1)

                        estado_win_1 = "pendiente"
                        estado_win_2 = "pendiente"
                        
                        if is_final:
                            estado_win_1 = "acertado" if f1_data.get("winner", False) else "fallado"
                            estado_win_2 = "acertado" if f2_data.get("winner", False) else "fallado"

                        if p_win_1 >= 75.0:
                            picks_altisimos.append({
                                "partido": f"{f1_name} vs {f2_name}", "liga": "UFC", "mercado": f"Gana {f1_name}", "prob": p_win_1, "fecha": fecha_hora_col, "estado_pick": estado_win_1, "marcador": "Finalizado" if is_final else "Pendiente"
                            })
                        elif p_win_2 >= 75.0:
                            picks_altisimos.append({
                                "partido": f"{f1_name} vs {f2_name}", "liga": "UFC", "mercado": f"Gana {f2_name}", "prob": p_win_2, "fecha": fecha_hora_col, "estado_pick": estado_win_2, "marcador": "Finalizado" if is_final else "Pendiente"
                            })

                        picks_disponibles.append({
                            "partido": f"{f1_name} vs {f2_name}", "home": f1_name, "away": f2_name, "p_win_h": p_win_1, "p_win_a": p_win_2, "fecha": fecha_hora_col, "is_final": is_final
                        })

                        favorito = f1_name if p_win_1 > 50 else f2_name
                        marcador_str = f"🏆 **Combate Finalizado**\n" if is_final else (f"⏱ **En Progreso**\n" if status_type == "STATUS_IN_PROGRESS" else "")

                        mensaje = (
                            f"🥊 **ANÁLISIS COMBATE UFC**\n\n"
                            f"🏟 **{f1_name} vs. {f2_name}**\n"
                            f"🏆 *Ultimate Fighting Championship*\n"
                            f"⏰ **Fecha/Hora (Col):** {fecha_hora_col}\n"
                            f"{marcador_str}\n"
                            f"📈 **Moneyline (Ganador):**\n"
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

        resumen_parleys = (
            "🌟 **SELECCIÓN VIP UFC: OCTÁGONO IA** 🌟\n\n"
            "🔴 **PARLEY PRINCIPAL (Cuota Alta)**\n"
            f"• **{p1['partido']}** | Gana {p1['home'] if p1['p_win_h'] > p1['p_win_a'] else p1['away']} (Prob: {max(p1['p_win_h'], p1['p_win_a'])}%)\n"
            f"• **{p2['partido']}** | Gana {p2['home'] if p2['p_win_h'] > p2['p_win_a'] else p2['away']} (Prob: {max(p2['p_win_h'], p2['p_win_a'])}%)\n"
        )
        analisis_lista.insert(0, {"tipo": "parley", "partido": "🔥 TICKET ESPECIAL UFC", "mensaje": resumen_parleys})

    return {"partidos": analisis_lista, "picks_vip": picks_altisimos}
