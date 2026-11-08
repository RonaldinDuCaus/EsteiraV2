import os

import psycopg


if os.getenv("CONFIRM_RESET") != "SIM":
    raise SystemExit("Operação cancelada. Execute com CONFIRM_RESET=SIM somente quando quiser apagar os dados.")

database_url = os.environ["DATABASE_URL"]
with psycopg.connect(database_url) as connection:
    with connection.cursor() as cursor:
        cursor.execute("TRUNCATE recognition_events, component_images, components RESTART IDENTITY CASCADE")
print("Cadastros, imagens de referência e histórico foram removidos do banco.")

