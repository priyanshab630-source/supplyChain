export default function MessageBubble({ role, content }) {
  return <div className={`bubble ${role}`}>{content}</div>;
}
