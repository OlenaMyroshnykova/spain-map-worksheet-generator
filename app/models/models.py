from dataclasses import dataclass

@dataclass(frozen=True)
class Province:
    id: str
    name: str
    community_code: str