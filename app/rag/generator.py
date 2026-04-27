"""
Answer generator using Google Gemini API.
Takes retrieved context chunks and generates a grounded answer with citations.
Falls back to context-only mode if no API key is configured.
"""

import logging
from typing import List, Optional

from app.config import settings
from app.models.schemas import SourceChunk

logger = logging.getLogger(__name__)

# System prompt for grounded financial reporting answers
SYSTEM_PROMPT = """You are ReportMaster AI, an expert financial reporting assistant. Your role is to provide accurate, 
professional answers about financial reporting standards, accounting procedures, and compliance requirements.

IMPORTANT RULES:
1. ONLY answer based on the provided context from the financial reporting manuals.
2. If the context does not contain enough information to answer the question, clearly state that.
3. Always cite the source document(s) in your answer using [Source: document_name] format.
4. Use professional accounting terminology and provide clear, structured answers.
5. When referencing specific standards (e.g., ASC 606, ASC 842), provide the relevant details.
6. Format your answers with clear headings and bullet points where appropriate.
7. If multiple documents are relevant, synthesize the information coherently.
8. Never make up information that is not in the provided context.

You are helping accounting professionals prepare accurate financial reports. Precision and compliance are paramount."""


class AnswerGenerator:
    """Generates grounded answers using Google Gemini API with retrieved context."""

    def __init__(self):
        self.api_key = settings.google_api_key
        self.model_name = "gemini-2.5-flash"
        self._model = None
        self._available = False
        self._initialize()

    def _initialize(self):
        """Initialize the Gemini model if API key is available."""
        if not self.api_key or self.api_key == "your_google_api_key_here":
            logger.warning(
                "Google API key not configured. Running in context-only mode. "
                "Set GOOGLE_API_KEY in .env file for AI-generated answers."
            )
            self._available = False
            return

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=SYSTEM_PROMPT
            )
            self._available = True
            logger.info(f"Gemini model '{self.model_name}' initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    def generate_answer(self, query: str, sources: List[SourceChunk]) -> str:
        """
        Generate a grounded answer based on query and retrieved source chunks.
        
        Args:
            query: The user's question
            sources: Retrieved source chunks with content and metadata
            
        Returns:
            Generated answer string
        """
        if not sources:
            return ("I could not find any relevant information in the financial reporting manuals "
                    "to answer your question. Please try rephrasing your query or ensure the "
                    "relevant documents have been indexed.")

        # Build context from retrieved chunks
        context = self._build_context(sources)

        if not self._available:
            return self._fallback_response(query, sources, context)

        try:
            prompt = self._build_prompt(query, context)
            response = self._model.generate_content(prompt)

            if response and response.text:
                return response.text.strip()
            else:
                logger.warning("Empty response from Gemini, using fallback")
                return self._fallback_response(query, sources, context)

        except Exception as e:
            logger.error(f"Error generating answer with Gemini: {e}")
            return self._fallback_response(query, sources, context)

    def _build_context(self, sources: List[SourceChunk]) -> str:
        """Build a formatted context string from source chunks."""
        context_parts = []
        for i, source in enumerate(sources, 1):
            context_parts.append(
                f"[Source {i}: {source.document_name} | Relevance: {source.relevance_score:.1%}]\n"
                f"{source.content}\n"
            )
        return "\n---\n".join(context_parts)

    def _build_prompt(self, query: str, context: str) -> str:
        """Build the full prompt for the LLM."""
        return (
            f"Based on the following context from financial reporting manuals, "
            f"answer the user's question accurately and professionally.\n\n"
            f"CONTEXT:\n{context}\n\n"
            f"QUESTION: {query}\n\n"
            f"Provide a comprehensive, well-structured answer with citations to the source documents. "
            f"If the context doesn't fully address the question, acknowledge the limitation."
        )

    def _fallback_response(self, query: str, sources: List[SourceChunk], context: str) -> str:
        """
        Generate a structured response without LLM when API key is not available.
        Returns the retrieved context in a readable format.
        """
        response_parts = [
            "📋 **Retrieved Information from Financial Reporting Manuals**\n",
            f"*Query: {query}*\n",
            "---\n",
            "The following relevant sections were found in the indexed manuals:\n\n"
        ]

        for i, source in enumerate(sources, 1):
            response_parts.append(
                f"### Source {i}: {source.document_name}\n"
                f"**Relevance Score:** {source.relevance_score:.1%}\n\n"
                f"{source.content}\n\n"
                f"---\n\n"
            )

        response_parts.append(
            "\n> **Note:** Running in context-retrieval mode. "
            "Configure a Google Gemini API key in the `.env` file to enable "
            "AI-powered answer synthesis with citations."
        )

        return ''.join(response_parts)
