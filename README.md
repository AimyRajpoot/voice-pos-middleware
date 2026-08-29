# Voice POS System

A voice-assisted Point of Sale (POS) system with a business adapter layer that normalizes data from different restaurant backends.

## Features

- Voice ordering via speech-to-text
- Multi-restaurant support (Burger Barn, Pizza Plaza)
- Business adapter pattern for backend normalization
- Inventory tracking with stock management
- Real-time order management
- Text-to-speech responses

## Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment:
   - Copy `.env.example` to `.env`
   - Add your `OPENROUTER_API_KEY`
5. Seed the databases:
   ```bash
   python seed_data/seed_burger_barn.py
   python seed_data/seed_pizza_plaza.py
   ```
6. Run the server:
   ```bash
   uvicorn backend.main:app --reload
   ```
7. Open `frontend/index.html` in your browser

## Project Structure

```
voice-pos-demo/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── order_state.py       # Order state management
│   ├── adapters/             # Business adapter layer
│   │   ├── base.py          # Abstract base adapter
│   │   ├── burger_barn.py   # Burger Barn implementation
│   │   └── pizza_plaza.py   # Pizza Plaza implementation
│   ├── db/                  # SQLite databases
│   ├── llm/                 # LLM client
│   ├── stt/                 # Speech-to-text
│   └── tts/                 # Text-to-speech
├── frontend/
│   └── index.html           # Web interface
├── seed_data/               # Database seeding scripts
├── requirements.txt
└── .env.example
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | API key for OpenRouter | Required |
| `OPENROUTER_MODEL` | Model to use | `minimax/minimax-m3:free` |

## API Endpoints

- `POST /order` - Process voice command
- `GET /menu` - Get current menu
- `GET /order` - Get current order
- `POST /switch-business` - Switch between restaurants
