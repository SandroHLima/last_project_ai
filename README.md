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