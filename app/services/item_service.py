from app.models.item import Item, ItemCreate


class ItemService:
    """Minimal in-memory service layer."""

    def __init__(self) -> None:
        self._items: dict[int, Item] = {}
        self._next_id = 1

    def list_items(self) -> list[Item]:
        return list(self._items.values())

    def get_item(self, item_id: int) -> Item | None:
        return self._items.get(item_id)

    def create_item(self, payload: ItemCreate) -> Item:
        item = Item(id=self._next_id, **payload.model_dump())
        self._items[item.id] = item
        self._next_id += 1
        return item


item_service = ItemService()
