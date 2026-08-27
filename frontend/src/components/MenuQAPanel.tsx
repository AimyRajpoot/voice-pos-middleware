"use client"

import * as React from "react"
import { motion, AnimatePresence } from "framer-motion"
import { MessageSquare, X, Send, Loader2, Sparkles } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"

interface QAMessage {
  role: "user" | "assistant"
  content: string
  citations?: Array<{
    name: string
    category: string
    price: number
    stock: number
    relevance_score: number
  }>
}

interface MenuQAPanelProps {
  isOpen: boolean
  onClose: () => void
  onAskQuestion: (question: string) => Promise<void>
  messages: QAMessage[]
  isLoading: boolean
}

const SUGGESTED_QUESTIONS = [
  "What's in the Zinger Burger?",
  "How much is the double burger?",
  "Is the double burger in stock?",
  "What sides do you have?",
  "Any vegetarian options?",
  "Does the Coke have sugar?",
]

export function MenuQAPanel({ 
  isOpen, 
  onClose, 
  onAskQuestion, 
  messages, 
  isLoading 
}: MenuQAPanelProps) {
  const [inputValue, setInputValue] = React.useState("")
  const scrollAreaRef = React.useRef<HTMLDivElement>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputValue.trim() || isLoading) return
    
    const question = inputValue.trim()
    setInputValue("")
    await onAskQuestion(question)
  }

  const handleSuggestedClick = async (question: string) => {
    if (isLoading) return
    await onAskQuestion(question)
  }

  React.useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight
    }
  }, [messages])

  return (
<AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/20 z-40 lg:hidden"
            onClick={onClose}
          />
          
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 h-full w-full max-w-md lg:relative lg:max-w-none lg:w-auto lg:h-auto lg:static lg:rounded-none lg:border-l lg:border-gray-200 z-50 bg-white shadow-xl flex flex-col"
          >
            <CardHeader className="p-4 border-b border-gray-200 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <CardTitle className="text-lg">Menu Assistant</CardTitle>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                className="lg:hidden"
              >
                <X className="w-5 h-5" />
              </Button>
            </CardHeader>

            <CardContent className="flex-1 flex flex-col p-0">
              <ScrollArea className="flex-1 p-4">
                <div ref={scrollAreaRef} className="space-y-4">
{messages.length === 0 && (
                    <div className="space-y-4">
                      <div className="text-center text-gray-500 py-8">
                        <MessageSquare className="w-12 h-12 mx-auto text-gray-300 mb-3" />
                        <p className="text-sm">Ask me anything about the menu!</p>
                      </div>
                      
                      <div>
                        <p className="text-xs text-gray-400 uppercase tracking-wider mb-2">Suggested questions</p>
                        <div className="flex flex-wrap gap-2">
                          {SUGGESTED_QUESTIONS.map((q, i) => (
                            <Button
                              key={i}
                              variant="outline"
                              size="sm"
                              className="text-xs h-8 px-3"
                              onClick={() => handleSuggestedClick(q)}
                            >
                              {q}
                            </Button>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {messages.map((msg, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className={cn("flex gap-3", msg.role === "user" && "flex-row-reverse")}
                    >
                      <div
                        className={cn(
                          "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0",
                          msg.role === "user" 
                            ? "bg-blue-100 text-blue-600" 
                            : "bg-gradient-to-br from-blue-500 to-purple-600 text-white"
                        )}
                      >
                        {msg.role === "user" ? (
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        ) : (
                          <Sparkles className="w-4 h-4" />
                        )}
                      </div>
                      
                      <div className={cn(
                        "max-w-[80%] rounded-2xl px-4 py-2",
                        msg.role === "user"
                          ? "bg-blue-50 rounded-tr-none text-gray-900"
                          : "bg-gray-50 rounded-tl-none text-gray-900"
                      )}>
                        <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
{msg.citations && msg.citations.length > 0 && msg.role === "assistant" && (
                          <div className="mt-2 pt-2 border-t border-gray-200">
                            <p className="text-xs text-gray-500 mb-1">Sources:</p>
                            <div className="flex flex-wrap gap-1">
                              {msg.citations.map((c, i) => (
                                <span
                                  key={i}
                                  className="px-2 py-0.5 bg-white border border-gray-200 rounded text-xs text-gray-600"
                                >
                                  {c.name} (${c.price.toFixed(2)})
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </motion.div>
                  ))}
                  
                  {isLoading && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex gap-3"
                    >
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                        <Loader2 className="w-4 h-4 text-white animate-spin" />
                      </div>
                      <div className="bg-gray-50 rounded-2xl rounded-tl-none px-4 py-2">
                        <div className="flex gap-1">
                          <motion.span
                            animate={{ y: [0, -4, 0] }}
                            transition={{ duration: 0.6, repeat: Infinity, delay: 0 }}
                            className="w-2 h-2 bg-blue-500 rounded-full"
                          />
                          <motion.span
                            animate={{ y: [0, -4, 0] }}
                            transition={{ duration: 0.6, repeat: Infinity, delay: 0.15 }}
                            className="w-2 h-2 bg-blue-500 rounded-full"
                          />
                          <motion.span
                            animate={{ y: [0, -4, 0] }}
                            transition={{ duration: 0.6, repeat: Infinity, delay: 0.3 }}
                            className="w-2 h-2 bg-blue-500 rounded-full"
                          />
                        </div>
                      </div>
                    </motion.div>
                  )}
                </div>
              </ScrollArea>

              <Separator />
              
              <form onSubmit={handleSubmit} className="p-4">
                <div className="flex gap-2">
                  <Input
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    placeholder="Ask about menu items..."
                    className="flex-1"
                    disabled={isLoading}
                    aria-label="Ask a question about the menu"
                  />
                  <Button
                    type="submit"
                    disabled={!inputValue.trim() || isLoading}
                    size="icon"
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    <Send className="w-4 h-4" />
                  </Button>
                </div>
              </form>
            </CardContent>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
