# app.py
from re import T
import time
import os
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain_community.llms import HuggingFacePipeline
from rag_utils import fetch_web_documents, split_documents, embed_documents
from local_docs_manager import LocalDocsManager
from online_models import OnlineModelManager
from context_manager import context_manager

# 加载环境变量
load_dotenv()

MODEL_TYPE = "deepseek"  # 在这里修改模型类型

# 全局变量，便于外部import
model_type = None
online_manager = None
tokenizer = None
model = None
memory = None
conversation = None

# 初始化模型
if MODEL_TYPE == "local":
    print("加载本地模型...")
    start_time = time.time()
    tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen1.5-1.8B-Chat", trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        "Qwen/Qwen1.5-1.8B-Chat",
        trust_remote_code=True
    ).to("cuda").eval()

    # 封装为 LangChain 接口
    pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, device=0, max_new_tokens=256, truncation=True, return_full_text=False)
    llm = HuggingFacePipeline(pipeline=pipe)
    
    memory = ConversationBufferMemory()
    conversation = ConversationChain(llm=llm, memory=memory, verbose=False)
    
    print(f"本地模型加载完成，耗时: {time.time() - start_time:.2f}秒")
    model_type = "local"
    online_manager = None
else:
    print(f"初始化在线模型: {MODEL_TYPE}")
    try:
        online_manager = OnlineModelManager(MODEL_TYPE)
        model_type = "online"
        print(f"在线模型初始化成功: {MODEL_TYPE}")
        tokenizer = None
        model = None
        memory = ConversationBufferMemory()  # 依然初始化memory，便于上下文管理
        conversation = None
    except Exception as e:
        print(f"在线模型初始化失败: {e}")
        print("回退到本地模型...")
        
        start_time = time.time()
        tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen1.5-1.8B-Chat", trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen1.5-1.8B-Chat",
            trust_remote_code=True
        ).to("cuda").eval()

        pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, device=0, max_new_tokens=256, truncation=True, return_full_text=False)
        llm = HuggingFacePipeline(pipeline=pipe)
        
        memory = ConversationBufferMemory()
        conversation = ConversationChain(llm=llm, memory=memory, verbose=False)
        
        print(f"本地模型加载完成，耗时: {time.time() - start_time:.2f}秒")
        model_type = "local"
        online_manager = None

# 初始化本地资料库管理器
docs_manager = LocalDocsManager()

# print("DEEPSEEK_API_KEY:", os.getenv("DEEPSEEK_API_KEY"))

def main():
    print("中文论文助手已启动")
    print("提示：输入 'local' 查看本地资料库，输入 'stats' 查看统计信息")
    print("输入 'context' 查看上下文统计，输入 'clear' 清空对话历史，输入 'all' 展示所有匹配论文")

    last_local_results = []  # 用于存储最近一次检索结果

    while True:
        query = input("请问：")
        if query.strip().lower() in ["exit", "quit"]:
            break
        
        if query.strip().lower() == "local":
            print("\n=== 本地资料库 ===")
            categories = docs_manager.list_categories()
            if categories:
                for category in categories:
                    print(f"\n【{category}】")
                    docs = docs_manager.list_documents(category)
                    for doc in docs:
                        print(f"  - {doc['title']}")
                        print(f"    来源: {doc['source']}")
                        print(f"    网址: {doc['url']}")
                        print(f"    长度: {doc['content_length']}字")
            else:
                print("资料库为空")
            print()
            continue
        
        if query.strip().lower() == "stats":
            print("\n=== 资料库统计 ===")
            stats = docs_manager.get_stats()
            print(f"总文档数: {stats['total_docs']}")
            print(f"总字数: {stats['total_size']}")
            print("分类统计:")
            for category, count in stats['categories'].items():
                print(f"  {category}: {count} 篇")
            print()
            continue
        
        if query.strip().lower() == "context":
            print("\n=== 上下文统计 ===")
            context_stats = context_manager.get_context_stats()
            print(f"对话历史长度: {context_stats['history_length']}")
            print(f"话题关键词数量: {context_stats['topic_keywords_count']}")
            print(f"实体提及数量: {context_stats['entity_mentions_count']}")
            print(f"主要话题关键词: {', '.join(context_stats['top_keywords'])}")
            print(f"主要实体: {', '.join(context_stats['top_entities'])}")
            print()
            continue
        
        if query.strip().lower() == "clear":
            context_manager.clear_history()
            if memory is not None:
                memory.clear()
            print("对话历史已清空")
            continue

        if query.strip().lower() == "all":
            if last_local_results:
                print("\n=== 所有匹配论文 ===")
                for i, doc in enumerate(last_local_results, 1):
                    print(f"\n{i}. 标题：{doc['title']}")
                    print(f"   分类：{doc['category']}")
                    print(f"   来源：{doc['source']}")
                    print(f"   网址：{doc['url']}")
                    print(f"   摘要：{doc['content']}")
                print("\n—— 完 ——")
            else:
                print("没有可展示的匹配论文，请先进行一次检索。")
            continue

        if len(query.strip()) < 2:
            print("输入过短，请重新提问。")
            continue

        # 记录开始时间
        query_start_time = time.time()
        print(f"\n开始处理查询: {time.strftime('%H:%M:%S')}")

        # 使用上下文管理器增强查询
        enhanced_query = context_manager.enhance_query_with_context(query)
        print(f"增强后的查询: {enhanced_query[:100]}...")

        # 优先从本地资料库搜索（使用增强的查询）
        print("开始本地资料库搜索...")
        local_start_time = time.time()
        local_results = docs_manager.search_documents(enhanced_query, top_k=10)
        last_local_results = local_results  # 存储本次检索结果
        local_time = time.time() - local_start_time
        print(f"本地搜索完成，耗时: {local_time:.2f}秒")
        
        if local_results:
            print(f"找到 {len(local_results)} 个相关本地文档")
            # 拼接最多3段摘要
            snippets = [doc["content"][:200] for doc in local_results[:3]]
            snippet = "\n\n".join(snippets)
            source_url = f"本地资料库: {local_results[0]['title']} (来源: {local_results[0]['source']}, 网址: {local_results[0]['url']})"
        else:
            print("本地未找到相关内容，开始抓取网页...")
            web_start_time = time.time()
            docs = fetch_web_documents(enhanced_query)  # 使用增强的查询
            web_time = time.time() - web_start_time
            print(f"网页抓取完成，耗时: {web_time:.2f}秒")
            
            if not docs:
                print("未找到网页内容。")
                continue

            print("开始向量化处理...")
            vector_start_time = time.time()
            chunks = split_documents(docs)
            vectorstore = embed_documents(chunks)
            retriever = vectorstore.as_retriever()
            relevant_docs = retriever.invoke(enhanced_query)[:3]  # 使用增强的查询
            vector_time = time.time() - vector_start_time
            print(f"向量检索完成，耗时: {vector_time:.2f}秒")

            if not relevant_docs:
                print(" 未找到匹配段落。")
                continue

            # 拼接最多3段摘要
            snippets = [doc.page_content[:200] for doc in relevant_docs]
            snippet = "\n\n".join(snippets)
            source_url = getattr(relevant_docs[0].metadata, "source", "(未知来源)")
            # last_local_results 不更新（只展示本地检索结果）
            
            # 自动保存到本地资料库
            print("正在保存到本地资料库...")
            try:
                # 从原始文档中获取更多信息
                original_doc = docs[0]  # 取第一个文档
                title = getattr(original_doc.metadata, "title", f"关于{query}的搜索结果")
                content = original_doc.page_content
                
                # 尝试从URL推断分类
                category = "其他"
                if "arxiv" in source_url.lower():
                    category = "AI"
                elif "pubmed" in source_url.lower() or "ncbi" in source_url.lower():
                    category = "医学"
                elif "nature" in source_url.lower() or "science" in source_url.lower():
                    category = "科学"
                
                # 添加到本地资料库
                docs_manager.add_document(
                    title=title,
                    content=content,
                    source="网页抓取",
                    url=source_url,
                    category=category
                )
                print(f"已保存到本地资料库 (分类: {category})")
            except Exception as e:
                print(f"保存到本地资料库失败: {e}")

        # 使用上下文管理器创建具有上下文感知的 Prompt
        print("开始模型推理...")
        model_start_time = time.time()
        prompt = context_manager.create_context_aware_prompt(query, snippet)

        if model_type == "online":
            # 使用在线模型
            try:
                result_data = online_manager.generate_response(prompt, max_tokens=512)
                if result_data["success"]:
                    result = result_data["response"]
                    model_time = result_data["time"]
                    print(f"在线模型推理完成，耗时: {model_time:.2f}秒")
                else:
                    print(f"在线模型调用失败: {result_data['error']}")
                    result = "抱歉，在线模型暂时不可用，请稍后重试。"
                    model_time = time.time() - model_start_time
            except Exception as e:
                print(f"在线模型调用异常: {e}")
                result = "抱歉，在线模型暂时不可用，请稍后重试。"
                model_time = time.time() - model_start_time
        else:
            # 使用本地模型
            inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
            
            import torch
            with torch.no_grad():  # 减少显存占用，加速推理
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=128,  #生成长度
                    do_sample=True,     # False 的报错可以忽略
                    eos_token_id=tokenizer.eos_token_id,
                    pad_token_id=tokenizer.eos_token_id
                )
            result = tokenizer.decode(outputs[0], skip_special_tokens=True)
            model_time = time.time() - model_start_time
            print(f"本地模型推理完成，耗时: {model_time:.2f}秒")

        # 更新上下文管理器
        context_manager.add_conversation_turn(query, result)
        
        # 更新对话历史
        if memory is not None:
            memory.chat_memory.add_user_message(query)
            memory.chat_memory.add_ai_message(result)

        total_time = time.time() - query_start_time#
        print(f"\n总耗时: {total_time:.2f}秒")#
        # 清理输出文本，确保没有乱码
        def clean_text(text):
            if not text:
                return text
            # 移除或替换可能导致乱码的字符
            text = text.replace('\xa0', ' ')  # 不间断空格
            text = text.replace('\u200b', '')  # 零宽空格
            text = text.replace('\u200c', '')  # 零宽非连接符
            text = text.replace('\u200d', '')  # 零宽连接符
            # 确保文本是可打印的
            try:
                text = text.encode('utf-8', errors='ignore').decode('utf-8')
            except:
                pass
            return text

        print("\n回答：", clean_text(result))
        if local_results:
            print("\n=== 本次检索返回的前三篇论文 ===")
            for i, doc in enumerate(local_results[:3], 1):
                print(f"\n{i}. 标题：{doc['title']}")
                print(f"   分类：{doc['category']}")
                print(f"   来源：{doc['source']}")
                print(f"   网址：{doc['url']}")
                print(f"   摘要：{doc['content']}")
        else:
            print(f"来源：{clean_text(source_url)}")
        print("\n—— 完 ——")

if __name__ == "__main__":
    main()


