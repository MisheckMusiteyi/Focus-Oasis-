import os
from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from typing import List, Optional
from datetime import datetime, date

from .database import engine, Base, get_db
from . import models, schemas, auth

# Initialize Database tables if SQLite is used (for zero-setup dev)
# In production, migrations (e.g. Alembic) are used.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Advanced Focus Portal API",
    description="Secure, production-grade API for the Focus Oasis Student and Admin Portal",
    version="1.0.0"
)

# CORS setup for frontend dynamic integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token")

# ============================================
# DEPENDENCY: CURRENT USER EXTRACTION
# ============================================
def get_current_user_data(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        username: str = payload.get("sub")
        user_type: str = payload.get("user_type")
        if username is None or user_type is None:
            raise credentials_exception
        return schemas.TokenData(username=username, user_type=user_type)
    except JWTError:
        raise credentials_exception

def get_current_admin(
    token_data: schemas.TokenData = Depends(get_current_user_data),
    db: Session = Depends(get_db)
):
    if token_data.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin privileges required."
        )
    admin = db.query(models.Admin).filter(models.Admin.username == token_data.username).first()
    if not admin:
        raise HTTPException(status_code=401, detail="Admin account not found")
    return admin

def get_current_student(
    token_data: schemas.TokenData = Depends(get_current_user_data),
    db: Session = Depends(get_db)
):
    if token_data.user_type != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Student account required."
        )
    student = db.query(models.Student).filter(models.Student.username == token_data.username).first()
    if not student:
        raise HTTPException(status_code=401, detail="Student account not found")
    if student.status != "Active":
        raise HTTPException(status_code=403, detail="Student account is inactive or suspended.")
    return student

# ============================================
# ENDPOINTS: AUTHENTICATION
# ============================================
@app.post("/api/token", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # 1. Try checking if it's an admin first
    admin = db.query(models.Admin).filter(models.Admin.username == form_data.username).first()
    if admin and auth.verify_password(form_data.password, admin.password_hash):
        access_token = auth.create_access_token(data={"sub": admin.username, "user_type": "admin"})
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_type": "admin",
            "username": admin.username,
            "display_name": "Administrator"
        }

    # 2. Try checking if it's a student
    student = db.query(models.Student).filter(models.Student.username == form_data.username).first()
    if student:
        if student.status != "Active":
            raise HTTPException(status_code=400, detail="Student account is inactive.")
        if auth.verify_password(form_data.password, student.password_hash):
            access_token = auth.create_access_token(data={"sub": student.username, "user_type": "student"})
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user_type": "student",
                "username": student.username,
                "display_name": student.student_name
            }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

# Setup initial admin if table is empty (Seed)
@app.post("/api/setup/admin", response_model=schemas.AdminOut, status_code=201)
def seed_admin(admin_data: schemas.AdminCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Admin).first()
    if existing:
        raise HTTPException(status_code=400, detail="Admin account already exists.")
    hashed_pass = auth.get_password_hash(admin_data.password)
    new_admin = models.Admin(
        username=admin_data.username,
        password_hash=hashed_pass,
        email=admin_data.email
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    return new_admin

# ============================================
# ENDPOINTS: ADMIN ACTIONS (CRUD students)
# ============================================
@app.post("/api/admin/students", response_model=schemas.StudentOut, status_code=201)
def create_student(
    student_data: schemas.StudentCreate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    # Check if username exists
    dup = db.query(models.Student).filter(models.Student.username == student_data.username).first()
    if dup:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Check if student number exists
    dup_num = db.query(models.Student).filter(models.Student.student_number == student_data.student_number).first()
    if dup_num:
        raise HTTPException(status_code=400, detail="Student number already registered")

    hashed_pass = auth.get_password_hash(student_data.password)
    db_student = models.Student(
        username=student_data.username,
        password_hash=hashed_pass,
        student_name=student_data.student_name,
        student_number=student_data.student_number,
        student_class=student_data.student_class,
        date_of_birth=student_data.date_of_birth,
        gender=student_data.gender,
        address=student_data.address,
        guardian_name=student_data.guardian_name,
        guardian_phone=student_data.guardian_phone
    )
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student

@app.get("/api/admin/students", response_model=List[schemas.StudentOut])
def list_students(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return db.query(models.Student).order_by(models.Student.student_name).all()

@app.delete("/api/admin/students/{student_id}", status_code=204)
def delete_student(
    student_id: int,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    db.delete(student)
    db.commit()
    return

# ============================================
# ENDPOINTS: ADMIN ACTIONS (Finances & Marks)
# ============================================
@app.post("/api/admin/payments", response_model=schemas.FeePaymentOut, status_code=201)
def record_payment(
    payment_data: schemas.FeePaymentCreate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.id == payment_data.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    payment = models.FeePayment(
        student_id=payment_data.student_id,
        month_covered=payment_data.month_covered,
        amount_paid=payment_data.amount_paid,
        payment_method=payment_data.payment_method,
        date=payment_data.date or datetime.utcnow().date()
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment

@app.post("/api/admin/performances", response_model=schemas.PerformanceOut, status_code=201)
def add_performance(
    perf_data: schemas.PerformanceCreate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.id == perf_data.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    perf = models.Performance(
        student_id=perf_data.student_id,
        activity=perf_data.activity,
        mark=perf_data.mark,
        comment=perf_data.comment,
        date=perf_data.date or datetime.utcnow().date()
    )
    db.add(perf)
    db.commit()
    db.refresh(perf)
    return perf

@app.post("/api/admin/attendances", response_model=schemas.AttendanceOut, status_code=201)
def add_attendance(
    att_data: schemas.AttendanceCreate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter(models.Student.id == att_data.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    att = models.Attendance(
        student_id=att_data.student_id,
        status=att_data.status,
        date=att_data.date or datetime.utcnow().date()
    )
    db.add(att)
    db.commit()
    db.refresh(att)
    return att

# Expense & Other Income Endpoints
@app.post("/api/admin/expenses", response_model=schemas.SchoolExpenseOut, status_code=201)
def record_expense(
    expense_data: schemas.SchoolExpenseCreate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    exp = models.SchoolExpense(
        category=expense_data.category,
        description=expense_data.description,
        amount=expense_data.amount,
        date=expense_data.date or datetime.utcnow().date()
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return exp

@app.get("/api/admin/expenses", response_model=List[schemas.SchoolExpenseOut])
def list_expenses(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return db.query(models.SchoolExpense).order_by(models.SchoolExpense.date.desc()).all()

@app.post("/api/admin/income", response_model=schemas.OtherIncomeOut, status_code=201)
def record_income(
    income_data: schemas.OtherIncomeCreate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    inc = models.OtherIncome(
        source=income_data.source,
        amount=income_data.amount,
        date=income_data.date or datetime.utcnow().date()
    )
    db.add(inc)
    db.commit()
    db.refresh(inc)
    return inc

@app.get("/api/admin/income", response_model=List[schemas.OtherIncomeOut])
def list_income(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return db.query(models.OtherIncome).order_by(models.OtherIncome.date.desc()).all()

# Admin Dashboard Overview Metrics
@app.get("/api/admin/overview")
def get_admin_overview(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    total_students = db.query(models.Student).count()

    # Financial aggregate sums
    total_fees_collected = db.query(models.FeePayment).with_entities(models.FeePayment.amount_paid).all()
    fees_sum = sum([p[0] for p in total_fees_collected])

    total_expenses = db.query(models.SchoolExpense).with_entities(models.SchoolExpense.amount).all()
    expenses_sum = sum([e[0] for e in total_expenses])

    other_income = db.query(models.OtherIncome).with_entities(models.OtherIncome.amount).all()
    other_income_sum = sum([o[0] for o in other_income])

    net_position = fees_sum + other_income_sum - expenses_sum

    # Class distribution
    students = db.query(models.Student).all()
    classes_distribution = {}
    for s in students:
        if s.student_class:
            classes_distribution[s.student_class] = classes_distribution.get(s.student_class, 0) + 1

    return {
        "total_students": total_students,
        "total_classes": len(classes_distribution),
        "fees_collected": fees_sum,
        "other_income": other_income_sum,
        "expenses": expenses_sum,
        "net_position": net_position,
        "classes_distribution": classes_distribution
    }

# ============================================
# ENDPOINTS: STUDENT ACTIONS
# ============================================
@app.get("/api/student/profile", response_model=schemas.StudentDashboardData)
def get_student_dashboard_profile(
    student: models.Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    # Fetch Student data from relationship queries
    payments = student.payments
    performances = student.performances
    attendances = student.attendances

    # Financial Balance calculations
    total_paid = sum([p.amount_paid for p in payments])

    # Fee structure model: default monthly fee is $50. In a full system, you could read this from models.
    monthly_fee = 50.0
    months_enrolled = len(set([p.month_covered for p in payments])) if len(payments) > 0 else 1
    months_enrolled = max(months_enrolled, 1)

    total_fees_due = months_enrolled * monthly_fee
    overall_balance = max(0.0, total_fees_due - total_paid)

    return {
        "student": student,
        "payments": payments,
        "performances": performances,
        "attendances": attendances,
        "overall_balance": overall_balance
    }

@app.put("/api/student/profile", response_model=schemas.StudentOut)
def update_own_student_profile(
    profile_data: schemas.StudentUpdate,
    student: models.Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    if profile_data.student_name is not None:
        student.student_name = profile_data.student_name
    if profile_data.date_of_birth is not None:
        student.date_of_birth = profile_data.date_of_birth
    if profile_data.gender is not None:
        student.gender = profile_data.gender
    if profile_data.address is not None:
        student.address = profile_data.address
    if profile_data.guardian_name is not None:
        student.guardian_name = profile_data.guardian_name
    if profile_data.guardian_phone is not None:
        student.guardian_phone = profile_data.guardian_phone
    if profile_data.profile_photo_b64 is not None:
        student.profile_photo_b64 = profile_data.profile_photo_b64

    db.commit()
    db.refresh(student)
    return student
