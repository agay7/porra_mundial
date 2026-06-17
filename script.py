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

# PUNTOS
P_GANADOR = 1
P_DIFERENCIA = 3
P_RESULTADO_EXACTO = 5
P_POSICION_GRUPO = 3
P_PICHICHI = 10
P_BALON_ORO = 10

# ======================
# PARTIDOS
# ======================
def puntos_partido(real, apuesta):

    gl_r, gv_r = real["GOLES LOCAL"], real["GOLES VISITANTE"]
    gl_a, gv_a = apuesta["GOLES LOCAL"], apuesta["GOLES VISITANTE"]

    local_r = str(real["LOCAL"]).strip().upper()
    visitante_r = str(real["VISITANTE"]).strip().upper()

    local_a = str(apuesta["LOCAL"]).strip().upper()
    visitante_a = str(apuesta["VISITANTE"]).strip().upper()

    # ganador real
    if gl_r > gv_r:
        ganador_real = local_r
    elif gv_r > gl_r:
        ganador_real = visitante_r
    else:
        ganador_real = None

    # ganador apuesta
    if gl_a > gv_a:
        ganador_apuesta = local_a
    elif gv_a > gl_a:
        ganador_apuesta = visitante_a
    else:
        ganador_apuesta = None

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


# ======================
# MAIN
# ======================
def main():

    maestro = pd.read_excel(RUTA_MAESTRO, sheet_name="Datos")

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

    df = pd.DataFrame(ranking).sort_values("Totales", ascending=False).reset_index(drop=True)
    df.insert(0, "Posición", df.index + 1)

    # ======================
    # GUARDAR EXCEL
    # ======================
    df.to_excel(SALIDA, index=False)

    # colorear movimientos opcional
    wb = load_workbook(SALIDA)
    ws = wb.active

    verde = PatternFill("solid", fgColor="C6EFCE")

    for fila in range(2, ws.max_row + 1):
        ws.cell(row=fila, column=5).fill = verde

    wb.save(SALIDA)

    # ======================
    # HTML (WEB)
    # ======================

    now = datetime.now().strftime("%d/%m %H:%M")

    html_table = df.to_html(index=False)

    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
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
            tr:nth-child(2) {{ background: gold; color: black; }}
            tr:nth-child(3) {{ background: silver; color: black; }}
            tr:nth-child(4) {{ background: #cd7f32; color: black; }}
        </style>
    </head>
    <body>

    <h1>🏆 Clasificación Porra</h1>
    <p>Actualizado: {now}</p>

    {html_table}

    </body>
    </html>
    """

    with open(HTML_SALIDA, "w", encoding="utf-8") as f:
        f.write(html)

    print("✅ HTML generado")

    # ======================
    # AUTO PUSH
    # ======================

    print("🚀 Subiendo a GitHub...")

    os.system("git add .")
    os.system('git commit -m "update automatico"')
    os.system("git push")

    print("✅ Todo actualizado")


if __name__ == "__main__":
    main()