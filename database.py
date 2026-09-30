import sqlite3

DB_NAME = "alertas.db"


def inicializar_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alertas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fixture_id INTEGER,
                equipo_local TEXT,
                equipo_visita TEXT,
                liga TEXT,
                minuto INTEGER,
                equipo_cumple TEXT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        print("✅ Base de datos inicializada correctamente.", flush=True)
    except Exception as e:
        print(f"❌ Error inicializando DB: {e}", flush=True)


def guardar_alerta(
    fixture_id, equipo_local, equipo_visita, liga, minuto, equipo_cumple
):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO alertas (fixture_id, equipo_local, equipo_visita, liga, minuto, equipo_cumple)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                fixture_id,
                equipo_local,
                equipo_visita,
                liga,
                minuto,
                equipo_cumple,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Error guardando alerta en DB: {e}", flush=True)


def obtener_alertas():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fixture_id, equipo_local, equipo_visita, liga, minuto, equipo_cumple, fecha
            FROM alertas ORDER BY id DESC LIMIT 20
        """)
        filas = cursor.fetchall()
        conn.close()

        alertas = []
        for fila in filas:
            alertas.append({
                "fixture_id": fila[0],
                "equipo_local": fila[1],
                "equipo_visita": fila[2],
                "liga": fila[3],
                "minuto": fila[4],
                "equipo_cumple": fila[5],
                "fecha": fila[6],
            })
        return alertas
    except Exception as e:
        print(f"❌ Error obteniendo alertas de DB: {e}", flush=True)
        return []
