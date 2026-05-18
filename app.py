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

HTML_PAGE = open(__file__.replace("app.py", "music_perceptron.html"),
                 encoding="utf-8").read() if False else None
# Nếu bạn muốn serve HTML riêng, đặt music_perceptron.html cùng thư mục
# và bỏ comment phần trên. Mặc định API trả JSON để dùng với frontend bất kỳ.


@app.route("/")
def index():
    """Trả về trang HTML (nếu có file music_perceptron.html kế bên)"""
    import os
    html_path = os.path.join(os.path.dirname(__file__), "music_perceptron.html")
    if os.path.exists(html_path):
        with open(html_path, encoding="utf-8") as f:
            return f.read()
    return "<h2>Đặt file <code>music_perceptron.html</code> cùng thư mục với app.py</h2>"


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