from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import json
import os
from random import choice
from typing import List, Dict  # 用于类型注解


@register("hero_picker", "YourName", "随机抽取各位置LOL英雄及阵容插件", "1.1.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 定义位置优先级配置：(指令名, 文件名, JSON键名, 显示名, 优先级)
        self.position_configs = [
            ("上单", "sd.json", "上单", "上单", 4),    # 优先级最高(4)
            ("中单", "zd.json", "中单", "中单", 3),
            ("AD", "xl.json", "下路", "下路AD", 2),
            ("打野", "dy.json", "打野", "打野", 1),
            ("辅助", "fz.json", "辅助", "辅助", 0)     # 优先级最低(0)
        ]

    async def initialize(self):
        """插件初始化"""
        logger.info("LOL英雄抽取插件已初始化")

    def _get_hero_list(self, file_name: str, key: str) -> List[str]:
        """获取指定位置的英雄列表（工具方法）"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(current_dir, file_name)
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get(key, [])
        except Exception as e:
            logger.error(f"获取{file_name}中{key}英雄列表失败: {str(e)}")
            return []

    async def _pick_hero(self, event: AstrMessageEvent, file_name: str, key: str, position_name: str):
        """通用单位置英雄抽取方法"""
        user_name = event.get_sender_name()
        try:
            heroes = self._get_hero_list(file_name, key)
            if not heroes:
                yield event.plain_result(f"未找到可用的{position_name}英雄列表哦~")
                return
            
            picked_hero = choice(heroes)
            yield event.plain_result(f"随机抽取的{position_name}英雄是：{picked_hero}")
        
        except FileNotFoundError:
            yield event.plain_result(f"未找到{file_name}文件，请检查文件是否在插件目录下~")
        except json.JSONDecodeError:
            yield event.plain_result(f"{file_name}文件格式错误，无法解析~")
        except Exception as e:
            logger.error(f"抽取{position_name}英雄时发生错误：{str(e)}")
            yield event.plain_result(f"抽取失败，请稍后再试~")

    @filter.command("上单")
    async def pick_top(self, event: AstrMessageEvent):
        async for result in self._pick_hero(event, "sd.json", "上单", "上单"):
            yield result

    @filter.command("AD")
    async def pick_ad(self, event: AstrMessageEvent):
        async for result in self._pick_hero(event, "xl.json", "下路", "下路AD"):
            yield result

    @filter.command("辅助")
    async def pick_support(self, event: AstrMessageEvent):
        async for result in self._pick_hero(event, "fz.json", "辅助", "辅助"):
            yield result

    @filter.command("打野")
    async def pick_jungle(self, event: AstrMessageEvent):
        async for result in self._pick_hero(event, "dy.json", "打野", "打野"):
            yield result

    @filter.command("中单")
    async def pick_mid(self, event: AstrMessageEvent):
        async for result in self._pick_hero(event, "zd.json", "中单", "中单"):
            yield result

    @filter.command("随机阵容")
    async def pick_team(self, event: AstrMessageEvent):
        """随机抽取完整阵容（5个位置），处理重复英雄（低优先级重抽）"""
        user_name = event.get_sender_name()
        max_attempts = 100  # 最大尝试次数，避免死循环
        team = []  # 存储最终阵容：[(位置名, 英雄名, 优先级), ...]

        try:
            # 按优先级从高到低抽取（上单→中单→下路→打野→辅助）
            for cmd, file, key, display_name, priority in self.position_configs:
                hero_list = self._get_hero_list(file, key)
                if not hero_list:
                    yield event.plain_result(f"@{user_name} 未找到可用的{display_name}英雄列表，无法组成阵容~")
                    return

                attempts = 0
                picked_hero = None
                # 抽取当前位置英雄，确保不与已选高优先级英雄重复
                while attempts < max_attempts:
                    candidate = choice(hero_list)
                    # 检查是否与已选英雄重复（只对比英雄名）
                    if candidate not in [h[1] for h in team]:
                        picked_hero = candidate
                        break
                    attempts += 1

                if not picked_hero:
                    yield event.plain_result(f"尝试{max_attempts}次后仍无法为{display_name}找到不重复的英雄，请重试~")
                    return

                team.append((display_name, picked_hero, priority))
                logger.info(f"已抽取{display_name}英雄: {picked_hero}")

            # 生成阵容回复文本
            reply = f"随机阵容已生成：\n"
            for pos, hero, _ in team:
                reply += f"- {pos}：{hero}\n"
            yield event.plain_result(reply.strip())

        except Exception as e:
            logger.error(f"生成随机阵容时发生错误：{str(e)}")
            yield event.plain_result(f"阵容生成失败，请稍后再试~")

    async def terminate(self):
        """插件销毁"""
        logger.info("LOL英雄抽取插件已停用")