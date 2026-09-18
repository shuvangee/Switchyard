from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import ModelConfigOut
from app.db.session import get_db
from app.models.model_config import ModelConfigORM

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[ModelConfigOut])
def list_models(db: Session = Depends(get_db)) -> list[ModelConfigOut]:
    models = db.query(ModelConfigORM).order_by(ModelConfigORM.id).all()
    return [ModelConfigOut.from_orm_model(model) for model in models]
