"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, models, vendors, taxonomies, audit_logs, validations

app = FastAPI(title="MRM System v3", version="3.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(models.router, prefix="/models", tags=["models"])
app.include_router(vendors.router, prefix="/vendors", tags=["vendors"])
app.include_router(taxonomies.router, prefix="/taxonomies", tags=["taxonomies"])
app.include_router(audit_logs.router, prefix="/audit-logs", tags=["audit-logs"])
app.include_router(validations.router, prefix="/validations", tags=["validations"])


@app.get("/")
def read_root():
    return {"message": "MRM System v3 API"}
