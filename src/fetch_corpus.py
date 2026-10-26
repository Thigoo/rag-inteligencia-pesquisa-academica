import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import requests
import yaml

# Diretórios base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
INVENTORY_DIR = DATA_DIR / "inventory"


def calculate_sha256(filepath: Path) -> str:
    """Calcula o hash SHA256 de um arquivo."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def calculate_string_sha256(text: str) -> str:
    """Calcula o hash SHA256 de uma string/manifesto."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_manifest(manifest_path: Path) -> dict:
    """Lê e retorna o dicionário do corpus_manifest.yaml."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifesto não encontrado em: {manifest_path}")
    with open(manifest_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def download_file(url: str, dest_path: Path, rate_limit: float = 1.0) -> dict:
    """
    Baixa um arquivo via HTTP GET.
    Retorna dicionário com status e metadados.
    """
    if dest_path.exists():
        bytes_size = dest_path.stat().st_size
        return {
            "path": str(dest_path.relative_to(DATA_DIR)),
            "bytes": bytes_size,
            "sha256": calculate_sha256(dest_path),
            "origem": url,
            "status": "cached",
        }

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    time.sleep(rate_limit)

    try:
        headers = {"User-Agent": "Residencia-IA-RAG/1.0"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        with open(dest_path, "wb") as f:
            f.write(response.content)

        return {
            "path": str(dest_path.relative_to(DATA_DIR)),
            "bytes": len(response.content),
            "sha256": calculate_sha256(dest_path),
            "origem": url,
            "status": "ok",
        }
    except Exception as e:
        return {
            "origem": url,
            "erro": str(e),
            "status": "failed",
        }


def process_base(base: dict, version_dir: Path) -> tuple[list, list]:
    """Processa a coleta de uma base declarada no manifesto."""
    base_id = base.get("base_id")
    natureza = base.get("natureza")
    acesso = base.get("acesso", {})
    tipo_acesso = acesso.get("tipo")
    rate_limit = acesso.get("rate_limit_seg", 1.0)

    base_out_dir = version_dir / base_id
    base_out_dir.mkdir(parents=True, exist_ok=True)

    arquivos_coletados = []
    falhas = []

    # 1. Downloads de arquivos PDF / HTTP
    if tipo_acesso == "http_pdf":
        urls = acesso.get("urls", [])
        for url in urls:
            filename = Path(urlparse(url).path).name or f"{base_id}_file.pdf"
            dest_path = base_out_dir / filename
            res = download_file(url, dest_path, rate_limit)
            if res.get("status") in ["ok", "cached"]:
                res["base_id"] = base_id
                res["tipo"] = base.get("formato", "pdf")
                res["coletado_em"] = datetime.now(timezone.utc).isoformat()
                arquivos_coletados.append(res)
            else:
                falhas.append(res)

    # 2. Consultas REST API (ex: OpenAlex, PNCP)
    elif tipo_acesso == "rest_api":
        endpoint = acesso.get("endpoint")
        params = acesso.get("params", {})
        dest_path = base_out_dir / "data.json"

        if dest_path.exists():
            bytes_size = dest_path.stat().st_size
            arquivos_coletados.append({
                "path": str(dest_path.relative_to(DATA_DIR)),
                "base_id": base_id,
                "tipo": "json",
                "bytes": bytes_size,
                "sha256": calculate_sha256(dest_path),
                "origem": endpoint,
                "coletado_em": datetime.now(timezone.utc).isoformat(),
                "status": "cached"
            })
        else:
            time.sleep(rate_limit)
            try:
                headers = {"User-Agent": "Residencia-IA-RAG/1.0"}
                resp = requests.get(endpoint, params=params, headers=headers, timeout=30)
                resp.raise_for_status()

                data = resp.json()
                with open(dest_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                bytes_size = dest_path.stat().st_size
                arquivos_coletados.append({
                    "path": str(dest_path.relative_to(DATA_DIR)),
                    "base_id": base_id,
                    "tipo": "json",
                    "bytes": bytes_size,
                    "sha256": calculate_sha256(dest_path),
                    "origem": endpoint,
                    "coletado_em": datetime.now(timezone.utc).isoformat(),
                    "status": "ok"
                })
            except Exception as e:
                falhas.append({"origem": endpoint, "erro": str(e), "status": "failed"})

    # 3. Base Sintética / Arquivo Local
    elif tipo_acesso in ["sintetico", "arquivo_local"]:
        paths_list = acesso.get("arquivos_locais", [])
        if not paths_list:
            raw_single = acesso.get("arquivo_origem") or acesso.get("caminho_local")
            if raw_single:
                paths_list = [raw_single]

        for raw_path in paths_list:
            src_path = Path(raw_path)
            if not src_path.is_absolute():
                src_path = BASE_DIR / src_path

            if src_path.exists():
                dest = base_out_dir / src_path.name
                dest.write_bytes(src_path.read_bytes())
                arquivos_coletados.append({
                    "path": str(dest.relative_to(DATA_DIR)),
                    "base_id": base_id,
                    "tipo": src_path.suffix.replace(".", "") or base.get("formato", "json"),
                    "bytes": dest.stat().st_size,
                    "sha256": calculate_sha256(dest),
                    "origem": str(src_path),
                    "coletado_em": datetime.now(timezone.utc).isoformat(),
                    "status": "ok"
                })
            else:
                falhas.append({"origem": base_id, "erro": f"Arquivo local não localizado em {raw_path}", "status": "failed"})

    return arquivos_coletados, falhas


def generate_inventory_data(manifest: dict, version_name: str, arquivos: list, falhas: list, manifest_str: str) -> dict:
    """Gera o dicionário no formato vX.json exigido pelo inventário."""
    totais_bytes = sum(a.get("bytes", 0) for a in arquivos)

    por_base_map = {}
    for base in manifest.get("bases", []):
        b_id = base.get("base_id")
        por_base_map[b_id] = {
            "base_id": b_id,
            "natureza": base.get("natureza"),
            "arquivos": 0,
            "formatos": {},
            "bytes": 0,
            "volume_alvo": base.get("volume_alvo", 0),
            "divergencia_alvo": 0,
        }

    for a in arquivos:
        b_id = a.get("base_id")
        if b_id in por_base_map:
            por_base_map[b_id]["arquivos"] += 1
            por_base_map[b_id]["bytes"] += a.get("bytes", 0)
            fmt = a.get("tipo", "outros")
            por_base_map[b_id]["formatos"][fmt] = por_base_map[b_id]["formatos"].get(fmt, 0) + 1

    for b_id, info in por_base_map.items():
        info["divergencia_alvo"] = info["arquivos"] - info["volume_alvo"]

    return {
        "scenario_id": manifest.get("scenario_id", "cenario-3"),
        "version": version_name,
        "coletado_em": datetime.now(timezone.utc).isoformat(),
        "manifest_hash": f"sha256:{calculate_string_sha256(manifest_str)}",
        "totais": {
            "arquivos": len(arquivos),
            "bytes": totais_bytes,
            "falhas": len(falhas)
        },
        "por_base": list(por_base_map.values()),
        "arquivos": arquivos,
        "falhas": falhas
    }


def save_markdown_inventory(inventory_data: dict, out_md_path: Path):
    """Gera o arquivo CORPUS_INVENTORY.md legível para seres humanos."""
    tot = inventory_data["totais"]
    md = [
        f"# Corpus Inventory - Versão {inventory_data['version']}",
        f"- **Cenário:** `{inventory_data['scenario_id']}`",
        f"- **Data da Coleta:** {inventory_data['coletado_em']}",
        f"- **Manifest Hash:** `{inventory_data['manifest_hash']}`",
        f"- **Total de Arquivos:** {tot['arquivos']}",
        f"- **Tamanho Total:** {tot['bytes'] / (1024*1024):.2f} MB",
        f"- **Falhas Registradas:** {tot['falhas']}\n",
        "## Resumo por Base",
        "| Base ID | Natureza | Arquivos | Formatos | Tamanho (MB) | Alvo | Divergência |",
        "|---|---|---|---|---|---|---|"
    ]

    for base in inventory_data["por_base"]:
        f_str = ", ".join([f"{k}:{v}" for k, v in base["formatos"].items()]) or "N/A"
        mb = base["bytes"] / (1024 * 1024)
        md.append(f"| `{base['base_id']}` | {base['natureza']} | {base['arquivos']} | {f_str} | {mb:.2f} | {base['volume_alvo']} | {base['divergencia_alvo']} |")

    if inventory_data["falhas"]:
        md.append("\n## Falhas de Coleta")
        md.append("| Origem | Erro |")
        md.append("|---|---|")
        for f in inventory_data["falhas"]:
            md.append(f"| {f.get('origem')} | {f.get('erro')} |")

    out_md_path.write_text("\n".join(md), encoding="utf-8")


def run_fetch(manifest_path: Path, version_name: str = "v1") -> dict:
    """Executa a coleta de uma nova versão do corpus."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifesto não encontrado em: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_str = f.read()
        manifest = yaml.safe_load(manifest_str)

    # Garante que o manifesto é um dicionário e recupera a lista de bases
    if not isinstance(manifest, dict):
        raise ValueError("O arquivo corpus_manifest.yaml precisa estar formatado como um dicionário YAML válido.")

    version_dir = RAW_DIR / version_name
    version_dir.mkdir(parents=True, exist_ok=True)

    todos_arquivos = []
    todas_falhas = []

    print(f"[*] Iniciando coleta para a versão `{version_name}`...")
    
    bases_list = manifest.get("bases", [])
    if isinstance(bases_list, dict):
        bases_list = [bases_list]

    for base in bases_list:
        if not isinstance(base, dict):
            continue
        print(f" -> Coletando base: {base.get('base_id')}...")
        arqs, falhas = process_base(base, version_dir)
        todos_arquivos.extend(arqs)
        todas_falhas.extend(falhas)

    inventory_data = generate_inventory_data(manifest, version_name, todos_arquivos, todas_falhas, manifest_str)

    # Persiste os resultados de inventário
    INVENTORY_DIR.mkdir(parents=True, exist_ok=True)
    json_inv_path = INVENTORY_DIR / f"{version_name}.json"
    with open(json_inv_path, "w", encoding="utf-8") as f:
        json.dump(inventory_data, f, ensure_ascii=False, indent=2)

    md_inv_path = BASE_DIR / "CORPUS_INVENTORY.md"
    save_markdown_inventory(inventory_data, md_inv_path)

    print(f"[OK] Coleta concluída! Inventários salvos em:")
    print(f"    - {json_inv_path.relative_to(BASE_DIR)}")
    print(f"    - {md_inv_path.relative_to(BASE_DIR)}")

    return inventory_data


def run_update(manifest_path: Path):
    """Executa update comparando v(n) com a nova v(n+1) e gera o arquivo de DIFF."""
    INVENTORY_DIR.mkdir(parents=True, exist_ok=True)
    existing_versions = sorted(INVENTORY_DIR.glob("v*.json"))

    if not existing_versions:
        print("[!] Nenhuma versão anterior encontrada. Executando fetch como v1...")
        run_fetch(manifest_path, "v1")
        return

    latest_json = existing_versions[-1]
    latest_v_num = int(latest_json.stem.replace("v", ""))
    new_v_num = latest_v_num + 1
    new_v_name = f"v{new_v_num}"
    old_v_name = f"v{latest_v_num}"

    with open(latest_json, "r", encoding="utf-8") as f:
        old_data = json.load(f)

    new_data = run_fetch(manifest_path, new_v_name)

    # Cálculo do DIFF entre versões
    old_files_map = {a["path"].replace(f"raw/{old_v_name}/", ""): a["sha256"] for a in old_data["arquivos"]}
    new_files_map = {a["path"].replace(f"raw/{new_v_name}/", ""): a["sha256"] for a in new_data["arquivos"]}

    entraram = set(new_files_map.keys()) - set(old_files_map.keys())
    sairam = set(old_files_map.keys()) - set(new_files_map.keys())
    modificados = set()

    for k in set(old_files_map.keys()) & set(new_files_map.keys()):
        if old_files_map[k] != new_files_map[k]:
            modificados.add(k)

    diff_md = [
        f"# Diff de Atualização do Corpus: {old_v_name} -> {new_v_name}",
        f"- **Data da Atualização:** {datetime.now(timezone.utc).isoformat()}",
        f"- **Arquivos Adicionados ({len(entraram)}):**",
        "\n".join([f"  + `{f}`" for f in sorted(entraram)]) or "  (Nenhum)",
        f"\n- **Arquivos Removidos ({len(sairam)}):**",
        "\n".join([f"  - `{f}`" for f in sorted(sairam)]) or "  (Nenhum)",
        f"\n- **Arquivos Alterados/Hash Diferente ({len(modificados)}):**",
        "\n".join([f"  * `{f}`" for f in sorted(modificados)]) or "  (Nenhum)"
    ]

    diff_file = INVENTORY_DIR / f"DIFF_{old_v_name}_{new_v_name}.md"
    diff_file.write_text("\n".join(diff_md), encoding="utf-8")
    print(f"[OK] Diff de versão registrado em: {diff_file.relative_to(BASE_DIR)}")


def run_inventory_cmd(version_name: str):
    """Lê o JSON de uma versão específica e regera o CORPUS_INVENTORY.md."""
    json_path = INVENTORY_DIR / f"{version_name}.json"
    if not json_path.exists():
        print(f"[X] Inventário da versão `{version_name}` não encontrado em {json_path}")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        inv_data = json.load(f)

    md_inv_path = BASE_DIR / "CORPUS_INVENTORY.md"
    save_markdown_inventory(inv_data, md_inv_path)
    print(f"[OK] CORPUS_INVENTORY.md atualizado com os dados da versão `{version_name}`!")


def main():
    parser = argparse.ArgumentParser(description="Módulo de Coleta e Versionamento do Corpus (RAG)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcomando fetch
    fetch_parser = subparsers.add_parser("fetch", help="Executa a coleta inicial do corpus")
    fetch_parser.add_argument("--manifest", type=Path, default=BASE_DIR / "corpus_manifest.yaml", help="Caminho para o corpus_manifest.yaml")
    fetch_parser.add_argument("--version", type=str, default="v1", help="Nome da versão da coleta (Padrão: v1)")

    # Subcomando update
    update_parser = subparsers.add_parser("update", help="Coleta nova versão e gera o DIFF em relação à anterior")
    update_parser.add_argument("--manifest", type=Path, default=BASE_DIR / "corpus_manifest.yaml", help="Caminho para o corpus_manifest.yaml")

    # Subcomando inventory
    inventory_parser = subparsers.add_parser("inventory", help="Regera o CORPUS_INVENTORY.md a partir do JSON da versão")
    inventory_parser.add_argument("--version", type=str, default="v1", help="Versão do inventário (ex: v1, v2)")

    args = parser.parse_args()

    if args.command == "fetch":
        run_fetch(args.manifest, args.version)
    elif args.command == "update":
        run_update(args.manifest)
    elif args.command == "inventory":
        run_inventory_cmd(args.version)


if __name__ == "__main__":
    main()