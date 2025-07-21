# online_models.py - 在线模型管理器
import os
import time
from typing import Optional, Dict, Any
import requests
import json

class OnlineModelManager:
    def __init__(self, model_type: str = "openai"):
        """
        初始化在线模型管理器
        model_type: "openai", "baidu", "aliyun", "zhipu", "deepseek"
        """
        self.model_type = model_type
        self.setup_model()
    
    def setup_model(self):
        """设置模型配置"""
        if self.model_type == "openai":
            self.api_key = os.getenv("OPENAI_API_KEY")
            self.base_url = "https://api.openai.com/v1/chat/completions"
            self.model_name = "gpt-3.5-turbo"
        elif self.model_type == "baidu":
            self.api_key = os.getenv("BAIDU_API_KEY")
            self.secret_key = os.getenv("BAIDU_SECRET_KEY")
            self.base_url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions"
            self.model_name = "ernie-bot-turbo"
        elif self.model_type == "aliyun":
            self.api_key = os.getenv("ALIYUN_API_KEY")
            self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
            self.model_name = "qwen-turbo"
        elif self.model_type == "zhipu":
            self.api_key = os.getenv("ZHIPU_API_KEY")
            self.base_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
            self.model_name = "glm-4"
        elif self.model_type == "deepseek":
            self.api_key = os.getenv("DEEPSEEK_API_KEY")
            self.base_url = "https://api.deepseek.com/v1/chat/completions"
            self.model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        else:
            raise ValueError(f"不支持的模型类型: {self.model_type}")
    
    def get_access_token(self) -> Optional[str]:
        """获取百度API访问令牌"""
        if self.model_type != "baidu":
            return None
        
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key
        }
        
        try:
            response = requests.post(url, params=params)
            response.raise_for_status()
            return response.json()["access_token"]
        except Exception as e:
            print(f"获取百度访问令牌失败: {e}")
            return None
    
    def generate_response(self, prompt: str, max_tokens: int = 256) -> Dict[str, Any]:
        """生成回答"""
        start_time = time.time()
        try:
            if self.model_type == "openai":
                return self._call_openai(prompt, max_tokens)
            elif self.model_type == "baidu":
                return self._call_baidu(prompt, max_tokens)
            elif self.model_type == "aliyun":
                return self._call_aliyun(prompt, max_tokens)
            elif self.model_type == "zhipu":
                return self._call_zhipu(prompt, max_tokens)
            elif self.model_type == "deepseek":
                return self._call_deepseek(prompt, max_tokens)
            else:
                return {
                    "success": False,
                    "error": f"未知模型类型: {self.model_type}",
                    "response": "",
                    "time": time.time() - start_time
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": "",
                "time": time.time() - start_time
            }
    
    def _call_openai(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        """调用OpenAI API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        response = requests.post(self.base_url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return {
            "success": True,
            "response": result["choices"][0]["message"]["content"],
            "time": time.time() - time.time(),
            "model": self.model_name
        }
    
    def _call_baidu(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        """调用百度文心API"""
        access_token = self.get_access_token()
        if not access_token:
            return {"success": False, "error": "无法获取访问令牌", "response": ""}
        
        url = f"{self.base_url}?access_token={access_token}"
        headers = {"Content-Type": "application/json"}
        
        data = {
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_output_tokens": max_tokens,
            "temperature": 0.7
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return {
            "success": True,
            "response": result["result"],
            "time": time.time() - time.time(),
            "model": self.model_name
        }
    
    def _call_aliyun(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        """调用阿里通义API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model_name,
            "input": {
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            },
            "parameters": {
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
        }
        
        response = requests.post(self.base_url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return {
            "success": True,
            "response": result["output"]["text"],
            "time": time.time() - time.time(),
            "model": self.model_name
        }
    
    def _call_zhipu(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        """调用智谱GLM API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        response = requests.post(self.base_url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return {
            "success": True,
            "response": result["choices"][0]["message"]["content"],
            "time": time.time() - time.time(),
            "model": self.model_name
        }

    def _call_deepseek(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        """调用DeepSeek API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        response = requests.post(self.base_url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        return {
            "success": True,
            "response": result["choices"][0]["message"]["content"],
            "time": time.time() - time.time(),
            "model": self.model_name
        }

def test_online_models():
    """测试在线模型"""
    print("=== 在线模型测试 ===")
    
    test_prompt = "请简要介绍一下人工智能的发展历史（100字以内）"
    
    models = ["openai", "baidu", "aliyun", "zhipu"]
    
    for model_type in models:
        print(f"\n测试 {model_type} 模型...")
        try:
            manager = OnlineModelManager(model_type)
            result = manager.generate_response(test_prompt)
            
            if result["success"]:
                print(f"✓ 成功 - 耗时: {result['time']:.2f}秒")
                print(f"回答: {result['response'][:100]}...")
            else:
                print(f"✗ 失败: {result['error']}")
                
        except Exception as e:
            print(f"✗ 初始化失败: {e}")

if __name__ == "__main__":
    test_online_models() 