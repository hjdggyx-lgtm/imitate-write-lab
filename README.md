# 写作训练（imitate-write-lab）

基于 PyQt6 的写作训练工具，通过抄写、默写经典小说原文进行打字与写作手感训练。

## 当前状态

**抄写 / 默写功能已可使用。**

## 下载使用

1. 前往 [Releases](https://gitee.com/hjdgkj/imitate-write-lab/releases) 下载最新 `写作训练-v*.zip`
2. 解压后双击 `写作训练.exe` 即可运行，无需安装 Python 环境
3. 数据文件放 exe 同级目录，整个文件夹可拷贝到任意路径运行，不写注册表 / 系统位置

## 功能

- **抄写练习**：左侧原文区显示原文，右侧复写区跟打，行号对齐、当前行高亮
- **默写练习**：原文按行隐藏，凭记忆默写，支持手动 / 自动两种模式，按字数分档控制显示时间
- **双卡片布局**：原文区 + 复写区，自定义圆角卡片 + 深色主题
- **自动对齐**：复写区写到 2/3 处原文区自动同步上滚
- **字体 / 主题切换**：段首缩进已归一化为全角空格，任意字体下段首恒空两字
- **听写**：高亮行语音播报
- **数据记忆**：每章节复写内容自动保存，切换章节不丢失

## 从源码运行（开发者）

```bash
python writing_train_ui.py
```

依赖：Python 3.13 + PyQt6（+ pygame 用于听写语音）

## 项目结构

```
writing_train_ui.py   主程序（界面 + 逻辑）
training_tool.py      启动入口
core/                 数据读写
ui/                   主题、控件、样式
  widgets.py          OrnateCardFrame / LineNumberWidget / SegmentedToggle 等
  theme.py            深色主题与 QSS
writing_train_data.json   用户练习数据（运行时生成，不入库）
```

## 说明

- 用户练习数据 `writing_train_data.json` 体积较大且为个人数据，已加入 `.gitignore`，不入仓库
- 段首缩进：原文区加载时把段首半角空格归一化为全角空格（2 半角 → 1 全角），保证任意字体下段首缩进恒为两个中文字宽，复写区回车自动插入 `\u3000\u3000` 与之保持一致