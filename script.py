import pandas as pd
from pathlib import Path
import os
import json
import unicodedata
from datetime import datetime, timedelta
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
FASE_GRUPOS_TERMINADA = True


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
                winner_real = None

            # Ganador predicho en el mismo ID
            if gl_a > gv_a:
                winner_pred = pred_local
            elif gv_a > gl_a:
                winner_pred = pred_visit
            else:
                winner_pred = None

            # --- LEVEL 1: equipos acertados en el mismo ID ---
            acertados_l1 = set()
            if pred_local in equipos_reales:
                acertados_l1.add(pred_local)
            if pred_visit in equipos_reales:
                acertados_l1.add(pred_visit)

            pred_invertido = (pred_local == real_visit and pred_visit == real_local)

            # ── DOS equipos correctos en el mismo ID ─────────────────────────
            if len(acertados_l1) == 2:

                if winner_pred is not None and winner_pred == winner_real:
                    if pred_invertido:
                        gl_a, gv_a = gv_a, gl_a
                    if gl_r == gl_a and gv_r == gv_a:
                        total += 10; e += 1
                    elif (gl_r - gv_r) == (gl_a - gv_a):
                        total += 7; d += 1
                    else:
                        total += 5; g += 1
                # empate predicho → el ganador real debe avanzar en otro cruce
                elif winner_pred is None and winner_real is not None:
                    # Empate: el ganador real debe APARECER en rondas posteriores (avanzó por penaltis)
                    encontrado_draw = jugador_ko[
                        (jugador_ko["ID"] > real_id) &
                        (
                            (jugador_ko["LOCAL"]     == winner_real) |
                            (jugador_ko["VISITANTE"] == winner_real)
                        )
                    ]
                    if not encontrado_draw.empty:
                        total += 5; g += 1

            # ── UN equipo correcto en el mismo ID ────────────────────────────
            elif len(acertados_l1) == 1:

                if winner_pred is not None and winner_pred == winner_real:
                    total += 5; g += 1
                elif winner_real is not None:
                    if winner_pred is None:
                        # Empate: aparición en ronda posterior basta (avanzó por penaltis)
                        encontrado_l1 = jugador_ko[
                            (jugador_ko["ID"] > real_id) &
                            (
                                (jugador_ko["LOCAL"]     == winner_real) |
                                (jugador_ko["VISITANTE"] == winner_real)
                            )
                        ]
                    else:
                        # Ganador equivocado: debe GANAR en otro cruce
                        encontrado_l1 = jugador_ko[
                            (jugador_ko["ID"] != real_id) &
                            (
                                ((jugador_ko["LOCAL"]     == winner_real) & (jugador_ko["GOLES LOCAL"] > jugador_ko["GOLES VISITANTE"])) |
                                ((jugador_ko["VISITANTE"] == winner_real) & (jugador_ko["GOLES VISITANTE"] > jugador_ko["GOLES LOCAL"]))
                            )
                        ]
                    if not encontrado_l1.empty:
                        total += 5; g += 1

            # ── CERO equipos correctos en el mismo ID ────────────────────────
            else:

                # ¿Están los DOS equipos reales juntos en otro cruce predicho?
                partido_l2 = None
                for _, pred_row in jugador_ko[jugador_ko["ID"] != real_id].iterrows():
                    p_loc = str(pred_row["LOCAL"]).strip()
                    p_vis = str(pred_row["VISITANTE"]).strip()
                    if real_local in {p_loc, p_vis} and real_visit in {p_loc, p_vis}:
                        partido_l2 = pred_row
                        break

                if partido_l2 is not None:
                    # Ambos equipos predichos juntos en otro cruce → puntuación completa
                    gl_l2 = partido_l2["GOLES LOCAL"]
                    gv_l2 = partido_l2["GOLES VISITANTE"]
                    p_loc_l2 = str(partido_l2["LOCAL"]).strip()
                    invertido_l2 = (p_loc_l2 == real_visit)

                    if gl_l2 > gv_l2:
                        winner_l2 = p_loc_l2
                    elif gv_l2 > gl_l2:
                        winner_l2 = str(partido_l2["VISITANTE"]).strip()
                    else:
                        winner_l2 = None

                    if winner_l2 is not None and winner_l2 == winner_real:
                        gl_cmp = gv_l2 if invertido_l2 else gl_l2
                        gv_cmp = gl_l2 if invertido_l2 else gv_l2
                        if gl_r == gl_cmp and gv_r == gv_cmp:
                            total += 10; e += 1
                        elif (gl_r - gv_r) == (gl_cmp - gv_cmp):
                            total += 7; d += 1
                        else:
                            total += 5; g += 1
                    # ganador incorrecto → 0 pts

                else:
                    # ¿Ganador real GANA en otro cruce, o aparece en ronda posterior (empate → penaltis)?
                    if winner_real is not None:
                        encontrado = jugador_ko[
                            (jugador_ko["ID"] != real_id) &
                            (
                                ((jugador_ko["LOCAL"]     == winner_real) & (jugador_ko["GOLES LOCAL"] > jugador_ko["GOLES VISITANTE"])) |
                                ((jugador_ko["VISITANTE"] == winner_real) & (jugador_ko["GOLES VISITANTE"] > jugador_ko["GOLES LOCAL"]))
                            )
                        ]
                        if encontrado.empty:
                            encontrado = jugador_ko[
                                (jugador_ko["ID"] > real_id) &
                                (
                                    (jugador_ko["LOCAL"]     == winner_real) |
                                    (jugador_ko["VISITANTE"] == winner_real)
                                )
                            ]
                        if not encontrado.empty:
                            total += 5; g += 1

    return total, g, d, e


def cargar_historico():
    """Lee la clasificación de referencia desde historico.json."""
    if RUTA_HISTORICO.exists():
        try:
            with open(RUTA_HISTORICO, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            posiciones = data.get("posiciones", data)
            return {unicodedata.normalize("NFC", k): v for k, v in posiciones.items() if k != "fecha"}
        except Exception as e:
            print(f"No se pudo leer historico.json: {e}")
            return {}
    return {}


def guardar_historico(df):
    """Guarda la clasificación actual en historico.json para la próxima ejecución."""
    nuevo = {
        "fecha": datetime.now().date().isoformat(),
        "posiciones": dict(zip(df["Participante"], df["Posición"].astype(int)))
    }
    with open(RUTA_HISTORICO, "w", encoding="utf-8") as f:
        json.dump(nuevo, f, ensure_ascii=False, indent=2)


def partidos_por_dia(maestro):

    maestro["Fecha"] = pd.to_datetime(maestro["Fecha"], dayfirst=True, errors="coerce")
    maestro["Hora"]  = pd.to_datetime(maestro["Hora"],  format="%H:%M", errors="coerce")

    hoy = datetime.now().date()

    # Cargar todos los participantes una sola vez
    participantes = {}
    for archivo in sorted(RUTA_PARTICIPANTES.glob("*.xlsx")):
        if archivo.name.startswith("~$"):
            continue
        nombre = archivo.stem.replace("_", " ")
        df_jug = pd.read_excel(archivo, sheet_name="Datos")
        participantes[nombre] = df_jug.set_index("ID")

    # Días con partidos, ordenados
    fechas = sorted(maestro["Fecha"].dropna().dt.date.unique())

    if not fechas:
        return ""

    # Índice del día a mostrar por defecto: hoy o el próximo con partidos
    idx_actual = len(fechas) - 1
    for i, f in enumerate(fechas):
        if f >= hoy:
            idx_actual = i
            break

    secciones = []

    for i, fecha in enumerate(fechas):
        partidos_dia = maestro[maestro["Fecha"].dt.date == fecha].sort_values("Hora")

        proximos   = partidos_dia[partidos_dia["JUGADO"] != 1]
        id_proximo = int(proximos.iloc[0]["ID"]) if not proximos.empty else None

        if fecha == hoy:
            label = "Partidos de hoy"
        elif fecha == hoy - timedelta(days=1):
            label = "Partidos de ayer"
        elif fecha == hoy + timedelta(days=1):
            label = "Partidos de tomorrow"
        else:
            label = fecha.strftime("%d/%m/%Y")

        visible       = "block" if i == idx_actual else "none"
        prev_disabled = " disabled" if i == 0 else ""
        next_disabled = " disabled" if i == len(fechas) - 1 else ""

        html  = f"<div class='partidos' id='dia-{i}' style='display:{visible}'>"
        html += (
            f"<div class='nav-partidos'>"
            f"<button class='nav-btn'{prev_disabled} onclick='cambiarDia({i - 1})'>&#9664;</button>"
            f"<h2>&#128197; {label}</h2>"
            f"<button class='nav-btn'{next_disabled} onclick='cambiarDia({i + 1})'>&#9654;</button>"
            f"</div>"
        )

        for _, partido in partidos_dia.iterrows():

            jugado     = int(partido.get("JUGADO", 0)) == 1
            es_proximo = (int(partido["ID"]) == id_proximo)

            hora_txt = partido["Hora"].strftime("%H:%M") if pd.notna(partido["Hora"]) else ""

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
            icono = "&#9989;" if jugado else ("&#128284;" if es_proximo else "&#128336;")

            html += f"<div class='{clase}'>"
            html += f"<h3>{icono} {hora_txt} - {partido['LOCAL']} vs {partido['VISITANTE']}</h3>"

            if jugado:
                html += f"<p class='resultado-final'>Resultado: {resultado_txt}</p>"

            pid = partido["ID"]
            es_eliminatoria = int(pid) > ID_GRUPOS_MAX
            real_local_eq = str(partido["LOCAL"]).strip() if "LOCAL" in partido.index and pd.notna(partido["LOCAL"]) else ""
            real_visit_eq = str(partido["VISITANTE"]).strip() if "VISITANTE" in partido.index and pd.notna(partido["VISITANTE"]) else ""
            equipos_reales = {e for e in [real_local_eq, real_visit_eq] if e and e != "nan"}

            for nombre, df_jug in participantes.items():
                if pid not in df_jug.index:
                    continue

                pred = df_jug.loc[pid]
                gl_a = int(pred["GOLES LOCAL"])
                gv_a = int(pred["GOLES VISITANTE"])

                if jugado:
                  if not es_eliminatoria:
                    ganador_a = 1 if gl_a > gv_a else -1 if gv_a > gl_a else 0
                    acerto    = ganador_a == ganador_r
                    marca     = "&#9989;" if acerto else "&#10060;"
                    exacto    = (gl_a == gl_r and gv_a == gv_r)
                    estilo    = " class='pred-exacto'" if exacto else ""
                    html += f"<p{estilo}>{marca} <b>{nombre}:</b> {gl_a}-{gv_a}</p>"
                  else:
                    # Eliminatoria jugada: buscar equipos y calcular puntos
                    pj_local = str(pred["LOCAL"]).strip() if "LOCAL" in pred.index and pd.notna(pred["LOCAL"]) else ""
                    pj_visit = str(pred["VISITANTE"]).strip() if "VISITANTE" in pred.index and pd.notna(pred["VISITANTE"]) else ""
                    eq_slot  = {e for e in [pj_local, pj_visit] if e and e != "nan"}
                    com_slot = equipos_reales & eq_slot
                    dj_loc, dj_vis = pj_local, pj_visit
                    dj_gl,  dj_gv  = gl_a, gv_a
                    tiene_ambos_j = len(com_slot) == 2
                    tiene_alguno_j = len(com_slot) >= 1
                    # Level 2 solo cuando hay CERO equipos en el slot directo (igual que puntuar())
                    if not tiene_alguno_j:
                        for lid in sorted((i for i in df_jug.index if pd.notna(i) and int(i) != int(pid) and 73 <= int(i) <= 104), key=int):
                            lp = df_jug.loc[lid]
                            if "LOCAL" not in lp.index or "VISITANTE" not in lp.index:
                                continue
                            ll = str(lp["LOCAL"]).strip() if pd.notna(lp["LOCAL"]) else ""
                            lv = str(lp["VISITANTE"]).strip() if pd.notna(lp["VISITANTE"]) else ""
                            if ll not in ("", "nan") and lv not in ("", "nan"):
                                if real_local_eq in {ll, lv} and real_visit_eq in {ll, lv}:
                                    dj_loc, dj_vis = ll, lv
                                    dj_gl = int(lp["GOLES LOCAL"])
                                    dj_gv = int(lp["GOLES VISITANTE"])
                                    tiene_ambos_j = True
                                    tiene_alguno_j = True
                                    break
                    # Bracket individual (excluye slot directo, igual que puntuar())
                    # Si el equipo aparece en varios slots, se prefiere el slot donde GANA
                    eq_bracket_j = {}
                    for lid in sorted((i for i in df_jug.index if pd.notna(i) and int(i) != int(pid) and 73 <= int(i) <= 104), key=int):
                        lp2 = df_jug.loc[lid]
                        if "LOCAL" not in lp2.index or "VISITANTE" not in lp2.index:
                            continue
                        ll2 = str(lp2["LOCAL"]).strip() if pd.notna(lp2["LOCAL"]) else ""
                        lv2 = str(lp2["VISITANTE"]).strip() if pd.notna(lp2["VISITANTE"]) else ""
                        if ll2 in ("", "nan") or lv2 in ("", "nan"):
                            continue
                        gl2j = int(lp2["GOLES LOCAL"]); gv2j = int(lp2["GOLES VISITANTE"])
                        for eq in equipos_reales:
                            if eq in {ll2, lv2}:
                                gana = (eq == ll2 and gl2j > gv2j) or (eq == lv2 and gv2j > gl2j)
                                if eq not in eq_bracket_j or gana:
                                    eq_bracket_j[eq] = (ll2, gl2j, gv2j, lv2)
                    # Ganador real
                    winner_r_j = real_local_eq if gl_r > gv_r else (real_visit_eq if gv_r > gl_r else None)
                    # Calcular puntos (replicando exactamente puntuar())
                    pts_j = 0
                    if tiene_ambos_j:
                        pred_w = dj_loc if dj_gl > dj_gv else (dj_vis if dj_gv > dj_gl else None)
                        if pred_w is not None and pred_w == winner_r_j:
                            cmp_gl = dj_gv if dj_loc == real_visit_eq else dj_gl
                            cmp_gv = dj_gl if dj_loc == real_visit_eq else dj_gv
                            if gl_r == cmp_gl and gv_r == cmp_gv:
                                pts_j = 10
                            elif (gl_r - gv_r) == (cmp_gl - cmp_gv):
                                pts_j = 7
                            else:
                                pts_j = 5
                        elif pred_w is None and winner_r_j:
                            for nid in (i for i in df_jug.index if pd.notna(i) and int(i) > int(pid) and 73 <= int(i) <= 104):
                                np2 = df_jug.loc[nid]
                                if "LOCAL" not in np2.index or "VISITANTE" not in np2.index:
                                    continue
                                nl2 = str(np2["LOCAL"]).strip() if pd.notna(np2["LOCAL"]) else ""
                                nv2 = str(np2["VISITANTE"]).strip() if pd.notna(np2["VISITANTE"]) else ""
                                if winner_r_j in {nl2, nv2}:
                                    pts_j = 5; break
                    elif tiene_alguno_j:
                        pred_w = dj_loc if dj_gl > dj_gv else (dj_vis if dj_gv > dj_gl else None)
                        if pred_w is not None and pred_w == winner_r_j:
                            pts_j = 5
                        elif pred_w is None and winner_r_j:
                            # Empate: aparición en ronda posterior basta
                            for nid in (i for i in df_jug.index if pd.notna(i) and int(i) > int(pid) and 73 <= int(i) <= 104):
                                np2 = df_jug.loc[nid]
                                if "LOCAL" not in np2.index or "VISITANTE" not in np2.index:
                                    continue
                                nl2 = str(np2["LOCAL"]).strip() if pd.notna(np2["LOCAL"]) else ""
                                nv2 = str(np2["VISITANTE"]).strip() if pd.notna(np2["VISITANTE"]) else ""
                                if winner_r_j in {nl2, nv2}:
                                    pts_j = 5; break
                        elif winner_r_j and winner_r_j in eq_bracket_j:
                            v = eq_bracket_j[winner_r_j]
                            if (winner_r_j == v[0] and v[1] > v[2]) or (winner_r_j == v[3] and v[2] > v[1]):
                                pts_j = 5
                    else:
                        if winner_r_j and winner_r_j in eq_bracket_j:
                            v = eq_bracket_j[winner_r_j]
                            if (winner_r_j == v[0] and v[1] > v[2]) or (winner_r_j == v[3] and v[2] > v[1]):
                                pts_j = 5
                            else:
                                for nid in (i for i in df_jug.index if pd.notna(i) and int(i) > int(pid) and 73 <= int(i) <= 104):
                                    np2 = df_jug.loc[nid]
                                    if "LOCAL" not in np2.index or "VISITANTE" not in np2.index:
                                        continue
                                    nl2 = str(np2["LOCAL"]).strip() if pd.notna(np2["LOCAL"]) else ""
                                    nv2 = str(np2["VISITANTE"]).strip() if pd.notna(np2["VISITANTE"]) else ""
                                    if winner_r_j in {nl2, nv2}:
                                        pts_j = 5; break
                    # Display
                    marca_j  = "&#9989;" if pts_j > 0 else "&#10060;"
                    pts_txt  = f" <span style='color:#0f0'>+{pts_j}pts</span>" if pts_j > 0 else ""
                    estilo_j = " class='pred-exacto'" if pts_j == 10 else (" class='pred-diff'" if pts_j == 7 else "")
                    dj_eq_set = {e for e in [dj_loc, dj_vis] if e and e not in ("", "nan")}
                    extras_j  = {eq: v for eq, v in eq_bracket_j.items() if eq not in dj_eq_set}
                    nota_j    = ""
                    if extras_j and not tiene_ambos_j:
                        partes_j = [f"{eq}: {v[0]} {v[1]}-{v[2]} {v[3]}" for eq, v in sorted(extras_j.items())]
                        nota_j = " [también: " + " | ".join(partes_j) + "]"
                    if tiene_ambos_j or tiene_alguno_j:
                        html += f"<p{estilo_j}>{marca_j} <b>{nombre}:</b> <span style='color:#aaa'>{dj_loc} {dj_gl}-{dj_gv} {dj_vis}{nota_j}</span>{pts_txt}</p>"
                    elif eq_bracket_j:
                        partes_b = [f"{eq}: {v[0]} {v[1]}-{v[2]} {v[3]}" for eq, v in sorted(eq_bracket_j.items())]
                        html += f"<p>{marca_j} <b>{nombre}:</b> <span style='color:#aaa'>{' | '.join(partes_b)}</span>{pts_txt}</p>"
                    else:
                        html += f"<p>&#10060; <b>{nombre}:</b> &#10060;</p>"
                else:
                    if es_eliminatoria and equipos_reales:
                        pred_local_eq = str(pred["LOCAL"]).strip() if "LOCAL" in pred.index and pd.notna(pred["LOCAL"]) else ""
                        pred_visit_eq = str(pred["VISITANTE"]).strip() if "VISITANTE" in pred.index and pd.notna(pred["VISITANTE"]) else ""
                        equipos_slot = {e for e in [pred_local_eq, pred_visit_eq] if e and e != "nan"}
                        comunes_slot = equipos_reales & equipos_slot

                        disp_local, disp_visit = pred_local_eq, pred_visit_eq
                        disp_gl, disp_gv = gl_a, gv_a
                        tiene_ambos = len(comunes_slot) == 2
                        tiene_alguno = len(comunes_slot) >= 1

                        # Level 2: buscar ambos equipos reales juntos en otro slot de eliminatoria
                        if not tiene_ambos:
                            for lid in sorted((i for i in df_jug.index if pd.notna(i) and int(i) != int(pid) and 73 <= int(i) <= 104), key=int):
                                lpred = df_jug.loc[lid]
                                if "LOCAL" not in lpred.index or "VISITANTE" not in lpred.index:
                                    continue
                                ll = str(lpred["LOCAL"]).strip() if pd.notna(lpred["LOCAL"]) else ""
                                lv = str(lpred["VISITANTE"]).strip() if pd.notna(lpred["VISITANTE"]) else ""
                                if ll not in ("", "nan") and lv not in ("", "nan"):
                                    if real_local_eq in {ll, lv} and real_visit_eq in {ll, lv}:
                                        disp_local, disp_visit = ll, lv
                                        disp_gl = int(lpred["GOLES LOCAL"])
                                        disp_gv = int(lpred["GOLES VISITANTE"])
                                        tiene_ambos = True
                                        tiene_alguno = True
                                        break

                        # Buscar cada equipo real individualmente en todo el bracket (guardando el resultado de ese slot)
                        equipos_en_bracket = {}
                        for lid in sorted((i for i in df_jug.index if pd.notna(i) and 73 <= int(i) <= 104), key=int):
                            lpred2 = df_jug.loc[lid]
                            if "LOCAL" not in lpred2.index or "VISITANTE" not in lpred2.index:
                                continue
                            ll2 = str(lpred2["LOCAL"]).strip() if pd.notna(lpred2["LOCAL"]) else ""
                            lv2 = str(lpred2["VISITANTE"]).strip() if pd.notna(lpred2["VISITANTE"]) else ""
                            if ll2 in ("", "nan") or lv2 in ("", "nan"):
                                continue
                            gl2 = int(lpred2["GOLES LOCAL"])
                            gv2 = int(lpred2["GOLES VISITANTE"])
                            for eq in equipos_reales:
                                if eq in {ll2, lv2} and eq not in equipos_en_bracket:
                                    equipos_en_bracket[eq] = (ll2, gl2, gv2, lv2)

                        # En caso de empate (con al menos un equipo real), buscar quién clasifica en rondas siguientes
                        clasificado = ""
                        if tiene_alguno and disp_gl == disp_gv:
                            for nid in sorted((i for i in df_jug.index if pd.notna(i) and int(i) > int(pid) and 73 <= int(i) <= 104), key=int):
                                npred = df_jug.loc[nid]
                                if "LOCAL" not in npred.index or "VISITANTE" not in npred.index:
                                    continue
                                nl = str(npred["LOCAL"]).strip() if pd.notna(npred["LOCAL"]) else ""
                                nv = str(npred["VISITANTE"]).strip() if pd.notna(npred["VISITANTE"]) else ""
                                for eq in equipos_reales:
                                    if eq in {nl, nv}:
                                        clasificado = f" (→ {eq})"
                                        break
                                if clasificado:
                                    break

                        # Equipos reales en bracket pero no en el slot mostrado → añadir resultado de ese otro cruce
                        disp_equipos = {e for e in [disp_local, disp_visit] if e and e not in ("", "nan")}
                        extras = {eq: v for eq, v in equipos_en_bracket.items() if eq not in disp_equipos}
                        if extras and not tiene_ambos:
                            partes = [f"{eq}: {v[0]} {v[1]}-{v[2]} {v[3]}" for eq, v in sorted(extras.items())]
                            nota_extras = " [también: " + " | ".join(partes) + "]"
                        else:
                            nota_extras = ""

                        if tiene_ambos:
                            html += f"<p><b>{nombre}:</b> <span style='color:#aaa'>{disp_local} {disp_gl}-{disp_gv} {disp_visit}{clasificado}</span></p>"
                        elif tiene_alguno:
                            html += f"<p><b>{nombre}:</b> <span style='color:#aaa'>{disp_local} {disp_gl}-{disp_gv} {disp_visit}{clasificado}{nota_extras}</span></p>"
                        elif equipos_en_bracket:
                            partes = [f"{eq}: {v[0]} {v[1]}-{v[2]} {v[3]}" for eq, v in sorted(equipos_en_bracket.items())]
                            html += f"<p><b>{nombre}:</b> <span style='color:#aaa'>{' | '.join(partes)}</span></p>"
                        else:
                            html += f"<p style='color:#666'><b>{nombre}:</b> &#10060;</p>"
                    else:
                        html += f"<p><b>{nombre}:</b> {gl_a}-{gv_a}</p>"

            html += "</div>"

        html += "</div>"
        secciones.append(html)

    return "\n".join(secciones)


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
        "Extras",
        "Totales"
    ]]

    html_table = df.to_html(index=False, escape=False)
    partidos_html = partidos_por_dia(maestro)

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

.pred-diff {{
    color:#00bfff;
    font-weight: bold;
}}

td:nth-child(8) {{
    color:#00ff99;
    font-weight:bold;
}}

.nav-partidos {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 15px;
}}

.nav-partidos h2 {{
    margin: 0;
    flex: 1;
    text-align: center;
}}

.nav-btn {{
    background: #333;
    color: #fff;
    border: none;
    padding: 8px 18px;
    font-size: 1.2em;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.2s;
}}

.nav-btn:hover:not(:disabled) {{
    background: #00ff99;
    color: #000;
}}

.nav-btn:disabled {{
    opacity: 0.25;
    cursor: default;
}}

</style>

</head>

<body>

<h1>🏆 Clasificación Porra Mundial</h1>

<p>Actualizado: {now}</p>

{html_table}

{partidos_html}

<script>
function cambiarDia(idx) {{
    document.querySelectorAll('.partidos').forEach(function(el) {{ el.style.display = 'none'; }});
    var el = document.getElementById('dia-' + idx);
    if (el) el.style.display = 'block';
}}
</script>

</body>
</html>
"""

    with open(HTML_SALIDA, "w", encoding="utf-8") as f:
        f.write(html)

    # 💾 guardar la clasificación de ESTA ejecución como histórico
    # para que la próxima vez la evolución se calcule correctamente
    guardar_historico(df)

    print("OK")


# ======================
# GIT AUTO
# ======================

def push_git():
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "auto update"], check=False)
        subprocess.run(["git", "push"], check=True)
        print("Git OK")
    except Exception as e:
        print(f"Git error: {e}")


if __name__ == "__main__":
    main()
    push_git()