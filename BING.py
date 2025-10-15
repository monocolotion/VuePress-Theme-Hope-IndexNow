import requests
import xml.etree.ElementTree as ET
import hashlib
import os
import glob
import json
from datetime import datetime
import time
from urllib.parse import urlparse

class SmartIndexNowSubmitter:
    def __init__(self, storage_dir="sitemap_data", max_history=20):
        self.storage_dir = storage_dir
        self.history_file = os.path.join(storage_dir, "历史提交.txt")
        self.max_history = max_history
        self.settings_file = os.path.join(storage_dir, "Settings.json")
        
        # 创建存储目录
        os.makedirs(storage_dir, exist_ok=True)
        
        # 加载配置
        self.sitemap_url, self.host, self.key = self.load_settings()
        
    def load_settings(self):
        """从Settings.json文件加载配置"""
        default_settings = {
            "sitemap_url": "https://你的域名/sitemap.xml",
            "host": "你的域名",
            "key": "IndexNowKEY"
        }
        
        # 如果配置文件不存在，创建默认配置
        if not os.path.exists(self.settings_file):
            print(f"配置文件不存在，创建默认配置: {self.settings_file}")
            try:
                with open(self.settings_file, 'w', encoding='utf-8') as f:
                    json.dump(default_settings, f, indent=4, ensure_ascii=False)
                print("✓ 默认配置文件已创建，请检查配置是否正确")
            except Exception as e:
                print(f"创建配置文件失败: {e}")
                return default_settings.values()
        
        # 读取配置文件
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            # 检查必要配置项
            sitemap_url = settings.get("sitemap_url", default_settings["sitemap_url"])
            host = settings.get("host", default_settings["host"])
            key = settings.get("key", default_settings["key"])
            
            print(f"✓ 配置加载成功: {host}")
            return sitemap_url, host, key
            
        except Exception as e:
            print(f"读取配置文件失败: {e}，使用默认配置")
            return default_settings.values()
    
    def get_latest_sitemap_file(self):
        """获取最新的本地sitemap文件"""
        sitemap_files = [f for f in os.listdir(self.storage_dir) if f.startswith("sitemap_") and f.endswith(".xml")]
        if not sitemap_files:
            return None
            
        # 按文件名排序（文件名包含日期），返回最新的
        latest_file = sorted(sitemap_files)[-1]
        return os.path.join(self.storage_dir, latest_file)
    
    def get_new_sitemap_filename(self):
        """生成新的sitemap文件名"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.storage_dir, f"sitemap_{timestamp}.xml")
    
    def calculate_hash(self, content):
        """计算内容的SHA-256哈希值"""
        return hashlib.sha256(content).hexdigest()
    
    def download_sitemap(self):
        """下载sitemap.xml文件"""
        try:
            response = requests.get(self.sitemap_url, timeout=10)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            print(f"下载sitemap失败: {e}")
            return None
    
    def save_sitemap(self, content, filename):
        """保存sitemap到本地文件"""
        try:
            with open(filename, 'wb') as f:
                f.write(content)
            print(f"Sitemap已保存到: {filename}")
            return True
        except IOError as e:
            print(f"保存sitemap文件失败: {e}")
            return False
    
    def parse_sitemap_urls(self, xml_content):
        """解析sitemap.xml文件，提取所有URL及其lastmod"""
        urls_data = {}
        try:
            root = ET.fromstring(xml_content)
            
            # 命名空间处理
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            # 查找所有url条目
            for url_entry in root.findall('ns:url', namespace):
                loc_elem = url_entry.find('ns:loc', namespace)
                lastmod_elem = url_entry.find('ns:lastmod', namespace)
                
                if loc_elem is not None:
                    url = loc_elem.text
                    lastmod = lastmod_elem.text if lastmod_elem is not None else None
                    urls_data[url] = lastmod
                
            # 处理嵌套的sitemap索引文件
            for sitemap in root.findall('ns:sitemap/ns:loc', namespace):
                print(f"发现嵌套sitemap: {sitemap.text}")
                # 这里可以添加递归下载嵌套sitemap的逻辑
                
        except ET.ParseError as e:
            print(f"解析XML失败: {e}")
            
        return urls_data
    
    def compare_urls_and_filter_changes(self, current_urls, previous_urls):
        """比较两个URL集合，返回有变化的URL列表"""
        new_urls = []
        changed_urls = []
        deleted_urls = []
        
        # 检查新增和更新的URL
        for url, lastmod in current_urls.items():
            # 如果是新URL
            if url not in previous_urls:
                new_urls.append(url)
                continue
                
            # 如果lastmod字段有变化
            prev_lastmod = previous_urls[url]
            if lastmod != prev_lastmod:
                changed_urls.append(url)
        
        # 检查删除的URL
        for url in previous_urls:
            if url not in current_urls:
                deleted_urls.append(url)
        
        return new_urls, changed_urls, deleted_urls
    
    def submit_to_indexnow(self, urls, batch_size=100):
        """提交URL到IndexNow服务"""
        if not urls:
            print("没有需要提交的URL")
            return True
            
        api_url = "https://api.indexnow.org/indexnow"
        
        total_urls = len(urls)
        successful_batches = 0
        
        print(f"开始提交 {total_urls} 个URL到IndexNow...")
        
        # 分批处理URL，避免单次请求过大
        for i in range(0, total_urls, batch_size):
            batch = urls[i:i+batch_size]
            batch_num = i//batch_size + 1
            total_batches = (total_urls + batch_size - 1) // batch_size
            
            # 构建请求数据
            data = {
                "host": self.host,
                "key": self.key,
                "keyLocation": f"https://{self.host}/{self.key}.txt",
                "urlList": batch
            }
            
            try:
                print(f"提交批次 {batch_num}/{total_batches} ({len(batch)} 个URL)...")
                response = requests.post(api_url, json=data)
                
                if response.status_code == 200:
                    print(f"✓ 批次 {batch_num} 提交成功")
                    successful_batches += 1
                else:
                    print(f"✗ 批次 {batch_num} 提交失败: HTTP {response.status_code} - {response.text}")
                    
                # 避免请求过于频繁
                time.sleep(1)
                
            except requests.exceptions.RequestException as e:
                print(f"✗ 批次 {batch_num} 请求IndexNow API失败: {e}")
        
        success_rate = (successful_batches / total_batches) * 100 if total_batches > 0 else 0
        print(f"提交完成: {successful_batches}/{total_batches} 批次成功 ({success_rate:.1f}%)")
        
        return successful_batches == total_batches
    
    def save_submission_history(self, new_urls, changed_urls, deleted_urls, total_submitted):
        """保存提交历史到文件"""
        # 读取现有历史记录
        history_entries = []
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        entries = content.split('-' * 50 + '\n')
                        for entry in entries:
                            if entry.strip():
                                history_entries.append(entry.strip())
            except Exception as e:
                print(f"读取历史记录失败: {e}")
        
        # 创建新记录
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_entry = f"""提交时间: {current_time}
新增提交: {len(new_urls)}个
"""
        # 添加新增URL详情
        for url in new_urls:
            new_entry += f"  + {url}\n"
        
        new_entry += f"更改提交: {len(changed_urls)}个\n"
        
        # 添加更改URL详情
        for url in changed_urls:
            new_entry += f"  * {url}\n"
        
        new_entry += f"删除路径: {len(deleted_urls)}个\n"
        
        # 添加删除URL详情
        for url in deleted_urls:
            new_entry += f"  - {url}\n"
        
        new_entry += f"总计提交: {total_submitted}个\n"
        
        # 将新记录添加到历史记录列表
        history_entries.append(new_entry)
        
        # 限制记录数量
        if len(history_entries) > self.max_history:
            history_entries = history_entries[-self.max_history:]
        
        # 写入文件
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                f.write(('\n' + '-' * 50 + '\n').join(history_entries))
            
            print(f"✓ 提交记录已保存到: {self.history_file}")
        except Exception as e:
            print(f"保存提交记录失败: {e}")
    
    def cleanup_old_sitemaps(self, keep_count=1):
        """清理旧的sitemap文件，只保留指定数量的最新文件"""
        sitemap_files = glob.glob(os.path.join(self.storage_dir, "sitemap_*.xml"))
        
        # 按修改时间排序，最新的在前面
        sitemap_files.sort(key=os.path.getmtime, reverse=True)
        
        # 删除旧文件，只保留指定数量的最新文件
        if len(sitemap_files) > keep_count:
            for old_file in sitemap_files[keep_count:]:
                try:
                    os.remove(old_file)
                    print(f"已删除旧sitemap文件: {os.path.basename(old_file)}")
                except OSError as e:
                    print(f"删除文件 {old_file} 失败: {e}")
    
    def run(self):
        """主执行流程"""
        print("=" * 50)
        print("智能 IndexNow 提交工具")
        print(f"目标网站: {self.host}")
        print(f"Sitemap地址: {self.sitemap_url}")
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
        # 下载当前sitemap
        print("步骤 1/4: 下载当前sitemap...")
        current_content = self.download_sitemap()
        if not current_content:
            print("❌ 无法获取sitemap，程序退出")
            return False
            
        current_hash = self.calculate_hash(current_content)
        
        # 查找最新的本地sitemap
        print("步骤 2/4: 查找本地sitemap...")
        latest_file = self.get_latest_sitemap_file()
        
        new_urls = []
        changed_urls = []
        deleted_urls = []
        urls_to_submit = []
        
        if latest_file:
            # 读取本地sitemap并计算哈希
            with open(latest_file, 'rb') as f:
                previous_content = f.read()
            previous_hash = self.calculate_hash(previous_content)
            
            # 比较哈希值
            if current_hash == previous_hash:
                print("✓ Sitemap未发生变化，无需处理")
                return True
            else:
                print("✓ 检测到sitemap变化，开始分析具体变更...")
                
                # 解析两个sitemap
                current_urls = self.parse_sitemap_urls(current_content)
                previous_urls = self.parse_sitemap_urls(previous_content)
                
                # 比较URL变化
                new_urls, changed_urls, deleted_urls = self.compare_urls_and_filter_changes(current_urls, previous_urls)
                
                # 合并需要提交的URL
                urls_to_submit = new_urls + changed_urls
                
                print(f"分析结果: {len(new_urls)} 个新URL, {len(changed_urls)} 个更新的URL, {len(deleted_urls)} 个删除的URL")
                
                if deleted_urls:
                    print("删除路径提醒:")
                    for url in deleted_urls[:5]:  # 只显示前5个删除的URL
                        print(f"  - {url}")
                    if len(deleted_urls) > 5:
                        print(f"  ... 还有 {len(deleted_urls) - 5} 个删除的URL")
                
                if not urls_to_submit:
                    print("✓ 没有需要提交的URL (只有删除或无关变更)")
                    # 虽然哈希变化但没有URL需要提交，我们仍然保存新的sitemap
                    new_filename = self.get_new_sitemap_filename()
                    self.save_sitemap(current_content, new_filename)
                    # 清理旧的sitemap文件
                    self.cleanup_old_sitemaps(keep_count=1)
                    return True
        else:
            print("✓ 未找到本地sitemap，将提交所有URL")
            # 首次运行，提交所有URL
            current_urls = self.parse_sitemap_urls(current_content)
            urls_to_submit = list(current_urls.keys())
            new_urls = urls_to_submit  # 首次运行时所有URL都视为新增
            print(f"找到 {len(urls_to_submit)} 个URL")
        
        # 提交到IndexNow
        print("步骤 3/4: 提交到IndexNow...")
        if urls_to_submit:
            success = self.submit_to_indexnow(urls_to_submit)
        else:
            success = True  # 没有URL需要提交也视为成功
            
        # 保存新的sitemap和提交记录
        print("步骤 4/4: 保存新的sitemap和提交记录...")
        new_filename = self.get_new_sitemap_filename()
        save_success = self.save_sitemap(current_content, new_filename)
        
        # 保存提交历史
        if urls_to_submit or deleted_urls:
            total_submitted = len(urls_to_submit)
            self.save_submission_history(new_urls, changed_urls, deleted_urls, total_submitted)
        
        # 清理旧的sitemap文件，只保留最新的一个
        self.cleanup_old_sitemaps(keep_count=1)
        
        if success and save_success:
            print("✅ 处理完成")
        else:
            print("⚠️  处理过程中出现问题，请检查日志")
        
        return success

def main():
    # 创建提交器实例并运行
    submitter = SmartIndexNowSubmitter()
    submitter.run()

if __name__ == "__main__":
    main()