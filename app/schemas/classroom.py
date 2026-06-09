from pydantic import BaseModel

class ClassroomCreate(BaseModel):
    name: str
    section: str
    academic_year: str

class ClassroomResponse(BaseModel):
    id: int
    name: str
    section: str | None
    academic_year: str

    class Config:
        from_attributes = True
