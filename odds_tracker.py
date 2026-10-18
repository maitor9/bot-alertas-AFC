import os
import requests
import sqlite3
from datetime import datetime

# Obtenemos la API Key desde las variables de entorno de Render
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "87843c0f13532b677bc7dcde129e97ae")

def init_odds_db():
    conn = sqlite3.connect('odds_tracking.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS line_movement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            partido TEXT,
            mercado TEXT,
            cuota_apertura REAL,
            cuota_actual REAL,
            variacion_pct REAL,
            fecha_actualizacion TEXT
        )
    ''')
    conn.commit()
    conn.close()

def actualizar_y_rastrear_cuotas(sport_key="soccer_epl"):
    init_odds_db()
    conn = sqlite3.connect('odds_tracking.db')
    cursor = conn.cursor()
    
    # Consultamos una liga con partidos activos reales (ej. Premier League)
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h&oddsFormat=decimal"
    
    try:
        response = requests.get(url, timeout=5.0)
        if response.status_code != 200:
            print(f"⚠️ Error al conectar con The Odds API: {response.status_code}")
            conn.close()
            return []
            
        data = response.json()
        resultados_tracking = []
        
        for evento in data:
            home_team = evento.get("home_team")
            away_team = evento.get("away_team")
            partido_str = f"{home_team} vs {away_team}"
            
            bookmakers = evento.get("bookmakers", [])
            if not bookmakers: continue
            
            # Tomamos la cuota oficial de Bet365 o la primera casa disponible
            bookmaker = next((b for b in bookmakers if b.get("key") == "bet365"), bookmakers[0])
            markets = bookmaker.get("markets", [])
            h2h_market = next((m for m in markets if m.get("key") == "h2h"), None)
            
            if not h2h_market: continue
            
            outcomes = h2h_market.get("outcomes", [])
            for outcome in outcomes:
                nombre_equipo = outcome.get("name")
                precio_actual = float(outcome.get("price"))
                mercado = f"Victoria {nombre_equipo} (1X2)"
                
                # Verificamos si ya tenemos registrada una cuota de apertura en nuestra base de datos local
                cursor.execute("SELECT cuota_apertura FROM line_movement WHERE partido = ? AND mercado = ?", (partido_str, mercado))
                row = cursor.fetchone()
                
                if row is None:
                    # Primera vez que el bot detecta este partido: fijamos estrictamente la cuota de apertura
                    cursor.execute("""
                        INSERT INTO line_movement (partido, mercado, cuota_apertura, cuota_actual, variacion_pct, fecha_actualizacion)
                        VALUES (?, ?, ?, ?, 0.0, ?)
                    """, (partido_str, mercado, precio_actual, precio_actual, datetime.now().strftime("%Y-%m-%d %H:%M")))
                    apertura = precio_actual
                    actual = precio_actual
                    variacion = 0.0
                else:
                    apertura = float(row[0])
                    actual = precio_actual
                    
                    # Cálculo matemático real de la variación porcentual respecto a la apertura guardada
                    if apertura > 0:
                        variacion = round(((actual - apertura) / apertura) * 100, 2)
                    else:
                        variacion = 0.0
                        
                    # Actualizamos la cuota actual en la base de datos
                    cursor.execute("""
                        UPDATE line_movement 
                        SET cuota_actual = ?, variacion_pct = ?, fecha_actualizacion = ?
                        WHERE partido = ? AND mercado = ?
                    """, (actual, variacion, datetime.now().strftime("%Y-%m-%d %H:%M"), partido_str, mercado))
                
                conn.commit()
                
                # Clasificación de tendencia basada en el movimiento real del mercado
                if variacion < -0.1:
                    tendencia = "🔥 Steam Money (Bajada)"
                elif variacion > 0.1:
                    tendencia = "📈 Drift (Subida)"
                else:
                    tendencia = "⚖️ Estable"
                
                resultados_tracking.append({
                    "partido": partido_str,
                    "mercado": mercado,
                    "cuota_apertura": apertura,
                    "cuota_actual": actual,
                    "variacion_pct": variacion,
                    "tendencia": tendencia
                })
                
        conn.close()
        return resultados_tracking
    except Exception as e:
        print(f"⚠️ Error en tracking de cuotas: {e}")
        conn.close()
        return []
