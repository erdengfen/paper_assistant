#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上下文管理模块 - 提供智能的对话上下文处理
"""

import re
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import jieba
import jieba.analyse
import time

class ContextManager:
    def __init__(self, max_history_length: int = 10):
        self.max_history_length = max_history_length
        self.conversation_history = []
        self.topic_keywords = defaultdict(int)  # 话题关键词统计
        self.entity_mentions = defaultdict(int)  # 实体提及统计
        self.user_preferences = {}  # 用户偏好
        
    def add_conversation_turn(self, user_message: str, assistant_message: str):
        """添加一轮对话"""
        self.conversation_history.append({
            "user": user_message,
            "assistant": assistant_message,
            "timestamp": time.time()
        })
        
        # 保持历史长度
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history.pop(0)
        
        # 更新话题关键词
        self._update_topic_keywords(user_message, assistant_message)
        
        # 更新实体提及
        self._update_entity_mentions(user_message, assistant_message)
    
    def _update_topic_keywords(self, user_msg: str, assistant_msg: str):
        """更新话题关键词"""
        # 使用jieba提取关键词
        user_keywords = jieba.analyse.extract_tags(user_msg, topK=5)
        assistant_keywords = jieba.analyse.extract_tags(assistant_msg, topK=5)
        
        for keyword in user_keywords + assistant_keywords:
            self.topic_keywords[keyword] += 1
    
    def _update_entity_mentions(self, user_msg: str, assistant_msg: str):
        """更新实体提及统计"""
        # 简单的实体识别（可以根据需要改进）
        entities = re.findall(r'[A-Z][a-z]+|[一-龯]{2,}', user_msg + assistant_msg)
        for entity in entities:
            if len(entity) >= 2:
                self.entity_mentions[entity] += 1
    
    def get_recent_context(self, turns: int = 3) -> str:
        """获取最近的对话上下文"""
        if not self.conversation_history:
            return ""
        
        recent_turns = self.conversation_history[-turns:]
        context_parts = []
        
        for turn in recent_turns:
            context_parts.append(f"用户: {turn['user']}")
            context_parts.append(f"助手: {turn['assistant']}")
        
        return "\n".join(context_parts)
    
    def get_topic_keywords(self, top_k: int = 5) -> List[str]:
        """获取当前话题的关键词"""
        sorted_keywords = sorted(self.topic_keywords.items(), 
                               key=lambda x: x[1], reverse=True)
        return [kw for kw, count in sorted_keywords[:top_k]]
    
    def get_relevant_entities(self, top_k: int = 3) -> List[str]:
        """获取相关的实体"""
        sorted_entities = sorted(self.entity_mentions.items(), 
                               key=lambda x: x[1], reverse=True)
        return [entity for entity, count in sorted_entities[:top_k]]
    
    def enhance_query_with_context(self, query: str) -> str:
        """使用上下文增强查询"""
        if not self.conversation_history:
            return query
        
        # 获取相关上下文信息
        topic_keywords = self.get_topic_keywords(3)
        relevant_entities = self.get_relevant_entities(2)
        recent_context = self.get_recent_context(2)
        
        # 构建增强查询
        enhancement_parts = []
        
        if topic_keywords:
            enhancement_parts.append(f"话题关键词: {', '.join(topic_keywords)}")
        
        if relevant_entities:
            enhancement_parts.append(f"相关实体: {', '.join(relevant_entities)}")
        
        if recent_context:
            # 提取最近对话的关键信息
            context_summary = self._summarize_context(recent_context)
            enhancement_parts.append(f"对话背景: {context_summary}")
        
        if enhancement_parts:
            enhanced_query = f"{query} [上下文: {'; '.join(enhancement_parts)}]"
            return enhanced_query
        
        return query
    
    def _summarize_context(self, context: str) -> str:
        """总结上下文信息"""
        # 简单的上下文总结
        lines = context.split('\n')
        summary_parts = []
        
        for line in lines:
            if '用户:' in line:
                user_msg = line.replace('用户:', '').strip()
                if len(user_msg) > 10:
                    summary_parts.append(f"用户询问: {user_msg[:20]}...")
            elif '助手:' in line:
                assistant_msg = line.replace('助手:', '').strip()
                if len(assistant_msg) > 10:
                    summary_parts.append(f"助手回答: {assistant_msg[:20]}...")
        
        return '; '.join(summary_parts[-3:])  # 只保留最近3个要点
    
    def create_context_aware_prompt(self, query: str, reference_material: str) -> str:
        """创建具有上下文感知的prompt"""
        context = self.get_recent_context(3)
        topic_keywords = self.get_topic_keywords(3)
        
        if context and topic_keywords:
            prompt = f"""  你是一个中文学术助手，请用中文详细、充分、分点说明以下问题，400字以内：

当前对话背景：
{context}

讨论话题关键词：{', '.join(topic_keywords)}

参考资料：
{reference_material}

当前问题：{query}

请基于以上信息，特别是对话历史中的相关内容，给出准确、连贯的回答：

回答："""
        else:
            prompt = f"""  你是一个中文学术助手，请用中文详细、充分、分点说明以下问题，400字以内：

资料：{reference_material}

问题：{query}

回答："""
        
        return prompt
    
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history.clear()
        self.topic_keywords.clear()
        self.entity_mentions.clear()
    
    def get_context_stats(self) -> Dict:
        """获取上下文统计信息"""
        return {
            "history_length": len(self.conversation_history),
            "topic_keywords_count": len(self.topic_keywords),
            "entity_mentions_count": len(self.entity_mentions),
            "top_keywords": self.get_topic_keywords(5),
            "top_entities": self.get_relevant_entities(3)
        }

# 全局上下文管理器实例
context_manager = ContextManager()
