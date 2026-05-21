# SIGR — Backend Flask

Backend del Sistema Inteligente de Gestión de Residuos.  
Recibe imágenes desde la página web, las sube a S3 y las clasifica con AWS Rekognition Custom Labels.

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Verifica que el servidor está corriendo |
| POST | `/clasificar` | Recibe imagen y retorna clasificación |
| POST | `/feedback` | Guarda feedback en MySQL |
| GET | `/feedback` | Lista todos los feedbacks guardados |

### POST /clasificar
**Body:** `multipart/form-data` con campo `imagen` (archivo de imagen)

**Respuesta exitosa:**
```json
{
  "detectado": true,
  "label": "Reciclable",
  "confianza": 97.4,
  "icono": "♻️",
  "clase": "res-reciclable",
  "desc": "Este residuo puede ser reciclado.",
  "imagen_key": "uploads/abc123.jpg",
  "todos_los_labels": [...]
}
```

### POST /feedback
**Body:** `application/json`
```json
{
  "nombre": "Juan",
  "email": "juan@email.com",
  "comentario": "Excelente sistema"
}
```

---

## Despliegue en Railway

### 1. Crear cuenta y proyecto
1. Ve a [railway.app](https://railway.app) y crea una cuenta
2. Click en **New Project** → **Deploy from GitHub repo**
3. Conecta tu repositorio de GitHub con estos archivos

### 2. Agregar MySQL
1. En tu proyecto de Railway click en **+ New** → **Database** → **MySQL**
2. Railway crea la base de datos automáticamente
3. Click en la base de datos → pestaña **Connect** → copia las variables

### 3. Configurar variables de entorno
En Railway → tu servicio Flask → pestaña **Variables**, agrega:

```
AWS_ACCESS_KEY_ID        = tu_access_key
AWS_SECRET_ACCESS_KEY    = tu_secret_key
AWS_REGION               = us-east-1
S3_BUCKET                = test-image-dataset-01234
REKOGNITION_MODEL_ARN    = arn:aws:rekognition:...
MIN_CONFIDENCE           = 50
DB_HOST                  = (lo da Railway automáticamente)
DB_PORT                  = (lo da Railway automáticamente)
DB_NAME                  = (lo da Railway automáticamente)
DB_USER                  = (lo da Railway automáticamente)
DB_PASS                  = (lo da Railway automáticamente)
```

> Railway puede conectar la base de datos directamente al servicio con **Reference Variables**, lo que llena DB_HOST, DB_PORT, etc. automáticamente.

### 4. Obtener la URL pública
Una vez desplegado, Railway te da una URL pública tipo:
`https://sigr-backend-production.up.railway.app`

Esa URL va en la página web en los dos fetch():
```js
await fetch('https://sigr-backend-production.up.railway.app/clasificar', ...)
await fetch('https://sigr-backend-production.up.railway.app/feedback', ...)
```

---

## Desarrollo local

```bash
# 1. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Copiar y configurar variables de entorno
cp .env.example .env
# Editar .env con tus valores reales

# 4. Correr el servidor
python app.py
```

El servidor queda en: `http://localhost:5000`
