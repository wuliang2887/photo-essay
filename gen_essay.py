# -*- coding: utf-8 -*-
"""Generate a self-contained scrollytelling photo essay from text.docx.

Format (locked with USER):
  - Page 1: title (Arial) + scroll hint
  - Poem (定场诗): lines 1-8 as ONE block, Times New Roman, sticky fade in/stay/out
  - Introduction: intro.png first, then "Introduction" heading + body; small shot-at box with image
  - Sections 1-8: i.jpg first (with small shot-at box), then title number + body
  - Ending: "Thank you for reading."
Fonts: poem -> Times New Roman; everything else -> Arial.

Interaction model (locked 2026-10-19, revised):
  - Each media scene (Introduction + 1-8) is split into TWO quantized stages
    separated at scroll fraction pd:
      * IMAGE stage (p in [0, pd]): blur fade-in -> sharp -> short dwell.
        The image collapses (收起) early as the user scrolls down: the locked
        dwell is kept short so the cut to text happens soon after the image
        appears. Small "shot at" box travels with the image.
      * At p == pd: HARD CUT to TEXT stage (no scroll-scrubbed crossfade),
        followed by a short (~0.3s) spring: text bounces in from the right and
        fills the screen, image slides off the left.
      * TEXT stage (p in [pd, 1]): a frosted purple-bordered panel, left-aligned,
        larger font.
      * Scroll up across pd reverses (image back from left, text out right).
  - Left drawer trigger: a tab on the left edge, visible ONLY in the TEXT stage
    (i.e. after the text has popped out). Click -> the current scene's photo
    slides in from the left (~65vw), and the page text dims behind a scrim.
    Click scrim/photo to close.
  - Poem, cover and ending are unchanged.
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
        <div class="panel">
          <h2>{esc(heading)}</h2>
          {paras}
        </div>
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
  --fs:1; /* auto-fit text scale: largest value at which every panel fits 1 screen */
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
  filter:blur(28px) brightness(.55);transform:scale(1.2);
  transition:opacity .26s ease;}
.img-fg{position:relative;max-width:90vw;max-height:82vh;object-fit:contain;
  opacity:0;border-radius:6px;box-shadow:0 20px 60px rgba(0,0,0,.55);
  transition:transform .30s cubic-bezier(.25,.8,.25,1);}
.shot-box{position:absolute;bottom:7vh;left:50%;transform:translateX(-50%);
  background:rgba(13,10,20,.5);border:1px solid var(--purple-soft);color:var(--text);
  padding:.5rem 1.15rem;border-radius:999px;font-size:.95rem;letter-spacing:.02em;
  opacity:0;backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);
  text-align:center;max-width:82vw;white-space:nowrap;z-index:6;
  transition:opacity .2s ease;}

/* TEXT STAGE: frosted panel parked off the right until stage-text, left-aligned.
   No inner scroll (overflow:hidden) and the panel is sized so every section fits
   on one screen: font scales with viewport height (vh), so no vertical movement
   of the text is needed once it appears. */
.text-box{position:absolute;inset:0;left:0;top:0;width:100%;height:100%;
  display:flex;align-items:flex-start;justify-content:center;
  padding:4vh 5vw;overflow:hidden;background:transparent;
  transform:translateX(102%);opacity:0;pointer-events:none;z-index:5;
  transition:transform .30s cubic-bezier(.25,.8,.25,1),opacity .18s ease;}
.text-box .panel{width:100%;max-width:780px;
  background:rgba(13,10,20,.78);border:1px solid var(--purple-soft);
  border-radius:14px;
  padding:calc(1.5rem * var(--fs)) calc(2rem * var(--fs));
  box-shadow:0 0 46px rgba(139,92,246,.16);
  backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
  text-align:left;will-change:transform;}
.text-box h2{font-family:Arial,"PingFang SC","Microsoft YaHei",sans-serif;
  color:var(--purple);font-size:calc(2.2rem * var(--fs));
  margin-bottom:calc(.55rem * var(--fs));
  letter-spacing:.03em;text-align:left;}
.text-box p{font-size:calc(1.5rem * var(--fs));line-height:1.55;
  margin-bottom:calc(.62rem * var(--fs));color:var(--text);text-align:left;}
.text-box p:last-child{margin-bottom:0;}

/* STAGE-TEXT state: hard cut at pd + short bounce-in (no scroll-scrubbed blend) */
.scene--media.stage-text .img-bg{opacity:0;}
.scene--media.stage-text .img-fg{transform:translateX(-110vw) scale(.92);}
.scene--media.stage-text .shot-box{opacity:0 !important;pointer-events:none;}
.scene--media.stage-text .text-box{transform:translateX(0);opacity:1;pointer-events:auto;}

.poem{font-family:"Times New Roman","PingFang SC","Microsoft YaHei",serif;
  font-size:clamp(1.1rem,2.4vw,1.7rem);line-height:2;color:var(--text);
  text-align:center;max-width:min(720px,86vw);opacity:0;
  text-shadow:0 0 18px rgba(0,0,0,.6);}
.poem .pline{margin:.1rem 0;}
.poem .attr{margin-top:1.4rem;font-style:italic;opacity:.82;font-size:.92em;}

.end{height:100vh;display:flex;align-items:center;justify-content:center;
  font-size:clamp(1.4rem,3vw,2.4rem);color:var(--purple);letter-spacing:.06em;
  text-align:center;padding:0 1rem;}

/* LEFT DRAWER TRIGGER */
#drawerTab{position:fixed;left:0;top:50%;transform:translateY(-50%);
  width:34px;height:88px;background:var(--purple);color:#fff;cursor:pointer;
  display:flex;align-items:center;justify-content:center;font-size:1.5rem;
  border-radius:0 12px 12px 0;z-index:50;user-select:none;
  box-shadow:0 0 18px var(--purple-soft);transition:opacity .2s ease;}
#drawerTab.hidden{opacity:0;pointer-events:none;}
#drawer{position:fixed;left:0;top:0;height:100vh;width:65vw;max-width:880px;
  background:#0a0710;transform:translateX(-100%);
  transition:transform .32s cubic-bezier(.2,.8,.2,1.04);z-index:60;
  display:flex;align-items:center;justify-content:center;padding:3vh 2vw;
  box-shadow:0 0 60px rgba(0,0,0,.6);}
#drawer.open{transform:translateX(0);}
#drawer img{max-width:100%;max-height:94vh;object-fit:contain;border-radius:6px;cursor:pointer;}
#drawerScrim{position:fixed;inset:0;background:rgba(0,0,0,.55);
  opacity:0;pointer-events:none;transition:opacity .25s ease;z-index:55;}
#drawerScrim.open{opacity:1;pointer-events:auto;}
</style>
</head>
<body>
<div id="progress"></div>
<div id="drawerTab" class="hidden">&#8250;</div>
<div id="drawer"><img id="drawerImg" src="" alt=""></div>
<div id="drawerScrim"></div>
<header class="hero">
  <h1>__TITLE__</h1>
  <div class="sub">a photo essay</div>
  <div class="scroll-hint">&#8595; scroll down</div>
</header>
'''.replace("__TITLE__", esc(title))

# poem scene (text-only, no image dwell to preserve -> can be lean)
poem_html = poem_scene(poem_lines, attr, height=220)

def budget(n):
    # image fades in then collapses as the user scrolls down; the text stage is
    # now only 1/5 of its former length so a reader is not "stuck" on a pinned
    # screen -> scrolling right after the text appears moves on promptly.
    oldH = 380 + n * 42
    FADE = 0.16 * oldH
    DWELL = 0.22 * oldH
    TEXT = (100 + n * 20) * 0.2   # text hold = 1/5 of the old budget
    H = round(FADE + DWELL + TEXT)
    pe = FADE / H
    pd = (FADE + DWELL) / H      # = cut point between IMAGE stage and TEXT stage
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
  var drawerTab=document.getElementById('drawerTab');
  var drawer=document.getElementById('drawer');
  var drawerImg=document.getElementById('drawerImg');
  var drawerScrim=document.getElementById('drawerScrim');
  function clamp(x,a,b){return Math.max(a,Math.min(b,x));}
  function activeScene(){
    var vh=window.innerHeight;
    for(var i=0;i<scenes.length;i++){
      var r=scenes[i].getBoundingClientRect();
      if(r.top<=1 && r.bottom>=vh-1) return scenes[i];
    }
    return null;
  }
  function closeDrawer(){ drawer.classList.remove('open'); drawerScrim.classList.remove('open'); }
  drawerTab.addEventListener('click',function(){
    var act=activeScene(); if(!act) return;
    var img=act.querySelector('.img-fg');
    if(img) drawerImg.src=img.getAttribute('src');
    drawer.classList.add('open'); drawerScrim.classList.add('open');
  });
  drawerScrim.addEventListener('click',closeDrawer);
  drawerImg.addEventListener('click',closeDrawer);
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
      var pe=parseFloat(sc.getAttribute('data-pe'))||0.16;
      var pd=parseFloat(sc.getAttribute('data-pd'))||0.54;
      var isText = p>=pd;
      // only the image stage needs per-frame fade/blur work; skip it in the text
      // stage to avoid needless style recalcs (helps keep scrolling smooth)
      if(!isText){
        var fin=clamp(p/pe,0,1);
        fg.style.opacity=fin;
        var sh=clamp((p/pe-0.15)/0.85,0,1);
        fg.style.filter='blur('+(16*(1-sh)).toFixed(2)+'px)';
        if(shot){
          var sin=clamp((p-pe)/0.03,0,1);
          var sout=clamp((p-(pd-0.03))/0.03,0,1);
          shot.style.opacity=sin*(1-sout);
        }
      }
      // quantized stage flip at pd (discrete state -> CSS spring does the motion)
      if(isText){ sc.classList.add('stage-text'); }
      else { sc.classList.remove('stage-text'); }
      // the panel is sized to fit; keep it still (no vertical slide of the text).
      // cached viewport budget -> no per-frame layout reads.
      var panel=sc.querySelector('.panel');
      if(panel && isText){
        var avail=viewAvail;
        var ph=panel._h||0;
        var ty = ph<=avail ? ((avail-ph)/2) : 0; // center if it fits, else pin to top
        panel.style.transform='translateY('+ty.toFixed(1)+'px)';
      }
    }
    var doc=document.documentElement;
    var denom=(doc.scrollHeight-vh)||1;
    var sp=clamp(window.scrollY/denom,0,1);
    progress.style.width=(sp*100)+'%';
    var act=activeScene();
    // drawer handle appears ONLY after the text has popped out (text stage)
    drawerTab.classList.toggle('hidden', !(act && act.classList.contains('scene--media') && act.classList.contains('stage-text')));
  }
  function onScroll(){
    if(drawer.classList.contains('open')) closeDrawer();
    if(!ticking){ ticking=true; requestAnimationFrame(update); }
  }
  var viewAvail=0;
  var rootStyle=document.documentElement.style;
  function maxPanelH(){
    var m=0;
    for(var i=0;i<scenes.length;i++){
      var pn=scenes[i].querySelector('.panel');
      if(pn){
        pn.style.removeProperty('transform'); // measure untranslated
        var hh=pn.offsetHeight;
        pn._h=hh;
        if(hh>m){ m=hh; }
      }
    }
    return m;
  }
  // Binary-search the LARGEST --fs at which the tallest panel still fits one
  // screen. Robust against line-count jumps (H is non-decreasing in --fs).
  // Text is never made smaller than necessary; on big screens it grows.
  function fitAll(){
    viewAvail=window.innerHeight*0.92;   // text-box padding is 4vh top + bottom
    var limit=viewAvail*0.97;            // must fit with a small safety margin
    var lo=0.45, hi=1.2, best=0.45;
    for(var k=0;k<13;k++){
      var mid=(lo+hi)/2;
      rootStyle.setProperty('--fs',mid);
      var H=maxPanelH();
      if(H<=limit){ best=mid; lo=mid; } else { hi=mid; }
    }
    rootStyle.setProperty('--fs',best);
    maxPanelH(); // refresh cache for centering
  }
  window.addEventListener('scroll',onScroll,{passive:true});
  window.addEventListener('resize',function(){ fitAll(); update(); });
  window.addEventListener('load',function(){ fitAll(); update(); });
  fitAll();
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
