# Verificador de Certificados SSL

Script Python que lê uma lista de domínios de um arquivo de texto e, usando o `openssl`, consulta cada um deles para obter as datas de **emissão** e **expiração** dos certificados SSL/TLS. O resultado é gravado em um arquivo CSV.

---

## 1. Requisitos

| Dependência | Versão mínima | Observação |
|-------------|---------------|------------|
| Python      | 3.7+          | Usa apenas a biblioteca padrão (não exige `pip install`). |
| OpenSSL     | 1.1.1+        | Binário `openssl` precisa estar no `PATH`. |
| Acesso de rede | —          | Saída TCP liberada para a porta 443 dos domínios alvo. |

---

## 2. Instalação das dependências

### 2.1 Linux (Debian / Ubuntu)
```bash
sudo apt update
sudo apt install -y python3 openssl
```

### 2.2 Linux (RHEL / CentOS / Rocky / Fedora)
```bash
sudo dnf install -y python3 openssl
```

### 2.3 macOS (Homebrew)
```bash
brew install python openssl
```

### 2.4 Windows
1. Instale o Python: <https://www.python.org/downloads/> (marque **Add Python to PATH** durante a instalação).
2. Instale o OpenSSL (uma das opções):
   - **Git for Windows** (já inclui `openssl`): <https://git-scm.com/download/win>
   - **Chocolatey**: `choco install openssl`
   - **Winget**: `winget install ShiningLight.OpenSSL`
3. Reabra o terminal (PowerShell ou CMD) para recarregar o `PATH`.

### 2.5 Verificar a instalação
```bash
python3 --version      # ex.: Python 3.11.6
openssl version        # ex.: OpenSSL 3.0.13 30 Jan 2024
```
No Windows use `python --version` se `python3` não existir.

---

## 3. Obter o projeto

O repositório está espelhado em duas plataformas. Use a que preferir — o conteúdo é o mesmo.

### 3.1 Clonando via GitHub (público)

Repositório: <https://github.com/rafaelaquinoluizalabs/ssl-teste>

```bash
# HTTPS (não exige chave SSH configurada)
git clone https://github.com/rafaelaquinoluizalabs/ssl-teste.git
cd ssl-teste
```

```bash
# SSH (requer chave SSH cadastrada em https://github.com/settings/keys)
git clone git@github.com:rafaelaquinoluizalabs/ssl-teste.git
cd ssl-teste
```

### 3.2 Clonando via GitLab Luizalabs (público, requer VPN/rede corporativa)

Repositório: <https://gitlab.luizalabs.com/rafael.aquino/ssl-teste>

```bash
# HTTPS
git clone https://gitlab.luizalabs.com/rafael.aquino/ssl-teste.git
cd ssl-teste
```

```bash
# SSH (requer chave SSH cadastrada em https://gitlab.luizalabs.com/-/user_settings/ssh_keys)
git clone git@gitlab.luizalabs.com:rafael.aquino/ssl-teste.git
cd ssl-teste
```

### 3.3 Download direto (sem git)

Se não quiser usar `git`, basta baixar o `.zip`:

- GitHub: <https://github.com/rafaelaquinoluizalabs/ssl-teste/archive/refs/heads/main.zip>
- GitLab: <https://gitlab.luizalabs.com/rafael.aquino/ssl-teste/-/archive/main/ssl-teste-main.zip>

Descompacte e entre na pasta:
```bash
unzip ssl-teste-main.zip
cd ssl-teste-main
```

### 3.4 Atualizando uma cópia já clonada

```bash
cd ssl-teste
git pull
```

### 3.5 (Opcional) Manter os dois remotos na mesma cópia local

Útil para quem mantém o projeto em ambos os hosts ao mesmo tempo:
```bash
git clone https://github.com/rafaelaquinoluizalabs/ssl-teste.git
cd ssl-teste

# Adiciona o GitLab como remoto separado
git remote add gitlab git@gitlab.luizalabs.com:rafael.aquino/ssl-teste.git

# Faz com que 'git push' envie para os dois ao mesmo tempo
git remote set-url --add --push origin https://github.com/rafaelaquinoluizalabs/ssl-teste.git
git remote set-url --add --push origin git@gitlab.luizalabs.com:rafael.aquino/ssl-teste.git

git remote -v   # confere a configuração
```
A partir daí, `git push` envia o mesmo commit para o GitHub **e** para o GitLab.

---

## 4. Estrutura de arquivos esperada

```
ssl-teste/
├── lista-dominio.txt          # entrada: 1 domínio por linha
└── verificar_certificados.py  # o script
```

### Formato do `lista-dominio.txt`
- Um domínio por linha (sem `https://`, sem caminho, sem porta).
- Linhas em branco e linhas que começam com `#` são ignoradas.
- Duplicatas são removidas automaticamente.

Exemplo:
```
www.magazineluiza.com.br
api.magazineluiza.com.br
# linha de comentário ignorada
zoidberg.tst-mkt.magazineluiza.com.br
```

---

## 5. Execução

Abra um terminal na pasta do projeto:
```bash
cd ~/ssl-teste
```

### 5.1 Uso padrão
```bash
python3 verificar_certificados.py
```
Isto irá:
- ler `lista-dominio.txt`,
- consultar a porta 443,
- usar 10 conexões paralelas,
- gravar o resultado em `certificados.csv`.

### 5.2 Opções disponíveis

| Flag                    | Padrão                | Descrição |
|-------------------------|------------------------|-----------|
| `ARQUIVO` (posicional)  | —                      | Arquivo de entrada (alternativa rápida a `-i`). Sobrescreve `--input` se ambos forem informados. |
| `-i`, `--input ARQUIVO.txt` | `lista-dominio.txt` | Arquivo de entrada com os domínios (um por linha). |
| `-o`, `--output ARQUIVO.csv` | `certificados.csv` | Arquivo CSV de saída (criado na 1ª execução, atualizado nas seguintes). |
| `-p`, `--port`          | `443`                 | Porta TCP do serviço TLS. |
| `-t`, `--timeout`       | `10`                  | Timeout em segundos por domínio. |
| `-w`, `--workers`       | `20`                  | Quantidade de conexões paralelas. |
| `--keep-removed`        | desligado             | Mantém no CSV domínios que saíram da lista (padrão: remove). |
| `-h`, `--help`          | —                     | Mostra a ajuda. |

### 5.3 Exemplos
```bash
# Padrão (lê lista-dominio.txt, grava certificados.csv)
python3 verificar_certificados.py

# Definindo entrada e saída explicitamente
python3 verificar_certificados.py -i lista-dominio.txt -o certificados.csv

# Outro ambiente
python3 verificar_certificados.py --input dominios-prod.txt --output relatorio-prod.csv

# Caminhos absolutos
python3 verificar_certificados.py -i /etc/ssl-monitor/dominios.txt -o /var/log/ssl/relatorio.csv

# Mais paralelismo e timeout maior (lista grande / rede lenta)
python3 verificar_certificados.py -w 30 -t 20

# Verificar uma porta diferente
python3 verificar_certificados.py -p 8443
```

---

## 6. Saída

### 6.1 Terminal (stderr)
Durante a execução, o progresso é exibido linha a linha, indicando o que mudou em relação ao CSV anterior:
```
Verificando 1245 domínios (porta 443)... 1240 registro(s) anteriores carregados.
[1/1245] SEM_MUDANCA api.exemplo.com.br
[2/1245] ATUALIZADO  foo.exemplo.com.br
[3/1245] NOVO        bar.exemplo.com.br
[4/1245] IGNORADO    quebrado.exemplo.com.br (timeout na conexão) — mantendo valor anterior
...

CSV atualizado em: certificados.csv

Domínios IGNORADOS (CSV não atualizado para eles):
  - quebrado.exemplo.com.br  [timeout na conexão]
  - dns-ruim.exemplo.com.br  [falha na conexão]

Domínios REMOVIDOS (saíram da lista de entrada):
  - antigo1.exemplo.com.br
  - antigo2.exemplo.com.br

===== Resumo =====
  Total processados : 1245
  Novos             : 5
  Atualizados       : 12
  Inalterados       : 1226
  Ignorados         : 2
  Removidos         : 2
  (dos ignorados, 2 tiveram valor anterior mantido no CSV)
```

Marcadores:
- **NOVO** — domínio não existia no CSV.
- **ATUALIZADO** — datas mudaram em relação ao CSV anterior.
- **SEM_MUDANCA** — mesmas datas do CSV anterior.
- **IGNORADO** — falhou a conexão ou não foi possível obter as datas. O CSV **não é atualizado** para este domínio:
  - se o domínio já existia no CSV, o valor anterior é **preservado**;
  - se era um domínio novo, ele simplesmente não é gravado nesta execução.
- **Removidos** — estavam no CSV mas saíram de `lista-dominio.txt` (serão apagados, salvo `--keep-removed`).

### 6.2 Arquivo CSV
Quatro colunas, ordenadas por domínio:

| dominio | certificado | data_emissao | data_expiracao |
|---------|-------------|--------------|----------------|
| api.exemplo.com.br | api.exemplo.com.br        | 2025-03-12 00:00:00 UTC | 2026-03-12 23:59:59 UTC |
| www.exemplo.com.br | *.exemplo.com.br          | 2025-01-05 00:00:00 UTC | 2026-01-05 23:59:59 UTC |

- **certificado** — Common Name (CN) presente no Subject do certificado servido pelo domínio (pode ser um wildcard como `*.exemplo.com.br` ou um nome diferente do próprio domínio).
- Datas em **UTC**, formato `YYYY-MM-DD HH:MM:SS UTC`.
- Em caso de erro, o domínio é **ignorado** (ver seção 6.1) e o CSV **não** é alterado para ele.
- CSVs no formato antigo (3 colunas) são detectados e migrados automaticamente — a coluna `certificado` fica vazia até o próximo sucesso na coleta.

---

## 7. Solução de problemas

| Sintoma | Causa provável | O que fazer |
|---------|----------------|-------------|
| `Erro: 'openssl' não encontrado no PATH.` | OpenSSL não instalado ou fora do PATH. | Instalar (seção 2) e reabrir o terminal. |
| `Arquivo não encontrado: lista-dominio.txt` | Executando em diretório errado. | `cd` para a pasta do projeto ou passar caminho absoluto. |
| Muitos `timeout na conexão` | Rede lenta / firewall / DNS lento. | Aumentar `-t 20` e reduzir `-w 5`. |
| `falha na conexão` ou `Connection refused` | Domínio não responde na porta indicada. | Verificar se o serviço HTTPS está ativo na porta. |
| Processo demora muito | Lista muito grande. | Aumentar `-w` (ex.: `-w 30`); cuidado com limites do SO. |
| Erro de permissão ao gravar CSV | Sem permissão na pasta de saída. | Usar `-o` apontando para diretório com permissão de escrita. |

### 7.1 Validar um domínio manualmente
Caso queira confirmar uma falha de forma isolada:
```bash
echo | openssl s_client -connect exemplo.com.br:443 -servername exemplo.com.br 2>/dev/null \
  | openssl x509 -noout -startdate -enddate
```

---

## 8. Como interromper

Pressione `Ctrl + C` no terminal. As conexões em andamento serão canceladas; o CSV só é gravado ao final, portanto interromper antes do término significa **nenhum** arquivo de saída novo (o CSV anterior permanece intacto, pois a gravação é atômica).

---

## 9. Re-execução / atualização incremental

A cada execução o script:

1. Carrega o `certificados.csv` anterior (se existir).
2. Consulta todos os domínios da lista atual.
3. Compara cada resultado com o anterior e classifica como **NOVO**, **ATUALIZADO** ou **SEM_MUDANCA**.
4. Remove do CSV os domínios que saíram de `lista-dominio.txt` (use `--keep-removed` para preservá-los).
5. Grava o CSV de forma **atômica** (`.tmp` + rename), evitando arquivo corrompido em caso de falha.

Recomendado executar periodicamente (por exemplo, via `cron`) para acompanhar renovações:
```cron
# Todo dia às 06:00
0 6 * * * cd /home/rafaell/ssl-teste && /usr/bin/python3 verificar_certificados.py >> verificar.log 2>&1
```

---

## 10. Observações de segurança

- O script realiza **apenas conexões TLS de leitura** (não envia dados HTTP, não autentica, não modifica nada).
- Domínios da lista são tratados como entrada confiável; não execute o script com uma lista de origem desconhecida sem revisar.
- O CSV pode conter mensagens de erro do OpenSSL — trate como informação interna.
