"""ContextAgent - Uses Tavily API for scholarly tafsir and context."""

from typing import Dict, Any
from google import genai
from google.genai.types import Tool, FunctionDeclaration, Content, Part
from src.tools.web_search import WebSearchTool
from src.observability.logging import logger


class ContextAgent:
    """Agent that provides scholarly context and tafsir using web search."""

    def __init__(self, web_search_tool: WebSearchTool, model_name: str = "models/gemini-2.5-flash"):
        self.web_search_tool = web_search_tool
        self.model_name = model_name
        self.name = "ContextAgent"

        # Define tools for this agent
        self.tools = Tool(
            function_declarations=[
                FunctionDeclaration(
                    name="search_tafsir",
                    description=(
                        "Search for scholarly tafsir (interpretations) and explanations "
                        "of Quranic verses or concepts from Islamic scholars."
                    ),
                    parameters={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The topic or verse to get tafsir for"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                FunctionDeclaration(
                    name="search_historical_context",
                    description=(
                        "Search for historical context of revelation (asbab al-nuzul) "
                        "for specific Surah or Ayah."
                    ),
                    parameters={
                        "type": "object",
                        "properties": {
                            "surah": {
                                "type": "string",
                                "description": "Surah number or name"
                            },
                            "ayah": {
                                "type": "string",
                                "description": "Ayah number (optional)"
                            }
                        },
                        "required": ["surah"]
                    }
                )
            ]
        )

        logger.info(
            "Initialized ContextAgent",
            model=model_name
        )

    def search_tafsir(self, query: str) -> Dict[str, Any]:
        """Search for tafsir and scholarly interpretations."""
        try:
            logger.info(
                "ContextAgent searching tafsir",
                query=query
            )

            result = self.web_search_tool.search_for_tafsir(query)

            if not result.get("results"):
                return {
                    "success": False,
                    "message": "No tafsir results found",
                    "sources": []
                }

            # Format for agent consumption
            formatted = {
                "success": True,
                "answer": result.get("answer", ""),
                "sources": []
            }

            for res in result["results"]:
                formatted["sources"].append({
                    "title": res["title"],
                    "url": res["url"],
                    "content": res["content"][:500],  # Limit content length
                    "relevance": res["score"]
                })

            logger.info(
                "ContextAgent found tafsir",
                num_sources=len(formatted["sources"])
            )

            return formatted

        except Exception as e:
            logger.error(
                "ContextAgent tafsir search failed",
                error=str(e)
            )
            return {
                "success": False,
                "message": f"Tafsir search failed: {str(e)}",
                "sources": []
            }

    def search_historical_context(self, surah: str, ayah: str = None) -> Dict[str, Any]:
        """Search for historical context of revelation."""
        try:
            logger.info(
                "ContextAgent searching historical context",
                surah=surah,
                ayah=ayah
            )

            result = self.web_search_tool.search_for_context(surah, ayah)

            if not result.get("results"):
                return {
                    "success": False,
                    "message": "No historical context found",
                    "sources": []
                }

            # Format for agent consumption
            formatted = {
                "success": True,
                "answer": result.get("answer", ""),
                "sources": []
            }

            for res in result["results"]:
                formatted["sources"].append({
                    "title": res["title"],
                    "url": res["url"],
                    "content": res["content"][:500],
                    "relevance": res["score"]
                })

            logger.info(
                "ContextAgent found historical context",
                num_sources=len(formatted["sources"])
            )

            return formatted

        except Exception as e:
            logger.error(
                "ContextAgent historical search failed",
                error=str(e)
            )
            return {
                "success": False,
                "message": f"Historical context search failed: {str(e)}",
                "sources": []
            }

    def process_message(self, message: str, client: genai.Client) -> str:
        """Process a message using the context agent.

        Args:
            message: User query
            client: Google GenAI client

        Returns:
            Agent's response
        """
        try:
            logger.info(
                "ContextAgent processing message",
                message_preview=message[:100]
            )

            # Create system instruction
            system_instruction = """You are a ContextAgent specializing in providing scholarly context and tafsir for Quranic content.

Your role:
- Use search_tafsir to find scholarly interpretations and explanations
- Use search_historical_context to find the circumstances of revelation (asbab al-nuzul)
- Synthesize information from multiple scholarly sources
- Always cite your web sources
- Provide balanced perspectives from different Islamic scholars

Focus on academic and scholarly sources when available."""

            # Start a chat session with tools
            chat = client.chats.create(
                model=self.model_name,
                config={
                    "system_instruction": system_instruction,
                    "tools": [self.tools],
                    "temperature": 0.4
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
                        "ContextAgent calling function",
                        function=function_name,
                        function_args=dict(function_call.args)
                    )

                    # Execute the appropriate function
                    if function_name == "search_tafsir":
                        result = self.search_tafsir(**dict(function_call.args))
                    elif function_name == "search_historical_context":
                        result = self.search_historical_context(**dict(function_call.args))
                    else:
                        result = {"error": f"Unknown function: {function_name}"}

                    # Send function response back
                    response = chat.send_message(
                        Part.from_function_response(
                            name=function_name,
                            response=result
                        )
                    )
                else:
                    break

            # Extract final text response
            final_response = response.text

            logger.info(
                "ContextAgent completed processing",
                response_length=len(final_response)
            )

            return final_response

        except Exception as e:
            logger.error(
                "ContextAgent processing failed",
                error=str(e)
            )
            return f"I encountered an error while searching for context: {str(e)}"
