from langchain.prompts import PromptTemplate


class ProducerAgent:
    def __init__(self, llm):
        self.llm = llm
        self.template = """
        <|im_start|>system
        You are a helpful AI assistant. Below is the content from uploaded documents and our conversation history.
        DOCUMENTS CONTENT:
        {documents}
        CONVERSATION HISTORY:
        {history}
        {feedback}
        INSTRUCTIONS:
        1. Provide accurate, detailed responses based on context
        2. Maintain conversational flow
        3. Address all aspects of the user's query
        4. If unsure, ask clarifying questions
        <|im_end|>
        <|im_start|>user
        {question}
        <|im_end|>
        <|im_start|>assistant
        """

    def _build_prompt(self, context, question, feedback):
        history_text = "\n".join(
            f"{msg.__class__.__name__.replace('Message', '')}: {msg.content}"
            for msg in context["history"]
        )

        # Context-aware instructions
        doc_presence = (
            "Utilize document context where applicable"
            if context["documents"]
            else "No documents available - rely on general knowledge"
        )

        feedback_section = (
            f"FEEDBACK FROM PREVIOUS ATTEMPT:\n{feedback}\n"
            if feedback
            else "Provide a natural conversational response"
        )

        return PromptTemplate(
            input_variables=["documents", "history", "question"], template=self.template
        ).format(
            documents=context["documents"] or "No documents available",
            history=history_text,
            question=question,
            feedback=f"{feedback_section}\n{doc_presence}",
        )

    async def generate_response(self, context, question, feedback=None):
        prompt = self._build_prompt(context, question, feedback)
        print("producer-prompt", prompt)
        response = await self.llm.agenerate([prompt])
        print("producer-response", response)
        return response.generations[0][0].text.strip()
