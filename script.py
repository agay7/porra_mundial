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
# MAIN
# ======================

PAGE_CSS = r"""
* { box-sizing: border-box; }
body { background:#111; color:#fff; font-family:Arial, Helvetica, sans-serif; text-align:center; margin:0; padding:0 12px 60px; }
h1 { margin-top:24px; }
table { margin:20px auto; border-collapse:collapse; }
th, td { padding:10px; border-bottom:1px solid #444; }
th { background:#222; }
tbody tr:nth-child(even) { background:#1a1a1a; }
tbody tr:nth-of-type(1) { background:gold; color:#000; font-weight:bold; }
tbody tr:nth-of-type(2) { background:silver; color:#000; font-weight:bold; }
tbody tr:nth-of-type(3) { background:#cd7f32; color:#000; font-weight:bold; }
tbody tr:nth-of-type(n+4) td:last-child { font-weight:bold; color:#00ffcc; }

/* ---- grafica de evolucion ---- */
.evo { max-width:1000px; margin:50px auto 0; }
.evo h2 { color:#fff; margin-bottom:4px; }
.evo .sub { color:#888; font-size:13px; margin:0 0 14px; }
.evo .controls { display:flex; gap:8px; justify-content:center; flex-wrap:wrap; margin-bottom:12px; }
.evo button { background:#222; color:#ccc; border:1px solid #444; border-radius:6px; padding:7px 16px; cursor:pointer; font-family:inherit; font-size:13px; }
.evo button.on { background:#00ffcc; color:#111; border-color:#00ffcc; font-weight:bold; }
.evo button.ghost { color:#888; }
.evo .chartwrap { background:#1a1a1a; border:1px solid #444; border-radius:10px; padding:8px 6px 2px; position:relative; }
.evo svg { width:100%; height:auto; display:block; touch-action:pan-y; }
.evo .legend { display:flex; flex-wrap:wrap; gap:6px; justify-content:center; margin-top:16px; }
.evo .chip { display:flex; align-items:center; gap:7px; background:#222; border:1px solid #333; border-radius:20px; padding:5px 11px; cursor:pointer; font-size:12.5px; user-select:none; transition:opacity .12s; }
.evo .chip:hover { border-color:#666; }
.evo .chip .sw { width:11px; height:11px; border-radius:50%; flex:0 0 auto; }
.evo .chip .pn { color:#fff; }
.evo .chip .pp { color:#888; font-weight:bold; }
.evo .chip.off { opacity:.4; text-decoration:line-through; }
.evo .tip { position:absolute; pointer-events:none; background:#000; border:1px solid #00ffcc; border-radius:6px; padding:5px 9px; font-size:12px; opacity:0; transition:opacity .1s; white-space:nowrap; z-index:5; }
.evo .hint { color:#777; font-size:12px; margin-top:10px; }
"""

CHART_BLOCK = r"""
<div class="evo">
  <h2>📈 Evolución de la clasificación</h2>
  <p class="sub">Pulsa un nombre para ocultar o mostrar su línea</p>
  <div class="controls" id="evoCtrl">
    <button data-mode="pts" class="on">Puntos</button>
    <button data-mode="rank">Posición</button>
    <button id="evoAll" class="ghost">Mostrar todos</button>
    <button id="evoNone" class="ghost">Ocultar todos</button>
  </div>
  <div class="chartwrap" id="evoWrap">
    <svg id="evoSvg" viewBox="0 0 900 520" preserveAspectRatio="xMidYMid meet"></svg>
    <div class="tip" id="evoTip"></div>
  </div>
  <div class="legend" id="evoLegend"></div>
  <p class="hint">Top 3 en oro · plata · bronce. El resto, un color por persona.</p>
</div>
<script>
(function(){
  const EMBED = __EMBED__;
  const PODIUM = ["#FFD700","#C0C0C0","#CD7F32"];
  const PAL = ["#36e0b0","#56a8ff","#ff7eb6","#c79bff","#8ee65a","#ffa24d","#4fd6e6","#ff9bcb","#a9e34b","#b394ff","#39d3e0","#ffc14d","#8ea2ff","#7bd88f","#d6a0ff","#5bc8ff","#ff8a80","#c0e060","#74b9ff","#ff85b3","#7fe0d4","#e0e060","#aab4bd","#cdb0ff"];
  const norm = s => s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[_\s]+/g,' ').trim().toLowerCase();

  let MD = EMBED.md.slice();
  let players = EMBED.players.map(p=>({name:p[0], pts:p[1].slice()}));

  // ---- fusionar con la tabla de esta misma pagina (ultima jornada) ----
  try{
    const t = document.querySelector('table');
    if(t){
      const heads=[...t.querySelectorAll('thead th, thead td')].map(x=>norm(x.textContent));
      let iN=heads.indexOf('participante'); if(iN<0) iN=2;
      let iT=heads.indexOf('totales'); if(iT<0) iT=heads.length-1;
      const tot={};
      t.querySelectorAll('tbody tr').forEach(tr=>{const c=tr.querySelectorAll('td');
        if(c.length>iT){const n=c[iN].textContent.trim(); const p=parseInt(c[iT].textContent.trim(),10);
          if(n && !isNaN(p)) tot[norm(n)]={name:n,pts:p};}});
      const mm=(document.body.textContent.match(/Partidos?\s+jugados?\s*:?\s*(\d+)/i));
      const liveMd = mm?parseInt(mm[1],10):null;
      if(liveMd && Object.keys(tot).length){
        const by={}; players.forEach(p=>by[norm(p.name)]=p);
        if(MD[MD.length-1]===liveMd){
          players.forEach(p=>{const l=tot[norm(p.name)]; if(l) p.pts[p.pts.length-1]=l.pts;});
        } else if(liveMd>MD[MD.length-1]){
          MD.push(liveMd);
          players.forEach(p=>{const l=tot[norm(p.name)]; p.pts.push(l?l.pts:p.pts[p.pts.length-1]);});
          Object.values(tot).forEach(l=>{ if(!by[norm(l.name)]){const a=new Array(MD.length-1).fill(null);a.push(l.pts);players.push({name:l.name,pts:a});}});
        }
      }
    }
  }catch(e){}

  // ---- orden por total actual (fijo, no se mueve al ocultar) ----
  const last = MD.length-1;
  players.sort((a,b)=>(b.pts[last]||0)-(a.pts[last]||0));
  const DATA = players.map((p,i)=>({name:p.name, pts:p.pts, color:i<3?PODIUM[i]:PAL[(i-3)%PAL.length]}));
  const N = DATA.length;
  const maxPts = Math.max(1,...DATA.map(d=>Math.max(...d.pts.filter(v=>v!=null))));
  const minMD=MD[0], maxMD=MD[MD.length-1];
  const ranks = MD.map((_,s)=>{const arr=DATA.map((d,i)=>({i,p:d.pts[s]==null?-1:d.pts[s]})).sort((a,b)=>b.p-a.p);const r={};arr.forEach((o,k)=>r[o.i]=k+1);return r;});

  const NS="http://www.w3.org/2000/svg";
  const W=900,H=520,M={t:20,r:24,b:38,l:42}, ix=W-M.l-M.r, iy=H-M.t-M.b;
  const X=md=>M.l+(md-minMD)/Math.max(1,maxMD-minMD)*ix;
  const Yp=p=>M.t+iy-(p/maxPts)*iy;
  const Yr=r=>M.t+((r-1)/Math.max(1,N-1))*iy;
  const el=(t,a)=>{const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);return e;};

  const svg=document.getElementById('evoSvg');
  const legend=document.getElementById('evoLegend');
  const tip=document.getElementById('evoTip');
  const wrap=document.getElementById('evoWrap');
  let mode='pts', hidden=new Set(), hover=null;

  function draw(){
    svg.innerHTML="";
    if(mode==='pts'){
      const step=maxPts>30?10:5;
      for(let g=0;g<=maxPts;g+=step){const y=Yp(g);
        svg.appendChild(el('line',{x1:M.l,y1:y,x2:W-M.r,y2:y,stroke:'#333','stroke-width':1}));
        svg.appendChild(el('text',{x:M.l-7,y:y+4,fill:'#888','font-size':11,'text-anchor':'end','font-family':'Arial'})).textContent=g;}
    } else {
      [1,5,10,15,20,N].forEach(r=>{const y=Yr(r);
        svg.appendChild(el('line',{x1:M.l,y1:y,x2:W-M.r,y2:y,stroke:'#333','stroke-width':1}));
        svg.appendChild(el('text',{x:M.l-7,y:y+4,fill:'#888','font-size':11,'text-anchor':'end','font-family':'Arial'})).textContent=r+'º';});
    }
    MD.forEach(md=>svg.appendChild(el('text',{x:X(md),y:H-15,fill:'#888','font-size':11,'text-anchor':'middle','font-family':'Arial'})).textContent=md);
    svg.appendChild(el('text',{x:M.l+ix/2,y:H-2,fill:'#666','font-size':10,'text-anchor':'middle','font-family':'Arial','letter-spacing':2})).textContent='JORNADA';

    const order=DATA.map((_,i)=>i).filter(i=>!hidden.has(i)).sort((a,b)=>{
      const aa=a===hover,ab=b===hover; if(aa!==ab) return aa?1:-1;
      return ranks[last][b]-ranks[last][a];});

    order.forEach(i=>{
      const d=DATA[i], isH=hover===i, anyH=hover!==null, lead=i<3;
      let p="";
      MD.forEach((md,s)=>{ if(d.pts[s]==null) return;
        const x=X(md), y=mode==='pts'?Yp(d.pts[s]):Yr(ranks[s][i]);
        p+=(p?"L":"M")+x.toFixed(1)+" "+y.toFixed(1)+" ";});
      const op=anyH?(isH?1:.12):(lead?.95:.62);
      const w=isH?4:(lead?3:1.7);
      const path=el('path',{d:p,fill:'none',stroke:d.color,'stroke-width':w,'stroke-linejoin':'round','stroke-linecap':'round',opacity:op});
      path.style.cursor='pointer';
      path.addEventListener('mouseenter',()=>{hover=i;draw();});
      path.addEventListener('mouseleave',()=>{hover=null;draw();});
      svg.appendChild(path);
      if(isH){
        MD.forEach((md,s)=>{ if(d.pts[s]==null) return;
          const x=X(md), y=mode==='pts'?Yp(d.pts[s]):Yr(ranks[s][i]);
          const c=el('circle',{cx:x,cy:y,r:3.4,fill:'#111',stroke:d.color,'stroke-width':2.2});
          c.addEventListener('mousemove',ev=>showTip(ev,d.name,mode==='pts'?d.pts[s]+' pts':ranks[s][i]+'º',md));
          c.addEventListener('mouseleave',hideTip); svg.appendChild(c);});
        let ls=MD.length-1; while(ls>0&&d.pts[ls]==null) ls--;
        const lx=X(MD[ls]), ly=mode==='pts'?Yp(d.pts[ls]):Yr(ranks[ls][i]);
        svg.appendChild(el('text',{x:lx-6,y:ly-8,fill:d.color,'font-size':12,'text-anchor':'end','font-family':'Arial','font-weight':'bold'})).textContent=d.name;
      }
    });
  }
  function showTip(ev,name,val,md){const r=wrap.getBoundingClientRect();
    tip.innerHTML=name+' · J'+md+' · <b style="color:#00ffcc">'+val+'</b>';
    tip.style.left=(ev.clientX-r.left+12)+'px'; tip.style.top=(ev.clientY-r.top-10)+'px'; tip.style.opacity=1;}
  function hideTip(){tip.style.opacity=0;}

  function buildLegend(){
    legend.innerHTML="";
    DATA.forEach((d,i)=>{
      const last2=d.pts.filter(v=>v!=null).slice(-1)[0];
      const chip=document.createElement('div'); chip.className='chip'+(hidden.has(i)?' off':'');
      chip.innerHTML='<span class="sw" style="background:'+d.color+'"></span><span class="pn">'+(i+1)+'. '+d.name+'</span><span class="pp">'+last2+'</span>';
      chip.addEventListener('click',()=>{ if(hidden.has(i)) hidden.delete(i); else hidden.add(i); chip.classList.toggle('off'); hover=null; draw(); });
      chip.addEventListener('mouseenter',()=>{ if(!hidden.has(i)){hover=i;draw();} });
      chip.addEventListener('mouseleave',()=>{ hover=null; draw(); });
      legend.appendChild(chip);
    });
  }
  document.getElementById('evoCtrl').addEventListener('click',e=>{
    if(e.target.dataset.mode){ mode=e.target.dataset.mode;
      document.querySelectorAll('#evoCtrl [data-mode]').forEach(b=>b.classList.toggle('on',b===e.target)); draw(); }
  });
  document.getElementById('evoAll').addEventListener('click',()=>{hidden.clear();buildLegend();draw();});
  document.getElementById('evoNone').addEventListener('click',()=>{hidden=new Set(DATA.map((_,i)=>i));buildLegend();draw();});

  buildLegend(); draw();
})();
</script>
"""


def _nfc(s):
    return unicodedata.normalize("NFC", str(s))


def actualizar_historico(df, partidos_jugados, ruta="historico.json"):
    """Vuelca la clasificacion a historico.json. Normaliza tildes (NFC) para no duplicar."""
    totales = {_nfc(r["Participante"]).replace("_", " ").strip(): int(r["Totales"])
               for _, r in df.iterrows()}
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            raw = json.load(f)
    else:
        raw = {"md": [], "players": []}
    md = raw.get("md", [])
    # cargar jugadores fusionando posibles duplicados NFC/NFD ya existentes
    players = {}
    for p in raw.get("players", []):
        nm = _nfc(p[0]); arr = list(p[1])
        if nm in players:
            a = players[nm][1]; n = max(len(a), len(arr)); merged = []
            for i in range(n):
                av = a[i] if i < len(a) else None
                bv = arr[i] if i < len(arr) else None
                merged.append(bv if bv is not None else av)
            players[nm][1] = merged
        else:
            players[nm] = [nm, arr]
    if md and md[-1] == partidos_jugados:
        n = len(md)
        for nombre, pts in totales.items():
            if nombre in players: players[nombre][1][-1] = pts
            else: players[nombre] = [nombre, [None]*(n-1) + [pts]]
    else:
        md.append(partidos_jugados); n = len(md)
        for nombre, pts in totales.items():
            if nombre in players:
                arr = players[nombre][1]
                while len(arr) < n-1: arr.append(arr[-1] if arr else None)
                arr.append(pts)
            else: players[nombre] = [nombre, [None]*(n-1) + [pts]]
        for p in players.values():
            if len(p[1]) < n: p[1].append(p[1][-1] if p[1] else None)
    plist = sorted(players.values(), key=lambda p: -(p[1][-1] or 0))
    hist = {"md": md, "players": plist}
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False)
    print("✅ historico.json actualizado")
    return hist


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

    # ======================
    # DATAFRAME
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

            nombre = fila["Participante"]
            pos = fila["Posición"]

            if nombre not in posiciones_antiguas:
                movimientos.append("🆕")
                continue

            diff = posiciones_antiguas[nombre] - pos

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
    # HISTORICO (para la grafica)
    # ======================
    hist = actualizar_historico(df, partidos_jugados)

    # ======================
    # HTML (tabla + grafica)
    # ======================
    def formato_mov(val):
        if "↑" in str(val): return f'<span style="color:#00ff00">{val}</span>'
        elif "↓" in str(val): return f'<span style="color:#ff4d4d">{val}</span>'
        return val

    if "Mov" in df.columns:
        df["Mov"] = df["Mov"].apply(formato_mov)

    html_table = df.to_html(index=False, escape=False)
    now = datetime.now().strftime("%d/%m %H:%M:%S")
    chart_html = CHART_BLOCK.replace("__EMBED__", json.dumps(hist, ensure_ascii=False))

    html = (
        "<!DOCTYPE html><html lang='es'><head><meta charset='UTF-8'>"
        "<meta http-equiv='Cache-Control' content='no-cache, no-store, must-revalidate'>"
        "<meta http-equiv='Pragma' content='no-cache'><meta http-equiv='Expires' content='0'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>"
        "<title>Porra Mundial</title><style>" + PAGE_CSS + "</style></head><body>"
        "<h1>🏆 Clasificación Porra Mundial</h1>"
        f"<p>Actualizado: {now}</p>"
        f"<p>Partidos jugados: {partidos_jugados} / 104</p>"
        + html_table
        + chart_html
        + "</body></html>"
        + f"\n<!-- update {datetime.now().timestamp()} -->"
    )

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
