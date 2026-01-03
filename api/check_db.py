from app.core.database import SessionLocal
from app.models.model import Model
from app.models.user import User
from app.models.model_hierarchy import ModelHierarchy

db = SessionLocal()
try:
    model_count = db.query(Model).count()
    print(f"Total models: {model_count}")

    users = db.query(User).all()
    print(f"Total users: {len(users)}")
    for u in users:
        print(f"User: {u.email}, Role: {u.role}")

    models = db.query(Model).all()
    for m in models:
        print(
            f"Model: {m.model_name}, Owner: {m.owner_id}, Status: {m.status}, Approval: {m.row_approval_status}")

    hierarchy_count = db.query(ModelHierarchy).count()
    print(f"Total hierarchy entries: {hierarchy_count}")

    hierarchies = db.query(ModelHierarchy).all()
    for h in hierarchies:
        print(
            f"Parent: {h.parent_model_id}, Child: {h.child_model_id}, Type: {h.relation_type_id}")

finally:
    db.close()
