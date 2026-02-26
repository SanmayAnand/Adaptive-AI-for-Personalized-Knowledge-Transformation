"""
Unified AI System for OCR and Custom Text Transformation
Main Flask Application — v3 POLISHED
Features: OCR, NLP, Story Mode, Adaptive PDF, Quiz, Training, Image Preview
"""

from flask import Flask, request, jsonify, render_template_string
import os, json, traceback, platform, base64
from werkzeug.utils import secure_filename
from ocr_engine import OCREngine
from nlp_engine import TextTransformer, NLPEngine, StoryTransformer
from learning_engine import ConceptExtractor, TextExpander, QuizGenerator, UserLevelAssessor
from train import TrainingDataCollector, OCRPostProcessor, ModelEvaluator
# At the top with other imports
from menu_ocr_endpoint import register_menu_ocr_routes

# After all your existing routes, before if __name__ == '__main__':

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'gif'}
os.makedirs('uploads', exist_ok=True)
os.makedirs('outputs', exist_ok=True)
os.makedirs('models', exist_ok=True)

POPPLER_PATH = r"C:\Users\Hriday\Downloads\Release-25.12.0-0\poppler-25.12.0\Library\bin"
if platform.system() == 'Windows':
    for c in [r'C:\Program Files\Poppler-ai\poppler-25.12.0\Library\bin', r'C:\poppler\bin',
              r'C:\Program Files\poppler\bin', r'C:\Program Files\poppler\Library\bin']:
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
story_transformer = StoryTransformer()
concept_extractor = ConceptExtractor()
text_expander = TextExpander()
quiz_generator = QuizGenerator()
level_assessor = UserLevelAssessor()
training_collector = TrainingDataCollector()
post_processor = OCRPostProcessor()
evaluator = ModelEvaluator()

def allowed_file(f):
    return '.' in f and f.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ═══════════════════════════════════════════════════════════════════
#  HTML — COMPLETE REDESIGNED UI
# ═══════════════════════════════════════════════════════════════════

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>IntelliDoc AI — Smart PDF Understanding</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#05050f;--s1:#0b0b1e;--s2:#10102b;--s3:#181836;
  --bd:#1e1e42;--bd2:#2a2a55;
  --p:#7c3aed;--p2:#9d5cf4;--p3:#c084fc;
  --pk:#db2777;--pk2:#ec4899;
  --cy:#06b6d4;--cy2:#22d3ee;
  --gr:#10b981;--gr2:#34d399;
  --yw:#f59e0b;--rd:#ef4444;
  --tx:#e8e8ff;--tx2:#a8a8cc;--tx3:#6b6b8a;
  --gold:#fbbf24;
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--tx);font-family:'DM Sans',sans-serif;min-height:100vh;overflow-x:hidden}

/* ── BACKGROUND MESH ── */
body::before{content:'';position:fixed;inset:0;
  background:radial-gradient(ellipse 80% 50% at 20% 20%,#1a0a3a22,transparent),
             radial-gradient(ellipse 60% 40% at 80% 80%,#0a1a3a22,transparent),
             radial-gradient(ellipse 40% 30% at 50% 50%,#0a0a2a,transparent);
  pointer-events:none;z-index:0}

/* ── HEADER ── */
.hdr{position:sticky;top:0;z-index:100;
  background:linear-gradient(180deg,var(--bg) 0%,rgba(5,5,15,.95) 100%);
  backdrop-filter:blur(20px);border-bottom:1px solid var(--bd);
  padding:0 32px;display:flex;align-items:center;gap:20px;height:64px}
.logo{display:flex;align-items:center;gap:10px;flex-shrink:0}
.logo-icon{width:38px;height:38px;background:linear-gradient(135deg,var(--p),var(--pk));
  border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.2rem}
.logo-text{font-family:'Syne',sans-serif;font-weight:800;font-size:1.15rem;
  background:linear-gradient(90deg,var(--p3),var(--pk2),var(--cy2));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent}
.logo-sub{font-size:.68rem;color:var(--tx3);margin-top:-2px}
.nav{display:flex;gap:4px;flex:1;justify-content:center}
.nav-btn{padding:7px 16px;border-radius:8px;cursor:pointer;font-size:.82rem;font-weight:600;
  color:var(--tx3);border:1px solid transparent;background:transparent;
  transition:all .2s;display:flex;align-items:center;gap:6px;white-space:nowrap}
.nav-btn:hover{color:var(--tx);background:var(--s2)}
.nav-btn.active{color:var(--tx);background:var(--s3);border-color:var(--bd2)}
.nav-dot{width:6px;height:6px;border-radius:50%;background:var(--p);display:none}
.nav-btn.active .nav-dot{display:block}
.hdr-right{display:flex;align-items:center;gap:10px;flex-shrink:0}
.status-pill{padding:4px 10px;border-radius:20px;font-size:.7rem;font-weight:600;
  display:flex;align-items:center;gap:5px;background:var(--s2);border:1px solid var(--bd)}
.status-dot{width:6px;height:6px;border-radius:50%;background:var(--gr);
  animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}

/* ── LAYOUT ── */
.wrap{position:relative;z-index:1;max-width:1320px;margin:0 auto;padding:28px 24px}
.pane{display:none}.pane.active{display:block}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}
@media(max-width:900px){.g2,.g3{grid-template-columns:1fr}}
.full{grid-column:1/-1}

/* ── CARDS ── */
.card{background:var(--s1);border:1px solid var(--bd);border-radius:16px;
  padding:22px;position:relative;overflow:hidden}
.card::before{content:'';position:absolute;inset:0;
  background:linear-gradient(135deg,rgba(124,58,237,.04),transparent 60%);
  pointer-events:none}
.card-title{font-family:'Syne',sans-serif;font-size:.88rem;font-weight:700;
  margin-bottom:14px;display:flex;align-items:center;gap:8px;color:var(--tx)}
.chip{font-size:.62rem;padding:2px 8px;border-radius:20px;font-weight:700;
  font-family:'DM Sans',sans-serif}
.chip-p{background:#2d1b6955;color:var(--p3);border:1px solid #4a2a8a55}
.chip-g{background:#06433055;color:var(--gr2);border:1px solid #0a6a4855}
.chip-b{background:#1e3a6055;color:#93c5fd;border:1px solid #2563eb44}
.chip-pk{background:#4a0d2b55;color:#f9a8d4;border:1px solid #be185d44}
.chip-y{background:#4a2a0355;color:var(--gold);border:1px solid #92400e44}
.chip-r{background:#45050555;color:#fca5a5;border:1px solid #991b1b44}
.chip-cy{background:#0c394955;color:var(--cy2);border:1px solid #0e749444}

/* ── PIPELINE BAR ── */
.pipeline{display:flex;align-items:center;gap:3px;flex-wrap:wrap;padding:14px 18px;
  background:linear-gradient(90deg,var(--s1),var(--s2));border:1px solid var(--bd);
  border-radius:12px;margin-bottom:24px}
.pipe-step{padding:5px 12px;border-radius:8px;font-size:.72rem;font-weight:600;
  background:var(--s3);border:1px solid var(--bd2);color:var(--tx2);
  transition:all .3s;white-space:nowrap}
.pipe-step.done{background:#1a1040;border-color:var(--p);color:var(--p3)}
.pipe-step.active{background:linear-gradient(135deg,var(--p),var(--pk));
  border-color:transparent;color:#fff;animation:glow .8s infinite alternate}
@keyframes glow{from{box-shadow:0 0 5px var(--p)}to{box-shadow:0 0 15px var(--p),0 0 30px var(--pk)}}
.pipe-arrow{color:var(--tx3);font-size:.7rem}

/* ── UPLOAD ZONE ── */
.upload-zone{border:2px dashed var(--bd2);border-radius:14px;padding:40px 20px;
  text-align:center;cursor:pointer;transition:all .3s;background:var(--s2);
  position:relative;overflow:hidden}
.upload-zone::before{content:'';position:absolute;inset:0;
  background:radial-gradient(ellipse at 50% 100%,rgba(124,58,237,.08),transparent);
  pointer-events:none}
.upload-zone:hover,.upload-zone.over{border-color:var(--p);background:var(--s3);
  transform:translateY(-2px);box-shadow:0 8px 30px rgba(124,58,237,.15)}
.upload-icon{font-size:2.8rem;margin-bottom:10px;filter:drop-shadow(0 0 15px rgba(124,58,237,.4))}
.upload-title{font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;margin-bottom:4px}
.upload-sub{color:var(--tx3);font-size:.78rem}
.upload-types{display:flex;gap:5px;justify-content:center;flex-wrap:wrap;margin-top:10px}
.type-tag{padding:2px 8px;border-radius:4px;font-size:.65rem;font-weight:700;
  background:var(--s3);border:1px solid var(--bd2);color:var(--tx2)}

/* ── IMAGE PREVIEW ── */
.img-preview-wrap{margin-top:14px;border-radius:10px;overflow:hidden;
  border:1px solid var(--bd);display:none;position:relative}
.img-preview{width:100%;max-height:260px;object-fit:contain;background:#080818;display:block}
.img-preview-overlay{position:absolute;bottom:0;left:0;right:0;
  background:linear-gradient(0deg,rgba(5,5,15,.9),transparent);
  padding:12px 14px;font-size:.75rem;color:var(--tx2)}

/* ── BUTTONS ── */
.btn{padding:9px 18px;border-radius:10px;border:none;cursor:pointer;
  font-weight:600;font-size:.83rem;font-family:'DM Sans',sans-serif;
  transition:all .2s;display:inline-flex;align-items:center;gap:6px}
.btn-primary{background:linear-gradient(135deg,var(--p),var(--pk));color:#fff}
.btn-primary:hover{opacity:.9;transform:translateY(-1px);
  box-shadow:0 4px 20px rgba(124,58,237,.4)}
.btn-primary:disabled{opacity:.35;cursor:not-allowed;transform:none;box-shadow:none}
.btn-secondary{background:var(--s3);color:var(--tx);border:1px solid var(--bd2)}
.btn-secondary:hover{background:var(--bd);border-color:var(--bd2)}
.btn-story{background:linear-gradient(135deg,#be185d,#7c3aed);color:#fff}
.btn-story:hover{opacity:.9;transform:translateY(-1px);box-shadow:0 4px 20px rgba(219,39,119,.35)}
.btn-cyan{background:linear-gradient(135deg,#0891b2,#7c3aed);color:#fff}
.btn-green{background:linear-gradient(135deg,#059669,#0891b2);color:#fff}
.btn-sm{padding:5px 12px;font-size:.74rem;border-radius:7px}
.btn-full{width:100%;justify-content:center}

/* ── ALERTS ── */
.alert{padding:11px 15px;border-radius:10px;margin-bottom:12px;font-size:.8rem;line-height:1.55}
.alert-info{background:#1e3a6022;border:1px solid #2563eb44;color:#93c5fd}
.alert-warn{background:#45150322;border:1px solid var(--yw);color:#fde68a}
.alert-success{background:#022c2222;border:1px solid var(--gr);color:var(--gr2)}
.alert-error{background:#45050522;border:1px solid var(--rd);color:#fca5a5}
.alert-story{background:#4a0d2b22;border:1px solid #be185d44;color:#f9a8d4}

/* ── OUTPUT BOX ── */
.output-box{background:#030308;border:1px solid var(--bd);border-radius:10px;
  padding:14px;min-height:180px;max-height:420px;overflow-y:auto;
  font-size:.79rem;line-height:1.85;white-space:pre-wrap;color:var(--tx2)}
.output-box.story-mode{font-family:'DM Sans',sans-serif;font-size:.85rem;
  line-height:2;color:var(--tx);background:linear-gradient(180deg,#08041a,#030308)}
.output-box.mono{font-family:'Cascadia Code','Consolas',monospace;font-size:.74rem}
.output-box-actions{display:flex;gap:7px;margin-top:8px;flex-wrap:wrap}

/* ── CONFIDENCE BAR ── */
.conf-bar-wrap{height:8px;background:var(--s3);border-radius:4px;margin:6px 0}
.conf-bar{height:100%;border-radius:4px;transition:width .8s ease}
.stat-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:12px 0}
.stat-box{background:var(--s2);border:1px solid var(--bd);border-radius:10px;
  padding:12px 10px;text-align:center}
.stat-val{font-family:'Syne',sans-serif;font-size:1.5rem;font-weight:700;color:var(--p3)}
.stat-lbl{font-size:.67rem;color:var(--tx3);margin-top:2px;text-transform:uppercase;letter-spacing:.05em}

/* ── TAGS ── */
.tag{display:inline-block;padding:2px 8px;border-radius:5px;font-size:.7rem;
  margin:2px;font-weight:500}
.tag-p{background:#2d1b6944;color:var(--p3)}.tag-pk{background:#4a0d2b44;color:#f9a8d4}
.tag-b{background:#1e3a6044;color:#93c5fd}.tag-g{background:#06433044;color:var(--gr2)}
.tag-y{background:#4a2a0344;color:var(--gold)}.tag-r{background:#45050544;color:#fca5a5}
.tag-cy{background:#0c394944;color:var(--cy2)}

/* ── SECTION HEADING ── */
.sh{font-family:'Syne',sans-serif;font-size:.95rem;font-weight:700;
  margin-bottom:13px;padding-bottom:8px;border-bottom:1px solid var(--bd)}
.muted{color:var(--tx3)}

/* ── TRANSFORM GRID ── */
.t-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin-bottom:16px}
@media(max-width:700px){.t-grid{grid-template-columns:1fr 1fr}}
.t-card{padding:12px 14px;border-radius:10px;border:1px solid var(--bd2);
  cursor:pointer;background:var(--s2);transition:all .2s;text-align:left}
.t-card:hover,.t-card.on{background:var(--s3);border-color:var(--p)}
.t-card.on{box-shadow:0 0 15px rgba(124,58,237,.2)}
.t-card-icon{font-size:1.2rem;margin-bottom:4px;display:block}
.t-card-title{font-weight:700;font-size:.8rem;display:block}
.t-card-desc{color:var(--tx3);font-size:.69rem;margin-top:2px}

/* ── STORY STYLE GRID ── */
.story-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:9px;margin-bottom:18px}
@media(max-width:900px){.story-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:500px){.story-grid{grid-template-columns:1fr}}
.style-card{padding:14px;border-radius:12px;border:1px solid var(--bd2);
  cursor:pointer;background:var(--s2);transition:all .25s;text-align:center}
.style-card:hover,.style-card.on{background:var(--s3);border-color:var(--pk)}
.style-card.on{box-shadow:0 0 20px rgba(219,39,119,.25)}
.style-icon{font-size:1.8rem;margin-bottom:5px;display:block}
.style-name{font-weight:700;font-size:.78rem;display:block}
.style-desc{color:var(--tx3);font-size:.67rem;margin-top:3px;line-height:1.4}

/* ── LEVEL CARDS ── */
.lv-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:11px;margin-bottom:18px}
.lv-card{padding:16px;border-radius:12px;border:2px solid var(--bd);
  cursor:pointer;transition:all .25s;text-align:center}
.lv-card:hover{transform:translateY(-2px)}
.lv-card.sl-b{border-color:var(--cy2);background:rgba(6,182,212,.08)}
.lv-card.sl-i{border-color:var(--p3);background:rgba(124,58,237,.08)}
.lv-card.sl-a{border-color:var(--pk2);background:rgba(219,39,119,.08)}
.lv-icon{font-size:2rem;margin-bottom:6px;display:block}
.lv-name{font-family:'Syne',sans-serif;font-weight:700;font-size:.9rem}
.lv-desc{color:var(--tx3);font-size:.71rem;margin-top:3px;line-height:1.4}

/* ── GLOSSARY ITEM ── */
.glossary-item{background:var(--s2);border:1px solid var(--bd);border-radius:10px;
  padding:13px;margin-bottom:8px}
.glossary-term{font-weight:700;font-size:.87rem;color:var(--p3)}
.glossary-full{font-size:.72rem;color:var(--cy2);margin:2px 0}
.glossary-exp{font-size:.8rem;line-height:1.65;margin-top:4px}
.glossary-ctx{font-size:.72rem;color:var(--tx3);font-style:italic;margin-top:4px;
  border-left:2px solid var(--bd2);padding-left:8px}

/* ── PRE-READING ── */
.prereading-item{display:flex;gap:10px;padding:12px;background:var(--s2);
  border:1px solid var(--bd);border-radius:10px;margin-bottom:7px}
.prereading-icon{font-size:1.4rem;flex-shrink:0}
.prereading-term{font-weight:700;color:var(--p3);margin-bottom:2px;font-size:.84rem}
.prereading-why{font-size:.72rem;color:var(--tx3);margin-bottom:3px}
.prereading-exp{font-size:.8rem;line-height:1.6}

/* ── QUIZ ── */
.quiz-setup-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.qlevel-row{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:12px}
.qlevel-btn{padding:7px 16px;border-radius:8px;border:2px solid var(--bd);
  background:transparent;color:var(--tx);cursor:pointer;font-weight:600;
  font-size:.79rem;transition:all .2s}
.qlevel-btn.on{border-color:var(--p3);background:rgba(124,58,237,.15);color:var(--p3)}
.q-card{background:var(--s1);border:1px solid var(--bd);border-radius:12px;
  padding:18px;margin-bottom:12px;transition:border-color .2s}
.q-card.ok{border-color:var(--gr)}.q-card.ng{border-color:var(--rd)}
.q-meta{font-size:.68rem;color:var(--tx3);margin-bottom:5px;font-weight:600;text-transform:uppercase}
.q-text{font-size:.87rem;line-height:1.65;margin-bottom:13px}
.q-opts{display:grid;gap:7px}
.q-opt{padding:9px 14px;border-radius:8px;border:1px solid var(--bd);cursor:pointer;
  font-size:.8rem;background:var(--s2);color:var(--tx);text-align:left;
  transition:all .2s;width:100%}
.q-opt:hover:not(:disabled){background:var(--s3);border-color:var(--p)}
.q-opt.correct{background:#022c2222;border-color:var(--gr);color:var(--gr2)}
.q-opt.wrong{background:#45050522;border-color:var(--rd);color:#fca5a5}
.q-opt.reveal{background:#022c2211;border-color:var(--gr)}
.q-feedback{margin-top:10px;padding:10px 12px;border-radius:8px;font-size:.77rem;
  display:none;line-height:1.5}
.q-feedback.show{display:block}
.fb-right{background:#022c22;border:1px solid var(--gr);color:var(--gr2)}
.fb-wrong{background:#450505;border:1px solid var(--rd);color:#fca5a5}
.q-input{width:100%;padding:9px 12px;border-radius:8px;border:1px solid var(--bd);
  background:var(--s2);color:var(--tx);font-size:.82rem;margin-bottom:7px;font-family:'DM Sans',sans-serif}
.q-input:focus{outline:none;border-color:var(--p)}
.tf-row{display:flex;gap:9px;margin-bottom:7px}
.tf-btn{flex:1;padding:10px;border-radius:8px;border:1px solid var(--bd);
  cursor:pointer;font-weight:700;font-size:.87rem;background:var(--s2);
  color:var(--tx);transition:all .2s}
.tf-btn:hover:not(:disabled){border-color:var(--p)}
.ord-list{display:flex;flex-direction:column;gap:5px;margin-bottom:9px}
.ord-item{padding:9px 13px;border-radius:8px;background:var(--s2);
  border:1px solid var(--bd);font-size:.8rem;cursor:grab;
  display:flex;align-items:center;gap:8px}
.ord-handle{color:var(--tx3);font-size:.9rem}

/* ── QUIZ RESULTS ── */
.result-score{text-align:center;padding:24px 0 16px}
.big-score{font-family:'Syne',sans-serif;font-size:4.5rem;font-weight:800;
  background:linear-gradient(90deg,var(--p3),var(--pk2));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent}
.skill-item{margin-bottom:13px}
.skill-row{display:flex;justify-content:space-between;font-size:.77rem;margin-bottom:5px}
.skill-bar{height:9px;border-radius:5px;background:var(--s3)}
.skill-fill{height:100%;border-radius:5px;transition:width .8s ease}

/* ── TRAINING TAB ── */
.train-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.train-form{display:flex;flex-direction:column;gap:11px}
.form-label{font-size:.77rem;color:var(--tx3);display:block;margin-bottom:4px}
.form-input,.form-textarea,.form-select{width:100%;padding:9px 12px;border-radius:9px;
  border:1px solid var(--bd);background:var(--s2);color:var(--tx);
  font-size:.82rem;font-family:'DM Sans',sans-serif}
.form-input:focus,.form-textarea:focus,.form-select:focus{outline:none;border-color:var(--p)}
.form-textarea{resize:vertical;min-height:80px}
.stat-row{display:flex;align-items:center;justify-content:space-between;
  padding:10px 0;border-bottom:1px solid var(--bd);font-size:.8rem}
.stat-row:last-child{border:none}
.correction-item{background:var(--s2);border:1px solid var(--bd);border-radius:8px;
  padding:10px 13px;margin-bottom:7px;font-size:.79rem}
.corr-before{color:#fca5a5;font-size:.74rem;margin-bottom:3px}
.corr-after{color:var(--gr2);font-size:.74rem}
.eval-result{background:linear-gradient(135deg,var(--s2),var(--s3));
  border:1px solid var(--bd2);border-radius:12px;padding:20px;text-align:center}
.eval-metric{display:inline-block;margin:8px 14px}
.eval-num{font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:700;color:var(--p3)}
.eval-label{font-size:.7rem;color:var(--tx3);display:block;margin-top:2px}

/* ── PROGRESS BAR ── */
.quiz-progress{display:flex;align-items:center;gap:12px;margin-bottom:16px}
.qp-bar{flex:1;height:5px;background:var(--s3);border-radius:3px}
.qp-fill{height:100%;border-radius:3px;
  background:linear-gradient(90deg,var(--p),var(--pk));transition:width .4s}

/* ── SPINNER ── */
.spinner{display:inline-block;width:18px;height:18px;border:2.5px solid var(--s3);
  border-top-color:var(--p);border-radius:50%;animation:spin .7s linear infinite;vertical-align:middle}
@keyframes spin{to{transform:rotate(360deg)}}
.loading-bar{position:fixed;top:64px;left:0;right:0;height:2px;z-index:999;
  background:linear-gradient(90deg,var(--p),var(--pk),var(--cy));
  transform:scaleX(0);transform-origin:left;transition:transform .3s;display:none}
.loading-bar.show{display:block;animation:load 1.5s infinite}
@keyframes load{0%{transform:scaleX(0)}50%{transform:scaleX(.7)}100%{transform:scaleX(1)}}

/* ── STORY RESULT ── */
.story-meta{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}
.story-tag{padding:4px 12px;border-radius:20px;font-size:.72rem;font-weight:600;
  background:rgba(219,39,119,.15);border:1px solid rgba(219,39,119,.3);color:#f9a8d4}

/* ── SPACING UTILS ── */
.mt8{margin-top:8px}.mt12{margin-top:12px}.mt16{margin-top:16px}.mt20{margin-top:20px}
.flex{display:flex}.gap8{gap:8px}.gap12{gap:12px}.f1{flex:1}.center{text-align:center}
.hidden{display:none}

/* ── SCROLLBAR ── */
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:var(--s1)}
::-webkit-scrollbar-thumb{background:var(--bd2);border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:var(--p)}

/* ── PAGE TITLE ── */
.page-title{font-family:'Syne',sans-serif;font-size:1.6rem;font-weight:800;margin-bottom:6px}
.page-sub{color:var(--tx3);font-size:.83rem;margin-bottom:24px}
</style>
</head>
<body>

<div class="loading-bar" id="loading-bar"></div>

<!-- ── HEADER ── -->
<header class="hdr">
  <div class="logo">
    <div class="logo-icon">📚</div>
    <div>
      <div class="logo-text">IntelliDoc AI</div>
      <div class="logo-sub">by Hriday Jadhav &amp; Sanmay Anand</div>
    </div>
  </div>
  <nav class="nav">
    <button class="nav-btn active" onclick="sw('ocr',this)"><div class="nav-dot"></div>🔍 OCR Pipeline</button>
    <button class="nav-btn" onclick="sw('transform',this)"><div class="nav-dot"></div>✨ Transform</button>
    <button class="nav-btn" onclick="sw('learn',this)"><div class="nav-dot"></div>📖 Learn</button>
    <button class="nav-btn" onclick="sw('story',this)"><div class="nav-dot"></div>🎭 Story Mode</button>
    <button class="nav-btn" onclick="sw('quiz',this)"><div class="nav-dot"></div>🧠 Quiz</button>
    <button class="nav-btn" onclick="sw('train',this)"><div class="nav-dot"></div>⚙️ Train</button>
  </nav>
  <div class="hdr-right">
    <div class="status-pill"><div class="status-dot"></div><span>System Ready</span></div>
  </div>
</header>

<!-- ══════════════════════════════════════════════ -->
<!-- OCR PIPELINE TAB                              -->
<!-- ══════════════════════════════════════════════ -->
<div id="pane-ocr" class="pane active wrap">
  <div class="page-title">🔍 OCR Pipeline</div>
  <div class="page-sub">Upload any PDF or image — scanned, photographed, or digital. AI extracts every word.</div>

  <div class="pipeline" id="pipeline">
    <span class="pipe-step" id="ps-upload">📄 Upload</span>
    <span class="pipe-arrow">→</span>
    <span class="pipe-step" id="ps-vision">👁️ Vision Preproc</span>
    <span class="pipe-arrow">→</span>
    <span class="pipe-step" id="ps-layout">📐 Layout</span>
    <span class="pipe-arrow">→</span>
    <span class="pipe-step" id="ps-ocr">🔍 Tesseract</span>
    <span class="pipe-arrow">→</span>
    <span class="pipe-step" id="ps-conf">📊 Confidence</span>
    <span class="pipe-arrow">→</span>
    <span class="pipe-step" id="ps-nlp">🧠 NLP</span>
    <span class="pipe-arrow">→</span>
    <span class="pipe-step" id="ps-output">✨ Output</span>
  </div>

  <div class="g2">
    <!-- Upload -->
    <div class="card">
      <div class="card-title">📤 Upload Document <span class="chip chip-p">Step 1</span></div>
      <div class="upload-zone" id="dz" onclick="document.getElementById('fi').click()">
        <div class="upload-icon">📁</div>
        <div class="upload-title">Drop PDF or Image here</div>
        <div class="upload-sub">Any quality — scanned, photographed, or clear</div>
        <div class="upload-types">
          <span class="type-tag">PDF</span>
          <span class="type-tag">PNG</span>
          <span class="type-tag">JPG</span>
          <span class="type-tag">TIFF</span>
          <span class="type-tag">BMP</span>
        </div>
      </div>
      <input type="file" id="fi" accept=".pdf,.png,.jpg,.jpeg,.bmp,.tiff,.gif" style="display:none">
      
      <!-- Image Preview Area -->
      <div class="img-preview-wrap" id="img-preview-wrap">
        <img id="img-preview" class="img-preview" alt="Preview">
        <div class="img-preview-overlay" id="img-preview-info"></div>
      </div>

      <div class="alert alert-info mt12 hidden" id="fi-info">📄 <strong id="fi-name"></strong></div>
      <div class="mt12">
        <button class="btn btn-primary btn-full" id="ocr-btn" onclick="runOCR()" disabled>
          <span class="spinner" id="ocr-spinner" style="display:none"></span>
          🔍 Run OCR Pipeline
        </button>
      </div>
    </div>

    <!-- Confidence Panel -->
    <div class="card">
      <div class="card-title">📊 Confidence &amp; Quality <span class="chip chip-g">Uncertainty AI</span></div>
      <div class="alert alert-info" id="conf-ph">Process a document to see confidence analysis.</div>
      <div id="conf-c" class="hidden">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="font-size:.8rem;color:var(--tx3)">Overall OCR Confidence</span>
          <span id="cv" style="font-weight:700;font-family:'Syne',sans-serif;font-size:1.2rem"></span>
        </div>
        <div class="conf-bar-wrap"><div class="conf-bar" id="cbar"></div></div>
        <div class="stat-grid">
          <div class="stat-box"><div class="stat-val" id="sp">—</div><div class="stat-lbl">Pages</div></div>
          <div class="stat-box"><div class="stat-val" id="sw2">—</div><div class="stat-lbl">Words</div></div>
          <div class="stat-box"><div class="stat-val" id="sq">—</div><div class="stat-lbl">Quality</div></div>
        </div>
        <div class="mt12">
          <div style="font-size:.7rem;color:var(--tx3);text-transform:uppercase;margin-bottom:5px">⚠️ Ambiguous Characters</div>
          <div id="amb"></div>
        </div>
        <div class="mt10">
          <div style="font-size:.7rem;color:var(--tx3);text-transform:uppercase;margin-bottom:5px">📑 Layout Regions</div>
          <div id="reg"></div>
        </div>
      </div>
    </div>

    <!-- Extracted Text -->
    <div class="card">
      <div class="card-title">📝 Extracted Text <span class="chip chip-b">OCR Output</span></div>
      <div class="output-box" id="raw-out">Run the OCR pipeline to see extracted text here…</div>
      <div class="output-box-actions mt8">
        <button class="btn btn-secondary btn-sm" onclick="cp('raw-out')">📋 Copy</button>
        <button class="btn btn-secondary btn-sm" onclick="dl('raw-out','extracted.txt')">💾 Save .txt</button>
        <button class="btn btn-secondary btn-sm" id="apply-corrections-btn" onclick="applyCorrections()" style="display:none">🔧 Apply Learned Corrections</button>
      </div>
    </div>

    <!-- NLP Analysis -->
    <div class="card">
      <div class="card-title">🧠 NLP Analysis <span class="chip chip-cy">Understanding</span></div>
      <div class="alert alert-info" id="nlp-ph">NLP analysis appears after OCR completes.</div>
      <div id="nlp-c" class="hidden">
        <div style="font-size:.7rem;color:var(--tx3);text-transform:uppercase;margin-bottom:5px">Document Type</div>
        <div id="doc-t" class="mb8"></div>
        <div style="font-size:.7rem;color:var(--tx3);text-transform:uppercase;margin:10px 0 5px">Keywords</div>
        <div id="kws"></div>
        <div style="font-size:.7rem;color:var(--tx3);text-transform:uppercase;margin:10px 0 5px">Named Entities</div>
        <div id="ents"></div>
        <div style="font-size:.7rem;color:var(--tx3);text-transform:uppercase;margin:10px 0 5px">Sentiment · Language</div>
        <div id="senti"></div>
      </div>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════ -->
<!-- TRANSFORM TAB                                  -->
<!-- ══════════════════════════════════════════════ -->
<div id="pane-transform" class="pane wrap">
  <div class="page-title">✨ Text Transformation</div>
  <div class="page-sub">Apply powerful transformations to your extracted text — summarize, extract, redact, format.</div>
  <div class="alert alert-warn hidden" id="t-warn">Run OCR first, then come here to transform the text.</div>
  <div class="card">
    <div class="card-title">Choose Transformation Mode</div>
    <div class="t-grid">
      <button class="t-card on" onclick="selT(this,'summarize')">
        <span class="t-card-icon">📋</span>
        <span class="t-card-title">Summarization</span>
        <span class="t-card-desc">Extract the most important sentences</span>
      </button>
      <button class="t-card" onclick="selT(this,'extract')">
        <span class="t-card-icon">🔎</span>
        <span class="t-card-title">Info Extraction</span>
        <span class="t-card-desc">Entities, statistics, key-values</span>
      </button>
      <button class="t-card" onclick="selT(this,'redact')">
        <span class="t-card-icon">🔒</span>
        <span class="t-card-title">Redaction</span>
        <span class="t-card-desc">Remove PII: emails, phones, money</span>
      </button>
      <button class="t-card" onclick="selT(this,'classify')">
        <span class="t-card-icon">🏷️</span>
        <span class="t-card-title">Classify &amp; Tag</span>
        <span class="t-card-desc">Document type + semantic tags</span>
      </button>
      <button class="t-card" onclick="selT(this,'format_bullet')">
        <span class="t-card-icon">•</span>
        <span class="t-card-title">Bullet Points</span>
        <span class="t-card-desc">Structured bullet list format</span>
      </button>
      <button class="t-card" onclick="selT(this,'format_markdown')">
        <span class="t-card-icon">📄</span>
        <span class="t-card-title">Markdown</span>
        <span class="t-card-desc">Clean markdown output</span>
      </button>
    </div>
    <button class="btn btn-primary" id="t-btn" onclick="runT()" disabled>✨ Apply Transformation</button>
    <div class="alert alert-info mt12 hidden" id="t-ph">Run OCR first, then apply a transformation.</div>
    <div class="output-box mt12 mono hidden" id="t-out"></div>
    <div class="output-box-actions mt8 hidden" id="t-actions">
      <button class="btn btn-secondary btn-sm" onclick="cp('t-out')">📋 Copy</button>
      <button class="btn btn-secondary btn-sm" onclick="dl('t-out','transformed.txt')">💾 Save</button>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════ -->
<!-- LEARN TAB                                       -->
<!-- ══════════════════════════════════════════════ -->
<div id="pane-learn" class="pane wrap">
  <div class="page-title">📖 Adaptive Learning View</div>
  <div class="page-sub">See your document explained at your exact level — beginner analogies to advanced technical depth.</div>
  <div class="alert alert-info" id="lph">Run OCR on a document first, then come here to get a personalized learning view.</div>
  <div id="lc" class="hidden">
    <h3 class="sh">Step 1 — Choose Your Level</h3>
    <div class="lv-grid">
      <div class="lv-card" id="lv-b" onclick="setLv('beginner')">
        <span class="lv-icon">🌱</span>
        <div class="lv-name">Beginner</div>
        <div class="lv-desc">New to this topic — plain English with everyday analogies</div>
      </div>
      <div class="lv-card sl-i" id="lv-i" onclick="setLv('intermediate')">
        <span class="lv-icon">📘</span>
        <div class="lv-name">Intermediate</div>
        <div class="lv-desc">Know the basics — explain technical terms and architecture</div>
      </div>
      <div class="lv-card" id="lv-a" onclick="setLv('advanced')">
        <span class="lv-icon">🚀</span>
        <div class="lv-name">Advanced</div>
        <div class="lv-desc">Expert — precise definitions and implementation detail</div>
      </div>
    </div>
    <h3 class="sh">Step 2 — Your Learning Intent</h3>
    <div style="display:grid;gap:12px;max-width:520px;margin-bottom:18px">
      <div>
        <label class="form-label">What is your main goal?</label>
        <select class="form-select" id="ig">
          <option value="understand">Understand the concepts</option>
          <option value="present">Present / explain to others</option>
          <option value="implement">Build / implement this</option>
          <option value="exam">Prepare for exam / viva</option>
        </select>
      </div>
      <div>
        <label class="form-label">Topics you want extra help with:</label>
        <div style="display:flex;flex-direction:column;gap:5px" id="wt">
          <label style="display:flex;align-items:center;gap:7px;cursor:pointer;font-size:.8rem">
            <input type="checkbox" value="OCR" style="accent-color:var(--p);width:14px;height:14px"> OCR / Text Recognition</label>
          <label style="display:flex;align-items:center;gap:7px;cursor:pointer;font-size:.8rem">
            <input type="checkbox" value="CV" style="accent-color:var(--p);width:14px;height:14px"> Computer Vision / Image Processing</label>
          <label style="display:flex;align-items:center;gap:7px;cursor:pointer;font-size:.8rem">
            <input type="checkbox" value="NLP" style="accent-color:var(--p);width:14px;height:14px"> NLP / Language Processing</label>
          <label style="display:flex;align-items:center;gap:7px;cursor:pointer;font-size:.8rem">
            <input type="checkbox" value="ML" style="accent-color:var(--p);width:14px;height:14px"> Machine Learning / Training</label>
        </div>
      </div>
      <div>
        <label class="form-label">Any specific confusions? (optional)</label>
        <textarea class="form-textarea" id="in2" placeholder="e.g. I don't understand what confidence scores mean…"></textarea>
      </div>
    </div>
    <button class="btn btn-cyan" onclick="runExp()">📖 Generate My Learning View</button>

    <div id="exp-out" class="mt20 hidden">
      <!-- PDF Download Buttons -->
      <div class="card mt16" style="background:linear-gradient(135deg,rgba(124,58,237,.08),rgba(6,182,212,.05));border-color:rgba(124,58,237,.3)">
        <div class="card-title">📥 Download as PDF</div>
        <div style="display:flex;gap:10px;flex-wrap:wrap">
          <button class="btn btn-primary" onclick="downloadExpandPDF()" id="expand-pdf-btn">
            <span class="spinner" id="expand-pdf-spinner" style="display:none"></span>
            📄 Download Expanded Learning PDF
          </button>
          <button class="btn btn-cyan" onclick="downloadShrinkPDF()" id="shrink-pdf-btn">
            <span class="spinner" id="shrink-pdf-spinner" style="display:none"></span>
            📋 Download Condensed Summary PDF
          </button>
        </div>
        <div style="font-size:.74rem;color:var(--tx3);margin-top:8px">
          Expanded PDF: full annotated text + glossary at your level. &nbsp;|&nbsp; 
          Summary PDF: key sentences condensed into a clean document.
        </div>
      </div>

      <h3 class="sh mt16">📚 Pre-Reading — Understand These First</h3>
      <div id="pre-items"></div>
      <div class="mt16">
        <h3 class="sh">📄 Annotated Text <span style="font-size:.72rem;color:var(--tx3)">(key terms annotated inline)</span></h3>
        <div class="output-box" id="ann-t"></div>
      </div>
      <div id="simp-s" class="hidden mt16">
        <h3 class="sh">🌱 Simplified Plain-Language Version</h3>
        <div class="output-box" id="simp-t"></div>
      </div>
      <div class="mt16">
        <h3 class="sh">📖 Full Glossary — Terms Explained at Your Level</h3>
        <div id="gl-items"></div>
      </div>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════ -->
<!-- STORY MODE TAB                                  -->
<!-- ══════════════════════════════════════════════ -->
<div id="pane-story" class="pane wrap">
  <div class="page-title">🎭 Story Mode</div>
  <div class="page-sub">Transform any textbook chapter or academic PDF into a gripping story. Same facts, different soul.</div>
  <div class="alert alert-story" style="display:block">
    ✨ <strong>How it works:</strong> Upload a PDF and run OCR first. Then pick a narrative style below — the AI rewrites the content as that story type. The <em>facts and concepts never change</em>, only the way they're told.
  </div>
  <div class="alert alert-warn hidden" id="story-warn">Please run OCR on a document first, then come back here.</div>

  <div class="card mt16">
    <div class="card-title">Step 1 — Choose Your Narrative Style</div>
    <div class="story-grid" id="story-grid">
      <!-- Dynamically populated -->
    </div>

    <div>
      <label class="form-label">Optional: Add character names to personalize the story</label>
      <input class="form-input" id="story-chars" placeholder="e.g. protagonist: Arjun, mentor: Dr. Meera (leave blank for auto)">
    </div>

    <div class="mt12">
      <button class="btn btn-story btn-full" id="story-btn" onclick="runStory()" disabled>
        <span class="spinner" id="story-spinner" style="display:none"></span>
        🎭 Generate Story
      </button>
    </div>
  </div>

  <div id="story-out" class="mt20 hidden">
    <div class="card">
      <div class="card-title">📖 Your Story</div>
      <div class="story-meta" id="story-meta"></div>
      <div class="output-box story-mode" id="story-text"></div>
      <div class="output-box-actions mt8">
        <button class="btn btn-secondary btn-sm" onclick="cp('story-text')">📋 Copy Story</button>
        <button class="btn btn-secondary btn-sm" onclick="dl('story-text','story.txt')">💾 Save as .txt</button>
      </div>
    </div>
    <div class="g2 mt16">
      <div class="card">
        <div class="card-title">📊 Story Stats</div>
        <div id="story-stats"></div>
      </div>
      <div class="card">
        <div class="card-title">🧩 Concepts Woven In</div>
        <div id="story-concepts"></div>
      </div>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════ -->
<!-- QUIZ TAB                                        -->
<!-- ══════════════════════════════════════════════ -->
<div id="pane-quiz" class="pane wrap">
  <div class="page-title">🧠 Quiz &amp; Level Assessment</div>
  <div class="page-sub">Test your understanding with questions generated directly from your document.</div>
  <div class="alert alert-info" id="qph">📄 Upload a document and run OCR first — then your quiz will be generated directly from your document's content.</div>

  <div id="q-setup" class="hidden">
    <div class="quiz-setup-grid">
      <div class="card">
        <div class="card-title">🎯 Quiz Configuration</div>
        <label class="form-label mt8">Difficulty level:</label>
        <div class="qlevel-row">
          <button class="qlevel-btn" onclick="setQL('beginner',this)">🌱 Beginner</button>
          <button class="qlevel-btn on" onclick="setQL('intermediate',this)">📘 Intermediate</button>
          <button class="qlevel-btn" onclick="setQL('advanced',this)">🚀 Advanced</button>
        </div>
        <label class="form-label">Number of questions:</label>
        <div class="qlevel-row">
          <button class="qlevel-btn" onclick="setQN(5,this)">5 Quick</button>
          <button class="qlevel-btn on" onclick="setQN(8,this)">8 Standard</button>
          <button class="qlevel-btn" onclick="setQN(12,this)">12 Full</button>
        </div>
        <button class="btn btn-primary btn-full mt12" onclick="startQuiz()">🚀 Start Quiz</button>
      </div>
      <div class="card">
        <div class="card-title">ℹ️ What gets tested?</div>
        <div style="font-size:.8rem;line-height:1.9;color:var(--tx3)">
          All questions come <strong style="color:var(--p3)">directly from your uploaded document</strong>:<br>
          📌 <strong style="color:var(--tx)">Document MCQ</strong> — Which statement about X is in the document?<br>
          📌 <strong style="color:var(--tx)">Acronym expansion</strong> — What does OCR stand for?<br>
          📌 <strong style="color:var(--tx)">Fill-in-blank</strong> — from actual document sentences<br>
          📌 <strong style="color:var(--tx)">True / False</strong> — based on document statements<br>
          📌 <strong style="color:var(--tx)">Step ordering</strong> — arrange pipeline steps from document<br><br>
          After quiz: <strong style="color:var(--p3)">skill meters, weak area detection</strong>, and adaptive content recommendation.
        </div>
      </div>
    </div>
  </div>

  <!-- Quiz Questions -->
  <div id="q-qs" class="hidden">
    <div class="quiz-progress">
      <span style="font-size:.8rem;color:var(--tx3)">Q <span id="qcur">1</span>/<span id="qtot">8</span></span>
      <div class="qp-bar"><div class="qp-fill" id="qpf"></div></div>
      <button class="btn btn-secondary btn-sm" onclick="submitQ()">Submit All →</button>
    </div>
    <div id="q-cont"></div>
    <div class="center mt16">
      <button class="btn btn-green" onclick="submitQ()">✅ Submit &amp; See Results</button>
    </div>
  </div>

  <!-- Quiz Results -->
  <div id="q-res" class="hidden">
    <div class="g2">
      <div class="card">
        <div class="result-score">
          <div class="big-score" id="res-s">—</div>
          <div style="color:var(--tx3);margin-top:3px">Overall Score</div>
          <div class="mt8" id="res-l"></div>
        </div>
        <div style="display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin-top:8px" id="res-a"></div>
      </div>
      <div class="card">
        <div class="card-title">📊 Skill Meters</div>
        <div id="skm"></div>
      </div>
      <div class="card full">
        <div class="card-title">💡 Personalized Recommendations</div>
        <div id="recs"></div>
      </div>
      <div class="card full">
        <div class="card-title">📋 Answer Review</div>
        <div id="ar"></div>
      </div>
    </div>
    <div class="center mt16">
      <button class="btn btn-secondary" onclick="resetQ()">🔁 Retake Quiz</button>
      <button class="btn btn-cyan mt8 ml8" onclick="sw('learn',document.querySelector('.nav-btn:nth-child(3))'))">📖 Go to Learning View →</button>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════ -->
<!-- TRAINING TAB                                    -->
<!-- ══════════════════════════════════════════════ -->
<div id="pane-train" class="pane wrap">
  <div class="page-title">⚙️ Model Training &amp; Improvement</div>
  <div class="page-sub">The ML feedback loop — teach the system its mistakes. It gets smarter with every correction.</div>

  <div class="alert alert-info" style="display:block">
    🔄 <strong>How training works:</strong> When OCR gets something wrong, you correct it here. The system learns the pattern and auto-corrects it next time. After 50–100 corrections, accuracy improves noticeably.
  </div>

  <div class="train-grid mt16">
    <!-- Add Correction -->
    <div class="card">
      <div class="card-title">➕ Add Manual Correction</div>
      <div class="train-form">
        <div>
          <label class="form-label">What the OCR got WRONG (paste OCR output):</label>
          <textarea class="form-textarea" id="tr-wrong" placeholder="e.g. The algorithrn processes irnages using CNN…" style="border-color:rgba(239,68,68,.4)"></textarea>
        </div>
        <div>
          <label class="form-label">What it SHOULD say (the correct version):</label>
          <textarea class="form-textarea" id="tr-correct" placeholder="e.g. The algorithm processes images using CNN…" style="border-color:rgba(52,211,153,.4)"></textarea>
        </div>
        <div>
          <label class="form-label">Source document (optional):</label>
          <input class="form-input" id="tr-source" placeholder="e.g. NCERT Physics Chapter 12">
        </div>
        <button class="btn btn-green" onclick="addCorrection()">✅ Save Correction</button>
        <div id="tr-msg" class="hidden"></div>
      </div>
    </div>

    <!-- Test Post-Processor -->
    <div class="card">
      <div class="card-title">🧪 Test Auto-Correction</div>
      <div class="form-label">Paste OCR text to auto-correct using learned patterns:</div>
      <textarea class="form-textarea mt8" id="tr-test-in" placeholder="Paste OCR output here to see learned corrections applied…" style="min-height:100px"></textarea>
      <button class="btn btn-cyan mt8" onclick="testCorrections()">🔧 Apply Learned Corrections</button>
      <div id="tr-test-out" class="hidden mt12">
        <div style="font-size:.75rem;color:var(--tx3);margin-bottom:6px">Corrected Output:</div>
        <div class="output-box mono" id="tr-corrected-text"></div>
        <div id="tr-changes" class="mt8"></div>
      </div>
    </div>

    <!-- Statistics -->
    <div class="card">
      <div class="card-title">📊 Training Statistics</div>
      <div id="train-stats">
        <div style="font-size:.8rem;color:var(--tx3);margin-bottom:12px">Loading stats…</div>
      </div>
      <button class="btn btn-secondary btn-sm mt12" onclick="loadTrainStats()">🔄 Refresh Stats</button>
    </div>

    <!-- Evaluate -->
    <div class="card">
      <div class="card-title">📈 Evaluate Accuracy</div>
      <div style="font-size:.8rem;color:var(--tx3);line-height:1.7;margin-bottom:14px">
        Run evaluation on all stored correction pairs to measure:<br>
        <strong style="color:var(--tx)">CER</strong> (Character Error Rate) — lower is better, 0 = perfect<br>
        <strong style="color:var(--tx)">WER</strong> (Word Error Rate) — lower is better<br>
        <strong style="color:var(--tx)">Accuracy %</strong> — overall quality score
      </div>
      <button class="btn btn-primary" onclick="runEval()">📈 Run Evaluation</button>
      <div id="eval-result" class="hidden mt12"></div>
    </div>
  </div>

  <!-- Recent Corrections -->
  <div class="card mt16">
    <div class="card-title">📋 Recent Corrections <span id="corr-count" class="chip chip-g"></span></div>
    <div id="corrections-list">
      <div style="font-size:.8rem;color:var(--tx3)">No corrections yet. Add some above.</div>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════ -->
<!-- JAVASCRIPT                                      -->
<!-- ══════════════════════════════════════════════ -->
<script>
let txt='', ocrR=null, cpts=null, selTr='summarize', lvl='intermediate';
let qlvl='intermediate', qn=8, qs=[], ua={};
let selStyle='romantic';

// ── Navigation ──────────────────────────────────
function sw(n, el){
  document.querySelectorAll('.pane').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById('pane-'+n).classList.add('active');
  if(el) el.classList.add('active');
  if(n==='train') loadTrainStats();
}

// ── Loading bar ─────────────────────────────────
function showLoad(){document.getElementById('loading-bar').classList.add('show');}
function hideLoad(){document.getElementById('loading-bar').classList.remove('show');}

// ── File upload handling ─────────────────────────
const fi=document.getElementById('fi');
fi.addEventListener('change',e=>{if(e.target.files[0])handleFile(e.target.files[0])});
const dz=document.getElementById('dz');
dz.addEventListener('dragover',e=>{e.preventDefault();dz.classList.add('over')});
dz.addEventListener('dragleave',()=>dz.classList.remove('over'));
dz.addEventListener('drop',e=>{e.preventDefault();dz.classList.remove('over');
  if(e.dataTransfer.files[0])handleFile(e.dataTransfer.files[0])});

function handleFile(f){
  const kb=(f.size/1024).toFixed(1);
  document.getElementById('fi-name').textContent=f.name+' ('+kb+' KB)';
  document.getElementById('fi-info').classList.remove('hidden');
  document.getElementById('ocr-btn').disabled=false;
  document.getElementById('story-btn').disabled=false;
  fi._f=f;
  // Show image preview if it's an image
  const ext=f.name.split('.').pop().toLowerCase();
  if(['png','jpg','jpeg','bmp','tiff','gif'].includes(ext)){
    const reader=new FileReader();
    reader.onload=e=>{
      const wrap=document.getElementById('img-preview-wrap');
      const img=document.getElementById('img-preview');
      img.src=e.target.result;
      wrap.style.display='block';
      document.getElementById('img-preview-info').textContent=
        f.name+' · '+f.size>0?(f.size/1024).toFixed(0)+' KB':'';
    };
    reader.readAsDataURL(f);
  } else {
    document.getElementById('img-preview-wrap').style.display='none';
  }
}

// ── Pipeline step highlighting ───────────────────
const pipeSteps=['upload','vision','layout','ocr','conf','nlp','output'];
let pipeTimer=null;
function animatePipeline(){
  let i=0;
  pipeSteps.forEach(s=>document.getElementById('ps-'+s).className='pipe-step');
  document.getElementById('ps-upload').className='pipe-step done';
  pipeTimer=setInterval(()=>{
    if(i<pipeSteps.length){
      if(i>0) document.getElementById('ps-'+pipeSteps[i-1]).className='pipe-step done';
      document.getElementById('ps-'+pipeSteps[i]).className='pipe-step active';
      i++;
    }else{
      clearInterval(pipeTimer);
      pipeSteps.forEach(s=>document.getElementById('ps-'+s).className='pipe-step done');
    }
  },600);
}

// ── OCR ──────────────────────────────────────────
async function runOCR(){
  if(!fi._f)return;
  animatePipeline();
  showLoad();
  document.getElementById('ocr-spinner').style.display='inline-block';
  document.getElementById('ocr-btn').disabled=true;
  document.getElementById('raw-out').textContent='Processing through AI pipeline…';
  const fd=new FormData();fd.append('file',fi._f);
  try{
    const r=await fetch('/api/ocr',{method:'POST',body:fd});
    const d=await r.json();
    if(d.error)throw new Error(d.error);
    ocrR=d;txt=d.full_text;
    document.getElementById('raw-out').textContent=txt||'No text extracted.';
    // Unlock apply corrections button
    document.getElementById('apply-corrections-btn').style.display='inline-flex';

    // Confidence panel
    document.getElementById('conf-ph').classList.add('hidden');
    document.getElementById('conf-c').classList.remove('hidden');
    const conf=Math.round(d.overall_confidence||0);
    document.getElementById('cv').textContent=conf+'%';
    const bar=document.getElementById('cbar');
    bar.style.width=conf+'%';
    bar.style.background=conf>=80?'var(--gr)':conf>=60?'var(--yw)':'var(--rd)';
    document.getElementById('sp').textContent=d.total_pages||1;
    document.getElementById('sw2').textContent=txt.split(/\s+/).filter(Boolean).length;
    document.getElementById('sq').textContent=conf>=80?'HIGH ✅':conf>=60?'MED ⚠️':'LOW ❌';
    const amb=d.pages?.[0]?.confidence?.ambiguous_chars||[];
    document.getElementById('amb').innerHTML=amb.length?
      amb.map(a=>`<span class="tag tag-pk">${a.pattern} ×${a.count}</span>`).join(''):
      '<span class="muted" style="font-size:.77rem">None detected ✓</span>';
    const rgs=d.pages?.[0]?.regions||[],rc={};
    rgs.forEach(r=>rc[r.type]=(rc[r.type]||0)+1);
    document.getElementById('reg').innerHTML=Object.entries(rc)
      .map(([t,c])=>`<span class="tag tag-b">${t}: ${c}</span>`).join('')||
      '<span class="muted" style="font-size:.77rem">—</span>';

    // Enable tabs
    document.getElementById('t-btn').disabled=false;
    document.getElementById('story-btn').disabled=false;
    await runNLP();
    const cr=await fetch('/api/concepts',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({text:txt})});
    const cd=await cr.json();
    if(!cd.error){
      cpts=cd;
      document.getElementById('lph').classList.add('hidden');
      document.getElementById('lc').classList.remove('hidden');
      document.getElementById('qph').classList.add('hidden');
      document.getElementById('q-setup').classList.remove('hidden');
    }
  }catch(e){
    document.getElementById('raw-out').textContent='❌ Error: '+e.message+
      '\n\nIf PDF fails: install Poppler and check README.md';
    pipeSteps.forEach(s=>document.getElementById('ps-'+s).className='pipe-step');
  }
  document.getElementById('ocr-spinner').style.display='none';
  document.getElementById('ocr-btn').disabled=false;
  hideLoad();
}

async function runNLP(){
  const r=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({text:txt})});
  const d=await r.json();
  document.getElementById('nlp-ph').classList.add('hidden');
  document.getElementById('nlp-c').classList.remove('hidden');
  const confMap={'Academic/Research':'chip-b','Legal/Contract':'chip-y','Medical/Health':'chip-g',
    'Financial':'chip-y','Technical/Engineering':'chip-cy','News/Article':'chip-pk','Educational':'chip-g'};
  const dt=d.classification?.document_type||'Unknown';
  document.getElementById('doc-t').innerHTML=
    `<span class="chip ${confMap[dt]||'chip-p'}">${dt}</span> `+
    `<span class="chip chip-g">${d.classification?.type_confidence||0}% confidence</span>`;
  document.getElementById('kws').innerHTML=(d.keywords||[])
    .map(([w,c])=>`<span class="tag tag-p">${w} <span style="opacity:.5;font-size:.65rem">${c}</span></span>`).join('');
  const tc={EMAIL:'tag-pk',PHONE:'tag-pk',DATE:'tag-b',URL:'tag-b',
    CAPITALIZED_PHRASE:'tag-g',ACRONYM:'tag-g'};
  let eh='';
  for(const[t,v]of Object.entries(d.entities||{})){
    if(v.length)eh+=`<span class="tag ${tc[t]||'tag-p'}">${t}: ${v.slice(0,3).join(', ')}</span>`;
  }
  document.getElementById('ents').innerHTML=eh||'<span class="muted" style="font-size:.77rem">None found</span>';
  const sm={Positive:'tag-g',Negative:'tag-r',Neutral:'tag-b'};
  const se=d.classification?.sentiment||'Neutral';
  document.getElementById('senti').innerHTML=
    `<span class="tag ${sm[se]}">${se}</span> `+
    `<span class="tag tag-b">${d.classification?.language||'English'}</span>`;
}

// ── Apply learned corrections ────────────────────
async function applyCorrections(){
  if(!txt)return;
  const r=await fetch('/api/apply_corrections',{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({text:txt})});
  const d=await r.json();
  if(d.error){alert(d.error);return;}
  txt=d.corrected_text;
  document.getElementById('raw-out').textContent=txt;
  if(d.changes.length){
    alert(`✅ Applied ${d.changes.length} corrections:\n`+d.changes.join('\n'));
  } else {
    alert('No learned corrections to apply — the text looks good already!');
  }
}

// ── Transform ────────────────────────────────────
function selT(btn,t){
  document.querySelectorAll('.t-card').forEach(b=>b.classList.remove('on'));
  btn.classList.add('on');selTr=t;
}
async function runT(){
  if(!txt){document.getElementById('t-ph').classList.remove('hidden');return;}
  document.getElementById('t-ph').classList.add('hidden');
  const out=document.getElementById('t-out');
  out.classList.remove('hidden');out.textContent='Transforming…';
  showLoad();
  try{
    const r=await fetch('/api/transform',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify({text:txt,transform:selTr})});
    const d=await r.json();
    if(d.error)throw new Error(d.error);
    out.textContent=typeof d.result==='object'?JSON.stringify(d.result,null,2):d.result;
    document.getElementById('t-actions').classList.remove('hidden');
  }catch(e){out.textContent='❌ '+e.message;}
  hideLoad();
}

// ── Learn ────────────────────────────────────────
function setLv(l){
  lvl=l;
  ['b','i','a'].forEach((x,i)=>{
    const ll=['beginner','intermediate','advanced'][i];
    document.getElementById('lv-'+x).className='lv-card'+(l===ll?' sl-'+x:'');
  });
}
async function runExp(){
  if(!txt||!cpts)return;
  const wk=[...document.querySelectorAll('#wt input:checked')].map(c=>c.value);
  showLoad();
  const r=await fetch('/api/expand',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({text:txt,level:lvl,concepts:cpts,intent:document.getElementById('ig').value,
      weak_topics:wk,notes:document.getElementById('in2').value})});
  const d=await r.json();
  hideLoad();
  if(d.error){alert(d.error);return;}
  document.getElementById('exp-out').classList.remove('hidden');
  const pre=d.pre_reading||[];
  document.getElementById('pre-items').innerHTML=pre.length?
    pre.map(p=>`<div class="prereading-item"><div class="prereading-icon">📌</div>
      <div><div class="prereading-term">${p.term}</div>
      <div class="prereading-why">${p.why_needed}</div>
      <div class="prereading-exp">${p.explanation}</div></div></div>`).join(''):
    '<span class="muted" style="font-size:.8rem">No pre-reading needed at this level.</span>';
  document.getElementById('ann-t').textContent=d.annotated_text||txt;
  const ss=document.getElementById('simp-s');
  if(d.simplified_summary&&lvl==='beginner'){
    ss.classList.remove('hidden');
    document.getElementById('simp-t').textContent=d.simplified_summary;
  }else{ss.classList.add('hidden');}
  const gl=d.glossary||[];
  document.getElementById('gl-items').innerHTML=gl.length?
    gl.map(g=>`<div class="glossary-item">
      <div class="glossary-term">${g.term} <span class="chip chip-b" style="font-size:.6rem">${g.type}</span></div>
      ${g.full_form?`<div class="glossary-full">📌 ${g.full_form}</div>`:''}
      <div class="glossary-exp">${g.explanation||'See domain references.'}</div>
      ${g.context?`<div class="glossary-ctx">"…${g.context}…"</div>`:''}</div>`).join(''):
    '<span class="muted" style="font-size:.8rem">No terms to explain at this level.</span>';
}

// ── Story Mode ───────────────────────────────────
(async()=>{
  const r=await fetch('/api/story/styles');
  const d=await r.json();
  const grid=document.getElementById('story-grid');
  grid.innerHTML=(d.styles||[]).map(s=>`
    <div class="style-card${s.key==='romantic'?' on':''}" onclick="selStyle2(this,'${s.key}')">
      <span class="style-icon">${s.name.split(' ')[0]}</span>
      <span class="style-name">${s.name.substring(s.name.indexOf(' ')+1)}</span>
      <span class="style-desc">${s.description}</span>
    </div>`).join('');
})();

function selStyle2(btn,key){
  document.querySelectorAll('.style-card').forEach(b=>b.classList.remove('on'));
  btn.classList.add('on');selStyle=key;
}

async function runStory(){
  if(!txt){
    document.getElementById('story-warn').classList.remove('hidden');return;
  }
  document.getElementById('story-spinner').style.display='inline-block';
  document.getElementById('story-btn').disabled=true;
  showLoad();
  try{
    const r=await fetch('/api/story',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({text:txt,style:selStyle,
        characters:document.getElementById('story-chars').value})});
    const d=await r.json();
    if(d.error)throw new Error(d.error);
    document.getElementById('story-out').classList.remove('hidden');
    document.getElementById('story-text').textContent=d.story_text;
    document.getElementById('story-meta').innerHTML=
      `<span class="story-tag">${d.style_used}</span>`+
      `<span class="story-tag">📖 ${d.reading_time_minutes} min read</span>`+
      `<span class="story-tag">🎯 ${d.topic_detected}</span>`;
    document.getElementById('story-stats').innerHTML=`
      <div class="stat-row"><span>Story Words</span><strong>${d.word_count}</strong></div>
      <div class="stat-row"><span>Original Words</span><strong>${d.original_word_count}</strong></div>
      <div class="stat-row"><span>Reading Time</span><strong>${d.reading_time_minutes} min</strong></div>
      <div class="stat-row"><span>Topic Detected</span><strong>${d.topic_detected}</strong></div>`;
    document.getElementById('story-concepts').innerHTML=(d.concepts_woven||[])
      .map(c=>`<span class="tag tag-pk">✓ ${c}</span>`).join('')||
      '<span class="muted" style="font-size:.8rem">—</span>';
  }catch(e){
    document.getElementById('story-out').classList.remove('hidden');
    document.getElementById('story-text').textContent='❌ '+e.message;
  }
  document.getElementById('story-spinner').style.display='none';
  document.getElementById('story-btn').disabled=false;
  hideLoad();
}

// ── Quiz ─────────────────────────────────────────
function setQL(l,btn){qlvl=l;[...btn.parentElement.querySelectorAll('.qlevel-btn')].forEach(b=>b.classList.remove('on'));btn.classList.add('on');}
function setQN(n,btn){qn=n;[...btn.parentElement.querySelectorAll('.qlevel-btn')].forEach(b=>b.classList.remove('on'));btn.classList.add('on');}

async function startQuiz(){
  showLoad();
  const r=await fetch('/api/quiz',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({text:txt,concepts:cpts,level:qlvl,n:qn})});
  const d=await r.json();hideLoad();
  if(d.error){alert(d.error);return;}
  qs=d.questions;ua={};
  document.getElementById('q-setup').classList.add('hidden');
  document.getElementById('q-qs').classList.remove('hidden');
  document.getElementById('qtot').textContent=qs.length;
  renderQ();
}

function eq(s){return(s||'').replace(/'/g,"\\'").replace(/"/g,'&quot;')}

function renderQ(){
  const c=document.getElementById('q-cont');c.innerHTML='';
  qs.forEach((q,i)=>{
    const div=document.createElement('div');div.className='q-card';div.id='qc-'+q.id;
    const dt=`<span class="chip ${q.difficulty==='beginner'?'chip-cy':'chip-p'}">${q.difficulty}</span>`;
    let body=`<div class="q-meta">Q${q.id} · ${q.topic} ${dt}</div><div class="q-text">${q.question}</div>`;
    if(q.type==='mcq'){
      body+=`<div class="q-opts">`+q.options.map(o=>
        `<button class="q-opt" onclick="aMCQ(${q.id},this,'${eq(o)}','${eq(q.answer)}')">${o}</button>`
      ).join('')+`</div>`;
    }else if(q.type==='fill_blank'){
      body+=`<input class="q-input" id="fbi-${q.id}" placeholder="Type your answer…">
        <div style="font-size:.72rem;color:var(--tx3)">${q.hint||''}</div>
        <button class="btn btn-secondary btn-sm mt8" onclick="aFill(${q.id},'${eq(q.answer)}')">Check ✓</button>`;
    }else if(q.type==='true_false'){
      body+=`<div class="tf-row">
        <button class="tf-btn" onclick="aTF(${q.id},this,'True','${eq(q.answer)}')">✅ True</button>
        <button class="tf-btn" onclick="aTF(${q.id},this,'False','${eq(q.answer)}')">❌ False</button></div>`;
    }else if(q.type==='ordering'){
      body+=`<div class="ord-list" id="ord-${q.id}">`+
        q.items.map((it,j)=>`<div class="ord-item" draggable="true" data-i="${j}">
          <span class="ord-handle">☰</span>${it}</div>`).join('')+
        `</div><button class="btn btn-secondary btn-sm" onclick="aOrd(${q.id})">Check Order ✓</button>`;
    }
    body+=`<div class="q-feedback" id="fb-${q.id}"></div>`;
    div.innerHTML=body;c.appendChild(div);
    document.getElementById('qcur').textContent=Math.min(i+1,qs.length);
    document.getElementById('qpf').style.width=((i+1)/qs.length*100)+'%';
  });
  setupDrag();
}

function aMCQ(id,btn,ch,co){
  const card=document.getElementById('qc-'+id);
  card.querySelectorAll('.q-opt').forEach(b=>b.disabled=true);
  const ok=ch.toLowerCase().slice(0,40)===co.toLowerCase().slice(0,40)||
    co.toLowerCase().includes(ch.toLowerCase().slice(0,30));
  btn.classList.add(ok?'correct':'wrong');
  if(!ok)card.querySelectorAll('.q-opt').forEach(b=>{
    if(b.textContent.trim().toLowerCase().slice(0,30)===co.toLowerCase().slice(0,30))b.classList.add('reveal');
  });
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
  document.getElementById('qc-'+id).querySelectorAll('.tf-btn').forEach(b=>b.disabled=true);
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
  fb.className='q-feedback show '+(ok?'fb-right':'fb-wrong');
  fb.innerHTML=(ok?'✅ Correct! ':'❌ Incorrect. ')+(exp||'');
}
function setupDrag(){
  document.querySelectorAll('.ord-list').forEach(list=>{
    let drag=null;
    list.querySelectorAll('.ord-item').forEach(item=>{
      item.addEventListener('dragstart',()=>drag=item);
      item.addEventListener('dragover',e=>e.preventDefault());
      item.addEventListener('drop',e=>{e.preventDefault();
        if(drag&&drag!==item)list.insertBefore(drag,item.nextSibling);});
    });
  });
}
async function submitQ(){
  qs.forEach(q=>{if(!(q.id in ua))ua[q.id]='';});
  const answers=Object.entries(ua).map(([id,given])=>({id:parseInt(id),given}));
  showLoad();
  const r=await fetch('/api/quiz/score',{method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({answers,questions:qs})});
  const d=await r.json();hideLoad();
  if(d.error){alert(d.error);return;}
  showRes(d);
}
function showRes(d){
  document.getElementById('q-qs').classList.add('hidden');
  document.getElementById('q-res').classList.remove('hidden');
  document.getElementById('res-s').textContent=d.overall_score+'%';
  const lm={beginner:'🌱 Beginner',intermediate:'📘 Intermediate',advanced:'🚀 Advanced'};
  document.getElementById('res-l').innerHTML=
    `<span class="tag tag-p">${lm[d.inferred_level]||d.inferred_level}</span> `+
    `<span class="tag tag-b">${d.correct}/${d.total} correct</span>`;
  let ah='';
  (d.strong_areas||[]).forEach(a=>ah+=`<span class="tag tag-g">✅ ${a}</span>`);
  (d.weak_areas||[]).forEach(a=>ah+=`<span class="tag tag-r">⚠️ ${a}</span>`);
  document.getElementById('res-a').innerHTML=ah;
  document.getElementById('skm').innerHTML=Object.entries(d.skill_meters||{}).map(([t,info])=>{
    const col=info.score>=75?'var(--gr)':info.score>=50?'var(--yw)':'var(--rd)';
    return`<div class="skill-item">
      <div class="skill-row"><span>${t}</span><strong>${info.score}% <span style="color:var(--tx3);font-size:.72rem">${info.level}</span></strong></div>
      <div class="skill-bar"><div class="skill-fill" style="width:${info.score}%;background:${col}"></div></div></div>`;
  }).join('')||'<span class="muted">No breakdown.</span>';
  document.getElementById('recs').innerHTML=(d.recommendations||[])
    .map(r=>`<div style="padding:7px 0;border-bottom:1px solid var(--bd);font-size:.82rem;line-height:1.65">${r}</div>`).join('');
  document.getElementById('ar').innerHTML=(d.details||[]).map(r=>`
    <div style="padding:11px 0;border-bottom:1px solid var(--bd)">
      <div style="display:flex;gap:7px;align-items:flex-start">
        <span style="flex-shrink:0">${r.is_correct?'✅':'❌'}</span>
        <div>
          <div style="font-size:.8rem;margin-bottom:3px">${r.question}</div>
          ${!r.is_correct?`<div style="font-size:.75rem;color:var(--tx3)">You: ${r.given||'(blank)'} · Correct: <strong style="color:var(--gr2)">${r.correct_answer}</strong></div>`:''}
          ${r.explanation?`<div style="font-size:.73rem;color:var(--tx3);font-style:italic;margin-top:2px">${r.explanation}</div>`:''}
        </div>
      </div>
    </div>`).join('');
}
function resetQ(){
  document.getElementById('q-res').classList.add('hidden');
  document.getElementById('q-setup').classList.remove('hidden');
  qs=[];ua={};
}

// ── PDF Downloads ────────────────────────────────
async function downloadExpandPDF(){
  if(!txt){alert('Run OCR first to extract document text.');return;}
  const btn=document.getElementById('expand-pdf-btn');
  const spin=document.getElementById('expand-pdf-spinner');
  btn.disabled=true;spin.style.display='inline-block';
  try{
    const r=await fetch('/api/expand_pdf',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({text:txt,level:lvl,concepts:cpts||{}})});
    if(!r.ok){const d=await r.json();alert('Error: '+d.error);return;}
    const blob=await r.blob();
    const url=URL.createObjectURL(blob);
    const a=document.createElement('a');
    a.href=url;a.download=`learning_view_${lvl}.pdf`;a.click();
    URL.revokeObjectURL(url);
  }catch(e){alert('PDF generation failed: '+e.message);}
  btn.disabled=false;spin.style.display='none';
}

async function downloadShrinkPDF(){
  if(!txt){alert('Run OCR first to extract document text.');return;}
  const btn=document.getElementById('shrink-pdf-btn');
  const spin=document.getElementById('shrink-pdf-spinner');
  btn.disabled=true;spin.style.display='inline-block';
  try{
    const r=await fetch('/api/shrink_pdf',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({text:txt,ratio:0.3})});
    if(!r.ok){const d=await r.json();alert('Error: '+d.error);return;}
    const blob=await r.blob();
    const url=URL.createObjectURL(blob);
    const a=document.createElement('a');
    a.href=url;a.download='document_summary.pdf';a.click();
    URL.revokeObjectURL(url);
  }catch(e){alert('PDF generation failed: '+e.message);}
  btn.disabled=false;spin.style.display='none';
}

// ── Training ─────────────────────────────────────
async function addCorrection(){
  const wrong=document.getElementById('tr-wrong').value.trim();
  const correct=document.getElementById('tr-correct').value.trim();
  const source=document.getElementById('tr-source').value.trim();
  if(!wrong||!correct){alert('Please fill in both fields.');return;}
  const r=await fetch('/api/train/add',{method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({ocr_text:wrong,correct_text:correct,source})});
  const d=await r.json();
  const msg=document.getElementById('tr-msg');
  msg.classList.remove('hidden');
  msg.className='alert '+(d.error?'alert-error':'alert-success');
  msg.textContent=d.error?('❌ '+d.error):('✅ Correction #'+d.total+' saved!');
  if(!d.error){
    document.getElementById('tr-wrong').value='';
    document.getElementById('tr-correct').value='';
    document.getElementById('tr-source').value='';
    loadTrainStats();
  }
}
async function testCorrections(){
  const text=document.getElementById('tr-test-in').value.trim();
  if(!text){alert('Paste some text first.');return;}
  const r=await fetch('/api/apply_corrections',{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});
  const d=await r.json();
  document.getElementById('tr-test-out').classList.remove('hidden');
  document.getElementById('tr-corrected-text').textContent=d.corrected_text;
  document.getElementById('tr-changes').innerHTML=d.changes.length?
    `<div style="font-size:.75rem;color:var(--tx3);margin-bottom:5px">${d.changes.length} corrections applied:</div>`+
    d.changes.map(c=>`<div class="correction-item"><div class="corr-before">Before: ${c.split(' → ')[0]}</div><div class="corr-after">After: ${c.split(' → ')[1]||c}</div></div>`).join(''):
    '<span class="muted" style="font-size:.79rem">No known corrections to apply.</span>';
}
async function loadTrainStats(){
  const r=await fetch('/api/train/stats');
  const d=await r.json();
  const ss=document.getElementById('train-stats');
  ss.innerHTML=`
    <div class="stat-row"><span>Total correction pairs</span><strong>${d.total_pairs}</strong></div>
    <div class="stat-row"><span>Unique char patterns learned</span><strong>${d.unique_patterns}</strong></div>
    <div class="stat-row"><span>Top substitution</span><strong>${d.top_pattern||'None yet'}</strong></div>`;
  const cl=document.getElementById('corrections-list');
  const corrs=d.recent_corrections||[];
  document.getElementById('corr-count').textContent=d.total_pairs+' total';
  cl.innerHTML=corrs.length?corrs.map(c=>`
    <div class="correction-item">
      <div class="corr-before">❌ OCR: ${c.ocr}</div>
      <div class="corr-after">✅ Correct: ${c.correct}</div>
      ${c.source?`<div style="font-size:.68rem;color:var(--tx3);margin-top:2px">Source: ${c.source}</div>`:''}
    </div>`).join(''):
    '<span class="muted" style="font-size:.8rem">No corrections yet. Add some above to start training!</span>';
}
async function runEval(){
  showLoad();
  const r=await fetch('/api/train/evaluate',{method:'POST'});
  const d=await r.json();hideLoad();
  const er=document.getElementById('eval-result');er.classList.remove('hidden');
  if(d.error){er.innerHTML=`<div class="alert alert-error">${d.error}</div>`;return;}
  const accColor=d.accuracy>=80?'var(--gr)':d.accuracy>=60?'var(--yw)':'var(--rd)';
  er.innerHTML=`<div class="eval-result">
    <div style="margin-bottom:10px;font-size:.8rem;color:var(--tx3)">Evaluated on ${d.total_samples} correction pairs</div>
    <div class="eval-metric"><div class="eval-num">${(d.mean_cer*100).toFixed(1)}%</div><div class="eval-label">Character Error Rate</div></div>
    <div class="eval-metric"><div class="eval-num">${(d.mean_wer*100).toFixed(1)}%</div><div class="eval-label">Word Error Rate</div></div>
    <div class="eval-metric"><div class="eval-num" style="color:${accColor}">${d.accuracy.toFixed(1)}%</div><div class="eval-label">Accuracy Score</div></div>
  </div>`;
}

// ── Utilities ────────────────────────────────────
function cp(id){navigator.clipboard.writeText(document.getElementById(id).textContent);}
function dl(id,fn){
  const b=new Blob([document.getElementById(id).textContent],{type:'text/plain'});
  Object.assign(document.createElement('a'),{href:URL.createObjectURL(b),download:fn}).click();
}
</script>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════
#  ROUTES
# ═══════════════════════════════════════════════════════════════════

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
        if t == 'summarize':
            result = transformer.summarize(text, ratio=0.35, max_sentences=8)
        elif t == 'extract':
            result = transformer.extract_information(text)
        elif t == 'redact':
            r = transformer.redact(text)
            result = r['redacted_text'] + f"\n\n[{r['items_redacted']} items redacted]"
        elif t == 'classify':
            result = transformer.classify_and_tag(text)
        elif t == 'format_bullet':
            result = transformer.format_text(text, style='bullet_points')
        elif t == 'format_markdown':
            result = transformer.format_text(text, style='markdown')
        else:
            return jsonify({'error': 'Unknown transform'}), 400
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
        result = level_assessor.calculate_score(
            data.get('answers', []), data.get('questions', []))
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Story Mode Routes ──────────────────────────────

@app.route('/api/story/styles', methods=['GET'])
def api_story_styles():
    try:
        return jsonify({'styles': story_transformer.get_available_styles()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/story', methods=['POST'])
def api_story():
    data = request.get_json()
    text = data.get('text', '')
    style = data.get('style', 'romantic')
    characters = data.get('characters', '')
    if not text:
        return jsonify({'error': 'No text to transform'}), 400
    try:
        result = story_transformer.transform_to_story(text, style, characters)
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ── Training Routes ────────────────────────────────

@app.route('/api/apply_corrections', methods=['POST'])
def api_apply_corrections():
    data = request.get_json()
    text = data.get('text', '')
    if not text:
        return jsonify({'error': 'No text'}), 400
    try:
        # Reload corrections in case new ones were added
        processor = OCRPostProcessor()
        corrected, changes = processor.apply(text)
        return jsonify({'corrected_text': corrected, 'changes': changes})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/train/add', methods=['POST'])
def api_train_add():
    data = request.get_json()
    ocr_text = data.get('ocr_text', '').strip()
    correct_text = data.get('correct_text', '').strip()
    source = data.get('source', '')
    if not ocr_text or not correct_text:
        return jsonify({'error': 'Both fields required'}), 400
    try:
        training_collector.add_correction(ocr_text, correct_text, source)
        total = len(training_collector.corrections.get('pairs', []))
        return jsonify({'success': True, 'total': total})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/train/stats', methods=['GET'])
def api_train_stats():
    try:
        pairs = training_collector.corrections.get('pairs', [])
        char_corr = training_collector.corrections.get('char_corrections', {})
        top = sorted(char_corr.items(), key=lambda x: x[1], reverse=True)
        return jsonify({
            'total_pairs': len(pairs),
            'unique_patterns': len(char_corr),
            'top_pattern': top[0][0] if top else None,
            'recent_corrections': pairs[-5:][::-1]  # last 5, newest first
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/train/evaluate', methods=['POST'])
def api_train_evaluate():
    try:
        pairs = training_collector.corrections.get('pairs', [])
        if not pairs:
            return jsonify({'error': 'No correction pairs yet. Add some corrections first.'}), 400
        metrics = evaluator.evaluate_batch(pairs)
        return jsonify(metrics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/expand_pdf', methods=['POST'])
def api_expand_pdf():
    """Generate and return an expanded/annotated PDF."""
    data = request.get_json()
    text = data.get('text', '')
    level = data.get('level', 'intermediate')
    concepts = data.get('concepts', {})
    if not text:
        return jsonify({'error': 'No text'}), 400
    try:
        from flask import send_file
        output_path = os.path.join('outputs', f'expanded_{level}.pdf')
        text_expander.expand_to_pdf(text, level, concepts, output_path)
        return send_file(output_path, as_attachment=True,
                         download_name=f'learning_view_{level}.pdf',
                         mimetype='application/pdf')
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/shrink_pdf', methods=['POST'])
def api_shrink_pdf():
    """Generate and return a condensed summary PDF."""
    data = request.get_json()
    text = data.get('text', '')
    ratio = float(data.get('ratio', 0.3))
    if not text:
        return jsonify({'error': 'No text'}), 400
    try:
        from flask import send_file
        output_path = os.path.join('outputs', 'summary.pdf')
        text_expander.shrink_to_pdf(text, output_path, ratio)
        return send_file(output_path, as_attachment=True,
                         download_name='document_summary.pdf',
                         mimetype='application/pdf')
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

register_menu_ocr_routes(app, ocr_engine)

if __name__ == '__main__':
    print("=" * 65)
    print("🤖 IntelliDoc AI — v3 POLISHED")
    print("   Features: OCR · Transform · Learn · Story · Quiz · Train")
    if POPPLER_PATH:
        print(f"   ✅ Poppler: {POPPLER_PATH}")
    else:
        print("   ⚠️  Poppler not found — PDF needs setup (see README)")
    print("   Open: http://localhost:5000")
    print("=" * 65)
    app.run(host="0.0.0.0", port=5000, debug=True)