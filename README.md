# Qualitative Coding Tool — Backend (Flask + SQLite)

This is the backend API for a qualitative coding platform designed for tagging and annotating TikTok videos. It supports project setup, coder progress tracking, autosaving of responses, and final submission of coded entries.

---

## 🚀 Features

- Create and manage coding projects
- Upload CSV datasets for each project
- Track coder progress through videos
- Autosave tag and note drafts per video
- Submit finalized coding responses
- Resume incomplete work (draft recovery)
- Navigate to next/previous/specific videos
- Easily export coded data (planned)

---

## 🛠️ Tech Stack

- Python 3.9+
- Flask
- Flask-SQLAlchemy
- Flask-CORS
- SQLite (file-based database)

---

## 📁 Project Structure

backend/
├── app.py # Main Flask app
├── models.py # SQLAlchemy models (Project, Coder, Result)
├── routes/
│ ├── project_routes.py # Project creation and metadata
│ └── coding_routes.py # Coding session logic
├── data/ # CSV datasets and database file
│ └── database.db
├── storage/ # Optional for future uploads
├── requirements.txt
└── README.md

---

## ⚙️ Setup Instructions

### 1. Clone and navigate into the project

```bash
git clone https://github.com/your-username/your-repo.git
cd your-repo/backend

2. Create a virtual environment and install dependencies
bash
Copy
Edit
python3 -m venv venv
source venv/bin/activate         # On Windows: venv\Scripts\activate
pip install -r requirements.txt

3. Create database and tables
bash
Copy
Edit
mkdir -p data
export FLASK_APP=app.py          # Windows: set FLASK_APP=app.py
flask shell
>>> from app import db
>>> db.create_all()
>>> exit()

🧪 Running the Server
flask run
Server will be available at http://localhost:5000

🔌 Key Endpoints
Projects
POST /api/projects — Create a new project

GET /api/project-info?project=slug — Get project metadata

CSV Data
(Planned) POST /api/upload-data — Upload TikTok dataset CSV

(Planned) GET /api/download-results?project=slug — Export results as CSV

Coding Workflow
GET /api/next-video?project=slug&coder=name

GET /api/previous-video?project=slug&coder=name

GET /api/video-at-index?project=slug&coder=name&index=3

POST /api/save-progress — Autosaves tags/notes as draft

POST /api/submit — Finalizes a result and advances index

📋 Notes
CSV files must be placed in /data and referenced by name when creating a project

Coder progress (progress_index) is tracked per coder and auto-incremented on submission

All tag/response data is stored in the results table and can be exported per project

✅ TODO / Future Features
 File upload endpoint for TikTok CSVs

 CSV download of all submitted results

 Admin dashboard stats route

 Optional authentication
