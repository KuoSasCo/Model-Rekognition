# Setup & Deployment

## Prerequisites

- AWS account with admin access
- Terraform ≥ 1.0
- Python 3.11+
- Raspberry Pi (any model with Python 3.11+ support)
- Railway account (for Flask deployment)

---

## 1. Provision AWS Infrastructure

```bash
cd terraform
terraform init
terraform apply
```

Note the outputs — you will need them in the next steps:

```bash
terraform output s3_bucket_name
terraform output sqs_queue_url
terraform output iot_endpoint
terraform output raspberry_access_key_id
terraform output -raw raspberry_secret_access_key
terraform output backend_access_key_id
terraform output -raw backend_secret_access_key
```

> **Note:** Terraform manages `sigr-detection-bucket-2026`. If you use a different bucket (`test-image-dataset-01234`), configure the S3 → SQS notification and IAM policies manually — see [infrastructure.md](infrastructure.md).

---

## 2. Configure the Rekognition Model

1. Go to **AWS Console → Rekognition → Use Custom Labels → Projects**.
2. Train or import your model.
3. Start the model version (minimum 1 inference unit).
4. Copy the **Project Version ARN** — you will set it in the Pi's config.

The current hardcoded ARN in `raspberry/main.py`:
```
arn:aws:rekognition:us-east-1:097300397506:project/model-black-background/version/model-black-background.2026-03-27T22.38.32/1774669112670
```

---

## 3. Deploy Flask Backend (Railway)

Set these environment variables in the Railway dashboard for the `Frontend` service:

| Variable | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | `terraform output backend_access_key_id` |
| `AWS_SECRET_ACCESS_KEY` | `terraform output -raw backend_secret_access_key` |
| `AWS_REGION` | `us-east-1` |
| `S3_BUCKET` | your bucket name |
| `AWS_IOT_ENDPOINT` | `terraform output iot_endpoint` |
| `MYSQLHOST` | Railway MySQL host |
| `MYSQLPORT` | Railway MySQL port |
| `MYSQL_DATABASE` | Railway MySQL database |
| `MYSQLUSER` | Railway MySQL user |
| `MYSQLPASSWORD` | Railway MySQL password |

Railway auto-deploys on push to `main`. The start command is in `Frontend/railway.toml`:
```
gunicorn app:app --bind 0.0.0.0:8080 --workers 2 --timeout 120
```

---

## 4. Configure the Raspberry Pi

Create `raspberry/.env`:

```env
AWS_ACCESS_KEY_ID=<terraform output raspberry_access_key_id>
AWS_SECRET_ACCESS_KEY=<terraform output -raw raspberry_secret_access_key>
AWS_REGION=us-east-1
MY_BUCKET=<your S3 bucket>
AWS_IOT_ENDPOINT=<terraform output iot_endpoint>
```

Install dependencies and run:

```bash
cd raspberry
python -m venv venv
source venv/bin/activate
pip install boto3 python-dotenv pillow
python main.py
```

To run on boot, create a systemd service:

```ini
# /etc/systemd/system/sigr.service
[Unit]
Description=SIGR Edge Processor
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/SIRG/raspberry
ExecStart=/home/pi/SIRG/raspberry/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable sigr
sudo systemctl start sigr
```

---

## 5. Serve the Frontend

`index.html` is a standalone file — no build step. Point `BACKEND` at the end of the file to your Railway URL:

```javascript
const BACKEND = 'https://model-rekognition-production.up.railway.app';
```

Host it anywhere (S3 static, GitHub Pages, Nginx, etc.) or open it directly in a browser.

---

## Local Development

```bash
# Flask
cd Frontend
pip install -r requirements.txt
cp .env.example .env  # fill in values
flask run

# Raspberry Pi
cd raspberry
pip install boto3 python-dotenv pillow
cp ../.env.example .env  # fill in values
python main.py
```
