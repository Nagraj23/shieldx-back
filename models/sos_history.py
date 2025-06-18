from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from bson import ObjectId

class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(ObjectId(v))

    @classmethod
    def __get_pydantic_json_schema__(cls, _schema_generator):
        return {"type": "string"}

class SOSHistory(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    user_id: str
    location_latitude: float
    location_longitude: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    notifiedContacts: List[str]
    status: str = "triggered"  # triggered, resolved, false_alarm

    def dict(self, *args, **kwargs):
        """Custom serialization for dict output."""
        data = super().dict(*args, **kwargs)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
