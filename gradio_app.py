import gradio as gr
from app import context_manager, docs_manager, memory, model_type, tokenizer, model, online_manager, fetch_web_documents, split_documents, embed_documents
import torch
import webbrowser

def clean_text(text):
    if not text:
        return text
    text = text.replace('\xa0', ' ')
    text = text.replace('\u200b', '')
    text = text.replace('\u200c', '')
    text = text.replace('\u200d', '')
    try:
        text = text.encode('utf-8', errors='ignore').decode('utf-8')
    except:
        pass
    return text

# 全局变量用于存储最近一次检索结果
global_last_local_results = []

def academic_assistant(query, action, last_answer, net_only):
    global global_last_local_results
    output = ""
    extra = ""
    if action == "local":
        categories = docs_manager.list_categories()
        if categories:
            for category in categories:
                output += f"\n【{category}】\n"
                docs = docs_manager.list_documents(category)
                for doc in docs:
                    output += f"- {doc['title']}\n  来源: {doc['source']}\n  网址: {doc['url']}\n  长度: {doc['content_length']}字\n"
        else:
            output = "资料库为空"
        return gr.update(value=last_answer), output, last_answer
    elif action == "context":
        context_stats = context_manager.get_context_stats()
        output = (
            f"对话历史长度: {context_stats['history_length']}\n"
            f"话题关键词数量: {context_stats['topic_keywords_count']}\n"
            f"实体提及数量: {context_stats['entity_mentions_count']}\n"
            f"主要话题关键词: {', '.join(context_stats['top_keywords'])}\n"
            f"主要实体: {', '.join(context_stats['top_entities'])}"
        )
        return gr.update(value=last_answer), output, last_answer
    elif action == "clear":
        context_manager.clear_history()
        if memory is not None:
            memory.clear()
        output = "对话历史已清空"
        global_last_local_results = []
        return gr.update(value=last_answer), output, last_answer
    elif action == "all":
        if global_last_local_results:
            output = "=== 所有匹配论文 ===\n"
            for i, doc in enumerate(global_last_local_results, 1):
                output += f"\n{i}. 标题：{doc['title']}\n   分类：{doc['category']}\n   来源：{doc['source']}\n   网址：{doc['url']}\n   摘要：{doc['content']}\n"
            output += "\n—— 完 ——"
        else:
            output = "没有可展示的匹配论文，请先进行一次检索。"
        return gr.update(value=last_answer), output, last_answer
    # 正常学术问答流程
    if not query or len(query.strip()) < 2:
        return "输入过短，请重新提问。", "", last_answer
    enhanced_query = context_manager.enhance_query_with_context(query)
    if not net_only:
        local_results = docs_manager.search_documents(enhanced_query, top_k=10)
        global_last_local_results = local_results
    else:
        local_results = []
    if local_results:
        snippets = [doc["content"][:200] for doc in local_results[:3]]
        snippet = "\n\n".join(snippets)
        source_url = f"本地资料库: {local_results[0]['title']} (来源: {local_results[0]['source']}, 网址: {local_results[0]['url']})"
    else:
        # 仅网络检索或本地无结果时，直接爬取
        docs = fetch_web_documents(enhanced_query)
        if docs:
            chunks = split_documents(docs)
            vectorstore = embed_documents(chunks)
            retriever = vectorstore.as_retriever()
            relevant_docs = retriever.invoke(enhanced_query)[:3]
            snippets = [doc.page_content[:200] for doc in relevant_docs]
            snippet = "\n\n".join(snippets)
            # 保存网络检索结果到global_last_local_results，结构与本地一致
            global_last_local_results = [
                {
                    'title': doc.metadata.get('title', '(无标题)'),
                    'category': '网络',
                    'source': doc.metadata.get('source', '(未知来源)'),
                    'url': doc.metadata.get('source', ''),
                    'content': doc.page_content
                }
                for doc in relevant_docs
            ]
        else:
            snippet = "未找到相关资料。"
            source_url = ""
            # 不清空global_last_local_results，保留上一次有结果的内容
    prompt = context_manager.create_context_aware_prompt(query, snippet)
    # 推理
    if model_type == "online":
        try:
            result_data = online_manager.generate_response(prompt, max_tokens=512)
            if result_data["success"]:
                result = result_data["response"]
            else:
                result = f"在线模型调用失败: {result_data['error']}"
        except Exception as e:
            result = f"在线模型调用异常: {e}"
    else:
        inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=128,
                do_sample=True,
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.eos_token_id
            )
        result = tokenizer.decode(outputs[0], skip_special_tokens=True)
    # 更新上下文
    context_manager.add_conversation_turn(query, result)
    if memory is not None:
        memory.chat_memory.add_user_message(query)
        memory.chat_memory.add_ai_message(result)
    # 展示前三篇论文
    if local_results:
        extra = "=== 本次检索返回的前三篇论文 ===\n"
        for i, doc in enumerate(local_results[:3], 1):
            extra += f"\n{i}. 标题：{doc['title']}\n   分类：{doc['category']}\n   来源：{doc['source']}\n   网址：{doc['url']}\n   摘要：{doc['content']}\n"
    else:
        if docs and 'relevant_docs' in locals() and relevant_docs:
            extra = "=== 网络检索返回的前三篇资料 ===\n"
            for i, doc in enumerate(relevant_docs, 1):
                meta = doc.metadata
                extra += f"\n{i}. 标题：{meta.get('title', '(无标题)')}\n   来源：{meta.get('source', '(未知来源)')}\n   摘要：{doc.page_content[:100]}\n"
        else:
            extra = source_url
    return clean_text(result), extra, clean_text(result)

with gr.Blocks() as demo:
    gr.Markdown("# 中文学术助手（Web版）\n\n支持本地检索、上下文统计、历史清空、全部论文展示。\n\n")
    with gr.Row():
        query_box = gr.Textbox(label="请输入你的学术问题", lines=2)
    with gr.Row():
        net_only_checkbox = gr.Checkbox(label="仅通过网络爬取获得资料", value=False)
    with gr.Row():
        btn_ask = gr.Button("学术问答")
        btn_local = gr.Button("本地资料库")
        btn_context = gr.Button("上下文统计")
        btn_clear = gr.Button("清空历史")
        btn_all = gr.Button("全部论文")
    with gr.Row():
        answer_box = gr.Markdown(label="学术助手回答")
        extra_box = gr.Markdown(label="论文引用/资料展示")
    state_answer = gr.State("")
    # 事件绑定
    btn_ask.click(academic_assistant, inputs=[query_box, gr.State("ask"), state_answer, net_only_checkbox], outputs=[answer_box, extra_box, state_answer], queue=False)
    btn_local.click(lambda q, last, net: academic_assistant("", "local", last, net), inputs=[query_box, state_answer, net_only_checkbox], outputs=[answer_box, extra_box, state_answer], queue=False)
    btn_context.click(lambda q, last, net: academic_assistant("", "context", last, net), inputs=[query_box, state_answer, net_only_checkbox], outputs=[answer_box, extra_box, state_answer], queue=False)
    btn_clear.click(lambda q, last, net: academic_assistant("", "clear", last, net), inputs=[query_box, state_answer, net_only_checkbox], outputs=[answer_box, extra_box, state_answer], queue=False)
    btn_all.click(lambda q, last, net: academic_assistant("", "all", last, net), inputs=[query_box, state_answer, net_only_checkbox], outputs=[answer_box, extra_box, state_answer], queue=False)

if __name__ == "__main__":
    webbrowser.open("http://127.0.0.1:7860")
    demo.launch()