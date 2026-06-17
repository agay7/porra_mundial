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
# PUNTOS
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

        puntos = puntos_partido(real, fila.iloc[0])
        total += puntos

        if puntos == 5: e += 1
        elif puntos == 3: d += 1
        elif puntos == 1: g += 1

    return total, g, d, e


def contar_partidos_jugados(maestro):
    return int((maestro["JUGADO"] == 1).sum())


# ======================
# HISTÓRICO CORRECTO
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

    md = hist.get("md", [])
    players = {p[0]: p for p in hist.get("players", [])}

    if md and md[-1] == partidos_jugados:
        for nombre, pts in totales.items():
            if nombre in players:
                players[nombre][1][-1] = pts
            else:
                players[nombre] = [nombre, [None]*(len(md)-1) + [pts]]

    else:
        md.append(partidos_jugados)
        n = len(md)

        for nombre, pts in totales.items():
            if nombre in players:
                arr = players[nombre][1]
                while len(arr) < n-1:
                    arr.append(arr[-1] if arr else None)
                arr.append(pts)
            else:
                players[nombre] = [nombre, [None]*(n-1) + [pts]]

        for p in players.values():
            if len(p[1]) < n:
                p[1].append(p[1][-1] if p[1] else None)

    plist = sorted(players.values(), key=lambda p: -(p[1][-1] or 0))

    hist = {"md": md, "players": plist}

    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False)

    return hist


# ======================
# CSS + GRÁFICA PRO (IMPORTANTE)
# ======================
PAGE_CSS = """
body { background:#111; color:white; font-family:Arial; text-align:center; }

table { margin:auto; border-collapse:collapse; }
th, td { padding:10px; border-bottom:1px solid #444; }

tbody tr:nth-of-type(1) { background:gold; color:black; }
tbody tr:nth-of-type(2) { background:silver; color:black; }
tbody tr:nth-of-type(3) { background:#cd7f32; color:black; }

tbody tr:nth-of-type(n+4) td:last-child { color:#00ffcc; }

.evo { max-width:1000px; margin:40px auto; }
.legend { margin-top:20px; }
"""

CHART_BLOCK = """
<div class="evo">
<h2>📈 Evolución</h2>
<svg id="evoSvg" viewBox="0 0 900 500"></svg>

<script>
(function(){

const DATA = __EMBED__;
const svg = document.getElementById("evoSvg");

const players = DATA.players;
const md = DATA.md;

const W = 900;
const H = 500;

const maxPts = Math.max(...players.flatMap(p => p[1]));

function X(i) {
  return 50 + (i / (md.length-1)) * (W-100);
}

function Y(p) {
  return H - 50 - (p/maxPts)*(H-100);
}

// grid
for(let g=0; g<=maxPts; g+=5){
  const y = Y(g);
  const line = document.createElementNS("http://www.w3.org/2000/svg","line");
  line.setAttribute("x1", 50);
  line.setAttribute("x2", W-20);
  line.setAttribute("y1", y);
  line.setAttribute("y2", y);
  line.setAttribute("stroke", "#333");
  svg.appendChild(line);
}

// lineas
players.forEach((p,i) => {

  const color = i==0?"gold":i==1?"silver":i==2?"#cd7f32":"hsl("+(i*35%360)+",70%,60%)";

  let d="";

  p[1].forEach((pts,j)=>{
    const x = X(j);
    const y = Y(pts);
    d += (j==0?"M":"L")+x+" "+y+" ";

    const c = document.createElementNS("http://www.w3.org/2000/svg","circle");
    c.setAttribute("cx",x);
    c.setAttribute("cy",y);
    c.setAttribute("r",3);
    c.setAttribute("fill",color);
    svg.appendChild(c);
  });

  const path = document.createElementNS("http://www.w3.org/2000/svg","path");
  path.setAttribute("d",d);
  path.setAttribute("stroke",color);
  path.setAttribute("stroke-width",2);
  path.setAttribute("fill","none");
  svg.appendChild(path);

});

// jornadas
md.forEach((m,i)=>{
  const x = X(i);
  const t = document.createElementNS("http://www.w3.org/2000/svg","text");
  t.setAttribute("x",x);
  t.setAttribute("y",H-10);
  t.setAttribute("fill","#aaa");
  t.setAttribute("font-size",10);
  t.setAttribute("text-anchor","middle");
  t.textContent=m;
  svg.appendChild(t);
});

})();
</script>

</div>
"""


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
    df.insert(0, "Posición", range(1, len(df)+1))

    if os.path.exists(SALIDA):
        old = pd.read_excel(SALIDA)
        pos_old = dict(zip(old["Participante"], old["Posición"]))

        mov = []
        for _, r in df.iterrows():
            if r["Participante"] not in pos_old:
                mov.append("🆕")
            else:
                diff = pos_old[r["Participante"]] - r["Posición"]
                mov.append("↑" if diff>0 else "↓" if diff<0 else "=")

        df.insert(1, "Mov", mov)

    df.to_excel(SALIDA, index=False)

    hist = actualizar_historico(df, partidos_jugados)

    html_table = df.to_html(index=False, escape=False)

    chart_html = CHART_BLOCK.replace("__EMBED__", json.dumps(hist, ensure_ascii=False))

    now = datetime.now().strftime("%d/%m %H:%M:%S")

    html = f"""
<html>
<head>
<style>{PAGE_CSS}</style>
</head>

<body>

<h1>🏆 Porra Mundial</h1>
<p>Actualizado: {now}</p>
<p>Partidos: {partidos_jugados}</p>

{html_table}

{chart_html}

</body>
</html>
"""

    html += f"\n<!-- {datetime.now().timestamp()} -->"

    with open(HTML_SALIDA, "w", encoding="utf-8") as f:
        f.write(html)

    os.system("git add .")
    os.system(f'git commit -m "update {now}"')
    os.system("git push")

    print("✅ TODO OK - gráfico pro activo")


if __name__ == "__main__":
    main()