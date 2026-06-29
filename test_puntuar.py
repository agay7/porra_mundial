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

def run(name, real_rows, pred_rows, expected):
    maestro = pd.DataFrame(real_rows)
    jugador = pd.DataFrame(pred_rows)
    total, *_ = puntuar(maestro, jugador)
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

def t(name, pred_rows, expected):
    global passed, failed
    ok = run(name, R, pred_rows, expected)
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

print(f"\n{'═'*50}")
print(f"  Resultado: {passed} ✅  /  {failed} ❌  de {passed+failed} tests")
print(f"{'═'*50}")
