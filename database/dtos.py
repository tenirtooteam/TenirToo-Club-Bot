from dataclasses import dataclass, field
from typing import List, Optional, Any

@dataclass
class EventDTO:
    id: int
    title: str
    start_date: str
    end_date: Optional[str]
    creator_id: Optional[int]
    is_approved: bool
    sheet_url: Optional[str]
    start_iso: Optional[str] = None
    end_iso: Optional[str] = None
    leads: List[int] = field(default_factory=list)
    participants: List[int] = field(default_factory=list)

    def __getitem__(self, item: Any) -> Any:
        if not isinstance(item, str):
            raise TypeError(f"attribute name must be string, not '{type(item).__name__}'")
        if item == 'event_id':
            return self.id
        if not hasattr(self, item):
            raise KeyError(item)
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        if item == 'event_id':
            return self.id
        return getattr(self, item, default)

    def __contains__(self, item: Any) -> bool:
        if item == 'event_id':
            return True
        return hasattr(self, item)


@dataclass
class AuditRequestDTO:
    id: int
    user_id: int
    entity_type: str
    entity_id: int
    status: str
    comment: Optional[str] = None
    created_at: Optional[str] = None

    def __getitem__(self, item: Any) -> Any:
        if not isinstance(item, str):
            raise TypeError(f"attribute name must be string, not '{type(item).__name__}'")
        if not hasattr(self, item):
            raise KeyError(item)
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)

    def __contains__(self, item: Any) -> bool:
        return hasattr(self, item)
