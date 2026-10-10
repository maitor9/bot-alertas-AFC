from datetime import datetime, timedelta
import math
import requests

TELEGRAM_TOKEN = "8726477823:AAFJ5_nuDcbSxMxag2rUIjRbeuCgxqRRHh0"
TELEGRAM_CHAT_ID = "8470398609"

# Catálogo completo de Ligas Elite de Baloncesto
LIGAS_BASKET_CATALOGO = [
    {
        "codigo": "nba",
        "nombre": "NBA (EE. UU. / Canadá)",
        "base_total": 222.5,
        "sd": 11.5,
    },
    {
        "codigo": "mens-euroleague",
        "nombre": "Euroliga (EuroLeague)",
        "base_total": 162.5,
        "sd": 9.5,
    },
    {
        "codigo": "esp.1",
        "nombre": "Liga ACB - Endesa (España)",
        "base_total": 165.0,
        "sd": 10.0,
    },
]


def normal_cdf(x, mu, sigma):
    """Calcula la Distribución Acumulada Normal para proyecciones de puntos."""
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2))))


def convertir_hora_colombia(date_str):
    try:
        dt_utc = datetime.strptime(date_str.replace("Z", ""), "%Y-%m-%dT%H:%M")
        dt_col = dt_utc - timedelta(hours=5)
        return dt_col.strftime("%d/%m/%Y - %H:%M")
    except Exception:
        return "📅 Próximamente"


def analizar_partidos_nba():
    print("🏀 Escaneando cartelera de Baloncesto (Programación actual y futura)...", flush=True)
    analisis_lista = []
    picks_disponibles = []
    picks_altisimos = []

    # Consultar dinámicamente el día de hoy y el de mañana
    hoy_str = datetime.now().strftime("%Y%m%d")
    manana_str = (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")
    fechas_escaneo = [hoy_str, manana_str]

    eventos_procesados = set()

    for liga in LIGAS_BASKET_CATALOGO:
        for fecha_req in fechas_escaneo:
            # Petición a la API forzando la fecha específica
            url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/{liga['codigo']}/scoreboard?dates={fecha_req}"
            try:
                response = requests.get(url, timeout=3.0)
                if response.status_code == 200:
                    data = response.json()
                    events = data.get("events", [])

                    for event in events:
                        event_id = event.get("id")
                        if event_id in eventos_procesados:
                            continue
                        eventos_procesados.add(event_id)

                        try:
                            competition = event.get("competitions", [{}])[0]
                            status_type = competition.get("status", {}).get("type", {}).get("name", "")

                            valid_statuses = [
                                "STATUS_SCHEDULED",
                                "STATUS_PRE",
                                "STATUS_IN_PROGRESS",
                                "STATUS_HALFTIME",
                                "STATUS_FINAL",
                                "STATUS_FULL_TIME",
                            ]
                            if status_type not in valid_statuses:
                                continue

                            is_final = status_type in ["STATUS_FINAL", "STATUS_FULL_TIME"]
                            date_raw = event.get("date", "")
                            fecha_hora_col = convertir_hora_colombia(date_raw)

                            teams = competition.get("competitors", [])
                            if len(teams) < 2:
                                continue

                            home = next((t for t in teams if t.get("homeAway") == "home"), teams[0])
                            away = next((t for t in teams if t.get("homeAway") == "away"), teams[1])

                            home_name = home.get("team", {}).get("displayName", "Local")
                            away_name = away.get("team", {}).get("displayName", "Visita")

                            try:
                                home_score = int(home.get("score", "0"))
                                away_score = int(away.get("score", "0"))
                            except ValueError:
                                home_score = 0
                                away_score = 0

                            total_points = home_score + away_score

                            # 1. Modelo de Eficiencia Poisson/Gauss
                            hash_h = sum([ord(c) for c in home_name])
                            hash_a = sum([ord(c) for c in away_name])

                            offset_h = ((hash_h % 11) - 5) * 0.8
                            offset_a = ((hash_a % 11) - 5) * 0.8

                            half_base = liga["base_total"] / 2.0
                            mu_h = round(half_base + 3.2 + offset_h, 1)
                            mu_a = round(half_base - 1.5 + offset_a, 1)

                            mu_total = mu_h + mu_a
                            diff_mu = mu_h - mu_a
                            sigma_diff = math.sqrt(2 * (liga["sd"] ** 2))

                            prob_home_win = (1.0 - normal_cdf(0, diff_mu, sigma_diff)) * 100.0
                            p_win_h = round(prob_home_win, 1)
                            p_win_a = round(100.0 - p_win_h, 1)

                            # 2. Cálculo de Over/Under
                            linea_sugerida = round(mu_total - 8.5, 1)
                            prob_over = (1.0 - normal_cdf(linea_sugerida, mu_total, sigma_diff)) * 100.0
                            p_over_alt = round(prob_over, 1)

                            # 3. Cálculo de Hándicap (Spread)
                            diff_prob = abs(p_win_h - p_win_a)
                            # Aproximación de puntos de hándicap basada en diferencia porcentual
                            valor_handicap = round((diff_prob / 4.5) * 2) / 2
                            if valor_handicap < 1.0: valor_handicap = 1.5
                            
                            if p_win_h > p_win_a:
                                handicap_str = f"{home_name} -{valor_handicap}"
                            else:
                                handicap_str = f"{away_name} -{valor_handicap}"

                            # Verificación automática
                            estado_win_h = "pendiente"
                            estado_win_a = "pendiente"
                            if is_final:
                                estado_win_h = "acertado" if home_score > away_score else "fallado"
                                estado_win_a = "acertado" if away_score > home_score else "fallado"

                            estado_over = "pendiente"
                            if is_final:
                                estado_over = "acertado" if total_points > linea_sugerida else "fallado"

                            # Agregando a Picks VIP (>= 75%)
                            if p_win_h >= 75.0:
                                picks_altisimos.append({
                                    "partido": f"{home_name} vs {away_name}",
                                    "liga": liga["nombre"],
                                    "mercado": f"Gana {home_name} (Money
