from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.core.database import SessionLocal
import os
os.environ["DATABASE_URL"] = "postgresql://mrm_user:mrm_pass@localhost:5432/mrm_db"


db = SessionLocal()

taxonomies = db.query(Taxonomy).all()
for tax in taxonomies:
    print(f"Taxonomy: {tax.name}")
    if "Risk" in tax.name or "Tier" in tax.name:
        for v in db.query(TaxonomyValue).filter(TaxonomyValue.taxonomy_id == tax.taxonomy_id).all():
            print(f'  - {v.code}: {v.label}')

db.close()
