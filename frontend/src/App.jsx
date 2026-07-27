import { useEffect, useState } from "react";
import ChatWindow from "./components/ChatWindow";
import { createThread } from "./api/client";

export default function App() {
  const [threadId, setThreadId] = useState(null);

  useEffect(() => {
    createThread().then(setThreadId);
  }, []);

  if (!threadId) {
    return <p className="loading">Starting conversation...</p>;
  }

  return (
    <div className="app">
      <h1>Supply Chain Assistant</h1>
      <ChatWindow threadId={threadId} />
    </div>
  );
}
