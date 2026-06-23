import pandas as pd
from pathlib import Path
import os
import json
import unicodedata
from datetime import datetime
import subprocess

# ======================
# CONFIG
# ======================
RUTA_MAESTRO = Path("data/maestro.xlsx")
RUTA_PARTICIPANTES = Path("data/participantes")
SALIDA = "clasificacion.xlsx"
HTML_SALIDA = "index.html"
RUTA_HISTORICO = Path("historico.json")

# Cambiar a True cuando termine la fase de grupos
# para activar el cálculo de posiciones, Balón de Oro y Bota de Oro
FASE_GRUPOS_TERMINADA = False


# ======================
# FUNCIONES
# ======================

ID_GRUPOS_MAX    = 72             # IDs 1-72   → fase de grupos (equipos fijos)
ID_ELIMINATORIA  = range(73, 105) # IDs 73-104 → eliminatorias
ID_POSICIONES    = range(1000, 1048)  # IDs 1000-1047 → posiciones de grupo (3 pts c/u)
ID_BOTA_ORO      = 988            # Pichichi  → 10 pts
ID_BALON_ORO     = 999            # Balón de Oro → 10 pts


def puntuar_extras(maestro, jugador):
    """
    Puntúa los bonus:
      - Posición exacta de equipo en fase de grupos (IDs 1000-1047): 3 pts
      - Bota de Oro / Pichichi (ID 988): 10 pts
      - Balón de Oro (ID 999): 10 pts
    Devuelve los puntos extra totales.
    """
    puntos_extra = 0

    # ── Posiciones de grupo ──────────────────────────────
    maestro_pos = maestro[maestro["ID"].isin(ID_POSICIONES)]

    for _, real in maestro_pos.iterrows():
        real_id    = int(real["ID"])
        equipo_real = str(real["GOLES LOCAL"]).strip() if pd.notna(real["GOLES LOCAL"]) else ""

        if not equipo_real or equipo_real in ("nan", "0", ""):
            continue  # resultado aún no rellenado

        fila_jug = jugador[jugador["ID"] == real_id]
        if fila_jug.empty:
            continue

        equipo_pred = str(fila_jug.iloc[0]["GOLES LOCAL"]).strip()
        if equipo_pred.lower() == equipo_real.lower():
            puntos_extra += 3

    # ── Bota de Oro / Balón de Oro ───────────────────────
    for id_premio, col_maestro in [(ID_BOTA_ORO, "Unnamed: 6"), (ID_BALON_ORO, "Unnamed: 6")]:

        fila_real = maestro[maestro["ID"] == id_premio]
        if fila_real.empty:
            continue

        resultado_real = str(fila_real.iloc[0].get(col_maestro, "")).strip()
        if not resultado_real or resultado_real in ("nan", "0", "0.0", ""):
            continue  # aún no resuelto

        fila_jug = jugador[jugador["ID"] == id_premio]
        if fila_jug.empty:
            continue

        pred = str(fila_jug.iloc[0].get("PREMIO", "")).strip()
        if pred.lower() == resultado_real.lower():
            puntos_extra += 10

    return puntos_extra


def puntuar(maestro, jugador):

    total, g, d, e = 0, 0, 0, 0

    partidos = maestro[(maestro["ID"] >= 1) & (maestro["ID"] <= 104)]

    # Pre-cargamos las predicciones de eliminatoria del jugador
    # para poder buscar equipos en otros IDs (Level 2)
    jugador_ko = jugador[jugador["ID"].isin(ID_ELIMINATORIA)].copy()
    jugador_ko["LOCAL"]     = jugador_ko["LOCAL"].astype(str).str.strip()
    jugador_ko["VISITANTE"] = jugador_ko["VISITANTE"].astype(str).str.strip()

    for _, real in partidos.iterrows():

        if int(real.get("JUGADO", 0)) != 1:
            continue

        real_id = int(real["ID"])
        fila = jugador[jugador["ID"] == real_id]
        if fila.empty:
            continue

        apuesta = fila.iloc[0]
        gl_r = real["GOLES LOCAL"]
        gv_r = real["GOLES VISITANTE"]
        gl_a = apuesta["GOLES LOCAL"]
        gv_a = apuesta["GOLES VISITANTE"]

        # =====================================================
        # FASE DE GRUPOS (IDs 1-72): lógica original
        # =====================================================
        if real_id <= ID_GRUPOS_MAX:

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

        # =====================================================
        # ELIMINATORIAS (IDs 73-104): validación de equipos
        # =====================================================
        else:

            real_local = str(real["LOCAL"]).strip()
            real_visit = str(real["VISITANTE"]).strip()
            pred_local = str(apuesta["LOCAL"]).strip()
            pred_visit = str(apuesta["VISITANTE"]).strip()
            equipos_reales = {real_local, real_visit}

            # Ganador real (tras 90' + prórroga)
            if gl_r > gv_r:
                winner_real = real_local
            elif gv_r > gl_r:
                winner_real = real_visit
            else:
                # Empate tras prórroga → ganador por penaltis no cambia el marcador;
                # en este caso no se puede puntuar diferencia ni exacto
                winner_real = None

            # --- LEVEL 1: equipos acertados en el mismo ID ---
            acertados_l1 = set()
            if pred_local in equipos_reales:
                acertados_l1.add(pred_local)
            if pred_visit in equipos_reales:
                acertados_l1.add(pred_visit)

            # Detectamos si los dos equipos están pero invertidos
            pred_invertido = (pred_local == real_visit and pred_visit == real_local)

            # --- LEVEL 2: buscar equipos reales en otros IDs de eliminatoria ---
            acertados_l2 = set()
            for equipo in equipos_reales:
                if equipo not in acertados_l1:
                    encontrado = jugador_ko[
                        (jugador_ko["ID"] != real_id) &
                        (
                            (jugador_ko["LOCAL"]     == equipo) |
                            (jugador_ko["VISITANTE"] == equipo)
                        )
                    ]
                    if not encontrado.empty:
                        acertados_l2.add(equipo)

            acertados = acertados_l1 | acertados_l2

            # Si no acertó ningún equipo real → 0 puntos
            if not acertados:
                continue

            # Ganador predicho desde la apuesta del mismo ID
            if gl_a > gv_a:
                winner_pred = pred_local
            elif gv_a > gl_a:
                winner_pred = pred_visit
            else:
                winner_pred = None

            # ¿El ganador predicho (mismo ID) es el equipo ganador real?
            if winner_pred in equipos_reales and winner_pred == winner_real:

                # Acertó el ganador desde el mismo ID → puntuación completa
                # Si los equipos estaban invertidos, normalizamos el marcador
                if pred_invertido:
                    gl_a, gv_a = gv_a, gl_a

                if gl_r == gl_a and gv_r == gv_a:
                    total += 5; e += 1
                elif (gl_r - gv_r) == (gl_a - gv_a):
                    total += 3; d += 1
                else:
                    total += 1; g += 1

            elif winner_real in acertados_l2:
                # El ganador real no aparece como ganador en la predicción del mismo ID,
                # pero el participante lo predijo en algún otro cruce de eliminatoria (Level 2)
                # → acertó que ese equipo llegaría hasta aquí → 1 punto
                total += 1; g += 1

    return total, g, d, e


def cargar_historico():
    """Lee la clasificación de la ejecución anterior desde historico.json."""
    if RUTA_HISTORICO.exists():
        try:
            with open(RUTA_HISTORICO, "r", encoding="utf-8") as f:
                data = json.load(f)
            # normalizamos los nombres (NFC) para evitar que un mismo nombre
            # con tildes codificadas de forma distinta no haga "match"
            return {unicodedata.normalize("NFC", k): v for k, v in data.items()}
        except Exception as e:
            print(f"⚠️ No se pudo leer historico.json: {e}")
            return {}
    return {}


def guardar_historico(df):
    """Guarda la clasificación actual en historico.json para la próxima ejecución."""
    historico = dict(zip(df["Participante"], df["Posición"].astype(int)))
    with open(RUTA_HISTORICO, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)


def partidos_hoy_predicciones(maestro):

    maestro["Fecha"] = pd.to_datetime(maestro["Fecha"], dayfirst=True, errors="coerce")
    maestro["Hora"]  = pd.to_datetime(maestro["Hora"],  format="%H:%M", errors="coerce")

    hoy = datetime.now().date()

    partidos = maestro[maestro["Fecha"].dt.date == hoy].sort_values("Hora")

    if partidos.empty:
        partidos = maestro[maestro["JUGADO"] != 1].head(3)

    # Primer partido sin jugar hoy → se resalta como "próximo"
    proximos = partidos[partidos["JUGADO"] != 1]
    id_proximo = int(proximos.iloc[0]["ID"]) if not proximos.empty else None

    html = "<div class='partidos'><h2>📅 Partidos de hoy</h2>"

    for _, partido in partidos.iterrows():

        jugado   = int(partido.get("JUGADO", 0)) == 1
        es_proximo = (int(partido["ID"]) == id_proximo)

        hora_txt = partido["Hora"].strftime("%H:%M") if pd.notna(partido["Hora"]) else ""

        # Resultado real si ya se jugó
        if jugado:
            gl_r = int(partido["GOLES LOCAL"])
            gv_r = int(partido["GOLES VISITANTE"])
            resultado_txt = (
                f"<span class='resultado'>"
                f"{partido['LOCAL']} <b>{gl_r} - {gv_r}</b> {partido['VISITANTE']}"
                f"</span>"
            )
            ganador_r = 1 if gl_r > gv_r else -1 if gv_r > gl_r else 0
        else:
            resultado_txt = ""
            ganador_r     = None

        clase = "partido jugado" if jugado else ("partido proximo" if es_proximo else "partido")
        icono = "✅" if jugado else ("🔜" if es_proximo else "🕐")

        html += f"<div class='{clase}'>"
        html += f"<h3>{icono} {hora_txt} - {partido['LOCAL']} vs {partido['VISITANTE']}</h3>"

        if jugado:
            html += f"<p class='resultado-final'>Resultado: {resultado_txt}</p>"

        # Predicciones de cada participante
        for archivo in RUTA_PARTICIPANTES.glob("*.xlsx"):

            if archivo.name.startswith("~$"):
                continue

            nombre = archivo.stem.replace("_", " ")
            jugador = pd.read_excel(archivo, sheet_name="Datos")

            fila = jugador[jugador["ID"] == partido["ID"]]
            if fila.empty:
                continue

            pred  = fila.iloc[0]
            gl_a  = int(pred["GOLES LOCAL"])
            gv_a  = int(pred["GOLES VISITANTE"])

            if jugado:
                ganador_a = 1 if gl_a > gv_a else -1 if gv_a > gl_a else 0
                acerto    = ganador_a == ganador_r
                marca     = "✅" if acerto else "❌"
                # resaltamos si acertó exacto
                exacto    = (gl_a == gl_r and gv_a == gv_r)
                estilo    = " class='pred-exacto'" if exacto else ""
                html += f"<p{estilo}>{marca} <b>{nombre}:</b> {gl_a}-{gv_a}</p>"
            else:
                html += f"<p><b>{nombre}:</b> {gl_a}-{gv_a}</p>"

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
        extras = puntuar_extras(maestro, jugador) if FASE_GRUPOS_TERMINADA else 0

        ranking.append({
            "Participante": unicodedata.normalize("NFC", archivo.stem),
            "Signo":        g,
            "Diferencia":   d,
            "Exactos":      e,
            "Extras":       extras,
            "Totales":      puntos + extras
        })

    df = pd.DataFrame(ranking).sort_values("Totales", ascending=False).reset_index(drop=True)
    df.insert(0, "Posición", df.index + 1)

    # 📥 clasificación de la ejecución ANTERIOR (real), leída de historico.json
    historico_anterior = cargar_historico()

    # ======================
    # EVOLUCIÓN
    # ======================

    evolucion = []

    for _, row in df.iterrows():
        nombre = row["Participante"]
        pos_actual = row["Posición"]

        pos_anterior = historico_anterior.get(nombre)

        if pos_anterior is None:
            evolucion.append("")
        else:
            diff = pos_anterior - pos_actual

            if diff > 0:
                evolucion.append(f"<span style='color:#00ff00'>⬆️ +{diff}</span>")
            elif diff < 0:
                evolucion.append(f"<span style='color:#ff4d4d'>⬇️ -{abs(diff)}</span>")
            else:
                evolucion.append(f"<span style='color:#ffffff; font-weight:bold'>=</span>")


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

<style>
body {{
    background:#111;
    color:#fff;
    font-family:Arial;
    text-align:center;
}}

table {{
    margin:30px auto;
    border-collapse:collapse;
    width:80%;
    background:#181818;
    border-radius:10px;
}}

th {{
    background:#222;
    color:#fff;
    padding:12px;
}}

th, td {{
    padding:10px;
    border-bottom:1px solid #333;
    text-align:center;
}}

tr:hover {{
    background:#2a2a2a;
}}

tbody tr:nth-of-type(1) {{
    background:gold;
    color:#000;
    font-weight:bold;
}}

tbody tr:nth-of-type(2) {{
    background:silver;
    color:#000;
    font-weight:bold;
}}

tbody tr:nth-of-type(3) {{
    background:#cd7f32;
    color:#000;
    font-weight:bold;
}}

tbody tr:nth-of-type(4) {{
    background:#4caf50;
    color:#000;
    font-weight:bold;
}}

td:nth-child(3) {{
    font-weight:bold;
}}

.partidos {{
    max-width:900px;
    margin:40px auto;
    text-align:left;
}}

.partido {{
    background:#1a1a1a;
    padding:12px;
    margin-bottom:15px;
    border-radius:8px;
}}

.partido h3 {{
    color:#00ffcc;
}}

.partido.jugado {{
    background:#1a1a1a;
    border-left: 4px solid #555;
    opacity: 0.85;
}}

.partido.jugado h3 {{
    color:#888;
}}

.partido.proximo {{
    background:#1a2a1a;
    border-left: 4px solid #00ff99;
    box-shadow: 0 0 12px #00ff9933;
}}

.partido.proximo h3 {{
    color:#00ff99;
}}

.resultado-final {{
    font-size: 1.1em;
    margin: 6px 0 10px 0;
    padding: 6px 10px;
    background:#222;
    border-radius:6px;
    display: inline-block;
}}

.resultado {{
    color:#fff;
}}

.pred-exacto {{
    color:#ffd700;
    font-weight: bold;
}}

td:nth-child(7) {{
    color:#00ff99;
    font-weight:bold;
}}

</style>

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

    # 💾 guardar la clasificación de ESTA ejecución como histórico
    # para que la próxima vez la evolución se calcule correctamente
    guardar_historico(df)

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