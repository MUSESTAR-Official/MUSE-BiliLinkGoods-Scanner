import json
import asyncio
import httpx
from datetime import datetime
from typing import Dict, List, Optional
import os
import re
import sys

DATA_FILE = "场贩活动列表.json"
LOG_FILE = "扫描日志.txt"

def get_version():
    try:
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        version_file = os.path.join(base_path, "version_info.txt")
        
        if os.path.exists(version_file):
            with open(version_file, 'r', encoding='utf-8') as f:
                content = f.read()
                match = re.search(r"StringStruct\(u'ProductVersion',\s*u'([^']+)'\)", content)
                if match:
                    return match.group(1)
        
        return "0.0.0"
    except Exception:
        return "未知版本"

def show_muse_banner():
    banner = r"""
          _____                    _____                    _____                    _____          
         /\    \                  /\    \                  /\    \                  /\    \         
        /::\____\                /::\____\                /::\    \                /::\    \        
       /::::|   |               /:::/    /               /::::\    \              /::::\    \       
      /:::::|   |              /:::/    /               /::::::\    \            /::::::\    \      
     /::::::|   |             /:::/    /               /:::/\:::\    \          /:::/\:::\    \     
    /:::/|::|   |            /:::/    /               /:::/__\:::\    \        /:::/__\:::\    \    
   /:::/ |::|   |           /:::/    /                \:::\   \:::\    \      /::::\   \:::\    \   
  /:::/  |::|___|______    /:::/    /      _____    ___\:::\   \:::\    \    /::::::\   \:::\    \  
 /:::/   |::::::::\    \  /:::/____/      /\    \  /\   \:::\   \:::\    \  /:::/\:::\   \:::\    \ 
/:::/    |:::::::::\____\|:::|    /      /::\____\/::\   \:::\   \:::\____\/:::/__\:::\   \:::\____\
\::/    / ~~~~~/:::/    /|:::|____\     /:::/    /\:::\   \:::\   \::/    /\:::\   \:::\   \::/    /
 \/____/      /:::/    /  \:::\    \   /:::/    /  \:::\   \:::\   \/____/  \:::\   \:::\   \/____/ 
             /:::/    /    \:::\    \ /:::/    /    \:::\   \:::\    \       \:::\   \:::\    \     
            /:::/    /      \:::\    /:::/    /      \:::\   \:::\____\       \:::\   \:::\____\    
           /:::/    /        \:::\__/:::/    /        \:::\  /:::/    /        \:::\   \::/    /    
          /:::/    /          \::::::::/    /          \:::\/:::/    /          \:::\   \/____/     
         /:::/    /            \::::::/    /            \::::::/    /            \:::\    \         
        /:::/    /              \::::/    /              \::::/    /              \:::\____\        
        \::/    /                \::/____/                \::/    /                \::/    /        
         \/____/                  ~~                       \/____/                  \/____/         
    """
    print(banner)
    version = get_version()
    print(f"MUSE-BiliLinkGoods-Scanner v{version}")
    print("=" * 88)
    print()

def get_headers() -> Dict[str, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://show.bilibili.com/",
        "Origin": "https://show.bilibili.com",
        "Connection": "keep-alive"
    }
    return headers

async def get_project_list(page: int = 1, pagesize: int = 20) -> Optional[Dict]:
    try:
        url = f"https://show.bilibili.com/api/ticket/project/listV2?pagesize={pagesize}&area=-1&filter=&platform=web&p_type=%E5%85%A8%E9%83%A8%E7%B1%BB%E5%9E%8B&page={page}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=get_headers())
            
            print(f"获取第 {page} 页活动列表，HTTP状态码: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"获取活动列表HTTP错误: 状态码 {resp.status_code}")
                return None
            
            try:
                data = resp.json()
            except Exception as json_error:
                print(f"获取活动列表JSON解析失败: {str(json_error)}")
                return None
            
            # 检查API返回码
            errno = data.get("errno")
            if errno == 0 and "data" in data:
                print(f"成功获取第 {page} 页活动列表，共 {len(data['data'].get('result', []))} 个活动")
                return data["data"]
            
            print(f"获取活动列表API错误: 错误码 {errno}, 错误信息: {data.get('msg', '未知错误')}")
            return None
            
    except Exception as e:
        print(f"获取活动列表发生错误: {type(e).__name__}: {str(e)}")
        return None

async def get_linkgoods_list(project_id: str) -> Optional[Dict]:
    try:
        url = f"https://show.bilibili.com/api/ticket/linkgoods/list?page_type=0&project_id={project_id}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=get_headers())
            
            if resp.status_code != 200:
                return None
            
            try:
                data = resp.json()
            except Exception:
                return None
            
            # 检查API返回码
            errno = data.get("errno")
            if errno == 0 and "data" in data:
                return data["data"]
            
            return None
            
    except Exception:
        return None

def get_sale_time_status(sale_time_text: str) -> str:
    try:
        if "开始" in sale_time_text:
            return "未开售"
        elif "至" in sale_time_text:
            return "预售中"
        elif "已结束" in sale_time_text:
            return "已售罄"
        else:
            current_time = datetime.now()
            time_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2})-(\d{4}-\d{2}-\d{2} \d{2}:\d{2})', sale_time_text)
            if time_match:
                start_str, end_str = time_match.groups()
                start_datetime = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
                end_datetime = datetime.strptime(end_str, "%Y-%m-%d %H:%M")
                
                if current_time < start_datetime:
                    return "未开售"
                elif start_datetime <= current_time <= end_datetime:
                    return "预售中"
                else:
                    return "已售罄"
            return "未知状态"
    except Exception:
        return "未知状态"

async def get_linkgoods_sale_status(project_id: str) -> str:
    try:
        linkgoods_data = await get_linkgoods_list(project_id)
        if linkgoods_data is None:
            return "未知状态"
        
        goods_list = linkgoods_data.get("list", [])
        if not goods_list:
            return "未知状态"
        
        statuses = set()
        for goods in goods_list:
            sale_flag_txt = goods.get("sale_flag_txt")
            if sale_flag_txt:
                if "未开售" in sale_flag_txt or "即将开售" in sale_flag_txt:
                    statuses.add("未开售")
                elif "预售中" in sale_flag_txt or "售卖中" in sale_flag_txt or "开售" in sale_flag_txt:
                    statuses.add("预售中")
                elif "已售罄" in sale_flag_txt or "售罄" in sale_flag_txt:
                    statuses.add("已售罄")
                else:
                    statuses.add(sale_flag_txt)
            
            spec_list = goods.get("spec_list", [])
            for spec in spec_list:
                ticket_list = spec.get("ticket_list", [])
                for ticket in ticket_list:
                    sale_start = ticket.get("sale_start")
                    sale_end = ticket.get("sale_end")
                    
                    if sale_start and sale_end:
                        sale_time_text = f"{sale_start}-{sale_end}"
                        status = get_sale_time_status(sale_time_text)
                        statuses.add(status)
                    
                    stock_num = ticket.get("num", 0)
                    if stock_num == 0:
                        statuses.add("已售罄")
        
        if "预售中" in statuses:
            return "预售中"
        elif "未开售" in statuses:
            return "未开售"
        elif "已售罄" in statuses:
            return "已售罄"
        elif statuses:
            return list(statuses)[0]
        else:
            return "未知状态"
            
    except Exception as e:
        print(f"检测场贩销售状态失败: {str(e)}")
        return "未知状态"

async def check_project_has_linkgoods(project_id: str) -> bool:
    linkgoods_data = await get_linkgoods_list(project_id)
    
    if linkgoods_data is None:
        return False
    
    # 检查是否有场贩商品
    goods_list = linkgoods_data.get("list", [])
    return len(goods_list) > 0

async def save_linkgoods_project(project_info: Dict, sale_status: str, filter_status: str):
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"scan_time": None, "filter_status": None, "projects": []}
        
        data["scan_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data["filter_status"] = filter_status
        
        project_id = str(project_info["project_id"])
        existing_project = None
        for i, project in enumerate(data["projects"]):
            if str(project["project_id"]) == project_id:
                existing_project = i
                break
        
        project_data = {
            "project_id": project_info["project_id"],
            "project_name": project_info["project_name"],
            "sale_status": sale_status,
            "found_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if existing_project is not None:
            data["projects"][existing_project] = project_data
            print(f"更新项目: {project_info['project_name']} (ID: {project_id}) - 状态: {sale_status}")
        else:
            data["projects"].append(project_data)
            print(f"发现新的场贩活动: {project_info['project_name']} (ID: {project_id}) - 状态: {sale_status}")
        
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
    except Exception as e:
        print(f"保存场贩活动信息失败: {str(e)}")

def log_message(message: str):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
        
        print(message)
    except Exception as e:
        print(f"记录日志失败: {str(e)}")

async def scan_all_projects(filter_status: str):
    log_message(f"开始扫描所有活动的场贩信息... (过滤条件: {filter_status})")
    
    page = 1
    total_projects = 0
    linkgoods_projects = 0
    filtered_projects = 0
    
    while True:
        project_data = await get_project_list(page)
        
        if project_data is None:
            log_message(f"获取第 {page} 页活动列表失败，停止扫描")
            break
        
        projects = project_data.get("result", [])
        
        if not projects:
            log_message(f"第 {page} 页没有活动，扫描完成")
            break
        
        log_message(f"正在扫描第 {page} 页，共 {len(projects)} 个活动")
        
        for project in projects:
            project_id = str(project["project_id"])
            project_name = project["project_name"]
            total_projects += 1
            
            print(f"检查活动: {project_name} (ID: {project_id})")
            
            has_linkgoods = await check_project_has_linkgoods(project_id)
            
            if has_linkgoods:
                linkgoods_projects += 1
                
                sale_status = await get_linkgoods_sale_status(project_id)
                log_message(f"发现场贩活动: {project_name} (ID: {project_id}) - 状态: {sale_status}")
                
                should_save = False
                if filter_status == "全部":
                    should_save = True
                elif filter_status == sale_status:
                    should_save = True
                
                if should_save:
                    filtered_projects += 1
                    await save_linkgoods_project(project, sale_status, filter_status)
                else:
                    print(f"跳过项目 {project_name} (状态: {sale_status}, 不符合过滤条件: {filter_status})")
            
            await asyncio.sleep(1.0)
        
        total_pages = project_data.get("numPages", 0)
        if page >= total_pages:
            log_message(f"已扫描完所有 {total_pages} 页")
            break
        
        page += 1
        await asyncio.sleep(2.0)
    
    log_message(f"扫描完成！共扫描 {total_projects} 个活动，发现 {linkgoods_projects} 个有场贩的活动")
    log_message(f"符合过滤条件 '{filter_status}' 的活动: {filtered_projects} 个")
    log_message(f"结果已保存到: {DATA_FILE}")

async def main():
    show_muse_banner()
    print("本程序将扫描所有B站会员购活动，找出存在场贩的活动")
    print(f"扫描结果将保存到: {DATA_FILE}")
    print(f"扫描日志将保存到: {LOG_FILE}")
    
    print("\n请选择要扫描的场贩销售状态:")
    print("1. 未开售")
    print("2. 预售中")
    print("3. 已售罄")
    print("4. 全部")
    
    while True:
        try:
            choice = input("\n请输入选项 (1-4): ").strip()
            
            if choice == "1":
                filter_status = "未开售"
                break
            elif choice == "2":
                filter_status = "预售中"
                break
            elif choice == "3":
                filter_status = "已售罄"
                break
            elif choice == "4":
                filter_status = "全部"
                break
            else:
                print("无效选项，请输入 1-4 之间的数字")
        except KeyboardInterrupt:
            print("\n\n程序已取消")
            return
        except Exception:
            print("输入错误，请重新输入")
    
    print(f"\n已选择扫描类型: {filter_status}")
    print("开始扫描...\n")
    
    await scan_all_projects(filter_status)
    
    print("\n扫描完成！")
    print(f"请查看 {DATA_FILE} 文件获取扫描结果")

def run_main():
    while True:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\n程序已被用户中断")
        except Exception as e:
            import traceback
            print(f"程序运行出错: {e}")
            print("\n完整错误详情:")
            print(traceback.format_exc())
        
        while True:
            choice = input("\n退出(T)/重新开始(S): ").strip().upper()
            if choice == 'T':
                print("程序已退出")
                return
            elif choice == 'S':
                print("\n重新开始程序...\n")
                break
            else:
                print("请输入 T 或 S")

if __name__ == "__main__":
    run_main()