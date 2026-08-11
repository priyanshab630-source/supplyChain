const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";

export async function createThread() {
  const res = await fetch(`${API_BASE}/threads`, { method: "POST" });
  const data = await res.json();
  return data.thread_id;
}

export async function fetchHistory(threadId) {
  const res = await fetch(`${API_BASE}/threads/${threadId}/history`);
  return res.json();
}

export async function askQuestion(threadId, question, onEvent) {
  const res = await fetch(`${API_BASE}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: threadId, question }),
  });

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop();

    for (const chunk of chunks) {
      const lines = chunk.split("\n");
      const eventLine = lines.find((l) => l.startsWith("event: "));
      const dataLine = lines.find((l) => l.startsWith("data: "));
      if (!eventLine || !dataLine) continue;

      const nodeName = eventLine.replace("event: ", "");
      const payload = JSON.parse(dataLine.replace("data: ", ""));
      onEvent(nodeName, payload);
    }
  }
}
