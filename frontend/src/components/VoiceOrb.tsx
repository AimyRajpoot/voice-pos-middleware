"use client"

import * as React from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Mic, MicOff, Loader2, Volume2, X } from "lucide-react"
import { cn } from "@/lib/utils"

interface VoiceOrbProps {
  state: 'idle' | 'listening' | 'processing' | 'speaking' | 'error'
  onMouseDown: () => void
  onMouseUp: () => void
  onTouchStart: (e: React.TouchEvent) => void
  onTouchEnd: (e: React.TouchEvent) => void
  className?: string
  errorMessage?: string
}

const stateConfig = {
  idle: {
    color: "bg-emerald-500",
    ringColor: "ring-emerald-500/30",
    icon: Mic,
    label: "Hold to speak",
    pulse: false,
  },
  listening: {
    color: "bg-red-500",
    ringColor: "ring-red-500/50",
    icon: MicOff,
    label: "Listening...",
    pulse: true,
  },
  processing: {
    color: "bg-amber-500",
    ringColor: "ring-amber-500/50",
    icon: Loader2,
    label: "Processing...",
    pulse: true,
  },
  speaking: {
    color: "bg-emerald-500",
    ringColor: "ring-emerald-500/50",
    icon: Volume2,
    label: "Speaking...",
    pulse: true,
  },
  error: {
    color: "bg-red-600",
    ringColor: "ring-red-600/50",
    icon: X,
    label: "Error",
    pulse: false,
  },
}

export function VoiceOrb({ 
  state, 
  onMouseDown, 
  onMouseUp,
  onTouchStart,
  onTouchEnd,
  className, 
  errorMessage 
}: VoiceOrbProps) {
  const config = stateConfig[state]
  const Icon = config.icon

  return (
    <div className={cn("relative flex flex-col items-center", className)}>
      <motion.button
        onMouseDown={onMouseDown}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
        onTouchStart={onTouchStart}
        onTouchEnd={onTouchEnd}
        disabled={state === 'processing' || state === 'speaking'}
        className={cn(
          "relative z-10 w-24 h-24 rounded-full flex items-center justify-center",
          "transition-all duration-300",
          "focus:outline-none focus:ring-4 focus:ring-offset-2 focus:ring-offset-slate-900",
          config.ringColor,
          config.color,
          "text-white shadow-[0_0_40px_rgba(16,185,129,0.4)]",
          state === 'error' && "cursor-not-allowed",
          state !== 'error' && state !== 'processing' && state !== 'speaking' && "hover:scale-105 active:scale-95",
          state === 'listening' && "animate-pulse"
        )}
        whileTap={{ scale: 0.95 }}
        aria-label={config.label}
      >
        <AnimatePresence mode="wait">
          {config.pulse && (
            <motion.div
              key="pulse-ring"
              initial={{ scale: 1, opacity: 0.5 }}
              animate={{ scale: 2.5, opacity: 0 }}
              transition={{ duration: 1.5, repeat: Infinity, ease: "easeOut" }}
              className={cn(
                "absolute inset-0 rounded-full",
                config.color.replace("bg-", "bg-").replace("500", "500")
              )}
            />
          )}
        </AnimatePresence>
        
        <AnimatePresence mode="wait">
          <motion.div
            key={state}
            initial={{ scale: 0, rotate: -180 }}
            animate={{ scale: 1, rotate: 0 }}
            exit={{ scale: 0, rotate: 180 }}
            transition={{ type: "spring", stiffness: 260, damping: 20 }}
          >
            <Icon 
              className={cn(
                "w-8 h-8",
                state === 'processing' && "animate-spin",
                state === 'speaking' && "animate-pulse"
              )} 
            />
          </motion.div>
        </AnimatePresence>
      </motion.button>

      <motion.p
        className="mt-4 text-center text-sm font-medium text-slate-300 min-h-[1.25rem]"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        {config.label}
      </motion.p>

      {state === 'error' && errorMessage && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-2 text-center text-xs text-red-400 max-w-xs px-2"
        >
          {errorMessage}
        </motion.div>
      )}

      <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2 flex gap-1">
        {['idle', 'listening', 'processing', 'speaking'].map((s, i) => (
          <motion.div
            key={s}
            className={cn(
              "w-2 h-2 rounded-full transition-colors",
              state === s ? "scale-125" : "scale-75"
            )}
            style={{
              backgroundColor: state === s 
                ? stateConfig[s as keyof typeof stateConfig].color.replace("bg-", "").replace("500", "500")
                : "#475569"
            }}
            initial={{ scale: 0 }}
            animate={{ scale: state === s ? 1.25 : 0.75 }}
          />
        ))}
      </div>
    </div>
  )
}