#!/usr/bin/env python3
"""Publica de 3 a 5 Stories gerados e hospedados no GitHub Pages via API oficial da Meta."""
import os, time
import requests

def raise_meta_error(response, etapa):
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        # A Meta normalmente devolve o motivo real em JSON; registrar sem expor o token.
        try:
            detalhe = response.json()
        except ValueError:
            detalhe = response.text[:3000]
        raise RuntimeError(
            f"Erro da Meta na etapa '{etapa}': HTTP {response.status_code}. "
            f"Resposta: {detalhe}"
        ) from exc

def main():
    version = os.getenv("IG_GRAPH_API_VERSION", "").strip()
    token = os.getenv("IG_ACCESS_TOKEN", "").strip()
    ig_id = os.getenv("IG_USER_ID", "").strip()
    confirm = os.getenv("CONFIRMAR_PUBLICACAO", "")
    base = os.getenv("PAGES_URL", "").rstrip("/")
    count = int(os.getenv("STORY_COUNT", "0"))
    if confirm != "SIM":
        raise SystemExit("Bloqueado: CONFIRMAR_PUBLICACAO precisa ser SIM.")
    if not all((version, token, ig_id, base)):
        raise SystemExit("Faltam credenciais da Meta ou URL do GitHub Pages.")
    if count < 3 or count > 5:
        raise SystemExit(f"Quantidade inválida de Stories: {count}. Esperado de 3 a 5.")
    api = f"https://graph.facebook.com/{version}"
    published_ids = []
    with requests.Session() as session:
        for index in range(1, count + 1):
            image = f"{base}/story-assets/story-{index:02d}.jpg"
            response = session.post(f"{api}/{ig_id}/media", data={
                "image_url": image, "media_type": "STORIES", "access_token": token
            }, timeout=45)
            raise_meta_error(response, f"criação do Story {index} (imagem: {image})")
            creation_id = response.json().get("id")
            if not creation_id:
                raise RuntimeError(f"Meta não retornou ID de mídia para Story {index}. Resposta: {response.text[:1000]}")
            for _ in range(18):
                status = session.get(f"{api}/{creation_id}", params={
                    "fields": "status_code", "access_token": token
                }, timeout=30)
                raise_meta_error(status, f"consulta do processamento do Story {index}")
                code = status.json().get("status_code")
                if code == "FINISHED":
                    break
                if code == "ERROR":
                    raise RuntimeError(f"Meta não conseguiu processar o Story {index}. Resposta: {status.text[:1000]}")
                time.sleep(5)
            else:
                raise RuntimeError(f"Tempo esgotado aguardando processamento do Story {index}.")
            published = session.post(f"{api}/{ig_id}/media_publish", data={
                "creation_id": creation_id, "access_token": token
            }, timeout=45)
            raise_meta_error(published, f"publicação do Story {index}")
            media_id = published.json().get("id")
            if not media_id:
                raise RuntimeError(f"Meta não confirmou a publicação do Story {index}. Resposta: {published.text[:1000]}")
            published_ids.append(media_id)
            print(f"STORY {index}/{count} PUBLICADO. media_id={media_id}")
            if index < count:
                time.sleep(8)
    print(f"RODADA CONCLUÍDA: {len(published_ids)} de {count} Stories publicados.")
    print("CTA da arte: envie OFERTAS no Direct para receber o link do Telegram.")

if __name__ == "__main__":
    main()
