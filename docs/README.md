# SIGR — Sistema Inteligente de Gestión de Residuos

Real-time waste classification system powered by Amazon Rekognition, a Raspberry Pi edge device, and a browser-based UI with live results via AWS IoT Core.

## Architecture

```
Browser (index.html)
  │
  ├─► POST /clasificar ──► Flask (Railway)
  │                           │
  │                           └─► S3 (test-image-dataset-01234/uploads/)
  │                                   │
  │                           Raspberry Pi ◄── polls S3 every 5s
  │                                   │
  │                                   └─► Rekognition DetectCustomLabels
  │                                           │
  │                                           └─► IoT Core (sigr/results)
  │                                                   │
  └─◄── WebSocket (mqtt.js) ◄────────────────────────┘
```

## Components

| Component | Location | Runtime |
|---|---|---|
| Frontend UI | `index.html` | Browser |
| Flask API | `Frontend/app.py` | Railway (gunicorn) |
| Edge processor | `raspberry/main.py` | Raspberry Pi |
| Infrastructure | `terraform/` | AWS |

## Docs

- [Architecture & Data Flow](architecture.md)
- [Setup & Deployment](setup.md)
- [AWS Infrastructure](infrastructure.md)
