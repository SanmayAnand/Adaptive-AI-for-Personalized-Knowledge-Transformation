"""
Unified AI System for OCR and Custom Text Transformation
Main Flask Application — v2 with Learning & Quiz features
Poppler auto-detect fix included.
"""

from flask import Flask, request, jsonify, render_template_string
import os, json, traceback, platform
from werkzeug.utils import secure_filename
from ocr_engine import OCREngine
from nlp_engine import TextTransformer, NLPEngine
from learning_engine import ConceptExtractor, TextExpander, QuizGenerator, UserLevelAssessor

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'gif'}
os.makedirs('uploads', exist_ok=True)
os.makedirs('outputs', exist_ok=True)

# ── Poppler path auto-detect (Windows fix) ──────────────────────────
POPPLER_PATH = None
if platform.system() == 'Windows':
    for c in [r'C:\Program Files\Poppler-ai\poppler-25.12.0\Library\bin', r'C:\poppler\bin',
              r'C:\Program Files\poppler\bin',
              r'C:\Program Files\poppler\Library\bin']:
        if os.path.exists(c):
            POPPLER_PATH = c
            break
    if not POPPLER_PATH:
        env = os.environ.get('POPPLER_PATH')
        if env and os.path.exists(env):
            POPPLER_PATH = env

ocr_engine = OCREngine()
transformer = TextTransformer()
nlp_engine = NLPEngine()
concept_extractor = ConceptExtractor()
text_expander = TextExpander()
quiz_generator = QuizGenerator()
level_assessor = UserLevelAssessor()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Unified AI OCR System</title>
<style>
:root{--bg:#080812;--s:#0e0e20;--c:#13132a;--b:#1e1e3f;--p:#7c3aed;--pk:#db2777;
  --bl:#2563eb;--cy:#06b6d4;--tx:#e2e8f0;--mt:#64748b;--gr:#10b981;--yw:#f59e0b;--rd:#ef4444}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--tx);font-family:'Segoe UI',system-ui,sans-serif;min-height:100vh}
.hdr{background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);padding:18px 28px;
  border-bottom:1px solid var(--b);display:flex;align-items:center;gap:14px}
.hdr-t{font-size:1.35rem;font-weight:700;background:linear-gradient(90deg,#a78bfa,#f472b6,#38bdf8);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hdr-s{color:var(--mt);font-size:.78rem;margin-top:2px}
.tabs{display:flex;gap:2px;padding:14px 28px 0;background:var(--bg);border-bottom:1px solid var(--b)}
.tab{padding:9px 18px;border-radius:8px 8px 0 0;cursor:pointer;font-size:.83rem;font-weight:600;
  color:var(--mt);border:1px solid transparent;border-bottom:none;transition:all .2s}
.tab.active{background:var(--s);color:var(--tx);border-color:var(--b)}
.tab:hover:not(.active){color:var(--tx)}
.wrap{max-width:1280px;margin:0 auto;padding:24px}
.pane{display:none}.pane.active{display:block}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}
@media(max-width:850px){.g2,.g3{grid-template-columns:1fr}}
.full{grid-column:1/-1}
.card{background:var(--c);border:1px solid var(--b);border-radius:13px;padding:20px}
.ct{font-size:.88rem;font-weight:700;margin-bottom:13px;display:flex;align-items:center;gap:7px}
.badge{font-size:.65rem;padding:2px 7px;border-radius:7px;font-weight:700;background:#2d1b69;color:#a78bfa}
.bdg-g{background:#064e3b;color:#6ee7b7}.bdg-b{background:#1e3a5f;color:#93c5fd}
.bdg-p{background:#4a0d2b;color:#f9a8d4}
.pipe{display:flex;gap:5px;align-items:center;flex-wrap:wrap;padding:12px 16px;
  background:linear-gradient(135deg,#0f0c29,#0e0e20);border:1px solid var(--b);
  border-radius:11px;margin-bottom:22px}
.ps{padding:4px 10px;border-radius:14px;font-size:.73rem;font-weight:600;
  background:#1a1a3a;border:1px solid #3a3a6a;color:#a78bfa}
.pa{color:var(--mt);font-size:.85rem}
.dz{border:2px dashed var(--p);border-radius:11px;padding:34px 18px;text-align:center;
  cursor:pointer;transition:all .2s;background:#0a0a1e}
.dz:hover,.dz.ov{background:#12123a;border-color:#a78bfa}
.dz-ic{font-size:2.3rem;margin-bottom:9px}
.dz h3{font-size:.95rem;margin-bottom:3px}
.dz p{color:var(--mt);font-size:.79rem}
#fi{display:none}
.btn{padding:8px 16px;border-radius:8px;border:none;cursor:pointer;font-weight:600;
  font-size:.83rem;transition:all .2s;display:inline-flex;align-items:center;gap:5px}
.btn-p{background:linear-gradient(135deg,var(--p),var(--pk));color:#fff}
.btn-p:hover{opacity:.9;transform:translateY(-1px)}
.btn-p:disabled{opacity:.4;cursor:not-allowed;transform:none}
.btn-g{background:var(--b);color:var(--tx)}.btn-g:hover{background:#2a2a4a}
.btn-cy{background:linear-gradient(135deg,#0891b2,#7c3aed);color:#fff}
.btn-gr{background:linear-gradient(135deg,#059669,#0891b2);color:#fff}
.btn-sm{padding:5px 11px;font-size:.75rem}
.al{padding:10px 14px;border-radius:8px;margin-bottom:12px;font-size:.8rem;line-height:1.5}
.al-i{background:#1e3a5f22;border:1px solid #2563eb44;color:#93c5fd}
.al-w{background:#45150322;border:1px solid var(--yw);color:#fde68a}
.al-s{background:#022c2222;border:1px solid var(--gr);color:#6ee7b7}
.al-d{background:#45050522;border:1px solid var(--rd);color:#fca5a5}
.ob{background:#060610;border:1px solid var(--b);border-radius:9px;padding:13px;
  min-height:170px;max-height:360px;overflow-y:auto;font-size:.8rem;line-height:1.75;white-space:pre-wrap}
.ob.mn{font-family:'Consolas',monospace;font-size:.74rem}
.cb{height:7px;border-radius:4px;background:var(--b);margin-top:5px}
.cf{height:100%;border-radius:4px;transition:width .6s}
.sv{font-size:1.45rem;font-weight:700;color:#a78bfa}
.sl{font-size:.7rem;color:var(--mt);margin-top:3px}
.sb{background:#0a0a1e;border:1px solid var(--b);border-radius:9px;padding:12px;text-align:center}
.tag{display:inline-block;padding:2px 7px;border-radius:5px;font-size:.71rem;margin:2px}
.tp{background:#2d1b69;color:#a78bfa}.tpk{background:#4a0d2b;color:#f9a8d4}
.tb{background:#1e3a5f;color:#93c5fd}.tg{background:#064e3b;color:#6ee7b7}
.ty{background:#4a2a03;color:#fde68a}.tr{background:#450505;color:#fca5a5}
.tcy{background:#0c3949;color:#67e8f9}
.tgd{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-bottom:13px}
@media(max-width:680px){.tgd{grid-template-columns:1fr 1fr}}
.tb2{padding:10px;border-radius:9px;border:1px solid var(--b);background:#0a0a1e;
  cursor:pointer;text-align:left;color:var(--tx);transition:all .2s;font-size:.76rem}
.tb2:hover,.tb2.on{background:#1a1a3a;border-color:#a78bfa}
.tb2 .ti{font-size:1rem;margin-bottom:2px;display:block}
.tb2 .tn{font-weight:700;display:block}
.tb2 .td{color:var(--mt);font-size:.7rem;margin-top:1px}
#ld{display:none;text-align:center;padding:16px;color:var(--mt)}
.sp{display:inline-block;width:18px;height:18px;border:2.5px solid var(--b);
  border-top-color:var(--p);border-radius:50%;animation:spin .7s linear infinite;
  vertical-align:middle;margin-right:5px}
@keyframes spin{to{transform:rotate(360deg)}}
.mt8{margin-top:8px}.mt12{margin-top:12px}.mt16{margin-top:16px}.mt20{margin-top:20px}
.fx{display:flex}.g8{gap:8px}.g12{gap:12px}.f1{flex:1}.cn{text-align:center}
.sh{font-size:.9rem;font-weight:700;margin-bottom:11px;padding-bottom:7px;border-bottom:1px solid var(--b)}
.mu{color:var(--mt)}
/* LEARN */
.lv-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:11px;margin-bottom:16px}
@media(max-width:650px){.lv-grid{grid-template-columns:1fr}}
.lvc{padding:16px;border-radius:11px;border:2px solid var(--b);cursor:pointer;transition:all .25s;text-align:center}
.lvc:hover{transform:translateY(-2px)}
.lvc.sl-b{border-color:#06b6d4;background:#06b6d411}
.lvc.sl-i{border-color:#a78bfa;background:#7c3aed11}
.lvc.sl-a{border-color:#f472b6;background:#db277711}
.lv-ic{font-size:1.9rem;margin-bottom:6px}
.lv-n{font-weight:700;font-size:.95rem}
.lv-d{color:var(--mt);font-size:.73rem;margin-top:3px}
.gi{background:#0a0a1e;border:1px solid var(--b);border-radius:9px;padding:13px;margin-bottom:9px}
.gt{font-weight:700;font-size:.87rem;color:#a78bfa}
.gf{font-size:.76rem;color:var(--cy);margin:2px 0}
.ge{font-size:.8rem;line-height:1.6;margin-top:3px}
.gc{font-size:.73rem;color:var(--mt);font-style:italic;margin-top:3px;
  border-left:2px solid var(--b);padding-left:7px}
.pri{display:flex;gap:10px;padding:11px;background:#0f0f25;
  border:1px solid var(--b);border-radius:9px;margin-bottom:7px}
.pri-ic{font-size:1.3rem;flex-shrink:0}
.pri-t{font-weight:700;color:#a78bfa;margin-bottom:2px;font-size:.85rem}
.pri-e{font-size:.8rem;line-height:1.6}
/* INTENT FORM */
.ifl{font-size:.78rem;color:var(--mt);margin-bottom:4px;display:block}
.fis,.fss,.fta{width:100%;padding:8px 11px;border-radius:8px;border:1px solid var(--b);
  background:#0a0a1e;color:var(--tx);font-size:.82rem}
.fis:focus,.fss:focus,.fta:focus{outline:none;border-color:#a78bfa}
.fta{resize:vertical;min-height:70px}
.cbg{display:flex;flex-direction:column;gap:5px}
.cbi{display:flex;align-items:center;gap:7px;cursor:pointer;font-size:.8rem}
.cbi input{accent-color:#a78bfa;width:14px;height:14px}
/* QUIZ */
.qlb-row{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap}
.qlb{padding:7px 15px;border-radius:8px;border:2px solid var(--b);background:transparent;
  color:var(--tx);cursor:pointer;font-weight:600;font-size:.8rem;transition:all .2s}
.qlb.on{border-color:#a78bfa;background:#2d1b6933;color:#a78bfa}
.qc{background:var(--c);border:1px solid var(--b);border-radius:11px;
  padding:18px;margin-bottom:14px;transition:border-color .2s}
.qc.ok{border-color:var(--gr)}.qc.ng{border-color:var(--rd)}
.qn{font-size:.7rem;color:var(--mt);margin-bottom:5px;font-weight:600;text-transform:uppercase;letter-spacing:.04em}
.qt{font-size:.88rem;line-height:1.6;margin-bottom:13px}
.qopts{display:grid;gap:7px}
.qo{padding:9px 13px;border-radius:8px;border:1px solid var(--b);cursor:pointer;
  font-size:.81rem;background:#0a0a1e;color:var(--tx);text-align:left;transition:all .2s;width:100%}
.qo:hover:not(:disabled){background:#1a1a3a;border-color:#a78bfa}
.qo.cr{background:#064e3b33;border-color:var(--gr);color:#6ee7b7}
.qo.wr{background:#45050522;border-color:var(--rd);color:#fca5a5}
.qo.rv{background:#064e3b22;border-color:var(--gr)}
.qfb{margin-top:9px;padding:9px 11px;border-radius:8px;font-size:.78rem;display:none;line-height:1.5}
.qfb.sh2{display:block}.fb-r{background:#022c22;border:1px solid var(--gr);color:#6ee7b7}
.fb-w{background:#45050522;border:1px solid var(--rd);color:#fca5a5}
.fbi{width:100%;padding:8px 11px;border-radius:8px;border:1px solid var(--b);
  background:#0a0a1e;color:var(--tx);font-size:.83rem;margin-bottom:7px}
.fbi:focus{outline:none;border-color:#a78bfa}
.tf-row{display:flex;gap:9px;margin-bottom:7px}
.tfb{flex:1;padding:9px;border-radius:8px;border:1px solid var(--b);cursor:pointer;
  font-weight:700;font-size:.88rem;background:#0a0a1e;color:var(--tx);transition:all .2s}
.tfb:hover:not(:disabled){border-color:#a78bfa}
.ord-list{display:flex;flex-direction:column;gap:5px;margin-bottom:9px}
.ord-item{padding:8px 13px;border-radius:8px;background:#0a0a1e;border:1px solid var(--b);
  font-size:.8rem;cursor:grab;display:flex;align-items:center;gap:7px}
.ord-h{color:var(--mt)}
.rh{text-align:center;padding:20px 0}
.rs{font-size:3.8rem;font-weight:700;background:linear-gradient(90deg,#a78bfa,#f472b6);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent}
.skm{margin-bottom:12px}
.sk-row{display:flex;justify-content:space-between;font-size:.78rem;margin-bottom:4px}
.sk-bar{height:9px;border-radius:5px;background:var(--b)}
.sk-fill{height:100%;border-radius:5px;transition:width .8s}
</style>
</head>
<body>
<div class="hdr">
  <span style="font-size:2rem">🤖</span>
  <div>
    <div class="hdr-t">Unified AI System — OCR &amp; Text Transformation</div>
    <div class="hdr-s">Hriday Jadhav &amp; Sanmay Anand · CV + ML + NLP Pipeline</div>
  </div>
</div>
<div class="tabs">
  <div class="tab active" onclick="sw('ocr',this)">🔍 OCR Pipeline</div>
  <div class="tab" onclick="sw('transform',this)">✨ Transform</div>
  <div class="tab" onclick="sw('learn',this)">📖 Learn &amp; Expand</div>
  <div class="tab" onclick="sw('quiz',this)">🧠 Quiz &amp; Level</div>
</div>

<!-- OCR TAB -->
<div id="pane-ocr" class="pane active wrap">
  <div class="pipe">
    <span class="ps">📄 Input</span><span class="pa">→</span>
    <span class="ps">👁️ Vision Preproc</span><span class="pa">→</span>
    <span class="ps">📐 Layout</span><span class="pa">→</span>
    <span class="ps">🔍 Tesseract</span><span class="pa">→</span>
    <span class="ps">📊 Confidence</span><span class="pa">→</span>
    <span class="ps">🧠 NLP</span><span class="pa">→</span>
    <span class="ps">✨ Output</span>
  </div>
  <div class="g2">
    <div class="card">
      <div class="ct">📤 Upload Document <span class="badge">Step 1</span></div>
      <div class="dz" id="dz" onclick="document.getElementById('fi').click()">
        <div class="dz-ic">📁</div>
        <h3>Drop PDF or Image here</h3>
        <p>PDF, PNG, JPG, TIFF, BMP — any quality</p>
        <p style="margin-top:7px;color:#7c3aed;font-weight:600">Click to browse</p>
      </div>
      <input type="file" id="fi" accept=".pdf,.png,.jpg,.jpeg,.bmp,.tiff,.gif">
      <div id="fi-info" class="al al-i mt8" style="display:none">📄 <strong id="fi-name"></strong></div>
      <div class="mt12"><button class="btn btn-p" id="ocr-btn" onclick="runOCR()" disabled style="width:100%">🔍 Run OCR Pipeline</button></div>
      <div id="ld"><span class="sp"></span>Processing through AI pipeline…</div>
    </div>
    <div class="card">
      <div class="ct">📊 Confidence &amp; Error Analysis <span class="badge">Uncertainty</span></div>
      <div id="conf-ph" class="al al-i">Process a document to see confidence.</div>
      <div id="conf-c" style="display:none">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="font-size:.8rem;color:var(--mt)">Overall OCR Confidence</span>
          <span id="cv" style="font-weight:700;font-size:1.1rem"></span>
        </div>
        <div class="cb"><div class="cf" id="cbar"></div></div>
        <div class="g3 mt12">
          <div class="sb"><div class="sv" id="sp">-</div><div class="sl">Pages</div></div>
          <div class="sb"><div class="sv" id="sw2">-</div><div class="sl">Words</div></div>
          <div class="sb"><div class="sv" id="sq">-</div><div class="sl">Quality</div></div>
        </div>
        <div class="mt12"><div style="font-size:.72rem;color:var(--mt);margin-bottom:4px;text-transform:uppercase">⚠️ Ambiguous Chars</div><div id="amb"></div></div>
        <div class="mt8"><div style="font-size:.72rem;color:var(--mt);margin-bottom:4px;text-transform:uppercase">📑 Layout Regions</div><div id="reg"></div></div>
      </div>
    </div>
    <div class="card">
      <div class="ct">📝 Extracted Text <span class="badge">OCR Output</span></div>
      <div class="ob" id="raw-out">Run the OCR pipeline to see extracted text here…</div>
      <div class="fx g8 mt8">
        <button class="btn btn-g btn-sm" onclick="cp('raw-out')">📋 Copy</button>
        <button class="btn btn-g btn-sm" onclick="dl('raw-out','extracted.txt')">💾 Save</button>
      </div>
    </div>
    <div class="card">
      <div class="ct">🧠 NLP Analysis <span class="badge">Understanding</span></div>
      <div id="nlp-ph" class="al al-i">NLP analysis appears after OCR.</div>
      <div id="nlp-c" style="display:none">
        <div style="font-size:.72rem;color:var(--mt);text-transform:uppercase;margin-bottom:4px">Document Type</div>
        <div id="doc-t"></div>
        <div style="font-size:.72rem;color:var(--mt);text-transform:uppercase;margin:9px 0 4px">Keywords</div>
        <div id="kws"></div>
        <div style="font-size:.72rem;color:var(--mt);text-transform:uppercase;margin:9px 0 4px">Named Entities</div>
        <div id="ents"></div>
        <div style="font-size:.72rem;color:var(--mt);text-transform:uppercase;margin:9px 0 4px">Sentiment · Language</div>
        <div id="senti"></div>
      </div>
    </div>
  </div>
</div>

<!-- TRANSFORM TAB -->
<div id="pane-transform" class="pane wrap">
  <div class="card">
    <div class="ct">✨ Custom Text Transformation <span class="badge">Action Layer</span></div>
    <div class="tgd">
      <button class="tb2 on" onclick="selT(this,'summarize')"><span class="ti">📋</span><span class="tn">Summarization</span><span class="td">Extract key sentences</span></button>
      <button class="tb2" onclick="selT(this,'extract')"><span class="ti">🔎</span><span class="tn">Info Extraction</span><span class="td">Entities, stats, key-values</span></button>
      <button class="tb2" onclick="selT(this,'redact')"><span class="ti">🔒</span><span class="tn">Redaction</span><span class="td">Remove PII, emails, phones</span></button>
      <button class="tb2" onclick="selT(this,'classify')"><span class="ti">🏷️</span><span class="tn">Classify &amp; Tag</span><span class="td">Document type + tags</span></button>
      <button class="tb2" onclick="selT(this,'format_bullet')"><span class="ti">•</span><span class="tn">Bullet Points</span><span class="td">Structured bullets</span></button>
      <button class="tb2" onclick="selT(this,'format_markdown')"><span class="ti">📄</span><span class="tn">Markdown</span><span class="td">Clean Markdown output</span></button>
    </div>
    <button class="btn btn-p" id="t-btn" onclick="runT()" disabled>✨ Apply Transformation</button>
    <div id="t-ph" class="al al-i mt12">Run OCR first, then pick a transformation.</div>
    <div class="ob mt12" id="t-out" style="display:none"></div>
    <div class="fx g8 mt8">
      <button class="btn btn-g btn-sm" onclick="cp('t-out')">📋 Copy</button>
      <button class="btn btn-g btn-sm" onclick="dl('t-out','transformed.txt')">💾 Save</button>
    </div>
  </div>
</div>

<!-- LEARN TAB -->
<div id="pane-learn" class="pane wrap">
  <div id="lph" class="al al-i">Run OCR on a document first, then come here to understand it.</div>
  <div id="lc" style="display:none">
    <h3 class="sh">Step 1 — Choose Your Level</h3>
    <div class="lv-grid">
      <div class="lvc" id="lv-b" onclick="setLv('beginner')"><div class="lv-ic">🌱</div><div class="lv-n">Beginner</div><div class="lv-d">New to this topic — explain everything in plain English with analogies</div></div>
      <div class="lvc sl-i" id="lv-i" onclick="setLv('intermediate')"><div class="lv-ic">📘</div><div class="lv-n">Intermediate</div><div class="lv-d">Know the basics — explain technical terms and architecture clearly</div></div>
      <div class="lvc" id="lv-a" onclick="setLv('advanced')"><div class="lv-ic">🚀</div><div class="lv-n">Advanced</div><div class="lv-d">Expert — give precise definitions and implementation detail</div></div>
    </div>
    <h3 class="sh">Step 2 — Your Learning Intent (Optional)</h3>
    <div style="display:grid;gap:12px;max-width:500px;margin-bottom:16px">
      <div><label class="ifl">What is your main goal?</label>
        <select class="fss" id="ig">
          <option value="understand">Understand the concepts</option>
          <option value="present">Present / explain to others</option>
          <option value="implement">Build / implement this</option>
          <option value="exam">Prepare for exam / viva</option>
        </select></div>
      <div><label class="ifl">Topics you are weak in (tick all that apply):</label>
        <div class="cbg" id="wt">
          <label class="cbi"><input type="checkbox" value="OCR"> OCR / Text Recognition</label>
          <label class="cbi"><input type="checkbox" value="CV"> Computer Vision / Image Processing</label>
          <label class="cbi"><input type="checkbox" value="NLP"> NLP / Language Processing</label>
          <label class="cbi"><input type="checkbox" value="ML"> Machine Learning / Training</label>
          <label class="cbi"><input type="checkbox" value="arch"> System Architecture / Design</label>
        </div></div>
      <div><label class="ifl">Any specific confusions? (optional)</label>
        <textarea class="fta" id="in2" placeholder="e.g. I don't understand what confidence scores mean…"></textarea></div>
    </div>
    <button class="btn btn-cy" onclick="runExp()">📖 Generate Learning View</button>
    <div id="exp-out" style="display:none;margin-top:22px">
      <div id="pre-s"><h3 class="sh mt16">📚 Pre-Reading — Understand These First</h3><div id="pre-items"></div></div>
      <div style="margin-top:18px"><h3 class="sh">📄 Annotated Text <span style="font-size:.72rem;color:var(--mt)">(† = explained below)</span></h3><div class="ob" id="ann-t"></div></div>
      <div id="simp-s" style="display:none;margin-top:18px"><h3 class="sh">🌱 Simplified Plain-Language Version</h3><div class="ob" id="simp-t"></div></div>
      <div style="margin-top:18px"><h3 class="sh">📖 Full Glossary — Terms Explained at Your Level</h3><div id="gl-items"></div></div>
    </div>
  </div>
</div>

<!-- QUIZ TAB -->
<div id="pane-quiz" class="pane wrap">
  <div id="qph" class="al al-i">Run OCR on a document first, then take a quiz on its content.</div>
  <div id="q-setup" style="display:none">
    <div class="g2">
      <div class="card">
        <div class="ct">🎯 Quiz Setup</div>
        <label class="ifl mt8">Difficulty level:</label>
        <div class="qlb-row">
          <button class="qlb" onclick="setQL('beginner',this)">🌱 Beginner</button>
          <button class="qlb on" onclick="setQL('intermediate',this)">📘 Intermediate</button>
          <button class="qlb" onclick="setQL('advanced',this)">🚀 Advanced</button>
        </div>
        <label class="ifl">Number of questions:</label>
        <div class="qlb-row">
          <button class="qlb" onclick="setQN(5,this)">5</button>
          <button class="qlb on" onclick="setQN(8,this)">8</button>
          <button class="qlb" onclick="setQN(12,this)">12</button>
        </div>
        <button class="btn btn-p mt12" onclick="startQuiz()" style="width:100%">🚀 Start Quiz</button>
      </div>
      <div class="card">
        <div class="ct">ℹ️ What gets tested?</div>
        <div style="font-size:.8rem;line-height:1.85;color:var(--mt)">
          Questions come <strong style="color:var(--tx)">directly from your document</strong>:<br><br>
          📌 <strong style="color:var(--tx)">Acronym expansion</strong> — What does OCR stand for?<br>
          📌 <strong style="color:var(--tx)">Definition MCQ</strong> — Which best describes binarization?<br>
          📌 <strong style="color:var(--tx)">Fill-in-the-blank</strong> — from key document sentences<br>
          📌 <strong style="color:var(--tx)">True / False</strong> — based on document statements<br>
          📌 <strong style="color:var(--tx)">Step ordering</strong> — arrange pipeline steps correctly<br><br>
          After the quiz: <strong style="color:#a78bfa">skill meters per topic</strong>, weak/strong area detection, and personalized study plan.
        </div>
      </div>
    </div>
  </div>
  <div id="q-qs" style="display:none">
    <div style="display:flex;align-items:center;gap:14px;margin-bottom:14px">
      <span style="font-size:.82rem;color:var(--mt)">Q <span id="qcur">1</span>/<span id="qtot">8</span></span>
      <div style="flex:1;height:5px;background:var(--b);border-radius:3px">
        <div id="qpf" style="height:100%;border-radius:3px;background:linear-gradient(90deg,#7c3aed,#db2777);width:0%;transition:width .4s"></div>
      </div>
      <button class="btn btn-g btn-sm" onclick="submitQ()">Submit All →</button>
    </div>
    <div id="q-cont"></div>
    <div class="cn mt16"><button class="btn btn-gr" onclick="submitQ()">✅ Submit &amp; See Results</button></div>
  </div>
  <div id="q-res" style="display:none">
    <div class="g2">
      <div class="card">
        <div class="rh"><div class="rs" id="res-s">-</div><div style="color:var(--mt);margin-top:3px">Overall Score</div><div class="mt8" id="res-l"></div></div>
        <div style="display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin-top:10px" id="res-a"></div>
      </div>
      <div class="card">
        <div class="ct">📊 Skill Meters</div>
        <div id="skm"></div>
      </div>
      <div class="card full">
        <div class="ct">💡 Personalized Recommendations</div>
        <div id="recs"></div>
      </div>
      <div class="card full">
        <div class="ct">📋 Answer Review</div>
        <div id="ar"></div>
      </div>
    </div>
    <div class="cn mt16"><button class="btn btn-g" onclick="resetQ()">🔁 Retake Quiz</button></div>
  </div>
</div>

<script>
let txt='',ocrR=null,cpts=null,selTr='summarize',lvl='intermediate',qlvl='intermediate',qn=8,qs=[],ua={};

function sw(n,el){
  document.querySelectorAll('.pane').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.getElementById('pane-'+n).classList.add('active');
  el.classList.add('active');
}

const fi=document.getElementById('fi');
fi.addEventListener('change',e=>{if(e.target.files[0])hf(e.target.files[0])});
const dz=document.getElementById('dz');
dz.addEventListener('dragover',e=>{e.preventDefault();dz.classList.add('ov')});
dz.addEventListener('dragleave',()=>dz.classList.remove('ov'));
dz.addEventListener('drop',e=>{e.preventDefault();dz.classList.remove('ov');if(e.dataTransfer.files[0])hf(e.dataTransfer.files[0])});
function hf(f){document.getElementById('fi-name').textContent=f.name+' ('+(f.size/1024).toFixed(1)+' KB)';
  document.getElementById('fi-info').style.display='block';document.getElementById('ocr-btn').disabled=false;fi._f=f;}

async function runOCR(){
  if(!fi._f)return;
  document.getElementById('ld').style.display='block';
  document.getElementById('ocr-btn').disabled=true;
  document.getElementById('raw-out').textContent='Processing…';
  const fd=new FormData();fd.append('file',fi._f);
  try{
    const r=await fetch('/api/ocr',{method:'POST',body:fd});
    const d=await r.json();
    if(d.error)throw new Error(d.error);
    ocrR=d;txt=d.full_text;
    document.getElementById('raw-out').textContent=txt||'No text extracted.';
    document.getElementById('conf-ph').style.display='none';
    document.getElementById('conf-c').style.display='block';
    const conf=Math.round(d.overall_confidence);
    document.getElementById('cv').textContent=conf+'%';
    const bar=document.getElementById('cbar');
    bar.style.width=conf+'%';bar.style.background=conf>=80?'#10b981':conf>=60?'#f59e0b':'#ef4444';
    document.getElementById('sp').textContent=d.total_pages||1;
    document.getElementById('sw2').textContent=txt.split(/\s+/).filter(Boolean).length;
    document.getElementById('sq').textContent=conf>=80?'HIGH ✅':conf>=60?'MED ⚠️':'LOW ❌';
    const am=d.pages?.[0]?.confidence?.ambiguous_chars||[];
    document.getElementById('amb').innerHTML=am.length?am.map(a=>`<span class="tag tpk">${a.pattern} ×${a.count}</span>`).join(''):'<span class="mu" style="font-size:.78rem">None ✓</span>';
    const rgs=d.pages?.[0]?.regions||[],rc={};
    rgs.forEach(r=>rc[r.type]=(rc[r.type]||0)+1);
    document.getElementById('reg').innerHTML=Object.entries(rc).map(([t,c])=>`<span class="tag tb">${t}: ${c}</span>`).join('')||'<span class="mu" style="font-size:.78rem">—</span>';
    await runNLP();
    const cr=await fetch('/api/concepts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:txt})});
    const cd=await cr.json();
    if(!cd.error){cpts=cd;document.getElementById('lph').style.display='none';document.getElementById('lc').style.display='block';document.getElementById('qph').style.display='none';document.getElementById('q-setup').style.display='block';}
    document.getElementById('t-btn').disabled=false;
  }catch(e){document.getElementById('raw-out').textContent='❌ Error: '+e.message+'\n\nIf PDF fails: install Poppler and check README.md for Windows setup.';}
  document.getElementById('ld').style.display='none';document.getElementById('ocr-btn').disabled=false;
}

async function runNLP(){
  const r=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:txt})});
  const d=await r.json();
  document.getElementById('nlp-ph').style.display='none';document.getElementById('nlp-c').style.display='block';
  document.getElementById('doc-t').innerHTML=`<span class="tag tp">${d.classification?.document_type}</span><span class="tag tb">${d.classification?.type_confidence}%</span>`;
  document.getElementById('kws').innerHTML=(d.keywords||[]).map(([w,c])=>`<span class="tag tp">${w} <small style="opacity:.6">${c}</small></span>`).join('');
  const tc={EMAIL:'tpk',PHONE:'tpk',DATE:'tb',URL:'tb',CAPITALIZED_PHRASE:'tg',ACRONYM:'tg'};
  let eh='';for(const[t,v]of Object.entries(d.entities||{})){if(v.length)eh+=`<span class="tag ${tc[t]||'tp'}">${t}: ${v.slice(0,3).join(', ')}</span>`;}
  document.getElementById('ents').innerHTML=eh||'<span class="mu" style="font-size:.78rem">None</span>';
  const sm={Positive:'tg',Negative:'tr',Neutral:'tb'};const se=d.classification?.sentiment||'Neutral';
  document.getElementById('senti').innerHTML=`<span class="tag ${sm[se]}">${se}</span><span class="tag tb">${d.classification?.language||'English'}</span>`;
}

function selT(btn,t){document.querySelectorAll('.tb2').forEach(b=>b.classList.remove('on'));btn.classList.add('on');selTr=t;}
async function runT(){
  if(!txt)return;
  document.getElementById('t-ph').style.display='none';
  const out=document.getElementById('t-out');out.style.display='block';out.textContent='Transforming…';
  try{
    const r=await fetch('/api/transform',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:txt,transform:selTr})});
    const d=await r.json();
    if(d.error)throw new Error(d.error);
    out.textContent=typeof d.result==='object'?JSON.stringify(d.result,null,2):d.result;
    out.className='ob mt12'+(typeof d.result==='object'?' mn':'');
  }catch(e){out.textContent='❌ '+e.message;}
}

function setLv(l){lvl=l;['b','i','a'].forEach((x,i)=>{const ll=['beginner','intermediate','advanced'][i];document.getElementById('lv-'+x).className='lvc'+(l===ll?' sl-'+x:'');});}

async function runExp(){
  if(!txt||!cpts)return;
  const wk=[...document.querySelectorAll('#wt input:checked')].map(c=>c.value);
  const r=await fetch('/api/expand',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({text:txt,level:lvl,concepts:cpts,intent:document.getElementById('ig').value,
      weak_topics:wk,notes:document.getElementById('in2').value})});
  const d=await r.json();
  if(d.error){alert(d.error);return;}
  document.getElementById('exp-out').style.display='block';
  const pre=d.pre_reading||[];
  document.getElementById('pre-items').innerHTML=pre.length?pre.map(p=>`<div class="pri"><div class="pri-ic">📌</div><div><div class="pri-t">${p.term}</div><div style="font-size:.73rem;color:var(--mt);margin-bottom:2px">${p.why_needed}</div><div class="pri-e">${p.explanation}</div></div></div>`).join(''):'<span class="mu" style="font-size:.8rem">No pre-reading needed at this level.</span>';
  document.getElementById('ann-t').textContent=d.annotated_text||txt;
  const ss=document.getElementById('simp-s');
  if(d.simplified_summary&&lvl==='beginner'){ss.style.display='block';document.getElementById('simp-t').textContent=d.simplified_summary;}else{ss.style.display='none';}
  const gl=d.glossary||[];
  document.getElementById('gl-items').innerHTML=gl.length?gl.map(g=>`<div class="gi"><div class="gt">${g.term} <span class="tag tb" style="font-size:.63rem">${g.type}</span></div>${g.full_form?`<div class="gf">📌 ${g.full_form}</div>`:''}<div class="ge">${g.explanation||'See domain references.'}</div>${g.context?`<div class="gc">"…${g.context}…"</div>`:''}</div>`).join(''):'<span class="mu" style="font-size:.8rem">No terms to explain at this level.</span>';
}

function setQL(l,btn){qlvl=l;document.querySelectorAll('.qlb-row:first-of-type .qlb').forEach(b=>b.classList.remove('on'));btn.classList.add('on');}
function setQN(n,btn){qn=n;[...btn.parentElement.querySelectorAll('.qlb')].forEach(b=>b.classList.remove('on'));btn.classList.add('on');}

async function startQuiz(){
  const r=await fetch('/api/quiz',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({text:txt,concepts:cpts,level:qlvl,n:qn})});
  const d=await r.json();
  if(d.error){alert(d.error);return;}
  qs=d.questions;ua={};
  document.getElementById('q-setup').style.display='none';
  document.getElementById('q-qs').style.display='block';
  document.getElementById('qtot').textContent=qs.length;
  renderQ();
}

function eq(s){return(s||'').replace(/'/g,"\\'").replace(/"/g,'&quot;')}

function renderQ(){
  const c=document.getElementById('q-cont');c.innerHTML='';
  qs.forEach((q,i)=>{
    const div=document.createElement('div');div.className='qc';div.id='qc-'+q.id;
    const dt=`<span class="tag ${q.difficulty==='beginner'?'tcy':'tp'}" style="font-size:.63rem">${q.difficulty}</span>`;
    let body=`<div class="qn">Q${q.id} · ${q.topic} ${dt}</div><div class="qt">${q.question}</div>`;
    if(q.type==='mcq'){
      body+=`<div class="qopts">`+q.options.map(o=>`<button class="qo" onclick="aMCQ(${q.id},this,'${eq(o)}','${eq(q.answer)}')">${o}</button>`).join('')+`</div>`;
    }else if(q.type==='fill_blank'){
      body+=`<input class="fbi" id="fbi-${q.id}" placeholder="Type your answer…"><div style="font-size:.73rem;color:var(--mt)">${q.hint||''}</div><button class="btn btn-g btn-sm mt8" onclick="aFill(${q.id},'${eq(q.answer)}')">Check ✓</button>`;
    }else if(q.type==='true_false'){
      body+=`<div class="tf-row"><button class="tfb" onclick="aTF(${q.id},this,'True','${eq(q.answer)}')">✅ True</button><button class="tfb" onclick="aTF(${q.id},this,'False','${eq(q.answer)}')">❌ False</button></div>`;
    }else if(q.type==='ordering'){
      body+=`<div class="ord-list" id="ord-${q.id}">`+q.items.map((it,j)=>`<div class="ord-item" draggable="true" data-i="${j}"><span class="ord-h">☰</span>${it}</div>`).join('')+`</div><button class="btn btn-g btn-sm" onclick="aOrd(${q.id})">Check Order ✓</button>`;
    }
    body+=`<div class="qfb" id="fb-${q.id}"></div>`;
    div.innerHTML=body;c.appendChild(div);
    document.getElementById('qcur').textContent=Math.min(i+1,qs.length);
    document.getElementById('qpf').style.width=((i+1)/qs.length*100)+'%';
  });
  setupDrag();
}

function aMCQ(id,btn,ch,co){
  const card=document.getElementById('qc-'+id);
  card.querySelectorAll('.qo').forEach(b=>b.disabled=true);
  const ok=ch.toLowerCase().slice(0,40)===co.toLowerCase().slice(0,40)||co.toLowerCase().includes(ch.toLowerCase().slice(0,30));
  btn.classList.add(ok?'cr':'wr');
  if(!ok)card.querySelectorAll('.qo').forEach(b=>{if(b.textContent.trim().toLowerCase().slice(0,30)===co.toLowerCase().slice(0,30))b.classList.add('rv');});
  showFB(id,ok,qs.find(q=>q.id===id)?.explanation||'');
  ua[id]=ch;card.classList.add(ok?'ok':'ng');
}
function aFill(id,co){
  const val=document.getElementById('fbi-'+id).value.trim();
  const ok=val.toLowerCase()===co.toLowerCase();
  showFB(id,ok,'Correct answer: '+co);ua[id]=val;
  document.getElementById('qc-'+id).classList.add(ok?'ok':'ng');
}
function aTF(id,btn,ch,co){
  const ok=ch===co;
  document.getElementById('qc-'+id).querySelectorAll('.tfb').forEach(b=>b.disabled=true);
  btn.style.borderColor=ok?'var(--gr)':'var(--rd)';
  showFB(id,ok,qs.find(q=>q.id===id)?.explanation||'');ua[id]=ch;
  document.getElementById('qc-'+id).classList.add(ok?'ok':'ng');
}
function aOrd(id){
  const items=[...document.getElementById('ord-'+id).querySelectorAll('.ord-item')];
  const given=items.map(i=>i.textContent.replace('☰','').trim());
  const co=qs.find(q=>q.id===id).answer;
  const ok=JSON.stringify(given)===JSON.stringify(co);
  showFB(id,ok,'Correct order: '+co.join(' → '));ua[id]=given.join('|');
  document.getElementById('qc-'+id).classList.add(ok?'ok':'ng');
}
function showFB(id,ok,exp){
  const fb=document.getElementById('fb-'+id);
  fb.className='qfb sh2 '+(ok?'fb-r':'fb-w');
  fb.innerHTML=(ok?'✅ Correct! ':'❌ Incorrect. ')+(exp||'');
}
function setupDrag(){
  document.querySelectorAll('.ord-list').forEach(list=>{
    let drag=null;
    list.querySelectorAll('.ord-item').forEach(item=>{
      item.addEventListener('dragstart',()=>drag=item);
      item.addEventListener('dragover',e=>e.preventDefault());
      item.addEventListener('drop',e=>{e.preventDefault();if(drag&&drag!==item)list.insertBefore(drag,item.nextSibling);});
    });
  });
}
async function submitQ(){
  qs.forEach(q=>{if(!(q.id in ua))ua[q.id]='';});
  const answers=Object.entries(ua).map(([id,given])=>({id:parseInt(id),given}));
  const r=await fetch('/api/quiz/score',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({answers,questions:qs})});
  const d=await r.json();
  if(d.error){alert(d.error);return;}
  showRes(d);
}
function showRes(d){
  document.getElementById('q-qs').style.display='none';document.getElementById('q-res').style.display='block';
  document.getElementById('res-s').textContent=d.overall_score+'%';
  const lm={beginner:'🌱 Beginner',intermediate:'📘 Intermediate',advanced:'🚀 Advanced'};
  document.getElementById('res-l').innerHTML=`<span class="tag tp">${lm[d.inferred_level]||d.inferred_level}</span><span class="tag tb">${d.correct}/${d.total} correct</span>`;
  let ah='';
  (d.strong_areas||[]).forEach(a=>ah+=`<span class="tag tg">✅ ${a}</span>`);
  (d.weak_areas||[]).forEach(a=>ah+=`<span class="tag tr">⚠️ ${a}</span>`);
  document.getElementById('res-a').innerHTML=ah;
  document.getElementById('skm').innerHTML=Object.entries(d.skill_meters||{}).map(([t,info])=>{
    const col=info.score>=75?'#10b981':info.score>=50?'#f59e0b':'#ef4444';
    return`<div class="skm"><div class="sk-row"><span>${t}</span><span style="font-weight:700">${info.score}% <span style="color:var(--mt);font-size:.72rem">${info.level}</span></span></div><div class="sk-bar"><div class="sk-fill" style="width:${info.score}%;background:${col}"></div></div></div>`;
  }).join('')||'<span class="mu">No breakdown.</span>';
  document.getElementById('recs').innerHTML=(d.recommendations||[]).map(r=>`<div style="padding:7px 0;border-bottom:1px solid var(--b);font-size:.82rem;line-height:1.6">${r}</div>`).join('');
  document.getElementById('ar').innerHTML=(d.details||[]).map(r=>`<div style="padding:11px 0;border-bottom:1px solid var(--b)"><div style="display:flex;gap:7px"><span>${r.is_correct?'✅':'❌'}</span><div><div style="font-size:.8rem;margin-bottom:3px">${r.question}</div>${!r.is_correct?`<div style="font-size:.76rem;color:var(--mt)">You: ${r.given||'(blank)'} · Correct: <strong style="color:#6ee7b7">${r.correct_answer}</strong></div>`:''} ${r.explanation?`<div style="font-size:.74rem;color:var(--mt);font-style:italic;margin-top:2px">${r.explanation}</div>`:''}</div></div></div>`).join('');
}
function resetQ(){document.getElementById('q-res').style.display='none';document.getElementById('q-setup').style.display='block';qs=[];ua={};}

function cp(id){navigator.clipboard.writeText(document.getElementById(id).textContent);}
function dl(id,fn){const b=new Blob([document.getElementById(id).textContent],{type:'text/plain'});Object.assign(document.createElement('a'),{href:URL.createObjectURL(b),download:fn}).click();}
</script>
</body>
</html>"""


# ── Routes ──────────────────────────────────────────────────────────

@app.route('/')
def index():
    return HTML


@app.route('/api/ocr', methods=['POST'])
def api_ocr():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    try:
        ext = filename.rsplit('.', 1)[1].lower()
        if ext == 'pdf':
            result = ocr_engine.extract_from_pdf(filepath, poppler_path=POPPLER_PATH)
        else:
            result = ocr_engine.extract_from_image(filepath)
            result['total_pages'] = 1
            result['pages'] = [result.copy()]
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    data = request.get_json()
    text = data.get('text', '')
    if not text:
        return jsonify({'error': 'No text'}), 400
    try:
        normalized = nlp_engine.normalize(text)
        return jsonify({
            'keywords': nlp_engine.get_keywords(normalized, top_n=12),
            'entities': nlp_engine.named_entity_recognition(normalized),
            'classification': transformer.classify_and_tag(normalized),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/transform', methods=['POST'])
def api_transform():
    data = request.get_json()
    text = data.get('text', '')
    t = data.get('transform', 'summarize')
    if not text:
        return jsonify({'error': 'No text'}), 400
    try:
        if t == 'summarize':   result = transformer.summarize(text, ratio=0.35, max_sentences=8)
        elif t == 'extract':   result = transformer.extract_information(text)
        elif t == 'redact':
            r = transformer.redact(text)
            result = r['redacted_text'] + f"\n\n[{r['items_redacted']} items redacted]"
        elif t == 'classify':  result = transformer.classify_and_tag(text)
        elif t == 'format_bullet': result = transformer.format_text(text, style='bullet_points')
        elif t == 'format_markdown': result = transformer.format_text(text, style='markdown')
        else: return jsonify({'error': 'Unknown transform'}), 400
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/concepts', methods=['POST'])
def api_concepts():
    data = request.get_json()
    text = data.get('text', '')
    if not text:
        return jsonify({'error': 'No text'}), 400
    try:
        return jsonify(concept_extractor.extract(text))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/expand', methods=['POST'])
def api_expand():
    data = request.get_json()
    text = data.get('text', '')
    level = data.get('level', 'intermediate')
    concepts = data.get('concepts', {})
    if not text:
        return jsonify({'error': 'No text'}), 400
    try:
        return jsonify(text_expander.expand(text, level, concepts))
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/quiz', methods=['POST'])
def api_quiz():
    data = request.get_json()
    text = data.get('text', '')
    concepts = data.get('concepts', {})
    level = data.get('level', 'intermediate')
    n = int(data.get('n', 8))
    if not text:
        return jsonify({'error': 'No text'}), 400
    try:
        qs = quiz_generator.generate(text, concepts, level, n_questions=n)
        return jsonify({'questions': qs})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/quiz/score', methods=['POST'])
def api_quiz_score():
    data = request.get_json()
    try:
        result = level_assessor.calculate_score(data.get('answers', []), data.get('questions', []))
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("🤖 Unified AI OCR System v2")
    if POPPLER_PATH:
        print(f"   ✅ Poppler found: {POPPLER_PATH}")
    else:
        print("   ⚠️  Poppler not found — PDF needs setup (see README)")
    print("   Open: http://localhost:5000")
    print("=" * 60)
    app.run(debug=False, host='0.0.0.0', port=5000)
