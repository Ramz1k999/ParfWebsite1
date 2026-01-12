# scripts/backup_db.py
import os
import subprocess
import datetime
import shutil
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.config import settings


def backup_database():
    """
    Создает резервную копию базы данных PostgreSQL.
    """
    # Получаем текущую дату и время для имени файла
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d_%H-%M-%S")

    # Создаем директорию для бэкапов, если она не существует
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)

    # Имя файла бэкапа
    backup_file = backup_dir / f"perfume_store_backup_{date_str}.sql"

    # Получаем параметры подключения из DATABASE_URL
    db_url = settings.DATABASE_URL

    # Парсим URL для получения параметров
    if db_url.startswith("postgresql://"):
        # Формат: postgresql://user:password@host:port/dbname
        db_url = db_url.replace("postgresql://", "")
        user_pass, host_db = db_url.split("@")

        if ":" in user_pass:
            user, password = user_pass.split(":")
        else:
            user, password = user_pass, ""

        if "/" in host_db:
            host_port, dbname = host_db.split("/")
        else:
            host_port, dbname = host_db, "postgres"

        if ":" in host_port:
            host, port = host_port.split(":")
        else:
            host, port = host_port, "5432"
    else:
        print("Неподдерживаемый формат DATABASE_URL")
        return False

    # Команда для создания дампа базы данных
    cmd = [
        "pg_dump",
        f"--host={host}",
        f"--port={port}",
        f"--username={user}",
        f"--dbname={dbname}",
        f"--file={backup_file}"
    ]

    # Устанавливаем переменную окружения PGPASSWORD для аутентификации
    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password

    try:
        # Запускаем команду
        process = subprocess.run(cmd, env=env, check=True, capture_output=True)

        print(f"Резервная копия создана: {backup_file}")

        # Очищаем старые бэкапы (оставляем только 5 последних)
        backup_files = sorted(backup_dir.glob("*.sql"))
        if len(backup_files) > 5:
            for old_file in backup_files[:-5]:
                old_file.unlink()
                print(f"Удален старый бэкап: {old_file}")

        return True
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при создании резервной копии: {e}")
        print(f"Stdout: {e.stdout.decode('utf-8')}")
        print(f"Stderr: {e.stderr.decode('utf-8')}")
        return False


if __name__ == "__main__":
    backup_database()