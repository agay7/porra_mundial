import pandas as pd
from pathlib import Path
import os
import json
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
# HISTÓRICO
# ======================

def actualizar_historico(df, partidos_jugados, ruta="historico.json"):
    totales = {
        str(r["Participante"]).replace("_", " ").strip(): int(r["Totales"])
        for _, r in df.iterrows()
    }

    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            hist = json.load(f)
    else:
        hist = {"md": [], "players": []}

    md = hist["md"]
    players = {p[0]: p for p in hist["players"]}

    if md and md[-1] == partidos_jugados:
        for nombre, pts in totales.items():
            if nombre in players:
                players[nombre][1][-1] = pts
    else:
        md.append(partidos_jugados)
        n = len(md)

        for nombre, pts in totales.items():
            if nombre in players:
                players[nombre][1].append(pts)
            else:
                players[nombre] = [nombre, [None]*(n-1) + [pts]]

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

        nombre = archivo.stem
        jugador = pd.read_excel(archivo, sheet_name="Datos")

        puntos, g, d, e = puntuar(maestro, jugador)

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
    # MOVIMIENTO
    # ======================
    if os.path.exists(SALIDA):

        old = pd.read_excel(SALIDA)
        pos_ant = {r["Participante"]: r["Posición"] for _, r in old.iterrows()}

        mov = []

        for _, fila in df.iterrows():
            nombre = fila["Participante"]

            if nombre not in pos_ant:
                mov.append("🆕")
                continue

            diff = pos_ant[nombre] - fila["Posición"]

            if diff > 0:
                mov.append(f"↑{diff}")
            elif diff < 0:
                mov.append(f"↓{abs(diff)}")
            else:
                mov.append("=")

        df.insert(1, "Mov", mov)

    # ======================
    # GUARDAR EXCEL
    # ======================
    df.to_excel(SALIDA, index=False)

    # ======================
    # HISTÓRICO
    # ======================
    hist = actualizar_historico(df, partidos_jugados)

    # ======================
    # HTML
    # ======================

    def formato_mov(val):
        if "↑" in str(val): return f'<span style="color:#00ff00">{val}</span>'
        elif "↓" in str(val): return f'<span style="color:#ff4444">{val}</span>'
        return val

    if "Mov" in df.columns:
        df["Mov"] = df["Mov"].apply(formato_mov)

    html_table = df.to_html(index=False, escape=False)

    now = datetime.now().strftime("%d/%m %H:%M:%S")

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>
body {{
    background:#111;
    color:white;
    font-family:Arial;
    text-align:center;
}}

table {{
    margin:20px auto;
    border-collapse:collapse;
}}

th, td {{
    padding:10px;
    border-bottom:1px solid #444;
}}

th {{
    background:#222;
}}

/* ✅ TOP 3 (arreglado) */
tbody tr:nth-of-type(1) {{
    background:gold;
    color:black;
    font-weight:bold;
}}

tbody tr:nth-of-type(2) {{
    background:silver;
    color:black;
    font-weight:bold;
}}

tbody tr:nth-of-type(3) {{
    background:#cd7f32;
    color:black;
    font-weight:bold;
}}

/* ✅ totales */
tbody tr:nth-of-type(n+4) td:last-child {{
    color:#00ffcc;
    font-weight:bold;
}}
</style>

</head>

<body>

<h1>🏆 Clasificación Porra Mundial</h1>

<p>Actualizado: {now}</p>
<p>Partidos jugados: {partidos_jugados} / 104</p>

{html_table}

<h2>📈 Evolución</h2>
<pre style="color:#0f0; text-align:left; max-width:800px; margin:auto;">
{json.dumps(hist, indent=2, ensure_ascii=False)}
</pre>

</body>
</html>
"""

    html += f"\n<!-- {datetime.now().timestamp()} -->"

    with open(HTML_SALIDA, "w", encoding="utf-8") as f:
        f.write(html)

    print("✅ HTML generado")

    # ======================
    # GIT
    # ======================
    os.system("git add .")
    os.system(f'git commit -m "update {now}"')
    os.system("git push")

    print("🚀 Actualizado en GitHub")


if __name__ == "__main__":
    main()