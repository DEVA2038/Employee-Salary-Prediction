# emergency_fix.py
import sqlite3
import os
import sys

def get_database_path():
    """Find the database file"""
    possible_paths = [
        'salary_predictor.db',
        'instance/salary_predictor.db', 
        'app.db',
        'instance/app.db'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def emergency_fix():
    db_path = get_database_path()
    
    if not db_path:
        print("❌ No database file found! Creating a new one...")
        db_path = 'salary_predictor.db'
    
    print(f"📁 Database file: {db_path}")
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 Checking current schema...")
        
        # Get current table structure
        cursor.execute("PRAGMA table_info(company_requests)")
        current_columns = [row[1] for row in cursor.fetchall()]
        print(f"Current columns: {current_columns}")
        
        # List of columns we need to add
        columns_to_add = [
            ('data_points', 'INTEGER'),
            ('predictions_count', 'INTEGER DEFAULT 0'),
            ('updated_at', 'DATETIME')
        ]
        
        # Add missing columns
        for col_name, col_type in columns_to_add:
            if col_name not in current_columns:
                print(f"➕ Adding column: {col_name}")
                cursor.execute(f"ALTER TABLE company_requests ADD COLUMN {col_name} {col_type}")
        
        # Set default values for existing records
        print("🔄 Setting default values for existing records...")
        cursor.execute("UPDATE company_requests SET data_points = 0 WHERE data_points IS NULL")
        cursor.execute("UPDATE company_requests SET predictions_count = 0 WHERE predictions_count IS NULL")
        cursor.execute("UPDATE company_requests SET updated_at = datetime('now') WHERE updated_at IS NULL")
        
        # Commit changes
        conn.commit()
        
        # Verify the changes
        cursor.execute("PRAGMA table_info(company_requests)")
        updated_columns = [row[1] for row in cursor.fetchall()]
        print(f"✅ Updated columns: {updated_columns}")
        
        # Count records to verify everything is working
        cursor.execute("SELECT COUNT(*) FROM company_requests")
        count = cursor.fetchone()[0]
        print(f"📊 Total company requests: {count}")
        
        conn.close()
        print("🎉 Database fixed successfully! You can now login.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("🔄 Trying alternative approach...")
        try:
            # If the above fails, try a more direct approach
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Direct SQL commands
            sql_commands = [
                "ALTER TABLE company_requests ADD COLUMN data_points INTEGER;",
                "ALTER TABLE company_requests ADD COLUMN predictions_count INTEGER DEFAULT 0;", 
                "ALTER TABLE company_requests ADD COLUMN updated_at DATETIME;",
                "UPDATE company_requests SET data_points = 0;",
                "UPDATE company_requests SET predictions_count = 0;",
                "UPDATE company_requests SET updated_at = datetime('now');"
            ]
            
            for cmd in sql_commands:
                try:
                    cursor.execute(cmd)
                    print(f"✅ Executed: {cmd.split()[0]}...")
                except Exception as cmd_error:
                    print(f"⚠️  Note: {cmd_error}")
            
            conn.commit()
            conn.close()
            print("🎉 Database fixed with alternative method!")
            
        except Exception as e2:
            print(f"❌ Alternative method also failed: {e2}")
            print("💡 Creating a completely new database...")
            create_new_database()

def create_new_database():
    """Create a brand new database if all else fails"""
    import subprocess
    import time
    
    # Stop any running Flask app
    print("🛑 Please stop your Flask app (Ctrl+C) if it's running...")
    time.sleep(2)
    
    # Remove old database
    db_path = get_database_path()
    if db_path and os.path.exists(db_path):
        os.remove(db_path)
        print(f"🗑️ Removed old database: {db_path}")
    
    # Import and create new database
    from database import Base, engine
    Base.metadata.create_all(bind=engine)
    print("✅ Created brand new database with correct schema!")
    
    print("\n📝 Next steps:")
    print("1. Restart your Flask app: python app.py")
    print("2. You may need to register a new company account")
    print("3. Or approve existing companies again through admin")

if __name__ == "__main__":
    print("🚀 EMERGENCY DATABASE FIX")
    print("=" * 50)
    emergency_fix()
    print("=" * 50)
    print("🎯 Fix completed! Please restart your Flask app.")