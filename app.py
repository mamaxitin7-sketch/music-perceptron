"""
Dự đoán thể loại nhạc — Perceptron từ đầu
==========================================
Chạy local:
    pip install flask
    python app.py
    → Mở http://localhost:5000

Deploy lên Render/Railway:
    - Thêm requirements.txt: flask gunicorn
    - Start command: gunicorn app:app
"""

import math
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# ─── Dữ liệu thể loại nhạc ────────────────────────────────────────────────────

GENRES = [
    {"id": "pop",       "label": "Pop",           "desc": "Giai điệu bắt tai, dễ nghe, phổ biến rộng rãi",       "color": "#378ADD", "bg": "#E6F1FB", "tc": "#0C447C"},
    {"id": "rock",      "label": "Rock",           "desc": "Năng lượng cao, guitar điện, trống mạnh mẽ",          "color": "#D85A30", "bg": "#FAECE7", "tc": "#712B13"},
    {"id": "rap",       "label": "Rap / Hip-hop",  "desc": "Beat sắc nét, vần điệu, lời rap trực tiếp",           "color": "#7F77DD", "bg": "#EEEDFE", "tc": "#3C3489"},
    {"id": "edm",       "label": "EDM",            "desc": "Điện tử sôi động, festival, drop bass mạnh",          "color": "#1D9E75", "bg": "#E1F5EE", "tc": "#085041"},
    {"id": "jazz",      "label": "Jazz",           "desc": "Ngẫu hứng, saxophone, piano — thư giãn tập trung",    "color": "#BA7517", "bg": "#FAEEDA", "tc": "#633806"},
    {"id": "classical", "label": "Classical",      "desc": "Giao hưởng, piano, violin — cổ điển vượt thời gian",  "color": "#993556", "bg": "#FBEAF0", "tc": "#72243E"},
    {"id": "rnb",       "label": "R&B",            "desc": "Nhẹ nhàng, giàu cảm xúc, pha soul",                  "color": "#185FA5", "bg": "#E6F1FB", "tc": "#042C53"},
    {"id": "lofi",      "label": "Lo-fi",          "desc": "Chill, thư giãn, lý tưởng khi học bài",               "color": "#3B6D11", "bg": "#EAF3DE", "tc": "#173404"},
    {"id": "kpop",      "label": "K-pop",          "desc": "Nhạc Hàn, kết hợp dance và visual bắt mắt",           "color": "#D4537E", "bg": "#FBEAF0", "tc": "#4B1528"},
    {"id": "bolero",    "label": "Bolero",         "desc": "Nhạc trữ tình Việt Nam, sâu lắng và da diết",         "color": "#5F5E5A", "bg": "#F1EFE8", "tc": "#2C2C2A"},
]

# Features: [age, gender, hours, platform, device, freetime, social, exposure, language]
BASE_W = {
    "pop":       [ 0.30,  0.30,  0.55,  0.45,  0.10,  0.30,  0.55,  0.45,  0.20],
    "rock":      [ 0.15,  0.45,  0.65,  0.20,  0.45,  0.45,  0.15,  0.35,  0.20],
    "rap":       [-0.05,  0.25,  0.55,  0.35,  0.20,  0.55,  0.65,  0.50,  0.30],
    "edm":       [-0.10,  0.10,  0.75,  0.55,  0.30,  0.65,  0.55,  0.45,  0.10],
    "jazz":      [ 0.55, -0.05,  0.25,  0.15,  0.60, -0.05,  0.20, -0.15,  0.15],
    "classical": [ 0.65, -0.05,  0.15,  0.05,  0.65, -0.10,  0.10, -0.25,  0.05],
    "rnb":       [ 0.15,  0.45,  0.45,  0.45,  0.25,  0.35,  0.45,  0.45,  0.25],
    "lofi":      [ 0.05,  0.15,  0.35,  0.45,  0.15,  0.25,  0.25,  0.35,  0.15],
    "kpop":      [-0.25,  0.55,  0.55,  0.55,  0.15,  0.45,  0.75,  0.55,  0.65],
    "bolero":    [ 0.85, -0.15,  0.15, -0.05,  0.15,  0.15, -0.25,  0.25,  0.75],
}

# Timing bonus [sáng, làm/học, chiều, đêm, tập TD, mọi lúc]
TIMING_BONUS = {
    "pop":       [ 0.30,  0.00,  0.20,  0.10,  0.15,  0.20],
    "rock":      [ 0.00, -0.40,  0.20,  0.10,  0.50,  0.10],
    "rap":       [-0.10, -0.35,  0.10,  0.15,  0.40,  0.10],
    "edm":       [-0.10, -0.55,  0.10,  0.05,  0.60,  0.10],
    "jazz":      [ 0.20,  0.50,  0.25,  0.35, -0.30,  0.20],
    "classical": [ 0.35,  0.55,  0.20,  0.30, -0.35,  0.15],
    "rnb":       [ 0.10,  0.10,  0.30,  0.45, -0.10,  0.15],
    "lofi":      [ 0.15,  0.60,  0.20,  0.40, -0.25,  0.15],
    "kpop":      [ 0.10, -0.20,  0.35,  0.15,  0.25,  0.20],
    "bolero":    [ 0.10,  0.10,  0.30,  0.45, -0.20,  0.10],
}

BIAS = {
    "pop": 0.10, "rock": 0.00, "rap": 0.05, "edm": 0.00,
    "jazz": -0.05, "classical": -0.10, "rnb": 0.05,
    "lofi": 0.05, "kpop": -0.05, "bolero": -0.10,
}

TIMING_LABELS = ["sáng sớm", "khi làm việc / học bài", "buổi chiều tối",
                 "đêm khuya", "khi tập thể dục", "mọi lúc"]
FEAT_NAMES    = ["Tuổi", "Giới tính", "Giờ nghe", "Nền tảng", "Thiết bị",
                 "Giờ rảnh", "MXH", "Tiếp xúc", "Ngôn ngữ"]

GENRE_EXPS = {
    "pop":       "Pop hợp với nhiều thời điểm, giai điệu dễ nghe trên mọi nền tảng.",
    "rock":      "Rock phù hợp khi cần năng lượng cao, đặc biệt lúc tập thể dục.",
    "rap":       "Rap/Hip-hop hợp với người trẻ dùng MXH nhiều và ưa beat sắc.",
    "edm":       "EDM lý tưởng khi tập gym hoặc cần boost năng lượng — không phải để tập trung.",
    "jazz":      "Jazz tạo không khí tập trung nhẹ nhàng, lý tưởng khi làm việc hoặc học bài.",
    "classical": "Classical giúp tăng tập trung, rất phổ biến để học bài và làm việc sâu.",
    "rnb":       "R&B nhẹ nhàng, cảm xúc — hợp buổi tối hoặc khi cần thư giãn.",
    "lofi":      "Lo-fi là lựa chọn hàng đầu khi học bài — nhịp chậm, không lời, ít phân tâm.",
    "kpop":      "K-pop hợp với người trẻ, dùng MXH nhiều, gắn kết văn hóa Hàn.",
    "bolero":    "Bolero trữ tình, hợp với profile người Việt lớn tuổi, nghe buổi tối.",
}


# ─── Perceptron logic ─────────────────────────────────────────────────────────

def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def dot(weights: list, features: list) -> float:
    return sum(w * f for w, f in zip(weights, features))


def normalize_inputs(age, gender, hours, platform, device,
                     freetime, social, exposure, language) -> list:
    """Chuẩn hóa tất cả inputs về khoảng [0, 1]"""
    return [
        min(age / 60, 1.0),        # tuổi
        gender / 2.0,               # giới tính
        min(hours / 12, 1.0),       # giờ nghe
        platform / 5.0,             # nền tảng
        device / 4.0,               # thiết bị
        min(freetime / 10, 1.0),    # thời gian rảnh
        min(social / 8, 1.0),       # mạng xã hội
        exposure / 3.0,             # mức tiếp xúc
        language / 4.0,             # ngôn ngữ
    ]


def softmax_with_temperature(scores: dict, temperature: float = 0.4) -> dict:
    """Softmax với temperature để kéo giãn khoảng cách xác suất"""
    logits = {k: math.log(v + 1e-9) / temperature for k, v in scores.items()}
    max_l  = max(logits.values())
    exps   = {k: math.exp(v - max_l) for k, v in logits.items()}
    total  = sum(exps.values())
    return {k: v / total for k, v in exps.items()}


def perceptron_predict(features: list, timing: int) -> dict:
    """
    Chạy Perceptron cho tất cả thể loại và trả về xác suất sau softmax.

    Công thức mỗi thể loại:
        raw_score = sigmoid( dot(W, x) + timing_bonus + bias ) * 2.5
        prob      = softmax_temperature(raw_scores)
    """
    raw_scores = {}
    details    = {}

    for g in GENRES:
        gid        = g["id"]
        base_score = dot(BASE_W[gid], features)
        timing_b   = TIMING_BONUS[gid][timing]
        bias       = BIAS[gid]
        combined   = (base_score + timing_b + bias) * 2.5
        raw        = sigmoid(combined)
        raw_scores[gid] = raw

        # Lưu chi tiết để trả về cho frontend
        details[gid] = {
            "base_score":    round(base_score, 4),
            "timing_bonus":  timing_b,
            "bias":          bias,
            "sigmoid_input": round(combined, 4),
            "raw":           round(raw, 6),
        }

    probs = softmax_with_temperature(raw_scores, temperature=0.4)

    sorted_genres = sorted(GENRES, key=lambda g: probs[g["id"]], reverse=True)
    visible       = [g for g in sorted_genres if probs[g["id"]] > 0.03]

    top    = sorted_genres[0]
    top_id = top["id"]

    # Chi tiết weights cho thể loại đứng đầu
    weight_detail = []
    for i, (name, w) in enumerate(zip(FEAT_NAMES, BASE_W[top_id])):
        weight_detail.append({
            "feature": name,
            "weight":  round(w, 2),
            "input":   round(features[i], 4),
            "product": round(w * features[i], 4),
        })

    return {
        "top": {
            **top,
            "probability": round(probs[top_id] * 100, 1),
        },
        "visible": [
            {**g, "probability": round(probs[g["id"]] * 100, 1)}
            for g in visible
        ],
        "timing_label": TIMING_LABELS[timing],
        "explanation":  GENRE_EXPS.get(top_id, ""),
        "weight_detail": weight_detail,
        "timing_bonus_top": TIMING_BONUS[top_id][timing],
        "bias_top": BIAS[top_id],
    }


# ─── Flask routes ─────────────────────────────────────────────────────────────




@app.route("/")
def index():
    """Trả về trang HTML nhúng sẵn trong code."""
    return HTML_PAGE

HTML_PAGE = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dự đoán thể loại nhạc — Perceptron</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg: #f7f6f3;
    --surface: #ffffff;
    --surface2: #f1efe8;
    --border: rgba(0,0,0,0.10);
    --border-strong: rgba(0,0,0,0.18);
    --text: #1a1a18;
    --text2: #5f5e5a;
    --text3: #9e9c96;
    --radius: 12px;
    --radius-sm: 8px;
    --font: 'Segoe UI', system-ui, -apple-system, sans-serif;
    --font-mono: 'Fira Code', 'Cascadia Code', monospace;
  }

  body {
    font-family: var(--font);
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    padding: 0;
  }

  header {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 1.25rem 1.5rem;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  header .logo {
    width: 36px; height: 36px; border-radius: 10px;
    background: #185FA5;
    display: flex; align-items: center; justify-content: center;
    color: #fff; font-size: 18px; flex-shrink: 0;
  }
  header h1 { font-size: 17px; font-weight: 500; }
  header p  { font-size: 12px; color: var(--text2); margin-top: 1px; }

  .container { max-width: 720px; margin: 0 auto; padding: 1.5rem 1rem 4rem; }

  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.25rem;
    margin-bottom: 1rem;
  }
  .card-title {
    font-size: 13px; font-weight: 500; color: var(--text2);
    margin-bottom: 12px; text-transform: uppercase; letter-spacing: .04em;
  }

  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; }

  label { font-size: 12px; color: var(--text2); display: block; margin-bottom: 5px; }

  input[type=number], select {
    width: 100%; padding: 8px 10px; font-size: 14px;
    border: 1px solid var(--border-strong); border-radius: var(--radius-sm);
    background: var(--surface); color: var(--text);
    outline: none; font-family: var(--font);
    transition: border-color .15s;
  }
  input[type=number]:focus, select:focus { border-color: #378ADD; }

  .btn {
    width: 100%; padding: 12px; font-size: 15px; font-weight: 500;
    border: none; border-radius: var(--radius);
    background: #185FA5; color: #fff; cursor: pointer;
    font-family: var(--font); transition: background .15s, transform .1s;
    letter-spacing: .01em;
  }
  .btn:hover  { background: #0C447C; }
  .btn:active { transform: scale(0.99); }

  /* Result */
  #result { display: none; }

  .winner-card {
    border-radius: var(--radius);
    padding: 1.25rem 1.25rem 1rem;
    margin-bottom: 1rem;
    border: 2px solid transparent;
    display: flex; align-items: center; gap: 16px;
  }
  .winner-circle {
    width: 52px; height: 52px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; font-weight: 600; flex-shrink: 0; color: #fff;
  }
  .winner-label { font-size: 20px; font-weight: 500; }
  .winner-pct   { font-size: 32px; font-weight: 600; line-height: 1; margin-top: 2px; }
  .winner-desc  { font-size: 13px; margin-top: 4px; opacity: .75; }

  .bars-section p { font-size: 12px; color: var(--text2); margin-bottom: 10px; font-weight: 500; text-transform: uppercase; letter-spacing: .04em; }
  .bar-row { display: flex; align-items: center; gap: 8px; margin-bottom: 7px; }
  .bar-rank { width: 24px; text-align: center; font-size: 13px; flex-shrink: 0; }
  .bar-name { width: 118px; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex-shrink: 0; }
  .bar-track { flex: 1; background: var(--surface2); border-radius: 4px; overflow: hidden; }
  .bar-fill  { border-radius: 4px; transition: width .5s cubic-bezier(.4,0,.2,1); }
  .bar-pct   { width: 46px; text-align: right; font-size: 13px; flex-shrink: 0; }

  .explanation {
    margin-top: 1rem; font-size: 13px; color: var(--text2);
    border-top: 1px solid var(--border); padding-top: .85rem;
    line-height: 1.6;
  }

  .detail-block {
    margin-top: 1rem;
    background: var(--surface2);
    border-radius: var(--radius-sm);
    padding: 1rem;
    font-size: 12px; font-family: var(--font-mono);
    color: var(--text2); white-space: pre-wrap; line-height: 1.7;
  }

  .section-label {
    font-size: 12px; font-weight: 500; color: var(--text2);
    text-transform: uppercase; letter-spacing: .04em; margin-bottom: 10px;
  }

  footer {
    text-align: center; font-size: 12px; color: var(--text3);
    padding: 2rem 1rem 1rem;
  }

  @media (max-width: 480px) {
    .grid { grid-template-columns: 1fr 1fr; }
    .winner-label { font-size: 17px; }
    .winner-pct   { font-size: 26px; }
  }
</style>
</head>
<body>

<header>
  <div class="logo">♪</div>
  <div>
    <h1>Dự đoán thể loại nhạc</h1>
    <p>Perceptron — Machine Learning từ đầu</p>
  </div>
</header>

<div class="container">

  <div class="card">
    <p class="card-title">Về bạn</p>
    <div class="grid">
      <div>
        <label>Tuổi</label>
        <input type="number" id="age" min="5" max="80" value="22">
      </div>
      <div>
        <label>Giới tính</label>
        <select id="gender">
          <option value="0">Nam</option>
          <option value="1">Nữ</option>
          <option value="2">Khác</option>
        </select>
      </div>
      <div>
        <label>Ngôn ngữ thường dùng</label>
        <select id="language">
          <option value="0">Tiếng Việt</option>
          <option value="1">Tiếng Anh</option>
          <option value="2">Tiếng Hàn</option>
          <option value="3">Tiếng Nhật</option>
          <option value="4">Khác</option>
        </select>
      </div>
    </div>
  </div>

  <div class="card">
    <p class="card-title">Thói quen nghe nhạc</p>
    <div class="grid">
      <div>
        <label>Giờ nghe nhạc / ngày</label>
        <input type="number" id="hours" min="0" max="16" step="0.5" value="3">
      </div>
      <div>
        <label>Nền tảng chính</label>
        <select id="platform">
          <option value="0">Radio</option>
          <option value="1">Spotify</option>
          <option value="2">YouTube</option>
          <option value="3">Apple Music</option>
          <option value="4">Zing MP3</option>
          <option value="5">SoundCloud</option>
        </select>
      </div>
      <div>
        <label>Thiết bị nghe</label>
        <select id="device">
          <option value="0">Điện thoại</option>
          <option value="1">Máy tính / laptop</option>
          <option value="2">Tai nghe chuyên dụng</option>
          <option value="3">Loa</option>
          <option value="4">TV</option>
        </select>
      </div>
      <div>
        <label>Thời điểm nghe nhạc</label>
        <select id="timing">
          <option value="0">Sáng sớm</option>
          <option value="1">Khi làm việc / học bài</option>
          <option value="2">Chiều tối</option>
          <option value="3">Đêm khuya</option>
          <option value="4">Khi tập thể dục</option>
          <option value="5">Mọi lúc</option>
        </select>
      </div>
    </div>
  </div>

  <div class="card">
    <p class="card-title">Lối sống</p>
    <div class="grid">
      <div>
        <label>Thời gian rảnh / ngày (giờ)</label>
        <input type="number" id="freetime" min="0" max="16" step="0.5" value="4">
      </div>
      <div>
        <label>Giờ dùng mạng xã hội / ngày</label>
        <input type="number" id="social" min="0" max="16" step="0.5" value="2">
      </div>
      <div>
        <label>Mức độ tiếp xúc âm nhạc</label>
        <select id="exposure">
          <option value="0">Rất ít</option>
          <option value="1">Thỉnh thoảng</option>
          <option value="2" selected>Thường xuyên</option>
          <option value="3">Cả ngày có nhạc</option>
        </select>
      </div>
    </div>
  </div>

  <button class="btn" onclick="predict()">✦ Dự đoán thể loại nhạc</button>

  <div id="result" style="margin-top:1rem">

    <div id="winner-card" class="winner-card">
      <div id="winner-circle" class="winner-circle"></div>
      <div>
        <div id="winner-label" class="winner-label"></div>
        <div id="winner-pct"   class="winner-pct"></div>
        <div id="winner-desc"  class="winner-desc"></div>
      </div>
    </div>

    <div class="card bars-section">
      <p class="section-label">Thể loại phù hợp — độ tương thích</p>
      <div id="all-bars"></div>
      <div id="explanation" class="explanation"></div>
    </div>

    <details style="margin-top:.5rem">
      <summary style="cursor:pointer;font-size:13px;color:var(--text2);padding:.5rem 0;user-select:none">
        Chi tiết tính toán (weights × inputs)
      </summary>
      <div id="weights-display" class="detail-block"></div>
    </details>
  </div>

</div>

<footer>Perceptron · Bài tập nhóm · Machine Learning từ đầu</footer>

<script>
const GENRES = [
  { id:'pop',       label:'Pop',           desc:'Giai điệu bắt tai, dễ nghe, phổ biến rộng rãi',       color:'#378ADD', bg:'#E6F1FB', tc:'#0C447C' },
  { id:'rock',      label:'Rock',          desc:'Năng lượng cao, guitar điện, trống mạnh mẽ',           color:'#D85A30', bg:'#FAECE7', tc:'#712B13' },
  { id:'rap',       label:'Rap / Hip-hop', desc:'Beat sắc nét, vần điệu, lời rap trực tiếp',            color:'#7F77DD', bg:'#EEEDFE', tc:'#3C3489' },
  { id:'edm',       label:'EDM',           desc:'Điện tử sôi động, festival, drop bass mạnh',           color:'#1D9E75', bg:'#E1F5EE', tc:'#085041' },
  { id:'jazz',      label:'Jazz',          desc:'Ngẫu hứng, saxophone, piano — thư giãn tập trung',     color:'#BA7517', bg:'#FAEEDA', tc:'#633806' },
  { id:'classical', label:'Classical',     desc:'Giao hưởng, piano, violin — cổ điển vượt thời gian',   color:'#993556', bg:'#FBEAF0', tc:'#72243E' },
  { id:'rnb',       label:'R&B',           desc:'Nhẹ nhàng, giàu cảm xúc, pha soul',                   color:'#185FA5', bg:'#E6F1FB', tc:'#042C53' },
  { id:'lofi',      label:'Lo-fi',         desc:'Chill, thư giãn, lý tưởng khi học bài',                color:'#3B6D11', bg:'#EAF3DE', tc:'#173404' },
  { id:'kpop',      label:'K-pop',         desc:'Nhạc Hàn, kết hợp dance và visual bắt mắt',            color:'#D4537E', bg:'#FBEAF0', tc:'#4B1528' },
  { id:'bolero',    label:'Bolero',        desc:'Nhạc trữ tình Việt Nam, sâu lắng và da diết',          color:'#5F5E5A', bg:'#F1EFE8', tc:'#2C2C2A' },
];

// Features: [age, gender, hours, platform, device, freetime, social, exposure, language]
const BASE_W = {
  pop:       [ 0.30,  0.30,  0.55,  0.45,  0.10,  0.30,  0.55,  0.45,  0.20],
  rock:      [ 0.15,  0.45,  0.65,  0.20,  0.45,  0.45,  0.15,  0.35,  0.20],
  rap:       [-0.05,  0.25,  0.55,  0.35,  0.20,  0.55,  0.65,  0.50,  0.30],
  edm:       [-0.10,  0.10,  0.75,  0.55,  0.30,  0.65,  0.55,  0.45,  0.10],
  jazz:      [ 0.55, -0.05,  0.25,  0.15,  0.60, -0.05,  0.20, -0.15,  0.15],
  classical: [ 0.65, -0.05,  0.15,  0.05,  0.65, -0.10,  0.10, -0.25,  0.05],
  rnb:       [ 0.15,  0.45,  0.45,  0.45,  0.25,  0.35,  0.45,  0.45,  0.25],
  lofi:      [ 0.05,  0.15,  0.35,  0.45,  0.15,  0.25,  0.25,  0.35,  0.15],
  kpop:      [-0.25,  0.55,  0.55,  0.55,  0.15,  0.45,  0.75,  0.55,  0.65],
  bolero:    [ 0.85, -0.15,  0.15, -0.05,  0.15,  0.15, -0.25,  0.25,  0.75],
};

// Timing bonus [sáng, làm/học, chiều, đêm, tập TD, mọi lúc]
const TIMING_BONUS = {
  pop:       [ 0.30,  0.00,  0.20,  0.10,  0.15,  0.20],
  rock:      [ 0.00, -0.40,  0.20,  0.10,  0.50,  0.10],
  rap:       [-0.10, -0.35,  0.10,  0.15,  0.40,  0.10],
  edm:       [-0.10, -0.55,  0.10,  0.05,  0.60,  0.10],
  jazz:      [ 0.20,  0.50,  0.25,  0.35, -0.30,  0.20],
  classical: [ 0.35,  0.55,  0.20,  0.30, -0.35,  0.15],
  rnb:       [ 0.10,  0.10,  0.30,  0.45, -0.10,  0.15],
  lofi:      [ 0.15,  0.60,  0.20,  0.40, -0.25,  0.15],
  kpop:      [ 0.10, -0.20,  0.35,  0.15,  0.25,  0.20],
  bolero:    [ 0.10,  0.10,  0.30,  0.45, -0.20,  0.10],
};

const BIAS = { pop:0.10, rock:0.00, rap:0.05, edm:0.00, jazz:-0.05, classical:-0.10, rnb:0.05, lofi:0.05, kpop:-0.05, bolero:-0.10 };

const EXPS = {
  pop:       'Pop hợp với nhiều thời điểm, giai điệu dễ nghe trên mọi nền tảng.',
  rock:      'Rock phù hợp khi cần năng lượng cao, đặc biệt lúc tập thể dục.',
  rap:       'Rap/Hip-hop hợp với người trẻ dùng mạng xã hội nhiều và ưa beat sắc.',
  edm:       'EDM lý tưởng khi tập gym hoặc cần boost năng lượng — không phải để tập trung.',
  jazz:      'Jazz tạo không khí tập trung nhẹ nhàng, lý tưởng khi làm việc hoặc học bài.',
  classical: 'Classical giúp tăng tập trung, rất phổ biến để học bài và làm việc sâu.',
  rnb:       'R&B nhẹ nhàng, cảm xúc — hợp buổi tối hoặc khi cần thư giãn.',
  lofi:      'Lo-fi là lựa chọn hàng đầu khi học bài — nhịp chậm, không lời, ít phân tâm.',
  kpop:      'K-pop hợp với người trẻ, dùng MXH nhiều, gắn kết văn hóa Hàn.',
  bolero:    'Bolero trữ tình, hợp với profile người Việt lớn tuổi, nghe buổi tối.',
};

const TIMING_LABELS = ['sáng sớm','khi làm việc / học bài','buổi chiều tối','đêm khuya','khi tập thể dục','mọi lúc'];
const MEDALS = ['🥇','🥈','🥉'];
const FEAT_NAMES = ['Tuổi','Giới tính','Giờ nghe','Nền tảng','Thiết bị','Giờ rảnh','MXH','Tiếp xúc','Ngôn ngữ'];

function sigmoid(x) { return 1 / (1 + Math.exp(-x)); }
function dot(w, x)  { return w.reduce((s, wi, i) => s + wi * (x[i] || 0), 0); }

function getInputs() {
  const age      = parseFloat(document.getElementById('age').value)      || 22;
  const gender   = parseInt(document.getElementById('gender').value);
  const hours    = parseFloat(document.getElementById('hours').value)    || 3;
  const platform = parseInt(document.getElementById('platform').value);
  const device   = parseInt(document.getElementById('device').value);
  const timing   = parseInt(document.getElementById('timing').value);
  const freetime = parseFloat(document.getElementById('freetime').value) || 4;
  const social   = parseFloat(document.getElementById('social').value)   || 2;
  const exposure = parseInt(document.getElementById('exposure').value);
  const language = parseInt(document.getElementById('language').value);
  const x = [
    Math.min(age / 60, 1), gender / 2, Math.min(hours / 12, 1),
    platform / 5, device / 4, Math.min(freetime / 10, 1),
    Math.min(social / 8, 1), exposure / 3, language / 4,
  ];
  return { x, timing };
}

function predict() {
  const { x, timing } = getInputs();
  const rawScores = {};
  for (const g of GENRES) {
    const base = dot(BASE_W[g.id], x);
    const tb   = TIMING_BONUS[g.id][timing];
    rawScores[g.id] = sigmoid((base + tb + BIAS[g.id]) * 2.5);
  }

  // Softmax with temperature to spread scores
  const temp = 0.4;
  const logits = {};
  for (const g of GENRES) logits[g.id] = Math.log(rawScores[g.id] + 1e-9) / temp;
  const maxL = Math.max(...Object.values(logits));
  const exps = {}; let sumE = 0;
  for (const g of GENRES) { exps[g.id] = Math.exp(logits[g.id] - maxL); sumE += exps[g.id]; }
  const probs = {};
  for (const g of GENRES) probs[g.id] = exps[g.id] / sumE;

  const sorted  = GENRES.slice().sort((a, b) => probs[b.id] - probs[a.id]);
  const visible = sorted.filter(g => probs[g.id] > 0.03);
  const top     = sorted[0];
  const maxP    = probs[top.id];

  document.getElementById('result').style.display = 'block';
  document.getElementById('result').scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  // Winner card
  const wc = document.getElementById('winner-card');
  wc.style.background    = top.bg;
  wc.style.borderColor   = top.color;
  const circle = document.getElementById('winner-circle');
  circle.style.background = top.color;
  circle.textContent = '#1';
  document.getElementById('winner-label').style.color = top.tc;
  document.getElementById('winner-label').textContent = top.label;
  const pctEl = document.getElementById('winner-pct');
  pctEl.style.color   = top.color;
  pctEl.textContent   = (probs[top.id] * 100).toFixed(1) + '%';
  const descEl = document.getElementById('winner-desc');
  descEl.style.color  = top.tc;
  descEl.textContent  = top.desc;

  // Bars
  const allBars = document.getElementById('all-bars');
  allBars.innerHTML = '';
  visible.forEach((g, i) => {
    const pct  = (probs[g.id] * 100).toFixed(1);
    const barW = Math.round((probs[g.id] / maxP) * 100);
    const isTop = i === 0;
    const rank  = i < 3 ? MEDALS[i] : `${i + 1}.`;
    const row   = document.createElement('div');
    row.className = 'bar-row';
    row.innerHTML = `
      <span class="bar-rank">${rank}</span>
      <span class="bar-name" style="font-weight:${isTop ? '500' : '400'};color:${isTop ? 'var(--text)' : 'var(--text2)'}">${g.label}</span>
      <div class="bar-track" style="height:${isTop ? 20 : 13}px">
        <div class="bar-fill" style="width:0%;height:100%;background:${g.color}"></div>
      </div>
      <span class="bar-pct" style="font-weight:${isTop ? '500' : '400'};color:${isTop ? g.color : 'var(--text2)'}">${pct}%</span>`;
    allBars.appendChild(row);
    // animate bar after paint
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        row.querySelector('.bar-fill').style.width = barW + '%';
      });
    });
  });

  document.getElementById('explanation').textContent =
    `Thời điểm "${TIMING_LABELS[timing]}" ảnh hưởng lớn đến kết quả. ${EXPS[top.id] || ''}`;

  // Weights detail
  let wStr = `Weights của ${top.label} (+ timing bonus "${TIMING_LABELS[timing]}"):\\n`;
  BASE_W[top.id].forEach((w, i) => {
    wStr += `  ${FEAT_NAMES[i].padEnd(12)} × ${w.toFixed(2)} = ${(w * (x[i] || 0)).toFixed(3)}\\n`;
  });
  const rawScore = dot(BASE_W[top.id], x) + TIMING_BONUS[top.id][timing] + BIAS[top.id];
  wStr += `  Timing bonus  : +${TIMING_BONUS[top.id][timing].toFixed(2)}\\n`;
  wStr += `  Bias          : ${BIAS[top.id].toFixed(2)}\\n`;
  wStr += `  sigmoid(${rawScore.toFixed(3)} × 2.5) = ${sigmoid(rawScore * 2.5).toFixed(4)}\\n`;
  wStr += `  Sau softmax   → ${(probs[top.id] * 100).toFixed(1)}%`;
  document.getElementById('weights-display').textContent = wStr;
}
</script>
</body>
</html>
"""


@app.route("/predict", methods=["POST"])
def predict():
    """
    API endpoint nhận JSON và trả về kết quả dự đoán.

    Request body (JSON):
    {
        "age":      22,       // tuổi
        "gender":   0,        // 0=Nam, 1=Nữ, 2=Khác
        "hours":    3.0,      // giờ nghe nhạc/ngày
        "platform": 1,        // 0=Radio 1=Spotify 2=YouTube 3=Apple 4=Zing 5=SC
        "device":   0,        // 0=Điện thoại ... 4=TV
        "timing":   1,        // 0=Sáng 1=Làm/học 2=Chiều 3=Đêm 4=TậpTD 5=MọiLúc
        "freetime": 4.0,      // giờ rảnh/ngày
        "social":   2.0,      // giờ MXH/ngày
        "exposure": 2,        // 0=Rất ít ... 3=Cả ngày
        "language": 0         // 0=Việt 1=Anh 2=Hàn 3=Nhật 4=Khác
    }

    Response:
    {
        "top": { "id", "label", "desc", "color", "bg", "tc", "probability" },
        "visible": [ ...danh sách thể loại > 3%... ],
        "timing_label": "khi làm việc / học bài",
        "explanation": "...",
        "weight_detail": [ {"feature", "weight", "input", "product"}, ... ]
    }
    """
    data = request.get_json(force=True)

    try:
        features = normalize_inputs(
            age      = float(data.get("age",      22)),
            gender   = int(data.get("gender",   0)),
            hours    = float(data.get("hours",    3)),
            platform = int(data.get("platform", 1)),
            device   = int(data.get("device",   0)),
            freetime = float(data.get("freetime", 4)),
            social   = float(data.get("social",   2)),
            exposure = int(data.get("exposure", 2)),
            language = int(data.get("language", 0)),
        )
        timing = int(data.get("timing", 1))
        result = perceptron_predict(features, timing)
        return jsonify({"ok": True, **result})

    except (ValueError, KeyError) as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/genres", methods=["GET"])
def genres():
    """Trả về danh sách tất cả thể loại và thông tin màu sắc."""
    return jsonify(GENRES)


# ─── Chạy CLI demo ────────────────────────────────────────────────────────────

def cli_demo():
    """Demo nhanh trên terminal không cần Flask."""
    print("\n=== Perceptron — Dự đoán thể loại nhạc ===\n")
    inputs = {
        "age": 20, "gender": 1, "hours": 4, "platform": 1,
        "device": 2, "timing": 1,  # khi làm việc/học
        "freetime": 5, "social": 3, "exposure": 2, "language": 0,
    }
    print("Input:", inputs)

    features = normalize_inputs(**{k: v for k, v in inputs.items() if k != "timing"})
    result   = perceptron_predict(features, inputs["timing"])

    print(f"\nKết quả #1: {result['top']['label']}  {result['top']['probability']}%")
    print(f"Thời điểm : {result['timing_label']}")
    print(f"Lý do     : {result['explanation']}\n")

    print("Top thể loại phù hợp:")
    for i, g in enumerate(result["visible"]):
        bar = "█" * int(g["probability"] / 2)
        print(f"  {i+1:2}. {g['label']:15} {bar:25} {g['probability']:5.1f}%")

    print("\nChi tiết weights (thể loại #1):")
    for row in result["weight_detail"]:
        print(f"  {row['feature']:12} × {row['weight']:5.2f} = {row['product']:7.4f}")
    print(f"  Timing bonus : +{result['timing_bonus_top']:.2f}")
    print(f"  Bias         :  {result['bias_top']:.2f}")


if __name__ == "__main__":
    import sys
    if "--demo" in sys.argv:
        cli_demo()
    else:
        print("Server đang chạy tại http://localhost:5000")
        app.run(debug=True, port=5000)
