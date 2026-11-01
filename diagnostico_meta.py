#!/usr/bin/env python3
"""Diagnóstico somente leitura da conexão Instagram/Meta. Nunca publica conteúdo."""
import os
import requests

VERSION = os.getenv("IG_GRAPH_API_VERSION", "").strip()
TOKEN = os.getenv("IG_ACCESS_TOKEN", "").strip()
IG_USER_ID = os.getenv("IG_USER_ID", "").strip()
BASE = f"https://graph.facebook.com/{VERSION}"

def request(label, path, params=None):
    try:
        response = requests.get(
            f"{BASE}/{path.lstrip('/')}",
            params=params or {},
            headers={"Authorization": f"Bearer {TOKEN}"},
            timeout=30,
        )
        try:
            payload = response.json()
        except ValueError:
            print(f"{label}: resposta não JSON (HTTP {response.status_code})")
            return None

        if not response.ok or "error" in payload:
            error = payload.get("error", {})
            print(
                f"{label}: FALHOU | HTTP {response.status_code} | "
                f"code={error.get('code')} | subcode={error.get('error_subcode')} | "
                f"message={error.get('message', 'sem mensagem')}"
            )
            return None
        print(f"{label}: OK")
        return payload
    except requests.RequestException as exc:
        print(f"{label}: falha de conexão ({type(exc).__name__})")
        return None

def main():
    if not all((VERSION, TOKEN, IG_USER_ID)):
        raise SystemExit("Faltam IG_GRAPH_API_VERSION, IG_ACCESS_TOKEN ou IG_USER_ID nos Secrets/Variables.")

    print("Diagnóstico Meta — somente leitura; nenhuma publicação será feita.")
    permissions = request("Permissões do token", "me/permissions")
    if permissions:
        granted = sorted(
            item.get("permission", "")
            for item in permissions.get("data", [])
            if item.get("status") == "granted"
        )
        print("Permissões concedidas:", ", ".join(granted) if granted else "nenhuma listada")
        expected = ("instagram_basic", "instagram_content_publish", "pages_show_list", "pages_read_engagement")
        for name in expected:
            status = next(
                (item.get("status") for item in permissions.get("data", [])
                 if item.get("permission") == name),
                "ausente",
            )
            print(f"  {name}: {status}")

    profile = request(
        "Conta profissional Instagram",
        IG_USER_ID,
        {"fields": "id,username,account_type"},
    )
    if profile:
        print("Conta Instagram:", profile.get("username", "(nome não retornado)"))
        print("Tipo da conta:", profile.get("account_type", "(não retornado)"))

    pages = request(
        "Páginas acessíveis pelo token",
        "me/accounts",
        {"fields": "name,instagram_business_account", "limit": 25},
    )
    if pages:
        rows = pages.get("data", [])
        linked = sum(1 for page in rows if page.get("instagram_business_account"))
        print("Páginas retornadas:", len(rows))
        print("Páginas com conta Instagram profissional vinculada:", linked)

    print("Fim do diagnóstico. Nenhum token foi exibido e nenhuma publicação foi tentada.")

if __name__ == "__main__":
    main()
