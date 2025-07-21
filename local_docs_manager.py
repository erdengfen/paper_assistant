import os
import pickle
import json
from typing import List, Dict, Optional
from pathlib import Path
import hashlib
from datetime import datetime
import re
from sentence_transformers import SentenceTransformer, util
import torch

class LocalDocsManager:
    def __init__(self, docs_dir: str = "local_docs"):
        self.docs_dir = Path(docs_dir)
        self.docs_dir.mkdir(exist_ok=True)
        
        # 文档索引文件
        self.index_file = self.docs_dir / "docs_index.json"
        
        # 加载现有索引
        self.docs_index = self._load_index()
        
        # 加载句向量模型（推荐多语言模型）
        self.embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        # 预先缓存所有文档的向量
        self.doc_embeddings = {}
        for doc_id, doc_info in self.docs_index.items():
            try:
                with open(doc_info["file_path"], 'r', encoding='utf-8') as f:
                    content = f.read()
                self.doc_embeddings[doc_id] = self.embedder.encode(content[:512], convert_to_tensor=True)
            except:
                continue
    
    def _load_index(self) -> Dict:
        """加载文档索引"""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_index(self):
        """保存文档索引"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.docs_index, f, ensure_ascii=False, indent=2)
    
    def add_document(self, title: str, content: str, source: str = "", url: str = "", category: str = "general"):
        """添加文档到本地资料库"""
        # 生成文档ID
        doc_id = hashlib.md5(f"{title}_{source}_{url}".encode()).hexdigest()
        
        # 创建分类目录
        category_dir = self.docs_dir / category
        category_dir.mkdir(exist_ok=True)
        
        # 保存文档内容
        doc_file = category_dir / f"{doc_id}.txt"
        with open(doc_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 更新索引
        self.docs_index[doc_id] = {
            "title": title,
            "source": source,
            "url": url,
            "category": category,
            "file_path": str(doc_file),
            "content_length": len(content),
            "added_time": datetime.now().isoformat(),
            "keywords": self._extract_keywords(content)
        }
        
        self._save_index()
        print(f"文档已添加: {title} (分类: {category})")
        return doc_id
    
    def _extract_keywords(self, content: str) -> List[str]:
        """提取文档关键词"""
        # 简单的关键词提取，可以根据需要改进
        words = re.findall(r'[\u4e00-\u9fff]+', content)
        # 过滤掉太短的词
        keywords = [word for word in words if len(word) >= 2]
        # 取前10个最常见的词
        from collections import Counter
        return [word for word, _ in Counter(keywords).most_common(10)]
    
    def search_documents(self, query: str, category: Optional[str] = None, top_k: int = 5) -> List[Dict]:
        """语义向量检索+原有关键词检索"""
        results = []
        query_embedding = self.embedder.encode(query, convert_to_tensor=True)
        sim_scores = {}
        for doc_id, doc_info in self.docs_index.items():
            if category and doc_info["category"] != category:
                continue
            doc_emb = self.doc_embeddings.get(doc_id)
            if doc_emb is not None:
                sim = util.pytorch_cos_sim(query_embedding, doc_emb).item()
                sim_scores[doc_id] = sim
        
        # 2. 关键词匹配（作为补充）
        query_keywords = self._extract_keywords(query)
        keyword_scores = {}
        
        for doc_id, doc_info in self.docs_index.items():
            if category and doc_info["category"] != category:
                continue
            
            # 计算关键词匹配度
            doc_keywords = doc_info.get("keywords", [])
            keyword_matches = sum(1 for kw in query_keywords if any(kw in dk for dk in doc_keywords))
            if keyword_matches > 0:
                keyword_scores[doc_id] = keyword_matches / len(query_keywords) if query_keywords else 0
        
        # 3. 合并两种分数
        final_scores = {}
        for doc_id in set(list(sim_scores.keys()) + list(keyword_scores.keys())):
            semantic_score = sim_scores.get(doc_id, 0)
            keyword_score = keyword_scores.get(doc_id, 0)
            # 语义分数权重0.7，关键词分数权重0.3
            final_scores[doc_id] = semantic_score * 0.7 + keyword_score * 0.3
        
        # 4. 取相似度最高的top_k
        top_doc_ids = sorted(final_scores, key=lambda x: float(final_scores.get(x, 0)), reverse=True)[:top_k]
        
        for doc_id in top_doc_ids:
            doc_info = self.docs_index[doc_id]
            try:
                with open(doc_info["file_path"], 'r', encoding='utf-8') as f:
                    content = f.read()
            except:
                content = ""
            results.append({
                "doc_id": doc_id,
                "title": doc_info["title"],
                "source": doc_info["source"],
                "url": doc_info["url"],
                "category": doc_info["category"],
                "score": final_scores[doc_id],
                "semantic_score": sim_scores.get(doc_id, 0),
                "keyword_score": keyword_scores.get(doc_id, 0),
                "content": content[:300]
            })
        return results
    
    def get_document_content(self, doc_id: str) -> Optional[str]:
        """获取文档完整内容"""
        if doc_id not in self.docs_index:
            return None
        
        try:
            with open(self.docs_index[doc_id]["file_path"], 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return None
    
    def list_documents(self, category: Optional[str] = None) -> List[Dict]:
        """列出所有文档"""
        docs = []
        for doc_id, info in self.docs_index.items():
            if category and info["category"] != category:
                continue
            docs.append({
                "doc_id": doc_id,
                "title": info["title"],
                "source": info["source"],
                "url": info["url"],
                "category": info["category"],
                "content_length": info["content_length"],
                "added_time": info["added_time"]
            })
        return docs
    
    def list_categories(self) -> List[str]:
        """列出所有分类"""
        categories = set()
        for info in self.docs_index.values():
            categories.add(info["category"])
        return sorted(list(categories))
    
    def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        if doc_id not in self.docs_index:
            return False
        
        try:
            # 删除文件
            file_path = Path(self.docs_index[doc_id]["file_path"])
            if file_path.exists():
                file_path.unlink()
            
            # 从索引中移除
            del self.docs_index[doc_id]
            self._save_index()
            return True
        except:
            return False
    
    def get_stats(self) -> Dict:
        """获取资料库统计信息"""
        stats = {
            "total_docs": len(self.docs_index),
            "categories": {},
            "total_size": 0
        }
        
        for info in self.docs_index.values():
            category = info["category"]
            if category not in stats["categories"]:
                stats["categories"][category] = 0
            stats["categories"][category] += 1
            stats["total_size"] += info["content_length"]
        
        return stats
