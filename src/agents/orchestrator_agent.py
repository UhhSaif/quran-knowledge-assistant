"""OrchestratorAgent - Routes queries and coordinates sub-agents."""

from typing import Dict, Any, List
from google import genai
from src.agents.researcher_agent import ResearcherAgent
from src.agents.context_agent import ContextAgent
from src.observability.logging import logger


class OrchestratorAgent:
    """Agent that orchestrates ResearcherAgent and ContextAgent."""

    def __init__(
        self,
        researcher_agent: ResearcherAgent,
        context_agent: ContextAgent,
        client: genai.Client,
        model_name: str = "models/gemini-2.5-flash"
    ):
        self.researcher_agent = researcher_agent
        self.context_agent = context_agent
        self.client = client
        self.model_name = model_name
        self.name = "OrchestratorAgent"

        logger.info(
            "Initialized OrchestratorAgent",
            model=model_name
        )

    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze query to determine which agents to use.

        Returns:
            Dict with needs_rag, needs_context, and query_type
        """
        query_lower = query.lower()

        # Determine if RAG search is needed
        needs_rag = any([
            "verse" in query_lower,
            "ayah" in query_lower,
            "surah" in query_lower,
            "what does" in query_lower,
            "find" in query_lower,
            "show me" in query_lower,
            "references to" in query_lower,
            "about" in query_lower
        ])

        # Determine if context/tafsir is needed
        needs_context = any([
            "context" in query_lower,
            "tafsir" in query_lower,
            "interpretation" in query_lower,
            "explanation" in query_lower,
            "why" in query_lower,
            "when" in query_lower,
            "historical" in query_lower,
            "revelation" in query_lower,
            "revealed" in query_lower,
            "background" in query_lower,
            "meaning" in query_lower,
            "scholar" in query_lower
        ])

        # Determine query type
        if "context" in query_lower or "revelation" in query_lower or "when" in query_lower:
            query_type = "context"
        elif "tafsir" in query_lower or "interpretation" in query_lower or "meaning" in query_lower:
            query_type = "tafsir"
        elif needs_rag:
            query_type = "verse_search"
        else:
            query_type = "general"

        # Default: use both if unclear
        if not needs_rag and not needs_context:
            needs_rag = True
            needs_context = False

        analysis = {
            "needs_rag": needs_rag,
            "needs_context": needs_context,
            "query_type": query_type
        }

        logger.info(
            "Query analysis completed",
            query_preview=query[:100],
            **analysis
        )

        return analysis

    def process_query(self, query: str) -> str:
        """Process user query using appropriate agents.

        Implements Sequential Flow: Orchestrator → Researcher → Context → Orchestrator
        And Hierarchical Delegation: Orchestrator manages sub-agents

        Args:
            query: User's question

        Returns:
            Combined response from agents
        """
        try:
            logger.info(
                "OrchestratorAgent processing query",
                query=query
            )

            # Analyze what the query needs
            analysis = self.analyze_query(query)

            responses = []

            # Step 1: Research phase - Get verses from RAG
            if analysis["needs_rag"]:
                logger.info("Delegating to ResearcherAgent")

                researcher_response = self.researcher_agent.process_message(
                    query,
                    self.client
                )
                responses.append({
                    "agent": "ResearcherAgent",
                    "response": researcher_response
                })

                logger.info(
                    "ResearcherAgent completed",
                    response_length=len(researcher_response)
                )

            # Step 2: Context phase - Get scholarly context
            if analysis["needs_context"]:
                logger.info("Delegating to ContextAgent")

                # Enhance context query with research findings if available
                context_query = query
                if responses:
                    context_query = f"{query}\n\nBased on these verses found:\n{responses[0]['response'][:500]}"

                context_response = self.context_agent.process_message(
                    context_query,
                    self.client
                )
                responses.append({
                    "agent": "ContextAgent",
                    "response": context_response
                })

                logger.info(
                    "ContextAgent completed",
                    response_length=len(context_response)
                )

            # Step 3: Synthesis phase - Combine and QA check
            if len(responses) > 1:
                # Both agents were used, synthesize responses
                final_response = self._synthesize_responses(query, responses)
            elif responses:
                # Single agent response
                final_response = responses[0]["response"]
            else:
                # Fallback
                final_response = "I'm not sure how to help with that query. Please try asking about Quranic verses or their interpretations."

            logger.info(
                "OrchestratorAgent completed processing",
                num_agents_used=len(responses),
                final_response_length=len(final_response)
            )

            return final_response

        except Exception as e:
            logger.error(
                "OrchestratorAgent processing failed",
                query=query,
                error=str(e)
            )
            return f"I encountered an error processing your query: {str(e)}"

    def _synthesize_responses(self, query: str, responses: List[Dict[str, Any]]) -> str:
        """Synthesize multiple agent responses into a coherent answer."""
        try:
            logger.info(
                "Synthesizing responses",
                num_responses=len(responses)
            )

            # Build synthesis prompt
            synthesis_prompt = f"""I asked multiple specialized agents about: "{query}"

Here are their responses:

"""
            for resp in responses:
                synthesis_prompt += f"**{resp['agent']}**:\n{resp['response']}\n\n"

            synthesis_prompt += """
Please synthesize these responses into a single, coherent answer that:
1. Combines the verse citations from ResearcherAgent with the scholarly context from ContextAgent
2. Provides a clear, organized response
3. Maintains all citations and sources
4. Answers the user's question comprehensively

Your synthesized response:"""

            # Use LLM to synthesize
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=synthesis_prompt,
                config={
                    "temperature": 0.4
                }
            )

            synthesized = response.text

            logger.info(
                "Synthesis completed",
                synthesized_length=len(synthesized)
            )

            return synthesized

        except Exception as e:
            logger.error(
                "Response synthesis failed",
                error=str(e)
            )
            # Fallback: just concatenate responses
            return "\n\n---\n\n".join([r["response"] for r in responses])
