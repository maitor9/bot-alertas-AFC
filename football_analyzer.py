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
    return 0.55 

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
        ("lanús", "vélez"), ("lanus", "velez"), ("independiente", "racing"), ("america", "chivas"),
        ("tolima", "nacional"), ("medellin", "nacional")
    ]
    h_low = home_name.lower()
    a_low = away_name.lower()
    for t1, t2 in rivales_historicos:
        if (t1 in h_low and t2 in a_low) or (t2 in h_low and t1 in a_low):
            return True, "🔥⚡ ALTA TENSIÓN"
    return False, "⚽ Partido Oficial"

def obtener_ligas_robustas():
    return [
        "eng.1", "esp.1", "ita.1", "ger.1", "fra.1", "ned.1", "por.1",
        "arg.1", "bra.1", "col.1", "mex.1", "usa.1", "chi.1", "per.1", "uru.1",
        "uefa.champions", "uefa.europa", "copa.libertadores", "copa.sudamericana",
        "fifa.world.qualification.conmebol", "fifa.world.qualification.uefa",
        "fifa.world.qualification.concacaf", "uefa.nations", "fifa.friendly"
    ]

def analizar_partidos_futbol_prematch():
    print("⚽ Escaneando cartelera (Lista de Ligas Robusta - Anti Timeouts)...", flush=True)
    analisis_lista = []
    picks_disponibles = []
    picks_vip_seguros = []
    picks_vip_valor = []
    eventos_procesados = set()

    hoy_str = datetime.now().strftime("%Y%m%d")
    manana_str = (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")
    fechas = [hoy_str, manana_str]
    
    ligas_futbol = obtener_ligas_robustas()

    for liga in ligas_futbol:
        liga_under = any(x in liga for x in ["arg", "col", "bra", "mex", "uru", "chi", "per", "conmebol", "friendly"])
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

                            lambda_h = 1.40 * factor_liga * mult_h
                            lambda_a = 1.20 * factor_liga * mult_a
                            
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
                            
                            p_0_total = poisson(0, total_lambda)
                            p_1_total = poisson(1, total_lambda)
                            p_2_total = (total_lambda**2 * math.exp(-total_lambda)) / 2
                            p_3_total = (total_lambda**3 * math.exp(-total_lambda)) / 6

                            p_under_25 = round((p_0_total + p_1_total + p_2_total) * 100, 1)
                            p_under_35 = round((p_0_total + p_1_total + p_2_total + p_3_total) * 100, 1)
                            
                            p_home_ov_15 = round((1 - prob_0_h - prob_1_h) * 100, 1)
                            
                            p_roja = 18.0
                            motivo_roja = ""
                            if es_caliente:
                                p_roja += 22.0
                                motivo_roja = "Derbi (Fricción alta)"
                            if liga_under:
                                p_roja += 12.0
                                motivo_roja = "Juego Táctico Friccionado" if not motivo_roja else "Derbi de Altísima Tensión"

                            try:
                                home_score = int(home.get("score", "0"))
                                away_score = int(away.get("score", "0"))
                            except ValueError:
                                home_score, away_score = 0, 0
                                
                            total_goals = home_score + away_score
                            btts_real = (home_score > 0 and away_score > 0)
                            
                            oportunidades_alta_confianza = []
                            candidatos_grid = []

                            def evaluar_mercado_seguro(nombre_mercado, prob_val, estado_cumplido, umbral):
                                if prob_val >= umbral:
                                    est = "acertado" if (estado_cumplido and is_final) else ("fallado" if is_final else "pendiente")
                                    cuota_str = calcular_cuotas(prob_val)
                                    badge = " ✅" if est=="acertado" else (" ❌" if est=="fallado" else " ⏳")
                                    oportunidades_alta_confianza.append(f"• **{nombre_mercado}:** {prob_val}% | Cuota: *{calcular_cuotas(prob_val)}*{badge}")
                                    candidatos_grid.append({"mercado": nombre_mercado, "prob": prob_val, "estado": est})

                            evaluar_mercado_seguro("Doble Oportunidad (1X)", p_1x, home_score >= away_score, 70.0)
                            evaluar_mercado_seguro("Doble Oportunidad (X2)", p_x2, away_score >= home_score, 70.0)
                            evaluar_mercado_seguro("Over 1.5 Goles", p_over_15, total_goals > 1.5, 68.0)
                            evaluar_mercado_seguro("Ambos Marcan (BTTS)", p_btts, btts_real, 65.0)
                            evaluar_mercado_seguro("Menos de 2.5 Goles", p_under_25, total_goals < 2.5, 65.0)
                            evaluar_mercado_seguro("Menos de 3.5 Goles", p_under_35, total_goals < 3.5, 75.0)

                            if not oportunidades_alta_confianza:
                                continue

                            if candidatos_grid:
                                mejor_grid = max(candidatos_grid, key=lambda x: x["prob"])
                                picks_disponibles.append({
                                    "partido": f"{home_name} vs {away_name}", "home": home_name, "away": away_name,
                                    "liga": liga_nombre, "fecha": fecha_hora_col, "time": fecha_hora_col, "is_final": is_final,
                                    "prob": mejor_grid["prob"], "mercado": mejor_grid["mercado"],
                                    "estado_pick": mejor_grid["estado"]
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

                            # INYECTAMOS LA FECHA DIRECTAMENTE EN EL OBJETO QUE CONSUME EL FRONTEND
                            analisis_lista.append({
                                "tipo": "partido", 
                                "partido": f"{home_name} vs {away_name}", 
                                "mensaje": mensaje, 
                                "is_final": is_final,
                                "fecha": fecha_hora_col,
                                "time": fecha_hora_col,
                                "datetime": fecha_hora_col
                            })
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
        for p_val in picks_vip_valor[:2]:
            resumen_parleys += (
                f"• **{p_val['partido']}** | {p_val['mercado']}\n"
                f"  ↳ *Análisis:* {p_val['justificacion']} (Prob Real: {p_val['prob']}% | Cuota Aprox: {p_val['cuota']}) ⏳\n"
            )

    if len(picks_vip_seguros) >= 2 or len(picks_vip_valor) >= 1:
        analisis_lista.insert(0, {"tipo": "parley", "partido": "🔥 TICKET ESPECIAL DE PARLEYS IA", "mensaje": resumen_parleys})

    return {"partidos": analisis_lista, "picks_vip": picks_vip_seguros, "raw_picks": picks_disponibles}
