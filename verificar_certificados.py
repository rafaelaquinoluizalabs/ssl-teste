#!/usr/bin/env python3
"""Verifica datas de emissão e expiração dos certificados SSL dos domínios listados.

Em execuções subsequentes, compara o resultado atual com o CSV existente
e atualiza apenas as linhas que mudaram (adicionando novos domínios,
atualizando alterações e removendo os que saíram da lista)."""

import argparse
import concurrent.futures
import csv
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DATE_FMT = "%Y-%m-%d %H:%M:%S UTC"
CSV_HEADER = ["dominio", "certificado", "data_emissao", "data_expiracao"]


def _extract_cn(subject: str) -> str:
    """Extrai o Common Name (CN) de uma linha 'subject=...'"""
    if "=" in subject:
        subject = subject.split("=", 1)[1].strip()
    # Pode vir como 'CN = exemplo.com' ou 'CN=exemplo.com', separado por ',' ou '/'.
    partes = []
    for sep in (",", "/"):
        if sep in subject:
            partes = [p.strip() for p in subject.split(sep)]
            break
    if not partes:
        partes = [subject.strip()]
    for p in partes:
        if p.upper().startswith("CN"):
            return p.split("=", 1)[1].strip() if "=" in p else p
    return subject.strip()


def get_cert_dates(domain: str, port: int = 443, timeout: int = 10):
    """Retorna (domain, cn, emissao, expiracao, erro)."""
    domain = domain.strip()
    if not domain or domain.startswith("#"):
        return None

    host_port = f"{domain}:{port}"
    try:
        proc = subprocess.run(
            [
                "openssl", "s_client",
                "-connect", host_port,
                "-servername", domain,
                "-showcerts",
            ],
            input=b"",
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return (domain, "", None, None, "timeout na conexão")
    except FileNotFoundError:
        sys.exit("Erro: 'openssl' não encontrado no PATH.")

    if b"BEGIN CERTIFICATE" not in proc.stdout:
        err = proc.stderr.decode(errors="ignore").strip().splitlines()
        msg = err[-1] if err else "falha na conexão"
        return (domain, "", None, None, msg)

    try:
        info = subprocess.run(
            ["openssl", "x509", "-noout", "-subject", "-startdate", "-enddate"],
            input=proc.stdout,
            capture_output=True,
            timeout=timeout,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        return (domain, "", None, None, f"x509: {e.stderr.decode(errors='ignore').strip()}")
    except subprocess.TimeoutExpired:
        return (domain, "", None, None, "timeout no parser x509")

    cn = ""
    emissao = expiracao = None
    for linha in info.stdout.decode(errors="ignore").splitlines():
        if linha.startswith("subject"):
            cn = _extract_cn(linha)
            continue
        if "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        try:
            dt = datetime.strptime(valor.strip(), "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if chave == "notBefore":
            emissao = dt
        elif chave == "notAfter":
            expiracao = dt

    if not emissao or not expiracao:
        return (domain, cn, emissao, expiracao, "datas não encontradas")
    return (domain, cn, emissao, expiracao, "")


def format_cell(dt, erro):
    if dt:
        return dt.strftime(DATE_FMT)
    if erro:
        return f"ERRO: {erro}"
    return ""


def load_existing_csv(path: Path):
    """Carrega CSV anterior e retorna dict {dominio: (certificado, data_emissao, data_expiracao)}.

    Aceita também o formato antigo (sem a coluna 'certificado') para não quebrar
    quando o usuário já possui um CSV gerado por versões anteriores do script."""
    dados = {}
    if not path.is_file():
        return dados
    legado = ["dominio", "data_emissao", "data_expiracao"]
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            cabecalho = next(reader, None)
            if cabecalho == CSV_HEADER:
                for linha in reader:
                    if len(linha) < 4 or not linha[0]:
                        continue
                    dados[linha[0]] = (linha[1], linha[2], linha[3])
            elif cabecalho == legado:
                print(
                    f"Aviso: {path} está no formato antigo (sem coluna 'certificado'); "
                    "valores serão migrados nesta execução.",
                    file=sys.stderr,
                )
                for linha in reader:
                    if len(linha) < 3 or not linha[0]:
                        continue
                    dados[linha[0]] = ("", linha[1], linha[2])
            else:
                print(
                    f"Aviso: cabeçalho de {path} inesperado, ignorando dados anteriores.",
                    file=sys.stderr,
                )
                return {}
    except OSError as e:
        print(f"Aviso: falha ao ler CSV existente: {e}", file=sys.stderr)
        return {}
    return dados


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  %(prog)s\n"
            "  %(prog)s -i lista-dominio.txt -o certificados.csv\n"
            "  %(prog)s --input dominios-prod.txt --output relatorio-prod.csv\n"
        ),
    )
    parser.add_argument(
        "arquivo_posicional",
        nargs="?",
        default=None,
        metavar="ARQUIVO",
        help="Arquivo de entrada (alternativa posicional a -i/--input).",
    )
    parser.add_argument(
        "-i", "--input",
        dest="input",
        default="lista-dominio.txt",
        metavar="ARQUIVO.txt",
        help="Arquivo de entrada (.txt) com um domínio por linha.",
    )
    parser.add_argument(
        "-o", "--output",
        dest="output",
        default="certificados.csv",
        metavar="ARQUIVO.csv",
        help="Arquivo CSV de saída (será criado ou atualizado).",
    )
    parser.add_argument("-p", "--port", type=int, default=443, help="Porta TCP do serviço TLS.")
    parser.add_argument("-t", "--timeout", type=int, default=10, help="Timeout em segundos por domínio.")
    parser.add_argument("-w", "--workers", type=int, default=20, help="Conexões paralelas.")
    parser.add_argument(
        "--keep-removed",
        action="store_true",
        help="Mantém no CSV os domínios que não estão mais na lista (padrão: remove).",
    )
    args = parser.parse_args()

    # Posicional, se fornecido, sobrescreve -i/--input.
    arquivo_entrada = args.arquivo_posicional or args.input
    caminho = Path(arquivo_entrada)
    if not caminho.is_file():
        sys.exit(f"Arquivo de entrada não encontrado: {caminho}")

    output = Path(args.output)
    if output.parent and not output.parent.exists():
        sys.exit(f"Diretório de saída não existe: {output.parent}")

    print(f"Entrada : {caminho}", file=sys.stderr)
    print(f"Saída   : {output}", file=sys.stderr)

    existentes = load_existing_csv(output)

    dominios = []
    vistos = set()
    for linha in caminho.read_text(encoding="utf-8", errors="ignore").splitlines():
        d = linha.strip()
        if not d or d.startswith("#") or d in vistos:
            continue
        vistos.add(d)
        dominios.append(d)

    total = len(dominios)
    print(
        f"Verificando {total} domínios (porta {args.port})... "
        f"{len(existentes)} registro(s) anteriores carregados.",
        file=sys.stderr,
    )

    novos_dados = {}
    ignorados = []  # (dominio, motivo)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futuros = {
            pool.submit(get_cert_dates, d, args.port, args.timeout): d
            for d in dominios
        }
        for i, fut in enumerate(concurrent.futures.as_completed(futuros), 1):
            res = fut.result()
            if res is None:
                continue
            dom, cn, emissao, expiracao, erro = res

            # Erro de conexão ou datas indisponíveis → não atualiza o CSV.
            if erro or not emissao or not expiracao:
                motivo = erro or "datas não encontradas"
                ignorados.append((dom, motivo))
                if dom in existentes:
                    # Preserva o valor anterior.
                    novos_dados[dom] = existentes[dom]
                    print(
                        f"[{i}/{total}] IGNORADO    {dom} ({motivo}) — mantendo valor anterior",
                        file=sys.stderr,
                    )
                else:
                    print(
                        f"[{i}/{total}] IGNORADO    {dom} ({motivo}) — sem registro anterior",
                        file=sys.stderr,
                    )
                continue

            cel_emissao = format_cell(emissao, "")
            cel_expiracao = format_cell(expiracao, "")
            novos_dados[dom] = (cn, cel_emissao, cel_expiracao)

            anterior = existentes.get(dom)
            if anterior is None:
                marcador = "NOVO"
            elif anterior != (cn, cel_emissao, cel_expiracao):
                marcador = "ATUALIZADO"
            else:
                marcador = "SEM_MUDANCA"
            print(f"[{i}/{total}] {marcador:<11} {dom}", file=sys.stderr)

    # Mantém (ou remove) domínios que estavam no CSV mas saíram da lista.
    removidos = [d for d in existentes if d not in novos_dados]
    if args.keep_removed:
        for dom in removidos:
            novos_dados[dom] = existentes[dom]

    # Estatísticas
    novos = sum(
        1 for d in novos_dados
        if d not in existentes and d not in {x[0] for x in ignorados}
    )
    atualizados = sum(
        1 for d, v in novos_dados.items()
        if d in existentes and existentes[d] != v and d not in {x[0] for x in ignorados}
    )
    inalterados = sum(
        1 for d, v in novos_dados.items()
        if d in existentes and existentes[d] == v and d not in {x[0] for x in ignorados}
    )

    # Escrita atômica: grava em arquivo temporário e renomeia.
    tmp = output.with_suffix(output.suffix + ".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        for dom in sorted(novos_dados):
            cn, emissao_cel, expiracao_cel = novos_dados[dom]
            writer.writerow([dom, cn, emissao_cel, expiracao_cel])
    tmp.replace(output)

    print(f"\nCSV atualizado em: {output}", file=sys.stderr)

    if ignorados:
        print("\nDomínios IGNORADOS (CSV não atualizado para eles):", file=sys.stderr)
        for dom, motivo in ignorados:
            print(f"  - {dom}  [{motivo}]", file=sys.stderr)

    if removidos and not args.keep_removed:
        print("\nDomínios REMOVIDOS (saíram da lista de entrada):", file=sys.stderr)
        for dom in removidos:
            print(f"  - {dom}", file=sys.stderr)

    print("\n===== Resumo =====", file=sys.stderr)
    print(f"  Total processados : {total}", file=sys.stderr)
    print(f"  Novos             : {novos}", file=sys.stderr)
    print(f"  Atualizados       : {atualizados}", file=sys.stderr)
    print(f"  Inalterados       : {inalterados}", file=sys.stderr)
    print(f"  Ignorados         : {len(ignorados)}", file=sys.stderr)
    print(
        f"  Removidos         : {len(removidos)}"
        f"{' (mantidos no CSV)' if args.keep_removed else ''}",
        file=sys.stderr,
    )
    mantidos_apos_erro = sum(
        1 for dom, _ in ignorados if dom in existentes
    )
    if mantidos_apos_erro:
        print(
            f"  (dos ignorados, {mantidos_apos_erro} tiveram valor anterior mantido no CSV)",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
