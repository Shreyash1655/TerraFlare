from typing import List
from pydantic import BaseModel

class FirmsResponse(BaseModel):
    mode: str            # "real" | "synthetic"
    data_label: str
    note: str
    count: int
    items: List[dict]