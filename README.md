# 🎓 Edvora Study Companion

**An AI-powered learning platform designed to make studying more personalized, interactive, and effective.**

Edvora Study Companion helps learners organize course materials, interact with an AI tutor, practice questions, prepare for assessments, and track their learning progress through a unified study experience.

---

## 📌 Overview

Studying effectively requires more than reading notes. Learners need explanations, practice, feedback, and a clear understanding of their progress.

Edvora Study Companion brings these capabilities together in one platform, combining course management, AI-assisted learning, customizable practice sessions, and progress tracking.

## ✨ Features

### 🤖 AI Tutor

* Interactive tutoring experiences for course-related learning.
* Tutor sessions designed to support understanding and revision.
* Course-aware learning workflows.

### 📚 Course & Study Materials

* Create and organize courses.
* Manage uploaded learning materials.
* Preview course materials within the application.
* Support for PowerPoint and video material processing.

### 📝 Practice & Assessments

* Practice questions and assessment workflows.
* Customizable practice sessions.
* Adaptive practice experiences.
* Mock test and assessment interfaces.
* Review-oriented learning workflows.

### 📊 Learning Progress

* Course progress tracking.
* Course mastery insights.
* Identification of topics that may need additional attention.
* Dashboard recommendations to help learners decide what to study next.

### ⚙️ Settings & User Experience

* Dedicated settings interface.
* Course-focused navigation and study workflows.
* Dashboard and workspace experiences designed to keep learning activities organized.

---

## 🛠️ Technology Stack

The repository contains separate backend and frontend applications.

| Component             | Technology                                    |
| --------------------- | --------------------------------------------- |
| Backend               | Python                                        |
| Backend API framework | FastAPI                                       |
| Database migrations   | Alembic                                       |
| Frontend              | React                                         |
| Frontend tooling      | Node.js and npm                               |
| Automated testing     | Backend, frontend, and end-to-end test suites |

Additional libraries and integrations are defined in the backend requirements and frontend package configuration.

---

## 📂 Project Structure

```text
Edvora_StudyCompanion/
├── backend/
│   ├── alembic/             # Database migration configuration
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/      # API route handlers
│   │   ├── db/              # Database configuration
│   │   ├── schemas/         # API data schemas
│   │   └── services/        # Application and learning services
│   ├── requirements.txt     # Python dependencies
│   └── ...
├── frontend/
│   ├── e2e/                 # End-to-end tests
│   ├── src/
│   │   ├── api/             # Frontend API clients
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # Application pages
│   │   └── ...
│   ├── test/                # Frontend tests
│   └── package.json         # Frontend dependencies and scripts
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

Install the following tools before setting up the project:

* Git
* Python version compatible with the backend dependencies
* Node.js and npm
* A configured database supported by the project's backend configuration
* Any required AI provider credentials or external service credentials

Check the repository configuration for the exact required versions and environment variables.

### 1. Clone the Repository

```bash
git clone https://github.com/rachitpandya18-source/Edvora_StudyCompanion.git
cd Edvora_StudyCompanion
```

### 2. Set Up the Backend

Open a terminal in the project root.

Create and activate a Python virtual environment:

**Windows PowerShell**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the backend dependencies:

```powershell
python -m pip install -r requirements.txt
```

Configure the backend environment variables using the variables required by the application's configuration.

Start the backend using the project's configured application entry point. For example, if the application exposes `app.main:app`:

```powershell
uvicorn app.main:app --reload
```

If this entry point is correct for your local configuration, the API will generally be available at:

* API base: `http://127.0.0.1:8000`
* Swagger documentation: `http://127.0.0.1:8000/docs`

**Note:** Confirm the application entry point, database setup, and required environment variables before running the backend.

### 3. Set Up the Frontend

Open a second PowerShell terminal:

```powershell
cd frontend
npm install
```

Configure the frontend environment variables required by the project.

Check the scripts defined in `frontend/package.json` and start the development server using the configured command. If the project defines the standard Vite development script, use:

```powershell
npm run dev
```

Open the local URL printed in the terminal.

---

## 🧪 Testing

Edvora Study Companion includes backend, frontend, and end-to-end tests.

### Backend Tests

From the backend directory, activate the virtual environment and run the appropriate test command configured for the project.

If the project uses pytest:

```powershell
python -m pytest
```

### Frontend Tests

From the frontend directory, inspect the available scripts:

```powershell
npm run
```

Run the relevant test script listed in `package.json`.

### End-to-End Tests

Review the configured end-to-end testing framework and scripts before running the E2E suite.

Test results depend on the configured database, environment variables, external services, and application state.

---

## 🔐 Environment Variables & Security

The application may require database settings, authentication configuration, and AI or external service credentials.

* Configure secrets in local environment files as required by the application.
* Never commit API keys, passwords, access tokens, or production credentials.
* Keep `.env` files out of version control.
* Use example environment files containing placeholder values when documenting configuration.
* Validate environment configuration before starting the application.

---

## 🗺️ Development Workflow

Contributions should follow the repository's branch and review requirements.

1. Create a feature branch.
2. Implement and test your changes.
3. Review the changes before committing.
4. Push the feature branch.
5. Open a Pull Request against `main`.
6. Address review feedback and required checks.

Direct pushes to `main` may be blocked by repository rules.

---

## 🎯 Project Goals

Edvora Study Companion aims to make learning more structured and accessible by bringing together:

* Personalized learning support.
* Organized course materials.
* Interactive practice and assessments.
* Progress visibility.
* Focused revision workflows.

---

## 🤝 Contributing

Contributions, bug reports, and improvement suggestions are welcome through the repository's issue and pull request workflows.

Before submitting a Pull Request, ensure your changes are tested and do not include sensitive configuration or credentials.

---

## 📄 License

Check the repository for its applicable license before redistributing or reusing this project.

---

**Built to help learners study smarter, practice better, and understand their progress.** 🚀
