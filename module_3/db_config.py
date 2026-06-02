DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "gradcafe",
    "user": "postgres",
    "password": "Pamelaskye2116$",
}

def get_conn_string() -> str:
    c = DB_CONFIG
    return f"host={c['host']} port={c['port']} dbname={c['dbname']} user={c['user']} password={c['password']}"
