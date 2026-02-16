"""ResearcherAgent - Searches FAISS vector store for Quran verses."""

from typing import Dict, Any, List
from google import genai
from google.genai.types import Tool, FunctionDeclaration, Content, Part
from src.rag.rag_manager import RAGManager
from src.observability.logging import logger


class ResearcherAgent:
    """Agent that searches the Quran knowledge base using RAG."""

    def __init__(self, rag_manager: RAGManager, model_name: str = "models/gemini-2.5-flash"):
        self.rag_manager = rag_manager
        self.model_name = model_name
        self.name = "ResearcherAgent"

        # Define the search tool for this agent
        self.search_tool = Tool(
            function_declarations=[
                FunctionDeclaration(
                    name="search_quran",
                    description=(
                        "Search the Quran knowledge base for verses related to a query. "
                        "Returns verse text with Surah:Ayah citations and semantic similarity scores."
                    ),
                    parameters={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query to find relevant Quran verses"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of results to return (default: 5)",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                )
            ]
        )

        logger.info(
            "Initialized ResearcherAgent",
            model=model_name
        )

    def search_quran(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """Execute the search_quran function."""
        try:
            logger.info(
                "ResearcherAgent searching Quran",
                query=query,
                top_k=top_k
            )

            results = self.rag_manager.retrieve(query, top_k=top_k)

            if not results:
                return {
                    "success": False,
                    "message": "No relevant verses found in the knowledge base",
                    "results": []
                }

            # Format results for agent
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "citation": result["citation"] or "Unknown",
                    "text": result["text"],
                    "surah": result["surah"],
                    "ayah": result["ayah"],
                    "relevance_score": 1.0 / (1.0 + result["distance"])  # Convert distance to similarity
                })

            logger.info(
                "ResearcherAgent found verses",
                num_results=len(formatted_results)
            )

            return {
                "success": True,
                "results": formatted_results,
                "query": query
            }

        except Exception as e:
            logger.error(
                "ResearcherAgent search failed",
                query=query,
                error=str(e)
            )
            return {
                "success": False,
                "message": f"Search failed: {str(e)}",
                "results": []
            }

    def process_message(self, message: str, client: genai.Client) -> str:
        """Process a message using the researcher agent.

        Args:
            message: User query
            client: Google GenAI client

        Returns:
            Agent's response
        """
        try:
            logger.info(
                "ResearcherAgent processing message",
                message_preview=message[:100]
            )

            # Create system instruction
            system_instruction = """You are a ResearcherAgent specializing in searching the Quran knowledge base.

Your role:
- Use the search_quran function to find relevant Quran verses
- Provide verse citations in the format Surah:Ayah
- Extract and present the most relevant verses
- Focus on accuracy and proper attribution

Always cite your sources with Surah:Ayah format."""

            # Start a chat session with tool
            chat = client.chats.create(
                model=self.model_name,
                config={
                    "system_instruction": system_instruction,
                    "tools": [self.search_tool],
                    "temperature": 0.3
                }
            )

            # Send initial message
            response = chat.send_message(message)

            # Handle function calls
            while response.candidates[0].content.parts:
                part = response.candidates[0].content.parts[0]

                if hasattr(part, 'function_call') and part.function_call:
                    function_call = part.function_call
                    function_name = function_call.name

                    logger.info(
                        "ResearcherAgent calling function",
                        function=function_name,
                        function_args=dict(function_call.args)
                    )

                    # Execute the function
                    if function_name == "search_quran":
                        result = self.search_quran(**dict(function_call.args))

                        # Send function response back
                        response = chat.send_message(
                            Part.from_function_response(
                                name=function_name,
                                response=result
                            )
                        )
                    else:
                        break
                else:
                    break

            # Extract final text response
            final_response = response.text

            logger.info(
                "ResearcherAgent completed processing",
                response_length=len(final_response)
            )

            return final_response

        except Exception as e:
            logger.error(
                "ResearcherAgent processing failed",
                error=str(e)
            )
            return f"I encountered an error while searching the Quran: {str(e)}"
