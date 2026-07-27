import { useState, useEffect } from "react";
import MessageBubble from "./MessageBubble";
import AgentFlow from "./AgentFlow";
import ResultPanel from "./ResultPanel";
import { useChatStream } from "../hooks/useChatStream";

export default function ChatWindow({ threadId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const { flow, answer, loading, ask } = useChatStream(threadId);

  useEffect(() => {
    if (answer) {
      setMessages((prev) => [...prev, { role: "assistant", content: answer }]);
    }
  }, [answer]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    setMessages((prev) => [...prev, { role: "user", content: input }]);
    const question = input;
    setInput("");

    await ask(question);
  };

  return (
    <div className="chat-window">
      <div className="messages">
        {messages.map((m, i) => (
          <MessageBubble key={i} role={m.role} content={m.content} />
        ))}
      </div>

      {(loading || Object.keys(flow).length > 0) && <AgentFlow flow={flow} />}
      <ResultPanel flow={flow} />

      <form onSubmit={handleSubmit}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about a tank, supplier, or risk..."
        />
        <button type="submit" disabled={loading}>
          {loading ? "Thinking..." : "Ask"}
        </button>
      </form>
    </div>
  );
}
