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

def actualizar_y_rastrear_cuotas(sport_key="soccer_uefa_champs_league"):
    init_odds_db()
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h&oddsFormat=decimal"
    
    try:
        response = requests.get(url, timeout=5.0)
        if response.status_code != 200:
            print(f"⚠️ Error al conectar con The Odds API: {response.status_code}")
            return []
            
        data = response.json()
        conn = sqlite3.connect('odds_tracking.db')
        cursor = conn.cursor()
        
        resultados_tracking = []
        
        for evento in data:
            home_team = evento.get("home_team")
            away_team = evento.get("away_team")
            partido_str = f"{home_team} vs {away_team}"
            
            bookmakers = evento.get("bookmakers", [])
            if not bookmakers: continue
            
            # Tomamos la cuota de una casa de referencia (ej. Bet365 o la primera disponible)
            bookmaker = next((b for b in bookmakers if b.get("key") == "bet365"), bookmakers[0])
            markets = bookmaker.get("markets", [])
            h2h_market = next((m for m in markets if m.get("key") == "h2h"), None)
            
            if not h2h_market: continue
            
            outcomes = h2h_market.get("outcomes", [])
            for outcome in outcomes:
                nombre_equipo = outcome.get("name")
                cuota_actual = outcome.get("price")
                mercado = f"Victoria {nombre_equipo} (1X2)"
                
                # Consultar si ya existe cuota de apertura en base de datos
                cursor.execute("SELECT cuota_apertura FROM line_movement WHERE partido = ? AND mercado = ?", (partido_str, mercado))
                row = cursor.fetchone()
                
                if row is None:
                    # Registrar apertura
                    cursor.execute("""
                        INSERT INTO line_movement (partido, mercado, cuota_apertura, cuota_actual, variacion_pct, fecha_actualizacion)
                        VALUES (?, ?, ?, ?, 0.0, ?)
                    """, (partido_str, mercado, cuota_actual, cuota_actual, datetime.now().strftime("%Y-%m-%d %H:%M")))
                    apertura = cuota_actual
                    variacion = 0.0
                else:
                    apertura = row[0]
                    # Calcular variación porcentual de la línea
                    variacion = round(((cuota_actual - apertura) / apertura) * 100, 2)
                    cursor.execute("""
                        UPDATE line_movement 
                        SET cuota_actual = ?, variacion_pct = ?, fecha_actualizacion = ?
                        WHERE partido = ? AND mercado = ?
                    """, (cuota_actual, variacion, datetime.now().strftime("%Y-%m-%d %H:%M"), partido_str, mercado))
                
                conn.commit()
                
                resultados_tracking.append({
                    "partido": partido_str,
                    "mercado": mercado,
                    "cuota_apertura": apertura,
                    "cuota_actual": cuota_actual,
                    "variacion_pct": variacion,
                    "tendencia": "🔥 Steam Money (Caída de cuota)" if variacion < -2.0 else ("📈 Drift (Sube cuota)" if variacion > 2.0 else "⚖️ Estable")
                })
                
        conn.close()
        return resultados_tracking
    except Exception as e:
        print(f"⚠️ Error en el módulo de tracking de cuotas: {e}")
        return []
