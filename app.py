import threading
import time
from database import guardar_alerta, inicializar_db, obtener_alertas
from flask import Flask, jsonify, render_template_string
import requests

app = Flask(__name__)

# ==========================================
# 🔑 CONFIGURACIÓN DE APIS Y TELEGRAM
# ==========================================
API_KEY = "1919b9af07c4eeae00a059f0086f6473"
URL_LIVE = "https://v3.football.api-sports.io/fixtures"
URL_STATS = "https://v3.football.api-sports.io/fixtures/statistics"
HEADERS = {"x-apisports-key": API_KEY}

TELEGRAM_TOKEN = "8726477823:AAFJ5_nuDcbSxMxag2rUIjRbeuCgxqRRHh0"
TELEGRAM_CHAT_ID = "8470398609"

alertas_disparadas = set()
partidos_00_en_vivo = []


def enviar_alerta_telegram(
    home_name, away_name, league_name, minuto, equipo_cumple
):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return

    mensaje = (
        f"🚨 <b>¡ALERTA AFC OVER 0.5 GOALS!</b> 🚨\n\n"
        f"⚽ <b>Partido:</b> {home_name} vs {away_name}\n"
        f"🏆 <b>Liga:</b> {league_name}\n"
        f"⏱ <b>Minuto:</b> {minuto}' | <b>Marcador:</b> 0 - 0\n"
        f"🔥 <b>Presión ofensiva:</b> {equipo_cumple}\n\n"
        f"📈 <i>Filtros cumplidos: xG/Tiros + Marcador 0-0 en 2da mitad.</i>"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML",
    }

    try:
        requests.post(url, data=payload, timeout=5)
    except Exception as e:
        print(f"⚠️ Error enviando a Telegram: {e}")


def obtener_estadisticas_partido(fixture_id):
    try:
        response = requests.get(
            URL_STATS,
            headers=HEADERS,
            params={"fixture": fixture_id},
            timeout=8,
        )
        if response.status_code != 200:
            return {}
        data = response.json().get("response", [])
        if not data or len(data) < 2:
            return {}

        stats_local = {
            item["type"]: item["value"] for item in data[0]["statistics"]
        }
        stats_visita = {
            item["type"]: item["value"] for item in data[1]["statistics"]
        }

        def limpiar(val):
            if val is None:
                return 0.0
            if isinstance(val, str):
                val = val.replace("%", "")
            try:
                return float(val)
            except ValueError:
                return 0.0

        return {
            "remates_local": limpiar(stats_local.get("Total Shots")),
            "puerta_local": limpiar(stats_local.get("Shots on Goal")),
            "xg_local": limpiar(stats_local.get("expected_goals")),
            "ataques_p_local": limpiar(stats_local.get("Dangerous Attacks")),
            "remates_visita": limpiar(stats_visita.get("Total Shots")),
            "puerta_visita": limpiar(stats_visita.get("Shots on Goal")),
            "xg_visita": limpiar(stats_visita.get("expected_goals")),
            "ataques_p_visita": limpiar(stats_visita.get("Dangerous Attacks")),
        }
    except Exception:
        return {}


def evaluar_reglas_estrictas(datos):
    minuto = datos.get("minuto", 0)
    if not (46 <= minuto <= 78):
        return False, None
    if (datos.get("goles_local", 0) + datos.get("goles_visita", 0)) != 0:
        return False, None

    l_xg, l_remates, l_puerta, l_ataques = (
        datos.get("xg_local", 0.0),
        datos.get("remates_local", 0),
        datos.get("puerta_local", 0),
        datos.get("ataques_p_local", 0),
    )
    v_xg, v_remates, v_puerta, v_ataques = (
        datos.get("xg_visita", 0.0),
        datos.get("remates_visita", 0),
        datos.get("puerta_visita", 0),
        datos.get("ataques_p_visita", 0),
    )

    local_xg_ok = (l_xg >= 0.8) if l_xg > 0 else (l_remates >= 8)
    cumple_local = (
        local_xg_ok
        and l_remates >= 8
        and l_puerta >= 3
        and (l_ataques >= 30 or l_ataques == 0)
    )

    visita_xg_ok = (v_xg >= 0.8) if v_xg > 0 else (v_remates >= 8)
    cumple_visita = (
        visita_xg_ok
        and v_remates >= 8
        and v_puerta >= 3
        and (v_ataques >= 30 or v_ataques == 0)
    )

    if cumple_local or cumple_visita:
        equipo = (
            datos["equipo_local"] if cumple_local else datos["equipo_visita"]
        )
        return True, equipo
    return False, None


def bucle_escaneo():
    global partidos_00_en_vivo
    INTERVALO_SEGUNDOS = 600

    while True:
        try:
            response = requests.get(
                URL_LIVE, headers=HEADERS, params={"live": "all"}, timeout=10
            )
            if response.status_code == 200:
                partidos = response.json().get("response", [])
                temp_00 = []
                candidatos_validos = []

                for item in partidos:
                    fixture_id = item["fixture"]["id"]
                    minuto = item["fixture"]["status"]["elapsed"] or 0
                    goles_h = item["goals"]["home"] or 0
                    goles_a = item["goals"]["away"] or 0
                    home_name = item["teams"]["home"]["name"]
                    away_name = item["teams"]["away"]["name"]
                    league_name = item["league"]["name"]

                    # SECCIÓN 1: Captura todos los 0-0 en ventana 46'-78' sin gastar llamadas extra
                    if 46 <= minuto <= 78 and (goles_h + goles_a) == 0:
                        temp_00.append({
                            "fixture_id": fixture_id,
                            "equipo_local": home_name,
                            "equipo_visita": away_name,
                            "liga": league_name,
                            "minuto": minuto,
                        })

                        if fixture_id not in alertas_disparadas:
                            candidatos_validos.append((fixture_id, item, minuto))

                partidos_00_en_vivo = temp_00

                # SECCIÓN 2: Analiza detalladamente máximo 2 partidos por ciclo
                for fixture_id, item, minuto in candidatos_validos[:2]:
                    home_name = item["teams"]["home"]["name"]
                    away_name = item["teams"]["away"]["name"]
                    league_name = item["league"]["name"]

                    stats = obtener_estadisticas_partido(fixture_id)
                    datos_partido = {
                        "fixture_id": fixture_id,
                        "equipo_local": home_name,
                        "equipo_visita": away_name,
                        "minuto": minuto,
                        "goles_local": 0,
                        "goles_visita": 0,
                        **stats,
                    }

                    es_alerta, equipo = evaluar_reglas_estrictas(datos_partido)
                    if es_alerta:
                        guardar_alerta(
                            fixture_id,
                            home_name,
                            away_name,
                            league_name,
                            minuto,
                            equipo,
                        )
                        enviar_alerta_telegram(
                            home_name,
                            away_name,
                            league_name,
                            minuto,
                            equipo,
                        )
                        alertas_disparadas.add(fixture_id)
        except Exception as e:
            print(f"Error durante el escaneo: {e}")

        time.sleep(INTERVALO_SEGUNDOS)


# ==========================================
# 🎨 DISEÑO CON PESTAÑAS (TAB SYSTEM)
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AFC Analytics - Monitor Global 0-0</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #06090e;
            --card-bg: #0d131d;
            --card-border: rgba(255, 255, 255, 0.08);
            --accent-green: #10b981;
            --text-primary: #ffffff;
            --text-secondary: #94a3b8;
        }

        * { box-sizing: border-box; }

        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            margin: 0; padding: 0;
            line-height: 1.5;
        }

        .navbar {
            display: flex; justify-content: space-between; align-items: center;
            padding: 18px 5%;
            background: rgba(6, 9, 14, 0.85);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--card-border);
            position: sticky; top: 0; z-index: 100;
        }

        .brand { display: flex; align-items: center; gap: 12px; font-weight: 800; font-size: 20px; }
        .brand-icon {
            width: 36px; height: 36px;
            background: radial-gradient(circle, var(--accent-green) 0%, rgba(16,185,129,0.2) 100%);
            border-radius: 10px; display: flex; align-items: center; justify-content: center;
            border: 1px solid var(--accent-green);
        }

        .status-pill {
            background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3);
            color: var(--accent-green); padding: 6px 16px; border-radius: 20px;
            font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 8px;
        }

        .pulse {
            width: 8px; height: 8px; background: var(--accent-green); border-radius: 50%;
            box-shadow: 0 0 10px var(--accent-green); animation: pulse-anim 2s infinite;
        }

        @keyframes pulse-anim {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }

        .main-container { max-width: 1200px; margin: 30px auto; padding: 0 20px; }

        /* NAVEGACIÓN POR PESTAÑAS */
        .tabs-nav {
            display: flex; gap: 12px; margin-bottom: 30px;
            border-bottom: 1px solid var(--card-border); padding-bottom: 12px;
        }

        .tab-btn {
            background: rgba(255, 255, 255, 0.03); border: 1px solid var(--card-border);
            color: var(--text-secondary); padding: 10px 22px; border-radius: 12px;
            font-weight: 600; font-size: 14px; cursor: pointer; transition: all 0.2s ease;
            display: flex; align-items: center; gap: 8px;
        }

        .tab-btn.active {
            background: var(--accent-green); color: #000; border-color: var(--accent-green);
            font-weight: 700; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
        }

        .tab-badge {
            background: rgba(0,0,0,0.15); padding: 2px 8px; border-radius: 10px; font-size: 11px;
        }

        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }

        .match-card {
            background: var(--card-bg); border: 1px solid var(--card-border);
            border-radius: 16px; padding: 20px; transition: all 0.25s ease;
        }

        .match-card:hover { border-color: rgba(16, 185, 129, 0.4); transform: translateY(-3px); }

        .match-meta { display: flex; justify-content: space-between; font-size: 12px; color: var(--text-secondary); margin-bottom: 12px; }
        .league-badge { background: rgba(255, 255, 255, 0.05); padding: 3px 8px; border-radius: 6px; font-weight: 600; }
        .minute-badge { color: #f59e0b; font-weight: 700; }
        .teams-title { font-size: 17px; font-weight: 700; text-align: center; margin: 15px 0; }

        .fulfilled-box {
            background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2);
            padding: 10px 14px; border-radius: 10px; font-size: 13px;
            display: flex; justify-content: space-between; align-items: center;
        }

        .team-pill { background: var(--accent-green); color: #000; font-weight: 700; padding: 2px 8px; border-radius: 6px; font-size: 12px; }

        .empty-card {
            grid-column: 1 / -1; text-align: center; padding: 60px 20px;
            background: var(--card-bg); border: 1px dashed var(--card-border);
            border-radius: 20px; color: var(--text-secondary);
        }
    </style>
</head>
<body>

    <div class="navbar">
        <div class="brand">
            <div class="brand-icon">⚡</div>
            <span>AFC Analytics</span>
        </div>
        <div class="status-pill">
            <div class="pulse"></div>
            SCANNER EN VIVO
        </div>
    </div>

    <div class="main-container">
        <!-- BARRA DE PESTAÑAS -->
        <div class="tabs-nav">
            <button class="tab-btn active" onclick="cambiarPestana('radar')">
                📡 Radar Global 0-0 <span class="tab-badge" id="count-radar">0</span>
            </button>
            <button class="tab-btn" onclick="cambiarPestana('alertas')">
                🔥 Alertas VIP Cumplidas <span class="tab-badge" id="count-alertas">0</span>
            </button>
        </div>

        <!-- CONTENIDO PESTAÑA 1: RADAR GLOBAL 0-0 -->
        <div id="pestana-radar">
            <div id="grid-radar" class="grid">
                <div class="empty-card"><p>Cargando partidos 0-0 en ventana 46'-78'...</p></div>
            </div>
        </div>

        <!-- CONTENIDO PESTAÑA 2: ALERTAS CUMPLIDAS -->
        <div id="pestana-alertas" style="display: none;">
            <div id="grid-alertas" class="grid">
                <div class="empty-card"><p>Cargando alertas confirmadas...</p></div>
            </div>
        </div>
    </div>

    <script>
        let pestanaActual = 'radar';

        function cambiarPestana(pestana) {
            pestanaActual = pestana;
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            if(pestana === 'radar') {
                event.currentTarget.classList.add('active');
                document.getElementById('pestana-radar').style.display = 'block';
                document.getElementById('pestana-alertas').style.display = 'none';
            } else {
                event.currentTarget.classList.add('active');
                document.getElementById('pestana-radar').style.display = 'none';
                document.getElementById('pestana-alertas').style.display = 'block';
            }
        }

        function cargarDatos() {
            // 1. Cargar Todos los 0-0
            fetch('/api/partidos_00')
                .then(res => res.json())
                .then(data => {
                    const grid = document.getElementById('grid-radar');
                    document.getElementById('count-radar').innerText = data.length;
                    if (!data || data.length === 0) {
                        grid.innerHTML = '<div class="empty-card"><h3>🔎 No hay partidos 0-0 en este momento</h3><p>Monitoreando en vivo entre el min 46 y 78...</p></div>';
                        return;
                    }
                    grid.innerHTML = data.map(p => `
                        <div class="match-card">
                            <div class="match-meta">
                                <span class="league-badge">🏆 ${p.liga}</span>
                                <span class="minute-badge">⏱️ Min ${p.minuto}'</span>
                            </div>
                            <div class="teams-title">${p.equipo_local} 0 - 0 ${p.equipo_visita}</div>
                        </div>
                    `).join('');
                });

            // 2. Cargar Alertas VIP
            fetch('/api/alertas')
                .then(res => res.json())
                .then(data => {
                    const grid = document.getElementById('grid-alertas');
                    document.getElementById('count-alertas').innerText = data.length;
                    if (!data || data.length === 0) {
                        grid.innerHTML = '<div class="empty-card"><h3>🔥 Sin alertas VIP registradas hoy</h3><p>Las alertas que cumplan las 6 reglas aparecerán aquí.</p></div>';
                        return;
                    }
                    grid.innerHTML = data.map(a => `
                        <div class="match-card">
                            <div class="match-meta">
                                <span class="league-badge">🏆 ${a.liga}</span>
                                <span class="minute-badge">⏱️ Min ${a.minuto}'</span>
                            </div>
                            <div class="teams-title">${a.equipo_local} vs ${a.equipo_visita}</div>
                            <div class="fulfilled-box">
                                <span>Alta presión detectada:</span>
                                <span class="team-pill">${a.equipo_cumple}</span>
                            </div>
                        </div>
                    `).join('');
                });
        }

        window.onload = cargarDatos;
        setInterval(cargarDatos, 5000);
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/alertas")
def api_alertas():
    return jsonify(obtener_alertas())


@app.route("/api/partidos_00")
def api_partidos_00():
    return jsonify(partidos_00_en_vivo)


if __name__ == "__main__":
    inicializar_db()

    hilo_bot = threading.Thread(target=bucle_escaneo, daemon=True)
    hilo_bot.start()

    print("🚀 Servidor Web iniciado en http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
