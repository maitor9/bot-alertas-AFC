from datetime import datetime, timedelta
import requests

# Perfiles de posición propensos a tarjeta amarilla
POSICIONES_CALIENTES = ["Defensa Central", "Lateral", "Mediocampista Defensivo", "Pivote"]

def calcular_indice_friccion(home_name, away_name, fase_torneo=""):
    # Duelos de alta tensión histórica o fases calientes de Champions
    es_derbi, etiqueta = es_partido_caliente_tarjetas(home_name, away_name)
    factor_friccion = 1.3 if es_derbi else 1.0
    
    if "Champions" in fase_torneo or "Cuartos" in fase_torneo or "Semifinal" in fase_torneo:
        factor_friccion *= 1.25
        
    return factor_friccion

def es_partido_caliente_tarjetas(h, a):
    h_low, a_low = h.lower(), a.lower()
    # Mapeo rápido de duelos calientes
    if ("atletico" in h_low and "manchester" in a_low) or ("galatasaray" in h_low and "barcelona" in a_low):
        return True, "🔥 Duelo de Alto Impacto Táctico y Fricción"
    return False, "⚡ Partido Oficial"

def analizar_alineaciones_y_friccion(event_id, home_name, away_name, liga_nombre):
    # Endpoint de detalles para obtener alineaciones confirmadas 1 hora antes
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga_nombre}/summary?event={event_id}"
    try:
        response = requests.get(url, timeout=3.0)
        if response.status_code == 200:
            data = response.json()
            rosters = data.get("rosters", [])
            
            candidatos_tarjeta = []
            # Analizamos las alineaciones titulares confirmadas
            for team_roster in rosters:
                team_name = team_roster.get("team", {}).get("displayName", "")
                for player in team_roster.get("roster", []):
                    posicion = player.get("position", {}.get("name", ""))
                    stats = player.get("stats", [])
                    
                    # Buscamos jugadores con tendencia a faltas o en posiciones de fricción
                    if any(p in posicion for p in ["Defender", "Midfielder", "Back"]):
                        candidatos_tarjeta.append({
                            "jugador": player.get("athlete", {}).get("displayName", "Desconocido"),
                            "equipo": team_name,
                            "posicion": posicion,
                            "factor_riesgo": "Alto (Cortador táctico / Posición de fricción)"
                        })
            return candidatos_tarjeta
    except:
        pass
    return []
