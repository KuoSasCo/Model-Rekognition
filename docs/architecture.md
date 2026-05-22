# Architecture & Data Flow

## Overview

SIGR classifies waste images in real time. The browser uploads a photo, the Raspberry Pi runs inference via Amazon Rekognition Custom Labels, and the result is pushed back to the browser through AWS IoT Core over MQTT/WebSocket — no polling, no page refresh.

## Data Flow

### 1. Connection phase (browser)
1. User clicks **Clasificar**.
2. Browser calls `GET /iot-url` → Flask generates a SigV4-signed WebSocket URL for IoT Core.
3. Browser connects to IoT Core via `mqtt.js` over `wss://` and subscribes to `sigr/results`.

### 2. Upload phase
4. Browser calls `POST /clasificar` with the image file.
5. Flask converts the image to JPEG (Pillow) and uploads it to S3 under `uploads/<uuid>.jpg`.
6. Flask returns `{ "imagen_key": "uploads/<uuid>.jpg" }`.

### 3. Processing phase (Raspberry Pi)
7. Pi polls S3 (`uploads/` prefix) every 5 seconds.
8. On a new key, Pi calls `rekognition:DetectCustomLabels` with `MinConfidence=80`.
9. Pi annotates the image locally (bounding boxes + result banner) and displays it.
10. Pi publishes `{ "photo": "<key>", "detections": [...] }` to IoT topic `sigr/results`.

### 4. Result phase (browser)
11. Browser receives the MQTT message on `sigr/results`.
12. It matches the `photo` key to the pending upload and renders the detections.
13. MQTT client disconnects.

## Sequence Diagram

```
Browser          Flask (Railway)        S3              Raspberry Pi       IoT Core
  │                    │                 │                    │                │
  ├── GET /iot-url ───►│                 │                    │                │
  │◄── signed URL ─────┤                 │                    │                │
  │                    │                 │                    │                │
  ├── wss:// connect ──────────────────────────────────────────────────────────►│
  ├── SUBSCRIBE sigr/results ──────────────────────────────────────────────────►│
  │                    │                 │                    │                │
  ├── POST /clasificar►│                 │                    │                │
  │                    ├── PutObject ───►│                    │                │
  │◄── imagen_key ─────┤                 │                    │                │
  │                    │                 │                    │                │
  │                    │                 │◄─── list_objects ──┤                │
  │                    │                 ├──── GetObject ─────►│                │
  │                    │                 │    DetectCustomLabels                │
  │                    │                 │                    ├── Publish ─────►│
  │◄── MQTT message ───────────────────────────────────────────────────────────┤
  │    render result   │                 │                    │                │
```

## Key Design Decisions

**SigV4 signed URLs for IoT WebSocket** — Flask signs the WebSocket URL server-side using the `sigr-flask-backend` IAM credentials. The browser never sees raw AWS credentials.

**S3 polling on the Pi** — The Pi polls S3 directly every 5 seconds rather than consuming SQS events. This keeps the Pi code simple and stateless; it processes the most recent unprocessed upload on each tick.

**JPEG conversion on upload** — Flask converts every upload to JPEG before writing to S3. Rekognition Custom Labels only accepts JPEG and PNG; browsers may send WEBP, HEIC, or other formats.

**IoT Core topic: `sigr/results`** — Single topic; the browser matches incoming messages to the pending upload by comparing `payload.photo` to the key returned by `/clasificar`.

## IAM Users

| User | Purpose | Key permissions |
|---|---|---|
| `sigr-flask-backend` | Flask API (Railway) | `s3:PutObject` on `uploads/*`, `iot:Connect/Subscribe/Receive` |
| `sigr-raspberry-pi-edge` | Raspberry Pi | `s3:GetObject`, `sqs:*`, `rekognition:DetectCustomLabels`, `iot:Connect/Publish` |
