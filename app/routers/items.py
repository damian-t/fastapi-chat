from fastapi import APIRouter, HTTPException, status

from app.models.item import Item, ItemCreate
from app.services.item_service import item_service

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", response_model=list[Item])
def list_items() -> list[Item]:
    return item_service.list_items()


@router.get("/{item_id}", response_model=Item)
def get_item(item_id: int) -> Item:
    item = item_service.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.post("", response_model=Item, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreate) -> Item:
    return item_service.create_item(payload)
