import pandas as pd
from pathlib import Path
import os
import json
from datetime import datetime
import subprocess

# ======================
# CONFIG
# ======================
RUTA_MAESTRO = Path("data/maestro.xlsx")
RUTA_PARTICIPANTES = Path("data/participantes")
SALIDA = "clasificacion.xlsx"
HTML_SALIDA = "index.html"


# ======================
# FUNCIONES
# ======================

def puntuar(maestro, jugador):

    total, g, d, e = 0, 0, 0, 0

    partidos = maestro[(maestro["ID"] >= 1) & (maestro["ID"] <= 104)]

    for _, real in partidos.iterrows():

        if int(real.get("JUGADO", 0)) != 1:
            continue

        fila = jugador[jugador["ID"] == real["ID"]]
        if fila.empty:
            continue

        apuesta = fila.iloc[0]

        gl_r = real["GOLES LOCAL"]
        gv_r = real["GOLES VISITANTE"]

        gl_a = apuesta["GOLES LOCAL"]
        gv_a = apuesta["GOLES VISITANTE"]

        ganador_r = 1 if gl_r > gv_r else -1 if gv_r > gl_r else 0
        ganador_a = 1 if gl_a > gv_a else -1 if gv_a > gl_a else 0

        if ganador_r != ganador_a:
            continue

        if gl_r == gl_a and gv_r == gv_a:
            total += 5; e += 1
        elif (gl_r - gv_r) == (gl_a - gv_a):
            total += 3; d += 1
        else:
            total += 1; g += 1

    return total, g, d, e


def partidos_hoy_predicciones(maestro):

    maestro["Fecha"] = pd.to_datetime(maestro["Fecha"], dayfirst=True, errors="coerce")
    maestro["Hora"] = pd.to_datetime(maestro["Hora"], format="%H:%M", errors="coerce")

    hoy = datetime.now().date()

    partidos = maestro[
        maestro["Fecha"].dt.date == hoy
    ].sort_values("Hora")

    if partidos.empty:
        partidos = maestro[maestro["JUGADO"] != 1].head(3)

    html = "<div class='partidos'><h2>📅 Partidos de hoy</h2>"

    for _, partido in partidos.iterrows():

        hora_txt = ""
        if pd.notna(partido["Hora"]):
            hora_txt = partido["Hora"].strftime("%H:%M")

        html += f"<div class='partido'><h3>{hora_txt} - {partido['LOCAL']} vs {partido['VISITANTE']}</h3>"

        for archivo in RUTA_PARTICIPANTES.glob("*.xlsx"):

            if archivo.name.startswith("~$"):
                continue

            nombre = archivo.stem.replace("_", " ")
            jugador = pd.read_excel(archivo, sheet_name="Datos")

            fila = jugador[jugador["ID"] == partido["ID"]]
            if fila.empty:
                continue

            pred = fila.iloc[0]

            gl = int(pred["GOLES LOCAL"])
            gv = int(pred["GOLES VISITANTE"])

            html += f"<p><b>{nombre}:</b> {gl}-{gv}</p>"

        html += "</div>"

    html += "</div>"
    return html


# ======================
# MAIN
# ======================

def main():

    maestro = pd.read_excel(RUTA_MAESTRO, sheet_name="Datos")

    ranking = []

    for archivo in RUTA_PARTICIPANTES.glob("*.xlsx"):

        if archivo.name.startswith("~$"):
            continue

        jugador = pd.read_excel(archivo, sheet_name="Datos")

        puntos, g, d, e = puntuar(maestro, jugador)

        ranking.append({
            "Participante": archivo.stem,
            "Signo": g,
            "Diferencia": d,
            "Exactos": e,
            "Totales": puntos
        })

    df = pd.DataFrame(ranking).sort_values("Totales", ascending=False).reset_index(drop=True)
    df.insert(0, "Posición", df.index + 1)

    # ✅ guardar clasificación anterior EN MEMORIA (clave)
    clasificacion_anterior = df[["Participante", "Posición"]].copy()

    # ======================
    # EVOLUCIÓN (CORRECTA)
    # ======================

    evolucion = []

    for _, row in df.iterrows():
        nombre = row["Participante"]
        pos_actual = row["Posición"]

        fila_ant = clasificacion_anterior[
            clasificacion_anterior["Participante"] == nombre
        ]

        if fila_ant.empty:
            evolucion.append("")
        else:
            pos_anterior = int(fila_ant.iloc[0]["Posición"])
            diff = pos_anterior - pos_actual

            if diff > 0:
                evolucion.append(f"⬆️ {diff}")
            elif diff < 0:
                evolucion.append(f"⬇️ {abs(diff)}")
            else:
                evolucion.append("➡️")

    df["Evolución"] = evolucion

    df.to_excel(SALIDA, index=False)

    df = df[[
        "Posición",
        "Participante",
        "Evolución",
        "Signo",
        "Diferencia",
        "Exactos",
        "Totales"
    ]]

    html_table = df.to_html(index=False, escape=False)
    partidos_html = partidos_hoy_predicciones(maestro)

    now = datetime.now().strftime("%d/%m %H:%M:%S")

    html = f"""
<html>
<head>
<meta charset="UTF-8">
</head>

<body>

<h1>🏆 Clasificación Porra Mundial</h1>

<p>Actualizado: {now}</p>

{html_table}

{partidos_html}

</body>
</html>
"""

    with open(HTML_SALIDA, "w", encoding="utf-8") as f:
        f.write(html)

    print("✅ TODO OK")


# ======================
# GIT AUTO
# ======================

def push_git():
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "auto update"], check=False)
        subprocess.run(["git", "push"], check=True)
        print("✅ Repo actualizado automáticamente")
    except Exception as e:
        print(f"⚠️ Error en git: {e}")


if __name__ == "__main__":
    main()
    push_git()
