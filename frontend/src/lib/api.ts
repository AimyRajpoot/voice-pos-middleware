const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export interface ProcessAudioResponse {
  transcript: string
  receipt: {
    status: "success" | "unsupported"
    order_id?: string
    items: Array<{
      name: string
      quantity: number
      unit_price: number
      subtotal: number
    }>
    unavailable?: string[]
    total_amount: number
    assistant_note: string
    assistant_audio_base64?: string
    message?: string
  }
}

export interface TTSResponse {
  audio_base64: string
  duration_ms: number
  voice: string
}

export interface QARequest {
  question: string
  k?: number
  similarity_threshold?: number
}

export interface QACitation {
  name: string
  category: string
  price: number
  stock: number
  relevance_score: number
}

export interface QAResponse {
  answer: string
  citations: QACitation[]
  confidence: number
}

export interface HealthResponse {
  status: string
  whisper: string
  tts: string
  tts_voice: string
  available_voices: string[]
  rag: string
}

export async function processAudio(audioBlob: Blob): Promise<ProcessAudioResponse> {
  const formData = new FormData()
  formData.append("file", audioBlob, "audio.webm")
  
  const response = await fetch(`${API_BASE}/api/v1/process-audio`, {
    method: "POST",
    body: formData,
  })
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || "Failed to process audio")
  }
  
  return response.json()
}

export async function textToSpeech(text: string, voice: string = "en_US-aria"): Promise<TTSResponse> {
  const response = await fetch(`${API_BASE}/api/v1/tts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, voice }),
  })
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || "TTS failed")
  }
  
  return response.json()
}

export async function menuQA(request: QARequest): Promise<QAResponse> {
  const response = await fetch(`${API_BASE}/api/v1/menu-qa`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  })
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || "RAG query failed")
  }
  
  return response.json()
}

export async function healthCheck(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/api/v1/health`)
  return response.json()
}

export function playAudioBase64(base64: string): HTMLAudioElement {
  const audio = new Audio(`data:audio/mpeg;base64,${base64}`)
  audio.play().catch(console.error)
  return audio
}