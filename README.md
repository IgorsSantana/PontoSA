# NBA Analytics App

Aplicativo de análise de dados da NBA para auxiliar apostadores e entusiastas.

## Requisitos

- Python 3.8+
- PostgreSQL
- Node.js 16+ (para o frontend)

## Configuração do Ambiente

1. Clone o repositório:
```bash
git clone [url-do-repositorio]
cd nba-analytics
```

2. Crie um ambiente virtual Python:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
.\venv\Scripts\activate  # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente:
Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:
```
DEBUG=True
SECRET_KEY=sua-chave-secreta
DATABASE_URL=postgresql://usuario:senha@localhost:5432/nba_analytics
```

5. Execute as migrações:
```bash
python manage.py migrate
```

6. Inicie o servidor:
```bash
python manage.py runserver
```

## Estrutura do Projeto

```
nba-analytics/
├── backend/           # Código do backend Django
│   ├── api/          # APIs REST
│   ├── core/         # Funcionalidades principais
│   └── analytics/    # Módulos de análise
├── frontend/         # Código do frontend (React/Flutter)
└── docs/            # Documentação adicional
```

## Contribuição

1. Crie uma branch para sua feature
2. Faça commit das suas alterações
3. Envie um Pull Request

## Licença

MIT 