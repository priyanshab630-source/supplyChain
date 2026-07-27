import { useState, useCallback } from "react";
import { askQuestion } from "../api/client";

export const AGENT_ORDER = [
  "inventory",
  "forecast",
  "supplier",
  "kg",
  "network",
  "risk",
  "recommendation",
  "final_answer",
];

export function useChatStream(threadId) {
  const [flow, setFlow] = useState({});
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);

  const ask = useCallback(async (question) => {
  setFlow({});
  setAnswer(null);
  setLoading(true);

  let seenErrorCount = 0;

  await askQuestion(threadId, question, (nodeName, payload) => {
    const errors = payload.errors || [];
    const isNewError = errors.length > seenErrorCount;
    seenErrorCount = errors.length;

    setFlow((prev) => ({ ...prev, [nodeName]: { ...payload, _hasOwnError: isNewError } }));

    if (nodeName === "final_answer" && payload.final_answer) {
      setAnswer(payload.final_answer);
    }
  });

  setLoading(false);
}, [threadId]);

  return { flow, answer, loading, ask };
}
