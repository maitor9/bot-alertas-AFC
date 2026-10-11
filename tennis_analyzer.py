from datetime import datetime, timedelta
import math
import requests

LIGAS_TENNIS = [
    {"codigo": "atp", "nombre": "ATP Tour", "base_games": 22.5, "sd_games": 3.5},
    {"codigo": "wta", "nombre": "WTA Tour", "base_games": 21.5, "sd_games": 3.5}
]

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
    print("🎾 Escaneando cartelera GLOBAL de Tenis (Fuerza Bruta)...", flush=True)
    analisis_lista = []
    picks_disponibles = []
    picks_altisimos = []
    eventos_procesados = set()

    for liga in LIGAS_TENNIS:
        # ⚠️ SOLUCIÓN FINAL: Solo pedimos el Scoreboard base (trae el estado actual del circuito)
        url = f"https://site.api.espn.com/apis/site/v2/sports/tennis/{liga['codigo']}/scoreboard"
        try:
            response = requests.get(url, timeout=4.0)
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
                        
                        valid_statuses = ["STATUS_SCHEDULED", "STATUS_PRE", "STATUS_IN_PROGRESS", "STATUS_FINAL", "STATUS_FULL_TIME", "STATUS_DELAYED"]
                        if status_type not in valid_statuses: continue
                        is_final = status_type in ["STATUS_FINAL", "STATUS_FULL_TIME"]
                        fecha_hora_col = convertir_hora_colombia(event.get("date", ""))

                        teams = competition.get("competitors", [])
                        if len(teams) < 2: continue

                        p1_data = teams[0]
                        p2_data = teams[1]
                        p1_name = p1_data.get("athlete", {}).get("displayName", "Jugador 1")
                        p2_name = p2_data.get("athlete", {}).get("displayName", "Jugador 2")

                        p1_games = sum([int(p.get("score", 0)) for p in p1_data.get("linescores", [])])
                        p2_games = sum([int(p.get("score", 0)) for p in p2_data.get("linescores", [])])
                        total_games = p1_games + p2_games

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

                        estado_win_1, estado_win_2, estado_over = "pendiente", "pendiente", "pendiente"
                        if is_final:
                            estado_win_1 = "acertado" if p1_data.get("winner", False) else "fallado"
                            estado_win_2 = "acertado" if p2_data.get("winner", False) else "fallado"
                            estado_over = "acertado" if total_games > linea_sugerida else "fallado"

                        if p_win_1 >= 75.0:
                            picks_altisimos.append({
                                "partido": f"{p1_name} vs {p2_name}", "liga": liga["nombre"], "mercado": f"Gana {p1_name}", "prob": p_win_1, "fecha": fecha_hora_col, "estado_pick": estado_win_1, "marcador": f"{p1_games} - {p2_games} (Juegos)"
                            })
                        elif p_win_2 >= 75.0:
                            picks_altisimos.append({
                                "partido": f"{p1_name} vs {p2_name}", "liga": liga["nombre"], "mercado": f"Gana {p2_name}", "prob": p_win_2, "fecha": fecha_hora_col, "estado_pick": estado_win_2, "marcador": f"{p1_games} - {p2_games} (Juegos)"
                            })

                        if p_over_alt >= 75.0:
                            picks_altisimos.append({
                                "partido": f"{p1_name} vs {p2_name}", "liga": liga["nombre"], "mercado": f"Más de {linea_sugerida} Juegos", "prob": p_over_alt, "fecha": fecha_hora_col, "estado_pick": estado_over, "marcador": f"{total_games} Juegos"
                            })

                        picks_disponibles.append({
                            "partido": f"{p1_name} vs {p2_name}", "home": p1_name, "away": p
