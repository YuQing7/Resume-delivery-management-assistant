# 💼 秋招/校招投递管理助手 (Job Tracker Qt)

![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)
![GUI Framework](https://img.shields.io/badge/GUI-PyQt6-green.svg)
![Database](https://img.shields.io/badge/database-SQLite3-lightgrey.svg)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows-brightgreen.svg)

**秋招/校招投递管理助手** 是一款专为求职者打造的桌面端高效投递管理工具。基于 Python + PyQt6 开发，采用完全本地化的 SQLite 数据库，帮助你清晰记录每一份投递、动态追踪在线测评（OT）倒计时，告别表格错乱与错过测评的烦恼。

---

## ✨ 核心亮点与功能

- 📊 **投递记录全流程管理**：支持快速添加、编辑、删除投递记录（公司、岗位、投递状态、关联简历版本等）。
- ⏰ **测评倒计时与智能提醒**：
  - 精确显示测评剩余时间（支持以天/小时倒计时）。
  - 根据状态自动高亮颜色（橙色：待完成；红色：紧急/过期）。
  - 内置**紧急测评弹窗提示**，防止遗漏高优先级 OT。
- 📄 **简历版本绑定**：标记每次投递使用的简历版本编号，支持一键便捷查看绑定简历。
- 🔍 **高效检索与筛选**：支持按公司/岗位关键字模糊搜索，支持按投递状态分类筛选。
- 🔒 **纯本地存储，安全隐私**：所有数据均保存在本地 `job_tracker.db` 数据库中，不需要联网，零隐私泄露风险。
- 🎨 **现代化 UI 界面**：基于 PyQt6 打造的简约美观界面，高 DPI 自动适配，支持全局统一字体与交互体验。

---

## 🛠️ 技术栈

- **开发语言**：Python 3.9+
- **GUI 框架**：PyQt6
- **数据持久化**：SQLite 3
- **打包工具**：PyInstaller

---

## 🚀 快速开始（源码运行）

### 1. 环境准备
确保你的电脑已安装 **Python 3.9** 或更高版本。

### 2. 克隆/下载项目并安装依赖
```bash
# 进入项目目录
cd job-tracker-qt

# 安装 PyQt6 依赖包
pip install PyQt6
