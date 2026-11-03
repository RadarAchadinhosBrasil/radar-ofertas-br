import os
import time
import requests

API_VERSION = os.environ["IG_GRAPH_API_VERSION"]
IG_ID = os.environ["IG_USER_ID"]
TOKEN = os.environ["IG_ACCESS_TOKEN"]
IMAGE_URL = os.environ["IG_REMINDER_IMAGE_URL"]

CAPTION = """🔥 SEXTA-FEIRA DE OFERTAS!

Não esqueça de conferir o Radar de Ofertas BR! Todos os dias temos oportunidades e descontos para você economizar.

📲 Entre no nosso Telegram e receba as ofertas diretamente no celular.

👉 Acesse o link da bio e entre no canal: @radarachadinhosbrasil

Ative as notificações e não perca nenhuma promoção! 🛒

#RadarDeOfertas #Achadinhos #Ofertas"""

api = f"https://graph.facebook.com/{API_VERSION}"
session = requests.Session()
image = session.get(IMAGE_URL, timeout=45)
image.raise_for_status()
if not image.headers.get("Content-Type", "").lower().startswith("image/jpeg"):
    raise SystemExit("A imagem pública não é JPG.")

created = session.post(
    f"{api}/{IG_ID}/media",
    data={"image_url": IMAGE_URL, "caption": CAPTION, "access_token": TOKEN},
    timeout=45,
)
created.raise_for_status()
creation_id = created.json().get("id")
if not creation_id:
    raise SystemExit("A Meta não retornou o ID da mídia.")

for _ in range(36):
    status = session.get(
        f"{api}/{creation_id}",
        params={"fields": "status_code", "access_token": TOKEN},
        timeout=30,
    )
    status.raise_for_status()
    code = status.json().get("status_code")
    print("Status do processamento:", code)
    if code == "FINISHED":
        break
    if code == "ERROR":
        raise SystemExit("A Meta informou erro no processamento da imagem.")
    time.sleep(5)
else:
    raise SystemExit("Tempo esgotado aguardando processamento.")

published = session.post(
    f"{api}/{IG_ID}/media_publish",
    data={"creation_id": creation_id, "access_token": TOKEN},
    timeout=45,
)
published.raise_for_status()
print("PUBLICADO_NO_INSTAGRAM | media_id=" + str(published.json().get("id")))
