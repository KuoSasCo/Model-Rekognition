import os
import uuid
import datetime
import hashlib
import hmac
import urllib.parse
import boto3
import mysql.connector
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv



app = Flask(__name__)
CORS(app)

# ── AWS ──────────────────────────────────────────────────────────
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION     = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET      = os.getenv("S3_BUCKET")
IOT_ENDPOINT   = os.getenv("AWS_IOT_ENDPOINT")

# ── MySQL ─────────────────────────────────────────────────────────
DB_HOST = os.getenv("MYSQLHOST")
DB_PORT = int(os.getenv("MYSQLPORT", "3306"))
DB_NAME = os.getenv("MYSQL_DATABASE")
DB_USER = os.getenv("MYSQLUSER")
DB_PASS = os.getenv("MYSQLPASSWORD")


def get_db():
    return mysql.connector.connect(
        host=DB_HOST, port=DB_PORT,
        database=DB_NAME, user=DB_USER, password=DB_PASS
    )


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            nombre     VARCHAR(120),
            email      VARCHAR(180),
            comentario TEXT NOT NULL,
            creado_en  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()


def get_s3_client():
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=AWS_REGION
    )
    return session.client("s3")


def _iot_websocket_url():
    """Generate a SigV4-signed WebSocket URL for AWS IoT Core MQTT."""
    service    = 'iotdevicegateway'
    algorithm  = 'AWS4-HMAC-SHA256'
    now        = datetime.datetime.utcnow()
    amz_date   = now.strftime('%Y%m%dT%H%M%SZ')
    date_stamp = now.strftime('%Y%m%d')

    credential_scope = f'{date_stamp}/{AWS_REGION}/{service}/aws4_request'
    credential = urllib.parse.quote(f'{AWS_ACCESS_KEY}/{credential_scope}', safe='')

    qs = (
        f'X-Amz-Algorithm={algorithm}'
        f'&X-Amz-Credential={credential}'
        f'&X-Amz-Date={amz_date}'
        f'&X-Amz-Expires=3600'
        f'&X-Amz-SignedHeaders=host'
    )

    canonical_request = '\n'.join([
        'GET', '/mqtt', qs,
        f'host:{IOT_ENDPOINT}\n',
        'host',
        hashlib.sha256(b'').hexdigest()
    ])

    string_to_sign = '\n'.join([
        algorithm, amz_date, credential_scope,
        hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()
    ])

    def _sign(key, msg):
        if isinstance(key, str):
            key = key.encode('utf-8')
        return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

    signing_key = _sign(
        _sign(_sign(_sign(f'AWS4{AWS_SECRET_KEY}', date_stamp), AWS_REGION), service),
        'aws4_request'
    )
    signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

    return f'wss://{IOT_ENDPOINT}/mqtt?{qs}&X-Amz-Signature={signature}'


@app.route("/health", methods=["GET"])
def health():
    from datetime import datetime as _dt
    return jsonify({"status": "ok", "timestamp": _dt.utcnow().isoformat()})


@app.route("/iot-url", methods=["GET"])
def iot_url():
    import traceback
    try:
        if not IOT_ENDPOINT:
            return jsonify({"error": "AWS_IOT_ENDPOINT not configured"}), 500
        return jsonify({"websocket_url": _iot_websocket_url()})
    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/clasificar", methods=["POST"])
def clasificar():
    if "imagen" not in request.files:
        return jsonify({"error": "No se envió ninguna imagen."}), 400

    archivo = request.files["imagen"]
    extension = archivo.filename.rsplit(".", 1)[-1].lower()
    nombre_s3 = f"uploads/{uuid.uuid4().hex}.{extension}"

    try:
        s3 = get_s3_client()
        s3.upload_fileobj(
            archivo, S3_BUCKET, nombre_s3,
            ExtraArgs={"ContentType": archivo.content_type}
        )
        return jsonify({"imagen_key": nombre_s3, "status": "queued"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/feedback", methods=["POST"])
def feedback():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No se recibieron datos."}), 400

    comentario = data.get("comentario", "").strip()
    if not comentario:
        return jsonify({"error": "El comentario es obligatorio."}), 400

    nombre = data.get("nombre", "").strip() or None
    email  = data.get("email",  "").strip() or None

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO feedback (nombre, email, comentario) VALUES (%s, %s, %s)",
            (nombre, email, comentario)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"ok": True, "mensaje": "Feedback guardado correctamente."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/feedback", methods=["GET"])
def listar_feedback():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM feedback ORDER BY creado_en DESC")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        for row in rows:
            if row.get("creado_en"):
                row["creado_en"] = row["creado_en"].isoformat()
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    init_db()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)