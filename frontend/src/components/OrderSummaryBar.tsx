"use client"

import * as React from "react"
import { motion } from "framer-motion"
import { ShoppingCart, Plus, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface OrderSummaryBarProps {
  itemCount: number
  totalAmount: number
  onPlaceOrder: () => void
  onClearOrder: () => void
  disabled?: boolean
}

export function OrderSummaryBar({ 
  itemCount, 
  totalAmount, 
  onPlaceOrder, 
  onClearOrder,
  disabled = false
}: OrderSummaryBarProps) {
  if (itemCount === 0) return null

  return (
    <motion.div
      initial={{ y: 100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      exit={{ y: 100, opacity: 0 }}
      className="fixed bottom-0 left-0 right-0 z-50 lg:relative lg:static lg:shadow-none lg:rounded-none lg:border-t lg:border-gray-200 bg-white border-t border-gray-200 shadow-xl"
    >
      <Card className="shadow-none border-none p-4">
        <CardContent className="pt-0">
          <div className="flex items-center justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 text-sm text-gray-600 mb-1">
                <ShoppingCart className="w-4 h-4" />
                <span>{itemCount} item{itemCount !== 1 ? 's' : ''}</span>
              </div>
              <div className="text-2xl font-bold text-gray-900">
                ${totalAmount.toFixed(2)}
              </div>
            </div>
            
            <div className="flex gap-3 flex-shrink-0">
              <Button
                variant="outline"
                onClick={onClearOrder}
                disabled={disabled}
                className="lg:hidden"
                aria-label="Clear order"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
              <Button
                onClick={onPlaceOrder}
                disabled={disabled}
                className="flex-1 lg:w-auto bg-blue-600 hover:bg-blue-700 text-lg py-3"
                style={{ minWidth: '160px' }}
              >
                <Plus className="w-5 h-5 mr-2" />
                Place Order
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}