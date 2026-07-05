#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import yaml
import json
import argparse
import re
import subprocess
from typing import Dict, Any, List

class NovelPipeline:
    def __init__(self, project_dir: str):
        self.project_dir = os.path.abspath(project_dir)
        self.chars_dir = os.path.join(self.project_dir, "大纲", "人物档案")
        self.items_path = os.path.join(self.project_dir, "大纲", "物品表.json")
        self.plot_path = os.path.join(self.project_dir, "大纲", "剧情状态.md")
        self.outline_dir = os.path.join(self.project_dir, "大纲")

    # ================= C. 状态检查与加载 =================
    def load_states(self) -> Dict[str, Any]:
        """从结构化状态库中加载最新状态"""
        states = {"characters": [], "items": [], "plot": ""}
        
        # 1. 加载人物 YAML
        if os.path.exists(self.chars_dir):
            for file in os.listdir(self.chars_dir):
                if file.endswith((".yaml", ".yml")):
                    filepath = os.path.join(self.chars_dir, file)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            char_data = yaml.safe_load(f)
                            if char_data:
                                states["characters"].append(char_data)
                    except Exception as e:
                        print(f"警告: 读取人物档案 {file} 失败: {e}", file=sys.stderr)
                        
        # 2. 加载物品/蛊虫 JSON
        if os.path.exists(self.items_path):
            try:
                with open(self.items_path, "r", encoding="utf-8") as f:
                    states["items"] = json.load(f).get("items", [])
            except Exception as e:
                print(f"警告: 读取物品表失败: {e}", file=sys.stderr)
                
        # 3. 加载滑动窗口剧情
        if os.path.exists(self.plot_path):
            try:
                with open(self.plot_path, "r", encoding="utf-8") as f:
                    states["plot"] = f.read()
            except Exception as e:
                print(f"警告: 读取剧情状态文档失败: {e}", file=sys.stderr)
                
        return states

    # ================= E. 自动校验层 =================
    def validate_chapter(self, file_path: str) -> Dict[str, Any]:
        """执行章节格式、编码、字数、一致性检查"""
        results = {"valid": True, "errors": [], "warnings": []}
        
        # 1. 检查文件是否存在
        if not os.path.exists(file_path):
            results["valid"] = False
            results["errors"].append(f"文件不存在: {file_path}")
            return results
            
        # 2. 检查编码格式
        try:
            with open(file_path, "rb") as f:
                raw_data = f.read()
            raw_data.decode("utf-8")
        except UnicodeDecodeError:
            results["valid"] = False
            results["errors"].append("文件编码非 UTF-8，请转换编码。")
            return results

        # 读取正文
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        # 3. 检查标题格式 (Markdown # 第XXX章-标题)
        lines = content.split("\n")
        if not lines or not re.match(r"^#\s+第[0-9一二三四五六七八九十百千]+章[- ]", lines[0]):
            results["valid"] = False
            results["errors"].append("章节文件头部缺少合规的 Markdown 一级标题 (例如: '# 第001章 穿越与落地' 或 '# 第001章-穿越与落地')")

        # 4. 字数校验 (中文及英文字符数，去空白)
        pure_content = re.sub(r"\s+", "", content)
        char_count = len(pure_content)
        if char_count < 5000:
            results["valid"] = False
            results["errors"].append(f"正文字数不足: 当前 {char_count} 字 (去空白)，要求 >= 5000 字")
        else:
            results["warnings"].append(f"正文字数校验通过: 当前共 {char_count} 字")

        # 5. 截断检测 (检查正文末尾是否有合规标点)
        if not content or not content[-1] in ["。", "”", "！", "？", "…"]:
            results["valid"] = False
            results["errors"].append("正文输出疑似被截断 (末尾没有完整的中文结束标点符号，如 '。'、'”' 等)")

        # 6. 一致性校验：读取当前状态库
        states = self.load_states()
        
        # A级逻辑硬伤：死亡/退场角色发言或出场
        for char in states["characters"]:
            name = char.get("姓名")
            status = char.get("状态", "活跃")
            if not name:
                continue
                
            if status in ["死亡", "退场", "下线"] and name in content:
                # 检查是否仅仅是被提及，还是正在说话或行动
                # 简单的模式匹配：如 "姓名说"、"姓名道"、"姓名[动词]"
                speaking_patterns = [
                    f"{name}说", f"{name}道", f"{name}笑", f"{name}怒",
                    f"{name}冷哼", f"{name}叹", f"{name}点头", f"{name}摇头"
                ]
                is_active = any(p in content for p in speaking_patterns)
                if is_active:
                    results["valid"] = False
                    results["errors"].append(f"逻辑冲突: 角色 '{name}' 的状态为 '{status}'，但本章中其依然有直接的动作或对话。")
                else:
                    results["warnings"].append(f"提及警告: 已退场角色 '{name}' 在正文中被提及，请确认是否为回忆或谈话内容。")

        # B级建议：发现文中出现名字但在人物档案中未注册（常见写错名字、笔误或新角色未建档）
        # 寻找疑似人名：如中文中连续2-3个字符且包含常见姓氏
        common_surnames = "李王张刘陈杨黄赵周吴徐孙马胡朱郭何罗高林罗梁宋郑谢韩唐董萧袁许傅沈曾彭吕苏卢蒋蔡贾丁魏薛叶阎余潘杜戴夏钟汪田任姜范方石廖邹熊陆孟白秦邱侯江尹薛"
        suspected_names = re.findall(rf"([{common_surnames}][\u4e00-\u9fa5]{{1,2}})", content)
        known_names = {char.get("姓名") for char in states["characters"] if char.get("姓名")}
        
        unregistered = set()
        for name in suspected_names:
            if name not in known_names and len(name) >= 2:
                # 过滤掉一些常见干扰词（例如：“这里”、“如果”等）
                common_words = ["如果", "这里", "并且", "只是", "但是", "因为", "所以", "甚至", "突然", "最后", "开始", "然后", "虽然", "觉得", "知道", "发现", "准备"]
                if name not in common_words:
                    unregistered.add(name)
                    
        if unregistered:
            results["warnings"].append(f"未注册角色警告 (可能是笔误或新角色未建档): {list(unregistered)}")

        return results

    # ================= F. 状态自动更新 CLI 接口 =================
    def init_project(self):
        """项目初始化：创建标准结构"""
        paths = [
            os.path.join(self.project_dir, "大纲", "人物档案"),
            os.path.join(self.project_dir, "正文", "审查"),
            os.path.join(self.project_dir, "参考素材"),
            os.path.join(self.project_dir, "地缘格局"),
            os.path.join(self.project_dir, "风格")
        ]
        for p in paths:
            os.makedirs(p, exist_ok=True)
            
        # 自动生成初始物品表
        if not os.path.exists(self.items_path):
            with open(self.items_path, "w", encoding="utf-8") as f:
                json.dump({"items": []}, f, indent=4, ensure_ascii=False)
                
        # 自动生成初始剧情状态文档
        if not os.path.exists(self.plot_path):
            initial_plot = """# 剧情状态文档（滑动窗口）

## 基础信息（固定）
- 项目名：未知
- 当前卷：第一卷
- 当前章节范围：第1-10章

## 主角状态（动态更新）
- 姓名：
- 修为：
- 核心能力/金手指：
- 当前位置：
- 所属势力：
- 经济状况：
- 人际关系网：

## 本段剧情（最近5-10章）
- 当前阶段：
- 核心冲突：
- 情绪基调：
- 已解决的问题：
- 未解决的问题：

## 历史剧情精简（更早的章节）

## 未来伏笔/钩子

## 角色出场表
| 角色 | 首次出场 | 最近出场 | 身份 | 状态 |
|------|---------|---------|------|------|
"""
            with open(self.plot_path, "w", encoding="utf-8") as f:
                f.write(initial_plot)
        print("✅ 项目结构与状态文件初始化完成！")

    def update_character(self, name: str, data_updates: Dict[str, Any]):
        """增量更新或创建人物档案 YAML"""
        os.makedirs(self.chars_dir, exist_ok=True)
        filename = f"{name}.yaml"
        filepath = os.path.join(self.chars_dir, filename)
        
        char_data = {}
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                char_data = yaml.safe_load(f) or {}
                
        # 更新数据
        char_data["姓名"] = name
        for k, v in data_updates.items():
            if v is not None:
                char_data[k] = v
                
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.safe_dump(char_data, f, allow_unicode=True, default_flow_style=False)
        print(f"✅ 人物档案 '{name}' 更新完成！")

    def update_item(self, item_id: str, name: str, item_type: str, rank: int, owner: str, description: str):
        """增量更新或创建物品/蛊虫 JSON"""
        data = {"items": []}
        if os.path.exists(self.items_path):
            try:
                with open(self.items_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass
                
        items_list = data.get("items", [])
        
        # 查找是否存在
        found = False
        for item in items_list:
            if item.get("id") == item_id or (name and item.get("name") == name):
                if name: item["name"] = name
                if item_type: item["type"] = item_type
                if rank is not None: item["rank"] = rank
                if owner is not None: item["owner"] = owner
                if description: item["description"] = description
                found = True
                break
                
        if not found:
            new_item = {
                "id": item_id or f"I{len(items_list) + 1:03d}",
                "name": name,
                "type": item_type or "普通物品",
                "rank": rank or 1,
                "owner": owner or "主角",
                "description": description or ""
            }
            items_list.append(new_item)
            
        data["items"] = items_list
        with open(self.items_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"✅ 物品表更新完成！ (ID: {item_id or name})")

    # ================= G. Git 版本提交 =================
    def git_commit(self, message: str):
        """自动完成版本库提交提交"""
        try:
            # 检查是否有改动
            status_run = subprocess.run(["git", "status", "--porcelain"], cwd=self.project_dir, capture_output=True, text=True)
            if not status_run.stdout.strip():
                print("没有检测到本地文件变动，跳过 Git 提交。")
                return
                
            subprocess.run(["git", "add", "-A"], cwd=self.project_dir, check=True)
            subprocess.run(["git", "commit", "-m", message], cwd=self.project_dir, check=True)
            print("✅ Git 版本库提交成功！")
        except Exception as e:
            print(f"❌ Git 自动提交失败: {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description="小说创作流水线核心调度工具")
    parser.add_argument("--dir", default=".", help="项目根目录")
    
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # init 命令
    subparsers.add_parser("init", help="初始化项目结构")
    
    # validate 命令
    val_parser = subparsers.add_parser("validate", help="校验章节质量与逻辑自洽")
    val_parser.add_argument("--file", required=True, help="章节文件路径")
    
    # update-char 命令
    char_parser = subparsers.add_parser("update-char", help="创建或更新人物档案")
    char_parser.add_argument("--name", required=True, help="人物姓名")
    char_parser.add_argument("--status", choices=["活跃", "死亡", "退场", "下线"], help="人物状态")
    char_parser.add_argument("--修为", help="修为/力量境界")
    char_parser.add_argument("--desc", help="简介/特征描述")
    
    # update-item 命令
    item_parser = subparsers.add_parser("update-item", help="创建或更新物品/蛊虫数据")
    item_parser.add_argument("--name", required=True, help="物品名称")
    item_parser.add_argument("--id", help="物品ID(例如 I001)")
    item_parser.add_argument("--type", help="类别(例如 蛊虫/法宝/丹药)")
    item_parser.add_argument("--rank", type=int, help="品阶/星级")
    item_parser.add_argument("--owner", help="持有者")
    item_parser.add_argument("--desc", help="效果描述")
    
    # commit 命令
    commit_parser = subparsers.add_parser("commit", help="Git 自动打包提交")
    commit_parser.add_argument("--message", required=True, help="提交日志信息")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
        
    pipeline = NovelPipeline(args.dir)
    
    if args.command == "init":
        pipeline.init_project()
        
    elif args.command == "validate":
        res = pipeline.validate_chapter(args.file)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        sys.exit(0 if res["valid"] else 1)
        
    elif args.command == "update-char":
        updates = {}
        if args.status: updates["状态"] = args.status
        if args.修为: updates["修为"] = args.修为
        if args.desc: updates["特征/描述"] = args.desc
        pipeline.update_character(args.name, updates)
        
    elif args.command == "update-item":
        pipeline.update_item(args.id, args.name, args.type, args.rank, args.owner, args.desc)
        
    elif args.command == "commit":
        pipeline.git_commit(args.message)

if __name__ == "__main__":
    main()
