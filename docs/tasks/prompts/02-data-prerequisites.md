# 02 — Data and prerequisite agent

With shared context and an accepted Gate A contract, implement the catalog/profile and prerequisite domain.

Allowed paths: src/backend/data/, src/backend/domain/catalog.*, profile.*, prerequisites.*, graph.*, test/backend/test_catalog*, test_profile*, test_prerequisites*, tools/generate_dataset.*, docs/architecture/DATASET.md. Adapt filenames to the accepted layout. Shared schemas/routes are owned according to the assignment, not automatically yours.

Build a small hand-verifiable fixture first, then expand to the agreed synthetic dataset target. Label every dataset as synthetic. Use a reproducible seed for generated records; do not inflate counts with meaningless duplicate courses.

Validate unique IDs, positive credits, bounded grades/workload, known references and acyclic prerequisite graph. Implement public interfaces for eligible(course, profile), missing_prerequisites, dependency paths and conditional unlocks. Follow passed-course policy. Already completed courses are not new recommendations.

Direct eligibility uses recorded completion of required courses. Transitive traversal explains missing learning paths; it must not retrospectively revoke a passed course because an ancestor is absent from synthetic history. Fail clearly on invalid catalog cycles/references.

Provide fixtures: no history; failed prerequisite; fully eligible; partially unlocked future course; invalid cycle; missing course reference. Implement meaningful unit checks for each and a deterministic generation check.

Handoff: public interface signatures, fixture IDs, data-generation command, actual verification results and integration instructions for agent 03. Do not modify ranking or web.
