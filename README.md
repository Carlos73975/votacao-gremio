# Sistema de Votação — Grêmio Estudantil

Projeto editável em Python + Flask + SQLite. A interface funciona em celulares e computadores pelo navegador.

## O que está incluído
- Quatro chapas já cadastradas:
  - Jovens do Futuro
  - Jovens para um Futuro
  - As que vão se esforçar
  - Geração Revolucionária
- Códigos individuais de votação, de uso único.
- Cédulas sem o código do eleitor: o banco não grava qual código corresponde a qual escolha.
- Painel administrativo com abertura/encerramento e apuração.
- Exportação dos resultados em CSV.
- Layout adaptável a celular e computador.

## Requisitos
Python 3.10 ou mais recente.

## Instalação no Windows
1. Instale Python em https://www.python.org/downloads/ (marque "Add Python to PATH").
2. Extraia o ZIP.
3. Abra o Prompt de Comando na pasta do projeto.
4. Execute:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set ADMIN_PASSWORD=crie-uma-senha-forte
set SECRET_KEY=troque-por-uma-chave-longa-e-aleatoria
python app.py
```

Abra `http://127.0.0.1:5000`.

## Instalação no macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ADMIN_PASSWORD='crie-uma-senha-forte'
export SECRET_KEY='troque-por-uma-chave-longa-e-aleatoria'
python app.py
```
Abra `http://127.0.0.1:5000`.

## Preparar os votos
1. Entre em `http://127.0.0.1:5000/admin/login`.
2. Use a senha definida em `ADMIN_PASSWORD`.
3. Gere a quantidade de códigos necessária.
4. Imprima ou distribua cada código individualmente, sem associá-lo ao nome do aluno.
5. Os alunos abrem o endereço da votação no celular, digitam seu código e escolhem uma chapa.
6. No painel, encerre a votação e consulte ou baixe os resultados.

**Atenção:** os códigos são exibidos somente uma vez, quando são gerados. Guarde/imprima a lista nesse momento. Por segurança, o sistema salva apenas o hash dos códigos e não consegue recuperá-los depois.

## Como os alunos acessam pelo próprio celular?
- Para teste na mesma rede Wi-Fi: descubra o IP local do computador que está executando o sistema e acesse `http://IP-DO-COMPUTADOR:5000` nos celulares conectados à mesma rede. Ex.: `http://192.168.0.20:5000`.
- Para votação de qualquer lugar pela internet: publique o projeto em um servidor com HTTPS. Não exponha o computador pessoal diretamente à internet. Configure `ADMIN_PASSWORD`, `SECRET_KEY` e armazenamento persistente antes de usar.

## Limitações e segurança
Este é um projeto inicial editável, não um sistema eleitoral certificado. Faça uma eleição simulada antes da votação real. Use HTTPS em hospedagem pública, senha administrativa forte, backup protegido e um responsável técnico. A votação secreta é implementada sem guardar o código junto à cédula, mas o servidor e seus administradores ainda exigem confiança. O sistema não verifica identidade civil ou matrícula: a distribuição dos códigos é responsabilidade da escola.


## Publicar na internet (exemplo: Render)
1. Crie um repositório privado no GitHub e envie os arquivos desta pasta.
2. No Render, crie um **Web Service** e conecte o repositório.
3. Configure:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
4. Em Environment, defina `ADMIN_PASSWORD` e `SECRET_KEY` com valores fortes e exclusivos.
5. Configure armazenamento persistente para o banco. Se usar disco persistente montado em `/var/data`, defina `DB_PATH=/var/data/votacao.db`.
6. Faça o deploy e teste com códigos fictícios antes de abrir a eleição.

**Muito importante:** o sistema usa SQLite. No Render, o armazenamento padrão é temporário e pode ser apagado em reinicializações ou novos deploys. Para preservar votos, use armazenamento persistente e configure `DB_PATH` para dentro do disco, ou migre para um banco de dados gerenciado. Não faça uma eleição real sem confirmar a persistência, fazer backup e testar a recuperação.
