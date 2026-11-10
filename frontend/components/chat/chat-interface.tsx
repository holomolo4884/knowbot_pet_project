'use client'

import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport } from 'ai'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useState } from 'react'

export function ChatInterface() {
  const [input, setInput] = useState('')
  const { messages, sendMessage, status } = useChat({
    transport: new DefaultChatTransport({ api: '/api/chat/stream' }),
  })
  const isLoading = status === 'submitted' || status === 'streaming'

  return (
    <div className="flex flex-col h-[600px] max-w-4xl mx-auto">
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4">
          {messages.map((m) => (
            <div
              key={m.id}
              className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <Card className={`p-4 max-w-[80%] ${m.role === 'user' ? 'bg-blue-50' : 'bg-gray-50'}`}>
                <div className="whitespace-pre-wrap">
                  {m.parts.map((part, index) =>
                    part.type === 'text' ? <span key={index}>{part.text}</span> : null,
                  )}
                </div>
              </Card>
            </div>
          ))}
          
          {isLoading && (
            <div className="flex justify-start">
              <Card className="p-4 bg-gray-50">
                <div className="animate-pulse">Думаю...</div>
              </Card>
            </div>
          )}
        </div>
      </ScrollArea>

      <form
        onSubmit={(event) => {
          event.preventDefault()
          const text = input.trim()
          if (text) {
            sendMessage({ text })
            setInput('')
          }
        }}
        className="p-4 border-t"
      >
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Задайте вопрос по базе знаний..."
            className="flex-1"
          />
          <Button type="submit" disabled={isLoading}>
            Отправить
          </Button>
        </div>
      </form>
    </div>
  )
}
