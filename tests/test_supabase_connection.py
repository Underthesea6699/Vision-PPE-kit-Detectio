from sqlalchemy import text

from app.database.database import engine


print("Testing Supabase PostgreSQL connection...")


try:

    with engine.connect() as connection:

        result = connection.execute(
            text("SELECT 1")
        )

        print("Database response:", result.scalar())

    print("✅ Supabase connection successful!")


except Exception as error:

    print("❌ Supabase connection failed.")
    print(error)