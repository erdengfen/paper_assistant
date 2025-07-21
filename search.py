# search.py - 论文爬虫示例
import requests
from bs4 import BeautifulSoup
import time
from local_docs_manager import LocalDocsManager
from dotenv import load_dotenv
load_dotenv()


class PaperCrawler:
    def __init__(self):
        self.docs_manager = LocalDocsManager()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def crawl_arxiv(self, query: str, max_papers: int = 5):
        """从arXiv爬取论文"""
        print(f"正在从arXiv搜索: {query}")
        
        # arXiv搜索API
        search_url = "http://export.arxiv.org/api/query"
        params = {
            'search_query': f'all:"{query}"',
            'start': 0,
            'max_results': max_papers,
            'sortBy': 'relevance',
            'sortOrder': 'descending'
        }
        
        try:
            response = self.session.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'xml')
            entries = soup.find_all('entry')
            
            for entry in entries:
                title = entry.find('title').text.strip()
                summary = entry.find('summary').text.strip()
                authors = [author.find('name').text for author in entry.find_all('author')]
                published = entry.find('published').text[:10]  # 取日期部分
                url = entry.find('id').text
                
                # 构建内容
                content = f"标题: {title}\n\n作者: {', '.join(authors)}\n\n发表日期: {published}\n\n摘要: {summary}"
                
                # 添加到本地资料库
                self.docs_manager.add_document(
                    title=title,
                    content=content,
                    source="arXiv",
                    url=url,
                    category="AI"  # 可以根据关键词自动分类
                )
                
                print(f"已添加: {title}")
                time.sleep(1)  # 避免请求过快
                
        except Exception as e:
            print(f"爬取arXiv失败: {e}")
    
    def crawl_pubmed(self, query: str, max_papers: int = 5):
        """从PubMed爬取医学论文"""
        print(f"正在从PubMed搜索: {query}")
        
        # PubMed搜索API
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {
            'db': 'pubmed',
            'term': query,
            'retmax': max_papers,
            'retmode': 'json',
            'sort': 'relevance'
        }
        
        try:
            response = self.session.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            
            # 获取论文ID列表
            data = response.json()
            id_list = data['esearchresult']['idlist']
            
            for paper_id in id_list:
                # 获取论文详情
                fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
                fetch_params = {
                    'db': 'pubmed',
                    'id': paper_id,
                    'retmode': 'xml'
                }
                
                fetch_response = self.session.get(fetch_url, params=fetch_params, timeout=10)
                fetch_response.raise_for_status()
                
                soup = BeautifulSoup(fetch_response.content, 'xml')
                article = soup.find('PubmedArticle')
                
                if article:
                    title_elem = article.find('ArticleTitle')
                    title = str(title_elem.text) if title_elem else "未知标题"
                    
                    abstract_elem = article.find('AbstractText')
                    abstract = str(abstract_elem.text) if abstract_elem else "无摘要"
                    
                    authors = []
                    author_list = article.find_all('Author')
                    for author in author_list:
                        last_name = author.find('LastName')
                        first_name = author.find('ForeName')
                        if last_name and first_name:
                            authors.append(f"{str(first_name.text)} {str(last_name.text)}")
                    
                    # 构建内容
                    content = f"标题: {title}\n\n作者: {', '.join(authors)}\n\n摘要: {abstract}"
                    
                    # 添加到本地资料库
                    self.docs_manager.add_document(
                        title=title,
                        content=content,
                        source="PubMed",
                        url=f"https://pubmed.ncbi.nlm.nih.gov/{paper_id}/",
                        category="医学"
                    )
                    
                    print(f"已添加: {title}")
                    time.sleep(1)  # 避免请求过快
                    
        except Exception as e:
            print(f"爬取PubMed失败: {e}")
    
    def crawl_springer_science(self, query: str, max_papers: int = 5):
        """从Springer爬取科学类论文"""
        import os
        api_key = os.getenv("SPRINGER_API_KEY")
        if not api_key:
            print("未检测到Springer API Key，请设置SPRINGER_API_KEY环境变量！")
            return
        print(f"正在从Springer搜索: {query}")
        search_url = "https://api.springernature.com/meta/v2/json"
        params = {
            'q': query,
            'api_key': api_key,
            'p': max_papers
        }
        try:
            response = self.session.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            records = data.get('records', [])
            for rec in records:
                title = rec.get('title', '未知标题')
                abstract = rec.get('abstract', '无摘要')
                authors = rec.get('creators', [])
                author_names = [a.get('creator', '') for a in authors]
                published = rec.get('publicationDate', '')
                url = rec.get('url', [{}])[0].get('value', '')
                content = f"标题: {title}\n\n作者: {', '.join(author_names)}\n\n发表日期: {published}\n\n摘要: {abstract}"
                self.docs_manager.add_document(
                    title=title,
                    content=content,
                    source="Springer",
                    url=url,
                    category="科学"
                )
                print(f"已添加: {title}")
                time.sleep(1)
        except Exception as e:
            print(f"爬取Springer失败: {e}")
    
    def add_manual_paper(self):
        """手动添加论文"""
        print("\n=== 手动添加论文 ===")
        title = input("论文标题: ")
        content = input("论文内容: ")
        source = input("来源期刊/网站: ")
        url = input("网址: ")
        category = input("分类 (AI/医学/其他): ").strip()
        
        if not category:
            category = "其他"
        
        self.docs_manager.add_document(title, content, source, url, category)
        print("论文已添加！")

def main():
    crawler = PaperCrawler()
    
    while True:
        print("\n=== 论文爬虫 ===")
        print("1. 从arXiv爬取AI论文")
        print("2. 从PubMed爬取医学论文")
        print("3. 手动添加论文")
        print("4. 查看本地资料库")
        print("5. 从Springer爬取科学类论文")
        print("6. 退出")
        
        choice = input("\n请选择操作 (1-6): ").strip()
        
        if choice == "1":
            query = input("请输入搜索关键词: ")
            max_papers = int(input("最大爬取数量 (默认5): ") or "5")
            crawler.crawl_arxiv(query, max_papers)
            
        elif choice == "2":
            query = input("请输入搜索关键词: ")
            max_papers = int(input("最大爬取数量 (默认5): ") or "5")
            crawler.crawl_pubmed(query, max_papers)
            
        elif choice == "3":
            crawler.add_manual_paper()
            
        elif choice == "4":
            print("\n=== 本地资料库 ===")
            stats = crawler.docs_manager.get_stats()
            print(f"总文档数: {stats['total_docs']}")
            for category, count in stats['categories'].items():
                print(f"{category}: {count} 篇")
            
            categories = crawler.docs_manager.list_categories()
            if categories:
                category = input(f"\n选择分类查看详情 ({'/'.join(categories)}): ").strip()
                if category in categories:
                    docs = crawler.docs_manager.list_documents(category)
                    for doc in docs:
                        print(f"\n- {doc['title']}")
                        print(f"  来源: {doc['source']}")
                        print(f"  网址: {doc['url']}")
            
        elif choice == "5":
            query = input("请输入搜索关键词: ")
            max_papers = int(input("最大爬取数量 (默认5): ") or "5")
            crawler.crawl_springer_science(query, max_papers)
            
        elif choice == "6":
            print("退出爬虫程序")
            break
            
        else:
            print("无效选择，请重新输入")

if __name__ == "__main__":
    main()
