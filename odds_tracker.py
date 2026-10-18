import os
import requests
from football_analyzer import analizar_partidos_futbol_prematch

ODDS_API_KEY = os.getenv("ODDS_API_KEY", "87843c0f13532b677bc7dcde129e97ae")

def generar_parley_optimo(target_cuota=1.50):
    # 1. Obtenemos los picks VIP de fútbol del analizador sabermétrico
    resultado_futbol = analizar_partidos_futbol_prematch()
    picks_vip = resultado_futbol.get("picks_vip", [])
    
    if not picks_vip:
        return {"status": "error", "mensaje": "No hay picks VIP disponibles en este momento.", "picks": []}

    # 2. Consultamos cuotas reales en The Odds API (Premier League como referencia principal)
    url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h&oddsFormat=decimal"
    odds_map = {}
    
    try:
        response = requests.get(url, timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            for evento in data:
                home = evento.get("home_team", "").lower()
                away = evento.get("away_team", "").lower()
                bookmakers = evento.get("bookmakers", [])
                if not bookmakers: continue
                bm = next((b for b in bookmakers if b.get("key") == "bet365"), bookmakers[0])
                markets = bm.get("markets", [])
                h2h = next((m for m in markets if m.get("key") == "h2h"), None)
                if h2h:
                    prices = {o.get("name").lower(): o.get("price") for o in h2h.get("outcomes", [])}
                    odds_map[(home, away)] = prices
    except Exception as e:
        print(f"⚠️ Error conectando a The Odds API para parley: {e}")

    # 3. Ordenamos los picks por probabilidad de mayor a menor
    picks_ordenados = sorted(picks_vip, key=lambda x: x.get("prob", 0), reverse=True)
    
    parley_seleccionado = []
    cuota_acumulada = 1.0
    
    for pick in picks_ordenados:
        if cuota_acumulada >= target_cuota and len(parley_seleccionado) >= 1:
            break
            
        partido = pick.get("partido", "")
        mercado = pick.get("mercado", "")
        prob = pick.get("prob", 75.0)
        
        # Asignación de cuota real validada o estimación de alta probabilidad
        cuota_real = 1.28
        if " vs " in partido:
            equipos = partido.split(" vs ")
            h_key = equipos[0].strip().lower()
            a_key = equipos[1].strip().lower()
            for (h_api, a_api), prices in odds_map.items():
                if h_key in h_api or a_key in a_api:
                    if equipos[0].lower() in mercado.lower():
                        cuota_real = prices.get(equipos[0].lower(), 1.32)
                    elif equipos[1].lower() in mercado.lower():
                        cuota_real = prices.get(equipos[1].lower(), 1.42)
                    break

        parley_seleccionado.append({
            "partido": partido,
            "mercado": mercado,
            "prob": prob,
            "cuota": float(cuota_real),
            "estado_pick": pick.get("estado_pick", "pendiente")
        })
        cuota_acumulada *= float(cuota_real)

    return {
        "status": "success",
        "cuota_total": round(cuota_acumulada, 2),
        "target_alcanzado": cuota_acumulada >= target_cuota,
        "picks": parley_seleccionado
    }
