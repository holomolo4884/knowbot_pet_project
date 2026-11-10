const API_BASE = '/api'

export interface ChatResponse {
  answer: string
  citations: Array<{
    chunk_id: string
    doc_id: string
    section: string
    page: number
  }>
}

export async function askQuestion(
  question: string,
  filters?: Record<string, any>
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, filters }),
  })
  
  if (!response.ok) {
    throw new Error('Failed to get answer')
  }
  
  return response.json()
}

export async function uploadDocument(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  
  const response = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    body: formData,
  })
  
  if (!response.ok) {
    throw new Error('Failed to upload document')
  }
  
  return response.json()
}