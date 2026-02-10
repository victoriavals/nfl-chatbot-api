"""
RAG Service - Retrieval-Augmented Generation.

This module provides RAG functionality with knowledge base loading,
time-based activity detection, and augmented prompt building.
"""

import os
import random
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from config import APIConfig, debug_info, debug_error, debug_warning
from services.llm_service import get_llm_service, LLMResponse, LLMStatus
from services.memory_service import get_memory_service


class RAGService:
    """
    RAG Service for fal bot.
    
    Handles knowledge base loading, context building, and query processing.
    """
    
    def __init__(self) -> None:
        """Initialize the RAG service."""
        self.knowledge_base: str = self._load_knowledge_base()
        self.llm_service = get_llm_service()
        self.memory_service = get_memory_service()
        
        debug_info("[RAG] Service initialized")
        debug_info(f"[RAG] Knowledge base length: {len(self.knowledge_base)} characters")
    
    def _load_knowledge_base(self) -> str:
        """
        Load knowledge base from myData.md file.
        
        Returns:
            str: Content of the knowledge base
        """
        try:
            kb_path: str = APIConfig.KNOWLEDGE_BASE_PATH
            
            if os.path.exists(kb_path):
                with open(kb_path, 'r', encoding='utf-8') as f:
                    content: str = f.read()
                debug_info(f"[RAG] Loaded knowledge base from {kb_path}")
                return content
            else:
                debug_warning(f"[RAG] Knowledge base not found at {kb_path}")
                return self._get_default_knowledge_base()
                
        except Exception as e:
            debug_error(f"[RAG] Error loading knowledge base: {e}")
            return self._get_default_knowledge_base()
    
    def _get_default_knowledge_base(self) -> str:
        """
        Get default fallback knowledge base.
        
        Returns:
            str: Default knowledge base content
        """
        return """
# fal bot - Default Knowledge Base

## Identitas
* Nama AI: fal bot
* Representasi: Representasi digital dari Naufal
* Peran: AI Engineer & IoT Enthusiast

## Catatan
Knowledge base utama tidak ditemukan. Menggunakan fallback.
Jika ada pertanyaan di luar konteks, jawab:
"Wah aku gatau nih, tanya ke nomor Naufal langsung aja, tapi tunggu jawabannya."
"""
    
    def get_current_time_info(self) -> dict[str, any]:
        """
        Get current time info in WIB timezone.
        
        Returns:
            dict: Time information including hour, day, activity status
        """
        try:
            wib = ZoneInfo("Asia/Jakarta")
            now: datetime = datetime.now(wib)
        except Exception:
            # Fallback: manual UTC+7
            from datetime import timedelta
            now = datetime.utcnow() + timedelta(hours=7)
        
        hour: int = now.hour
        day: int = now.weekday()  # 0 = Monday, 6 = Sunday
        is_weekend: bool = day >= 5  # Saturday = 5, Sunday = 6
        
        day_names: list[str] = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
        
        return {
            "hour": hour,
            "day": day,
            "day_name": day_names[day],
            "is_weekend": is_weekend,
            "formatted_time": now.strftime("%H:%M"),
            "formatted_date": now.strftime("%A, %d %B %Y")
        }
    
    def get_activity_status(self, time_info: dict) -> str:
        """
        Determine activity status based on time.
        
        Args:
            time_info: Time information dictionary
            
        Returns:
            str: Current activity status
        """
        hour: int = time_info["hour"]
        is_weekend: bool = time_info["is_weekend"]
        
        # 23:00 - 06:00: Tidur
        if hour >= 23 or hour < 6:
            return "Tidur"
        
        # Weekend: Liburan
        if is_weekend:
            return "Liburan / Free Time"
        
        # Weekday 07:00 - 19:00: Kerja
        if 7 <= hour < 19:
            return "Bekerja (AI Engineer)"
        
        # Weekday 19:00 - 23:00: Kuliah S2
        if 19 <= hour < 23:
            return "Kuliah S2 / Belajar"
        
        return "Free Time"
    
    def _get_random_mood(self) -> str:
        """
        Generate a random mood/personality flavor for prompt variation.
        
        Each request gets a different mood injected, ensuring the LLM
        produces varied and creative responses.
        
        Returns:
            str: A random mood descriptor in Bahasa Indonesia.
        """
        moods: list[str] = [
            "Lagi semangat dan energik 🔥",
            "Santai dan chill vibes aja",
            "Agak iseng dan suka bercanda hari ini",
            "Lagi kalem dan thoughtful",
            "Excited banget, lagi good mood!",
            "Agak random dan playful",
            "Lagi fokus tapi tetap friendly",
            "Vibes-nya warm dan supportive",
            "Lagi seru-serunya, high energy",
            "Chill tapi informatif",
        ]
        return random.choice(moods)
    
    async def build_augmented_prompt(
        self, 
        user_query: str, 
        user_id: str,
        include_memory: bool = True
    ) -> str:
        """
        Build augmented prompt with knowledge base, time, memory, and random mood.
        
        Injects a randomized mood to ensure varied, creative responses.
        
        Args:
            user_query: The user's question
            user_id: User identifier for memory lookup
            include_memory: Whether to include conversation history
            
        Returns:
            str: Complete augmented prompt
        """
        time_info: dict = self.get_current_time_info()
        activity_status: str = self.get_activity_status(time_info)
        random_mood: str = self._get_random_mood()
        
        # Get conversation memory if enabled
        memory_context: str = ""
        if include_memory:
            memory_items = await self.memory_service.get_memory(user_id)
            if memory_items:
                memory_lines: list[str] = []
                for item in memory_items[-5:]:  # Last 5 messages
                    role: str = "User" if item["role"] == "user" else "fal bot"
                    memory_lines.append(f"{role}: {item['content']}")
                memory_context = "\n".join(memory_lines)
        
        prompt: str = f"""
=== CONTEXT ===
Waktu: {time_info['formatted_date']}, {time_info['formatted_time']} WIB
Status aktivitas Naufal: {activity_status}
Mood kamu sekarang: {random_mood}

=== KNOWLEDGE BASE ===
{self.knowledge_base}

=== CONVERSATION HISTORY ===
{memory_context if memory_context else "(Belum ada obrolan sebelumnya)"}

=== INSTRUKSI ===
Kamu adalah fal bot, representasi digital dari Naufal. Jawab berdasarkan Knowledge Base di atas.

ATURAN KREATIVITAS (WAJIB!):
1. Gaya bahasa SANTAI dan KASUAL — kayak chat sama teman.
2. WAJIB VARIASI: JANGAN pernah menjawab dengan kalimat yang persis sama. Selalu parafrase, ubah struktur kalimat, dan variasikan ekspresi.
3. Variasikan kata pembuka ("Nah", "Btw", "Oh itu", "Wah", "Jadi gini", "Hmm", dll). JANGAN selalu mulai dengan "Aku...".
4. Boleh elaborasi dan cerita ringan selama FAKTA tetap dari Knowledge Base.
5. Sesuaikan mood jawaban dengan: {random_mood}
6. Pertanyaan singkat → jawab singkat. Pertanyaan detail → jawab detail.
7. Boleh pakai emoji, humor ringan, dan filler words ("sih", "nih", "dong", "wkwk") supaya natural.

GUARDRAILS:
- Jika pertanyaan tentang aktivitas/jadwal, gunakan Status Aktivitas di atas.
- JANGAN mengarang fakta yang tidak ada di Knowledge Base.
- Jika pertanyaan di luar konteks, tolak dengan santai dan sarankan kontak Naufal langsung. VARIASIKAN cara menolaknya.
- Pertimbangkan riwayat percakapan untuk konteks.

=== PERTANYAAN USER ===
{user_query}

=== JAWABAN (kreatif, santai, JANGAN template) ===
""".strip()

        return prompt
    
    async def process_query(
        self, 
        user_id: str, 
        message: str,
        include_memory: bool = True
    ) -> LLMResponse:
        """
        Process user query with RAG pipeline.
        
        Args:
            user_id: Unique user identifier
            message: User's message
            include_memory: Whether to use conversation memory
            
        Returns:
            LLMResponse with result
        """
        debug_info(f"[RAG] Processing query for user: {user_id}")
        debug_info(f"[RAG] Message: {message[:50]}...")
        
        # Save user message to memory
        await self.memory_service.add_message(user_id, "user", message)
        
        try:
            # Build augmented prompt
            augmented_prompt: str = await self.build_augmented_prompt(
                user_query=message,
                user_id=user_id,
                include_memory=include_memory
            )
            
            # Query LLM
            response: LLMResponse = await self.llm_service.query(augmented_prompt)
            
            # Save assistant response to memory if successful
            if response.status == LLMStatus.SUCCESS and response.content:
                await self.memory_service.add_message(user_id, "assistant", response.content)
            
            return response
            
        except Exception as e:
            debug_error(f"[RAG] Error processing query: {e}")
            return LLMResponse(
                status=LLMStatus.ERROR,
                content=None,
                provider="RAG",
                model="None",
                error_message=str(e)
            )


# Singleton instance
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """
    Get or create the RAG service singleton.
    
    Returns:
        RAGService instance
    """
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
