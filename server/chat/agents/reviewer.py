class ReviewerAgent:
    REVIEW_TEMPLATE = """Evaluate this response STRICTLY in YES/NO format:
    1. Relevant to question: {question}?
    2. Uses document context properly if given?
    3. Logically coherent?
    4. Complete answer?
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
        evaluation_prompt = self.REVIEW_TEMPLATE.format(
            question=question, response=response
        )
        print("evaluation-prompt", evaluation_prompt)

        raw_eval = await self._get_evaluation(evaluation_prompt)
        print("evaluation-response", raw_eval)
        aspects = self._parse_evaluation(raw_eval)
        print("evaluation-aspects", aspects)
        return self._compile_review(aspects, response)

    async def _get_evaluation(self, prompt):
        response = await self.llm.agenerate([prompt])
        return response.generations[0][0].text.strip()

    def _parse_evaluation(self, raw_response):
        """Convert raw LLM response to boolean scores"""
        lines = [
            line.strip().upper() for line in raw_response.split("\n") if line.strip()
        ]
        return {
            "relevance": lines[0].startswith("1. YES") if len(lines) > 0 else False,
            "context_usage": lines[1].startswith("2. YES") if len(lines) > 1 else False,
            "coherence": lines[2].startswith("3. YES") if len(lines) > 2 else False,
            "completeness": lines[3].startswith("4. YES") if len(lines) > 3 else False,
            "instructions": lines[4].startswith("5. YES") if len(lines) > 4 else False,
        }

    def _compile_review(self, aspects, response):
        score = sum(aspects.values())
        print("score", score)
        if score >= 3:  # Require 3/5 positives
            return {"status": "approved", "response": response}

        feedback = "Improvements needed:\n" + "\n".join(
            f"- {reason}"
            for aspect, reason in [
                ("relevance", "Not relevant to question"),
                ("context_usage", "Poor document context usage"),
                ("coherence", "Lacks logical flow"),
                ("completeness", "Incomplete answer"),
                ("instructions", "Didn't follow instructions"),
            ]
            if not aspects[aspect]
        )
        print("feedback", feedback)

        return {"status": "rejected", "feedback": feedback}
