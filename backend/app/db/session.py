import json
import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, List, Optional
from app.config import get_settings


def get_db_path() -> str:
    settings = get_settings()
    url = settings.database_url
    if url.startswith("sqlite:///"):
        path = url.replace("sqlite:///", "")
    elif url.startswith("sqlite://"):
        path = url.replace("sqlite://", "")
    else:
        path = "./interviewpilot.db"
    return os.path.abspath(path)


class DatabaseManager:
    """SQLite persistence manager for interview sessions and generated questions."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_db_path()
        self.init_db()

    @contextmanager
    def get_connection(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self):
        """Create database tables if they do not exist."""
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    current_question_index INTEGER NOT NULL DEFAULT 0,
                    total_questions INTEGER NOT NULL DEFAULT 5,
                    candidate_profile_json TEXT NOT NULL,
                    job_requirements_json TEXT NOT NULL,
                    competency_plan_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS questions (
                    question_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    order_index INTEGER NOT NULL,
                    competency TEXT NOT NULL,
                    difficulty TEXT NOT NULL,
                    question_text TEXT NOT NULL,
                    expected_criteria_json TEXT NOT NULL,
                    retrieved_chunk_ids_json TEXT NOT NULL,
                    retrieved_context_json TEXT,
                    follow_up_rationale TEXT,
                    status TEXT NOT NULL DEFAULT 'unanswered',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS evaluations (
                    evaluation_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    question_id TEXT NOT NULL UNIQUE,
                    candidate_answer TEXT NOT NULL,
                    evaluation_status TEXT NOT NULL,
                    correctness INTEGER NOT NULL,
                    completeness INTEGER NOT NULL,
                    relevance INTEGER NOT NULL,
                    clarity INTEGER NOT NULL,
                    weighted_score REAL NOT NULL,
                    strengths_json TEXT NOT NULL,
                    missing_concepts_json TEXT NOT NULL,
                    actionable_feedback TEXT NOT NULL,
                    citation_chunk_ids_json TEXT NOT NULL,
                    citations_json TEXT NOT NULL,
                    rubric_version TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
                    FOREIGN KEY(question_id) REFERENCES questions(question_id) ON DELETE CASCADE
                );
                """
            )


    # --- Session Operations ---

    def create_session(
        self,
        session_id: str,
        status: str,
        total_questions: int,
        candidate_profile: Dict[str, Any],
        job_requirements: Dict[str, Any],
        competency_plan: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions (
                    session_id, status, current_question_index, total_questions,
                    candidate_profile_json, job_requirements_json, competency_plan_json,
                    created_at, updated_at
                ) VALUES (?, ?, 0, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
                """,
                (
                    session_id,
                    status,
                    total_questions,
                    json.dumps(candidate_profile),
                    json.dumps(job_requirements),
                    json.dumps(competency_plan),
                ),
            )
        return self.get_session(session_id)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?;", (session_id,)
            ).fetchone()
            if not row:
                return None
            return {
                "session_id": row["session_id"],
                "status": row["status"],
                "current_question_index": row["current_question_index"],
                "total_questions": row["total_questions"],
                "candidate_profile": json.loads(row["candidate_profile_json"]),
                "job_requirements": json.loads(row["job_requirements_json"]),
                "competency_plan": json.loads(row["competency_plan_json"]),
                "created_at": str(row["created_at"]),
                "updated_at": str(row["updated_at"]),
            }

    def update_session_state(
        self,
        session_id: str,
        status: str,
        current_question_index: Optional[int] = None,
    ) -> bool:
        with self.get_connection() as conn:
            if current_question_index is not None:
                conn.execute(
                    """
                    UPDATE sessions
                    SET status = ?, current_question_index = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = ?;
                    """,
                    (status, current_question_index, session_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE sessions
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = ?;
                    """,
                    (status, session_id),
                )
            return True

    def list_all_sessions(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT s.*, 
                       (SELECT COUNT(*) FROM questions q WHERE q.session_id = s.session_id) as questions_created,
                       (SELECT COUNT(*) FROM evaluations e WHERE e.session_id = s.session_id) as questions_evaluated,
                       (SELECT AVG(e.weighted_score) FROM evaluations e WHERE e.session_id = s.session_id) as avg_score
                FROM sessions s
                ORDER BY s.created_at DESC;
                """
            ).fetchall()
            results = []
            for r in rows:
                profile = json.loads(r["candidate_profile_json"])
                job = json.loads(r["job_requirements_json"])
                results.append({
                    "session_id": r["session_id"],
                    "status": r["status"],
                    "current_question_index": r["current_question_index"],
                    "total_questions": r["total_questions"],
                    "candidate_name": profile.get("full_name") or profile.get("name") or "Candidate",
                    "job_title": job.get("job_title") or job.get("title") or "Technical Role",
                    "questions_created": r["questions_created"],
                    "questions_evaluated": r["questions_evaluated"],
                    "avg_score": round(r["avg_score"], 1) if r["avg_score"] is not None else None,
                    "created_at": str(r["created_at"]),
                    "updated_at": str(r["updated_at"]),
                })
            return results

    def delete_session(self, session_id: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM sessions WHERE session_id = ?;", (session_id,))
            return cursor.rowcount > 0


    # --- Question Operations ---

    def save_question(
        self,
        question_id: str,
        session_id: str,
        order_index: int,
        competency: str,
        difficulty: str,
        question_text: str,
        expected_criteria: List[str],
        retrieved_chunk_ids: List[str],
        retrieved_context: Optional[List[Dict[str, Any]]] = None,
        follow_up_rationale: Optional[str] = None,
    ) -> Dict[str, Any]:
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO questions (
                    question_id, session_id, order_index, competency, difficulty,
                    question_text, expected_criteria_json, retrieved_chunk_ids_json,
                    retrieved_context_json, follow_up_rationale, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'unanswered', CURRENT_TIMESTAMP);
                """,
                (
                    question_id,
                    session_id,
                    order_index,
                    competency,
                    difficulty,
                    question_text,
                    json.dumps(expected_criteria),
                    json.dumps(retrieved_chunk_ids),
                    json.dumps(retrieved_context or []),
                    follow_up_rationale,
                ),
            )
        return self.get_question(question_id)

    def get_question(self, question_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM questions WHERE question_id = ?;", (question_id,)
            ).fetchone()
            if not row:
                return None
            return {
                "question_id": row["question_id"],
                "session_id": row["session_id"],
                "order_index": row["order_index"],
                "competency": row["competency"],
                "difficulty": row["difficulty"],
                "question_text": row["question_text"],
                "expected_criteria": json.loads(row["expected_criteria_json"]),
                "retrieved_chunk_ids": json.loads(row["retrieved_chunk_ids_json"]),
                "retrieved_context": json.loads(row["retrieved_context_json"] or "[]"),
                "follow_up_rationale": row["follow_up_rationale"],
                "status": row["status"],
                "created_at": str(row["created_at"]),
            }

    def list_questions_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM questions WHERE session_id = ? ORDER BY order_index ASC;",
                (session_id,),
            ).fetchall()
            return [
                {
                    "question_id": r["question_id"],
                    "session_id": r["session_id"],
                    "order_index": r["order_index"],
                    "competency": r["competency"],
                    "difficulty": r["difficulty"],
                    "question_text": r["question_text"],
                    "expected_criteria": json.loads(r["expected_criteria_json"]),
                    "retrieved_chunk_ids": json.loads(r["retrieved_chunk_ids_json"]),
                    "retrieved_context": json.loads(r["retrieved_context_json"] or "[]"),
                    "follow_up_rationale": r["follow_up_rationale"],
                    "status": r["status"],
                    "created_at": str(r["created_at"]),
                }
                for r in rows
            ]

    def update_question_status(self, question_id: str, status: str) -> bool:
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE questions SET status = ? WHERE question_id = ?;",
                (status, question_id),
            )
            return True

    # --- Evaluation Operations ---

    def save_evaluation(
        self,
        evaluation_id: str,
        session_id: str,
        question_id: str,
        candidate_answer: str,
        evaluation_status: str,
        correctness: int,
        completeness: int,
        relevance: int,
        clarity: int,
        weighted_score: float,
        strengths: List[str],
        missing_concepts: List[str],
        actionable_feedback: str,
        citation_chunk_ids: List[str],
        citations: List[Dict[str, Any]],
        rubric_version: str = "1.0.0",
    ) -> Dict[str, Any]:
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO evaluations (
                    evaluation_id, session_id, question_id, candidate_answer,
                    evaluation_status, correctness, completeness, relevance, clarity,
                    weighted_score, strengths_json, missing_concepts_json,
                    actionable_feedback, citation_chunk_ids_json, citations_json,
                    rubric_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(question_id) DO UPDATE SET
                    evaluation_id = excluded.evaluation_id,
                    candidate_answer = excluded.candidate_answer,
                    evaluation_status = excluded.evaluation_status,
                    correctness = excluded.correctness,
                    completeness = excluded.completeness,
                    relevance = excluded.relevance,
                    clarity = excluded.clarity,
                    weighted_score = excluded.weighted_score,
                    strengths_json = excluded.strengths_json,
                    missing_concepts_json = excluded.missing_concepts_json,
                    actionable_feedback = excluded.actionable_feedback,
                    citation_chunk_ids_json = excluded.citation_chunk_ids_json,
                    citations_json = excluded.citations_json,
                    rubric_version = excluded.rubric_version,
                    created_at = CURRENT_TIMESTAMP;
                """,
                (
                    evaluation_id,
                    session_id,
                    question_id,
                    candidate_answer,
                    evaluation_status,
                    correctness,
                    completeness,
                    relevance,
                    clarity,
                    weighted_score,
                    json.dumps(strengths),
                    json.dumps(missing_concepts),
                    actionable_feedback,
                    json.dumps(citation_chunk_ids),
                    json.dumps(citations),
                    rubric_version,
                ),
            )
            # Also mark question as evaluated
            conn.execute(
                "UPDATE questions SET status = 'evaluated' WHERE question_id = ?;",
                (question_id,),
            )
        return self.get_evaluation(evaluation_id)

    def get_evaluation(self, evaluation_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM evaluations WHERE evaluation_id = ?;", (evaluation_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_evaluation_dict(row)

    def get_evaluation_for_question(self, question_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM evaluations WHERE question_id = ?;", (question_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_evaluation_dict(row)

    def list_evaluations_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM evaluations WHERE session_id = ? ORDER BY created_at ASC;",
                (session_id,),
            ).fetchall()
            return [self._row_to_evaluation_dict(r) for r in rows]

    def _row_to_evaluation_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "evaluation_id": row["evaluation_id"],
            "session_id": row["session_id"],
            "question_id": row["question_id"],
            "candidate_answer": row["candidate_answer"],
            "evaluation_status": row["evaluation_status"],
            "dimension_scores": {
                "correctness": row["correctness"],
                "completeness": row["completeness"],
                "relevance": row["relevance"],
                "clarity": row["clarity"],
            },
            "weighted_score": row["weighted_score"],
            "strengths": json.loads(row["strengths_json"]),
            "missing_concepts": json.loads(row["missing_concepts_json"]),
            "actionable_feedback": row["actionable_feedback"],
            "citation_chunk_ids": json.loads(row["citation_chunk_ids_json"]),
            "citations": json.loads(row["citations_json"]),
            "rubric_version": row["rubric_version"],
            "created_at": str(row["created_at"]),
        }


