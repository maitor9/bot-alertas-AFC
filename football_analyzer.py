from datetime import datetime, timedelta
import math
import requests

def poisson(k, lmbda):
    try:
        return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)
    except:
        return 0

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
        return f"{max(1.70, decimal)}"
    except:
        return "2.20"

def extraer_form_index(team_data):
    try:
        records = team_data.get("records", [])
        if records:
            summary = records[0].get("summary", "0-0-0")
            parts = summary.split("-")
            wins = int(parts[0])
            draws = int(parts[1]) if len(parts) > 1 else 0
            losses = int(parts[2]) if len(parts) > 2 else 0
            total = wins + draws + losses
            if total > 0:
                return (wins + (draws * 0.5)) / total
    except Exception:
        pass
    return 0.5 

def convertir_hora_colombia(date_str):
    try:
        dt_utc = datetime.strptime(date_str.replace("Z", ""), "%Y-%m-%dT%H:%M")
        dt_col = dt_utc - timedelta(hours=5)
        return dt_col.strftime("%d/%m/%Y - %H:%M")
    except Exception:
        return "📅 Próximamente"

def es_partido_caliente(home_name, away_name):
    rivales_historicos = [
        ("real madrid", "barcelona"), ("inter", "milan"), ("lazio", "roma"),
        ("boca", "river"), ("celta", "deportivo"), ("liverpool", "everton"),
        ("arsenal", "tottenham"), ("manchester", "city"), ("united", "liverpool"),
        ("porto", "benfica"), ("ajax", "feyenoord"), ("psg", "marseille"),
        ("atletico", "real madrid"), ("juventus", "inter"), ("napoli", "juventus"),
        ("barcelona", "espanyol"), ("sevilla", "betis"), ("celtic", "rangers"),
        ("millonarios", "santa fe"), ("nacional", "america"), ("colo colo", "u de chile"),
        ("lanús", "vélez"), ("lanus", "velez"), ("independiente", "racing"), ("america", "chivas")
    ]
    h_low = home_name.lower()
    a_low = away_name.lower()
    for t1, t2 in rivales_historicos:
        if (t1 in h_low and t2 in a_low) or (t2 in h_low and t1 in a_low):
            return True, "🔥⚡ ALTA TENSIÓN"
    return False, "⚽ Partido Oficial"

def obtener_todas_las_ligas_futbol():
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/leagues"
    try:
        res = requests.get(url, timeout=4)
        if res.status_code == 200:
            data = res.json()
            slugs = []
            for league in data.get("leagues", []):
                slug = league.get("slug") or league.get("abbreviation")
                if slug: slugs.append(slug.lower())
            if slugs: return list(set(slugs))
    except Exception:
        pass
    return [
        "eng.1", "esp.1", "ita.1", "ger.1", "fra.1", "uefa.champions", "uefa.europa",
        "col.1", "arg.1", "bra.1", "mex.1", "usa.1", "ned.1", "por.1", "tur.1"
    ]

def analizar_partidos_futbol_prematch():
    print("⚽ Escaneando cartelera (Filtrando ruido y buscando valor)...", flush=True)
    analisis_lista = []
    picks_disponibles = []
    picks_vip_seguros = []
    picks_vip_valor = []
    eventos_procesados = set()

    hoy_str = datetime.now().strftime("%Y%m%d")
    manana_str = (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")
    fechas = [hoy_str, manana_str]
    
    ligas_futbol = obtener_todas_las_ligas_futbol()

    for liga in ligas_futbol:
        liga_under = any(x in liga for x in ["arg", "col", "bra", "mex", "uru", "chi", "per", "2", "3"])
        factor_liga = 0.85 if liga_under else 1.05

        for fecha in fechas:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga}/scoreboard?dates={fecha}"
            try:
                response = requests.get(url, timeout=2.5)
                if response.status_code == 200:
                    data = response.json()
                    events = data.get("events", [])
                    league_info = data.get("leagues", [{}])[0]
                    liga_nombre = league_info.get("name") or league_info.get("shortName") or "Fútbol Internacional"

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
                            
                            form_h = extraer_form_index(home)
                            form_a = extraer_form_index(away)

                            mult_h = 0.6 + (form_h * 0.8)
                            mult_a = 0.6 + (form_a * 0.8)

                            es_caliente, etiqueta_partido = es_partido_caliente(home_name, away_name)

                            lambda_h = 1.35 * factor_liga * mult_h
                            lambda_a = 1.15 * factor_liga * mult_a
                            
                            if es_caliente:
                                lambda_h *= 0.90
                                lambda_a *= 0.90

                            total_lambda = lambda_h + lambda_a

                            prob_0_h, prob_1_h = poisson(0, lambda_h), poisson(1, lambda_h)
                            prob_0_a, prob_1_a = poisson(0, lambda_a), poisson(1, lambda_a)
                            
                            p_home_win, p_away_win, p_draw = 0.0, 0.0, 0.0
                            for i in range(6):
                                for j in range(6):
                                    prob_score = poisson(i, lambda_h) * poisson(j, lambda_a)
                                    if i > j: p_home_win += prob_score
                                    elif i < j: p_away_win += prob_score
                                    else: p_draw += prob_score
                                    
                            tot_matrix = p_home_win + p_away_win + p_draw
                            if tot_matrix == 0: tot_matrix = 1
                            
                            p_win_h = (p_home_win / tot_matrix) * 100
                            p_win_a = (p_away_win / tot_matrix) * 100
                            p_draw_pct = (p_draw / tot_matrix) * 100

                            p_1x = round(min(92.0, p_win_h + p_draw_pct), 1)
                            p_x2 = round(min(92.0, p_win_a + p_draw_pct), 1)

                            p_btts = round((1 - prob_0_h) * (1 - prob_0_a) * 100, 1)
                            p_over_15 = round((1 - (prob_0_h * prob_0_a) - (prob_1_h * prob_0_a) - (prob_0_h * prob_1_a)) * 100, 1)
                            p_over_25 = round((1 - poisson(0, total_lambda) - poisson(1, total_lambda)) * 100, 1)
                            p_under_25 = round(100.0 - p_over_25, 1)

                            p_home_ov_15 = round((1 - prob_0_h - prob_1_h) * 100, 1)
                            p_away_ov_15 = round((1 - prob_0_a - prob_1_a) * 100, 1)
                            p_win_to_nil_h = round((p_win_h / 100.0) * prob_0_a * 100, 1)
                            
                            p_roja = 18.0
                            motivo_roja = ""
                            if es_caliente:
                                p_roja += 22.0
                                motivo_roja = "Derbi"
                            if liga_sudamericana:
                                p_roja += 12.0
                                motivo_roja = "Liga Friccionada" if not motivo_roja else "Derbi Sudamericano"

                            try:
                                home_score = int(home.get("score", "0"))
                                away_score = int(away.get("score", "0"))
                            except ValueError:
                                home_score, away_score = 0, 0
                                
                            total_goals = home_score + away_score
                            btts_real = (home_score > 0 and away_score > 0)
                            
                            oportunidades_alta_confianza = []
                            candidatos_seguros = []

                            # --- EXTRACCIÓN DE PICKS DE VALOR (+EV) ---
                            if p_roja >= 40.0:
                                picks_vip_valor.append({
                                    "partido": f"{home_name} vs {away_name}", "liga": liga_nombre,
                                    "mercado": f"Tarjeta Roja: Sí", "justificacion": motivo_roja,
                                    "prob": p_roja, "cuota": calcular_cuotas_valor(p_roja)
                                })
                                oportunidades_alta_confianza.append(f"• 💎 **Roja (Sí):** {p_roja}% | Cuota: *{calcular_cuotas_valor(p_roja)}* ⏳ (Valor: {motivo_roja})")
                            
                            if form_h >= 0.65 and form_a <= 0.40 and p_win_h < 45.0:
                                prob_ev = round(p_1x, 1)
                                picks_vip_valor.append({
                                    "partido": f"{home_name} vs {away_name}", "liga": liga_nombre,
                                    "mercado": f"{home_name} Hándicap Asiático +1.0 o (1X)", 
                                    "justificacion": "Mercado infla a la visita. Local sólido.",
                                    "prob": prob_ev, "cuota": calcular_cuotas_valor(prob_ev - 15.0) 
                                })
                                oportunidades_alta_confianza.append(f"• 💎 **{home_name} Hándicap +1.0 (1X):** {prob_ev}% | Cuota: *{calcular_cuotas_valor(prob_ev - 15.0)}* ⏳ (Valor: Falso Favorito)")

                            if liga_under and lambda_h > 1.3 and lambda_a > 1.15 and p_btts >= 50.0:
                                picks_vip_valor.append({
                                    "partido": f"{home_name} vs {away_name}", "liga": liga_nombre,
                                    "mercado": "Ambos Anotan: SÍ", 
                                    "justificacion": "Liga Under pero alta producción actual.",
                                    "prob": p_btts, "cuota": calcular_cuotas_valor(p_btts)
                                })
                                oportunidades_alta_confianza.append(f"• 💎 **Ambos Anotan (Sí):** {p_btts}% | Cuota: *{calcular_cuotas_valor(p_btts)}* ⏳ (Valor: Tendencia oculta)")
                            
                            if es_caliente and total_lambda < 2.3 and p_under_25 >= 55.0:
                                picks_vip_valor.append({
                                    "partido": f"{home_name} vs {away_name}", "liga": liga_nombre,
                                    "mercado": "Menos de 2.5 Goles", 
                                    "justificacion": "Derbi pasional y cerrado. Miedo a perder.",
                                    "prob": p_under_25, "cuota": calcular_cuotas_valor(p_under_25)
                                })
                                oportunidades_alta_confianza.append(f"• 💎 **Under 2.5 Goles:** {p_under_25}% | Cuota: *{calcular_cuotas_valor(p_under_25)}* ⏳ (Valor: Under táctico)")

                            if p_home_ov_15 >= 50.0 and p_home_ov_15 < 75.0 and lambda_h >= 1.6:
                                picks_vip_valor.append({
                                    "partido": f"{home_name} vs {away_name}", "liga": liga_nombre,
                                    "mercado": f"{home_name} - Más de 1.5 Goles", "justificacion": "Superioridad ofensiva local",
                                    "prob": p_home_ov_15, "cuota": calcular_cuotas_valor(p_home_ov_15)
                                })
                                oportunidades_alta_confianza.append(f"• 💎 **{home_name} Over 1.5:** {p_home_ov_15}% | Cuota: *{calcular_cuotas_valor(p_home_ov_15)}* ⏳ (Valor: Ofensiva fuerte)")
                                
                            if p_win_to_nil_h >= 35.0 and p_win_to_nil_h < 60.0:
                                picks_vip_valor.append({
                                    "partido": f"{home_name} vs {away_name}", "liga": liga_nombre,
                                    "mercado": f"{home_name} Gana a Cero (Win to Nil)", "justificacion": "Defensa local sólida",
                                    "prob": p_win_to_nil_h, "cuota": calcular_cuotas_valor(p_win_to_nil_h)
                                })
                                oportunidades_alta_confianza.append(f"• 💎 **{home_name} Gana a Cero:** {p_win_to_nil_h}% | Cuota: *{calcular_cuotas_valor(p_win_to_nil_h)}* ⏳ (Valor: Defensa de hierro)")

                            # --- MERCADOS SEGUROS CLÁSICOS ---
                            def evaluar_mercado_seguro(nombre_mercado, prob_val, estado_cumplido):
                                umbral = 75.0 if "Doble Oportunidad" in nombre_mercado else 65.0
                                if prob_val >= umbral:
                                    est = "acertado" if (estado_cumplido and is_final) else ("fallado" if is_final else "pendiente")
                                    cuota_str = calcular_cuotas(prob_val)
                                    badge = " ✅" if est=="acertado" else (" ❌" if est=="fallado" else " ⏳")
                                    oportunidades_alta_confianza.append(f"• **{nombre_mercado}:** {prob_val}% | Cuota: *{cuota_str}*{badge}")
                                    if "Doble Oportunidad" not in nombre_mercado:
                                        candidatos_seguros.append({"mercado": nombre_mercado, "prob": prob_val, "estado": est})

                            evaluar_mercado_seguro("Doble Oportunidad (1X)", p_1x, home_score >= away_score)
                            evaluar_mercado_seguro("Doble Oportunidad (X2)", p_x2, away_score >= home_score)
                            evaluar_mercado_seguro("Over 1.5 Goles", p_over_15, total_goals > 1.5)
                            evaluar_mercado_seguro("Ambos Marcan (BTTS)", p_btts, btts_real)

                            # FILTRO DE RUIDO ABSOLUTO: Si no hay oportunidades seguras ni de valor, saltamos el partido
                            if not oportunidades_alta_confianza:
                                continue

                            if candidatos_seguros:
                                mejor_seguro = max(candidatos_seguros, key=lambda x: x["prob"])
                                if mejor_seguro["prob"] >= 72.0:
                                    picks_vip_seguros.append({
                                        "partido": f"{home_name} vs {away_name}", "liga": liga_nombre, 
                                        "mercado": f"{mejor_seguro['mercado']} (Cuota: {calcular_cuotas(mejor_seguro['prob'])})", 
                                        "prob": mejor_seguro["prob"], "estado_pick": mejor_seguro["estado"]
                                    })
                                
                                picks_disponibles.append({
                                    "partido": f"{home_name} vs {away_name}", "home": home_name, "away": away_name,
                                    "liga": liga_nombre, "fecha": fecha_hora_col, "is_final": is_final,
                                    "prob": mejor_seguro["prob"], "mercado": f"{mejor_seguro['mercado']}",
                                    "estado_pick": mejor_seguro["estado"]
                                })

                            marcador_str = f"🏆 **Marcador Final:** {home_score} - {away_score}\n" if is_final else (f"⏱ **En Vivo:** {home_score} - {away_score}\n" if status_type == "STATUS_IN_PROGRESS" else "")
                            str_oportunidades = "\n".join(oportunidades_alta_confianza)

                            mensaje = (
                                f"⚽ **ANÁLISIS SABERMÉTRICO PROFESIONAL**\n"
                                f"📌 *{etiqueta_partido}*\n\n"
                                f"🏟 **{home_name} vs. {away_name}**\n"
                                f"🏆 *{liga_nombre}*\n"
                                f"⏰ **Fecha/Hora (Col):** {fecha_hora_col}\n"
                                f"{marcador_str}\n"
                                f"🎯 **Oportunidades Estadísticas:**\n"
                                f"{str_oportunidades}"
                            )

                            analisis_lista.append({"tipo": "partido", "partido": f"{home_name} vs {away_name}", "mensaje": mensaje, "is_final": is_final})
                        except Exception:
                            continue
            except Exception:
                continue

    analisis_lista = sorted(analisis_lista, key=lambda x: x.get("is_final", False))
    picks_vip_seguros = sorted(picks_vip_seguros, key=lambda x: x["prob"], reverse=True)
    picks_vip_valor = sorted(picks_vip_valor, key=lambda x: x["prob"], reverse=True)

    resumen_parleys = "🌟 **SELECCIÓN VIP: PARLEYS INTELIGENTES DE LA JORNADA** 🌟\n\n"

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
        for i, p_val in enumerate(picks_vip_valor[:2]):
            resumen_parleys += (
                f"• **{p_val['partido']}** | {p_val['mercado']}\n"
                f"  ↳ *Contexto de Valor:* {p_val['justificacion']} (Prob Real: {p_val['prob']}% | Cuota Aprox: {p_val['cuota']}) ⏳\n"
            )

    if len(picks_vip_seguros) >= 2 or len(picks_vip_valor) >= 1:
        analisis_lista.insert(0, {"tipo": "parley", "partido": "🔥 TICKET ESPECIAL DE PARLEYS IA", "mensaje": resumen_parleys})

    return {"partidos": analisis_lista, "picks_vip": picks_vip_seguros, "raw_picks": picks_disponibles}
