# -*- coding: utf-8 -*-
"""Generate a self-contained scrollytelling photo essay from text.docx.

Format (locked with USER):
  - Page 1: title (Arial) + scroll hint
  - Poem (定场诗): lines 1-8 as ONE block, Times New Roman, sticky fade in/stay/out
  - Introduction: intro.png first, then "Introduction" heading + body; small shot-at box with image
  - Sections 1-8: i.jpg first (with small shot-at box), then title number + body
  - Ending: "Thank you for reading."
Fonts: poem -> Times New Roman; everything else -> Arial.
"""
import zipfile, re, html

DOCX = "text.docx"
OUT = "index.html"

# ---------- read paragraphs from docx ----------
z = zipfile.ZipFile(DOCX)
from xml.etree import ElementTree as ET
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
root = ET.fromstring(z.read("word/document.xml").decode("utf-8", "ignore"))
paras = []
for p in root.iter(f"{W}p"):
    paras.append("".join(t.text or "" for t in p.iter(f"{W}t")))
texts = [t.strip() for t in paras if t.strip()]

# ---------- split into structure ----------
title = texts[0]
idx_intro = texts.index("Introduction")
poem = texts[1:idx_intro]
attr = poem[-1] if poem[-1].startswith("\u2014\u2014") else None  # ——
poem_lines = poem[:-1] if attr else poem

j = idx_intro + 1
intro_shot = None
if texts[j].startswith("("):
    intro_shot = texts[j]
    j += 1
intro_body = []
while j < len(texts) and not re.fullmatch(r"\d+", texts[j]):
    intro_body.append(texts[j])
    j += 1

sections = []
while j < len(texts):
    num = texts[j]; j += 1
    shot = texts[j] if (j < len(texts) and texts[j].startswith("(")) else None
    if shot:
        j += 1
    body = []
    while j < len(texts) and not re.fullmatch(r"\d+", texts[j]):
        body.append(texts[j]); j += 1
    sections.append((num, shot, body))

print(f"title={title!r}")
print(f"poem lines={len(poem_lines)}, attr={attr!r}")
print(f"intro shot={intro_shot!r}, body paras={len(intro_body)}")
print(f"sections={[(s[0], bool(s[1]), len(s[2])) for s in sections]}")

# ---------- html builders ----------
def esc(s):
    return html.escape(s, quote=True)

def media_scene(img, shot, heading, body, height, pe, pd):
    paras = "".join(f"<p>{esc(b)}</p>" for b in body)
    shot_html = f'<div class="shot-box">{esc(shot)}</div>' if shot else ""
    return f'''  <section class="scene scene--media" style="height:{height}vh" data-pe="{pe:.4f}" data-pd="{pd:.4f}">
    <div class="sticky">
      <div class="img-bg" style="background-image:url(\'{img}\')"></div>
      <img class="img-fg" src="{img}" alt="">
      {shot_html}
      <div class="text-box">
        <h2>{esc(heading)}</h2>
        {paras}
      </div>
    </div>
  </section>
'''

def poem_scene(lines, attr, height=300):
    body = "".join(f'<div class="pline">{esc(l)}</div>' for l in lines)
    attr_html = f'<div class="attr">{esc(attr)}</div>' if attr else ""
    return f'''  <section class="scene scene--poem" style="height:{height}vh" data-type="poem">
    <div class="sticky">
      <div class="poem" id="poem">{body}{attr_html}</div>
    </div>
  </section>
'''

HEAD = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Wanderer in the great Modern</title>
<style>
:root{
  --purple:#8b5cf6; --purple-deep:#6d28d9; --purple-soft:rgba(139,92,246,.4);
  --bg:#0d0a14; --text:#ece9f5;
}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--text);
  font-family:Arial,"PingFang SC","Microsoft YaHei",sans-serif;
  overflow-x:hidden;-webkit-font-smoothing:antialiased;}
#progress{position:fixed;top:0;left:0;height:4px;width:0;z-index:200;
  background:linear-gradient(90deg,var(--purple-deep),var(--purple));
  box-shadow:0 0 12px var(--purple-soft);}
.hero{height:100vh;display:flex;flex-direction:column;align-items:center;
  justify-content:center;text-align:center;position:relative;}
.hero h1{font-family:Arial,"PingFang SC","Microsoft YaHei",sans-serif;
  font-size:clamp(2rem,6vw,4.6rem);letter-spacing:.04em;color:#fff;
  text-shadow:0 0 26px var(--purple-soft);padding:0 1rem;}
.hero .sub{margin-top:1.1rem;color:var(--purple);opacity:.75;font-size:1rem;letter-spacing:.18em;text-transform:uppercase;}
.scroll-hint{position:absolute;bottom:6vh;color:var(--purple);opacity:.85;
  font-size:1rem;letter-spacing:.1em;animation:bob 1.8s ease-in-out infinite;}
@keyframes bob{0%,100%{transform:translateY(0)}50%{transform:translateY(9px)}}

.scene{position:relative;}
.sticky{position:sticky;top:0;height:100vh;overflow:hidden;
  display:flex;align-items:center;justify-content:center;}
.img-bg{position:absolute;inset:-12%;background-size:cover;background-position:center;
  filter:blur(28px) brightness(.55);transform:scale(1.2);}
.img-fg{position:relative;max-width:90vw;max-height:82vh;object-fit:contain;
  opacity:0;border-radius:6px;box-shadow:0 20px 60px rgba(0,0,0,.55);}
.shot-box{position:absolute;bottom:7vh;left:50%;transform:translateX(-50%);
  background:rgba(13,10,20,.5);border:1px solid var(--purple-soft);color:var(--text);
  padding:.5rem 1.15rem;border-radius:999px;font-size:.85rem;letter-spacing:.02em;
  opacity:0;backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);
  text-align:center;max-width:82vw;white-space:nowrap;}
.text-box{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%) scale(.96);
  width:min(760px,86vw);max-height:84vh;overflow:auto;
  background:rgba(20,15,32,.55);border:1px solid var(--purple-soft);border-radius:18px;
  padding:2.4rem 2.6rem;backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);
  box-shadow:0 0 40px rgba(139,92,246,.25);opacity:0;}
.text-box h2{font-family:Arial,"PingFang SC","Microsoft YaHei",sans-serif;
  color:var(--purple);font-size:1.9rem;margin-bottom:1.1rem;letter-spacing:.03em;}
.text-box p{font-size:1.02rem;line-height:1.78;margin-bottom:1rem;color:var(--text);}
.text-box p:last-child{margin-bottom:0;}

.poem{font-family:"Times New Roman","PingFang SC","Microsoft YaHei",serif;
  font-size:clamp(1.1rem,2.4vw,1.7rem);line-height:2;color:var(--text);
  text-align:center;max-width:min(720px,86vw);opacity:0;
  text-shadow:0 0 18px rgba(0,0,0,.6);}
.poem .pline{margin:.1rem 0;}
.poem .attr{margin-top:1.4rem;font-style:italic;opacity:.82;font-size:.92em;}

.end{height:100vh;display:flex;align-items:center;justify-content:center;
  font-size:clamp(1.4rem,3vw,2.4rem);color:var(--purple);letter-spacing:.06em;
  text-align:center;padding:0 1rem;}
</style>
</head>
<body>
<div id="progress"></div>
<header class="hero">
  <h1>__TITLE__</h1>
  <div class="sub">a photo essay</div>
  <div class="scroll-hint">&#8595; scroll down</div>
</header>
'''.replace("__TITLE__", esc(title))

# poem scene (text-only, no image dwell to preserve -> can be lean)
poem_html = poem_scene(poem_lines, attr, height=220)

def budget(n):
    # keep image phase (fade-in + pure dwell) absolute vh == original (0.54*oldH)
    oldH = 380 + n * 42
    FADE = 0.16 * oldH
    DWELL = 0.38 * oldH
    TEXT = 100 + n * 20          # lean reading budget -> drives sensitivity up
    H = round(FADE + DWELL + TEXT)
    pe = FADE / H
    pd = (FADE + DWELL) / H
    return H, pe, pd

# intro scene
intro_H, intro_pe, intro_pd = budget(len(intro_body))
intro_html = media_scene("photos/intro.png", intro_shot, "Introduction", intro_body, intro_H, intro_pe, intro_pd)

# section scenes
media_html = ""
for num, shot, body in sections:
    H, pe, pd = budget(len(body))
    media_html += media_scene(f"photos/{num}.jpg", shot, num, body, H, pe, pd)

END = '''<footer class="end">Thank you for reading.</footer>
'''

SCRIPT = '''<script>
(function(){
  var scenes=[].slice.call(document.querySelectorAll('.scene'));
  var progress=document.getElementById('progress');
  function clamp(x,a,b){return Math.max(a,Math.min(b,x));}
  var ticking=false;
  function update(){
    ticking=false;
    var vh=window.innerHeight;
    for(var i=0;i<scenes.length;i++){
      var sc=scenes[i];
      var r=sc.getBoundingClientRect();
      var total=r.height-vh;
      var p=clamp(-r.top/total,0,1);
      if(sc.getAttribute('data-type')==='poem'){
        var el=sc.querySelector('.poem');
        var o=clamp(p/0.18,0,1)*(1-clamp((p-0.70)/0.25,0,1));
        el.style.opacity=o;
        continue;
      }
      var fg=sc.querySelector('.img-fg');
      var shot=sc.querySelector('.shot-box');
      var tb=sc.querySelector('.text-box');
      var pe=parseFloat(sc.getAttribute('data-pe'))||0.16;
      var pd=parseFloat(sc.getAttribute('data-pd'))||0.54;
      var fin=clamp(p/pe,0,1);
      fg.style.opacity=fin;
      var sh=clamp((p/pe-0.15)/0.85,0,1);
      fg.style.filter='blur('+(16*(1-sh)).toFixed(2)+'px)';
      if(shot){
        var sin=clamp((p-pe)/0.03,0,1);
        var sout=clamp((p-(pd-0.03))/0.03,0,1);
        shot.style.opacity=sin*(1-sout);
      }
      var tin=clamp((p-pd)/0.06,0,1);
      tb.style.opacity=tin;
      tb.style.transform='translate(-50%,-50%) scale('+(0.96+0.04*tin).toFixed(3)+')';
    }
    var doc=document.documentElement;
    var denom=(doc.scrollHeight-vh)||1;
    var sp=clamp(window.scrollY/denom,0,1);
    progress.style.width=(sp*100)+'%';
  }
  function onScroll(){ if(!ticking){ ticking=true; requestAnimationFrame(update); } }
  window.addEventListener('scroll',onScroll,{passive:true});
  window.addEventListener('resize',update);
  update();
})();
</script>
</body>
</html>
'''

html_out = HEAD + poem_html + intro_html + media_html + END + SCRIPT
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html_out)
print("wrote", OUT, "bytes=", len(html_out))
