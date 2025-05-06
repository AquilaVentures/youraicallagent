# FastAPI Cron Job App

A FastAPI application that uses APScheduler to perform recurring background tasks, including fetching data from an external source and initiating/monitoring phone calls via a VAPI service. Data is persisted in MongoDB.

## Prerequisites

* Python 3.10+
* MongoDB instance (local or Atlas)
* VAPI account credentials (API key, assistant ID, phone number ID)

## Installation

Clone the repository:

```bash
git clone <your-repo-url>
cd <your-repo-directory>
```

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.\.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

# Configuration

Set the following environment variables in .env:

```bash
APP_NAME="FastAPI Cron Job App"
DEBUG=False
VAPI_API_KEY=<your_vapi_api_key>
VAPI_BASE_URL=https://api.voiceapi.com
VAPI_ASSISTANT_ID=<your_assistant_id>
VAPI_PHONE_NUMBER_ID=<your_phone_number_id>
MONGO_DB_URL=mongodb://username:password@host:port/dbname
DATA_SOURCE_URL=https://api.example.com/data
# Optional overrides
MONGO_DATABASE_NAME=earlybirds
MONGO_COLLECTION_NAME=fetched_clients
```

## Running the Application

Local Development

```bash
uvicorn app.main:app --reload
```

The API will be available at http://127.0.0.1:8000.

## Deployment

The included Procfile and `runtime.txt` make this project ready for platforms like Heroku:

Procfile:

```bash
web: uvicorn app.main:app --host=0.0.0.0 --port=${PORT:-8000}
```

## Scheduled Jobs

The application defines two recurring jobs using APScheduler:

**Fetch Job** (run_fetch_job)
Fetch data from DATA_SOURCE_URL and save new items to MongoDB.

**Call Job** (run_call_job)
Initiate calls for clients without prior calls
Check status of pending calls and update call history

Both jobs start automatically at application startup and shut down gracefully on shutdown.

## Project structure

```bash
├── app
│   ├── api               # API routers (optional)
│   ├── core
│   │   └── config.py     # Application settings via Pydantic
│   ├── services          # DataFetcher, MongoService, VAPI service
│   ├── tasks             # APScheduler job definitions
│   └── main.py           # FastAPI app & scheduler lifecycle
├── requirements.txt      # Python dependencies
├── Procfile              # Deployment entry for Heroku
├── runtime.txt           # Python runtime for deployment
└── README.md             # Project documentation (this file)
```

## Future Roadmap

The following enhancements and features are planned for future releases:

* Dashboard-Based Scheduling: Implement an admin dashboard to dynamically configure job intervals without code changes.
* Advanced Call Retry Logic: Allow configuration of retry counts and delays for unanswered calls (including custom handling for the initial call).
* Sales Script Workflow: Design a clearer VAPI conversation flow tailored to the sales script, with decision branches and variable prompts.
