#!/usr/bin/env python3
"""Publica uma imagem no Feed ou nos Stories de uma Página do Facebook.
Execução manual; não seleciona produtos nem altera automações do Instagram/Telegram.
"""
import os
import sys
import requests


def required(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Configuração ausente: {name}")
    return value


def fail(response, action):
    try:
        err = response.json().get("error", {})
        detail = f"{err.get('message', response.text[:1000])} (code={err.get('code')})"
    except Exception:
        detail = response.text[:1000]
    raise RuntimeError(f"Meta API falhou em {action}: HTTP {response.status_code}: {detail}")


def main():
    if required("FB_CONFIRM") != "SIM":
        raise SystemExit("Bloqueado: FB_CONFIRM precisa ser SIM.")
    page_id = required("FB_PAGE_ID")
    token = required("FB_PAGE_ACCESS_TOKEN")
    version = required("FB_GRAPH_API_VERSION")
    image_url = required("FB_IMAGE_URL")
    mode = required("FB_MODE").lower()
    message = os.getenv("FB_MESSAGE", "").strip()
    if not image_url.startswith("https://"):
        raise SystemExit("FB_IMAGE_URL precisa ser HTTPS.")
    if mode not in ("feed", "story"):
        raise SystemExit("FB_MODE deve ser feed ou story.")
    if mode == "feed" and not message:
        raise SystemExit("FB_MESSAGE é obrigatório para publicação no Feed.")

    api = f"https://graph.facebook.com/{version}"
    with requests.Session() as session:
        check = session.get(image_url, timeout=40)
        check.raise_for_status()
        if not check.headers.get("Content-Type", "").lower().startswith("image/"):
            raise SystemExit("A URL informada não entrega uma imagem.")
        if len(check.content) < 5000:
            raise SystemExit("A imagem parece incompleta.")

        if mode == "feed":
            response = session.post(
                f"{api}/{page_id}/photos",
                data={"url": image_url, "caption": message, "access_token": token},
                timeout=60,
            )
            if not response.ok:
                fail(response, "publicação no Feed")
            photo_id = response.json().get("post_id") or response.json().get("id")
            if not photo_id:
                raise RuntimeError("A Meta não retornou ID da publicação.")
            print(f"FEED FACEBOOK PUBLICADO. id={photo_id}")
        else:
            uploaded = session.post(
                f"{api}/{page_id}/photos",
                data={"url": image_url, "published": "false", "access_token": token},
                timeout=60,
            )
            if not uploaded.ok:
                fail(uploaded, "envio da foto para Story")
            photo_id = uploaded.json().get("id")
            if not photo_id:
                raise RuntimeError("A Meta não retornou ID da foto preparada.")
            published = session.post(
                f"{api}/{page_id}/photo_stories",
                data={"photo_id": photo_id, "access_token": token},
                timeout=60,
            )
            if not published.ok:
                fail(published, "publicação do Story")
            story_id = published.json().get("post_id") or published.json().get("id")
            if not story_id:
                raise RuntimeError("A Meta não confirmou o ID do Story.")
            print(f"STORY FACEBOOK PUBLICADO. id={story_id}")


if __name__ == "__main__":
    main()
