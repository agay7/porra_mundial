"""
Tests de simulación para puntuar() en eliminatorias.
Cubre todos los casos arreglados durante el desarrollo.
"""
import pandas as pd
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r'c:\Users\34669\Desktop\Git\porra_mundial')
from script import puntuar

# ─── helpers ────────────────────────────────────────────────────────────────

def real(id, local, visitante, gl, gv):
    return {"ID": id, "LOCAL": local, "VISITANTE": visitante,
            "GOLES LOCAL": gl, "GOLES VISITANTE": gv, "JUGADO": 1}

def pred(id, local, visitante, gl, gv):
    return {"ID": id, "LOCAL": local, "VISITANTE": visitante,
            "GOLES LOCAL": gl, "GOLES VISITANTE": gv}

def run(name, real_rows, pred_rows, expected, penaltis=None):
    maestro = pd.DataFrame(real_rows)
    jugador = pd.DataFrame(pred_rows)
    total, *_ = puntuar(maestro, jugador, penaltis)
    ok = "✅" if total == expected else "❌"
    if total != expected:
        print(f"{ok} {name}: esperado={expected}, obtenido={total}")
    else:
        print(f"{ok} {name}")
    return total == expected

# ─── partido de referencia: Brasil 2-1 Japón en ID 85 ───────────────────────

R = [real(85, "Brasil", "Japón", 2, 1)]

passed = failed = 0
results = []

def t(name, pred_rows, expected, penaltis=None):
    global passed, failed
    ok = run(name, R, pred_rows, expected, penaltis)
    if ok: passed += 1
    else:  failed += 1

print("\n═══ SLOT DIRECTO: 2 EQUIPOS CORRECTOS ═══")

t("Resultado exacto → 10pts",
  [pred(85, "Brasil", "Japón", 2, 1)], 10)

t("Diferencia correcta (3-2) → 7pts",
  [pred(85, "Brasil", "Japón", 3, 2)], 7)

t("Ganador correcto (3-0) → 5pts",
  [pred(85, "Brasil", "Japón", 3, 0)], 5)

t("Ganador incorrecto (Japón gana) → 0pts",
  [pred(85, "Brasil", "Japón", 0, 1)], 0)

t("Equipos invertidos, resultado exacto → 10pts",
  [pred(85, "Japón", "Brasil", 1, 2)], 10)

t("Equipos invertidos, diferencia correcta → 7pts",
  [pred(85, "Japón", "Brasil", 2, 3)], 7)

t("Equipos invertidos, ganador correcto → 5pts",
  [pred(85, "Japón", "Brasil", 0, 3)], 5)

t("Empate + Brasil avanza en ronda posterior → 5pts",
  [pred(85, "Brasil", "Japón", 1, 1),
   pred(92, "Brasil", "Alemania", 2, 1)], 5)

t("Empate + Japón avanza en ronda posterior (no Brasil) → 0pts",
  [pred(85, "Brasil", "Japón", 1, 1),
   pred(92, "Japón", "Alemania", 2, 1)], 0)

t("Empate + nadie en ronda posterior → 0pts",
  [pred(85, "Brasil", "Japón", 1, 1)], 0)

print("\n═══ SLOT DIRECTO: 1 EQUIPO CORRECTO ═══")

t("Brasil en slot, Brasil gana (correcto) → 5pts",
  [pred(85, "Brasil", "Corea", 2, 0)], 5)

t("Brasil en slot, Corea gana (incorrecto) → 0pts",
  [pred(85, "Brasil", "Corea", 0, 1)], 0)

t("Japón en slot, Marruecos gana (incorrecto) + Brasil gana en otro cruce → 5pts  [caso Álvaro Vidal]",
  [pred(85, "Marruecos", "Japón", 3, 2),
   pred(80, "Países Bajos", "Brasil", 1, 2)], 5)

t("Japón en slot, Marruecos gana + Brasil PIERDE en otro cruce → 0pts  [caso Villardón]",
  [pred(85, "Marruecos", "Japón", 3, 2),
   pred(80, "Países Bajos", "Brasil", 2, 0)], 0)

t("Brasil en slot, empate 2-2 + Brasil aparece en ronda posterior → 5pts  [caso Raúl]",
  [pred(85, "Brasil", "Países Bajos", 2, 2),
   pred(92, "Brasil", "Noruega", 1, 2)], 5)

t("Brasil en slot, empate 2-2 + sin ronda posterior → 0pts",
  [pred(85, "Brasil", "Países Bajos", 2, 2)], 0)

t("Japón en slot (PIERDE), empate predicho + Brasil aparece pero empata (no gana) → 0pts  [caso David Cabeza]",
  [pred(85, "Marruecos", "Japón", 1, 1),
   pred(80, "Brasil", "Países Bajos", 2, 2)], 0)

t("Japón en slot (PIERDE), empate predicho + Brasil GANA en otro cruce → 5pts",
  [pred(85, "Marruecos", "Japón", 1, 1),
   pred(80, "Países Bajos", "Brasil", 1, 2)], 5)

print("\n═══ SLOT DIRECTO: 0 EQUIPOS (FALLBACK) ═══")

t("Level 2 — ambos equipos en otro slot, exacto → 10pts",
  [pred(85, "Suiza", "Chile", 3, 0),
   pred(82, "Brasil", "Japón", 2, 1)], 10)

t("Level 2 — ambos equipos en otro slot, diferencia → 7pts",
  [pred(85, "Suiza", "Chile", 3, 0),
   pred(82, "Brasil", "Japón", 3, 2)], 7)

t("Level 2 — ambos equipos en otro slot, ganador → 5pts",
  [pred(85, "Suiza", "Chile", 3, 0),
   pred(82, "Brasil", "Japón", 3, 0)], 5)

t("Level 2 — ambos equipos en otro slot, ganador incorrecto → 0pts",
  [pred(85, "Suiza", "Chile", 3, 0),
   pred(82, "Brasil", "Japón", 0, 2)], 0)

t("Brasil GANA en otro cruce → 5pts  [caso Álvaro Vidal sin equipos en slot]",
  [pred(85, "Suiza", "Chile", 3, 0),
   pred(80, "Países Bajos", "Brasil", 1, 2)], 5)

t("Brasil PIERDE en otro cruce → 0pts  [caso Jesús García / Jorge Gamero]",
  [pred(85, "Suiza", "Chile", 3, 0),
   pred(92, "Paraguay", "Brasil", 2, 1)], 0)

t("Brasil EMPATA en ronda posterior + Brasil aparece en ronda aún posterior → 5pts  [caso Javier García]",
  [pred(85, "Suiza", "Chile", 3, 0),
   pred(92, "Brasil", "Irán", 2, 2),
   pred(97, "Brasil", "Francia", 1, 0)], 5)

t("Brasil EMPATA en ronda posterior + Turquía avanza (no Brasil) → 0pts  [caso Raúl Turquía]",
  [pred(85, "Suiza", "Chile", 3, 0),
   pred(92, "Turquía", "Brasil", 1, 1),
   pred(97, "Turquía", "Francia", 2, 0)], 0)

t("Sin ningún equipo real en ningún slot → 0pts",
  [pred(85, "Suiza", "Chile", 3, 0),
   pred(82, "Argentina", "Francia", 2, 1)], 0)

print("\n═══ EMPATE REAL 1-1 + GANADOR POR PENALTIS (data/penaltis.json) ═══")

# Partido real: Alemania 1-1 Paraguay (ID 75), Paraguay gana en penaltis
RP = [real(75, "Alemania", "Paraguay", 1, 1)]
PEN = {"75": "Paraguay"}

def tp(name, pred_rows, expected, penaltis=PEN):
    global passed, failed
    ok = run(name, RP, pred_rows, expected, penaltis)
    if ok: passed += 1
    else:  failed += 1

tp("2 equipos, predice Paraguay gana 2-1 → 5pts (ganador correcto, no exacto pq 1-1 real)",
   [pred(75, "Alemania", "Paraguay", 1, 2)], 5)

tp("2 equipos, predice Alemania gana (incorrecto) → 0pts",
   [pred(75, "Alemania", "Paraguay", 2, 1)], 0)

tp("2 equipos, predice empate 1-1 exacto + Paraguay avanza en ronda posterior → 10pts (exacto)",
   [pred(75, "Alemania", "Paraguay", 1, 1),
    pred(92, "Paraguay", "Francia", 1, 0)], 10)

tp("2 equipos, predice empate 1-1 + Alemania avanza (incorrecto) → 0pts",
   [pred(75, "Alemania", "Paraguay", 1, 1),
    pred(92, "Alemania", "Francia", 1, 0)], 0)

tp("1 equipo (Paraguay en slot), Paraguay gana 2-0 (correcto) → 5pts",
   [pred(75, "Corea", "Paraguay", 0, 2)], 5)

tp("0 equipos en slot, Paraguay GANA en otro cruce → 5pts",
   [pred(75, "Suiza", "Chile", 2, 0),
    pred(80, "Países Bajos", "Paraguay", 1, 2)], 5)

tp("0 equipos en slot, Paraguay PIERDE en otro cruce → 0pts",
   [pred(75, "Suiza", "Chile", 2, 0),
    pred(80, "Francia", "Paraguay", 2, 0)], 0)

tp("Sin penaltis.json (dict vacío) → empate real no se puede puntuar, 0pts",
   [pred(75, "Alemania", "Paraguay", 1, 2)], 0, penaltis={})

print("\n═══ EMPATE PREDICHO + ACIERTA AVANCE: BONUS EXACTO/DIFERENCIA ═══")

tp("Empate EXACTO 1-1 (igual al real) + Paraguay avanza → 10pts",
   [pred(75, "Alemania", "Paraguay", 1, 1),
    pred(92, "Paraguay", "Francia", 1, 0)], 10)

tp("Empate 0-0 (diferencia 0, igual que el real 1-1) + Paraguay avanza → 7pts",
   [pred(75, "Alemania", "Paraguay", 0, 0),
    pred(92, "Paraguay", "Francia", 1, 0)], 7)

tp("Empate 3-3 (diferencia 0) + Paraguay avanza → 7pts",
   [pred(75, "Alemania", "Paraguay", 3, 3),
    pred(92, "Paraguay", "Francia", 1, 0)], 7)

tp("Empate exacto 1-1 pero NO acierta avance (Alemania avanza) → 0pts",
   [pred(75, "Alemania", "Paraguay", 1, 1),
    pred(92, "Alemania", "Francia", 1, 0)], 0)

tp("Level 2 — empate exacto 1-1 en otro slot + Paraguay avanza después → 10pts",
   [pred(75, "Suiza", "Chile", 2, 0),
    pred(82, "Alemania", "Paraguay", 1, 1),
    pred(92, "Paraguay", "Francia", 1, 0)], 10)

tp("Level 2 — empate 2-2 (diferencia 0) en otro slot + Paraguay avanza después → 7pts",
   [pred(75, "Suiza", "Chile", 2, 0),
    pred(82, "Alemania", "Paraguay", 2, 2),
    pred(92, "Paraguay", "Francia", 1, 0)], 7)

tp("Level 2 — empate en otro slot pero Paraguay NO avanza después → 0pts",
   [pred(75, "Suiza", "Chile", 2, 0),
    pred(82, "Alemania", "Paraguay", 1, 1)], 0)

print(f"\n{'═'*50}")
print(f"  Resultado: {passed} ✅  /  {failed} ❌  de {passed+failed} tests")
print(f"{'═'*50}")
