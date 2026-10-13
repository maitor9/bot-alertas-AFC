from datetime import datetime, timedelta
import requests

def convertir_hora_colombia(date_str):
    try:
        dt_utc = datetime.strptime(date_str.replace("Z", ""), "%Y-%m-%dT%H:%M")
        dt_col = dt_utc - timedelta(hours=5)
        return dt_col.strftime("%d/%m/%Y - %H:%M")
    except Exception:
        return "📅 Próximamente"

def evaluar_nivel_friccion(home_name, away_name, liga_nombre):
    rivales_calientes = [
        ("real madrid", "barcelona"), ("inter", "milan"), ("lazio", "roma"),
        ("boca", "river"), ("atletico", "real madrid"), ("galatasaray", "barcelona"),
        ("atletico de madrid", "manchester utd"), ("arsenal", "lille"),
        ("porto", "benfica"), ("ajax", "feyenoord"), ("psg", "marseille")
    ]
    h_low = home_name.lower()
    a_low = away_name.lower()
    
    es_derbi = False
    for t1, t2 in rivales_calientes:
        if (t1 in h_low and t2 in a_low) or (t2 in h_low and t1 in a_low):
            es_derbi = True
            break
            
    if es_derbi or "Champions" in liga_nombre or "Libertadores" in liga_nombre:
        return "🔥 ALTA TENSIÓN (Derbi o Fase Crítica)", 85.0
    return "⚡ Fricción Moderada", 60.0

def analizar_alertas_tarjetas():
    print("⚡ Escaneando partidos en búsqueda de fricción y tarjetas...", flush=True)
    alertas_lista = []
    
    # Ligas clave para rastrear fricción
    ligas_objetivo = ["uefa.champions", "eng.1", "esp.1", "ita.1", "ger.1"]
    hoy_str = datetime.now().strftime("%Y%m%d")
    
    for liga in ligas_objetivo:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga}/scoreboard?dates={hoy_str}"
        try:
            response = requests.get(url, timeout=3.0)
            if response.status_code == 200:
                data = response.json()
                events = data.get("events", [])
                league_info = data.get("leagues", [{}])[0]
                liga_nombre = league_info.get("name") or league_info.get("shortName") or "Fútbol Internacional"

                for event in events:
                    competition = event.get("competitions", [{}])[0]
                    status_type = competition.get("status", {}).get("type", {}).get("name", "")
                    
                    # Filtramos partidos próximos o en cuenta regresiva
                    if status_type not in ["STATUS_SCHEDULED", "STATUS_PRE", "STATUS_IN_PROGRESS"]:
                        continue
                        
                    fecha_hora_col = convertir_hora_colombia(event.get("date", ""))
                    teams = competition.get("competitors", [])
                    if len(teams) < 2: continue

                    home = next((t for t in teams if t.get("homeAway") == "home"), teams[0])
                    away = next((t for t in teams if t.get("homeAway") == "away"), teams[1])

                    home_name = home.get("team", {}).get("displayName", "Local")
                    away_name = away.get("team", {}).get("displayName", "Visita")

                    nivel_friccion, prob_base = evaluar_nivel_friccion(home_name, away_name, liga_nombre)

                    # Candidatos tácticos simulados por posición de fricción (Pivotes, Laterales, Centrales)
                    candidatos = [
                        f"• 🛡 **{home_name} (Mediocampista / Pivote):** Alto riesgo de falta táctica en transición.",
                        f"• ⚠️ **{away_name} (Lateral Izquierdo/Derecho):** Expuesto a duelos con extremos veloces."
                    ]
                    str_candidatos = "\n".join(candidatos)

                    mensaje = (
                        f"🟨 **ALERTA DE FRICCIÓN Y AMONESTACIONES**\n"
                        f"📌 *{nivel_friccion}*\n\n"
                        f"🏟 **{home_name} vs. {away_name}**\n"
                        f"🏆 *{liga_nombre}*\n"
                        f"⏰ **Inicio (Col):** {fecha_hora_col}\n\n"
                        f"🎯 **Candidatos Sugeridos a Tarjeta:**\n"
                        f"{str_candidatos}"
                    )

                    alertas_lista.append({
                        "partido": f"{home_name} vs {away_name}",
                        "liga": liga_nombre,
                        "nivel_friccion": nivel_friccion,
                        "prob": prob_base,
                        "fecha": fecha_hora_col,
                        "mensaje": mensaje
                    })
        except Exception:
            continue
            
    return alertas_lista
