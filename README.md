# RecoverAI

RecoverAI is an intelligent platform designed for automated recovery operations and workflows.

## Project Structure

```text
recover-ai/
├── backend/          # Python / FastAPI backend service
├── frontend/         # React + TypeScript + Vite frontend application
├── tests/            # Test suites and test configuration
├── docs/             # Project and architecture documentation
├── README.md         # Project overview and getting started guide
└── .gitignore        # Git ignore rules for Python, Node, and environments
```

## Tech Stack

- **Backend**: Python 3, [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/)
- **Frontend**: [React](https://react.dev/), [TypeScript](https://www.typescriptlang.org/), [Vite](https://vitejs.dev/)
- **Database**: PostgreSQL *(planned)*

## Getting Started

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On Linux/macOS:
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
