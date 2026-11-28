// Types written against CONTRACT-2/PR #65, until OpenAPI includes /v2 (#62).
// Replace with generated types when that contract is exported; do not edit api/types.ts.
import type { Transcript, TranscriptBody } from "../transcript";

export interface User {
  user_id: string;
  email: string;
  role: "student" | "admin";
  created_at: string;
}
export interface Profile {
  university_code: "HUS";
  curriculum_code: string;
  cohort_year?: number;
  semesters_completed: number;
  updated_at: string;
}
export interface Session { user: User; profile: Profile | null }
export interface Credentials { email: string; password: string }
export interface ProfileIn { curriculum_code: string; cohort_year?: number }
export interface SavedTranscript extends TranscriptBody { curriculum_code: string; updated_at?: string }
export interface GraduationCondition {
  block_code: string;
  block_name: string;
  met: boolean;
  missing_courses: string[];
  text: string;
}
export interface Progress extends Transcript { graduation_conditions: GraduationCondition[] }
export interface AccountClient {
  readonly mode: "mock" | "live";
  register(body: Credentials): Promise<{ user: User }>;
  login(body: Credentials): Promise<{ user: User }>;
  logout(): Promise<void>;
  me(signal?: AbortSignal): Promise<Session>;
  password(body: { current_password: string; new_password: string }): Promise<void>;
  deleteAccount(body: { password: string }): Promise<void>;
  profile(body: ProfileIn): Promise<Profile>;
  transcript(signal?: AbortSignal): Promise<SavedTranscript>;
  saveTranscript(body: TranscriptBody): Promise<SavedTranscript>;
  progress(signal?: AbortSignal): Promise<Progress>;
  onUnauthenticated(callback: () => void): () => void;
}
