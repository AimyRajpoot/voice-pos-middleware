# DukaanMind Voice POS - Architecture Specification

## System Overview

DukaanMind is a voice-activated Point-of-Sale (POS) middleware system that processes spoken orders, transcribes audio locally, parses order intent into structured JSON schema, and executes real-time stock/price calculations against a POS inventory engine.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                FRONTEND LAYER                                   │
│  Next.js 14 (TypeScript / React) - localhost:3000                               │
│  └── Audio Stream Capture via MediaRecorder API (WebM/WAV)                      │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         │ HTTP POST /api/v1/process-audio
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                 BACKEND LAYER                                   │
│  FastAPI (Python 3.13) - localhost:8000                                         │
│  ├── CorsMiddleware (Allow All)                                                 │
│  └── Temporary Disk File Streaming                                              │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                             SPEECH RECOGNITION (STT)                            │
│  faster-whisper (CPU int8, base.en weights)                                     │
│  └── Voice Activity Detection (vad_filter=True, min_silence_duration_ms=500)   │
│  └── Domain Biasing (initial_prompt=MENU_VOCAB)                                 │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │ Raw Transcript
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            INTENT PARSING PIPELINE                              │
│  app/core/langgraph_pipeline.py (LangGraph StateGraph)                          │
│  ├── Node 1: intent_classifier → [ORDER, MENU_QA, OUT_OF_SCOPE]               │
│  ├── Node 2: inventory_validator → stock check, unavailable items             │
│  ├── Node 3: confirmation_node → store-oriented confirmation                   │
│  ├── Node 4: order_executor → stock deduction, receipt JSON                    │
│  ├── Handler: menu_qa_handler → RAG-powered Q&A                                │
│  └── Handler: out_of_scope_handler → rejection with menu                       │
│  └── LangSmith Tracing (optional)                                              │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │ Structured JSON Order
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                             POS ENGINE & ADAPTER                              │
│  app/adapters/mock_pos.py (MockPOSAdapter)                                      │
│  └── Inventory Management, Stock Validation, Receipt Generation                │
└─────────────────────────────────────────────────────────────────────────────────┘
```
---

## Directory Structure

```
voice_pos_middleware/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI entry point
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py                # BasePOSAdapter abstract class
│   │   └── mock_pos.py            # MockPOSAdapter implementation
│   ├── core/
│   │   ├── __init__.py
│   │   ├── pipeline.py            # Legacy pipeline (fallback parser)
│   │   ├── langgraph_pipeline.py  # NEW: LangGraph StateGraph
│   │   ├── tts_engine.py          # Edge TTS integration
│   │   └── rag_engine.py          # LanceDB + sentence-transformers
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── tts.py
│   │   └── rag.py
│   └── utils/
│       └── __init__.py
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx           # Main VoicePOS page (redesigned)
│   │   │   ├── layout.tsx
│   │   │   └── globals.css
│   │   ├── components/
│   │   │   ├── VoiceOrb.tsx       # Push-To-Talk visualizer
│   │   │   ├── ReceiptCard.tsx    # Itemized receipt
│   │   │   ├── MenuQAPanel.tsx    # Collapsible Q&A panel
│   │   │   └── ui/                # shadcn/ui components
│   │   ├── hooks/
│   │   │   └── useVoicePOS.ts     # Push-To-Talk hook
│   │   ├── lib/
│   │   │   ├── api.ts             # API client
│   │   │   └── utils.ts
│   │   └── styles/
│   ├── package.json
│   ├── tsconfig.json
│   └── tailwind.config.ts
├── requirements.txt
├── ARCHITECTURE.md
├── IMPLEMENTATION_REPORT.md
└── venv/
```

---

## Core Components

### 1. Speech Recognition (STT)

**File**: `app/main.py`

```python
whisper_model = WhisperModel("base.en", device="cpu", compute_type="int8")

# Domain vocabulary biasing
MENU_VOCAB = "Zinger Burger, Single Burger, Double Burger, Coca-Cola Zero, Fries, Peppy"

segments, _ = whisper_model.transcribe(
    audio_path,
    beam_size=5,
    vad_filter=True,
    vad_parameters=dict(min_silence_duration_ms=500),
    initial_prompt=MENU_VOCAB,  # Forces phonetic mapping
)
```

**Configuration**:
- Model: `base.en` (English optimized, ~74MB)
- Quantization: `int8` (CPU inference)
- VAD: Enabled with 500ms min silence
- Biasing: `initial_prompt` with menu items

### 2. LangGraph Pipeline

**File**: `app/core/langgraph_pipeline.py`

**State Schema**:
```python
class PipelineState(TypedDict):
    transcript: str
    intent: IntentType | None          # ORDER | MENU_QA | OUT_OF_SCOPE
    parsed_items: list[dict] | None
    validated_items: list[dict] | None
    unavailable_items: list[str] | None
    confirmation_message: str | None
    user_confirmed: bool | None
    receipt: dict | None
    error: str | None
```

**Nodes**:
1. `intent_classifier` - LLM + keyword fallback
2. `inventory_validator` - LLM parser → fallback → stock check
3. `confirmation_node` - Generates receipt preview
4. `order_executor` - Deducts stock, finalizes receipt
5. `menu_qa_handler` - RAG query via LanceDB
6. `out_of_scope_handler` - Standardized rejection

**Routing**:
```python
workflow.add_conditional_edges(
    "intent_classifier",
    route_after_classifier,
    {"inventory_validator": "inventory_validator", "menu_qa_handler": "menu_qa_handler", "out_of_scope_handler": "out_of_scope_handler"}
)
```

### 3. POS Adapter

**File**: `app/adapters/mock_pos.py`

---

## Frontend Architecture

### State Management

**Hook**: `frontend/src/hooks/useVoicePOS.ts`

```typescript
interface VoicePOSState {
  phase: 'idle' | 'listening' | 'processing' | 'speaking' | 'error'
  transcript: string
  receipt: ProcessAudioResponse['receipt'] | null
  error: string | null
  qaMessages: QAMessage[]
  qaLoading: boolean
  qaPanelOpen: boolean
}

// Push-To-Talk handlers
const onMouseDown = () => startRecording()
const onMouseUp = () => stopRecording()
const onTouchStart = (e) => { e.preventDefault(); startRecording() }
const onTouchEnd = (e) => { e.preventDefault(); stopRecording() }
```

### Component Hierarchy

```
VoicePOS (page.tsx)
├── Left Sidebar (MenuQAPanel)
│   ├── Header (toggle, title)
│   ├── ScrollArea (messages)
│   │   ├── UserMessage
│   │   ├── AssistantMessage + Citations
│   │   └── LoadingIndicator
│   └── Form (Input + Send)
├── Main Content
│   ├── TopBar (time, online status, receipt toggle)
│   ├── Center Studio
│   │   ├── VoiceOrb (Push-To-Talk)
│   │   ├── TranscriptDisplay
│   │   ├── QuickQuestions (idle only)
│   │   └── ErrorDisplay
│   └── BottomStatusBar (desktop only)
└── Right Panel (ReceiptCard)
    ├── Header (title, item count, close)
    └── ScrollArea (ReceiptCard)
        ├── Order ID
        ├── Assistant Note + TTS Play
        ├── Items List
        ├── Unavailable Items
        ├── Subtotal/Tax/Total
        └── Actions: [Confirm & Pay] [Clear Order]
```

### VoiceOrb Component

**File**: `frontend/src/components/VoiceOrb.tsx`

Props:
```typescript
interface VoiceOrbProps {
  state: 'idle' | 'listening' | 'processing' | 'speaking' | 'error'
  onMouseDown: () => void
  onMouseUp: () => void
  onTouchStart: (e: React.TouchEvent) => void
  onTouchEnd: (e: React.TouchEvent) => void
  errorMessage?: string
}
```

State Config:
| State | Color | Ring | Icon | Label | Pulse |
|-------|-------|------|------|-------|-------|
| idle | emerald-500 | emerald-500/30 | Mic | "Hold to speak" | false |
| listening | red-500 | red-500/50 | MicOff | "Listening..." | true |
| processing | amber-500 | amber-500/50 | Loader2 | "Processing..." | true |
| speaking | emerald-500 | emerald-500/50 | Volume2 | "Speaking..." | true |
| error | red-600 | red-600/50 | X | "Error" | false |
```python
class MockPOSAdapter(BasePOSAdapter):
    inventory = {
        "zinger burger": {"price": 5.99, "stock": 10},
        "single burger": {"price": 4.50, "stock": 5},
        "double burger": {"price": 6.50, "stock": 0},  # Out of stock
        "coca-cola zero": {"price": 1.99, "stock": 15},
        "fries": {"price": 2.50, "stock": 20},
        "peppy": {"price": 1.99, "stock": 100},
    }
    
    async def execute_order(self, parsed_data: dict) -> dict:
        # Validates stock, deducts, returns receipt
```

### 4. RAG Engine

**File**: `app/core/rag_engine.py`

- Vector DB: LanceDB (embedded)
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2`
- Menu items pre-indexed with metadata (price, stock, category)
- Similarity threshold: configurable (default 0.3)

### 5. TTS Engine

**File**: `app/core/tts_engine.py`

- Provider: Edge TTS (Microsoft)
- Voices: `en_US-aria` (default), configurable
- Output: Base64 MP3 or streaming chunks
- Latency: ~200-500ms for short texts