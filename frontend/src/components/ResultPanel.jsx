export default function ResultPanel({ flow }) {
  const entries = Object.entries(flow).filter(([name]) => name !== "final_answer");

  if (entries.length === 0) return null;

  return (
    <div className="result-panel">
      {entries.map(([name, payload]) => (
        <div key={name} className="result-card">
          <h4>{name}</h4>
          <pre>{JSON.stringify(payload, null, 2)}</pre>
        </div>
      ))}
    </div>
  );
}
