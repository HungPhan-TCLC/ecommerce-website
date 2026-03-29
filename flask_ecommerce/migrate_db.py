"""
migrate_db.py - Tạo các bảng mới trong database
Chạy: python migrate_db.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db

def migrate():
    app = create_app()
    with app.app_context():
        # Tạo tất cả bảng mới (không xóa bảng cũ)
        db.create_all()
        
        # Kiểm tra thêm cột source vào user_interactions nếu chưa có
        from sqlalchemy import text, inspect
        inspector = inspect(db.engine)
        
        # Check user_interactions
        cols_ui = [c['name'] for c in inspector.get_columns('user_interactions')]
        if 'source' not in cols_ui:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE user_interactions ADD COLUMN source VARCHAR(50)"))
                conn.commit()
            print("[OK] Added column 'source' to user_interactions")
        else:
            print("[OK] Column 'source' already exists in user_interactions")
        
        # Check evaluation_results table exists
        tables = inspector.get_table_names()
        if 'evaluation_results' in tables:
            print("[OK] Table 'evaluation_results' exists")
        else:
            print("[ERROR] Table 'evaluation_results' was not created!")
        
        print("\nMigration completed successfully!")
        print(f"Tables: {tables}")

if __name__ == '__main__':
    migrate()
