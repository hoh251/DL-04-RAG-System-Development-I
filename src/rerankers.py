

# Re-rank retrieved documents using a cross-encoder model.
#
# Why rerank?
# FAISS uses a bi-encoder for fast retrieval but may confuse similar topics.
# A cross-encoder scores each query-document pair together for higher accuracy.
#
# In practice:
# Retrieve the top 20 chunks, rerank them, then keep the best 3 results.
#
# Enable with config.USE_RERANK = True.
# Disabled by default because the model is large and slower than retrieval.



from sentence_transformers import CrossEncoder

import config


class Reranker:
    def __init__(self):
        print(f"[rerank] กำลังโหลดโมเดล {config.RERANK_MODEL_NAME} (ครั้งแรกอาจนาน) ...")
        self.model = CrossEncoder(config.RERANK_MODEL_NAME, device="cpu", max_length=512)

    def rerank(self, query, chunks, top_k=config.TOP_K):
        """
        เรียงลำดับ chunks ใหม่ตามความเกี่ยวข้องกับ query แล้วคืนแค่ top_k ชิ้น

        คะแนนเดิมจากขั้นค้นหาถูกเก็บไว้ในคีย์ retrieval_score
        เพื่อให้เทียบได้ว่า rerank เปลี่ยนอันดับไปยังไงบ้าง
        """
        if not chunks:
            return []

        # สร้างคู่ (คำถาม, ข้อความ) ให้โมเดลให้คะแนนทีละคู่
        pairs = [(query, chunk["text"]) for chunk in chunks]
        scores = self.model.predict(pairs, batch_size=4)

        results = []
        for chunk, score in zip(chunks, scores):
            chunk = dict(chunk)
            chunk["retrieval_score"] = chunk["score"]   # เก็บคะแนนเดิมไว้ดู
            chunk["score"] = float(score)               # ใช้คะแนนใหม่แทน
            results.append(chunk)

        results.sort(key=lambda chunk: chunk["score"], reverse=True)
        return results[:top_k]


def get_reranker():
    """
    คืน Reranker ถ้า config.USE_RERANK = True ไม่งั้นคืน None

    ถ้าเปิดใช้แล้วโหลดโมเดลไม่สำเร็จ จะรายงานข้อผิดพลาด ไม่ข้ามขั้นนี้แล้วนับว่าผ่าน
    """
    if not config.USE_RERANK:
        return None

    try:
        return Reranker()
    except Exception as error:
        raise RuntimeError("Reranking is enabled but its model could not be loaded.") from error
