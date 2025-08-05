from sqlalchemy import create_engine, text

engine = create_engine('sqlite:///green2b.db')
with engine.connect() as conn:
    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
    tables = result.fetchall()
    print([t[0] for t in tables])