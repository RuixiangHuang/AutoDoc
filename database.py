import sqlite3
import os
from typing import List, Tuple, Optional

DB_PATH = "data_clean/codebase.db"


def init_database():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            file TEXT NOT NULL,
            start_line INTEGER NOT NULL,
            end_line INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS functions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            file TEXT NOT NULL,
            class_name TEXT,
            start_line INTEGER NOT NULL,
            end_line INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS variables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            file TEXT NOT NULL,
            class_name TEXT,
            function_name TEXT,
            line_number INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_classes_name ON classes(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_classes_file ON classes(file)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_functions_name ON functions(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_functions_file ON functions(file)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_functions_class ON functions(class_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_variables_name ON variables(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_variables_file ON variables(file)")
    
    conn.commit()
    conn.close()
    print(f"✅ Database initialized at {DB_PATH}")


def clear_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM classes")
    cursor.execute("DELETE FROM functions")
    cursor.execute("DELETE FROM variables")
    conn.commit()
    conn.close()
    print("✅ Database cleared")


def save_classes(classes: List[Tuple[str, str, int, int]]):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT INTO classes (name, file, start_line, end_line) VALUES (?, ?, ?, ?)",
        classes
    )
    conn.commit()
    conn.close()
    print(f"✅ Saved {len(classes)} classes to database")


def save_functions(functions: List[Tuple[str, str, str, int, int]]):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT INTO functions (name, file, class_name, start_line, end_line) VALUES (?, ?, ?, ?, ?)",
        functions
    )
    conn.commit()
    conn.close()
    print(f"✅ Saved {len(functions)} functions to database")


def save_variables(variables: List[Tuple[str, str, str, str, int]]):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT INTO variables (name, file, class_name, function_name, line_number) VALUES (?, ?, ?, ?, ?)",
        variables
    )
    conn.commit()
    conn.close()
    print(f"✅ Saved {len(variables)} variables to database")


def search_classes(query: str) -> List[Tuple]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, file, start_line, end_line FROM classes WHERE name LIKE ? OR file LIKE ?",
        (f"%{query}%", f"%{query}%")
    )
    results = cursor.fetchall()
    conn.close()
    return results


def search_functions(query: str, class_name: Optional[str] = None) -> List[Tuple]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if class_name:
        cursor.execute(
            """SELECT name, file, class_name, start_line, end_line 
               FROM functions 
               WHERE (name LIKE ? OR file LIKE ?) AND class_name = ?""",
            (f"%{query}%", f"%{query}%", class_name)
        )
    else:
        cursor.execute(
            "SELECT name, file, class_name, start_line, end_line FROM functions WHERE name LIKE ? OR file LIKE ?",
            (f"%{query}%", f"%{query}%")
        )
    results = cursor.fetchall()
    conn.close()
    return results


def search_variables(query: str, file: Optional[str] = None) -> List[Tuple]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if file:
        cursor.execute(
            """SELECT name, file, class_name, function_name, line_number 
               FROM variables 
               WHERE (name LIKE ?) AND file = ?""",
            (f"%{query}%", file)
        )
    else:
        cursor.execute(
            "SELECT name, file, class_name, function_name, line_number FROM variables WHERE name LIKE ?",
            (f"%{query}%",)
        )
    results = cursor.fetchall()
    conn.close()
    return results


def get_class_with_details(class_name: str) -> Optional[Tuple]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT name, file, start_line, end_line FROM classes WHERE name = ?",
        (class_name,)
    )
    class_info = cursor.fetchone()
    
    if class_info:
        cursor.execute(
            "SELECT name, start_line, end_line FROM functions WHERE class_name = ?",
            (class_name,)
        )
        methods = cursor.fetchall()
        
        cursor.execute(
            "SELECT name, line_number FROM variables WHERE class_name = ? AND function_name = ''",
            (class_name,)
        )
        variables = cursor.fetchall()
        
        conn.close()
        return (class_info, methods, variables)
    
    conn.close()
    return None


def get_statistics() -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    stats = {
        'classes': cursor.execute("SELECT COUNT(*) FROM classes").fetchone()[0],
        'functions': cursor.execute("SELECT COUNT(*) FROM functions").fetchone()[0],
        'variables': cursor.execute("SELECT COUNT(*) FROM variables").fetchone()[0],
        'files': len(cursor.execute("SELECT DISTINCT file FROM classes").fetchall())
    }
    
    conn.close()
    return stats

