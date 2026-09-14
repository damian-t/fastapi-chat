from pydantic import BaseModel, Field


class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, examples=["Keyboard"])
    price: float = Field(..., gt=0, examples=[79.90])
    tags: list[str] = Field(default_factory=list, examples=[["hardware", "office"]])


class ItemCreate(ItemBase):
    pass


class Item(ItemBase):
    id: int = Field(..., examples=[1])
