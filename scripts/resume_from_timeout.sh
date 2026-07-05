#!/bin/bash
# 超时恢复脚本
# 用法：./resume_from_timeout.sh <项目路径> <起始章节号>

PROJECT_DIR=${1:-"."}
START_CHAPTER=${2:-1}

echo "=== 超时恢复检测 ==="
echo "项目路径：$PROJECT_DIR"
echo "起始章节：$START_CHAPTER"

# 检测已写完的章节
echo ""
echo "=== 已写完的章节 ==="
for i in $(seq -w $START_CHAPTER 999); do
    FILE="$PROJECT_DIR/正文/第${i}章-*.md"
    if ls $FILE 1> /dev/null 2>&1; then
        # 检查字数
        CHARS=$(wc -m $FILE | awk '{print $1}')
        if [ "$CHARS" -ge 5000 ]; then
            echo "✅ 第${i}章：${CHARS}字"
        else
            echo "⚠️  第${i}章：${CHARS}字（不足5000，需要扩充）"
        fi
    else
        echo "❌ 第${i}章：未找到，从这里继续"
        echo ""
        echo "=== 续写起点 ==="
        echo "从第${i}章开始继续写作"
        exit 0
    fi
done

echo ""
echo "所有章节都已完成！"
