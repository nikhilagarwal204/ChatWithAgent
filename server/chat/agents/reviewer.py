class ReviewerAgent:
    REVIEW_TEMPLATE = """Evaluate this response considering CONTEXT PRESENCE:
    {context_presence}
    
    1. Relevant to question: {question}?
    2. Uses document context properly (if provided)?
    3. Logically coherent?
    4. Appropriate completeness?
    5. Follows instructions?

    Response: {response}

    Answer ONLY in this format:
    1. YES/NO
    2. YES/NO
    3. YES/NO
    4. YES/NO
    5. YES/NO"""

    def __init__(self, llm):
        self.llm = llm

    async def evaluate_response(self, response, context, question):
        # Handle empty document context
        context_presence = (
            "Document context available"
            if context.get("documents")
            else "No documents provided"
        )

        evaluation_prompt = self.REVIEW_TEMPLATE.format(
            question=question, response=response, context_presence=context_presence
        )
        print("evaluation-prompt", evaluation_prompt)

        raw_eval = await self._get_evaluation(evaluation_prompt)
        print("evaluation-response", raw_eval)
        aspects = self._parse_evaluation(raw_eval, context)
        print("evaluation-aspects", aspects)
        return self._compile_review(aspects, response, context)

    async def _get_evaluation(self, prompt):
        response = await self.llm.agenerate([prompt])
        return response.generations[0][0].text.strip()

    def _parse_evaluation(self, raw_response, context):
        """Convert raw LLM response to boolean scores"""
        lines = [
            line.strip().upper() for line in raw_response.split("\n") if line.strip()
        ]

        # Auto-approve context check if no documents
        has_documents = bool(context.get("documents"))
        context_usage = (
            lines[1].startswith("2. YES")
            if has_documents and len(lines) > 1
            else True  # Auto-approve if no docs
        )

        return {
            "relevance": lines[0].startswith("1. YES") if len(lines) > 0 else False,
            "context_usage": context_usage,
            "coherence": lines[2].startswith("3. YES") if len(lines) > 2 else False,
            "completeness": lines[3].startswith("4. YES") if len(lines) > 3 else False,
            "instructions": lines[4].startswith("5. YES") if len(lines) > 4 else False,
        }

    def _compile_review(self, aspects, response, context):
        # Dynamic scoring based on context presence
        required_score = 3 if context.get("documents") else 2
        score = sum(aspects.values())
        print("score", score)

        if score >= required_score:
            return {"status": "approved", "response": response}

        feedback = self._generate_feedback(aspects, context)
        print("feedback", feedback)
        return {"status": "rejected", "feedback": feedback}

    def _generate_feedback(self, aspects, context):
        feedback_lines = []
        if not aspects["relevance"]:
            feedback_lines.append("- Improve relevance to question")
        if not aspects["context_usage"] and context.get("documents"):
            feedback_lines.append("- Better utilize document context")
        if not aspects["coherence"]:
            feedback_lines.append("- Improve logical flow")
        if not aspects["completeness"]:
            feedback_lines.append("- Provide more complete answer")
        if not aspects["instructions"]:
            feedback_lines.append("- Follow instructions carefully")

        return "Improvements needed:\n" + "\n".join(feedback_lines)
