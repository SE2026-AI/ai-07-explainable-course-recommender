"""Schema cho catalog: trường, học kỳ, khung CTĐT, học phần và sơ đồ tiên quyết."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class UniversityOut(BaseModel):
    """Thông tin một trường đại học."""
    university_code: str
    name: str
    name_en: str | None = None
    short_name: str | None = None
    is_demo: bool


class TermOut(BaseModel):
    """Thông tin một học kỳ."""
    term_code: str
    term_no: int
    name: str
    academic_year_code: str
    start_year: int
    start_date: str | None = None
    end_date: str | None = None


BlockSelectionRule = Literal["all", "choose_credits", "container"]


class CurriculumBlockOut(BaseModel):
    """Thông tin một khối kiến thức trong khung CTĐT."""
    block_code: str
    block_name: str
    parent_block_code: str | None = None
    selection_rule: BlockSelectionRule
    required_credits: int
    counts_toward_total: bool
    note: str | None = None


class CurriculumSummaryOut(BaseModel):
    """Tóm tắt chương trình đào tạo."""
    curriculum_code: str
    university_code: str
    major_code: str
    major_name: str
    name: str
    program_type: str = "standard"
    effective_from_cohort: int
    effective_to_cohort: int | None = None
    total_credits: int
    standard_semesters: int
    max_credits_per_term: int
    pass_score: float
    max_score: float
    status: str


class CurriculumDetailOut(CurriculumSummaryOut):
    """Chi tiết chương trình đào tạo kèm cây khối kiến thức phẳng (mục 6.2)."""
    blocks: list[CurriculumBlockOut] = Field(default_factory=list)


class CourseItemOut(BaseModel):
    """Thông tin một học phần trong khung chương trình (mục 6.3)."""
    course_code: str
    course_name: str
    course_name_en: str | None = None
    credits: int
    teaching_language: str | None = None
    block_code: str
    block_name: str
    is_required: bool
    recommended_semester: int | None = None
    prerequisite_groups: list[list[str]] = Field(default_factory=list)
    primary_topic: str | None = None
    topics: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)


class CurriculumCoursesOut(BaseModel):
    """Danh sách học phần của khung CTĐT (mục 6.3)."""
    curriculum_code: str
    count: int
    courses: list[CourseItemOut]


class PrerequisiteGraphNode(BaseModel):
    """Một nút trong sơ đồ tiên quyết (mục 6.9)."""
    course_code: str
    course_name: str
    credits: int
    block_code: str
    recommended_semester: int | None = None


class PrerequisiteGraphEdge(BaseModel):
    """Một cạnh trong sơ đồ tiên quyết (mục 6.9)."""
    course_code: str
    group_no: int
    required_course_code: str


class PrerequisiteGraphOut(BaseModel):
    """Sơ đồ tiên quyết của khung chương trình đào tạo (mục 6.9)."""
    curriculum_code: str
    nodes: list[PrerequisiteGraphNode] = Field(default_factory=list)
    edges: list[PrerequisiteGraphEdge] = Field(default_factory=list)

