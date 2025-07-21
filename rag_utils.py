# rag_utils.py

import os
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["http_proxy"] = ""
os.environ["https_proxy"] = ""

import requests
requests.sessions.Session.trust_env = False

from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document
from bs4 import BeautifulSoup
from serpapi import GoogleSearch

# 向量嵌入模型
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")

# 分割文档
from langchain.text_splitter import RecursiveCharacterTextSplitter

def split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
    return splitter.split_documents(documents)

# 向量化文档
def embed_documents(docs):
    return Chroma.from_documents(docs, embeddings)

# 搜索网页链接

def search_links(query, max_results=5):
    params = {
        "engine": "google",
        "q": query,  # 不再限定特定网站
        "api_key": "61d940811592115c34435f78a3f24c80fb09b68f40dd918ea7add7818c91132f"
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    return [r["link"] for r in results.get("organic_results", [])[:max_results]]

# 抓取网页正文文本

def extract_text_from_url(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        # 检测编码
        if response.encoding == 'ISO-8859-1':
            response.encoding = response.apparent_encoding
        
        # 确保使用UTF-8编码
        if response.encoding and response.encoding.lower() not in ['utf-8', 'utf8']:
            try:
                response.encoding = 'utf-8'
            except:
                response.encoding = response.apparent_encoding
        
        soup = BeautifulSoup(response.content, "html.parser", from_encoding=response.encoding)
        
        # 提取标题
        title = ""
        title_elem = soup.find("title")
        if title_elem:
            title = title_elem.get_text().strip()
        
        # 提取正文
        paragraphs = soup.find_all("p")
        text_parts = []
        for p in paragraphs:
            p_text = p.get_text().strip()
            if len(p_text) > 20:
                # 清理特殊字符
                p_text = p_text.replace('\xa0', ' ')  # 替换不间断空格
                p_text = p_text.replace('\u200b', '')  # 移除零宽空格
                text_parts.append(p_text)
        
        text = "\n".join(text_parts)
        
        # 最终编码检查
        if not text.isprintable():
            try:
                text = text.encode('utf-8', errors='ignore').decode('utf-8')
            except:
                text = ""
        
        return text, title
    except Exception as e:
        print(f"抓取失败：{url}，错误：{e}")
        return "", ""

# 整合为搜索 + 抓取 + 构建文档

def fetch_web_documents(query):
    links = search_links(query)
    print("搜索到链接：", links)

    if not links:
        print("没有搜索到网页链接，请尝试换个关键词。")
        return []

    # 只过滤掉 PDF
    filtered_links = [link for link in links if not link.endswith(".pdf")]

    if not filtered_links:
        print("没有找到可用网页来源。")
        return []

    documents = []
    for link in filtered_links:
        text, title = extract_text_from_url(link)
        if text.strip():
            print(f"抓取 {link} 的前300字：\n{text[:300]}")
            documents.append(Document(
                page_content=text, 
                metadata={"source": link, "title": title}
            ))
    return documents