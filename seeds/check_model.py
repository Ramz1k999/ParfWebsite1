import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.models.product import Product

def check_model():
    print("Поля модели Product:")
    for column in Product.__table__.columns:
        print(f"  - {column.name}: {column.type}")

if __name__ == "__main__":
    check_model()