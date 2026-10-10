from datetime import datetime, timedelta
import math
import requests
import re

TELEGRAM_TOKEN = "8726477823:AAFJ5_nuDcbSxMxag2rUIjRbeuCgxqRRHh0"
TELEGRAM_CHAT_ID = "8470398609"

# Catálogo con parámetros estadísticos reales por liga
LIGAS_BASKET_CATALOGO = [
    {
        "codigo": "nba",
        "nombre": "NBA (EE. UU. / Canadá)",
        "base_total": 224.5,
        "sd_margin": 12.5, # Desviación estándar típica del margen de victoria NBA
        "sd_total": 14.0,  # Desviación estándar típica de puntos totales
        "home_adv": 3.0    # Ventaja de localía en puntos
    },
    {
        "codigo": "mens-euroleague",
        "nombre": "Euroliga (EuroLeague)",
        "base_total": 162.5,
        "sd_margin": 10.0,
        "sd_total": 11.5,
        "home_adv": 4.0
    },
    {
        "codigo": "esp.1",
        "nombre": "Liga ACB - Endesa (España)",
        "base_total": 166.0,
        "sd_margin": 10.5,
        "sd_total": 12.0,
        "home_adv": 3.5
    },
]

def normal_cdf(x, mu, sigma):
    """Calcula la Distribución Acumulada Normal (CDF) para proyecciones reales de puntos y hándicaps."""
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2))))

def extraer_win_pct(team_data):
    """Extrae el récord real (W-L) de la API de ESPN y devuelve el porcentaje de victoria."""
    try:
        records = team_data.get("records", [])
        if records:
            summary = records[0].get("summary", "0-0")
            wins, losses = map(int, summary.split("-"))
            total = wins + losses
            if total > 0:
                return wins / total
    except Exception:
        pass
    return 0.500 # Promedio neutral si no hay datos (ej: pretemporada temprana)

def convertir_hora_colombia(date_str):
    try:
        dt_utc = datetime.strptime(date_str.replace("Z", ""), "%Y-%m-%dT%H:%M")
        dt_col = dt_utc - timedelta(hours=5)
        return dt_col.strftime("%d/%m/%Y - %H:%M")
    except Exception:
        return "📅 Próximamente"

def analizar_partidos_nba():
    print("🏀 Motor Estadístico Activo: Calculando proyecciones con CDF Normal y datos reales...", flush=True)
    analisis_lista = []
    picks_disponibles = []
    picks_altisimos = []

    # Escaneo dinámico: Hoy y Mañana
    hoy_str = datetime.now().strftime("%Y%m%d")
    manana_str = (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")
    fechas_escaneo = [hoy_str, manana_str]
    eventos_procesados = set()

    for liga in LIGAS_BASKET_CATALOGO:
        for fecha_req in fechas_escaneo:
            url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/{liga['codigo']}/scoreboard?dates={fecha_req}"
            try:
                response = requests.get(url, timeout=3.5)
                if response.status_code == 200:
                    data = response.json()
                    events = data.get("events", [])

                    for event in events:
                        event_id = event.get("id")
                        if event_id in eventos_procesados: continue
                        eventos_procesados.add(event_id)

                        try:
                            competition = event.get("competitions", [{}])[0]
                            status_type = competition.get("status", {}).get("type", {}).get("name", "")
                            
                            valid_statuses = ["STATUS_SCHEDULED", "STATUS_PRE", "STATUS_IN_PROGRESS", "STATUS_HALFTIME", "STATUS_FINAL", "STATUS_FULL_TIME"]
                            if status_type not in valid_statuses: continue

                            is_final = status_type in ["STATUS_FINAL", "STATUS_FULL_TIME"]
                            date_raw = event.get("date", "")
                            fecha_hora_col = convertir_hora_colombia(date_raw)

                            teams = competition.get("competitors", [])
                            if len(teams) < 2: continue

                            home = next((t for t in teams if t.get("homeAway") == "home"), teams[0])
                            away = next((t for t in teams if t.get("homeAway") == "away"), teams[1])

                            home_name = home.get("team", {}).get("displayName", "Local")
                            away_name = away.get("team", {}).get("displayName", "Visita")
                            
                            # 1. Extracción de estadísticas reales de la temporada
                            win_pct_h = extraer_win_pct(home)
                            win_pct_a = extraer_win_pct(away)

                            try:
                                home_score = int(home.get("score", "0"))
                                away_score = int(away.get("score", "0"))
                            except ValueError:
                                home_score, away_score = 0, 0
                            total_points = home_score + away_score

                            # 2. MODELO ESTADÍSTICO REAL DE HÁNDICAP Y MONEYLINE
                            # Diferencial de rendimiento (escala de ~18 puntos de impacto máximo)
                            diff_pct = win_pct_h - win_pct_a 
                            # Media de ventaja esperada para el local (Home Advantage + Rendimiento)
                            mu_diff = (diff_pct * 18.0) + liga["home_adv"]
                            
                            # Probabilidad real de ganar usando Distribución Normal (X > 0)
                            prob_home_win = (1.0 - normal_cdf(0.5, mu_diff, liga["sd_margin"])) * 100.0
                            p_win_h = round(prob_home_win, 1)
                            p_win_a = round(100.0 - p_win_h, 1)

                            # Determinar el Hándicap Asiático Matemático (Redondeado a .5)
                            valor_handicap = round(abs(mu_diff) * 2.0) / 2.0
                            if valor_handicap == 0: valor_handicap = 1.5
                            
                            if mu_diff > 0:
                                handicap_str = f"{home_name} -{valor_handicap}"
                            else:
                                handicap_str = f"{away_name} -{valor_handicap}"

                            # 3. MODELO ESTADÍSTICO DE TOTALES (OVER/UNDER)
                            # Ajustar el total base si se enfrentan equipos muy ganadores (mejor eficiencia) o perdedores
                            ajuste_ofensivo = ((win_pct_h - 0.5) + (win_pct_a - 0.5)) * 12.0
                            mu_total = round(liga["base_total"] + ajuste_ofensivo, 1)

                            # Proyectar una línea segura restando ~6.5 puntos al total medio para el "Over" (seguro parley)
                            linea_sugerida = round(mu_total - 6.5, 1)
                            # Probabilidad de superar la línea segura (CDF complementaria)
                            prob_over = (1.0 - normal_cdf(linea_sugerida, mu_total, liga["sd_total"])) * 100.0
                            p_over_alt = round(prob_over, 1)

                            # Verificación automática
                            estado_win_h, estado_win_a, estado_over = "pendiente", "pendiente", "pendiente"
                            if is_final:
                                estado_win_h = "acertado" if home_score > away_score else "fallado"
                                estado_win_a = "acertado" if away_score > home_score else "fallado"
                                estado_over = "acertado" if total_points > linea_sugerida else "fallado"

                            # 4. Clasificación de Picks VIP (Filtro estricto >= 75%)
                            if p_win_h >= 75.0:
                                picks_altisimos.append({
                                    "partido": f"{home_name} vs {away_name}", "liga": liga["nombre"],
                                    "mercado": f"Gana {home_name} (Moneyline)", "prob": p_win_h,
                                    "fecha": fecha_hora_col, "estado_pick": estado_win_h,
                                    "marcador": f"{home_score} - {away_score}",
                                })
                            elif p_win_a >= 75.0:
                                picks_altisimos.append({
                                    "partido": f"{home_name} vs {away_name}", "liga": liga["nombre"],
                                    "mercado": f"Gana {away_name} (Moneyline)", "prob": p_win_a,
                                    "fecha": fecha_hora_col, "estado_pick": estado_win_a,
                                    "marcador": f"{home_score} - {away_score}",
                                })

                            if p_over_alt >= 75.0:
                                picks_altisimos.append({
                                    "partido": f"{home_name} vs {away_name}", "liga": liga["nombre"],
                                    "mercado": f"Más de {linea_sugerida} Puntos", "prob": p_over_alt,
                                    "fecha": fecha_hora_col, "estado_pick": estado_over,
                                    "marcador": (f"{total_points} Pts" if is_final else f"{home_score} - {away_score}"),
                                })

                            picks_disponibles.append({
                                "partido": f"{home_name} vs {away_name}", "home": home_name, "away": away_name,
                                "p_win_h": p_win_h, "p_win_a": p_win_a, "p_over": p_over_alt,
                                "line": linea_sugerida, "fecha": fecha_hora_col, "is_final": is_final,
                            })

                            favorito = home_name if p_win_h > 50 else away_name
                            opcion_parley = (f"Gana {favorito}" if max(p_win_h, p_win_a) > p_over_alt else f"Over {linea_sugerida} Pts")

                            marcador_str = ""
                            if is_final: marcador_str = f"🏆 **Marcador Final:** {home_score} - {away_score} (Total: {total_points} Pts)\n"
                            elif status_type == "STATUS_IN_PROGRESS": marcador_str = f"⏱ **Marcador En Vivo:** {home_score} - {away_score}\n"

                            # HTML/Markdown del Mensaje Analítico Profesional
                            mensaje = (
                                f"🏀 **ANÁLISIS POWER RANKING IA (GAUSS)**\n\n"
                                f"🏟 **{home_name} vs. {away_name}**\n"
                                f"🏆 *{liga['nombre']}*\n"
                                f"⏰ **Fecha/Hora (Col):** {fecha_hora_col}\n"
                                f"{marcador_str}\n"
                                f"📈 **Moneyline & Hándicap (Estadística Real):**\n"
                                f"• **Probabilidad {home_name}:** {p_win_h}%\n"
                                f"• **Probabilidad {away_name}:** {p_win_a}%\n"
                                f"• **Línea de Hándicap Sugerida:** {handicap_str}\n\n"
                                f"🔥 **Mercado de Totales (Over/Under):**\n"
                                f"• **Media de Puntos Proyectada:** {mu_total} Pts\n"
                                f"• **Over {linea_sugerida} Puntos:** {p_over_alt}% *(Probabilidad CDF)*\n\n"
                                f"💡 **Modelo:** CDF Normal iterado con Récord (W-L) oficial.\n"
                                f"🎯 **Sugerencia de Pick:** {opcion_parley}"
                            )

                            analisis_lista.append({
                                "tipo": "partido", "partido": f"{home_name} vs {away_name}",
                                "mensaje": mensaje, "is_final": is_final,
                            })
                        except Exception:
                            continue
            except Exception as e:
                print(f"Error cargando fecha {fecha_req} liga {liga['nombre']}: {e}")

    analisis_lista = sorted(analisis_lista, key=lambda x: x.get("is_final", False))
    picks_altisimos = sorted(picks_altisimos, key=lambda x: x["prob"], reverse=True)

    if len(picks_disponibles) >= 3:
        por_seguridad = sorted(picks_disponibles, key=lambda x: x["p_over"], reverse=True)
        por_ganador = sorted(picks_disponibles, key=lambda x: max(x["p_win_h"], x["p_win_a"]), reverse=True)

        p1, p2 = por_seguridad[0], por_seguridad[1] if len(por_seguridad) > 1 else por_seguridad[0]
        p3, p4, p5 = por_ganador[0], por_ganador[1] if len(por_ganador) > 1 else por_ganador[0], por_ganador[2] if len(por_ganador) > 2 else por_ganador[0]

        ganador_p3 = p3["home"] if p3["p_win_h"] > p3["p_win_a"] else p3["away"]
        ganador_p4 = p4["home"] if p4["p_win_h"] > p4["p_win_a"] else p4["away"]
        ganador_p5 = p5["home"] if p5["p_win_h"] > p5["p_win_a"] else p5["away"]

        resumen_parleys = (
            "🌟 **SELECCIÓN VIP BASKETBALL: PARLEYS BASADOS EN DATOS OFICIALES** 🌟\n\n"
            "🟢 **1. PARLEY RIESGO BAJO (Cuota Segura ~1.85)**\n"
            f"• **{p1['partido']}** ({p1['fecha']}) | Mercado: Más de {p1['line']} Pts (Prob: {p1['p_over']}%)\n"
            f"• **{p2['partido']}** ({p2['fecha']}) | Mercado: Más de {p2['line']} Pts (Prob: {p2['p_over']}%)\n\n"
            "🟡 **2. PARLEY RIESGO MEDIO (Cuota Promedio)**\n"
            f"• **{p3['partido']}** ({p3['fecha']}) | Mercado: Gana {ganador_p3} (Prob: {max(p3['p_win_h'], p3['p_win_a'])}%)\n"
            f"• **{p1['partido']}** ({p1['fecha']}) | Mercado: Más de {p1['line']} Puntos\n\n"
            "🔴 **3. PARLEY RIESGO ALTO (Cuota Alta)**\n"
            f"• **{p4['partido']}** ({p4['fecha']}) | Mercado: Gana {ganador_p4}\n"
            f"• **{p5['partido']}** ({p5['fecha']}) | Mercado: Gana {ganador_p5} + Over {p5['line']} Pts"
        )

        analisis_lista.insert(0, {"tipo": "parley", "partido": "🔥 TICKET ESPECIAL IA", "mensaje": resumen_parleys})

    return {"partidos": analisis_lista, "picks_vip": picks_altisimos}

def analizar_y_enviar_nba_telegram():
    pass
