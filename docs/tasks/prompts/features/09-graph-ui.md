# Prerequisite graph visualization feature
Read common-context.md and graph API fixtures. Implement prerequisite -> dependent visualization inside existing web architecture.
Allowed writes: assigned src/web/components/graph*, graph page/hooks, test/web/graph*. Coordinate shared routes/manifests with web owner.
Show completed, eligible and blocked nodes, selected course details, prerequisites and conditional unlocks. Distinguish direct/transitive relationships. Provide an accessible textual dependency alternative and usable small-screen layout. Avoid duplicating graph/eligibility business rules in the client. Add a graph library only when it materially simplifies the agreed interaction.
Acceptance: edge direction matches API fixture; selected node shows correct dependencies; blocked status matches backend; empty/error/loading states are explicit; keyboard/text fallback works. Handoff review steps, actual checks and limitations.
