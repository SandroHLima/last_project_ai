# School Grades Agent API

Agente de avaliações escolares acessível via API, com controlo de acesso baseado em roles (Professor/Aluno) e guardrails de segurança.

## Índice

- [Objetivo](#objetivo)
- [Arquitetura](#arquitetura)
- [Modelo de Dados](#modelo-de-dados)
- [Regras de Autorização](#regras-de-autorização)
- [API Endpoints](#api-endpoints)
- [Instalação](#instalação)
- [Utilização](#utilização)
- [Testes e Demonstração](#testes-e-demonstração)

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

### Tabelas

| Tabela | Campos |
|--------|--------|
| **users** | id, name, role (ENUM: 'student', 'teacher') |
| **disciplinas** | id, name |
| **turmas** | id, name |
| **alunos_turmas** | user_id, turma_id |
| **avaliacoes** | id, user_id, disciplina_id, turma_id, modulo, descricao, valor, date, updated_by, updated_at |

## Regras de Autorização

### Princípios

1. **Nunca confiar no cliente para role** - Sempre: `role = get_user_role(user_id)` vindo da DB.
2. **Aluno**:
   - Só pode chamar tools que façam `WHERE student_id = user_id`
   - Se o texto pedir "notas do João", deve ser bloqueado.
3. **Professor**:
   - Pode inserir/editar notas
   - Pode consultar por qualquer aluno
4. **Sem DELETE**:
   - Não existe tool de apagar
   - Insert e update apenas por professor

### Defesa em Duas Camadas

1. **Guardrail**: Deteta intenção indevida e bloqueia.
2. **Tool-layer enforcement**: Mesmo que o LLM tente, a tool recusa.
   - Ex.: `get_student_grades(requester_user, target_student_id)` recusa se `role=student` e `target_student_id != requester_user.id`.

## API Endpoints

### Agent (Linguagem Natural)
- `POST /agent/chat` - Enviar mensagem ao agente

### Users
- `GET /users/{user_id}` - Obter informação do utilizador
- `GET /users/{user_id}/details` - Obter detalhes com turmas

### Tools (Acesso Direto)
- `POST /tools/grades/add` - Adicionar nota (professor)
- `POST /tools/grades/update` - Atualizar nota (professor)
- `POST /tools/grades/query` - Consultar notas
- `GET /tools/grades/summary/{student_id}` - Resumo de notas
- `POST /tools/reports/class` - Relatório de turma (professor)
- `DELETE /tools/grades/{grade_id}` - **SEMPRE RETORNA 405** (não permitido)

## Instalação

### Requisitos
- Python 3.10+
- MySQL 8.0+
- OpenAI API Key (para o parser LLM)

### Passos

1. **Clonar o repositório**
```bash
cd final_project
```

2. **Criar ambiente virtual**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

3. **Instalar dependências**
```bash
pip install -r requirements.txt
```

4. **Configurar variáveis de ambiente**
```bash
copy .env.example .env
# Editar .env com as credenciais da base de dados e OpenAI API key
```

5. **Criar base de dados MySQL**
```sql
CREATE DATABASE school_grades CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

6. **Inicializar e popular a base de dados**
```bash
python -m database.seed
```

7. **Iniciar o servidor**
```bash
python main.py
# ou
uvicorn main:app --reload
```

## Utilização

### Via API - Linguagem Natural

```bash
# Aluno consulta as suas notas
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": 3, "message": "Quero ver as minhas notas de Matemática"}'

# Professor adiciona nota
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "message": "Adicionar nota 18 ao Miguel em Matemática, Módulo 1, Teste 2"}'
```

### Via API - Acesso Direto

```bash
# Adicionar nota
curl -X POST http://localhost:8000/tools/grades/add \
  -H "Content-Type: application/json" \
  -d '{
    "teacher_id": 1,
    "student_id": 3,
    "disciplina_id": 1,
    "turma_id": 1,
    "modulo": "Módulo 1",
    "descricao": "Teste 1",
    "valor": 17.5
  }'

# Consultar notas
curl -X POST http://localhost:8000/tools/grades/query \
  -H "Content-Type: application/json" \
  -d '{
    "requester_id": 3,
    "student_id": 3,
    "disciplina_id": 1
  }'
```

### Documentação Interativa

Aceda a `http://localhost:8000/docs` para a documentação Swagger interativa.

## Testes e Demonstração

### Casos de Teste Obrigatórios

Os seguintes cenários são testados na demonstração:

1. **Aluno pede: "Mostra as notas do João"** → ❌ BLOQUEADO
2. **Professor adiciona nota** → ✅ OK
3. **Aluno pede as suas notas por disciplina/módulo** → ✅ OK
4. **Professor pede relatório de turma/disciplinas** → ✅ OK
5. **Tentativa de "apagar nota"** → ❌ RECUSADO (não existe feature)

### Executar Demonstração

```bash
python tests/demo_guardrails.py
```

### Executar Testes Unitários

```bash
pytest tests/ -v
```

## Estrutura do Projeto

```
final_project/
├── api/
│   ├── __init__.py
│   ├── routes.py          # Endpoints FastAPI
│   └── schemas.py         # Schemas Pydantic
├── agent/
│   ├── __init__.py
│   ├── state.py           # AgentState e Intents
│   ├── parser.py          # Parser de intenções e entidades
│   ├── nodes.py           # Nós do workflow LangGraph
│   └── workflow.py        # Grafo LangGraph compilado
├── config/
│   ├── __init__.py
│   └── settings.py        # Configurações da aplicação
├── database/
│   ├── __init__.py
│   ├── models.py          # Modelos SQLAlchemy
│   ├── connection.py      # Gestão de conexões
│   ├── schema.sql         # Schema SQL para MySQL
│   └── seed.py            # Script de dados de teste
├── guardrails/
│   ├── __init__.py
│   └── guardrails.py      # Guardrails de segurança
├── tools/
│   ├── __init__.py
│   ├── authorization.py   # Serviço de autorização
│   ├── exceptions.py      # Exceções customizadas
│   ├── identity.py        # Tools de identidade
│   ├── grades_read.py     # Tools de leitura de notas
│   ├── grades_write.py    # Tools de escrita de notas
│   └── reporting.py       # Tools de relatórios
├── tests/
│   ├── __init__.py
│   ├── demo_guardrails.py # Script de demonstração
│   └── test_authorization.py # Testes unitários
├── main.py                # Aplicação FastAPI principal
├── requirements.txt       # Dependências Python
├── .env.example          # Exemplo de configuração
└── README.md             # Este ficheiro
```

## Intents Suportados

| Intent | Descrição | Roles |
|--------|-----------|-------|
| ADD_GRADE | Adicionar nova nota | Professor |
| UPDATE_GRADE | Atualizar nota existente | Professor |
| QUERY_GRADES | Consultar notas | Professor, Aluno (só próprias) |
| SUMMARY | Ver médias e resumo | Professor, Aluno (só próprias) |
| CLASS_REPORT | Relatório de turma | Professor |
| FALLBACK | Mensagem não compreendida | Todos |
| BLOCKED | Pedido bloqueado por guardrail | - |

## Licença

Este projeto foi desenvolvido como trabalho final académico.
#   l a s t _ p r o j e c t _ a i  
 