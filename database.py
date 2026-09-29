import sqlite3

DB_NAME = "bot_alertas.db"


def inicializar_db():
    """Crea la tabla de alertas si no existe."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fixture_id INTEGER UNIQUE,
            equipo_local TEXT,
            equipo_visita TEXT,
            liga TEXT,
            minuto INTEGER,
            equipo_cumple TEXT,
            fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def guardar_alerta(
    fixture_id, equipo_local, equipo_visita, liga, minuto, equipo_cumple
):
    """Inserta una nueva alerta en la base de datos."""
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
        return True
    except sqlite3.IntegrityError:
        # Ya existe esa alerta en la base de datos
        return False


def obtener_alertas():
    """Obtiene todas las alertas guardadas para mostrar en la web."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alertas ORDER BY id DESC")
    alertas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return alertas