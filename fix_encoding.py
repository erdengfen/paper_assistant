# fix_encoding.py - 编码修复工具
import os
import json
from pathlib import Path
from local_docs_manager import LocalDocsManager

def check_and_fix_encoding():
    """检查并修复本地资料库的编码问题"""
    docs_manager = LocalDocsManager()
    
    print("=== 编码检查和修复工具 ===")
    
    # 检查索引文件
    index_file = docs_manager.docs_dir / "docs_index.json"
    if index_file.exists():
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            print("✓ 索引文件编码正常")
        except UnicodeDecodeError as e:
            print(f"✗ 索引文件编码错误: {e}")
            return
        except Exception as e:
            print(f"✗ 索引文件读取错误: {e}")
            return
    
    # 检查所有文档文件
    print("\n检查文档文件...")
    fixed_count = 0
    
    for doc_id, doc_info in docs_manager.docs_index.items():
        file_path = Path(doc_info["file_path"])
        if not file_path.exists():
            print(f"✗ 文件不存在: {file_path}")
            continue
        
        try:
            # 尝试用UTF-8读取
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否有乱码字符
            has_garbled = False
            for char in content:
                if ord(char) > 127 and not '\u4e00' <= char <= '\u9fff':  # 非ASCII且非中文
                    if char not in ['\n', '\r', '\t', ' ', '.', ',', '!', '?', ';', ':', '"', "'", '(', ')', '[', ']', '{', '}']:
                        has_garbled = True
                        break
            
            if has_garbled:
                print(f"✗ 发现乱码: {doc_info['title']}")
                
                # 尝试修复
                try:
                    # 尝试不同编码读取
                    encodings = ['gbk', 'gb2312', 'big5', 'utf-8-sig', 'latin-1']
                    fixed_content = None
                    
                    for encoding in encodings:
                        try:
                            with open(file_path, 'r', encoding=encoding) as f:
                                temp_content = f.read()
                            
                            # 检查修复后的内容是否正常
                            if temp_content and not any(ord(c) > 127 and not '\u4e00' <= c <= '\u9fff' for c in temp_content[:100]):
                                fixed_content = temp_content
                                break
                        except:
                            continue
                    
                    if fixed_content:
                        # 重新保存为UTF-8
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(fixed_content)
                        
                        # 更新索引中的内容长度
                        doc_info["content_length"] = len(fixed_content)
                        docs_manager._save_index()
                        
                        print(f"✓ 已修复: {doc_info['title']}")
                        fixed_count += 1
                    else:
                        print(f"✗ 无法修复: {doc_info['title']}")
                        
                except Exception as e:
                    print(f"✗ 修复失败: {doc_info['title']}, 错误: {e}")
            else:
                print(f"✓ 正常: {doc_info['title']}")
                
        except UnicodeDecodeError as e:
            print(f"✗ 编码错误: {doc_info['title']}, 错误: {e}")
            
            # 尝试修复编码错误
            try:
                encodings = ['gbk', 'gb2312', 'big5', 'utf-8-sig', 'latin-1']
                fixed_content = None
                
                for encoding in encodings:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            fixed_content = f.read()
                        break
                    except:
                        continue
                
                if fixed_content:
                    # 重新保存为UTF-8
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(fixed_content)
                    
                    # 更新索引
                    doc_info["content_length"] = len(fixed_content)
                    docs_manager._save_index()
                    
                    print(f"✓ 已修复编码: {doc_info['title']}")
                    fixed_count += 1
                else:
                    print(f"✗ 无法修复编码: {doc_info['title']}")
                    
            except Exception as e:
                print(f"✗ 修复编码失败: {doc_info['title']}, 错误: {e}")
        
        except Exception as e:
            print(f"✗ 读取错误: {doc_info['title']}, 错误: {e}")
    
    print(f"\n=== 修复完成 ===")
    print(f"总共修复了 {fixed_count} 个文档")
    
    if fixed_count > 0:
        print("建议重新运行主程序测试效果")

def clean_text_content():
    """清理文本内容中的特殊字符"""
    docs_manager = LocalDocsManager()
    
    print("=== 文本内容清理工具 ===")
    
    cleaned_count = 0
    
    for doc_id, doc_info in docs_manager.docs_index.items():
        file_path = Path(doc_info["file_path"])
        if not file_path.exists():
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 清理特殊字符
            original_content = content
            content = content.replace('\xa0', ' ')  # 不间断空格
            content = content.replace('\u200b', '')  # 零宽空格
            content = content.replace('\u200c', '')  # 零宽非连接符
            content = content.replace('\u200d', '')  # 零宽连接符
            content = content.replace('\ufeff', '')  # BOM标记
            
            # 移除多余的空白字符
            content = '\n'.join(line.strip() for line in content.split('\n') if line.strip())
            
            if content != original_content:
                # 重新保存
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # 更新索引
                doc_info["content_length"] = len(content)
                docs_manager._save_index()
                
                print(f"✓ 已清理: {doc_info['title']}")
                cleaned_count += 1
                
        except Exception as e:
            print(f"✗ 清理失败: {doc_info['title']}, 错误: {e}")
    
    print(f"\n=== 清理完成 ===")
    print(f"总共清理了 {cleaned_count} 个文档")

def main():
    print("编码修复工具")
    print("1. 检查并修复编码问题")
    print("2. 清理文本内容")
    print("3. 退出")
    
    choice = input("\n请选择操作 (1-3): ").strip()
    
    if choice == "1":
        check_and_fix_encoding()
    elif choice == "2":
        clean_text_content()
    elif choice == "3":
        print("退出")
    else:
        print("无效选择")

if __name__ == "__main__":
    main() 