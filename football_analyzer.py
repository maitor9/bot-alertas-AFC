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
        # 5% de margen de casa (juice)
        decimal = round(100.0 / (prob * 1.05), 2)
        return f"{max(1.10, decimal)}"
    except:
        return "1.90"

def extraer_form_index(team_data):
    """
    Extrae el récord actual (W-D-L) que SI está disponible en la API pre-partido
    y genera un índice de rendimiento dinámico entre 0.0 y 1.0.
    """
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
                # El empate suma la mitad de valor que una victoria para el rendimiento
                return (wins + (draws * 0.5)) / total
    except Exception:
        pass
    return 0.5 # Promedio neutral si no hay datos

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
        ("lanús", "vélez"), ("lanus", "velez")
    ]
    h_low = home_name.lower()
    a_low = away_name.lower()
    for t1, t2 in rivales_historicos:
        if (t1 in h_low and t2 in a_low) or (t2 in h_low and t1 in a_low):
            return True, "🔥⚡ [PARTIDO DE ALTA TENSIÓN] - DUELO CRUCIAL"
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
    print("⚽ Escaneando cartelera con Matriz de Poisson Dinámica (Corrección Pro)...", flush=True)
    analisis_lista = []
    picks_disponibles = []
    picks_vip = []
    eventos_procesados = set()

    hoy_str = datetime.now().strftime("%Y%m%d")
    manana_str = (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")
    fechas = [hoy_str, manana_str]
    
    ligas_futbol = obtener_todas_las_ligas_futbol()

    for liga in ligas_futbol:
        # Ligas sudamericanas tienden a tener menos goles que las europeas
        factor_liga = 0.85 if "arg" in liga or "col" in liga or "bra" in liga else 1.05

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
                            
                            # 1. Obtener índice dinámico de forma
                            form_h = extraer_form_index(home)
                            form_a = extraer_form_index(away)

                            # Multiplicador de fuerza (0.6 para equipos pésimos, 1.4 para excelentes)
                            mult_h = 0.6 + (form_h * 0.8)
                            mult_a = 0.6 + (form_a * 0.8)

                            es_caliente, etiqueta_partido = es_partido_caliente(home_name, away_name)

                            # 2. Goles Esperados Dinámicos (Lambdas)
                            lambda_h = 1.35 * factor_liga * mult_h
                            lambda_a = 1.15 * factor_liga * mult_a
                            
                            # Ajuste ligero si es clásico (partido más cerrado)
                            if es_caliente:
                                lambda_h *= 0.95
                                lambda_a *= 0.95

                            total_lambda = lambda_h + lambda_a

                            # 3. Probabilidades base de Poisson
                            prob_0_h, prob_1_h = poisson(0, lambda_h), poisson(1, lambda_h)
                            prob_0_a, prob_1_a = poisson(0, lambda_a), poisson(1, lambda_a)
                            
                            # 4. Matriz Genuina de Resultados para 1, X, 2
                            p_home_win, p_away_win, p_draw = 0.0, 0.0, 0.0
                            for i in range(6):
                                for j in range(6):
                                    prob_score = poisson(i, lambda_h) * poisson(j, lambda_a)
                                    if i > j: p_home_win += prob_score
                                    elif i < j: p_away_win += prob_score
                                    else: p_draw += prob_score
                                    
                            tot_matrix = p_home_win + p_away_win + p_draw
                            if tot_matrix == 0: tot_matrix = 1 # Evitar div/0
                            
                            p_win_h = (p_home_win / tot_matrix) * 100
                            p_win_a = (p_away_win / tot_matrix) * 100
                            p_draw_pct = (p_draw / tot_matrix) * 100

                            # Doble Oportunidad Matemática Pura
                            p_1x = round(p_win_h + p_draw_pct, 1)
                            p_x2 = round(p_win_a + p_draw_pct, 1)

                            # Mercados de Goles
                            p_btts = round((1 - prob_0_h) * (1 - prob_0_a) * 100, 1)
                            p_over_05_ht = round((1 - poisson(0, total_lambda * 0.45)) * 100, 1)
                            p_over_15 = round((1 - (prob_0_h * prob_0_a) - (prob_1_h * prob_0_a) - (prob_0_h * prob_1_a)) * 100, 1)
                            p_over_25 = round((1 - poisson(0, total_lambda) - poisson(1, total_lambda)) * 100, 1)
                            p_home_ov_15 = round((1 - prob_0_h - prob_1_h) * 100, 1)
                            p_away_ov_15 = round((1 - prob_0_a - prob_1_a) * 100, 1)

                            # Resultados reales (En Vivo / Final)
                            try:
                                home_score = int(home.get("score", "0"))
                                away_score = int(away.get("score", "0"))
                            except ValueError:
                                home_score, away_score = 0, 0
                                
                            total_goals = home_score + away_score
                            btts_real = (home_score > 0 and away_score > 0)

                            oportunidades_alta_confianza = []
                            candidatos_partido = []

                            def evaluar_mercado(nombre_mercado, prob_val, estado_cumplido):
                                # Umbral de 65% para filtrar oportunidades viables
                                if prob_val >= 65.0:
                                    est = "acertado" if (estado_cumplido and is_final) else ("fallado" if is_final else "pendiente")
                                    cuota_str = calcular_cuotas(prob_val)
                                    badge = " ✅" if est=="acertado" else (" ❌" if est=="fallado" else " ⏳")
                                    oportunidades_alta_confianza.append(f"• **{nombre_mercado}:** {prob_val}% | Cuota: *{cuota_str}*{badge}")
                                    candidatos_partido.append({"mercado": nombre_mercado, "prob": prob_val, "estado": est})

                            if es_caliente:
                                oportunidades_alta_confianza.append(f"• **🔥⚡ ALERTA DE ALTA TENSIÓN:** Duelo de riesgo.")

                            # Evaluamos todos los mercados sin excepción
                            evaluar_mercado("Doble Oportunidad (1X)", p_1x, home_score >= away_score)
                            evaluar_mercado("Doble Oportunidad (X2)", p_x2, away_score >= home_score)
                            evaluar_mercado("Over 0.5 Goles (1T)", p_over_05_ht, total_goals >= 1)
                            evaluar_mercado("Over 1.5 Goles", p_over_15, total_goals > 1.5)
                            evaluar_mercado("Over 2.5 Goles", p_over_25, total_goals > 2.5)
                            evaluar_mercado(f"Local ({home_name}) Over 1.5", p_home_ov_15, home_score > 1.5)
                            evaluar_mercado(f"Visita ({away_name}) Over 1.5", p_away_ov_15, away_score > 1.5)
                            evaluar_mercado("Ambos Marcan (BTTS)", p_btts, btts_real)

                            # Selección Dinámica del MEJOR mercado para el Grid y VIP
                            mejor_mercado = max(candidatos_partido, key=lambda x: x["prob"]) if candidatos_partido else None

                            if mejor_mercado:
                                # Exportar el mejor pick al VIP si supera el 75%
                                if mejor_mercado["prob"] >= 75.0:
                                    picks_vip.append({
                                        "partido": f"{home_name} vs {away_name}", "liga": liga_nombre, 
                                        "mercado": f"{mejor_mercado['mercado']} (Cuota: {calcular_cuotas(mejor_mercado['prob'])})", 
                                        "prob": mejor_mercado["prob"], "fecha": fecha_hora_col, "estado_pick": mejor_mercado["estado"], 
                                        "marcador": f"{home_score} - {away_score}" if is_final else "Pendiente"
                                    })
                                
                                # Exportar el mejor pick a la cuadrícula de Mega Parley (ya no está amarrado a Over 1.5)
                                picks_disponibles.append({
                                    "partido": f"{home_name} vs {away_name}", "home": home_name, "away": away_name,
                                    "liga": liga_nombre, "fecha": fecha_hora_col, "is_final": is_final,
                                    "prob": mejor_mercado["prob"], 
                                    "mercado": f"{mejor_mercado['mercado']}",
                                    "estado_pick": mejor_mercado["estado"]
                                })

                            marcador_str = f"🏆 **Marcador Final:** {home_score} - {away_score}\n" if is_final else (f"⏱ **En Vivo:** {home_score} - {away_score}\n" if status_type == "STATUS_IN_PROGRESS" else "")
                            str_oportunidades = "\n".join(oportunidades_alta_confianza) if oportunidades_alta_confianza else "• Partido sin tendencias estadísticas fuertes (>65%)."

                            mensaje = (
                                f"⚽ **ANÁLISIS SABERMÉTRICO PROFESIONAL**\n"
                                f"📌 *{etiqueta_partido}*\n\n"
                                f"🏟 **{home_name} vs. {away_name}**\n"
                                f"🏆 *{liga_nombre}*\n"
                                f"⏰ **Fecha/Hora (Col):** {fecha_hora_col}\n"
                                f"{marcador_str}\n"
                                f"🎯 **Oportunidades Estadísticas (> 65%):**\n"
                                f"{str_oportunidades}"
                            )

                            analisis_lista.append({"tipo": "partido", "partido": f"{home_name} vs {away_name}", "mensaje": mensaje, "is_final": is_final})
                        except Exception:
                            continue
            except Exception:
                continue

    analisis_lista = sorted(analisis_lista, key=lambda x: x.get("is_final", False))
    picks_vip = sorted(picks_vip, key=lambda x: x["prob"], reverse=True)

    if len(picks_vip) >= 2:
        p1_vip, p2_vip = picks_vip[0], picks_vip[1]
        badge_p1 = " ✅" if p1_vip["estado_pick"] == "acertado" else (" ❌" if p1_vip["estado_pick"] == "fallado" else " ⏳")
        badge_p2 = " ✅" if p2_vip["estado_pick"] == "acertado" else (" ❌" if p2_vip["estado_pick"] == "fallado" else " ⏳")

        resumen_parleys = (
            "🌟 **SELECCIÓN VIP: PARLEYS INTELIGENTES DE LA JORNADA** 🌟\n\n"
            "🟢 **1. PARLEY RIESGO BAJO (Cuota Segura)**\n"
            f"• **{p1_vip['partido']}** | {p1_vip['mercado']} (Prob: {p1_vip['prob']}%){badge_p1}\n"
            f"• **{p2_vip['partido']}** | {p2_vip['mercado']} (Prob: {p2_vip['prob']}%){badge_p2}\n"
        )
        analisis_lista.insert(0, {"tipo": "parley", "partido": "🔥 TICKET ESPECIAL DE PARLEYS IA", "mensaje": resumen_parleys})

    return {"partidos": analisis_lista, "picks_vip": picks_vip, "raw_picks": picks_disponibles}
