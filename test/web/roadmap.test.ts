// Demo roadmap ordering (client-side until a roadmap API exists). Catalog data: the recorded catalog-demo-v1 fixture.
import { describe, expect, it } from "vitest";
import fixtures from "@web/api/fixtures/base.json";
import type { CatalogCourse } from "@web/api/types";
import { planRoadmap, sortTerms } from "@web/lib/roadmap";
import { PRESETS } from "@web/lib/profile";

const courses = (fixtures as unknown as { courses: { items: CatalogCourse[] } }).courses.items;
const horizon = ["2027-FALL", "2028-SPRING", "2028-FALL"];

describe("planRoadmap", () => {
  it("READY: AI301 then DL401, one term apart (matches roadmap-complete example)", () => {
    const r = planRoadmap({ courses, history: PRESETS.READY.history, targets: ["AI301", "DL401"], horizon, maxCreditsPerTerm: 8 });
    expect(r.status).toBe("complete");
    expect(r.terms.map((t) => t.course_ids)).toEqual([["AI301"], ["DL401"], []]);
  });

  it("BASE: pulls in the missing prerequisite ST201 first and says why", () => {
    const r = planRoadmap({ courses, history: PRESETS.BASE.history, targets: ["AI301", "DL401"], horizon, maxCreditsPerTerm: 6 });
    expect(r.terms.map((t) => t.course_ids)).toEqual([["ST201"], ["AI301"], ["DL401"]]);
    expect(r.requiredBy.ST201).toEqual(["AI301"]);
  });

  it("reports what does not fit in the horizon", () => {
    const r = planRoadmap({ courses, history: PRESETS.BASE.history, targets: ["DL401"], horizon: ["2027-FALL"], maxCreditsPerTerm: 6 });
    expect(r.status).toBe("partial");
    expect(r.unscheduled).toEqual(["AI301", "DL401"]);
  });

  it("sorts term ids chronologically", () => {
    expect(sortTerms(["2028-FALL", "2027-FALL", "2028-SPRING", "2027-SPRING"])).toEqual(["2027-SPRING", "2027-FALL", "2028-SPRING", "2028-FALL"]);
  });
});
