import pandas as pd
from pathlib import Path
import os
import json
import unicodedata
from datetime import datetime

# ======================
# CONFIG
# ======================
RUTA_MAESTRO = Path("data/maestro.xlsx")
RUTA_PARTICIPANTES = Path("data/participantes")
SALIDA = "clasificacion.xlsx"
HTML_SALIDA = "index.html"

P_GANADOR = 1
P_DIFERENCIA = 3
P_RESULTADO_EXACTO = 5

# ======================
# FUNCIONES
# ======================
def puntos_partido(real, apuesta):

    gl_r, gv_r = real["GOLES LOCAL"], real["GOLES VISITANTE"]
    gl_a, gv_a = apuesta["GOLES LOCAL"], apuesta["GOLES VISITANTE"]

    ganador_r = 1 if gl_r > gv_r else -1 if gv_r > gl_r else 0
    ganador_a = 1 if gl_a > gv_a else -1 if gv_a > gl_a else 0

    if ganador_r != ganador_a:
        return 0

    if gl_r == gl_a and gv_r == gv_a:
        return P_RESULTADO_EXACTO

    if (gl_r - gv_r) == (gl_a - gv_a):
        return P_DIFERENCIA

    return P_GANADOR


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
        puntos = puntos_partido(real, apuesta)

        total += puntos

        if puntos == 5: e += 1
        elif puntos == 3: d += 1
        elif puntos == 1: g += 1

    return total, g, d, e


def contar_partidos_jugados(maestro):
    partidos = maestro[(maestro["ID"] >= 1) & (maestro["ID"] <= 104)]
    return int((partidos["JUGADO"] == 1).sum())


# ======================
# NUEVO BLOQUE 🔥
# ======================
def partidos_hoy_predicciones(maestro):

    partidos = maestro[(maestro["JUGADO"] != 1)].head(3)

    html = "<div class='partidos'>"
    html += "<h2>📅 Próximos partidos</h2>"

    for _, partido in partidos.iterrows():

        html += "<div class='partido'>"
        html += f"<h3>{partido['LOCAL']} vs {partido['VISITANTE']}</h3>"

        for archivo in RUTA_PARTICIPANTES.glob("*.xlsx"):

            if archivo.name.startswith("~$"):
                continue

            nombre = archivo.stem
            jugador = pd.read_excel(archivo, sheet_name="Datos")

            fila = jugador[jugador["ID"] == partido["ID"]]

            if fila.empty:
                continue

            pred = fila.iloc[0]

            html += f"<p><b>{nombre}:</b> {pred['GOLES LOCAL']}-{pred['GOLES VISITANTE']}</p>"

        html += "</div>"

    html += "</div>"

    return html


# ======================
# HISTÓRICO
# ======================
def _nfc(s):
    return unicodedata.normalize("NFC", str(s))


def actualizar_historico(df, partidos_jugados, ruta="historico.json"):

    totales = {_nfc(r["Participante"]).replace("_", " ").strip(): int(r["Totales"])
               for _, r in df.iterrows()}

    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            raw = json.load(f)
    else:
        raw = {"md": [], "players": []}

    md = raw["md"]
    players = {p[0]: p for p in raw["players"]}

    if md and md[-1] == partidos_jugados:
        for nombre, pts in totales.items():
            if nombre in players:
                players[nombre][1][-1] = pts
    else:
        md.append(partidos_jugados)
        for nombre, pts in totales.items():
            if nombre in players:
                players[nombre][1].append(pts)
            else:
                players[nombre] = [nombre, [pts]]

    hist = {"md": md, "players": list(players.values())}

    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False)

    return hist


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

        jugador = pd.read_excel(archivo, sheet_name="Datos")

        puntos, g, d, e = puntuar(maestro, jugador)

        ranking.append({
            "Participante": archivo.stem,
            "Signo": g,
            "Diferencia": d,
            "Exactos": e,
            "Totales": puntos
        })

    df = pd.DataFrame(ranking).sort_values("Totales", ascending=False)
    df.insert(0, "Posición", range(1, len(df) + 1))

    df.to_excel(SALIDA, index=False)

    hist = actualizar_historico(df, partidos_jugados)

    html_table = df.to_html(index=False, escape=False)
    partidos_html = partidos_hoy_predicciones(maestro)

    # ======================
    # HTML FINAL
    # ======================
    now = datetime.now().strftime("%d/%m %H:%M:%S")

    html = f"""
<html>
<head>
<style>

body {{ background:#111; color:white; font-family:Arial; text-align:center; }}

table {{ margin:20px auto; border-collapse:collapse; }}
th, td {{ padding:10px; border-bottom:1px solid #444; }}

tbody tr:nth-of-type(1) {{ background:gold; color:black; }}
tbody tr:nth-of-type(2) {{ background:silver; color:black; }}
tbody tr:nth-of-type(3) {{ background:#cd7f32; color:black; }}

.partidos {{
    max-width:900px;
    margin:30px auto;
    text-align:left;
}}

.partido {{
    background:#1a1a1a;
    padding:10px;
    margin-bottom:15px;
    border-radius:8px;
}}

.partido h3 {{
    color:#00ffcc;
    margin-bottom:5px;
}}

</style>
</head>

<body>

<h1>🏆 Porra Mundial</h1>

<p>Actualizado: {now}</p>
<p>Partidos jugados: {partidos_jugados}</p>

{html_table}

{partidos_html}

</body>
</html>
"""

    with open(HTML_SALIDA, "w", encoding="utf-8") as f:
        f.write(html)

    os.system("git add .")
    os.system(f'git commit -m "update {now}"')
    os.system("git push")

    print("✅ TODO OK")


if __name__ == "__main__":
    main()