import logging
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.interview import CompetencyPlanItem, GeneratedQuestion
from app.schemas.knowledge import SearchResultItem
from app.schemas.profile import CandidateProfile, JobRequirements
from app.services.groq_client import GroqClientService

logger = logging.getLogger(__name__)


class LLMQuestionPayload(BaseModel):
    """Schema expected from Groq LLM structured generation."""
    question_text: str = Field(..., description="The interview question text")
    expected_criteria: List[str] = Field(
        default_factory=list,
        description="3 to 5 key technical concepts/criteria the candidate should address"
    )
    follow_up_rationale: Optional[str] = Field(
        None,
        description="Rationale explaining why this question evaluates the target competency at this level"
    )


class QuestionGenerator:
    """
    Generates personalized, grounded technical interview questions
    based on candidate profile, job requirements, target competency, and retrieved RAG context.
    """

    def __init__(self, groq_client: Optional[GroqClientService] = None):
        self.groq_client = groq_client or GroqClientService()

    @staticmethod
    def plan_competencies(
        candidate_profile: CandidateProfile,
        job_requirements: JobRequirements,
        total_questions: int = 5,
    ) -> List[CompetencyPlanItem]:
        """
        Build an ordered interview competency plan balancing job requirements and candidate profile.
        Assigns progressive difficulty and scopes.
        """
        total = max(1, min(total_questions, 10))
        plan: List[CompetencyPlanItem] = []

        # 1. Gather competencies prioritizing job requirements
        seen = set()
        candidates_raw: List[Dict[str, str]] = []

        # Job requirements core competencies first
        for comp in job_requirements.core_competencies:
            normalized = comp.strip().lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                candidates_raw.append({"name": comp.strip(), "scope": "job_specific"})

        # Candidate profile primary competencies next
        for comp in candidate_profile.primary_competencies:
            normalized = comp.strip().lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                candidates_raw.append({"name": comp.strip(), "scope": "shared"})

        # Secondary fallback competencies if needed
        default_topics = [
            {"name": "System Architecture & Design", "scope": "shared"},
            {"name": "Concurrency & Asynchronous Processing", "scope": "shared"},
            {"name": "Database Design & Caching", "scope": "shared"},
            {"name": "Testing, Reliability & Error Handling", "scope": "shared"},
            {"name": "API Design & Performance Optimization", "scope": "shared"},
        ]
        for topic in default_topics:
            normalized = topic["name"].strip().lower()
            if normalized not in seen:
                seen.add(normalized)
                candidates_raw.append(topic)

        # 2. Select up to `total` items
        selected = candidates_raw[:total]

        # 3. Determine difficulty curve based on candidate experience
        years_exp = getattr(candidate_profile, "years_of_experience", None) or 3.0
        if years_exp >= 5.0:
            # Senior curve: Medium -> Medium -> Hard -> Medium -> Hard -> Hard ...
            difficulty_curve = ["Medium", "Medium", "Hard", "Medium", "Hard", "Hard", "Hard"]
        elif years_exp <= 2.0:
            # Junior curve: Easy -> Medium -> Medium -> Medium -> Hard -> Medium ...
            difficulty_curve = ["Easy", "Medium", "Medium", "Medium", "Hard", "Medium"]
        else:
            # Mid-level curve: Easy -> Medium -> Medium -> Hard -> Medium -> Hard ...
            difficulty_curve = ["Easy", "Medium", "Medium", "Hard", "Medium", "Hard"]

        for idx, item in enumerate(selected):
            difficulty = difficulty_curve[idx % len(difficulty_curve)]
            rationale = (
                f"Assessing core competency '{item['name']}' at {difficulty} level "
                f"matching candidate's ~{years_exp:.0f} years of experience."
            )
            plan.append(
                CompetencyPlanItem(
                    competency=item["name"],
                    difficulty=difficulty,
                    order_index=idx,
                    scope=item.get("scope", "shared"),
                    rationale=rationale,
                )
            )

        return plan

    def generate_question(
        self,
        session_id: str,
        order_index: int,
        competency: str,
        difficulty: str,
        candidate_profile: CandidateProfile,
        job_requirements: JobRequirements,
        retrieved_chunks: List[SearchResultItem],
        previous_questions: Optional[List[str]] = None,
        follow_up_rationale: Optional[str] = None,
    ) -> GeneratedQuestion:
        """
        Generate a structured, evidence-grounded question.
        Uses Groq if configured, with guaranteed deterministic fallback.
        Enforces backend ownership of source chunk IDs.
        """
        prev_q_list = previous_questions or []
        question_id = f"q_{uuid.uuid4().hex[:10]}"

        # Extract verified chunk IDs and summaries from retriever results
        # (The model cannot invent or hallucinate chunk IDs; backend supplies them)
        retrieved_chunk_ids = [c.chunk_id for c in retrieved_chunks]
        retrieved_context_summary = [
            {
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "source_name": c.source_name,
                "scope": c.scope,
                "topic": c.topic,
                "excerpt": c.text[:300].strip(),
            }
            for c in retrieved_chunks
        ]

        llm_payload: Optional[LLMQuestionPayload] = None

        if self.groq_client.is_configured:
            llm_payload = self._generate_with_groq(
                competency=competency,
                difficulty=difficulty,
                candidate_profile=candidate_profile,
                job_requirements=job_requirements,
                retrieved_chunks=retrieved_chunks,
                previous_questions=prev_q_list,
            )

        if not llm_payload:
            llm_payload = self._generate_deterministic_fallback(
                competency=competency,
                difficulty=difficulty,
                candidate_profile=candidate_profile,
                retrieved_chunks=retrieved_chunks,
                previous_questions=prev_q_list,
                order_index=order_index,
            )

        # Enforce duplicate avoidance check
        question_text = self._ensure_unique_question(llm_payload.question_text, prev_q_list)

        return GeneratedQuestion(
            question_id=question_id,
            session_id=session_id,
            order_index=order_index,
            competency=competency,
            difficulty=difficulty,
            question_text=question_text,
            expected_criteria=llm_payload.expected_criteria,
            retrieved_chunk_ids=retrieved_chunk_ids,
            retrieved_context=retrieved_context_summary,
            follow_up_rationale=llm_payload.follow_up_rationale or follow_up_rationale,
            status="unanswered",
        )

    def _generate_with_groq(
        self,
        competency: str,
        difficulty: str,
        candidate_profile: CandidateProfile,
        job_requirements: JobRequirements,
        retrieved_chunks: List[SearchResultItem],
        previous_questions: List[str],
    ) -> Optional[LLMQuestionPayload]:
        """Call Groq API with structured JSON output instructions."""
        system_prompt = (
            "You are a Staff Software Engineer conducting a rigorous technical interview. "
            "Formulate a deep, practical scenario-based interview question testing a specific technical "
            "competency at the designated difficulty level.\n\n"
            "STRICT RULES:\n"
            "1. Ground the question context in the provided technical reference excerpts.\n"
            "2. Tailor the scenario to the candidate's background without reciting their resume.\n"
            "3. Focus on architectural trade-offs, edge cases, performance, or concrete design decisions.\n"
            "4. NEVER repeat or rephrase topics already asked in previous questions.\n"
            "5. List 3 to 5 clear expected criteria/key concepts that an ideal answer must demonstrate.\n"
            "6. QUESTION FORMATTING:\n"
            "   - Format 'question_text' cleanly using structured Markdown:\n"
            "     * **Scenario:** A crisp 1-2 sentence real-world engineering situation or production context.\n"
            "     * **Technical Constraints:** Bullet points highlighting constraints, traffic scale, or trade-offs.\n"
            "     * **Question:** A direct, focused technical prompt for the candidate.\n"
            "   - Use backticks around code symbols, keywords, or APIs (e.g. `async def`, `Depends`, `Redis`, `useEffect`).\n"
            "   - Always use double line breaks between sections so the question renders as readable paragraphs instead of a continuous text block.\n"
            "7. Output MUST be valid JSON adhering strictly to the schema."
        )

        # Build context excerpt block
        context_block = ""
        for i, chunk in enumerate(retrieved_chunks[:3], 1):
            context_block += f"[Source {i}: {chunk.source_name} ({chunk.topic})]\n{chunk.text[:500]}\n\n"

        prev_q_block = "\n".join(f"- {q}" for q in previous_questions) if previous_questions else "None yet."

        cand_title = getattr(candidate_profile, "title", None) or (
            candidate_profile.experiences[0].title if getattr(candidate_profile, "experiences", None) else "Software Engineer"
        )
        years_exp = getattr(candidate_profile, "years_of_experience", None) or "3+"
        job_role = getattr(job_requirements, "job_title", None) or getattr(job_requirements, "title", None) or "Software Engineer"

        user_prompt = f"""
Candidate Profile:
- Role/Title: {cand_title}
- Years of Experience: {years_exp}
- Primary Competencies: {', '.join(candidate_profile.primary_competencies[:5])}

Job Requirements:
- Target Role: {job_role}
- Required Competencies: {', '.join(job_requirements.core_competencies[:5])}

Target Question Parameters:
- Competency to Test: {competency}
- Target Difficulty: {difficulty}

Previously Asked Questions (DO NOT DUPLICATE):
{prev_q_block}

Retrieved Technical Reference Documentation:
{context_block if context_block else 'General industry best practices and core engineering principles.'}

Please output a JSON object with:
- "question_text": The scenario-based interview question, formatted in clean Markdown with **Scenario:**, **Technical Constraints:** (bullet points), and **Question:** sections with code backticks.
- "expected_criteria": Array of 3-5 key technical concepts/trade-offs the candidate should cover.
- "follow_up_rationale": Short explanation of why this question fits this competency and difficulty.
"""
        return self.groq_client.extract_structured_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=LLMQuestionPayload,
        )

    def _generate_deterministic_fallback(
        self,
        competency: str,
        difficulty: str,
        candidate_profile: CandidateProfile,
        retrieved_chunks: List[SearchResultItem],
        previous_questions: List[str],
        order_index: int,
    ) -> LLMQuestionPayload:
        """
        Deterministic, offline fallback question generator.
        Provides robust questions grounded in the competency, difficulty, and retrieved context.
        """
        comp_lower = competency.lower()

        # Extract first reference excerpt if available
        first_excerpt = ""
        source_title = ""
        if retrieved_chunks:
            first_excerpt = retrieved_chunks[0].text[:200].replace("\n", " ")
            source_title = retrieved_chunks[0].source_name

        # Domain-specific curated scenarios
        if "python" in comp_lower or "fastapi" in comp_lower or "async" in comp_lower:
            if difficulty == "Easy":
                q_text = (
                    "**Scenario:**\n"
                    "You are building a modular backend service using FastAPI that handles database operations across multiple endpoints.\n\n"
                    "**Question:**\n"
                    "How does dependency injection with `Depends` work in FastAPI, and how does the framework manage "
                    "the lifecycle and automatic cleanup of database sessions or resources per request?"
                )
                criteria = [
                    "Yield fixtures and context management with Depends",
                    "Execution in the request scope and automatic exception cleanup",
                    "Separation of concerns between business logic and database sessions",
                ]
            elif difficulty == "Hard":
                q_text = (
                    "**Scenario:**\n"
                    "You are operating a high-throughput FastAPI service under heavy concurrent traffic where certain endpoints "
                    "rely on synchronous, CPU-bound parsing and legacy database drivers.\n\n"
                    "**Technical Constraints:**\n"
                    "- Synchronous blocking calls executed within Python's `asyncio` event loop.\n"
                    "- Threadpool sizing and latency spikes.\n\n"
                    "**Question:**\n"
                    "What happens to the event loop when blocking code runs directly inside an `async def` route versus a regular `def` route? "
                    "How do threadpools mitigate event loop starvation, and how would you tune worker processes?"
                )
                criteria = [
                    "Event loop starvation caused by blocking synchronous I/O",
                    "Differences between `async def` (runs on main event loop thread) and regular `def` (offloaded to threadpool)",
                    "`run_in_threadpool` or `asyncio.to_thread` usage for offloading CPU/blocking calls",
                    "Worker concurrency tuning with Uvicorn and Gunicorn worker processes",
                ]
            else:
                q_text = (
                    "**Scenario:**\n"
                    "You are designing an asynchronous backend API in FastAPI that handles high-concurrency read queries "
                    "while offloading heavy audit-logging tasks.\n\n"
                    "**Question:**\n"
                    "How does FastAPI's concurrency model handle I/O-bound operations using `async def` endpoints, "
                    "and what are the best practices for structuring non-blocking database queries and background tasks?"
                )
                criteria = [
                    "Cooperative multitasking via `await` on non-blocking async drivers",
                    "Use of `BackgroundTasks` for post-response operations without blocking response delivery",
                    "Avoiding mixing blocking sync calls inside async handlers without thread offloading",
                ]

        elif "react" in comp_lower or "frontend" in comp_lower or "state" in comp_lower:
            if difficulty == "Easy":
                q_text = (
                    "**Scenario:**\n"
                    "You are implementing interactive client components in React that synchronize with an external WebSocket subscription.\n\n"
                    "**Question:**\n"
                    "In modern React, how does the `useEffect` hook manage side effects and subscriptions? "
                    "Why is a cleanup function critical, and what happens if dependencies are omitted from the dependency array?"
                )
                criteria = [
                    "Execution timing after DOM paint and commit phases",
                    "Cleanup function invocation before unmount and prior to re-running the effect",
                    "Stale closures and infinite re-render loops caused by missing or incorrect dependencies",
                ]
            elif difficulty == "Hard":
                q_text = (
                    "**Scenario:**\n"
                    "You are building a real-time analytics dashboard in React with high-frequency telemetry updates "
                    "and deeply nested chart component trees.\n\n"
                    "**Technical Challenges:**\n"
                    "- Differentiating between urgent user inputs and non-urgent background render passes.\n"
                    "- Preventing UI tearing and render cascades.\n\n"
                    "**Question:**\n"
                    "How does React 18's Fiber reconciler differentiate between synchronous urgent updates and concurrent non-urgent transitions? "
                    "How would you prevent UI tearing and redundant render cascades across deep component trees?"
                )
                criteria = [
                    "React 18 Concurrent Features including `useTransition` and `useDeferredValue`",
                    "Fiber tree double-buffering (current vs work-in-progress trees) and interruptible rendering",
                    "Strategic state colocation and selective memoization (`useMemo`, `useCallback`, `memo`)",
                    "Context selector patterns or specialized external stores to avoid broad subscription invalidations",
                ]
            else:
                q_text = (
                    "**Scenario:**\n"
                    "You are architecting the client state architecture for a multi-page web application featuring "
                    "both complex local form flows and asynchronous server-persisted data.\n\n"
                    "**Question:**\n"
                    "When architecting state management in React, how do you decide between local component state, React Context, "
                    "and a dedicated server-state caching library? What are the performance implications of frequent context updates?"
                )
                criteria = [
                    "Context propagation re-rendering all consumer components regardless of prop consumption",
                    "Separation of transient client UI state from asynchronous server state cache",
                    "Techniques to isolate context providers or split state and dispatch contexts",
                ]

        elif "system design" in comp_lower or "architecture" in comp_lower or "caching" in comp_lower or "database" in comp_lower:
            if difficulty == "Hard":
                q_text = (
                    "**Scenario:**\n"
                    "You are designing a distributed caching tier with Redis in front of a primary relational database "
                    "experiencing unpredictable traffic spikes and cache invalidations.\n\n"
                    "**Technical Challenges:**\n"
                    "- Cache stampedes (dog-piling) on hot keys.\n"
                    "- Penetration of non-existent entity queries.\n"
                    "- Sudden TTL expiration avalanches.\n\n"
                    "**Question:**\n"
                    "How would you mitigate cache stampedes, penetration, and avalanche? Compare cache-aside versus "
                    "write-through patterns in terms of consistency guarantees and failure modes."
                )
                criteria = [
                    "Mutual exclusion locks or probabilistic early expiration (XFetch) for cache stampedes",
                    "Bloom filters or caching null results with short TTLs for cache penetration",
                    "Jittered TTLs to prevent simultaneous cache expiration avalanches",
                    "Eventual consistency trade-offs between cache-aside and write-through/write-behind",
                ]
            else:
                q_text = (
                    "**Scenario:**\n"
                    "You are scaling a relational database supporting a 95% read-heavy production workload with strict p99 latency SLA targets.\n\n"
                    "**Question:**\n"
                    "What strategies (indexing, read replicas, and caching tiers) would you deploy to maintain low query latency, "
                    "and how do you handle replication lag between primary and replica nodes?"
                )
                criteria = [
                    "B-tree index optimization and composite index column ordering",
                    "Read replica offloading and connection routing for read vs write operations",
                    "Addressing replication lag with sticky sessions or read-your-own-writes guarantees",
                ]

        elif "nexus" in comp_lower or "platform" in comp_lower:
            q_text = (
                "**Scenario:**\n"
                "You are architecting core platform microservices that handle distributed requests across untrusted network boundaries.\n\n"
                "**Question:**\n"
                "Regarding platform engineering standards, how do you design microservices for resilient inter-service "
                "communication, incorporating circuit breakers, idempotency keys, and structured distributed tracing?"
            )
            criteria = [
                "Circuit breaker states (Closed, Open, Half-Open) and fallback degraded responses",
                "Idempotency tokens to ensure safe retries on network failures",
                "Correlation IDs and OpenTelemetry propagation for end-to-end trace observability",
            ]

        else:
            # General fallback utilizing retrieved excerpt if available
            if first_excerpt:
                q_text = (
                    f"**Scenario:**\n"
                    f"In designing production systems for **{competency}** (referencing *{source_title or 'engineering standards'}*):\n\n"
                    f"> *\"{first_excerpt[:160]}...\"*\n\n"
                    f"**Question:**\n"
                    f"How would you approach implementing an architecture that satisfies these requirements at a **{difficulty}** level? "
                    f"What core trade-offs, fault-tolerance mechanisms, and operational edge cases must be managed?"
                )
            else:
                q_text = (
                    f"**Scenario:**\n"
                    f"You are tasked with leading technical design and implementation for **{competency}** at a **{difficulty}** level.\n\n"
                    f"**Question:**\n"
                    f"How would you approach designing and implementing this architecture to ensure low latency, "
                    f"fault tolerance, and maintainability? Outline your key trade-offs and component boundaries."
                )
            criteria = [
                f"Core architectural considerations for {competency}",
                "Failure handling, resilience, and operational observability",
                f"Appropriate technical trade-offs suited for a {difficulty.lower()} technical standard",
            ]

        return LLMQuestionPayload(
            question_text=q_text,
            expected_criteria=criteria,
            follow_up_rationale=(
                f"Assessing technical depth in {competency} at {difficulty} level "
                f"for question #{order_index + 1}."
            ),
        )

    def _ensure_unique_question(self, question_text: str, previous_questions: List[str]) -> str:
        """
        Check if the generated question is a duplicate of any previously asked question.
        If duplicate or near-duplicate, append a distinguishing technical angle.
        """
        normalized_new = set(question_text.lower().split())

        for prev in previous_questions:
            normalized_prev = set(prev.lower().split())
            if not normalized_new or not normalized_prev:
                continue
            # Jaccard overlap
            overlap = len(normalized_new & normalized_prev) / len(normalized_new | normalized_prev)
            if overlap > 0.8 or question_text.strip().lower() == prev.strip().lower():
                logger.info(f"Duplicate question detected with overlap {overlap:.2f}. Adding operational focus.")
                return (
                    f"{question_text} Additionally, discuss how you would monitor this in production, "
                    f"handle degraded states, and recover from unexpected runtime failures."
                )

        return question_text
