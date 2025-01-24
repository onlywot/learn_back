# FastAPI Project

This is a FastAPI-based platform designed for learning foreign languages. The main goal of the project is to create an easy-to-use tool for selecting a language and improving skills through different learning modes. The application supports multiple languages, including Russian, English, and French, and provides a variety of educational features.

## Features

- **Vocabulary Learning**: Study words in various modes, including flashcards, quizzes, and more.
- **Sentence Construction**: Learn how to construct sentences and practice grammar.
- **Grammar Lessons**: Focused lessons on grammar rules and structures.
- **Parts of Speech**: Words are categorized by parts of speech (nouns, verbs, adjectives, etc.) to allow more targeted learning.
- **Real-time Competition**: Compete with other users in real-time to test your knowledge and improve your skills.
- **User Profiles**: Track your learning progress, achievements, and statistics.
- **Multilingual Support**: The platform supports several languages.
- **Simple Navigation**: An easy-to-use interface to keep users focused on learning without distractions.

## Installation

### Prerequisites

- Python 3.9 or higher
- PostgreSQL
- Redis (optional for caching)
- Docker

### Steps to Set Up

1. Clone the repository:

   ```bash
   git clone https://github.com/regxb/fastapi_project.git
   cd fastapi_project
---
2. To configure the application, create a `.env` file in the root directory based on the `.env_example` file.
---
3. Build and run the Docker containers:
    
    ```bash
    docker-compose up --build
---
4. Start the FastAPI server:
    ```bash
   uvicorn app.main:app --reload