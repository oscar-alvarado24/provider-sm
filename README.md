# Provider Microservice ☁️

## Overview

This microservice manages provider information, including companies, their services, and branches, through a REST API. It's built using Python, FastAPI, and leverages AWS DynamoDB for data persistence. The service provides robust CRUD operations, filtering capabilities, and integrates with AWS Cognito for authentication.

## Features ✨

*   **CRUD Operations:** Full Create, Read, Update, and Delete capabilities for providers.
*   **Advanced Filtering:** Filter providers by branch city and the services they offer.
*   **Provider Retrieval:** Efficiently retrieve provider names or full details by their unique ID.
*   **Automatic API Documentation:** Interactive Swagger UI and ReDoc available for easy API exploration.
*   **Authentication:** Secure API endpoints using JWT authentication with AWS Cognito integration.
*   **Dynamic CORS Configuration:** Configurable Cross-Origin Resource Sharing policies.
*   **Environment Configuration:** Flexible settings management using Pydantic-Settings.
*   **Robust Error Handling:** Custom exceptions for clear error management.
*   **Containerization:** Dockerfile provided for easy deployment.

## Tech Stack 🛠️

*   **Language:** Python 3.11
*   **Framework:** FastAPI
*   **Database:** AWS DynamoDB
*   **Containerization:** Docker
*   **Authentication:** AWS Cognito (via JOSE and JWT validation)
*   **Dependencies:** Uvicorn, Boto3, Pydantic, Pydantic-Settings, Python-dotenv, Requests, cryptography

## Project Structure 📁

```
.
├── app/
│   ├── __init__.py
│   ├── core/
│   │   ├── config.py       # Application settings
│   │   └── exception/      # Custom exceptions
│   ├── entities/
│   │   └── provider.py     # Data models (Company, Branch, Service, Provider)
│   ├── helper/
│   │   ├── branch_data.py
│   │   ├── create_dict_provider.py
│   │   ├── create_provider.py
│   │   ├── crypto.py         # Encryption/Decryption service
│   │   └── validations.py    # Data validation utilities
│   ├── main.py             # FastAPI application entry point
│   ├── middlewares/
│   │   └── auth/
│   │       ├── config.py
│   │       ├── dependencies.py
│   │       └── jwt_validator.py
│   ├── repositories/
│   │   ├── connetion.py    # DynamoDB connection handler
│   │   └── provider_repository.py # DynamoDB interaction logic
│   ├── routers/
│   │   └── provider_router.py # API routes for providers
│   └── services/
│       └── dynamodb_service.py # Business logic layer
├── .env.example          # Example environment variables
├── .gitignore            # Git ignore file
├── Dockerfile            # Docker build configuration
├── README.md             # This file
├── requirements.txt      # Python dependencies
└── sonar-project.properties # SonarQube configuration (placeholder)
```

## Prerequisites 📋

*   **Python:** Version 3.8+
*   **Pip:** Python package installer
*   **AWS Account:** Required if deploying to AWS DynamoDB (or for local DynamoDB setup if not using Docker).
*   **Docker:** Recommended for running DynamoDB Local and containerizing the application.

## Setup and Installation 🚀

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/oscar-alvarado24/provider-sm.git
    cd provider-sm
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

4.  **Configure Environment Variables:**
    Copy `.env.example` to `.env` and fill in your specific settings:
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file with your configurations. Key variables include:
    *   `AWS_REGION_NAME`: Your AWS region (e.g., `us-east-1`).
    *   `DYNAMODB_TABLE_NAME`: The name of your DynamoDB table (defaults to `provider`).
    *   `DYNAMODB_ENDPOINT_URL`: Set this to `http://localhost:8000` if using DynamoDB Local.
    *   `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`: For AWS credentials, if not using IAM roles or environment variables.
    *   `AWS_DYNAMO_ROLE`: ARN of the IAM role to assume for accessing DynamoDB (useful in production).
    *   `SECRET_KEY`: A strong secret key for encryption/decryption (required for `CryptoService`).
    *   `ENVIRONMENT`: Set to `local`, `production`, etc., to control connection behavior.
    *   `COGNITO_USER_POOL_ID`, `COGNITO_APP_CLIENT_ID`: For Cognito authentication.

## Running DynamoDB Locally (Optional) 🌍

If you prefer local development without connecting to AWS DynamoDB, you can use DynamoDB Local. The `Dockerfile` and `repositories/connetion.py` are configured to support this.

1.  **Using Docker:**
    ```bash
    docker run -d -p 8000:8000 amazon/dynamodb-local
    ```
    Ensure your `.env` file has `DYNAMODB_ENDPOINT_URL=http://localhost:8000` and `ENVIRONMENT=local`.

2.  **Create the table (if not handled by application startup logic):**
    You might need to create the table manually using the AWS CLI against your local instance if the application doesn't handle it automatically. The `ProviderRepository` expects a table with a `company_id` (String) as the partition key and `SK` (String) as the sort key, along with specific Global Secondary Indexes (GSIs) like `ServiceCityLookup` and `BranchDataLookup` for efficient querying.
    ```bash
    # Example for creating the table with basic setup
    aws dynamodb create-table \
        --table-name providers \
        --attribute-definitions AttributeName=company_id,AttributeType=S AttributeName=SK,AttributeType=S \
        --key-schema AttributeName=company_id,KeyType=HASH AttributeName=SK,KeyType=RANGE \
        --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
        --endpoint-url http://localhost:8000
    ```
    *(Note: The `DynamoDBService` and `ProviderRepository` contain logic for interacting with DynamoDB and may require specific table structures and indexes for optimal performance.)*

## Running the Application 🚀

### Development Server

For local development, you can run the FastAPI application using `uvicorn`:

```bash
uvicorn app.main:app --reload --port 8050
```

The application will be available at `http://127.0.0.1:8050`.

### Production Deployment (using Docker)

Build the Docker image and run the container:

```bash
# Build the image
docker build -t provider-sm .

# Run the container
docker run -d -p 8050:8050 --name provider-microservice provider-sm
```

The `Dockerfile` is optimized for production with a multi-stage build, non-root user, and a robust health check.

## API Documentation (Swagger UI) 📚

Once the application is running, interactive API documentation is available at:

*   **Swagger UI:** `http://127.0.0.1:8050/docs`
*   **ReDoc:** `http://127.0.0.1:8050/redoc`

These interfaces allow you to explore all available endpoints, their request/response models, and execute API calls directly.

## API Endpoints 🌐

Here's a brief overview of the main API endpoints:

*   **`POST /providers/`**: Create a new provider with company, branches, and services details.
*   **`GET /providers/company/{company_id}`**: Retrieve a full provider's details (company, branches, services) by their `company_id`.
*   **`GET /providers/branches`**: Retrieve branch information. Accepts a comma-separated, encrypted string of `company_id | branch_id` pairs.
*   **`PUT /providers/update-company/{company_id}`**: Update existing company information for a provider.
*   **`GET /health`**: Health check endpoint to verify service availability.

*(Note: Endpoints related to filtering by service and city, or deleting providers, might exist but are not explicitly detailed in the main router file provided. Refer to `provider_router.py` and `provider_repository.py` for complete implementation details.)*

## Authentication 🔐

This service uses JWT authentication, integrated with AWS Cognito. API endpoints are protected and require a valid JWT token in the `Authorization` header (e.g., `Authorization: Bearer <your_token>`). The `app/middlewares/auth` directory contains the logic for token validation and group authorization (`require_groups` dependency).

## SonarQube Analysis 📊

This project is configured for SonarQube analysis. The `sonar-project.properties` file contains the necessary settings. You can run a code quality and security analysis by configuring your SonarQube server and using the SonarScanner.

## Contributing 🤝

Contributions are welcome! Please follow these steps:

1.  Fork the repository.
2.  Create a new branch for your feature (`git checkout -b feature/AmazingFeature`).
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

Please ensure your code adheres to the project's coding standards and includes tests where appropriate.

## License 📜

No license information was found in the repository. Please refer to the project owner for licensing details.

## Important Links 🔗

*   **Repository:** [https://github.com/oscar-alvarado24/provider-sm](https://github.com/oscar-alvarado24/provider-sm)
*   **Author:** oscar-alvarado24

--- 

## Footer 🌟

© 2024 [Provider Microservice](https://github.com/oscar-alvarado24/provider-sm). All rights reserved.

Made with ❤️ by [oscar-alvarado24](https://github.com/oscar-alvarado24).

[Fork me on GitHub](https://github.com/oscar-alvarado24/provider-sm) | [Star me on GitHub](https://github.com/oscar-alvarado24/provider-sm/stargazers) | [Report an issue](https://github.com/oscar-alvarado24/provider-sm/issues)


---
**<p align="center">Generated by [ReadmeCodeGen](https://www.readmecodegen.com/)</p>**