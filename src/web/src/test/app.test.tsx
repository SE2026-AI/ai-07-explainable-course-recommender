import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { expect, it } from "vitest";
import App from "../App";
import { createMockClient } from "../api/client";
function mount(
  path = "/profile",
  scenario: "success" | "empty" | "unavailable" = "success",
) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App client={createMockClient(scenario)} />
    </MemoryRouter>,
  );
}
it("submits profile, opens detail and requests blocked explanation", async () => {
  const user = userEvent.setup();
  mount();
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Gợi ý môn học" })).toBeEnabled(),
  );
  await user.click(screen.getByRole("button", { name: "Gợi ý môn học" }));
  expect(await screen.findByText("86%")).toBeInTheDocument();
  await user.click(screen.getByRole("link", { name: "Trí tuệ nhân tạo" }));
  expect(
    await screen.findByRole("heading", { name: "Môn tiên quyết bắt buộc" }),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "AI301" }));
  expect(await screen.findByTestId("whynot-result")).toHaveTextContent(
    "Thiếu môn tiên quyết",
  );
});
it("shows empty result after submission", async () => {
  mount("/profile", "empty");
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Gợi ý môn học" })).toBeEnabled(),
  );
  await userEvent.click(screen.getByRole("button", { name: "Gợi ý môn học" }));
  expect(
    await screen.findByText(/Không có môn nào đủ điều kiện học ngay/),
  ).toBeInTheDocument();
});
it("supports direct explain route and missing fixture feedback", async () => {
  mount("/explain");
  const button = await screen.findByRole("button", { name: "CS101" });
  await waitFor(() => expect(button).toBeEnabled());
  await userEvent.click(button);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Chưa có giải thích",
  );
});
it("shows catalog outage and retry control", async () => {
  mount("/profile", "unavailable");
  expect(await screen.findByRole("alert")).toHaveTextContent("unavailable");
  expect(screen.getByRole("button", { name: "Thử lại" })).toBeEnabled();
  expect(screen.getByRole("button", { name: "Gợi ý môn học" })).toBeDisabled();
});
it("handles unknown course deep links", async () => {
  mount("/course/UNKNOWN");
  expect(
    await screen.findByRole("heading", { name: "Không tìm thấy môn UNKNOWN" }),
  ).toBeInTheDocument();
});

it("marks results stale when profile changes", async () => {
  const user = userEvent.setup();
  mount();
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Gợi ý môn học" })).toBeEnabled(),
  );
  await user.click(screen.getByRole("button", { name: "Gợi ý môn học" }));
  await screen.findByText("86%");
  await user.click(screen.getByRole("link", { name: "Hồ sơ" }));
  await user.click(screen.getByRole("button", { name: "FAILED" }));
  await user.click(screen.getByRole("link", { name: "Kết quả" }));
  expect(screen.getByRole("status")).toHaveTextContent("Hồ sơ đã thay đổi");
  expect(screen.getByTestId("eligible-ST201")).toBeInTheDocument();
});
