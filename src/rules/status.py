"""Academic status rules for courses in a student's curriculum."""


def course_status(repo, student) -> dict[str, str]:
    """Return one status for every course in the student's curriculum.

    Prerequisite groups are ANDed, while alternatives within each group are ORed.
    Elective completion is based only on credits of passed courses in that block.
    """
    courses = repo.curriculum_courses(student["curriculum_code"])
    passed = set(student["passed_courses"])
    outstanding = set(student["outstanding_courses"])
    statuses = {code: "eligible" for code in courses["course_code"]}

    # Establish elective completion before the lower-priority prerequisite and retake rules.
    for _, block in repo.elective_blocks(student["curriculum_code"]).iterrows():
        block_code = block["block_code"]
        block_courses = courses[courses["elective_block"] == block_code]
        earned = block_courses[block_courses["course_code"].isin(passed)]["credits"].sum()
        if earned >= block["required_credits"]:
            for code in block_courses["course_code"]:
                if code not in passed:
                    statuses[code] = "block_complete"

    for _, course in courses.iterrows():
        code = course["course_code"]
        if code in passed:
            statuses[code] = "passed"
            continue
        if statuses[code] == "block_complete":
            continue
        groups = course["prerequisite_groups"]
        if any(not (set(group) & passed) for group in groups):
            statuses[code] = "missing_prerequisite"
        elif code in outstanding:
            statuses[code] = "retake"
    return statuses
