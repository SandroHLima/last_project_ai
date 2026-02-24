# School Grades Agent API

Agente de avaliações escolares acessível via API, com controlo de acesso baseado em roles (Professor/Aluno) e guardrails de segurança.

## Objetivo

Construir um agente de avaliações escolares acessível via API, onde:
- **Professor**: insere e edita notas; consulta notas por aluno/disciplinas/módulos/turma; gera relatórios e médias.
- **Aluno**: consulta apenas as suas notas e médias.
- **Regra crítica**: aluno não pode ver dados de outros alunos (guardrail + enforcement no nível da DB/tool).

## Regras de Autorização

1. **Nunca confiar no cliente para role** — Sempre: `role = get_user_role(user_id)` vindo da DB.
2. **Aluno**: Só pode chamar tools que façam `WHERE student_id = user_id`. Pedidos como "notas do João" são bloqueados.
3. **Professor**: Pode inserir/editar notas e consultar qualquer aluno.
4. **Sem DELETE**: Não existe funcionalidade de apagar notas. Insert e update apenas por professor.

### Requisitos
- Python 3.11 ou 3.12
- MySQL 8.0+
- Ollama com modelo `qwen3:8b` (para o parser LLM)

### Passos

```bash
# 1. Criar ambiente virtual
# IMPORTANT: create the venv using a specific Python 3.11 interpreter
# to avoid accidentally using an incompatible system Python (e.g. 3.13).
# On Windows (recommended):
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1     # PowerShell
# or, for cmd.exe:
.venv\Scripts\activate.bat

# On Linux / macOS (if python3.11 is available):
python3.11 -m venv .venv
source .venv/bin/activate

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente
copy .env.example .env
# Editar .env com as credenciais da base de dados

# 4. Iniciar o servidor (cria tabelas e dados de teste automaticamente)
python main.py
```

O servidor arranca em `http://localhost:8000`. A base de dados é criada e populada automaticamente no primeiro arranque.

### Cenários Testados

1. Aluno pede "Mostra as notas do João" → **BLOQUEADO**
2. Professor adiciona nota → **OK**
3. Aluno pede as suas notas por disciplina/módulo → **OK**
4. Professor pede relatório de turma → **OK**
5. Tentativa de "apagar nota" → **RECUSADO**

## Alterações recentes & Testes rápidos

Estas são as mudanças feitas recentemente e como testá-las rapidamente:

- Modelo LLM: o repositório requer o modelo `qwen3:8b` no Ollama. Se não estiver instalado, execute:

```bash
ollama pull qwen3:8b
```