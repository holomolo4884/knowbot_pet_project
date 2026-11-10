import { ChatInterface } from '@/components/chat/chat-interface'

export default function Home() {
  return (
    <main className="min-h-screen p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-4xl font-bold mb-2">KnowBot</h1>
        <p className="text-gray-600 mb-8">
          AI-ассистент по внутренней базе знаний компании
        </p>
        
        <ChatInterface />
      </div>
    </main>
  )
}