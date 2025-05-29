# Provider Microservice

## Overview
Brief description of the microservice: Manages provider information (companies, services, branches) via a REST API. Built with Python, FastAPI, and DynamoDB.

## Features
- CRUD operations for providers.
- Filter providers by city and service.
- Retrieve provider name by ID.
- Automatic API documentation via Swagger UI.

## Project Structure
```
.
├── app/                  # Main application code
│   ├── __init__.py
│   ├── config.py         # Application settings
│   ├── main.py           # FastAPI application entry point
│   ├── models/           # Pydantic models
│   │   ├── __init__.py
│   │   └── provider.py   # Defines Provider, Branch, etc.
│   ├── routers/          # API routers (controllers)
│   │   ├── __init__.py
│   │   └── provider_router.py
│   └── services/         # Business logic and external service integrations
│       ├── __init__.py
│       └── dynamodb_service.py
├── .env.example          # Example environment variables
├── .gitignore            # Git ignore file
├── README.md             # This file
├── requirements.txt      # Python dependencies
└── sonar-project.properties # SonarQube configuration (placeholder)
```

### Key Data Model Update (Branch)
The `Branch` model, as defined in `app/models/provider.py` and used in provider data, now includes a dedicated `city` field:
```json
{
  "name": "Downtown Office",
  "address": "100 Business Rd",
  "city": "Metropolis",
  "phone": "555-0100",
  "manager_name": "Alice Wonderland",
  "email": "alice.wonderland@example.com"
}
```

## Prerequisites
- Python 3.8+
- Pip (Python package installer)
- An AWS account (if deploying to AWS DynamoDB)
- Docker (optional, for running DynamoDB Local)

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Create and activate a virtual environment** (recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    Copy `.env.example` to a new file named `.env` and update the values:
    ```bash
    cp .env.example .env
    ```
    Edit `.env` with your specific configurations:
    ```
    # AWS Configuration (Required if not using DynamoDB Local or IAM roles)
    # AWS_REGION_NAME=your-aws-region

    # DynamoDB Configuration
    DYNAMODB_TABLE_NAME=providers # Or your desired table name

    # For local development with DynamoDB Local (Uncomment and configure if using)
    # DYNAMODB_ENDPOINT_URL=http://localhost:8000
    # AWS_ACCESS_KEY_ID=your_dummy_access_key # Not needed if IAM configured
    # AWS_SECRET_ACCESS_KEY=your_dummy_secret_key # Not needed if IAM configured
    ```
    Ensure your `.env` file is correctly configured. The application uses these settings (via `app/config.py`) to establish the connection to DynamoDB. The service initialization has been made robust to use these settings.

## Running DynamoDB Locally (Optional)
If you prefer to develop locally without connecting to AWS, you can use DynamoDB Local.

1.  **Using Docker:**
    ```bash
    docker run -d -p 8000:8000 amazon/dynamodb-local
    ```
    Ensure your `.env` file has `DYNAMODB_ENDPOINT_URL=http://localhost:8000`.

2.  **Create the table (if not handled by application startup logic):**
    You might need to create the table manually using AWS CLI against your local instance if the application doesn't do it automatically.
    ```bash
    aws dynamodb create-table \
        --table-name your_table_name_from_env \
        --attribute-definitions AttributeName=id,AttributeType=S \
        --key-schema AttributeName=id,KeyType=HASH \
        --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
        --endpoint-url http://localhost:8000
    ```
    *(Note: The `DynamoDBService` includes a commented-out example to create the table if it doesn't exist when using a local endpoint. This might need to be enabled or adapted based on final service implementation.)*

## Running the Application
```bash
uvicorn app.main:app --reload
```
The application will be available at `http://127.0.0.1:8000`.

## API Documentation (Swagger UI)
Once the application is running, API documentation (Swagger UI) is available at:
`http://127.0.0.1:8000/docs`

And alternative ReDoc documentation at:
`http://127.0.0.1:8000/redoc`

## Endpoints
Brief overview of main endpoints (details available in Swagger UI):
- `POST /providers/`: Create a new provider.
- `GET /providers/{provider_id}`: Get a provider by their ID.
- `PUT /providers/{provider_id}`: Update an existing provider.
- `DELETE /providers/{provider_id}`: Delete a provider.
- `GET /providers/`: Filter providers by branch city and service (e.g., `/providers/?city=Anytown&service=Consulting`). The city filter matches against the `city` field within each provider's branches (case-insensitive).
- `GET /providers/{provider_id}/name`: Get only the name of a provider by ID.

## SonarQube
This project is set up for SonarQube analysis. The `sonar-project.properties` file contains the basic configuration.
To run an analysis, configure your SonarQube server and use the SonarScanner.

## To-Do / Potential Enhancements
- Implement comprehensive unit and integration tests.
- For `get_providers_by_city_and_service`, consider using a DynamoDB Global Secondary Index (GSI) to optimize queries by `service`. Filtering by `branch.city` is currently done client-side after retrieving service-matched providers; a more advanced GSI strategy (e.g., on a denormalized city field at the top level, or a composite index) might be needed for very large datasets if city-based querying performance needs to be improved at the DB level, though this is complex with nested branch lists.
- More sophisticated error handling and logging.
- Security enhancements (e.g., authentication, authorization).
- CI/CD pipeline setup.