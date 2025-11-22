from app.core.database import SessionLocal
from app.models.taxonomy import Taxonomy, TaxonomyValue

db = SessionLocal()

val_status = db.query(Taxonomy).filter(Taxonomy.name == 'Validation Request Status').first()
if val_status:
    print('Validation Request Status values:')
    for v in db.query(TaxonomyValue).filter(TaxonomyValue.taxonomy_id == val_status.taxonomy_id).all():
        print(f'  - {v.code}: {v.label}')

val_type = db.query(Taxonomy).filter(Taxonomy.name == 'Validation Type').first()
if val_type:
    print('\nValidation Type values:')
    for v in db.query(TaxonomyValue).filter(TaxonomyValue.taxonomy_id == val_type.taxonomy_id).all():
        print(f'  - {v.code}: {v.label}')

priority = db.query(Taxonomy).filter(Taxonomy.name == 'Validation Priority').first()
if priority:
    print('\nValidation Priority values:')
    for v in db.query(TaxonomyValue).filter(TaxonomyValue.taxonomy_id == priority.taxonomy_id).all():
        print(f'  - {v.code}: {v.label}')

db.close()
