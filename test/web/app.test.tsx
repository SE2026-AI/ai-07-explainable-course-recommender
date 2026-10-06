// T-10 web journey. Expected values come from docs/tasks/prompts/fixtures/reference-scenarios.json
// (BASE: ST201/SE201 eligible, AI301 missing ST201), not from the UI implementation.
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import App from "@web/App";
import { ApiError, createMockClient, type ApiClient } from "@web/api/client";
import type { RecommendationResponse, SimulationResponse } from "@web/api/types";
import fixtures from "@web/api/fixtures/base.json";

const recorded = fixtures as unknown as { recommendations: RecommendationResponse; simulation: SimulationResponse };

function fakeClient(overrides: Partial<ApiClient>): ApiClient {
  return { ...createMockClient(0), mode: "live", ...overrides };
}

async function submit() {
  await userEvent.click(screen.getByRole("button", { name: /Gợi ý môn học/ }));
}

describe("web journey", () => {
  it("AC-1/AC-5: BASE in mock mode shows ST201+SE201 eligible and AI301 blocked by ST201, labeled MOCK", async () => {
    render(<App initialMode="mock" clientFor={() => createMockClient(0)} />);
    expect(screen.getByTestId("mock-badge")).toHaveTextContent("MOCK");
    await submit();
    await screen.findByTestId("eligible-ST201");
    expect(screen.getByTestId("eligible-SE201")).toBeInTheDocument();
    expect(screen.queryByTestId("eligible-AI301")).toBeNull();
    const ai = screen.getByTestId("ineligible-AI301");
    expect(within(ai).getAllByText(/ST201/).length).toBeGreaterThan(0); // reason text + prerequisite path
    expect(within(ai).queryByText(/%$/)).toBeNull(); // blocked courses carry no score
  });

  it("AC-3: a 422 field error is shown next to the field and no results are rendered", async () => {
    const client = fakeClient({
      recommend: async () => {
        throw new ApiError(422, "VALIDATION_ERROR", "Request failed validation.", false,
          { errors: [{ field: "profile.history.0.grade", message: "Input should be less than or equal to 10" }] });
      },
    });
    render(<App clientFor={() => client} />);
    await screen.findAllByText(/CS101 · /, { selector: "option" });
    await submit();
    expect(await screen.findByText(/Điểm CS101: Input should be less than or equal to 10/)).toBeInTheDocument();
    expect(screen.queryByTestId("eligible-ST201")).toBeNull();
  });

  it("AC-6: API unavailable keeps the draft profile and shows the status", async () => {
    const client = fakeClient({ recommend: async () => { throw new ApiError(0, "NETWORK_ERROR", "down", true); } });
    render(<App clientFor={() => client} />);
    await screen.findAllByText(/CS101 · /, { selector: "option" });
    const grade = screen.getByLabelText("Điểm CS101") as HTMLInputElement;
    await userEvent.clear(grade);
    await userEvent.type(grade, "9");
    await submit();
    expect(await screen.findByTestId("error-banner")).toHaveTextContent(/Không kết nối được tới API/);
    expect((screen.getByLabelText("Điểm CS101") as HTMLInputElement).value).toBe("9");
  });

  it("degraded responses are labeled, not shown as normal", async () => {
    const degraded = { ...recorded.recommendations, status: "degraded" as const,
      warnings: [{ code: "RANKING_UNAVAILABLE", message: "no ranking" }] };
    render(<App clientFor={() => fakeClient({ recommend: async () => degraded })} />);
    await screen.findAllByText(/CS101 · /, { selector: "option" });
    await submit();
    expect(await screen.findByTestId("degraded-banner")).toHaveTextContent("RANKING_UNAVAILABLE");
  });

  it("AC-2/AC-4: what-if shows the latest scenario only and leaves the baseline list unchanged", async () => {
    const pending: ((v: SimulationResponse) => void)[] = [];
    const client = fakeClient({
      recommend: async () => structuredClone(recorded.recommendations),
      simulate: () => new Promise<SimulationResponse>((resolve) => pending.push(resolve)),
    });
    render(<App clientFor={() => client} simulateDebounceMs={0} />);
    await screen.findAllByText(/CS101 · /, { selector: "option" });
    await submit();
    await screen.findByTestId("eligible-ST201");
    const baselineOrder = screen.getAllByTestId(/^eligible-/).map((el) => el.dataset.testid);

    const goal = screen.getByRole("slider", { name: /Mục tiêu/ });
    fireEvent.change(goal, { target: { value: "0.3" } });
    await waitFor(() => expect(pending.length).toBe(1));
    fireEvent.change(goal, { target: { value: "0.1" } });
    await waitFor(() => expect(pending.length).toBe(2));

    const make = (scoreAfter: number): SimulationResponse => ({
      ...recorded.simulation,
      changes: [{ course_id: "ST201", rank_before: 1, rank_after: 2, score_before: 0.778, score_after: scoreAfter, score_delta: scoreAfter - 0.778 }],
    });
    pending[1](make(0.5)); // newest resolves first
    pending[0](make(0.9)); // older resolves last and must be ignored
    const row = await screen.findByTestId("change-ST201");
    await waitFor(() => expect(row).toHaveTextContent("50.0%"));
    expect(row).not.toHaveTextContent("90.0%");
    expect(screen.getAllByTestId(/^eligible-/).map((el) => el.dataset.testid)).toEqual(baselineOrder);
  });

  it("marks results stale when the profile changes after submission", async () => {
    render(<App initialMode="mock" clientFor={() => createMockClient(0)} />);
    await submit();
    await screen.findByTestId("eligible-ST201");
    await userEvent.click(screen.getByRole("checkbox", { name: "AI" }));
    expect(screen.getByTestId("stale-banner")).toBeInTheDocument();
  });
});
