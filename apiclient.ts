
 
export async function getHealthStatus(): Promise<HealthResponse> {
  const res = await fetch(`${BASE_URL}/`, { method: "GET" });
 
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status}`);
  }
 
  return res.json();
}
 
export async function getChatReply(prompt: string): Promise<ChatResponse> {
  const params = new URLSearchParams({ prompt });
 
  const res = await fetch(`${BASE_URL}/chat-rep?${params.toString()}`, {
    method: "GET",
  });
 
  if (!res.ok) {
    throw new Error(`Chat request failed: ${res.status}`);
  }
 
  return res.json();
}
