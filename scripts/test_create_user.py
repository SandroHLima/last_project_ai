from database import get_db_context
from tools.identity import create_user

with get_db_context() as db:
    u = create_user(db=db, name='API Teacher', role='teacher')
    print('Created', u)
