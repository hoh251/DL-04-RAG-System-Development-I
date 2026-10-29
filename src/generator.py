


# generator.py
# Generate answers with an LLM from retrieved documents.
# Disable USE_LLM to return retrieved text only.

import os
import re
import warnings
from datetime import date

from openai import OpenAI

import config
from src.prompt_templates import build_messages


class LLM:
    """เรียก LLM ผ่านไลบรารี openai (ใช้ได้ทั้ง ollama / openai / gemini)"""

    def __init__(self):
        self.provider = config.LLM_PROVIDER
        if config.LLM_PROVIDER not in config.LLM_PROVIDERS:
            raise ValueError("Unknown LLM provider; use ollama, openai or gemini.")
        base_url, default_model, key_name = config.LLM_PROVIDERS[config.LLM_PROVIDER]

        self.model = config.LLM_MODEL or default_model

        if not self.model:
            raise ValueError("Set RAG_LLM_MODEL to an available model from your provider; no cloud model is selected automatically.")
        if config.LLM_PROVIDER == "gemini" and self.model.startswith(("gemini-1.5", "gemini-2.0")):
            raise ValueError("This Gemini model family is retired. Choose a currently available model explicitly.")
        if config.LLM_PROVIDER == "openai" and self.model.startswith(("gpt-4o", "gpt-4.1")):
            if date.today() >= date(2027, 1, 14):
                raise ValueError("This legacy OpenAI model has reached its published retirement date.")
            warnings.warn("Legacy GPT-4 series: check the published January 14, 2027 retirement schedule.", RuntimeWarning)
        api_key = os.getenv(key_name) if key_name else "ollama"
        if self.provider == "gemini" and not api_key:
            api_key = os.getenv("GEMINI_API_KEY")
        if key_name and not api_key:
            alias = " or GEMINI_API_KEY" if self.provider == "gemini" else ""
            raise ValueError(f"Missing {key_name}{alias}. Set it in your local environment; do not put it in source files.")

        self.client = OpenAI(base_url=base_url, api_key=api_key,
                             timeout=config.LLM_TIMEOUT, max_retries=0)
        #print(f"[llm] use {config.LLM_PROVIDER} · model {self.model}")

    def chat(self, messages):
        #แล้วคืนคำตอบเป็น string
        options = {"model": self.model, "messages": messages}
        if self.provider == "openai":
            options["max_completion_tokens"] = config.LLM_MAX_TOKENS
        elif self.provider == "gemini":
            options["max_tokens"] = config.LLM_MAX_TOKENS
            options["reasoning_effort"] = "low"
        else:
            options["temperature"] = config.LLM_TEMPERATURE
            options["max_tokens"] = config.LLM_MAX_TOKENS
        response = self.client.chat.completions.create(**options)
        content = response.choices[0].message.content
        if not content or not content.strip():
            raise RuntimeError("LLM returned an empty answer.")
        return content.strip()


class NoLLM:

    model = "don't use LLM"

    def chat(self, messages):
        raise RuntimeError("NoLLM does not generate text or transform queries. Use Generator's extractive mode.")


def get_llm():
    if not config.USE_LLM:
        return NoLLM()

    return LLM()


class Generator:
    def __init__(self, llm):
        self.llm = llm

    def generate(self, question, chunks, history=""):

        # ค้นไม่เจออะไรเลย — ตอบว่าไม่รู้ ดีกว่าให้ LLM เดา
        if not chunks:
            return {
                "answer": config.NO_CONTEXT_MESSAGE,
                "sources": [],
                "no_context": True,
            }

        messages = build_messages(question, chunks, history)

        answer_mode = "llm"
        try:
            if isinstance(self.llm, NoLLM):
                answer = f"{chunks[0]['answer']} [1]"
                answer_mode = "extractive"
            else:
                answer = self.llm.chat(messages)
        except Exception as error:
            if not config.ALLOW_LLM_FALLBACK:
                raise RuntimeError(f"LLM generation failed ({type(error).__name__}). Check the server, model and credentials.") from error
            print(f"[llm] Request failed ({type(error).__name__}); using retrieved text.")
            answer = f"{chunks[0]['answer']} [1]"
            answer_mode = "extractive_fallback"

        if config.DISCLAIMER not in answer:
            answer = f"{answer}\n\n{config.DISCLAIMER}"

        return {
            "answer": answer.strip(),
            "sources": self.build_sources(chunks),
            "no_context": False,
            "answer_mode": answer_mode,
        }

    def build_sources(self, chunks):    #  สร้างรายการแหล่งอ้างอิง ให้เลข [1] [2] ตรงกับที่อยู่ใน prompt
        sources = []
        for number, chunk in enumerate(chunks, start=1):
            sources.append({
                "n": number,
                "chunk_id": chunk["chunk_id"],
                "question": chunk["question"],
                "line_no": chunk["line_no"],
                "score": round(float(chunk["score"]), 4),
            })
        return sources
