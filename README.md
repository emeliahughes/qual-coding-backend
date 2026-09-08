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
- Restrict projects to individually authorized researcher accounts
- Bind researcher accounts to approved project and coder identities
- Navigate to next/previous/specific videos
- **NEW:** Export coded data to CSV format
- **NEW:** Comprehensive project management
- **NEW:** Support for excluded videos and status tracking

---

## 🛠️ Tech Stack

- Python 3.9+
- Flask
- Flask-SQLAlchemy
- Flask-CORS
- SQLite (file-based database)

---

## 📁 Project Structure

```
backend/
├── app.py                    # Main Flask app
├── models.py                 # SQLAlchemy models (Project, Coder, Result)
├── routes/
│   ├── project_routes.py     # Project creation and metadata
│   ├── coding_routes.py      # Coding session logic
│   └── utils.py              # Utility functions
├── data/                     # CSV datasets and database file
│   └── database.db
├── uploads/                  # File upload storage
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup Instructions

### 1. Clone and navigate into the project

```bash
git clone https://github.com/your-username/your-repo.git
cd your-repo/qual-coding-backend
```

### 2. Create a virtual environment and install dependencies

```bash
python3 -m venv venv
source venv/bin/activate         # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Create database and tables

```bash
mkdir -p data
export FLASK_APP=app.py          # Windows: set FLASK_APP=app.py
flask shell
>>> from app import db
>>> db.create_all()
>>> exit()
```

For a private deployment, create the authentication tables and first administrator using the instructions in `AUTH_DEPLOYMENT.md`.

### 4. Run the server

```bash
flask run --host=0.0.0.0 --port=5001
Server will be available at http://127.0.0.1:5001
```

---

## 🔌 Key Endpoints

### Projects
- `POST /api/projects` — Create a new project
- `GET /api/projects` — List all projects
- `GET /api/project-info?project=slug` — Get project metadata

### Authentication
- `POST /api/auth/login` — Start an authorized researcher session
- `POST /api/auth/logout` — End the current session
- `GET /api/auth/me` — Return the current account and CSRF token
- `POST /api/auth/change-password` — Replace the current password
- `GET/POST/PUT /api/admin/users` — Administrator-managed accounts and project access

### CSV Data
- `POST /api/upload-data` — Upload TikTok dataset CSV
- `GET /api/download-results?project=slug&format=text` — Export results as CSV

### Coding Workflow
- `GET /api/next-video?project=slug&coder=name` — Get next video for coder
- `GET /api/previous-video?project=slug&coder=name` — Get previous video for coder
- `GET /api/video-at-index?project=slug&coder=name&index=3` — Get specific video
- `POST /api/save-progress` — Autosaves tags/notes as draft
- `POST /api/submit` — Finalizes a result and advances index

---

## 📊 Database Schema

### Projects
- `id` (Primary Key)
- `slug` (Unique identifier)
- `name` (Project name)
- `codebook` (JSON coding schema)
- `video_count` (Number of videos)
- `created_at` (Timestamp)

### Results
- `id` (Primary Key)
- `project_id` (Foreign Key to Projects)
- `coder_id` (Foreign Key to Coders)
- `video_id` (Video identifier)
- `categories` (Coded categories and tags)
- `notes` (Coder notes)
- `timestamp` (Submission time)
- `status` (submitted/saved/excluded)
- `excluded` (Boolean flag)

### Coders
- `id` (Primary Key)
- `name` (Coder name)
- `project_id` (Foreign Key to Projects)
- `progress_index` (Current video position)

---

## 📋 Notes

- CSV files are uploaded through the frontend and stored in the uploads directory
- Coder progress (progress_index) is tracked per coder and auto-incremented on submission
- All tag/response data is stored in the results table and can be exported per project
- Support for video exclusion with status tracking
- Results can be exported in CSV format with comprehensive metadata

---

## ✅ TODO / Future Features

### Completed ✅
- [x] File upload endpoint for TikTok CSVs
- [x] CSV download of all submitted results
- [x] Project creation and management
- [x] Coder progress tracking
- [x] Autosave functionality
- [x] Video navigation (next/previous/specific)
- [x] Support for excluded videos
- [x] Comprehensive project metadata

### In Progress 🔄
- [ ] Admin dashboard stats route
- [ ] Optional authentication
- [ ] Large dataset pagination support
- [ ] Advanced filtering and search capabilities

### Planned 📋
- [ ] User management and permissions
- [ ] API rate limiting
- [ ] Data validation and sanitization
- [ ] Backup and restore functionality

---

## 🔧 Development

### Running Tests
```bash
python -m pytest tests/
```

### Database Reset
```bash
python reset_db.py
```

### Creating Test Data
```bash
python create_realistic_test_data.py
```

---

## 🐛 Known Issues

- Large datasets may cause memory issues (pagination needed)
- No authentication/authorization system
- Limited error handling for malformed CSV files
- No automatic backup system
