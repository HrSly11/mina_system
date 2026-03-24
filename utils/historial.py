from utils.db import execute_insert, execute_query

def registrar_accion(usuario_id, nombre_usuario, accion, modulo="", detalle=""):
    """Registra una acción en el historial."""
    try:
        execute_insert(
            """INSERT INTO historial (usuario_id, nombre_usuario, accion, modulo, detalle)
               VALUES (%s, %s, %s, %s, %s)""",
            (usuario_id, nombre_usuario, accion, modulo, detalle)
        )
    except Exception:
        pass  # No interrumpir el flujo principal

def get_historial(search="", modulo="", fecha_inicio=None, fecha_fin=None, limit=200):
    conditions = []
    params = []

    if search:
        conditions.append("(nombre_usuario ILIKE %s OR accion ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])
    if modulo and modulo != "Todos":
        conditions.append("modulo = %s")
        params.append(modulo)
    if fecha_inicio:
        conditions.append("fecha_hora::date >= %s")
        params.append(fecha_inicio)
    if fecha_fin:
        conditions.append("fecha_hora::date <= %s")
        params.append(fecha_fin)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    query = f"""
        SELECT h.*, u.nombre_completo
        FROM historial h
        LEFT JOIN usuarios u ON h.usuario_id = u.id
        {where}
        ORDER BY fecha_hora DESC
        LIMIT {limit}
    """
    return execute_query(query, params if params else None)
