import pandas as pd
from pathlib import Path
import os
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.styles import PatternFill

# ======================
# CONFIGURACIÓN
# ======================
RUTA_MAESTRO = Path("data/maestro.xlsx")
RUTA_PARTICIPANTES = Path("data/participantes")
SALIDA = "clasificacion.xlsx"
HTML_SALIDA = "index.html"

P_GANADOR = 1
P_DIFERENCIA = 3
P_RESULTADO_EXACTO = 5

# ======================
# PUNTUACIÓN PARTIDOS
# ======================
def puntos_partido(real, apuesta):

    gl_r, gv_r = real["GOLES LOCAL"], real["GOLES VISITANTE"]
    gl_a, gv_a = apuesta["GOLES LOCAL"], apuesta["GOLES VISITANTE"]

    # ganador real
    ganador_real = 1 if gl_r > gv_r else -1 if gv_r > gl_r else 0
    ganador_apuesta = 1 if gl_a > gv_a else -1 if gv_a > gl_a else 0

    if ganador_real != ganador_apuesta:
        return 0

    if gl_r == gl_a and gv_r == gv_a:
        return P_RESULTADO_EXACTO

    if (gl_r - gv_r) == (gl_a - gv_a):
        return P_DIFERENCIA

    return P_GANADOR


def puntuar_partidos(maestro, jugador):
    total, g, d, e = 0, 0, 0, 0

    partidos = maestro[(maestro["ID"] >= 1) & (maestro["ID"] <= 104)]

    for _, real in partidos.iterrows():

        if int(real.get("JUGADO", 0)) != 1:
            continue

        fila = jugador[jugador["ID"] == real["ID"]]
        if fila.empty:
            continue

        apuesta = fila.iloc[0]
        puntos = puntos_partido(real, apuesta)

        total += puntos

        if puntos == 5:
            e += 1
        elif puntos == 3:
            d += 1
        elif puntos == 1:
            g += 1

    return total, g, d, e


def contar_partidos_jugados(maestro):
    partidos = maestro[(maestro["ID"] >= 1) & (maestro["ID"] <= 104)]
    return int((partidos["JUGADO"] == 1).sum())


# ======================
# MAIN
# ======================
def main():

    maestro = pd.read_excel(RUTA_MAESTRO, sheet_name="Datos")

    partidos_jugados = contar_partidos_jugados(maestro)

    ranking = []

    for archivo in RUTA_PARTICIPANTES.glob("*.xlsx"):

        if archivo.name.startswith("~$"):
            continue

        nombre = archivo.stem
        jugador = pd.read_excel(archivo, sheet_name="Datos")

        puntos, g, d, e = puntuar_partidos(maestro, jugador)

        ranking.append({
            "Participante": nombre,
            "Signo": g,
            "Diferencia": d,
            "Exactos": e,
            "Totales": puntos
        })

    # ======================
    # CLASIFICACIÓN
    # ======================
    df = pd.DataFrame(ranking).sort_values("Totales", ascending=False).reset_index(drop=True)
    df.insert(0, "Posición", df.index + 1)

    # ======================
    # MOVIMIENTO
    # ======================
    clasificacion_anterior = None

    if os.path.exists(SALIDA):
        try:
            clasificacion_anterior = pd.read_excel(SALIDA)
        except:
            pass

    if clasificacion_anterior is not None:

        posiciones_antiguas = {
            fila["Participante"]: fila["Posición"]
            for _, fila in clasificacion_anterior.iterrows()
        }

        movimientos = []

        for _, fila in df.iterrows():

            jugador = fila["Participante"]
            posicion_actual = fila["Posición"]

            if jugador not in posiciones_antiguas:
                movimientos.append("🆕")
                continue

            posicion_anterior = posiciones_antiguas[jugador]

            diff = posicion_anterior - posicion_actual

            if diff > 0:
                movimientos.append(f"↑{diff}")
            elif diff < 0:
                movimientos.append(f"↓{abs(diff)}")
            else:
                movimientos.append("=")

        df.insert(1, "Mov", movimientos)

    # ======================
    # GUARDAR EXCEL
    # ======================
    df.to_excel(SALIDA, index=False)

    # ======================
    # HTML
    # ======================
    def formato_mov(val):
        if "↑" in str(val):
            return f'<span style="color:#00ff00">{val}</span>'
        elif "↓" in str(val):
            return f'<span style="color:#ff4d4d">{val}</span>'
        return val

    if "Mov" in df.columns:
        df["Mov"] = df["Mov"].apply(formato_mov)

    html_table = df.to_html(index=False, escape=False)

    now = datetime.now().strftime("%d/%m %H:%M:%S")

    
    html = f"""
    <html>
    <head>
    <meta charset="UTF-8">

    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">

    <title>Porra Mundial</title>


    <style>
    body {{
        background: #111;
        color: white;
        font-family: Arial;
        text-align: center;
    }}

    table {{
        margin: auto;
        border-collapse: collapse;
    }}

    th, td {{
        padding: 10px;
        border-bottom: 1px solid #444;
    }}

    th {{
        background: #222;
    }}

    tr:nth-child(even) {{
        background: #1a1a1a;
    }}

    tr:nth-child(2) {{
        background: gold;
        color: black;
    }}

    tr:nth-child(3) {{
        background: silver;
        color: black;
    }}

    tr:nth-child(4) {{
        background: #cd7f32;
        color: black;
    }}

    td:last-child {{
        font-weight: bold;
        color: #00ffcc;
    }}

    </style>
    </head>

    <body>
    <h1>🏆 Clasificación Porra Mundial</h1>
    <p>Actualizado: {now}</p>
    <p>Partidos jugados: {partidos_jugados} / 104</p>

    {html_table}

    </body>
    </html>
    """
    # FORZAR CAMBIO PARA QUE GITHUB ACTUALICE
    html += f"\n<!-- update {datetime.now().timestamp()} -->"

    with open(HTML_SALIDA, "w", encoding="utf-8") as f:
        f.write(html)

    print("✅ HTML generado")

    # ======================
    # AUTO PUSH
    # ======================
    print("🚀 Subiendo a GitHub...")

    os.system("git add .")
    os.system(f'git commit -m "update {now}"')
    os.system("git push")

    print("✅ Todo actualizado")


if __name__ == "__main__":
    main()
