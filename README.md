# Gemini Chatbot API (EquityLens AI)

An AI-powered financial assistant and chatbot API that leverages the Google GenAI (Gemini) models alongside comprehensive financial data providers to offer market insights, technical/fundamental analysis, and portfolio metrics.

## Features

- **Gemini Chatbot API**: A fast Express.js backend that handles conversational interactions and streams responses using Google GenAI (`gemini-3.5-flash`).
- **EquityLens Financial Backend**: A robust Python FastAPI engine that performs deep financial analysis, pulling data from Yahoo Finance and other providers.
- **Comprehensive Market Analysis**: Includes technical indicators, fundamental data, market sentiment, news aggregation, and valuation models.
- **Interactive Web Interface**: A responsive frontend (located in `public/`) for chatting with the AI and viewing structured financial reports.

## Architecture

This project consists of two main backend components and a static frontend:

1. **Node.js Express Server (`index.js`)**
   - Handles the core Chatbot API routes.
   - Integrates with `@google/genai` for NLP.
   - Uses `yahoo-finance2` for lightweight financial data queries.

2. **Python FastAPI Server (`backend/main.py`)**
   - Provides heavy-duty quantitative and financial analysis endpoints.
   - Built with libraries like `yfinance`, `pandas`, `scikit-learn`, `statsmodels`, and `PyPortfolioOpt`.
   - Runs as a secondary or separate service depending on your deployment model.

## Prerequisites

- **Node.js** (v18+ recommended)
- **Python** (v3.9+ recommended)
- A **Google Gemini API Key**

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/eunikeeunik/gemini-ai-api-project.git
   cd gemini-ai-api-project
   ```

2. **Environment Variables:**
   Create a `.env` file in the root directory and add your Gemini API Key:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

3. **Setup Node.js Server:**
   ```bash
   npm install
   ```

4. **Setup Python Backend:**
   It is recommended to use a virtual environment.
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On Mac/Linux:
   source .venv/bin/activate
   
   pip install -r requirements.txt
   ```

## Running the Application

**Run the Node.js Chatbot & Web Interface:**
```bash
node index.js
```
The server will start (default is typically port 3000). You can access the UI by opening `http://localhost:3000` in your browser.

**Run the Python Financial Analysis API:**
```bash
uvicorn backend.main:app --reload
```
The FastAPI application will be available at `http://localhost:8000`. You can access the interactive Swagger API documentation at `http://localhost:8000/docs`.

## License

This project is licensed under the ISC License.
