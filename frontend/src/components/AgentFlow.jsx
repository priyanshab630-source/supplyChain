import { AGENT_ORDER } from "../hooks/useChatStream";

export default function AgentFlow({ flow }) {
  return (
    <ul className="agent-flow">
      {AGENT_ORDER.map((name) => {
        const result = flow[name];
        const done = result !== undefined;
        const hasError = done && result._hasOwnError;
        const status = !done ? "pending" : hasError ? "error" : "done";

        return (
          <li key={name} className={status}>
            <span className="dot" />
            {name}
          </li>
        );
      })}
    </ul>
  );
}
