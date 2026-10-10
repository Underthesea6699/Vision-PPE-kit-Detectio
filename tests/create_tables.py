from app.database.database import Base, engine
from app.models.incident import Incident

print("Creating database tables...")

Base.metadata.create_all(bind=engine)

print("✅ Database tables created successfully!") 