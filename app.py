from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///fairtrack.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ================== MODELS ==================

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("team.id"), nullable=True)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(200))
    hours = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    team_id = db.Column(db.Integer, db.ForeignKey("team.id"))

# ================== ROUTES ==================

@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name = request.form["name"]
        password = request.form["password"]
        role = request.form["role"]
        team_id = request.form.get("team_id")

        user = User.query.filter_by(name=name).first()

        if not user:
            hashed = generate_password_hash(password)
            user = User(
                name=name,
                password=hashed,
                role=role,
                team_id=int(team_id) if role == "student" and team_id else None
            )
            db.session.add(user)
            db.session.commit()
        else:
            if not check_password_hash(user.password, password):
                return "Wrong password"

        session["user_id"] = user.id
        session["role"] = user.role

        if user.role == "teacher":
            return redirect(url_for("teacher_dashboard"))
        else:
            return redirect(url_for("student_dashboard"))

    teams = Team.query.all()
    return render_template("login.html", teams=teams)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))

# ================== TEACHER ==================

@app.route("/teacher")
def teacher_dashboard():
    if session.get("role") != "teacher":
        return redirect(url_for("landing"))

    teams = Team.query.all()
    selected_team_id = request.args.get("team_id")

    students_data = []
    team_total = 0

    if selected_team_id:
        selected_team_id = int(selected_team_id)

        students = User.query.filter_by(role="student", team_id=selected_team_id).all()
        tasks = Task.query.filter_by(team_id=selected_team_id).all()
        team_total = sum(t.hours for t in tasks)

        for student in students:
            user_tasks = Task.query.filter_by(user_id=student.id).all()
            total = sum(t.hours for t in user_tasks)
            contribution = (total / team_total * 100) if team_total > 0 else 0

            students_data.append({
                "name": student.name,
                "hours": total,
                "contribution": round(contribution, 2)
            })

        students_data = sorted(students_data, key=lambda x: x["contribution"], reverse=True)

    return render_template(
        "teacher_dashboard.html",
        teams=teams,
        students=students_data,
        team_total=team_total,
        selected_team_id=selected_team_id
    )

@app.route("/create_team", methods=["POST"])
def create_team():
    if session.get("role") != "teacher":
        return redirect(url_for("landing"))

    team_name = request.form["team_name"]
    team = Team(name=team_name)
    db.session.add(team)
    db.session.commit()

    return redirect(url_for("teacher_dashboard"))

# ================== STUDENT ==================

@app.route("/student")
def student_dashboard():
    if session.get("role") != "student":
        return redirect(url_for("landing"))

    user = User.query.get(session["user_id"])
    tasks = Task.query.filter_by(user_id=user.id).all()
    total_hours = sum(t.hours for t in tasks)

    return render_template(
        "student_dashboard.html",
        user=user,
        tasks=tasks,
        total_hours=total_hours
    )

@app.route("/add_task", methods=["POST"])
def add_task():
    if session.get("role") != "student":
        return redirect(url_for("landing"))

    task_name = request.form["task_name"]
    hours = float(request.form["hours"])

    user = User.query.get(session["user_id"])

    task = Task(
        task_name=task_name,
        hours=hours,
        user_id=user.id,
        team_id=user.team_id
    )

    db.session.add(task)
    db.session.commit()

    return redirect(url_for("student_dashboard"))

# ================== RUN ==================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)