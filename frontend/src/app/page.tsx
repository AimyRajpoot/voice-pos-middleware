"use client"

import { useState, useEffect, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  Mic,
  MicOff,
  Loader2,
  Volume2,
  X,
  Sparkles,
  Send,
  MessageSquare,
  Wifi,
  WifiOff,
  Clock,
  Receipt,
  Printer,
  CreditCard,
  Trash2,
  ChevronLeft,
  ChevronRight,
  Shield,
  AlertCircle,
  CheckCircle2,
  Speaker,
  Menu as MenuIcon,
  X as CloseIcon,
} from "lucide-react"
import { VoiceOrb } from "@/components/VoiceOrb"
import { ReceiptCard } from "@/components/ReceiptCard"
import { MenuQAPanel } from "@/components/MenuQAPanel"
import { useVoicePOS } from "@/hooks/useVoicePOS"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"

const QUICK_QUESTIONS = [
  "What's in the Zinger Burger?",
  "How much is the double burger?",
  "Is the double burger in stock?",
  "What sides do you have?",
  "Any vegetarian options?",
  "Does the Coke have sugar?",
]

interface ReceiptItem {
  name: string
  quantity: number
  unit_price: number
  subtotal: number
}

interface ReceiptData {
  status: "success" | "unsupported"
  order_id?: string
  items: ReceiptItem[]
  unavailable?: string[]
  total_amount: number
  assistant_note: string
  assistant_audio_base64?: string
  message?: string
}

export default function VoicePOS() {
  const {
    phase,
    transcript,
    receipt,
    error,
    qaMessages,
    qaLoading,
    qaPanelOpen,
    startRecording,
    stopRecording,
    toggleRecording,
    clearReceipt,
    orderAgain,
    askQuestion,
    toggleQAPanel,
    closeQAPanel,
  } = useVoicePOS()

  const [currentTime, setCurrentTime] = useState(new Date())
  const [isOnline, setIsOnline] = useState(true)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [rightPanelOpen, setRightPanelOpen] = useState(true)

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  const handlePlayAudio = useCallback((audioBase64: string) => {
    const audio = new Audio(`data:audio/mpeg;base64,${audioBase64}`)
    audio.play().catch(console.error)
  }, [])

  const calculateTotals = (items: ReceiptItem[]) => {
    const subtotal = items.reduce((sum, item) => sum + item.subtotal, 0)
    const tax = subtotal * 0.05
    const total = subtotal + tax
    return { subtotal, tax, total }
  }

  const totals = receipt?.items ? calculateTotals(receipt.items) : { subtotal: 0, tax: 0, total: 0 }

  const itemCount = receipt?.items?.reduce((sum, item) => sum + item.quantity, 0) || 0

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Left Sidebar - Menu/QA Panel */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 w-80 transform transition-transform duration-300 ease-in-out lg:relative lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <MenuQAPanel
          isOpen={qaPanelOpen}
          onClose={closeQAPanel}
          onAskQuestion={askQuestion}
          messages={qaMessages}
          isLoading={qaLoading}
        />
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 lg:ml-0">
        {/* Top Bar */}
        <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between sticky top-0 z-30">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="lg:hidden"
              aria-label="Toggle menu"
            >
              <MenuIcon className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">Voice POS</h1>
              <p className="text-xs text-gray-500">Speak to place an order</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Online Status */}
            <div className="flex items-center gap-2 text-sm hidden sm:flex">
              <span
                className={cn(
                  "w-2 h-2 rounded-full",
                  isOnline ? "bg-green-500" : "bg-red-500"
                )}
              />
              <span className={cn(isOnline ? "text-green-600" : "text-red-600")}>
                {isOnline ? "Online" : "Offline"}
              </span>
            </div>

            {/* Time */}
            <div className="hidden md:flex items-center gap-1 text-sm text-gray-500">
              <Clock className="w-4 h-4" />
              {currentTime.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </div>

            {/* Right Panel Toggle */}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setRightPanelOpen(!rightPanelOpen)}
              aria-label="Toggle receipt panel"
            >
              <Receipt className="w-5 h-5" />
            </Button>
          </div>
        </header>

        {/* Center Content - Voice Orb */}
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="w-full max-w-md">
            <VoiceOrb
              state={phase}
              onClick={toggleRecording}
              errorMessage={error ?? undefined}
            />

            {/* Transcript Display */}
            {(transcript || phase === "listening" || phase === "processing") && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-6 p-4 bg-white rounded-xl border border-gray-200 text-center"
              >
                <p className="text-sm text-gray-500 mb-1">You said:</p>
                <p className="text-lg font-medium text-gray-900 min-h-[1.5rem]">
                  {transcript || (phase === "listening" ? "Listening..." : "Processing...")}
                </p>
              </motion.div>
            )}

            {/* Quick Questions */}
            {phase === "idle" && !receipt && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-8"
              >
                <p className="text-sm text-gray-500 text-center mb-4">Or ask a question:</p>
                <div className="grid grid-cols-2 gap-2">
                  {QUICK_QUESTIONS.map((question, index) => (
                    <Button
                      key={index}
                      variant="outline"
                      size="sm"
                      className="text-left h-auto py-2 px-3"
                      onClick={() => askQuestion(question)}
                      disabled={qaLoading}
                    >
                      <MessageSquare className="w-4 h-4 mr-2" />
                      {question}
                    </Button>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Error Display */}
            {error && phase === "error" && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-6 p-4 bg-red-50 border border-red-200 rounded-xl text-center"
              >
                <AlertCircle className="w-6 h-6 text-red-500 mx-auto mb-2" />
                <p className="text-red-700">{error}</p>
                <Button
                  variant="outline"
                  className="mt-3"
                  onClick={toggleRecording}
                >
                  Try Again
                </Button>
              </motion.div>
            )}
          </div>
        </div>

        {/* Bottom Status Bar */}
        <footer className="bg-white border-t border-gray-200 px-4 py-2 hidden lg:flex items-center justify-between text-xs text-gray-500">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <Wifi className={cn("w-3 h-3", isOnline ? "text-green-500" : "text-red-500")} />
              {isOnline ? "Connected" : "Disconnected"}
            </span>
            <span className="flex items-center gap-1">
              <Shield className="w-3 h-3" />
              Secure
            </span>
          </div>
          <span>Press and hold to speak</span>
        </footer>
      </main>

      {/* Right Panel - Receipt */}
      <AnimatePresence>
        {rightPanelOpen && receipt && (
          <motion.aside
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed inset-y-0 right-0 z-40 w-full max-w-md lg:relative lg:max-w-md lg:border-l lg:border-gray-200 bg-white shadow-xl"
          >
            <div className="flex flex-col h-full">
              <div className="p-4 border-b border-gray-200 flex items-center justify-between sticky top-0 bg-white z-10">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                    <Receipt className="w-5 h-5 text-white" />
                  </div>
                  <h2 className="font-semibold text-gray-900">Order Summary</h2>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-500">{itemCount} items</span>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setRightPanelOpen(false)}
                    className="lg:hidden"
                  >
                    <X className="w-5 h-5" />
                  </Button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-4">
                <ReceiptCard
                  receipt={receipt}
                  onPlayAudio={handlePlayAudio}
                  onClear={clearReceipt}
                  onOrderAgain={orderAgain}
                />
              </div>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Mobile Overlay for Right Panel */}
      <AnimatePresence>
        {rightPanelOpen && receipt && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/20 z-30 lg:hidden"
            onClick={() => setRightPanelOpen(false)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}