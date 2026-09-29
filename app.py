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

                    if 46 <= minuto <= 78 and (goles_h + goles_a) == 0:
                        temp_00.append({
                            "fixture_id": fixture_id,
                            "equipo_local": home_name,
                            "equipo_visita": away_name,
                            "liga": league_name,
                            "minuto": minuto,
                        })

                        if fixture_id not in alertas_disparadas:
                            candidatos_validos.append((
                                fixture_id,
                                item,
                                minuto,
                            ))

                partidos_00_en_vivo = temp_00
                print(
                    f"🔎 [DIAGNÓSTICO] Partidos 0-0 detectados en ventana 46'-78': {len(temp_00)}"
                )

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
                    print(
                        f"📊 Evaluando {home_name} vs {away_name} (Min {minuto}') -> ¿Es Alerta?: {es_alerta}"
                    )
                    print(
                        f"   Local: xG={stats.get('xg_local')}, Remates={stats.get('remates_local')}, Tir.Puerta={stats.get('puerta_local')}, AtaquesP={stats.get('ataques_p_local')}"
                    )
                    print(
                        f"   Visita: xG={stats.get('xg_visita')}, Remates={stats.get('remates_visita')}, Tir.Puerta={stats.get('puerta_visita')}, AtaquesP={stats.get('ataques_p_visita')}"
                    )

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
# 🎨 DISEÑO PRO CON RADAR DINÁMICO & NEÓN
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AFC Analytics - Herramienta de Análisis en Vivo</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #05080e;
            --card-bg: rgba(13, 19, 29, 0.85);
            --card-border: rgba(255, 255, 255, 0.08);
            --accent-green: #10b981;
            --accent-green-glow: rgba(16, 185, 129, 0.35);
            --text-primary: #ffffff;
            --text-secondary: #94a3b8;
        }

        * { box-sizing: border-box; }

        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: var(--bg-color);
            background-image: 
                radial-gradient(circle at 15% 15%, rgba(16, 185, 129, 0.08) 0%, transparent 40%),
                radial-gradient(circle at 85% 85%, rgba(56, 189, 248, 0.05) 0%, transparent 40%),
                linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
            background-size: 100% 100%, 100% 100%, 30px 30px, 30px 30px;
            color: var(--text-primary);
            margin: 0; padding: 0;
            min-height: 100vh;
        }

        .navbar {
            display: flex; justify-content: space-between; align-items: center;
            padding: 18px 5%;
            background: rgba(5, 8, 14, 0.85);
            backdrop-filter: blur(16px);
            border-bottom: 1px solid var(--card-border);
            position: sticky; top: 0; z-index: 100;
        }

        .brand { display: flex; align-items: center; gap: 12px; font-weight: 800; font-size: 20px; }
        .brand-icon {
            width: 38px; height: 38px;
            background: radial-gradient(circle, var(--accent-green) 0%, rgba(16,185,129,0.2) 100%);
            border-radius: 12px; display: flex; align-items: center; justify-content: center;
            border: 1px solid var(--accent-green);
            box-shadow: 0 0 15px var(--accent-green-glow);
        }

        .status-pill {
            background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3);
            color: var(--accent-green); padding: 6px 16px; border-radius: 20px;
            font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 8px;
            box-shadow: 0 0 12px var(--accent-green-glow);
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

        .hero-section {
            max-width: 1200px; margin: 40px auto; padding: 0 20px;
            display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 40px; align-items: center;
        }

        .badge-tag {
            color: var(--accent-green); font-size: 12px; font-weight: 700;
            letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 12px;
            display: inline-block; background: rgba(16, 185, 129, 0.08); padding: 4px 12px;
            border-radius: 20px; border: 1px solid rgba(16, 185, 129, 0.2);
        }

        .hero-title { font-size: 42px; font-weight: 800; line-height: 1.15; margin: 0 0 16px 0; letter-spacing: -1px; }
        .highlight-green { color: var(--accent-green); text-shadow: 0 0 20px var(--accent-green-glow); }
        .hero-desc { color: var(--text-secondary); font-size: 16px; margin-bottom: 30px; max-width: 520px; }

        .features-grid { display: flex; gap: 15px; margin-bottom: 30px; flex-wrap: wrap; }
        .feature-item {
            display: flex; align-items: center; gap: 12px;
            background: rgba(255, 255, 255, 0.02); border: 1px solid var(--card-border);
            padding: 10px 16px; border-radius: 12px; backdrop-filter: blur(8px);
        }
        .feature-icon { color: var(--accent-green); font-size: 18px; }
        .feature-title { font-size: 12px; font-weight: 700; }
        .feature-sub { font-size: 11px; color: var(--text-secondary); }

        /* RADAR CYBERPUNK DE ALTO IMPACTO */
        .radar-card {
            background: var(--card-bg); border: 1px solid var(--card-border);
            border-radius: 24px; padding: 35px; text-align: center; position: relative;
            box-shadow: 0 20px 40px rgba(0,0,0,0.5), inset 0 0 30px rgba(16, 185, 129, 0.03);
            backdrop-filter: blur(12px);
        }

        .radar-box {
            width: 200px; height: 200px; margin: 0 auto 20px auto; border-radius: 50%;
            border: 1px solid rgba(16, 185, 129, 0.35); position: relative;
            display: flex; align-items: center; justify-content: center;
            background: radial-gradient(circle, rgba(16,185,129,0.08) 0%, transparent 75%);
            box-shadow: 0 0 25px rgba(16, 185, 129, 0.15);
            overflow: hidden;
        }

        /* Ejes en cruz del radar */
        .radar-box::before {
            content: ''; position: absolute; width: 100%; height: 1px;
            background: rgba(16, 185, 129, 0.2);
        }
        .radar-box::after {
            content: ''; position: absolute; height: 100%; width: 1px;
            background: rgba(16, 185, 129, 0.2);
        }

        .radar-circle-inner {
            position: absolute; width: 120px; height: 120px; border-radius: 50%;
            border: 1px solid rgba(16, 185, 129, 0.25);
        }

        .radar-circle-center {
            position: absolute; width: 50px; height: 50px; border-radius: 50%;
            border: 1px solid rgba(16, 185, 129, 0.25);
        }

        .radar-sweep {
            position: absolute; width: 100px; height: 100px; top: 0; right: 0;
            background: conic-gradient(from 0deg at 0% 100%, rgba(16, 185, 129, 0.45) 0deg, transparent 90deg);
            border-radius: 100% 0 0 0; transform-origin: 0% 100%;
            animation: sweep 3.5s linear infinite;
        }

        @keyframes sweep {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        /* Puntos de blip en el radar */
        .blip {
            position: absolute; width: 6px; height: 6px; background: #38bdf8;
            border-radius: 50%; box-shadow: 0 0 8px #38bdf8; animation: blip-flash 2s infinite alternate;
        }
        .blip1 { top: 35%; left: 65%; animation-delay: 0.5s; }
        .blip2 { top: 70%; left: 30%; animation-delay: 1.2s; }

        @keyframes blip-flash {
            0% { opacity: 0.2; transform: scale(0.8); }
            100% { opacity: 1; transform: scale(1.3); }
        }

        .stats-counter { font-size: 48px; font-weight: 800; letter-spacing: -1px; margin-bottom: 2px; }
        .stats-label { font-size: 12px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }

        /* PESTAÑAS Y LISTA */
        .main-container { max-width: 1200px; margin: 30px auto; padding: 0 20px; }

        .tabs-nav {
            display: flex; gap: 12px; margin-bottom: 30px;
            border-bottom: 1px solid var(--card-border); padding-bottom: 15px;
        }

        .tab-btn {
            background: rgba(255, 255, 255, 0.03); border: 1px solid var(--card-border);
            color: var(--text-secondary); padding: 12px 24px; border-radius: 14px;
            font-weight: 600; font-size: 14px; cursor: pointer; transition: all 0.25s ease;
            display: flex; align-items: center; gap: 10px;
        }

        .tab-btn.active {
            background: var(--accent-green); color: #000; border-color: var(--accent-green);
            font-weight: 700; box-shadow: 0 4px 20px rgba(16, 185, 129, 0.4);
        }

        .tab-badge { background: rgba(0,0,0,0.2); padding: 2px 8px; border-radius: 10px; font-size: 11px; }

        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 22px; }

        .match-card {
            background: var(--card-bg); border: 1px solid var(--card-border);
            border-radius: 18px; padding: 22px; transition: all 0.3s ease;
            backdrop-filter: blur(10px); position: relative; overflow: hidden;
        }

        .match-card::before {
            content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
            background: linear-gradient(90deg, transparent, var(--accent-green), transparent);
            opacity: 0.6;
        }

        .match-card:hover {
            border-color: rgba(16, 185, 129, 0.4); transform: translateY(-4px);
            box-shadow: 0 12px 30px rgba(0,0,0,0.5), 0 0 15px rgba(16, 185, 129, 0.1);
        }

        .match-meta { display: flex; justify-content: space-between; font-size: 12px; color: var(--text-secondary); margin-bottom: 12px; }
        .league-badge { background: rgba(255, 255, 255, 0.05); padding: 4px 10px; border-radius: 6px; font-weight: 600; }
        .minute-badge { color: #f59e0b; font-weight: 800; background: rgba(245, 158, 11, 0.1); padding: 3px 8px; border-radius: 6px; }
        .teams-title { font-size: 18px; font-weight: 700; text-align: center; margin: 15px 0; line-height: 1.3; }

        .fulfilled-box {
            background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25);
            padding: 10px 14px; border-radius: 12px; font-size: 13px;
            display: flex; justify-content: space-between; align-items: center;
        }

        .team-pill { background: var(--accent-green); color: #000; font-weight: 700; padding: 3px 10px; border-radius: 8px; font-size: 12px; }

        .empty-card {
            grid-column: 1 / -1; text-align: center; padding: 65px 20px;
            background: var(--card-bg); border: 1px dashed var(--card-border);
            border-radius: 20px; color: var(--text-secondary);
        }

        @media (max-width: 900px) { .hero-section { grid-template-columns: 1fr; } }
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

    <div class="hero-section">
        <div>
            <div class="badge-tag">Análisis Algorítmico en Vivo</div>
            <h1 class="hero-title">Partidos 0-0 con alta presión para <span class="highlight-green">Gol Inminente</span></h1>
            <p class="hero-desc">Monitoreo continuo de partidos globales entre el minuto 46' y 78' para detectar patrones estricto de presión ofensiva (xG, remates y ataques peligrosos).</p>

            <div class="features-grid">
                <div class="feature-item">
                    <span class="feature-icon">📡</span>
                    <div>
                        <div class="feature-title">Análisis</div>
                        <div class="feature-sub">Tiempo real</div>
                    </div>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">⏱️</span>
                    <div>
                        <div class="feature-title">Ventana</div>
                        <div class="feature-sub">46' - 78'</div>
                    </div>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">📊</span>
                    <div>
                        <div class="feature-title">Datos</div>
                        <div class="feature-sub">xG, Remates, Ataques</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="radar-card">
            <div class="radar-box">
                <div class="radar-circle-inner"></div>
                <div class="radar-circle-center"></div>
                <div class="radar-sweep"></div>
                <div class="blip blip1"></div>
                <div class="blip blip2"></div>
            </div>
            <div class="stats-counter" id="alertas-counter">0</div>
            <div class="stats-label">alertas registradas hoy</div>
        </div>
    </div>

    <div class="main-container">
        <div class="tabs-nav">
            <button class="tab-btn active" onclick="cambiarPestana('radar')">
                📡 Radar Global 0-0 <span class="tab-badge" id="count-radar">0</span>
            </button>
            <button class="tab-btn" onclick="cambiarPestana('alertas')">
                🔥 Alertas VIP Cumplidas <span class="tab-badge" id="count-alertas">0</span>
            </button>
        </div>

        <div id="pestana-radar">
            <div id="grid-radar" class="grid">
                <div class="empty-card"><p>Cargando escáner global en vivo...</p></div>
            </div>
        </div>

        <div id="pestana-alertas" style="display: none;">
            <div id="grid-alertas" class="grid">
                <div class="empty-card"><p>Cargando alertas VIP confirmadas...</p></div>
            </div>
        </div>
    </div>

    <script>
        function cambiarPestana(pestana) {
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
            fetch('/api/partidos_00')
                .then(res => res.json())
                .then(data => {
                    const grid = document.getElementById('grid-radar');
                    document.getElementById('count-radar').innerText = data.length;
                    if (!data || data.length === 0) {
                        grid.innerHTML = '<div class="empty-card"><h3>🔎 No hay partidos 0-0 en ventana 46\'-78\' actualmente</h3><p>Escaneando continuamente la liga mundial...</p></div>';
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

            fetch('/api/alertas')
                .then(res => res.json())
                .then(data => {
                    const grid = document.getElementById('grid-alertas');
                    const counter = document.getElementById('alertas-counter');
                    document.getElementById('count-alertas').innerText = data.length;
                    counter.innerText = data.length;

                    if (!data || data.length === 0) {
                        grid.innerHTML = '<div class="empty-card"><h3>🔥 Sin alertas VIP confirmadas hoy</h3><p>Las alertas que cumplan el 100% de las 6 reglas aparecerán aquí y en Telegram.</p></div>';
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
