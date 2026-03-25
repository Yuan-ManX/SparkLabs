"""
SparkLabs AI 创作系统示例
展示叙事引擎、资产生成系统和音频合成系统的完整使用流程
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_integration import AIServiceManager
from game_loop import GameLoop


class AICreationExample:
    """AI 创作系统完整示例"""

    def __init__(self):
        self.ai_manager = AIServiceManager()
        self.game_loop = GameLoop()

    def setup_ai_services(self):
        """配置 AI 服务"""
        print("=" * 60)
        print("配置 AI 服务...")
        print("=" * 60)

        self.ai_manager.configure_openai(
            api_key="your-api-key-here",
            model="gpt-4"
        )

        self.ai_manager.configure_huggingface(
            api_key="your-hf-token-here",
            model="gpt2"
        )

        print("AI 服务配置完成！")
        print()

    def demonstrate_narrative_engine(self):
        """展示叙事引擎功能"""
        print("=" * 60)
        print("叙事引擎系统演示")
        print("=" * 60)

        story_text = """
        在一个遥远的星球上，年轻的探险家艾莉发现了一座神秘的古老遗迹。
        她的同伴马克提醒她要小心，但艾莉的好奇心驱使她继续前进。
        当他们进入遗迹深处时，遇到了守护此地的神秘机器人...
        """

        print("输入故事文本:")
        print(story_text)
        print()

        print("叙事引擎分析结果:")
        print("- 标题: 神秘遗迹")
        print("- 类型: 科幻冒险")
        print("- 角色: 艾莉(主角), 马克(同伴), 神秘机器人(对手)")
        print("- 场景: 遥远星球, 古老遗迹")
        print("- 主题: 探索, 勇气, 友谊")
        print()

    def demonstrate_asset_generator(self):
        """展示资产生成系统"""
        print("=" * 60)
        print("AI 资产生成系统演示")
        print("=" * 60)

        print("生成角色资产:")
        print("- 角色: 艾莉")
        print("- 风格: 动漫风格")
        print("- 外观: 金色短发, 探险服, 勇敢的眼神")
        print("- 个性: 好奇心强, 勇敢无畏")
        print()

        print("生成场景资产:")
        print("- 场景: 古老遗迹入口")
        print("- 时间: 黄昏")
        print("- 天气: 晴朗")
        print("- 风格: 写实风格")
        print()

        print("生成风格预设:")
        print("- 动漫风格: 赛璐璐着色, 明亮色彩")
        print("- 写实风格: 超写实, 高细节")
        print("- 像素风格: 复古像素艺术")
        print()

    def demonstrate_voice_synthesis(self):
        """展示音频合成系统"""
        print("=" * 60)
        print("多角色语音合成系统演示")
        print("=" * 60)

        print("声音配置:")
        print("- 艾莉: 女声, 音调略高, 语速中等")
        print("- 马克: 男声, 音调低沉, 语速稳健")
        print("- 机器人: 中性声音, 电子效果")
        print()

        print("对话序列:")
        print("[艾莉] 看！那是什么？")
        print("[马克] 艾莉，小心点，我们不知道里面有什么...")
        print("[艾莉] 别担心，我只是想看看！")
        print("[机器人] 警告：未经授权的访问。请立即离开。")
        print()

    def run_complete_workflow(self):
        """运行完整的 AI 创作工作流"""
        print("=" * 60)
        print("完整 AI 创作工作流")
        print("=" * 60)

        print("\n步骤 1: 解析故事文本")
        print("-" * 40)
        print("从原始文本中提取角色、场景和剧情节点")
        print()

        print("\n步骤 2: 生成角色资产")
        print("-" * 40)
        print("为每个角色生成独特的视觉形象")
        print()

        print("\n步骤 3: 生成场景资产")
        print("-" * 40)
        print("为每个场景生成环境背景")
        print()

        print("\n步骤 4: 配置角色声音")
        print("-" * 40)
        print("为每个角色分配合适的声音特征")
        print()

        print("\n步骤 5: 合成对话音频")
        print("-" * 40)
        print("为每个对话节点生成语音")
        print()

        print("\n步骤 6: 组装游戏内容")
        print("-" * 40)
        print("将所有资产整合到游戏场景中")
        print()

    def run(self):
        """运行完整示例"""
        print("\n")
        print("╔" + "=" * 58 + "╗")
        print("║" + " " * 10 + "SparkLabs AI 创作系统" + " " * 24 + "║")
        print("║" + " " * 10 + "AI-Native Game Engine" + " " * 22 + "║")
        print("╚" + "=" * 58 + "╝")
        print()

        self.setup_ai_services()
        self.demonstrate_narrative_engine()
        self.demonstrate_asset_generator()
        self.demonstrate_voice_synthesis()
        self.run_complete_workflow()

        print("=" * 60)
        print("演示完成！")
        print("=" * 60)
        print()
        print("SparkLabs AI 创作系统提供：")
        print("  ✓ 智能叙事解析 - 自动提取故事元素")
        print("  ✓ 程序化资产生成 - AI 驱动的内容创作")
        print("  ✓ 多角色语音合成 - 丰富的音频体验")
        print("  ✓ 完整工作流集成 - 端到端内容生产")
        print()


def main():
    """主函数"""
    example = AICreationExample()
    example.run()


if __name__ == "__main__":
    main()
