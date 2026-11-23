import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import fixture from "../api/mocks/contract/transcript-recommendations.json";
import type { TranscriptRecommendations } from "../api/transcript";
import { useState } from "react";
import { ChatPanel, type Turn } from "../components/ChatPanel";
import { answerQuestion, suggestions } from "../lib/chat";

const data = fixture as TranscriptRecommendations;
const CODE = /\b[A-Z]{2,4}\d{3,4}[A-Z]?\b/g;
const known = new Set(JSON.stringify(data).match(CODE));

/** Mọi mã môn trong câu trả lời phải có trong dữ liệu hoặc do người dùng gõ. */
function codesIn(question: string): string[] {
  const a = answerQuestion(question, data);
  const typed = new Set(question.toUpperCase().match(CODE) ?? []);
  return (
    [a.text, ...(a.lines ?? [])]
      .join(" ")
      .match(CODE)
      ?.filter((c) => !known.has(c) && !typed.has(c)) ?? []
  );
}

describe("answerQuestion", () => {
  it("vì sao có môn: hạng và lý do server trả, theo tên không dấu hoặc mã", () => {
    const a = answerQuestion("vi sao goi y lap trinh co ban", data);
    expect(a.text).toBe("Lập trình cơ bản (MAT2505) đứng hạng 1 trong gợi ý kỳ 3.");
    expect(a.lines).toEqual(data.items![0].reasons!.map((r) => r.text!));
    expect(answerQuestion("Vì sao có MAT2407?", data).text).toContain("hạng 7");
  });

  it("vì sao chưa có môn: câu chữ của not_selected và not_eligible", () => {
    expect(answerQuestion("Vì sao chưa có môn Phương trình vi phân?", data).text).toBe(data.not_selected![2].text);
    expect(answerQuestion("Vì sao chưa học được Học máy?", data).text).toBe(data.not_eligible![0].text);
  });

  it("tên dài khớp trước tên ngắn", () => {
    expect(answerQuestion("Giải tích 3 thì sao?", data).text).toBe(data.not_selected![1].text);
  });

  it("tín chỉ: dùng credit_window.text", () => {
    const a = answerQuestion("Kỳ này nên đăng ký bao nhiêu tín chỉ?", data);
    expect(a.text).toBe(data.credit_window.text);
    expect(a.lines).toEqual(["Danh sách gợi ý hiện có 2 môn."]);
  });

  it("còn thiếu điều kiện: liệt kê not_eligible", () => {
    const a = answerQuestion("Mình còn thiếu điều kiện gì?", data);
    expect(a.text).toBe("Có 1 môn chưa học được hoặc đã xong:");
    expect(a.lines).toEqual([data.not_eligible![0].text]);
    expect(answerQuestion("còn thiếu gì", { ...data, not_eligible: [] }).text).toContain("Không có môn nào");
  });

  it("bỏ môn: trả action skip để màn hình gọi lại API, môn ngoài danh sách thì không", () => {
    expect(answerQuestion("Bỏ môn Tối ưu hóa thì sao?", data).action).toEqual({ type: "skip", course_code: "MAT2407" });
    const notIn = answerQuestion("bỏ Học máy", data);
    expect(notIn.action).toBeUndefined();
    expect(notIn.text).toContain("không nằm trong danh sách gợi ý");
  });

  it("ngoài phạm vi: từ chối", () => {
    for (const q of ["Học xong làm nghề nghiệp gì?", "Dự đoán điểm Tối ưu hóa", "Mình có qua môn không?"]) {
      expect(answerQuestion(q, data).text).toContain("ngoài phạm vi");
    }
  });

  it("mã môn không có trong dữ liệu, câu không khớp, câu rỗng", () => {
    expect(answerQuestion("Vì sao chưa có INT9999?", data).text).toBe(
      "Không thấy môn INT9999 trong kết quả gợi ý lần này.",
    );
    expect(answerQuestion("thời tiết hôm nay", data).text).toContain("chưa hiểu");
    expect(answerQuestion("   ", data).action).toBeUndefined();
  });

  it("không bịa mã môn", () => {
    for (const q of [...suggestions(data), "Vì sao chưa có INT9999?", "bỏ MAT2505", "Học máy", "tín chỉ", "?"]) {
      expect(codesIn(q)).toEqual([]);
    }
  });

  it("câu hỏi mẫu chỉ nhắc tên môn có trong dữ liệu", () => {
    expect(suggestions(data)).toEqual([
      "Vì sao gợi ý môn Lập trình cơ bản?",
      "Vì sao chưa có môn Nhập môn Robotic?",
      "Kỳ này nên đăng ký bao nhiêu tín chỉ?",
      "Mình còn thiếu điều kiện gì?",
    ]);
    expect(suggestions({ ...data, items: [], not_selected: [], not_eligible: [] })).toHaveLength(2);
  });
});

describe("ChatPanel", () => {
  it("bấm câu hỏi mẫu, gõ câu hỏi, và bỏ môn gọi onSkip", async () => {
    const onSkip = vi.fn();
    function Host() {
      const [turns, setTurns] = useState<Turn[]>([]);
      return <ChatPanel data={data} turns={turns} setTurns={setTurns} onSkip={onSkip} />;
    }
    render(<Host />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Kỳ này nên đăng ký bao nhiêu tín chỉ?" }));
    expect(screen.getByText(data.credit_window.text)).toBeInTheDocument();

    const input = screen.getByRole("textbox", { name: "Câu hỏi về gợi ý" });
    expect(screen.getByRole("button", { name: "Hỏi" })).toBeDisabled();
    await user.type(input, "Bỏ môn MAT2407{Enter}");
    expect(onSkip).toHaveBeenCalledWith("MAT2407");
    expect(input).toHaveValue("");
    expect(screen.getByText(/Tối ưu hóa \(MAT2407\)/)).toBeInTheDocument();
  });
});
