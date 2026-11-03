#!/usr/bin/env python3
"""Publica de 3 a 5 Stories gerados e hospedados no GitHub Pages via API oficial da Meta."""
import os, time
import requests


def meta_error_details(response):
    try:
        return response.json()
    except ValueError:
        return {"message": response.text[:3000]}


def raise_meta_error(response, etapa):
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        # Registrar o motivo da Meta sem expor o token.
        detalhe = meta_error_details(response)
        raise RuntimeError(
            f"Erro da Meta na etapa '{etapa}': HTTP {response.status_code}. "
            f"Resposta: {detalhe}"
        ) from exc


def publish_story_with_retry(session, api, ig_id, creation_id, token, index):
    """Repete apenas o publish do mesmo creation_id quando a Meta ainda processa a mídia."""
    delays = (10, 20, 30, 45, 60, 60)
    for attempt in range(len(delays) + 1):
        response = session.post(f"{api}/{ig_id}/media_publish", data={
            "creation_id": creation_id, "access_token": token
        }, timeout=45)

        if response.ok:
            payload = response.json()
            media_id = payload.get("id")
            if not media_id:
                raise RuntimeError(
                    f"Meta não confirmou a publicação do Story {index}. "
                    f"Resposta: {payload}"
                )
            return media_id

        detalhe = meta_error_details(response)
        error = detalhe.get("error", {}) if isinstance(detalhe, dict) else {}
        # Erro transitório observado: 9007 / 2207027 = mídia ainda não disponível.
        ainda_processando = (
            response.status_code == 400
            and error.get("code") == 9007
            and error.get("error_subcode") == 2207027
        )
        if not ainda_processando or attempt >= len(delays):
            raise_meta_error(response, f"publicação do Story {index}")

        espera = delays[attempt]
        print(
            f"Story {index}: mídia ainda não liberada pela Meta "
            f"(tentativa {attempt + 1}/{len(delays) + 1}). "
            f"Aguardando {espera}s e tentando novamente o mesmo conteúdo."
        )
        time.sleep(espera)


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
                raise RuntimeError(
                    f"Meta não retornou ID de mídia para Story {index}. "
                    f"Resposta: {response.text[:1000]}"
                )

            # Aguardar até 3 minutos pelo processamento da mídia.
            for poll in range(36):
                status = session.get(f"{api}/{creation_id}", params={
                    "fields": "status_code", "access_token": token
                }, timeout=30)
                raise_meta_error(status, f"consulta do processamento do Story {index}")
                code = status.json().get("status_code")
                if code == "FINISHED":
                    break
                if code == "ERROR":
                    raise RuntimeError(
                        f"Meta não conseguiu processar o Story {index}. "
                        f"Resposta: {status.text[:1000]}"
                    )
                if poll < 35:
                    time.sleep(5)
            else:
                raise RuntimeError(
                    f"Tempo esgotado aguardando processamento do Story {index} "
                    "após 3 minutos."
                )

            # Se a Meta ainda não liberou o media_publish, repetir o mesmo creation_id.
            media_id = publish_story_with_retry(
                session, api, ig_id, creation_id, token, index
            )
            published_ids.append(media_id)
            print(f"STORY {index}/{count} PUBLICADO. media_id={media_id}")
            if index < count:
                time.sleep(8)

    print(f"RODADA CONCLUÍDA: {len(published_ids)} de {count} Stories publicados.")
    print("CTA da arte: envie OFERTAS no Direct para receber o link do Telegram.")


if __name__ == "__main__":
    main()
