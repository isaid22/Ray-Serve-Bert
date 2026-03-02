from typing import Any, Dict, List, Optional, Union
import asyncio

import torch
from transformers import AutoModel, AutoTokenizer
from ray import serve
from fastapi import FastAPI
from pydantic import BaseModel

# 1. Initialize FastAPI app
fastapi_app = FastAPI()

# 2. Define Pydantic Model for request validation
class EmbedRequest(BaseModel):
    text: Optional[str] = None
    texts: Optional[List[str]] = None

# 3. Add FastAPI ingress decorator
@serve.deployment(
    ray_actor_options={"num_gpus": 1},
    max_ongoing_requests=32,
    max_queued_requests=200,
)
@serve.ingress(fastapi_app)
class BertEmbedder:
    def __init__(self, model_name: str = "bert-base-uncased"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
        self.model = AutoModel.from_pretrained(model_name)

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        self.model.eval()

    @serve.batch(max_batch_size=32, batch_wait_timeout_s=0.01)
    async def embed(self, texts: List[Any]) -> List[Dict[str, Any]]:
        """
        IMPORTANT:
        - Ray collects many *single calls* into `texts: List[Any]`
        - You should return a list of results, same length as `texts`
        """
        # Normalize to List[str]
        norm_texts: List[str] = []
        for t in texts:
            if t is None:
                norm_texts.append("")
            elif isinstance(t, bytes):
                norm_texts.append(t.decode("utf-8", errors="ignore"))
            else:
                norm_texts.append(str(t))

        # Per-item validation (must return list of same length)
        results: List[Dict[str, Any]] = []
        good_positions: List[int] = []
        good_texts: List[str] = []

        for i, s in enumerate(norm_texts):
            if not s.strip():
                results.append({"error": "Text must be a non-empty string."})
            else:
                results.append({"_pending": True})
                good_positions.append(i)
                good_texts.append(s)

        if not good_texts:
            return results

        inputs = self.tokenizer(
            text=good_texts,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=256,
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            cls = outputs.last_hidden_state[:, 0, :]  # (B, H)

        embs = cls.detach().float().cpu().numpy()

        for j, pos in enumerate(good_positions):
            e = embs[j]
            results[pos] = {
                "model": "bert-base-uncased",
                "dim": int(e.shape[0]),
                "embedding": e.tolist(),
            }

        return results

    # 4. Use FastAPI route definition instead of the raw __call__ method
    @fastapi_app.post("/")
    async def handle_request(self, request: EmbedRequest) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        if request.text is not None:
            # Call batched method with ONE item (not a list)
            return await self.embed(request.text)
        elif request.texts is not None:
            if len(request.texts) == 0:
                return {"error": "Field 'texts' must be a non-empty list."}
            
            # For batch input, fan-out many single calls; Serve will batch them internally.
            return await asyncio.gather(*[self.embed(t) for t in request.texts])

        return {"error": "Provide either 'text' or 'texts'."}


deployment = BertEmbedder.bind()
