# AutoReport AI – Autonomous Dashboard Generation Agent

Upload a CSV or Excel file. Six AI agents run in sequence to clean, analyze,
generate KPIs, build interactive charts, produce a PDF report, and let you
chat with the dataset — all from a clean React + Flask interface.

---

## ✨ Features

| # | Agent | What it does |
|---|-------|--------------|
| 1 | **Data Cleaning Agent**      | Fills missing values (mean / mode), removes duplicates & empty rows, coerces types |
| 2 | **Analysis Agent**           | Counts, dtypes, missing values, statistical summary, correlation matrix |
| 3 | **KPI Generation Agent**     | Auto-generates KPIs from every numeric column (sum, avg, min, max) |
| 4 | **Dashboard Generation Agent** | Builds Bar, Line, Pie, and Histogram charts with Plotly |
| 5 | **Report Generation Agent**  | Renders a professional PDF report using ReportLab |
| 6 | **Chatbot Agent**            | LangChain + OpenAI assistant — answers **only** about the uploaded dataset |

---

## 📁 Project Structure

```
AutoReport-AI/
├── frontend/
│   ├── package.json
│   ├── public/
│   │   └── index.html
│   └── src/
│       ├── App.jsx
│       ├── index.js
│       ├── api/
│       │   └── client.js
│       ├── components/
│       │   ├── Navbar.jsx
│       │   ├── UploadSection.jsx
│       │   ├── ProcessControls.jsx
│       │   ├── ProcessingStatus.jsx
│       │   ├── KpiCards.jsx
│       │   ├── DashboardCharts.jsx
│       │   ├── ReportDownload.jsx
│       │   └── Chatbot.jsx
│       └── styles/
│           └── global.css
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── database.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── data_cleaning_agent.py
│   │   ├── analysis_agent.py
│   │   ├── kpi_agent.py
│   │   ├── dashboard_agent.py
│   │   ├── report_agent.py
│   │   └── chatbot_agent.py
│   ├── uploads/        ← uploaded datasets land here
│   └── reports/        ← generated PDFs land here
├── requirements.txt    (root - symlink/copy of backend/requirements.txt)
└── README.md
```

---

## 🛠 Requirements

- **Node.js** 18+ and **npm** (for the frontend)
- **Python** 3.10+
- **MySQL** 8.x (optional — the app falls back to SQLite if MySQL is not configured)
- An **OpenAI** API key for the chatbot

---

## ⚙️ Installation

### 1. Clone & enter the project

```bash
git clone <your-repo-url> AutoReport-AI
cd AutoReport-AI
```

### 2. Backend setup

```bash
cd backend

# (recommended) create a virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Frontend setup

```bash
cd ../frontend
npm install
```

---

## 🔐 Configuration (OpenAI & MySQL)

Create `backend/.env` (copy from `backend/.env.example`):

```dotenv
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-3.5-turbo

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DB=autoreport_ai

SECRET_KEY=autoreport-ai-dev-secret
```

### MySQL setup (optional)

If you want to use MySQL instead of the default SQLite fallback:

```sql
CREATE DATABASE autoreport_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Tables are auto-created the first time the Flask app starts
(`db.create_all()` in `app.py`).

### OpenAI setup

1. Create an API key at <https://platform.openai.com/api-keys>
2. Paste it into `OPENAI_API_KEY` in `backend/.env`
3. Make sure your account has credit. The chatbot uses `gpt-3.5-turbo`
   by default — change `OPENAI_MODEL` to `gpt-4o-mini` etc. if you prefer.

---

## 🚀 Running the App

Open two terminals.

### Terminal 1 — Backend (Flask)

```bash
cd backend
# activate venv if you created one
python app.py
```

The API runs on **http://localhost:5000**.

### Terminal 2 — Frontend (React)

```bash
cd frontend
npm start
```

The UI runs on **http://localhost:3000**. The React dev server proxies
API calls to the Flask backend automatically (see `package.json`).

---

## 🧪 Trying It Out

1. Open <http://localhost:3000>.
2. Drag-and-drop a CSV / Excel file into the upload zone.
3. Click **🚀 Run AI Agents**.
4. Watch the six agents tick through in order.
5. Explore KPIs, charts, download the PDF, then chat with the dataset.

A good starter dataset is the classic *Titanic* or *Iris* CSV — both work
out of the box.

---

## 📡 API Reference

| Endpoint        | Method | Description |
|-----------------|--------|-------------|
| `/upload`       | POST   | Upload a CSV/Excel file (multipart form-data) |
| `/process`      | POST   | Run the full agent pipeline for a given `file_id` |
| `/dashboard`    | GET    | Return cached KPIs + chart figures |
| `/report`       | GET    | Return the generated PDF metadata |
| `/chat`         | POST   | Ask the chatbot a question about a file |
| `/reports/<fn>` | GET    | Serve a generated PDF |
| `/health`       | GET    | Service health check |
| `/history`      | GET    | Recent pipeline runs |

---

## 🧯 Troubleshooting

- **`OpenAI API key invalid`** — verify `OPENAI_API_KEY` in `backend/.env`,
  then restart Flask.
- **`pymysql.err.OperationalError`** — MySQL isn't reachable. Either start
  MySQL or unset `MYSQL_USER` in `.env` to fall back to SQLite.
- **Charts look empty** — your dataset may be missing a numeric column.
  The dashboard agent needs at least one numeric and (for the pie) one
  categorical column to render all four charts.
- **PDF report missing images** — make sure `kaleido` is installed
  (`pip install -r backend/requirements.txt`). It's required to export
  Plotly figures to PNG for ReportLab.

---

## 📸 Screenshots

_Add screenshots of the running app here once you have them._

| Upload | Dashboard |
|--------|-----------|
| _placeholder_ | _placeholder_ |

| KPIs | Chatbot |
|------|---------|
| _placeholder_ | _placeholder_ |

---

## 🧾 License

MIT — use freely, attribution appreciated.