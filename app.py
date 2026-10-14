"""
Local Skill & Job Exchange Platform
Flask Backend Server with RESTful APIs & Institutional Reporting.
Community Engineering Project (BIT42304) - TGPCET Nagpur
Presented by: Mr. Yash Jadhav | Department of Information Technology
"""

import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_file, session, Response
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_db_connection, db_session, init_db
try:
    from .seed_data import NEIGHBORHOODS
except ImportError:
    from seed_data import NEIGHBORHOODS
from reports_generator import generate_pdf_report, generate_csv_report, get_report_data


def calculate_match_score(job, skill, provider=None):
    """Calculate a dependency-free compatibility score for a job and skill."""
    score = 0.0
    if job.get("category", "").casefold() == skill.get("category", "").casefold():
        score += 45
    if job.get("neighborhood", "").casefold() == skill.get("neighborhood", "").casefold():
        score += 25

    budget = float(job.get("budget") or 0)
    rate = float(skill.get("hourly_rate") or 0)
    if not budget or not rate:
        score += 10
    elif rate <= budget:
        score += 20
    else:
        score += max(0, 20 - ((rate - budget) / budget) * 20)

    if provider:
        score += 5 if provider.get("is_verified") else 0
        score += min(5, float(provider.get("rating") or 0))
    return round(min(score, 100), 2)


def find_top_matches_for_job(job, skills, users, top_k=10):
    """Return active providers ranked by compatibility with the job."""
    matches = []
    for skill in skills:
        provider = users.get(skill.get("user_id"))
        if not provider or provider.get("status", "active") != "active":
            continue
        match = dict(skill)
        match["provider"] = provider
        match["match_score"] = calculate_match_score(job, skill, provider)
        matches.append(match)
    return sorted(matches, key=lambda item: item["match_score"], reverse=True)[:top_k]

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("SECRET_KEY", "tgpcet-community-engineering-secret-key-2026")
init_db()

CATEGORIES = [
    "Electrical",
    "Plumbing",
    "Education & Tutoring",
    "IT & Tech Support",
    "Carpentry & Furniture",
    "House Painting & Masonry",
    "Appliance & AC Repair",
    "Tailoring & Fashion",
    "Gardening & Landscaping",
    "Cooking & Catering",
    "Automobile Maintenance",
    "Handyman & General Repairs"
]


def log_activity(user_id, action, details, conn=None):
    """Log platform activity for admin monitoring."""
    try:
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO activity_logs (user_id, action, details, ip_address)
                VALUES (?, ?, ?, ?)
            """, (user_id, action, details, request.remote_addr or '127.0.0.1'))
        else:
            with db_session() as c:
                cursor = c.cursor()
                cursor.execute("""
                    INSERT INTO activity_logs (user_id, action, details, ip_address)
                    VALUES (?, ?, ?, ?)
                """, (user_id, action, details, request.remote_addr or '127.0.0.1'))
    except Exception as e:
        print(f"Failed to log activity: {e}")


def create_notification(user_id, title, message, link=None, conn=None):
    """Create a persistent notification for a user."""
    try:
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO notifications (user_id, title, message, link)
                VALUES (?, ?, ?, ?)
            """, (user_id, title, message, link))
        else:
            with db_session() as c:
                cursor = c.cursor()
                cursor.execute("""
                    INSERT INTO notifications (user_id, title, message, link)
                    VALUES (?, ?, ?, ?)
                """, (user_id, title, message, link))
    except Exception as e:
        print(f"Failed to create notification: {e}")


# -----------------------------------------------------------------------------
# Web Page Route
# -----------------------------------------------------------------------------
@app.route("/")
def index():
    """Serve the single page web application interface."""
    return render_template("index.html")


@app.route("/api/meta")
def get_metadata():
    """Return platform metadata (categories, neighborhoods, college info)."""
    return jsonify({
        "success": True,
        "project": {
            "title": "Local Skill & Job Exchange Platform",
            "institution": "Tulsiramji Gaikwad-Patil College of Engineering & Technology",
            "group": "Gaikwad-Patil Group of Institutions (GPGI)",
            "department": "Department of Information Technology",
            "course": "Community Engineering Project (BIT42304)",
            "presenter": "Mr. Yash Jadhav",
            "location": "Nagpur, Maharashtra"
        },
        "categories": CATEGORIES,
        "neighborhoods": list(NEIGHBORHOODS.keys())
    })


# -----------------------------------------------------------------------------
# Module 01: User Registration & Authentication (Slide 7 & 11)
# -----------------------------------------------------------------------------
@app.route("/api/auth/register", methods=["POST"])
def register():
    """Secure signup, input validation, and password hashing."""
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    role = data.get("role", "both")
    neighborhood = data.get("neighborhood", "Wardha Road")
    phone = data.get("phone", "").strip()
    bio = data.get("bio", "").strip()

    if not name or not email or not password:
        return jsonify({"success": False, "error": "Name, email, and password are required."}), 400

    lat, lng = NEIGHBORHOODS.get(neighborhood, (21.1458, 79.0882))
    pw_hash = generate_password_hash(password)
    avatar = f"https://api.dicebear.com/7.x/avataaars/svg?seed={name.replace(' ', '')}"

    try:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                return jsonify({"success": False, "error": "Email is already registered."}), 409

            cursor.execute("""
                INSERT INTO users (name, email, password_hash, role, phone, neighborhood, city, lat, lng, bio, avatar)
                VALUES (?, ?, ?, ?, ?, ?, 'Nagpur', ?, ?, ?, ?)
            """, (name, email, pw_hash, role, phone, neighborhood, lat, lng, bio, avatar))
            user_id = cursor.lastrowid

        log_activity(user_id, "USER_REGISTER", f"User {name} registered with role '{role}'.")
        create_notification(user_id, "Welcome to Local Exchange!", "Your community profile has been activated successfully.", "#profile")

        session["user_id"] = user_id
        return jsonify({
            "success": True,
            "message": "Registration successful! Confirmation email simulated.",
            "user": {
                "id": user_id,
                "name": name,
                "email": email,
                "role": role,
                "neighborhood": neighborhood,
                "avatar": avatar,
                "rating": 5.0
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/auth/login", methods=["POST"])
def login():
    """Authenticate user with email and password."""
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"success": False, "error": "Email and password are required."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"success": False, "error": "Invalid email or password."}), 401

    if user["status"] == "suspended":
        return jsonify({"success": False, "error": "Your account has been suspended by administration."}), 403

    session["user_id"] = user["id"]
    log_activity(user["id"], "USER_LOGIN", f"User {user['name']} logged in.")

    return jsonify({
        "success": True,
        "message": f"Welcome back, {user['name']}!",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "phone": user["phone"],
            "neighborhood": user["neighborhood"],
            "bio": user["bio"],
            "avatar": user["avatar"],
            "rating": user["rating"],
            "total_reviews": user["total_reviews"],
            "is_verified": bool(user["is_verified"]),
            "status": user["status"]
        }
    })


@app.route("/api/auth/me")
def get_current_user():
    """Get active session user profile."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "user": None})

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        session.pop("user_id", None)
        return jsonify({"success": False, "user": None})

    return jsonify({
        "success": True,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "phone": user["phone"],
            "neighborhood": user["neighborhood"],
            "bio": user["bio"],
            "avatar": user["avatar"],
            "rating": user["rating"],
            "total_reviews": user["total_reviews"],
            "is_verified": bool(user["is_verified"]),
            "status": user["status"]
        }
    })


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    """Logout current user."""
    uid = session.pop("user_id", None)
    if uid:
        log_activity(uid, "USER_LOGOUT", "User logged out.")
    return jsonify({"success": True, "message": "Logged out successfully."})


# -----------------------------------------------------------------------------
# Module 02: Skill Listing & Search (Slide 7 & 11)
# -----------------------------------------------------------------------------
@app.route("/api/skills", methods=["GET"])
def list_skills():
    """List and search skills with multi-criteria filtering."""
    category = request.args.get("category", "").strip()
    neighborhood = request.args.get("neighborhood", "").strip()
    search = request.args.get("search", "").strip()
    max_rate = request.args.get("max_rate", type=float)
    user_id = request.args.get("user_id", type=int)

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT s.*, u.name as provider_name, u.rating as provider_rating, 
               u.total_reviews as provider_reviews, u.avatar as provider_avatar,
               u.phone as provider_phone, u.is_verified as provider_verified
        FROM skills s
        JOIN users u ON s.user_id = u.id
        WHERE s.status = 'active' AND u.status = 'active'
    """
    params = []

    if category:
        query += " AND s.category = ?"
        params.append(category)

    if neighborhood:
        query += " AND s.neighborhood = ?"
        params.append(neighborhood)

    if user_id:
        query += " AND s.user_id = ?"
        params.append(user_id)

    if max_rate:
        query += " AND s.hourly_rate <= ?"
        params.append(max_rate)

    if search:
        query += " AND (s.title LIKE ? OR s.description LIKE ? OR s.tags LIKE ? OR u.name LIKE ?)"
        like_term = f"%{search}%"
        params.extend([like_term, like_term, like_term, like_term])

    query += " ORDER BY u.rating DESC, s.created_at DESC"
    cursor.execute(query, params)
    skills = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return jsonify({"success": True, "count": len(skills), "skills": skills})


@app.route("/api/skills", methods=["POST"])
def create_skill():
    """Publish a new skill listing."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "Please login to publish a skill."}), 401

    data = request.get_json() or {}
    title = data.get("title", "").strip()
    category = data.get("category", "").strip()
    description = data.get("description", "").strip()
    hourly_rate = float(data.get("hourly_rate") or 0.0)
    experience_years = int(data.get("experience_years") or 1)
    neighborhood = data.get("neighborhood", "Wardha Road").strip()
    availability = data.get("availability", "flexible")
    tags = data.get("tags", "").strip()

    if not title or not category or not description:
        return jsonify({"success": False, "error": "Title, category, and description are required."}), 400

    lat, lng = NEIGHBORHOODS.get(neighborhood, (21.1458, 79.0882))

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO skills (user_id, title, category, description, hourly_rate, experience_years, neighborhood, lat, lng, availability, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, title, category, description, hourly_rate, experience_years, neighborhood, lat, lng, availability, tags))
        skill_id = cursor.lastrowid

    log_activity(user_id, "SKILL_CREATED", f"Created skill: '{title}' in category '{category}'")
    return jsonify({"success": True, "message": "Skill published successfully!", "skill_id": skill_id})


@app.route("/api/skills/<int:skill_id>", methods=["DELETE"])
def delete_skill(skill_id):
    """Delete a skill listing."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "Authentication required."}), 401

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM skills WHERE id = ?", (skill_id,))
        skill = cursor.fetchone()
        if not skill:
            return jsonify({"success": False, "error": "Skill not found."}), 404

        # Allow author or admin
        cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if skill["user_id"] != user_id and user["role"] != "admin":
            return jsonify({"success": False, "error": "Unauthorized action."}), 403

        cursor.execute("DELETE FROM skills WHERE id = ?", (skill_id,))

    log_activity(user_id, "SKILL_DELETED", f"Deleted skill ID {skill_id}")
    return jsonify({"success": True, "message": "Skill removed successfully."})


# -----------------------------------------------------------------------------
# Module 03: Job Posting & Matching Engine (Slide 7, 9 & 11)
# -----------------------------------------------------------------------------
@app.route("/api/jobs", methods=["GET"])
def list_jobs():
    """List service requests / jobs with status and category filtering."""
    category = request.args.get("category", "").strip()
    neighborhood = request.args.get("neighborhood", "").strip()
    status = request.args.get("status", "").strip()
    user_id = request.args.get("user_id", type=int)

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT j.*, u.name as requester_name, u.avatar as requester_avatar, 
               u.rating as requester_rating, u.phone as requester_phone
        FROM jobs j
        JOIN users u ON j.user_id = u.id
        WHERE 1=1
    """
    params = []

    if status:
        query += " AND j.status = ?"
        params.append(status)

    if category:
        query += " AND j.category = ?"
        params.append(category)

    if neighborhood:
        query += " AND j.neighborhood = ?"
        params.append(neighborhood)

    if user_id:
        query += " AND j.user_id = ?"
        params.append(user_id)

    query += " ORDER BY j.created_at DESC"
    cursor.execute(query, params)
    jobs = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return jsonify({"success": True, "count": len(jobs), "jobs": jobs})


@app.route("/api/jobs", methods=["POST"])
def create_job():
    """Create a new community job / service request."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "Please login to post a service request."}), 401

    data = request.get_json() or {}
    title = data.get("title", "").strip()
    category = data.get("category", "").strip()
    description = data.get("description", "").strip()
    budget = float(data.get("budget") or 0.0)
    urgency = data.get("urgency", "medium")
    neighborhood = data.get("neighborhood", "Wardha Road").strip()
    max_distance_km = float(data.get("max_distance_km") or 15.0)

    if not title or not category or not description or budget <= 0:
        return jsonify({"success": False, "error": "Title, category, description, and budget are required."}), 400

    lat, lng = NEIGHBORHOODS.get(neighborhood, (21.1458, 79.0882))

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO jobs (user_id, title, category, description, budget, urgency, neighborhood, lat, lng, max_distance_km)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, title, category, description, budget, urgency, neighborhood, lat, lng, max_distance_km))
        job_id = cursor.lastrowid

    log_activity(user_id, "JOB_POSTED", f"Posted job: '{title}' in {neighborhood} (Budget: INR {budget})")
    return jsonify({"success": True, "message": "Job request posted successfully!", "job_id": job_id})


@app.route("/api/jobs/<int:job_id>/matches")
def get_job_matches(job_id):
    """Run the algorithmic matching engine to suggest best local providers."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    if not job:
        conn.close()
        return jsonify({"success": False, "error": "Job not found."}), 404

    job_dict = dict(job)

    cursor.execute("SELECT * FROM skills WHERE status = 'active'")
    skills_list = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM users WHERE status = 'active'")
    users_dict = {r["id"]: dict(r) for r in cursor.fetchall()}
    conn.close()

    top_matches = find_top_matches_for_job(job_dict, skills_list, users_dict, top_k=10)

    return jsonify({
        "success": True,
        "job": job_dict,
        "match_count": len(top_matches),
        "matches": top_matches
    })


@app.route("/api/jobs/<int:job_id>/status", methods=["PUT"])
def update_job_status(job_id):
    """Update job lifecycle status (open -> in_progress -> completed -> cancelled)."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "Authentication required."}), 401

    data = request.get_json() or {}
    new_status = data.get("status")
    assigned_provider_id = data.get("assigned_provider_id")

    if new_status not in ["open", "in_progress", "completed", "cancelled"]:
        return jsonify({"success": False, "error": "Invalid status."}), 400

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, title FROM jobs WHERE id = ?", (job_id,))
        job = cursor.fetchone()
        if not job:
            return jsonify({"success": False, "error": "Job not found."}), 404

        if assigned_provider_id:
            cursor.execute("""
                UPDATE jobs SET status = ?, assigned_provider_id = ? WHERE id = ?
            """, (new_status, assigned_provider_id, job_id))
            create_notification(assigned_provider_id, "Job Status Update", f"You have been assigned to job: {job['title']}", "#jobs")
        else:
            cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", (new_status, job_id))

    log_activity(user_id, "JOB_STATUS_CHANGE", f"Job ID {job_id} status updated to {new_status}")
    return jsonify({"success": True, "message": f"Job status updated to '{new_status}'."})


# -----------------------------------------------------------------------------
# Module 04: Messaging & Notifications (Slide 7, 9 & 11)
# -----------------------------------------------------------------------------
@app.route("/api/messages/conversations")
def get_conversations():
    """Retrieve all conversations for the active user."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "Authentication required."}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    # Distinct conversation partners
    cursor.execute("""
        SELECT DISTINCT 
            CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END as other_user_id
        FROM messages
        WHERE sender_id = ? OR receiver_id = ?
    """, (user_id, user_id, user_id))
    partners = cursor.fetchall()

    conversations = []
    for p in partners:
        other_id = p["other_user_id"]
        cursor.execute("SELECT * FROM users WHERE id = ?", (other_id,))
        other_user = cursor.fetchone()
        if not other_user:
            continue

        cursor.execute("""
            SELECT * FROM messages
            WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id, other_id, other_id, user_id))
        last_msg = cursor.fetchone()

        cursor.execute("""
            SELECT COUNT(*) as unread FROM messages
            WHERE sender_id = ? AND receiver_id = ? AND is_read = 0
        """, (other_id, user_id))
        unread = cursor.fetchone()["unread"]

        conversations.append({
            "user": dict(other_user),
            "last_message": dict(last_msg) if last_msg else None,
            "unread_count": unread
        })

    conn.close()
    return jsonify({"success": True, "conversations": conversations})


@app.route("/api/messages/thread/<int:other_user_id>")
def get_message_thread(other_user_id):
    """Get chat history with another user and mark received messages as read."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "Authentication required."}), 401

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE messages SET is_read = 1
            WHERE sender_id = ? AND receiver_id = ? AND is_read = 0
        """, (other_user_id, user_id))

        cursor.execute("""
            SELECT m.*, u.name as sender_name, u.avatar as sender_avatar
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE (m.sender_id = ? AND m.receiver_id = ?) OR (m.sender_id = ? AND m.receiver_id = ?)
            ORDER BY m.created_at ASC
        """, (user_id, other_user_id, other_user_id, user_id))
        messages = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT * FROM users WHERE id = ?", (other_user_id,))
        other_user = cursor.fetchone()

    return jsonify({
        "success": True,
        "other_user": dict(other_user) if other_user else None,
        "messages": messages
    })


@app.route("/api/messages", methods=["POST"])
def send_message():
    """Send a direct message to another user."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "Authentication required."}), 401

    data = request.get_json() or {}
    receiver_id = int(data.get("receiver_id") or 0)
    job_id = data.get("job_id")
    content = data.get("content", "").strip()

    if not receiver_id or not content:
        return jsonify({"success": False, "error": "Receiver and message content are required."}), 400

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO messages (sender_id, receiver_id, job_id, content)
            VALUES (?, ?, ?, ?)
        """, (user_id, receiver_id, job_id, content))
        msg_id = cursor.lastrowid

        cursor.execute("SELECT name FROM users WHERE id = ?", (user_id,))
        sender = cursor.fetchone()
        sender_name = sender["name"] if sender else "A community member"

        create_notification(receiver_id, f"New message from {sender_name}", content[:50] + ("..." if len(content) > 50 else ""), "#messages", conn=conn)

    return jsonify({"success": True, "message_id": msg_id, "created_at": datetime.now().isoformat()})


@app.route("/api/notifications")
def get_notifications():
    """Get active user notifications."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "notifications": []})

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 20
    """, (user_id,))
    notifications = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return jsonify({"success": True, "notifications": notifications})


# -----------------------------------------------------------------------------
# Feedback & Ratings (Slide 9 & 11)
# -----------------------------------------------------------------------------
@app.route("/api/reviews", methods=["POST"])
def submit_review():
    """Submit rating and feedback after job completion."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "Authentication required."}), 401

    data = request.get_json() or {}
    job_id = data.get("job_id")
    reviewee_id = int(data.get("reviewee_id") or 0)
    rating = int(data.get("rating") or 5)
    comment = data.get("comment", "").strip()

    if not reviewee_id or rating < 1 or rating > 5:
        return jsonify({"success": False, "error": "Valid reviewee and rating (1-5) required."}), 400

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reviews (job_id, reviewer_id, reviewee_id, rating, comment)
            VALUES (?, ?, ?, ?, ?)
        """, (job_id, user_id, reviewee_id, rating, comment))

        # Recalculate average rating for reviewee
        cursor.execute("""
            SELECT AVG(rating) as avg_r, COUNT(*) as cnt FROM reviews WHERE reviewee_id = ?
        """, (reviewee_id,))
        stats = cursor.fetchone()
        new_rating = round(stats["avg_r"], 1) if stats["avg_r"] else 5.0
        total_reviews = stats["cnt"]

        cursor.execute("""
            UPDATE users SET rating = ?, total_reviews = ? WHERE id = ?
        """, (new_rating, total_reviews, reviewee_id))

    log_activity(user_id, "REVIEW_SUBMITTED", f"Rated user ID {reviewee_id} with {rating} stars.")
    create_notification(reviewee_id, "New Review Received", f"You received a {rating}-star review!", "#reviews")

    return jsonify({"success": True, "message": "Feedback submitted successfully!", "new_rating": new_rating})


# -----------------------------------------------------------------------------
# Module 05: Admin Dashboard & Reports (Slide 7, 11 & 12)
# -----------------------------------------------------------------------------
@app.route("/api/admin/dashboard")
def admin_dashboard():
    """Provide real-time telemetry, KPIs, and recent logs for administrator."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as cnt FROM users")
    total_users = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM skills WHERE status = 'active'")
    total_skills = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM jobs")
    total_jobs = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM jobs WHERE status = 'completed'")
    completed_jobs = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM messages")
    total_messages = cursor.fetchone()["cnt"]

    # Category distribution for skills
    cursor.execute("""
        SELECT category, COUNT(*) as count FROM skills GROUP BY category ORDER BY count DESC LIMIT 6
    """)
    skill_categories = [dict(r) for r in cursor.fetchall()]

    # Users list
    cursor.execute("SELECT id, name, email, role, neighborhood, rating, status, created_at FROM users ORDER BY id ASC")
    users = [dict(r) for r in cursor.fetchall()]

    # Activity logs
    cursor.execute("""
        SELECT l.*, u.name as user_name FROM activity_logs l
        LEFT JOIN users u ON l.user_id = u.id
        ORDER BY l.created_at DESC LIMIT 20
    """)
    logs = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return jsonify({
        "success": True,
        "kpis": {
            "total_users": total_users,
            "total_skills": total_skills,
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "total_messages": total_messages,
            "success_rate": f"{round((completed_jobs / max(total_jobs, 1)) * 100, 1)}%"
        },
        "skill_categories": skill_categories,
        "users": users,
        "logs": logs
    })


@app.route("/api/admin/users/<int:user_id>/status", methods=["PUT"])
def update_user_status(user_id):
    """Suspend or activate a user account."""
    current_uid = session.get("user_id")
    if not current_uid:
        return jsonify({"success": False, "error": "Admin login required."}), 401

    data = request.get_json() or {}
    new_status = data.get("status")
    if new_status not in ["active", "suspended", "pending"]:
        return jsonify({"success": False, "error": "Invalid status."}), 400

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM users WHERE id = ?", (current_uid,))
        admin_check = cursor.fetchone()
        if not admin_check or admin_check["role"] != "admin":
            return jsonify({"success": False, "error": "Only admins can perform this action."}), 403

        cursor.execute("UPDATE users SET status = ? WHERE id = ?", (new_status, user_id))

    log_activity(current_uid, "USER_STATUS_CHANGE", f"Admin updated User ID {user_id} status to {new_status}")
    return jsonify({"success": True, "message": f"User status set to {new_status}."})


@app.route("/api/reports/preview/<report_type>")
def preview_report(report_type):
    """Return JSON preview data for one of the 4 report types."""
    if report_type not in ["user_activity", "skill_demand", "system_usage", "admin_summary"]:
        return jsonify({"success": False, "error": "Invalid report type."}), 400

    conn = get_db_connection()
    try:
        data = get_report_data(conn, report_type)
        return jsonify({"success": True, "report": data})
    finally:
        conn.close()


@app.route("/api/reports/download/<report_type>")
def download_report(report_type):
    """Download report as PDF or CSV file."""
    if report_type not in ["user_activity", "skill_demand", "system_usage", "admin_summary"]:
        return jsonify({"success": False, "error": "Invalid report type."}), 400

    fmt = request.args.get("format", "pdf").lower()
    conn = get_db_connection()

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if fmt == "csv":
            csv_content = generate_csv_report(conn, report_type)
            return Response(
                csv_content,
                mimetype="text/csv",
                headers={"Content-Disposition": f"attachment; filename={report_type}_report_{timestamp}.csv"}
            )
        else:
            # Default to PDF
            pdf_bytes = generate_pdf_report(conn, report_type)
            import io
            return send_file(
                io.BytesIO(pdf_bytes),
                mimetype="application/pdf",
                as_attachment=True,
                download_name=f"{report_type}_report_{timestamp}.pdf"
            )
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG") == "1"
    )
