# Mathematix-Back

## Introduction
Mathematix-Back is the backend component of the Mathematix application, designed to support interactive learning and teaching of mathematics. This backend service is built using Flask, a lightweight WSGI web application framework in Python. The project is structured to facilitate easy development, testing, and deployment of educational tools and content.

## Features
- RESTful API for managing educational content.
- Support for various mathematical unit tests.
- Integration with databases for storing user data and educational content.
- Built-in acceptance and unit testing.

## Getting Started

### Prerequisites
- Python 3.x
- Flask

### Installation
1. Clone the repository to your local machine.
2. Navigate to the project directory.
3. Install the required dependencies using pip:
    ```
    pip install -r requirements.txt
    ```
4. Initialize the database (if necessary).

### Running the Application
To start the server, run the following command from the project root directory:
```
python flaskProject/app.py
```
The server will start, and you can access the API endpoints as defined in the application.

## Project Structure
- `.gitignore`: Specifies intentionally untracked files to ignore.
- `.idea`: IDE-specific settings for JetBrains PyCharm.
- `diagram back`: Contains the architectural diagrams of the backend.
- `flaskProject`: The main project directory containing the Flask application and tests.
  - `MathematiXLoadTests.jmx`: Load testing script.
  - `Tests`: Directory containing acceptance and unit tests.
  - `app.py`: The entry point to the Flask application.
  - `dbtest.sqlite`: SQLite database for testing purposes.

## Testing
The project includes a suite of acceptance and unit tests to ensure the reliability and integrity of the application. To run the tests, navigate to the `flaskProject/Tests` directory and execute the test scripts.
