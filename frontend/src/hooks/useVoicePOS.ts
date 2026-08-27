"use client"

import { useState, useRef, useCallback, useEffect } from "react"
import { processAudio, playAudioBase64, menuQA, type ProcessAudioResponse, type QAResponse, type QARequest } from "@/lib/api"

interface ReceiptItem {
  name: string
  quantity: number
  unit_price: number
  subtotal: number
}

interface VoicePOSState {
  phase: 'idle' | 'listening' | 'processing' | 'speaking' | 'error'
  transcript: string
  receipt: ProcessAudioResponse['receipt'] | null
  error: string | null
  qaMessages: Array<{
    role: 'user' | 'assistant'
    content: string
    citations?: QAResponse['citations']
  }>
  qaLoading: boolean
  qaPanelOpen: boolean
  isPressingToTalk: boolean
}

const initialState: VoicePOSState = {
  phase: 'idle',
  transcript: '',
  receipt: null,
  error: null,
  qaMessages: [],
  qaLoading: false,
  qaPanelOpen: false,
  isPressingToTalk: false,
}

export function useVoicePOS() {
  const [state, setState] = useState<VoicePOSState>(initialState)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const recordingStartRef = useRef<number>(0)

  const clearReceipt = useCallback(() => {
    setState(prev => ({ ...prev, receipt: null, transcript: '', error: null }))
  }, [])

  const startRecording = useCallback(async () => {
    if (state.phase === 'listening' || state.phase === 'processing') return
    
    setState(prev => ({ ...prev, error: null, transcript: '', receipt: null, isPressingToTalk: true }))
    
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true }
      })
      streamRef.current = stream

      let mimeType = "audio/webm"
      if (!MediaRecorder.isTypeSupported("audio/webm")) {
        if (MediaRecorder.isTypeSupported("audio/mp4")) mimeType = "audio/mp4"
        else if (MediaRecorder.isTypeSupported("audio/ogg")) mimeType = "audio/ogg"
      }

      const mediaRecorder = new MediaRecorder(stream, { mimeType })
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []
      recordingStartRef.current = Date.now()

      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          audioChunksRef.current.push(e.data)
        }
      }

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType })
        const duration = Date.now() - recordingStartRef.current
        
        if (audioBlob.size === 0 || duration < 300) {
          setState(prev => ({ 
            ...prev, 
            phase: 'error', 
            error: "Recording too short. Please hold the button longer.",
            isPressingToTalk: false
          }))
          return
        }

        setState(prev => ({ ...prev, phase: 'processing', isPressingToTalk: false }))
        
        try {
          const result = await processAudio(audioBlob)
          
          if (result.receipt.assistant_audio_base64) {
            setState(prev => ({ ...prev, phase: 'speaking' }))
            playAudioBase64(result.receipt.assistant_audio_base64)
          }
          
          setState(prev => ({
            ...prev,
            phase: 'idle',
            transcript: result.transcript,
            receipt: result.receipt,
          }))
        } catch (err: any) {
          setState(prev => ({
            ...prev,
            phase: 'error',
            error: err.message || "Failed to process audio",
            isPressingToTalk: false
          }))
        }
      }

      mediaRecorder.start(200)
      setState(prev => ({ ...prev, phase: 'listening' }))
    } catch (err) {
      setState(prev => ({
        ...prev,
        phase: 'error',
        error: "Microphone access failed. Please grant permission in browser.",
        isPressingToTalk: false
      }))
    }
  }, [])

  const stopAndSubmitRecording = useCallback(() => {
    if (mediaRecorderRef.current && state.phase === 'listening') {
      mediaRecorderRef.current.stop()
      streamRef.current?.getTracks().forEach(track => track.stop())
    } else {
      setState(prev => ({ ...prev, isPressingToTalk: false }))
    }
  }, [state.phase])

  const onMouseDown = useCallback(() => {
    if (state.phase === 'idle' || state.phase === 'error') {
      startRecording()
    }
  }, [state.phase, startRecording])

  const onMouseUp = useCallback(() => {
    if (state.phase === 'listening') {
      stopAndSubmitRecording()
    }
  }, [state.phase, stopAndSubmitRecording])

  const onTouchStart = useCallback((e: React.TouchEvent) => {
    e.preventDefault()
    if (state.phase === 'idle' || state.phase === 'error') {
      startRecording()
    }
  }, [state.phase, startRecording])

  const onTouchEnd = useCallback((e: React.TouchEvent) => {
    e.preventDefault()
    if (state.phase === 'listening') {
      stopAndSubmitRecording()
    }
  }, [state.phase, stopAndSubmitRecording])

  const askQuestion = useCallback(async (question: string) => {
    setState(prev => ({ ...prev, qaLoading: true }))
    try {
      const request: QARequest = { question }
      const result = await menuQA(request)
      
      setState(prev => ({
        ...prev,
        qaMessages: [
          ...prev.qaMessages,
          { role: 'user', content: question },
          { role: 'assistant', content: result.answer, citations: result.citations }
        ],
        qaLoading: false,
      }))
    } catch (err: any) {
      setState(prev => ({
        ...prev,
        qaMessages: [
          ...prev.qaMessages,
          { role: 'user', content: question },
          { role: 'assistant', content: err.message || "Failed to get answer" }
        ],
        qaLoading: false,
      }))
    }
  }, [])

  const toggleQAPanel = useCallback(() => {
    setState(prev => ({ ...prev, qaPanelOpen: !prev.qaPanelOpen }))
  }, [])

  const closeQAPanel = useCallback(() => {
    setState(prev => ({ ...prev, qaPanelOpen: false }))
  }, [])

  const orderAgain = useCallback(() => {
    setState(prev => ({ 
      ...prev, 
      receipt: null, 
      transcript: '', 
      error: null 
    }))
  }, [])

  const confirmAndPay = useCallback(() => {
    if (state.receipt) {
      setState(prev => ({
        ...prev,
        transcript: "Payment confirmed! Thank you for your order.",
      }))
    }
  }, [state.receipt])

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach(track => track.stop())
    }
  }, [])

  return {
    ...state,
    startRecording,
    stopRecording: stopAndSubmitRecording,
    onMouseDown,
    onMouseUp,
    onTouchStart,
    onTouchEnd,
    clearReceipt,
    orderAgain,
    confirmAndPay,
    askQuestion,
    toggleQAPanel,
    closeQAPanel,
  }
}