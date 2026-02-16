"""Tavily API integration for web search."""

import os
from typing import List, Dict, Any
from tavily import TavilyClient
from src.observability.logging import logger


class WebSearchTool:
    """Web search tool using Tavily API."""

    def __init__(self):
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY environment variable must be set")

        self.client = TavilyClient(api_key=api_key)
        logger.info("Initialized Tavily web search tool")

    def search(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "advanced"
    ) -> List[Dict[str, Any]]:
        """Perform web search for scholarly information.

        Args:
            query: Search query
            max_results: Maximum number of results to return
            search_depth: "basic" or "advanced" search

        Returns:
            List of search results with title, url, content, and score
        """
        try:
            logger.info(
                "Performing web search",
                query=query,
                max_results=max_results,
                search_depth=search_depth
            )

            # Perform search
            response = self.client.search(
                query=query,
                max_results=max_results,
                search_depth=search_depth,
                include_answer=True,
                include_raw_content=False
            )

            # Format results
            results = []
            for result in response.get("results", []):
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "score": result.get("score", 0.0)
                })

            # Add the generated answer if available
            answer = response.get("answer", "")

            logger.info(
                "Web search completed",
                query=query,
                num_results=len(results),
                has_answer=bool(answer)
            )

            return {
                "results": results,
                "answer": answer,
                "query": query
            }

        except Exception as e:
            logger.error(
                "Web search failed",
                query=query,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    def search_for_tafsir(self, query: str) -> Dict[str, Any]:
        """Specialized search for Quranic tafsir and interpretations.

        Enhances the query with tafsir-specific terms.
        """
        enhanced_query = f"Quran tafsir interpretation {query}"

        logger.info(
            "Performing tafsir search",
            original_query=query,
            enhanced_query=enhanced_query
        )

        return self.search(
            query=enhanced_query,
            max_results=5,
            search_depth="advanced"
        )

    def search_for_context(self, surah: str, ayah: str = None) -> Dict[str, Any]:
        """Search for historical context of revelation.

        Args:
            surah: Surah number or name
            ayah: Optional ayah number
        """
        if ayah:
            query = f"Quran Surah {surah} Ayah {ayah} revelation context asbab al-nuzul"
        else:
            query = f"Quran Surah {surah} revelation context historical background"

        logger.info(
            "Performing context search",
            surah=surah,
            ayah=ayah,
            query=query
        )

        return self.search(
            query=query,
            max_results=5,
            search_depth="advanced"
        )
