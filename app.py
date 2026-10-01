import threading
import time
from database import guardar_alerta, inicializar_db, obtener_alertas
from flask import Flask, jsonify, render_template_string
import requests

app = Flask(__name__)

# ==========================================
# 🔑 CONFIGURACIÓN DE APIS Y TELEGRAM
# ==========================================
API_KEY_FOOTBALL = "1919b9af07c4eeae00a059f0086f6473"
URL_LIVE = "https://v3.football.api-sports.io/fixtures"
URL_STATS_FOOTBALL = "https://v3.football.api-sports.io/fixtures/statistics"
HEADERS_FOOTBALL = {"x-apisports-key": API_KEY_FOOTBALL}

TELEGRAM_TOKEN = "8726477823:AAFJ5_nuDcbSxMxag2rUIjRbeuCgxqRRHh0"
TELEGRAM_CHAT_ID = "8470398609"

alertas_disparadas = set()
partidos_00_en_vivo = []
ultimas_stats_evaluadas = []


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
      f"📈 <i>Filtros cumplidos: Remates + Tiros a puerta en 2da mitad.</i>"
  )

  url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
  payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}

  try:
    requests.post(url, data=payload, timeout=5)
    print(
        f"📱 Alerta enviada a Telegram: {home_name} vs {away_name}", flush=True
    )
  except Exception as e:
    print(f"⚠️ Error enviando a Telegram: {e}", flush=True)


def obtener_estadisticas_partido(fixture_id):
  try:
    response = requests.get(
        URL_STATS_FOOTBALL,
        headers=HEADERS_FOOTBALL,
        params={"fixture": fixture_id},
        timeout=8,
    )
    if response.status_code != 200:
      return {}
    data = response.json().get("response", [])
    if not data or len(data) < 2:
      return {}

    stats_local = {item["type"]: item["value"] for item in data[0]["statistics"]}
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
  except Exception as e:
    print(f"⚠️ Error obteniendo stats: {e}", flush=True)
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

  local_xg_ok = (l_xg >= 0.8) if l_xg > 0 else True
  cumple_local = (
      local_xg_ok
      and l_remates >= 8
      and l_puerta >= 3
      and (l_ataques >= 30 or l_ataques == 0)
  )

  visita_xg_ok = (v_xg >= 0.8) if v_xg > 0 else True
  cumple_visita = (
      visita_xg_ok
      and v_remates >= 8
      and v_puerta >= 3
      and (v_ataques >= 30 or v_ataques == 0)
  )

  if cumple_local or cumple_visita:
    equipo = datos["equipo_local"] if cumple_local else datos["equipo_visita"]
    return True, equipo
  return False, None


def bucle_escaneo():
  global partidos_00_en_vivo, ultimas_stats_evaluadas
  INTERVALO_SEGUNDOS = 300

  print("🚀 Bucle de escaneo IA iniciado (cada 5 min)...", flush=True)

  while True:
    try:
      print("🔄 Iniciando ciclo de escaneo en API...", flush=True)
      response = requests.get(
          URL_LIVE, headers=HEADERS_FOOTBALL, params={"live": "all"}, timeout=10
      )
      if response.status_code == 200:
        partidos = response.json().get("response", [])
        temp_00 = []
        candidatos_validos = []
        stats_recientes = []

        for item in partidos:
          fixture_id = item["fixture"]["id"]
          minuto = item["fixture"]["status"]["elapsed"] or 0
          goles_h = item["goals"]["home"] or 0
          goles_a = item["goals"]["away"] or 0
          home_name = item["teams"]["home"]["name"] or "Local"
          away_name = item["teams"]["away"]["name"] or "Visitante"
          league_name = item["league"]["name"] or "Liga"

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
        print(
            f"🔎 [DIAGNÓSTICO] Partidos 0-0 detectados en ventana 46'-78':"
            f" {len(temp_00)}",
            flush=True,
        )

        for fixture_id, item, minuto in candidatos_validos[:3]:
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

          stats_recientes.append({
              "partido": f"{home_name} vs {away_name}",
              "liga": league_name,
              "minuto": minuto,
              "es_alerta": es_alerta,
              "stats": stats,
          })

          print(
              f"📊 Evaluando {home_name} vs {away_name} (Min {minuto}') -> ¿Es"
              f" Alerta?: {es_alerta}",
              flush=True,
          )

          if es_alerta:
            try:
              guardar_alerta(
                  fixture_id,
                  home_name,
                  away_name,
                  league_name,
                  minuto,
                  equipo,
              )
            except Exception as e_db:
              print(f"⚠️ Error guardando en DB: {e_db}", flush=True)

            enviar_alerta_telegram(
                home_name, away_name, league_name, minuto, equipo
            )
            alertas_disparadas.add(fixture_id)

        ultimas_stats_evaluadas = stats_recientes
      else:
        print(
            f"⚠️ Error en respuesta de API: Status {response.status_code}",
            flush=True,
        )
    except Exception as e:
      print(f"Error durante el escaneo: {e}", flush=True)

    print(
        f"💤 Esperando {INTERVALO_SEGUNDOS} segundos para el próximo ciclo...",
        flush=True,
    )
    time.sleep(INTERVALO_SEGUNDOS)


# ==========================================
# 🎨 DISEÑO CYBERPUNK / SOLO NÚCLEO NEURAL
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AFC Analytics - Neural Engine</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Orbitron:wght@600;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #030508;
            --card-bg: rgba(10, 14, 23, 0.85);
            --card-border: rgba(245, 158, 11, 0.18);
            --accent-gold: #f59e0b;
            --accent-gold-bright: #fbbf24;
            --accent-gold-glow: rgba(245, 158, 11, 0.4);
            --accent-cyan: #06b6d4;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
        }

        * { box-sizing: border-box; }

        body {
            font-family: 'Space Grotesk', sans-serif;
            background-color: var(--bg-color);
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(245, 158, 11, 0.07) 0%, transparent 35%),
                radial-gradient(circle at 90% 80%, rgba(6, 182, 212, 0.05) 0%, transparent 40%),
                linear-gradient(rgba(245, 158, 11, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(245, 158, 11, 0.03) 1px, transparent 1px);
            background-size: 100% 100%, 100% 100%, 40px 40px, 40px 40px;
            color: var(--text-primary);
            margin: 0; padding: 0;
            min-height: 100vh;
        }

        .navbar {
            display: flex; justify-content: space-between; align-items: center;
            padding: 20px 6%;
            background: rgba(3, 5, 8, 0.9);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--card-border);
            position: sticky; top: 0; z-index: 100;
        }

        .brand { 
            display: flex; align-items: center; gap: 14px; 
            font-family: 'Orbitron', sans-serif; font-weight: 900; font-size: 22px; 
            letter-spacing: 1px; color: #fff;
        }
        .brand-icon {
            width: 42px; height: 42px;
            background: radial-gradient(circle, var(--accent-gold) 0%, rgba(245,158,11,0.15) 100%);
            border-radius: 12px; display: flex; align-items: center; justify-content: center;
            border: 1px solid var(--accent-gold);
            box-shadow: 0 0 20px var(--accent-gold-glow);
            font-size: 20px;
        }

        .status-pill {
            background: rgba(245, 158, 11, 0.08); border: 1px solid var(--accent-gold);
            color: var(--accent-gold-bright); padding: 7px 18px; border-radius: 30px;
            font-family: 'Orbitron', sans-serif; font-size: 11px; font-weight: 700;
            display: flex; align-items: center; gap: 10px; letter-spacing: 1px;
            box-shadow: 0 0 15px var(--accent-gold-glow);
        }

        .pulse {
            width: 8px; height: 8px; background: var(--accent-gold-bright); border-radius: 50%;
            box-shadow: 0 0 12px var(--accent-gold-bright); animation: pulse-anim 1.8s infinite;
        }

        @keyframes pulse-anim {
            0% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.8); }
            70% { transform: scale(1.1); box-shadow: 0 0 0 10px rgba(245, 158, 11, 0); }
            100% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }
        }

        .hero-section {
            max-width: 1240px; margin: 40px auto; padding: 0 24px;
            display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 40px; align-items: center;
        }

        .badge-tag {
            color: var(--accent-gold-bright); font-family: 'Orbitron', sans-serif;
            font-size: 11px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase;
            margin-bottom: 14px; display: inline-block; background: rgba(245, 158, 11, 0.1);
            padding: 6px 14px; border-radius: 6px; border: 1px solid rgba(245, 158, 11, 0.3);
        }

        .hero-title { 
            font-family: 'Orbitron', sans-serif; font-size: 38px; font-weight: 900; 
            line-height: 1.2; margin: 0 0 18px 0; letter-spacing: -0.5px; 
        }
        .highlight-gold { 
            color: var(--accent-gold-bright); 
            text-shadow: 0 0 25px var(--accent-gold-glow); 
        }
        .hero-desc { color: var(--text-secondary); font-size: 16px; margin-bottom: 32px; max-width: 540px; line-height: 1.6; }

        .features-grid { display: flex; gap: 16px; margin-bottom: 30px; flex-wrap: wrap; }
        .feature-item {
            display: flex; align-items: center; gap: 12px;
            background: rgba(10, 14, 23, 0.6); border: 1px solid var(--card-border);
            padding: 12px 18px; border-radius: 14px; backdrop-filter: blur(10px);
        }
        .feature-icon { color: var(--accent-gold); font-size: 20px; }
        .feature-title { font-size: 13px; font-weight: 700; }
        .feature-sub { font-size: 11px; color: var(--text-secondary); }

        /* MÓDULO EXCLUSIVO NÚCLEO NEURAL */
        .neural-card {
            background: var(--card-bg); border: 1px solid var(--card-border);
            border-radius: 28px; padding: 35px 24px; text-align: center; position: relative;
            box-shadow: 0 25px 50px rgba(0,0,0,0.7), inset 0 0 40px rgba(245, 158, 11, 0.04);
            backdrop-filter: blur(16px); overflow: hidden;
        }

        .laser-line {
            position: absolute; top: 0; left: 0; right: 0; height: 2px;
            background: linear-gradient(90deg, transparent, var(--accent-gold-bright), var(--accent-cyan), transparent);
            box-shadow: 0 0 15px var(--accent-gold-bright);
            animation: laser-scan 4s ease-in-out infinite alternate;
            z-index: 5;
        }

        @keyframes laser-scan {
            0% { top: 0%; opacity: 0.3; }
            50% { opacity: 1; }
            100% { top: 98%; opacity: 0.3; }
        }

        .scout-display {
            display: flex; justify-content: center; align-items: center;
            margin: 0 auto 20px auto; height: 180px; position: relative;
        }

        /* NÚCLEO NEURAL CENTRADO Y LIMPIO */
        .neural-core {
            width: 160px; height: 160px; border-radius: 50%; position: relative;
            display: flex; align-items: center; justify-content: center;
            border: 1px dashed rgba(245, 158, 11, 0.4);
            animation: spin-core 12s linear infinite;
        }

        @keyframes spin-core {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .core-inner-ring {
            width: 110px; height: 110px; border-radius: 50%;
            border: 2px solid var(--accent-cyan);
            border-top-color: transparent; border-bottom-color: transparent;
            position: absolute; animation: spin-inner 4s linear infinite reverse;
            box-shadow: 0 0 15px rgba(6, 182, 212, 0.3);
        }

        @keyframes spin-inner {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .core-center-node {
            width: 55px; height: 55px; border-radius: 50%;
            background: radial-gradient(circle, var(--accent-gold-bright) 0%, rgba(245, 158, 11, 0.2) 80%);
            box-shadow: 0 0 25px var(--accent-gold-bright);
            display: flex; align-items: center; justify-content: center;
            font-size: 22px; font-weight: 900; color: #000;
            animation: core-pulse 1.5s ease-in-out infinite alternate;
        }

        @keyframes core-pulse {
            0% { transform: scale(0.85); box-shadow: 0 0 15px var(--accent-gold); }
            100% { transform: scale(1.1); box-shadow: 0 0 35px var(--accent-gold-bright); }
        }

        .stats-counter { 
            font-family: 'Orbitron', sans-serif; font-size: 52px; font-weight: 900; 
            color: var(--accent-gold-bright); text-shadow: 0 0 20px var(--accent-gold-glow);
            margin-bottom: 2px; 
        }
        .stats-label { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 2px; font-weight: 700; }

        .main-container { max-width: 1240px; margin: 30px auto; padding: 0 24px; }

        .tabs-nav {
            display: flex; gap: 14px; margin-bottom: 30px;
            border-bottom: 1px solid var(--card-border); padding-bottom: 16px;
        }

        .tab-btn {
            background: rgba(10, 14, 23, 0.6); border: 1px solid var(--card-border);
            color: var(--text-secondary); padding: 14px 28px; border-radius: 16px;
            font-family: 'Orbitron', sans-serif; font-weight: 700; font-size: 13px; 
            cursor: pointer; transition: all 0.3s ease; letter-spacing: 0.5px;
            display: flex; align-items: center; gap: 12px;
        }

        .tab-btn.active {
            background: linear-gradient(135deg, var(--accent-gold) 0%, #b45309 100%); 
            color: #000; border-color: var(--accent-gold-bright);
            box-shadow: 0 6px 25px rgba(245, 158, 11, 0.4);
        }

        .tab-badge { background: rgba(0,0,0,0.3); padding: 3px 10px; border-radius: 12px; font-size: 11px; }

        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 24px; }

        .match-card {
            background: var(--card-bg); border: 1px solid var(--card-border);
            border-radius: 20px; padding: 24px; transition: all 0.3s ease;
            backdrop-filter: blur(12px); position: relative; overflow: hidden;
        }

        .match-card::before {
            content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
            background: linear-gradient(90deg, transparent, var(--accent-gold-bright), transparent);
            opacity: 0.7;
        }

        .match-card:hover {
            border-color: var(--accent-gold-bright); transform: translateY(-5px);
            box-shadow: 0 15px 35px rgba(0,0,0,0.6), 0 0 20px rgba(245, 158, 11, 0.15);
        }

        .match-meta { display: flex; justify-content: space-between; font-size: 12px; color: var(--text-secondary); margin-bottom: 14px; }
        .league-badge { background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.2); padding: 5px 12px; border-radius: 8px; font-weight: 600; color: var(--accent-gold-bright); }
        .minute-badge { color: var(--accent-cyan); font-weight: 800; background: rgba(6, 182, 212, 0.1); padding: 4px 10px; border-radius: 8px; font-family: 'Orbitron', sans-serif; }
        .teams-title { font-size: 19px; font-weight: 700; text-align: center; margin: 18px 0; line-height: 1.3; }

        .fulfilled-box {
            background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3);
            padding: 12px 16px; border-radius: 14px; font-size: 13px;
            display: flex; justify-content: space-between; align-items: center;
        }

        .team-pill { background: var(--accent-gold-bright); color: #000; font-weight: 800; padding: 4px 12px; border-radius: 8px; font-size: 12px; font-family: 'Orbitron', sans-serif; }

        .empty-card {
            grid-column: 1 / -1; text-align: center; padding: 70px 20px;
            background: var(--card-bg); border: 1px dashed var(--card-border);
            border-radius: 24px; color: var(--text-secondary);
        }

        @media (max-width: 900px) { .hero-section { grid-template-columns: 1fr; } }
    </style>
</head>
<body>

    <div class="navbar">
        <div class="brand">
            <div class="brand-icon">🧠</div>
            <span>AFC ANALYTICS AI</span>
        </div>
        <div class="status-pill">
            <div class="pulse"></div>
            SYSTEM ONLINE
        </div>
    </div>

    <div class="hero-section">
        <div>
            <div class="badge-tag">Motor Algorítmico de IA</div>
            <h1 class="hero-title">Rastreo de Partidos 0-0 con <span class="highlight-gold">Presión Inminente</span></h1>
            <p class="hero-desc">Análisis predictivo de patrones de ataque en vivo (ventana min 46'-78') evaluando métricas avanzadas de xG, disparos directos y volumen ofensivo.</p>

            <div class="features-grid">
                <div class="feature-item">
                    <span class="feature-icon">🤖</span>
                    <div>
                        <div class="feature-title">Algoritmo</div>
                        <div class="feature-sub">Filtro Adaptativo</div>
                    </div>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">⏱</span>
                    <div>
                        <div class="feature-title">Ventana</div>
                        <div class="feature-sub">46' - 78'</div>
                    </div>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">🎯</span>
                    <div>
                        <div class="feature-title">Métricas</div>
                        <div class="feature-sub">xG & Shot Volume</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="neural-card">
            <div class="laser-line"></div>
            <div class="scout-display">
                <!-- Núcleo Neural Exclusivo Centrado -->
                <div class="neural-core">
                    <div class="core-inner-ring"></div>
                    <div class="core-center-node">⚡</div>
                </div>
            </div>
            <div class="stats-counter" id="alertas-counter">0</div>
            <div class="stats-label">alertas confirmadas hoy</div>
        </div>
    </div>

    <div class="main-container">
        <div class="tabs-nav">
            <button class="tab-btn active" onclick="cambiarPestana(event, 'radar')">
                📡 Radar Global 0-0 <span class="tab-badge" id="count-radar">0</span>
            </button>
            <button class="tab-btn" onclick="cambiarPestana(event, 'alertas')">
                ⚡ Alertas VIP AI <span class="tab-badge" id="count-alertas">0</span>
            </button>
        </div>

        <div id="pestana-radar">
            <div id="grid-radar" class="grid">
                <div class="empty-card">
                    <h3>🔎 Buscando partidos 0-0 en ventana 46'-78'...</h3>
                    <p>Escaneando continuamente la liga mundial...</p>
                </div>
            </div>
        </div>

        <div id="pestana-alertas" style="display: none;">
            <div id="grid-alertas" class="grid">
                <div class="empty-card">
                    <h3>⚡ Sin alertas VIP confirmadas hoy</h3>
                    <p>Las oportunidades que cumplan el 100% de los filtros de presión aparecerán aquí y en Telegram.</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        function cambiarPestana(evt, pestana) {
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            if (evt && evt.currentTarget) {
                evt.currentTarget.classList.add('active');
            }
            if (pestana === 'radar') {
                document.getElementById('pestana-radar').style.display = 'block';
                document.getElementById('pestana-alertas').style.display = 'none';
            } else {
                document.getElementById('pestana-radar').style.display = 'none';
                document.getElementById('pestana-alertas').style.display = 'block';
            }
        }

        function cargarDatos() {
            fetch('/api/partidos_00')
                .then(res => res.json())
                .then(data => {
                    const grid = document.getElementById('grid-radar');
                    document.getElementById('count-radar').innerText = data ? data.length : 0;
                    if (!data || data.length === 0) {
                        grid.innerHTML = '<div class="empty-card"><h3>🔎 No hay partidos 0-0 en ventana 46\'-78\' actualmente</h3><p>Escaneando continuamente la liga mundial...</p></div>';
                    } else {
                        grid.innerHTML = data.map(p => `
                            <div class="match-card">
                                <div class="match-meta">
                                    <span class="league-badge">🏆 ${p.liga || 'General'}</span>
                                    <span class="minute-badge">⏱️ Min ${p.minuto}'</span>
                                </div>
                                <div class="teams-title">${p.equipo_local} 0 - 0 ${p.equipo_visita}</div>
                            </div>
                        `).join('');
                    }
                })
                .catch(err => console.log('Error en partidos_00:', err));

            fetch('/api/alertas')
                .then(res => res.json())
                .then(data => {
                    const grid = document.getElementById('grid-alertas');
                    const counter = document.getElementById('alertas-counter');
                    const total = data ? data.length : 0;
                    document.getElementById('count-alertas').innerText = total;
                    counter.innerText = total;

                    if (!data || data.length === 0) {
                        grid.innerHTML = '<div class="empty-card"><h3>⚡ Sin alertas VIP confirmadas hoy</h3><p>Las oportunidades que cumplan el 100% de los filtros de presión aparecerán aquí y en Telegram.</p></div>';
                    } else {
                        grid.innerHTML = data.map(a => `
                            <div class="match-card">
                                <div class="match-meta">
                                    <span class="league-badge">🏆 ${a.liga || 'General'}</span>
                                    <span class="minute-badge">⏱️ Min ${a.minuto}'</span>
                                </div>
                                <div class="teams-title">${a.equipo_local} vs ${a.equipo_visita}</div>
                                <div class="fulfilled-box">
                                    <span>Presión IA Detectada:</span>
                                    <span class="team-pill">${a.equipo_cumple || 'Confirmado'}</span>
                                </div>
                            </div>
                        `).join('');
                    }
                })
                .catch(err => console.log('Error en alertas:', err));
        }

        window.onload = cargarDatos;
        setInterval(cargarDatos, 3000);
    </script>
</body>
</html>
"""


@app.route("/")
def index():
  return render_template_string(HTML_TEMPLATE)


@app.route("/api/alertas")
def api_alertas():
  try:
    alertas = obtener_alertas()
    return jsonify(alertas if alertas else [])
  except Exception as e:
    print(f"Error en API alertas: {e}", flush=True)
    return jsonify([])


@app.route("/api/partidos_00")
def api_partidos_00():
  return jsonify(partidos_00_en_vivo)


@app.route("/ver-stats")
def ver_stats():
  return jsonify(ultimas_stats_evaluadas)


@app.route("/probar-alerta")
def probar_alerta():
  try:
    home = "Real Madrid (Prueba)"
    away = "Barcelona (Prueba)"
    liga = "Liga Santander"
    minuto = 65
    equipo = "Real Madrid (Prueba)"
    fixture_id = 999999

    enviar_alerta_telegram(home, away, liga, minuto, equipo)

    try:
      guardar_alerta(fixture_id, home, away, liga, minuto, equipo)
    except Exception as db_err:
      print(f"⚠️ Nota de DB en prueba: {db_err}", flush=True)

    return "<h1>✅ Alerta de prueba ejecutada exitosamente. Revisa tu Telegram y el Dashboard.</h1>"
  except Exception as e:
    print(f"❌ Error en prueba: {e}", flush=True)
    return f"<h1>⚠ Ocurrió un error en la prueba: {e}</h1>"


inicializar_db()
hilo_bot = threading.Thread(target=bucle_escaneo, daemon=True)
hilo_bot.start()

if __name__ == "__main__":
  print("🚀 Servidor Web iniciado en http://127.0.0.1:5000", flush=True)
  app.run(host="0.0.0.0", port=5000, debug=False)
