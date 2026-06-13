import psycopg2
import psycopg2.pool
import os
import logging

logging.basicConfig(level=logging.INFO)

try:
    db_pool = psycopg2.pool.SimpleConnectionPool(
        1, 20,  
        os.getenv("DATABASE_URL")
    )
    logging.info("Пул соединений успешно создан.")
except psycopg2.DatabaseError as error:
    logging.error(f"Ошибка при создании пула соединений: {error}")
    db_pool = None

def get_connection():
    """Получить соединение из пула"""
    if db_pool is None:
        logging.error("Пул соединений не инициализирован.")
        return None
    try:
        conn = db_pool.getconn()
        logging.info("Получено соединение из пула.")
        return conn
    except psycopg2.DatabaseError as error:
        logging.error(f"Ошибка подключения к базе данных: {error}")
        return None

def release_connection(conn):
    """Вернуть соединение в пул"""
    if db_pool and conn:
        db_pool.putconn(conn)
        logging.info("Соединение возвращено в пул.")

def create_table():
    """Создать таблицу clients, если она не существует"""
    conn = get_connection()
    if conn is None:
        return
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clients (
                    id SERIAL PRIMARY KEY,
                    trip_direction VARCHAR(255),
                    people_number VARCHAR(255),
                    travel_dates VARCHAR(255),
                    budget VARCHAR(255),
                    customer_wishes VARCHAR(500),
                    phone_number VARCHAR(50),
                    name VARCHAR(100)
                );
                CREATE INDEX IF NOT EXISTS idx_phone_number ON clients(phone_number);
                CREATE INDEX IF NOT EXISTS idx_name ON clients(name);
            """)
            conn.commit()
            logging.info("Таблица clients успешно создана.")
    except Exception as error:
        logging.error(f"Ошибка при создании таблицы: {error}")
    finally:
        release_connection(conn)

def insert_data(trip_details, contact_details):
    """Вставить данные о клиенте в таблицу clients"""
    conn = get_connection()
    if conn is None:
        return
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO clients (trip_direction, people_number, travel_dates, budget, customer_wishes, phone_number, name)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, (
                trip_details.get("trip_direction"),
                trip_details.get("people_number"),
                trip_details.get("travel_dates"),
                trip_details.get("budget"),
                trip_details.get("customer_wishes"),
                contact_details.get("phone_number"),
                contact_details.get("name")
            ))
            conn.commit()
            logging.info("Данные успешно записаны в базу данных.")
    except Exception as error:
        logging.error(f"Ошибка записи данных в базу данных: {error}")
    finally:
        release_connection(conn)
