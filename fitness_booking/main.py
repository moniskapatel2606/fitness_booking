from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import pytz
import logging

# Setup
app = FastAPI()
templates = Jinja2Templates(directory="templates")


logging.basicConfig(level=logging.INFO)

# DB Setup
DATABASE_URL = "sqlite:///./database.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class FitnessClass(Base):
    __tablename__ = "classes"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    datetime = Column(DateTime)
    instructor = Column(String)
    slots = Column(Integer)

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True)
    class_id = Column(Integer, ForeignKey("classes.id"))
    client_name = Column(String)
    client_email = Column(String)
    fitness_class = relationship("FitnessClass")

Base.metadata.create_all(bind=engine)

# Seed sample data if not exists
def seed_classes():
    db = SessionLocal()
    if db.query(FitnessClass).count() == 0:
        classes = [
            FitnessClass(name="Yoga", datetime=datetime(2025, 6, 12, 7, 0, tzinfo=pytz.timezone("Asia/Kolkata")), instructor="Anu", slots=5),
            FitnessClass(name="Zumba", datetime=datetime(2025, 6, 12, 9, 0, tzinfo=pytz.timezone("Asia/Kolkata")), instructor="Ravi", slots=5),
            FitnessClass(name="HIIT", datetime=datetime(2025, 6, 12, 18, 0, tzinfo=pytz.timezone("Asia/Kolkata")), instructor="Neha", slots=5),
        ]
        db.add_all(classes)
        db.commit()
    db.close()

seed_classes()

# Utility
def get_classes_in_timezone(timezone: str = "Asia/Kolkata"):
    tz = pytz.timezone(timezone)
    db = SessionLocal()
    classes = db.query(FitnessClass).all()
    result = []
    for c in classes:
        utc_time = c.datetime.astimezone(pytz.utc)
        local_time = utc_time.astimezone(tz)
        result.append({
            "id": c.id,
            "name": c.name,
            "datetime": local_time.strftime("%Y-%m-%d %H:%M"),
            "instructor": c.instructor,
            "available_slots": c.slots
        })
    db.close()
    return result

# Routes
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/classes")
def get_classes(timezone: str = "Asia/Kolkata"):
    return get_classes_in_timezone(timezone)

@app.post("/book")
def book_class(class_id: int = Form(...), client_name: str = Form(...), client_email: str = Form(...)):
    db = SessionLocal()
    fitness_class = db.query(FitnessClass).filter(FitnessClass.id == class_id).first()
    if not fitness_class:
        return {"error": "Class not found"}
    if fitness_class.slots <= 0:
        return {"error": "No slots available"}
    booking = Booking(class_id=class_id, client_name=client_name, client_email=client_email)
    fitness_class.slots -= 1
    db.add(booking)
    db.commit()
    db.close()
    return {"message": "Booking successful"}

@app.get("/bookings", response_class=HTMLResponse)
def view_bookings(request: Request, email: str):
    db = SessionLocal()
    bookings = db.query(Booking).filter(Booking.client_email == email).all()
    result = [{
        "name": b.fitness_class.name,
        "datetime": b.fitness_class.datetime.strftime("%Y-%m-%d %H:%M"),
        "instructor": b.fitness_class.instructor
    } for b in bookings]
    db.close()
    return templates.TemplateResponse("bookings.html", {"request": request, "bookings": result})
