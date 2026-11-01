#!/usr/bin/env python3
"""Publica um Story gerado e hospedado no GitHub Pages usando a API oficial da Meta."""
import csv, os, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent

def main():
    version = os.getenv("IG_GRAPH_API_VERSION", "").strip()
    token = os.getenv("IG_ACCESS_TOKEN", "").strip()
    ig_id = os.getenv("IG_USER_ID", "").strip()
    confirm = os.getenv("CONFIRMAR_PUBLICACAO", "")
    base = os.getenv("PAGES_URL", "").rstrip("/")
    if confirm != "SIM":
        raise SystemExit("Bloqueado: CONFIRMAR_PUBLICACAO precisa ser SIM.")
    if not all((version, token, ig_id, base)):
        raise SystemExit("Faltam credenciais da Meta ou URL do GitHub Pages.")
    image = base + "/story-assets/story.jpg"
    api = f"https://graph.facebook.com/{version}"
    with requests.Session() as session:
        response = session.post(f"{api}/{ig_id}/media", data={
            "image_url": image, "media_type": "STORIES", "access_token": token
        }, timeout=45)
        response.raise_for_status()
        creation_id = response.json().get("id")
        if not creation_id:
            raise RuntimeError(f"Meta não retornou ID de mídia: {response.text[:400]}")
        for _ in range(18):
            status = session.get(f"{api}/{creation_id}", params={
                "fields": "status_code", "access_token": token
            }, timeout=30)
            status.raise_for_status()
            code = status.json().get("status_code")
            if code == "FINISHED":
                break
            if code == "ERROR":
                raise RuntimeError("Meta não conseguiu processar a arte hospedada.")
            time.sleep(5)
        else:
            raise RuntimeError("Tempo esgotado aguardando processamento do Story.")
        published = session.post(f"{api}/{ig_id}/media_publish", data={
            "creation_id": creation_id, "access_token": token
        }, timeout=45)
        published.raise_for_status()
        print(f"STORY PUBLICADO. media_id={published.json().get('id')}")
        print("CTA da arte: ACESSE O LINK NA BIO.")

if __name__ == "__main__":
    main()
