import argparse
import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

DIFFICULTIES = ("easy", "normal", "hard")
DIFFICULTY_LABELS = {"easy": "简单", "normal": "标准", "hard": "困难"}
EVENT_FLOORS = {3, 6, 9}
RELIC_FLOORS = {5, 8}
DEFAULT_FLOORS = 10
HAND_SIZE = 5


@dataclass
class Card:
    name: str
    cost: int
    card_type: str
    value: int
    description: str


@dataclass
class Relic:
    name: str
    description: str


@dataclass
class Player:
    hp: int = 72
    max_hp: int = 72
    energy: int = 3
    block: int = 0
    gold: int = 99
    deck: List[Card] = field(default_factory=list)
    relics: List[Relic] = field(default_factory=list)


@dataclass
class Enemy:
    name: str
    hp: int
    max_hp: int
    pattern: List[Tuple[str, int]]
    turn: int = 0

    def next_action(self) -> Tuple[str, int]:
        action = self.pattern[self.turn % len(self.pattern)]
        self.turn += 1
        return action


def starter_deck() -> List[Card]:
    return [
        Card("直刺", 1, "attack", 6, "造成6点伤害"),
        Card("直刺", 1, "attack", 6, "造成6点伤害"),
        Card("直刺", 1, "attack", 6, "造成6点伤害"),
        Card("回风掌", 1, "attack", 8, "造成8点伤害"),
        Card("护体", 1, "skill", 5, "获得5点格挡"),
        Card("护体", 1, "skill", 5, "获得5点格挡"),
        Card("运气", 0, "skill", 1, "抽1张牌"),
        Card("聚气", 1, "skill", 1, "本回合额外+1点能量"),
    ]


def card_pool() -> List[Card]:
    return [
        Card("青龙摆尾", 2, "attack", 16, "造成16点伤害"),
        Card("八卦护心", 1, "skill", 10, "获得10点格挡"),
        Card("点穴", 1, "attack", 10, "造成10点伤害"),
        Card("丹田吐纳", 1, "skill", 2, "抽2张牌"),
        Card("破甲掌", 1, "attack", 7, "造成7点伤害，若敌人将要攻击则额外+5"),
        Card("飞燕回身", 0, "skill", 4, "获得4点格挡"),
        Card("雷火珠", 2, "attack", 20, "造成20点伤害"),
    ]


def relic_pool() -> List[Relic]:
    return [
        Relic("温玉佩", "每回合开始获得2点格挡"),
        Relic("铜钱剑穗", "战斗胜利额外获得20金币"),
        Relic("太极图", "每场战斗首次出牌额外+1能量"),
    ]


def enemy_for_floor(floor: int, difficulty: str) -> Enemy:
    mult = {"easy": 0.9, "normal": 1.0, "hard": 1.15}[difficulty]

    def scaled(v: int) -> int:
        return max(1, int(v * mult))

    if floor < 4:
        return Enemy(
            "山贼",
            scaled(30 + floor * 4),
            scaled(30 + floor * 4),
            [("attack", scaled(6)), ("block", scaled(5))],
        )
    if floor < 7:
        return Enemy(
            "黑店掌柜",
            scaled(48 + floor * 5),
            scaled(48 + floor * 5),
            [("attack", scaled(9)), ("attack", scaled(12)), ("block", scaled(8))],
        )
    if floor < 10:
        return Enemy(
            "血刀客",
            scaled(70 + floor * 6),
            scaled(70 + floor * 6),
            [("attack", scaled(14)), ("block", scaled(10)), ("attack", scaled(16))],
        )
    return Enemy(
        "东厂督主",
        scaled(160),
        scaled(160),
        [("attack", scaled(18)), ("block", scaled(14)), ("attack", scaled(24)), ("block", scaled(10))],
    )


def draw_cards(
    draw_pile: List[Card],
    discard_pile: List[Card],
    n: int,
    rng: random.Random,
) -> List[Card]:
    hand: List[Card] = []
    for _ in range(n):
        if not draw_pile:
            draw_pile.extend(discard_pile)
            discard_pile.clear()
            rng.shuffle(draw_pile)
        if not draw_pile:
            break
        hand.append(draw_pile.pop())
    return hand


def apply_relic_start_turn(player: Player) -> None:
    for relic in player.relics:
        if relic.name == "温玉佩":
            player.block += 2


def play_card(
    card: Card,
    player: Player,
    enemy: Enemy,
    will_enemy_attack: bool,
    draw_pile: List[Card],
    discard_pile: List[Card],
    rng: random.Random,
) -> None:
    if card.card_type == "attack":
        dmg = card.value
        if card.name == "破甲掌" and will_enemy_attack:
            dmg += 5
        enemy.hp -= dmg
        return

    if card.name == "丹田吐纳":
        extra = draw_cards(draw_pile, discard_pile, card.value, rng)
        discard_pile.extend(extra)
    elif card.name == "聚气":
        player.energy += 1
    else:
        player.block += card.value


def event_room(player: Player, rng: random.Random) -> str:
    event = rng.choice(["老道传功", "黑市赌局", "药师问诊"])
    if event == "老道传功":
        player.max_hp += 6
        player.hp += 6
        return "你遇到老道传功，最大生命+6。"
    if event == "黑市赌局":
        delta = rng.choice([-30, 50])
        player.gold = max(0, player.gold + delta)
        return f"黑市赌局后，你的金币变化 {delta}。"
    player.hp = min(player.max_hp, player.hp + 12)
    return "药师为你施针，回复12点生命。"


def relic_reward(rng: random.Random) -> Relic:
    return rng.choice(relic_pool())


def choose_card_reward(
    options: List[Card],
    chooser: Optional[Callable[[List[Card]], int]],
) -> Card:
    if chooser:
        idx = chooser(options)
        return options[max(0, min(idx, len(options) - 1))]
    # 默认新手友好：优先选择耗能低、收益高的卡，便于自动演示或测试。
    return sorted(options, key=lambda c: (c.cost, -c.value))[0]


def build_summary(
    win: bool,
    floor: int,
    player: Player,
    logs: List[str],
) -> Dict[str, object]:
    return {
        "win": win,
        "floor": floor,
        "hp": player.hp,
        "max_hp": player.max_hp,
        "gold": player.gold,
        "deck_size": len(player.deck),
        "relics": [r.name for r in player.relics],
        "logs": logs,
    }


def run_game(
    seed: Optional[int] = None,
    floors: int = DEFAULT_FLOORS,
    difficulty: str = "normal",
    chooser: Optional[Callable[[List[Card]], int]] = None,
) -> Dict[str, object]:
    if difficulty not in DIFFICULTIES:
        raise ValueError("difficulty must be easy|normal|hard")
    if floors < 1:
        raise ValueError("floors must be greater than 0")

    rng = random.Random(seed)
    player = Player(deck=starter_deck(), relics=[Relic("初入江湖", "无特殊效果")])
    if difficulty == "easy":
        player.hp += 8
        player.max_hp += 8
    logs: List[str] = [f"难度：{difficulty}（{DIFFICULTY_LABELS[difficulty]}）"]

    for floor in range(1, floors + 1):
        if floor in EVENT_FLOORS:
            logs.append(f"第{floor}层奇遇：{event_room(player, rng)}")
            continue

        enemy = enemy_for_floor(floor, difficulty)
        draw_pile = player.deck[:]
        rng.shuffle(draw_pile)
        discard_pile: List[Card] = []
        first_card_bonus = any(r.name == "太极图" for r in player.relics)

        while enemy.hp > 0 and player.hp > 0:
            player.energy = 3
            player.block = 0
            apply_relic_start_turn(player)
            enemy_action, enemy_val = enemy.next_action()
            hand = draw_cards(draw_pile, discard_pile, HAND_SIZE, rng)

            for card in hand:
                if player.energy < card.cost:
                    continue
                if first_card_bonus:
                    player.energy += 1
                    first_card_bonus = False
                player.energy -= card.cost
                play_card(
                    card,
                    player,
                    enemy,
                    enemy_action == "attack",
                    draw_pile,
                    discard_pile,
                    rng,
                )
                discard_pile.append(card)
                if enemy.hp <= 0:
                    break

            if enemy.hp <= 0:
                break

            if enemy_action == "attack":
                player.hp -= max(0, enemy_val - player.block)
            else:
                enemy.hp = min(enemy.max_hp, enemy.hp + enemy_val // 2)

        if player.hp <= 0:
            logs.append(f"第{floor}层败于{enemy.name}。")
            return build_summary(False, floor, player, logs)

        gain = 25 + floor * 3 + (10 if difficulty == "hard" else 0)
        if any(r.name == "铜钱剑穗" for r in player.relics):
            gain += 20
        player.gold += gain
        logs.append(f"第{floor}层击败{enemy.name}，获得{gain}金币。")

        if floor % 2 == 0:
            options = rng.sample(card_pool(), 3)
            chosen = choose_card_reward(options, chooser)
            player.deck.append(chosen)
            logs.append(f"你在 {', '.join(c.name for c in options)} 中选择了：{chosen.name}。")
        if floor in RELIC_FLOORS:
            rel = relic_reward(rng)
            player.relics.append(rel)
            logs.append(f"获得遗物：{rel.name}（{rel.description}）。")

    return build_summary(True, floors, player, logs)


def render_result(result: Dict[str, object]) -> str:
    outcome = "胜利" if result["win"] else "失败"
    lines = [
        "=== 结果 ===",
        outcome,
        f"层数: {result['floor']} 生命: {result['hp']}/{result['max_hp']} 金币: {result['gold']} 卡组: {result['deck_size']}",
        "遗物: " + "、".join(result["relics"]),
    ]
    lines.extend(f"- {line}" for line in result["logs"])
    return "\n".join(lines)


def prompt(text: str, default: str) -> str:
    raw = input(text).strip()
    return raw or default


def interactive_cli(seed: Optional[int] = None, floors: int = DEFAULT_FLOORS) -> None:
    print("=== 江湖爬塔（新手友好版）===")
    print("输入难度：1 简单 / 2 标准 / 3 困难（默认1）")
    mapping = {"1": "easy", "2": "normal", "3": "hard"}
    difficulty = mapping.get(prompt("> ", "1"), "easy")

    def chooser(options: List[Card]) -> int:
        print("可选卡牌：")
        for i, c in enumerate(options, 1):
            print(f" {i}. {c.name} [耗能{c.cost}] - {c.description}")
        raw = prompt("选择卡牌编号（默认1）> ", "1")
        return int(raw) - 1 if raw.isdigit() else 0

    result = run_game(seed=seed, floors=floors, difficulty=difficulty, chooser=chooser)
    print("\n" + render_result(result))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="中国风爬塔卡牌小游戏（类杀戮尖塔）")
    parser.add_argument("--auto", action="store_true", help="无需交互，自动选择新手友好卡牌")
    parser.add_argument("--seed", type=int, default=None, help="随机种子，便于复现同一局")
    parser.add_argument("--floors", type=int, default=DEFAULT_FLOORS, help="爬塔层数，默认10")
    parser.add_argument(
        "--difficulty",
        choices=DIFFICULTIES,
        default="easy",
        help="自动模式使用的难度，默认easy",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.auto:
        result = run_game(seed=args.seed, floors=args.floors, difficulty=args.difficulty)
        print(render_result(result))
        return
    interactive_cli(seed=args.seed, floors=args.floors)


if __name__ == "__main__":
    main()
