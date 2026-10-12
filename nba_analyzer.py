from datetime import datetime, timedelta
import math
import requests
import concurrent.futures

LIGAS_BASKET = [
    {"codigo": "nba", "nombre": "NBA", "base_total": 225.5, "sd_margin": 12.5, "sd_total": 15.0, "home_adv": 3.0},
    {"codigo": "euroleague", "nombre": "Euroliga", "base_total": 160.5, "sd_margin": 10.0, "sd_total": 11.0, "home_adv": 3.5},
    {"codigo": "mens-euroleague", "nombre": "Euroliga", "base_total": 160.5, "sd_margin": 10.0, "sd_total": 11.0, "home_adv": 3.5},
    {"codigo": "eurocup", "nombre": "Eurocup", "base_total": 162.0, "sd_margin": 10.5, "sd_total": 11.5, "home_adv": 3.0},
    {"codigo": "mens-eurocup", "nombre": "Eurocup", "base_total": 162.0, "sd_margin": 10.5, "sd_total": 11.5, "home_adv": 3.0},
    {"codigo": "fiba.champions", "nombre": "FIBA Champions League", "base_total": 158.0, "sd_margin": 10.5, "sd_total": 11.5, "home_adv": 3.2},
    {"codigo": "esp.1", "nombre": "Liga Endesa (España)", "base_total": 164.5, "sd_margin": 11.0, "sd_total": 12.0, "home_adv": 3.0},
    {"codigo": "tur.1", "nombre": "BSL (Turquía)", "base_total": 164.0, "sd_margin": 11.0, "sd_total": 12.0, "home_adv": 3.2},
    {"codigo": "gre.1", "nombre": "A1 (Grecia)", "base_total": 156.0, "sd_margin": 10.0, "sd_total": 11.0, "home_adv": 3.5},
    {"codigo": "ita.1", "nombre": "Lega Basket (Italia)", "base_total": 162.0, "sd_margin": 11.0, "sd_total": 12.0, "home_adv": 2.8},
    {"codigo": "ger.1", "nombre": "BBL (Alemania)", "base_total": 166.0, "sd_margin": 11.5, "sd_total": 12.5, "home_adv": 2.5},
    {"codigo": "fra.1", "nombre": "LNB Pro A (Francia)", "base_total": 158.0, "sd_margin": 10.5, "sd_total": 11.5, "home_adv": 2.8},
    {"codigo": "aba.1", "nombre": "Liga Adriática", "base_total": 160.0, "sd_margin": 11.0, "sd_total": 12.0, "home_adv": 3.0},
    {"codigo": "wnba", "nombre": "WNBA", "base_total": 165.5, "sd_margin": 10.5, "sd_total": 12.0, "home_adv": 2.5},
    {"codigo": "mens-college-basketball", "nombre": "NCAA Masculino", "base_total": 145.5, "sd_margin": 11.5, "sd_total": 11.0, "home_adv": 3.5}
]

def normal_cdf(x, mu, sigma):
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2))))

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

def extraer_win_pct(team_data):
    try:
        records = team_data.get("records", [])
        if records:
            summary = records[0].get("summary", "0-0")
            partes = summary.replace("W", "").replace("L", "").split("-")
            if len(partes) >= 2:
                wins = int(partes[0])
                losses = int(partes[1])
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

def procesar_api_basket(liga, fecha):
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/{liga['codigo']}/scoreboard?dates={fecha}"
    try:
        response = requests.get(url, timeout=3.5)
        if response.status_code == 200:
            data = response.json()
            leagues = data.get("leagues", [])
            if leagues:
                api_nombre = leagues[0].get("name") or leagues[0].get("shortName")
                if api_nombre and len(api_nombre) > 3:
                    liga = liga.copy()
                    liga["nombre"] = api_nombre
            return liga, data
    except:
        pass
    return liga, None

def analizar_partidos_nba():
    print("🏀 Escaneando cartelera Global de Basket (Con umbrales adaptados para Euroliga)...", flush=True)
    analisis_lista = []
    picks_disponibles = []
    picks_vip_seguros = []
    picks_vip_valor = []
    eventos_procesados = set()

    hoy_str = datetime.now().strftime("%Y%m%d")
    manana_str = (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")
    fechas = [hoy_str, manana_str]

    tareas_url = [(liga, fecha) for liga in LIGAS_BASKET for fecha in fechas]

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
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
                    
                    win_pct_h = extraer_win_pct(home)
                    win_pct_a = extraer_win_pct(away)

                    diff_pct = win_pct_h - win_pct_a 
                    mu_diff = (diff_pct * 15.0) + liga["home_adv"]
                    
                    prob_home_win = (1.0 - normal_cdf(0, mu_diff, liga["sd_margin"])) * 100.0
                    p_win_h = round(prob_home_win, 1)
                    p_win_a = round(100.0 - p_win_h, 1)

                    ajuste_ofensivo = ((win_pct_h - 0.5) + (win_pct_a - 0.5)) * 18.0
                    mu_total = round(liga["base_total"] + ajuste_ofensivo, 1)
                    
                    valor_handicap_base = round(abs(mu_diff) * 2.0) / 2.0
                    linea_over_base = round(mu_total, 1)
                    
                    margen_seguro = 5.5
                    safe_spread_val = max(1.0, valor_handicap_base - margen_seguro)
                    
                    if mu_diff > 0:
                        p_spread_safe = round((1.0 - normal_cdf(safe_spread_val, mu_diff, liga["sd_margin"])) * 100.0, 1)
                        safe_spread_str = f"{home_name} +{safe_spread_val}" if safe_spread_val < 0 else f"{home_name} -{safe_spread_val}"
                        cover_estado = home_name
                    else:
                        p_spread_safe = round(normal_cdf(-safe_spread_val, mu_diff, liga["sd_margin"]) * 100.0, 1)
                        safe_spread_str = f"{away_name} +{safe_spread_val}" if safe_spread_val < 0 else f"{away_name} -{safe_spread_val}"
                        cover_estado = away_name

                    linea_over_safe = round(mu_total - 6.5, 1)
                    linea_under_safe = round(mu_total + 6.5, 1)
                    p_over_safe = round((1.0 - normal_cdf(linea_over_safe, mu_total, liga["sd_total"])) * 100.0, 1)
                    p_under_safe = round(normal_cdf(linea_under_safe, mu_total, liga["sd_total"]) * 100.0, 1)

                    try:
                        home_score = int(home.get("score", "0"))
                        away_score = int(away.get("score", "0"))
                    except ValueError:
                        home_score, away_score = 0, 0
                    total_points = home_score + away_score

                    oportunidades_alta_confianza = []
                    candidatos_grid = []

                    # Umbral flexible para Europa (permite capturar partidos muy parejos)
                    es_liga_europea = "Euro" in liga["nombre"] or "Endesa" in liga["nombre"] or "BSL" in liga["nombre"]
                    umbral_dinamico = 58.0 if es_liga_europea else 65.0

                    # --- MOTORES DE INEFICIENCIA (+EV) ---
                    if win_pct_a > win_pct_h and p_win_h >= 42.0:
                        val_just = "Mercado infla visita. Factor de localía hostil clave en Europa." if es_liga_europea else "Mercado sobrevalora el récord visitante."
                        picks_vip_valor.append({
                            "partido": f"{home_name} vs {away_name}", "liga": liga["nombre"],
                            "mercado": f"Moneyline: Gana {home_name}", 
                            "justificacion": val_just,
                            "prob": p_win_h, "cuota": calcular_cuotas_valor(p_win_h) 
                        })
                        oportunidades_alta_confianza.append(f"• 💎 **Gana {home_name} (ML):** {p_win_h}% | Cuota: *{calcular_cuotas_valor(p_win_h)}* ⏳ (Valor: Underdog Local)")

                    if p_under_safe >= 50.0:
                        picks_vip_valor.append({
                            "partido": f"{home_name} vs {away_name}", "liga": liga["nombre"],
                            "mercado": f"Under {linea_over_base} Pts", 
                            "justificacion": "Alta exigencia táctica y posesiones largas en competiciones FIBA/Europa.",
                            "prob": 55.0, "cuota": calcular_cuotas_valor(55.0)
                        })
                        oportunidades_alta_confianza.append(f"• 💎 **Under {linea_over_base} Pts:** 55.0% | Cuota: *{calcular_cuotas_valor(55.0)}* ⏳ (Valor: Under Táctico)")

                    # --- MERCADOS SEGUROS (Con umbral adaptado) ---
                    def evaluar_mercado_seguro(nombre_mercado, prob_val, estado_cumplido, base_umbral):
                        if prob_val >= base_umbral:
                            est = "acertado" if (estado_cumplido and is_final) else ("fallado" if is_final else "pendiente")
                            cuota_str = calcular_cuotas(prob_val)
                            badge = " ✅" if est=="acertado" else (" ❌" if est=="fallado" else " ⏳")
                            oportunidades_alta_confianza.append(f"• **{nombre_mercado}:** {prob_val}% | Cuota: *{cuota_str}*{badge}")
                            candidatos_grid.append({"mercado": nombre_mercado, "prob": prob_val, "estado": est})

                    evaluar_mercado_seguro(f"Moneyline ({home_name})", p_win_h, home_score > away_score, umbral_dinamico)
                    evaluar_mercado_seguro(f"Moneyline ({away_name})", p_win_a, away_score > home_score, umbral_dinamico)
                    
                    spread_won = False
                    if is_final:
                        if cover_estado == home_name: spread_won = (home_score + safe_spread_val) > away_score
                        else: spread_won = (away_score + safe_spread_val) > home_score
                    evaluar_mercado_seguro(f"Hándicap {safe_spread_str}", p_spread_safe, spread_won, umbral_dinamico)
                    
                    evaluar_mercado_seguro(f"Over {linea_over_safe} Pts", p_over_safe, total_points > linea_over_safe, umbral_dinamico)
                    evaluar_mercado_seguro(f"Under {linea_under_safe} Pts", p_under_safe, total_points < linea_under_safe, umbral_dinamico)

                    if not oportunidades_alta_confianza:
                        continue

                    if candidatos_grid:
                        mejor_grid = max(candidatos_grid, key=lambda x: x["prob"])
                        picks_disponibles.append({
                            "partido": f"{home_name} vs {away_name}", "home": home_name, "away": away_name,
                            "liga": liga["nombre"], "fecha": fecha_hora_col, "is_final": is_final,
                            "prob": mejor_grid["prob"], "mercado": mejor_grid["mercado"],
                            "estado_pick": mejor_grid["estado"]
                        })

                        if mejor_grid["prob"] >= (65.0 if es_liga_europea else 72.0):
                            picks_vip_seguros.append({
                                "partido": f"{home_name} vs {away_name}", "liga": liga["nombre"], 
                                "mercado": f"{mejor_grid['mercado']} (Cuota: {calcular_cuotas(mejor_grid['prob'])})", 
                                "prob": mejor_grid["prob"], "estado_pick": mejor_grid["estado"]
                            })

                    marcador_str = f"🏆 **Marcador Final:** {home_score} - {away_score} (Total: {total_points})\n" if is_final else (f"⏱ **En Vivo:** {home_score} - {away_score}\n" if status_type == "STATUS_IN_PROGRESS" else "")
                    str_oportunidades = "\n".join(oportunidades_alta_confianza)

                    mensaje = (
                        f"🏀 **ANÁLISIS SABERMÉTRICO BASKET**\n"
                        f"🏟 **{home_name} vs. {away_name}**\n"
                        f"🏆 *{liga['nombre']}*\n"
                        f"⏰ **Fecha/Hora (Col):** {fecha_hora_col}\n"
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

    resumen_parleys = "🌟 **SELECCIÓN VIP: PARLEYS INTELIGENTES DE BASKET** 🌟\n\n"

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
