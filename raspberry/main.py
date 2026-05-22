import os
import boto3
import io
import json
import time
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

BUCKET         = os.getenv('MY_BUCKET')
IOT_ENDPOINT   = os.getenv('AWS_IOT_ENDPOINT')
MODEL          = 'arn:aws:rekognition:us-east-1:097300397506:project/model-black-background/version/model-black-background.2026-03-27T22.38.32/1774669112670'
MIN_CONFIDENCE = 80
PREFIX         = 'uploads/'
CHECK_INTERVAL = 5

procesados = set()

iot_data = boto3.client(
    'iot-data',
    region_name='us-east-1',
    endpoint_url=f"https://{IOT_ENDPOINT}"
)


def display_image(bucket, photo, response):
    s3_connection = boto3.resource('s3')
    s3_object = s3_connection.Object(bucket, photo)
    s3_response = s3_object.get()
    stream = io.BytesIO(s3_response['Body'].read())
    image = Image.open(stream)

    imgWidth, imgHeight = image.size
    draw = ImageDraw.Draw(image)

    print('Detected custom labels for ' + photo)
    for customLabel in response['CustomLabels']:
        print('Label ' + str(customLabel['Name']))
        print('Confidence ' + str(customLabel['Confidence']))
        if 'Geometry' in customLabel:
            box = customLabel['Geometry']['BoundingBox']
            left = imgWidth * box['Left']
            top = imgHeight * box['Top']
            width = imgWidth * box['Width']
            height = imgHeight * box['Height']
            try:
                fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 50)
            except:
                fnt = ImageFont.load_default()
            draw.text((left, top), customLabel['Name'], fill='#00d400', font=fnt)
            points = (
                (left, top),
                (left + width, top),
                (left + width, top + height),
                (left, top + height),
                (left, top)
            )
            draw.line(points, fill='#00d400', width=5)

    draw.rectangle([(0, imgHeight - 80), (imgWidth, imgHeight)], fill=(20, 20, 20))
    if response['CustomLabels']:
        mejor = max(response['CustomLabels'], key=lambda x: x['Confidence'])
        texto = f"{mejor['Name'].upper()}  —  {round(mejor['Confidence'], 1)}%"
    else:
        texto = "SIN DETECCIÓN"
    try:
        fnt_banner = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 32)
    except:
        fnt_banner = ImageFont.load_default()
    draw.text((20, imgHeight - 60), texto, fill='#00d400', font=fnt_banner)
    draw.text((20, imgHeight - 25), datetime.now().strftime('%H:%M:%S'), fill='#888888', font=fnt_banner)

    image.show()


def show_custom_labels(bucket, photo):
    session = boto3.Session(region_name='us-east-1')
    client = session.client('rekognition')
    response = client.detect_custom_labels(
        Image={'S3Object': {'Bucket': bucket, 'Name': photo}},
        MinConfidence=MIN_CONFIDENCE,
        ProjectVersionArn=MODEL
    )
    display_image(bucket, photo, response)

    payload = {"photo": photo, "detections": response['CustomLabels']}
    iot_data.publish(
        topic='sigr/results',
        qos=1,
        payload=json.dumps(payload)
    )
    print(f"[AWS IoT] Result dispatched — {len(response['CustomLabels'])} label(s)")

    return len(response['CustomLabels'])


def revisar_bucket():
    s3 = boto3.client('s3', region_name='us-east-1')
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix=PREFIX)
    objetos = response.get('Contents', [])
    objetos.sort(key=lambda x: x['LastModified'], reverse=True)

    for obj in objetos:
        key = obj['Key']
        if key in procesados or key.endswith('/'):
            continue
        procesados.add(key)
        print("\nAnalyzing " + key + " from bucket " + BUCKET)
        label_count = show_custom_labels(BUCKET, key)
        print("Custom labels detected: " + str(label_count))
        break


def main():
    print('SIGR — Raspberry Pi en espera de imágenes...')
    print(f'Bucket : {BUCKET}')
    print(f'Revisando cada {CHECK_INTERVAL} segundos\n')
    while True:
        try:
            revisar_bucket()
        except Exception as e:
            print(f'Error: {e}')
        time.sleep(CHECK_INTERVAL)


if __name__ == '__main__':
    main()
