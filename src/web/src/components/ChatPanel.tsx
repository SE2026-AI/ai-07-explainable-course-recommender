import { useEffect, useRef, useState, type FormEvent } from "react";
import type { TranscriptRecommendations } from "../api/transcript";
import { answerQuestion, suggestions, type Answer } from "../lib/chat";

export type Turn = { question: string; answer: Answer };

/**
 * Khung hỏi đáp về gợi ý đang hiện (bản thử, không dùng LLM): trả lời từ `answerQuestion`. Lịch sử do màn cha
 * giữ, vì bỏ môn làm kết quả tải lại và khung này bị gỡ khỏi cây trong lúc tải.
 */
export function ChatPanel({
  data,
  turns,
  setTurns,
  onSkip,
}: {
  data: TranscriptRecommendations;
  turns: Turn[];
  setTurns: (update: (t: Turn[]) => Turn[]) => void;
  onSkip: (code: string) => void;
}) {
  const [draft, setDraft] = useState("");
  const log = useRef<HTMLOListElement>(null);
  // Khung hội thoại có chiều cao tối đa: cuộn xuống câu trả lời mới nhất.
  useEffect(() => {
    if (log.current) log.current.scrollTop = log.current.scrollHeight;
  }, [turns]);

  function ask(question: string) {
    if (!question.trim()) return;
    const answer = answerQuestion(question, data);
    setTurns((t) => [...t, { question, answer }]);
    setDraft("");
    if (answer.action) onSkip(answer.action.course_code);
  }
  function submit(e: FormEvent) {
    e.preventDefault();
    ask(draft);
  }

  return (
    <section className="panel chat" aria-labelledby="chat-title">
      <div className="panel-head">
        <div>
          <h2 id="chat-title">Hỏi đáp về gợi ý</h2>
          <p>Trả lời từ chính kết quả ở trên, không dùng mô hình ngôn ngữ.</p>
        </div>
      </div>
      {turns.length > 0 && (
        <ol ref={log} className="chat-log" aria-live="polite">
          {turns.map((t, i) => (
            <li key={i}>
              <p className="chat-q">{t.question}</p>
              <div className="chat-a">
                <p>{t.answer.text}</p>
                {t.answer.lines && t.answer.lines.length > 0 && (
                  <ul>
                    {t.answer.lines.map((l, j) => (
                      <li key={j}>{l}</li>
                    ))}
                  </ul>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
      <ul className="chips chat-suggest" aria-label="Câu hỏi mẫu">
        {suggestions(data).map((s) => (
          <li key={s}>
            <button type="button" className="ghost small" onClick={() => ask(s)}>
              {s}
            </button>
          </li>
        ))}
      </ul>
      <form className="chat-form" onSubmit={submit}>
        <input
          aria-label="Câu hỏi về gợi ý"
          placeholder="Ví dụ: Vì sao gợi ý môn này? Bỏ môn này thì sao?"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />
        <button type="submit" className="primary" disabled={!draft.trim()}>
          Hỏi
        </button>
      </form>
    </section>
  );
}
