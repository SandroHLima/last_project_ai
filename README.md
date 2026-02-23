# School Grades Agent API

Agente de avaliações escolares acessível via API, com controlo de acesso baseado em roles (Professor/Aluno) e guardrails de segurança.

## Objetivo

Construir um agente de avaliações escolares acessível via API, onde:
- **Professor**: insere e edita notas; consulta notas por aluno/disciplinas/módulos/turma; gera relatórios e médias.
- **Aluno**: consulta apenas as suas notas e médias.
- **Regra crítica**: aluno não pode ver dados de outros alunos (guardrail + enforcement no nível da DB/tool).

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                         API (FastAPI)                        │
├─────────────────────────────────────────────────────────────┤
│                   LangGraph Agent Workflow                   │
│  ┌─────────┐  ┌───────────┐  ┌─────────┐  ┌─────────────┐  │
│  │ Load    │→ │ Guardrail │→ │ Parse   │→ │ Check       │  │
│  │ User    │  │ Pre       │  │ Intent  │  │ Fields      │  │
│  │ Context │  │           │  │         │  │             │  │
│  └─────────┘  └───────────┘  └─────────┘  └─────┬───────┘  │
│                                                  │          │
│  ┌─────────┐  ┌───────────┐  ┌─────────────────┐│          │
│  │ Final   │← │ Guardrail │← │ Execute Tools   │←          │
│  │ Response│  │ Post      │  │                 │           │
│  └─────────┘  └───────────┘  └─────────────────┘           │
├─────────────────────────────────────────────────────────────┤
│                    Tools (with Authorization)                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Identity │  │ Grades   │  │ Grades   │  │ Reporting│    │
│  │ Tools    │  │ Write    │  │ Read     │  │ Tools    │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
├─────────────────────────────────────────────────────────────┤
│                   Database (MySQL + SQLAlchemy)              │
└─────────────────────────────────────────────────────────────┘
```

## Modelo de Dados

| Tabela | Campos |
|--------|--------|
| **users** | id, name, role (ENUM: 'student', 'teacher') |
| **disciplinas** | id, name |
| **turmas** | id, name |
| **alunos_turmas** | user_id, turma_id |
| **avaliacoes** | id, user_id, disciplina_id, turma_id, modulo, descricao, valor, date, updated_by, updated_at |

## Regras de Autorização

1. **Nunca confiar no cliente para role** — Sempre: `role = get_user_role(user_id)` vindo da DB.
2. **Aluno**: Só pode chamar tools que façam `WHERE student_id = user_id`. Pedidos como "notas do João" são bloqueados.
3. **Professor**: Pode inserir/editar notas e consultar qualquer aluno.
4. **Sem DELETE**: Não existe funcionalidade de apagar notas. Insert e update apenas por professor.

### Defesa em Duas Camadas

1. **Guardrail**: Deteta intenção indevida e bloqueia antes da execução.
2. **Tool-layer enforcement**: Mesmo que o LLM tente, a tool recusa (ex.: `get_student_grades` recusa se `role=student` e `target_student_id != requester_user.id`).

## Intents Suportados

| Intent | Descrição | Roles |
|--------|-----------|-------|
| `add_grade` | Adicionar nova nota | Professor |
| `update_grade` | Atualizar nota existente | Professor |
| `delete_grade` | Eliminar nota (sempre recusado) | — |
| `query_grades` | Consultar notas | Professor, Aluno (só próprias) |
| `summary` | Ver médias e resumo | Professor, Aluno (só próprias) |
| `class_report` | Relatório de turma | Professor |
| `fallback` | Mensagem não compreendida | Todos |

## Instalação

### Requisitos
- Python 3.11 ou 3.12
- MySQL 8.0+
- Ollama com modelo `qwen3:8b` (para o parser LLM)

### Passos

```bash
# 1. Criar ambiente virtual
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente
copy .env.example .env
# Editar .env com as credenciais da base de dados

# 4. Iniciar o servidor (cria tabelas e dados de teste automaticamente)
python main.py
```

O servidor arranca em `http://localhost:8000`. A base de dados é criada e populada automaticamente no primeiro arranque.

## API Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/agent/chat` | Enviar mensagem ao agente (linguagem natural) |
| `GET` | `/users/` | Listar utilizadores |
| `POST` | `/users/` | Criar utilizador |
| `GET` | `/users/{id}` | Obter utilizador |
| `GET` | `/users/{id}/details` | Detalhes com turmas |
| `POST` | `/tools/grades/add` | Adicionar nota (professor) |
| `POST` | `/tools/grades/update` | Atualizar nota (professor) |
| `POST` | `/tools/grades/query` | Consultar notas |
| `GET` | `/tools/grades/summary/{id}` | Resumo de notas |
| `POST` | `/tools/reports/class` | Relatório de turma (professor) |
| `DELETE` | `/tools/grades/{id}` | **Sempre 405** (não permitido) |

Documentação interativa: `http://localhost:8000/docs`

## Testes

```bash
# Testes unitários
pytest tests/ -v

# Demonstração dos guardrails
python tests/demo_guardrails.py
```

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

- Parser: o parser LLM foi endurecido — ele remove blocos `<think>` e tem um fallback rule-based mais robusto. Para reduzir latência, mensagens curtas (ex.: "minhas notas") agora usam o parser rule-based sem chamar o LLM.

- Bloqueios: alunos são automaticamente bloqueados para operações de escrita (adicionar/editar notas) pelo guardrail pré-execução.

- UI de testes: adicionei `static/prompts.html` com prompts prontos (inclui exemplos bloqueados) e um link no cabeçalho do SPA.

- Mostrar tudo / truncamento: existe um toggle `Mostrar todas` no cabeçalho que envia `show_all` ao endpoint `/agent/chat`. As configurações padrão podem ser ajustadas em `config/settings.py` (`grades_truncate_default`, `grades_truncate_limit`).

Testes rápidos (após arrancar o servidor):

```bash
# List users
curl http://localhost:8000/users/

# Agent: add grade (teacher id 21 in seeded DB)
curl -X POST http://localhost:8000/agent/chat -H 'Content-Type: application/json' \
    -d '{"user_id":21,"message":"adicionar nota 16 ao aluno Ana Costa em matematica turma 10A modulo 1 trabalho final"}'

# Agent: list own grades (student id 23)
curl -X POST http://localhost:8000/agent/chat -H 'Content-Type: application/json' \
    -d '{"user_id":23,"message":"minhas notas"}'
```

## Estrutura do Projeto

```
├── main.py                  # Entrypoint FastAPI
├── requirements.txt         # Dependências
├── .env                     # Configuração (não versionado)
├── agent/                   # LangGraph agent workflow
│   ├── state.py             # AgentState, Intent enum
│   ├── parser.py            # Parser LLM (Ollama/Qwen3)
│   ├── nodes.py             # Nós do workflow
│   └── workflow.py          # Grafo compilado
├── api/                     # Camada HTTP
│   ├── routes.py            # Endpoints FastAPI
│   └── schemas.py           # Schemas Pydantic
├── config/
│   └── settings.py          # Configuração centralizada
├── database/
│   ├── models.py            # Modelos SQLAlchemy
│   ├── connection.py        # Engine & sessões
│   ├── schema.sql           # Schema SQL de referência
│   └── seed.py              # Dados de teste
├── guardrails/
│   └── guardrails.py        # Guardrails pré/pós execução
├── tools/                   # Ferramentas com autorização
│   ├── authorization.py     # Serviço de autorização
│   ├── exceptions.py        # Exceções customizadas
│   ├── identity.py          # Gestão de utilizadores
│   ├── grades.py            # Leitura e escrita de notas
│   └── reporting.py         # Relatórios
├── static/
│   └── index.html           # Interface web
└── tests/
    ├── test_authorization.py # Testes unitários
    ├── test_bug_fixes.py     # Testes de regressão
    └── demo_guardrails.py    # Script de demonstração
```
