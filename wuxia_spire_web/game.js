const cards = [
  { name: '直刺', cost: 1, type: 'attack', value: 6, text: '造成6点伤害' },
  { name: '回风掌', cost: 1, type: 'attack', value: 8, text: '造成8点伤害' },
  { name: '护体', cost: 1, type: 'skill', value: 5, text: '获得5点格挡' },
  { name: '运气', cost: 0, type: 'skill', value: 1, text: '抽1张牌' },
  { name: '聚气', cost: 1, type: 'skill', value: 1, text: '本回合额外+1点真气' },
  { name: '青龙摆尾', cost: 2, type: 'attack', value: 16, text: '造成16点伤害' },
  { name: '八卦护心', cost: 1, type: 'skill', value: 10, text: '获得10点格挡' },
  { name: '点穴', cost: 1, type: 'attack', value: 10, text: '造成10点伤害' },
  { name: '丹田吐纳', cost: 1, type: 'skill', value: 2, text: '抽2张牌' },
  { name: '破甲掌', cost: 1, type: 'attack', value: 7, text: '造成7点伤害；敌人攻击时额外+5' },
  { name: '飞燕回身', cost: 0, type: 'skill', value: 4, text: '获得4点格挡' },
  { name: '雷火珠', cost: 2, type: 'attack', value: 20, text: '造成20点伤害' },
];

const relics = [
  { name: '温玉佩', text: '每回合开始获得2点格挡' },
  { name: '铜钱剑穗', text: '战斗胜利额外获得20金币' },
  { name: '太极图', text: '每场战斗首次出牌额外+1真气' },
];

const mapPlan = [
  { floor: 1, type: 'fight', label: '山道遭遇', icon: '⚔' },
  { floor: 2, type: 'fight', label: '破庙夜战', icon: '⚔' },
  { floor: 3, type: 'event', label: '江湖奇遇', icon: '❖' },
  { floor: 4, type: 'fight', label: '黑店疑云', icon: '⚔' },
  { floor: 5, type: 'elite', label: '强敌守关', icon: '☯' },
  { floor: 6, type: 'event', label: '山中机缘', icon: '❖' },
  { floor: 7, type: 'fight', label: '血刀追杀', icon: '⚔' },
  { floor: 8, type: 'elite', label: '武林宿敌', icon: '☯' },
  { floor: 9, type: 'event', label: '古寺问心', icon: '❖' },
  { floor: 10, type: 'boss', label: '东厂督主', icon: '👑' },
];

const state = {
  difficulty: 'easy',
  floorIndex: 0,
  player: null,
  enemy: null,
  deck: [],
  drawPile: [],
  discardPile: [],
  hand: [],
  energy: 3,
  enemyIntent: null,
  logs: [],
  draggedCardId: null,
  firstCardBonus: false,
};

const $ = (id) => document.getElementById(id);
let nextCardId = 1;
const clone = (card) => ({ ...card, id: `card-${nextCardId++}` });
const shuffle = (items) => items.sort(() => Math.random() - 0.5);
const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

function showScreen(id) {
  ['start-screen', 'map-screen', 'combat-screen', 'reward-screen', 'event-screen', 'result-screen']
    .forEach((screen) => $(screen).classList.toggle('hidden', screen !== id));
}

function setupDifficultyButtons() {
  document.querySelectorAll('.difficulty').forEach((button) => {
    button.addEventListener('click', () => {
      state.difficulty = button.dataset.difficulty;
      document.querySelectorAll('.difficulty').forEach((b) => b.classList.remove('selected'));
      button.classList.add('selected');
    });
  });
}

function newPlayer() {
  const baseHp = state.difficulty === 'easy' ? 80 : 72;
  const starter = [cards[0], cards[0], cards[0], cards[1], cards[2], cards[2], cards[3], cards[4]];
  state.deck = starter.map(clone);
  return { hp: baseHp, maxHp: baseHp, block: 0, gold: 99, relics: [{ name: '初入江湖', text: '无特殊效果' }] };
}

function startRun() {
  state.floorIndex = 0;
  state.player = newPlayer();
  state.logs = ['少侠踏入江湖。'];
  renderMap();
  showScreen('map-screen');
}

function difficultyMultiplier() {
  return { easy: 0.9, normal: 1, hard: 1.15 }[state.difficulty];
}

function scaled(value) {
  return Math.max(1, Math.floor(value * difficultyMultiplier()));
}

function makeEnemy(floor) {
  if (floor < 4) return { name: '山贼', hp: scaled(30 + floor * 4), maxHp: scaled(30 + floor * 4), pattern: [['attack', scaled(6)], ['block', scaled(5)]], turn: 0 };
  if (floor < 7) return { name: '黑店掌柜', hp: scaled(48 + floor * 5), maxHp: scaled(48 + floor * 5), pattern: [['attack', scaled(9)], ['attack', scaled(12)], ['block', scaled(8)]], turn: 0 };
  if (floor < 10) return { name: '血刀客', hp: scaled(70 + floor * 6), maxHp: scaled(70 + floor * 6), pattern: [['attack', scaled(14)], ['block', scaled(10)], ['attack', scaled(16)]], turn: 0 };
  return { name: '东厂督主', hp: scaled(160), maxHp: scaled(160), pattern: [['attack', scaled(18)], ['block', scaled(14)], ['attack', scaled(24)], ['block', scaled(10)]], turn: 0 };
}

function renderMap() {
  $('map-stats').innerHTML = statsPills();
  $('map').innerHTML = mapPlan.map((node, index) => {
    const cls = index < state.floorIndex ? 'cleared' : index === state.floorIndex ? 'available' : '';
    return `<button class="map-node ${cls}" data-index="${index}" ${index === state.floorIndex ? '' : 'disabled'}>
      <span class="icon">${node.icon}</span>
      <span class="floor">第${node.floor}层</span>
      <span>${node.label}</span>
    </button>`;
  }).join('');
  document.querySelectorAll('.map-node.available').forEach((node) => node.addEventListener('click', enterNode));
}

function statsPills() {
  return `<span class="pill">生命 ${state.player.hp}/${state.player.maxHp}</span>
    <span class="pill">金币 ${state.player.gold}</span>
    <span class="pill">卡组 ${state.deck.length}</span>
    <span class="pill">遗物 ${state.player.relics.length}</span>`;
}

function enterNode() {
  const node = mapPlan[state.floorIndex];
  if (node.type === 'event') {
    resolveEvent(node);
    return;
  }
  startCombat(node);
}

function resolveEvent(node) {
  const events = [
    () => { state.player.maxHp += 6; state.player.hp += 6; return '老道传功：最大生命+6。'; },
    () => { const delta = Math.random() < 0.5 ? -30 : 50; state.player.gold = Math.max(0, state.player.gold + delta); return `黑市赌局：金币变化 ${delta}。`; },
    () => { state.player.hp = Math.min(state.player.maxHp, state.player.hp + 12); return '药师问诊：回复12点生命。'; },
  ];
  const text = events[Math.floor(Math.random() * events.length)]();
  state.logs.push(`第${node.floor}层：${text}`);
  $('event-title').textContent = node.label;
  $('event-description').textContent = text;
  $('event-continue').onclick = completeFloor;
  showScreen('event-screen');
}

function startCombat(node) {
  state.enemy = makeEnemy(node.floor);
  state.player.block = 0;
  state.energy = 3;
  state.drawPile = shuffle([...state.deck]);
  state.discardPile = [];
  state.hand = [];
  state.firstCardBonus = hasRelic('太极图');
  $('floor-label').textContent = `第 ${node.floor} 层`;
  $('encounter-title').textContent = node.label;
  $('enemy-name').textContent = state.enemy.name;
  state.logs = [`遭遇 ${state.enemy.name}。`];
  startTurn();
  showScreen('combat-screen');
}

function hasRelic(name) {
  return state.player.relics.some((relic) => relic.name === name);
}

function startTurn() {
  state.energy = 3;
  state.player.block = hasRelic('温玉佩') ? 2 : 0;
  state.enemyIntent = nextEnemyIntent();
  draw(5);
  addLog(`敌人意图：${intentText(state.enemyIntent)}。`);
  renderCombat();
}

function nextEnemyIntent() {
  const intent = state.enemy.pattern[state.enemy.turn % state.enemy.pattern.length];
  state.enemy.turn += 1;
  return { type: intent[0], value: intent[1] };
}

function intentText(intent) {
  return intent.type === 'attack' ? `攻击 ${intent.value}` : `蓄势回血 ${Math.floor(intent.value / 2)}`;
}

function draw(count) {
  for (let i = 0; i < count; i += 1) {
    if (state.drawPile.length === 0) {
      state.drawPile = shuffle(state.discardPile.splice(0));
    }
    const card = state.drawPile.pop();
    if (card) state.hand.push(card);
  }
}

function renderCombat() {
  $('combat-stats').innerHTML = statsPills();
  $('player-bars').innerHTML = bars(state.player.hp, state.player.maxHp, state.player.block);
  $('enemy-bars').innerHTML = bars(state.enemy.hp, state.enemy.maxHp, 0);
  $('enemy-intent').textContent = intentText(state.enemyIntent);
  $('energy-pill').textContent = `真气 ${state.energy}/3`;
  $('draw-pill').textContent = `牌库 ${state.drawPile.length}`;
  $('discard-pill').textContent = `弃牌 ${state.discardPile.length}`;
  $('battle-log').innerHTML = state.logs.slice(-8).map((line) => `<p>· ${line}</p>`).join('');
  renderHand();
}

function bars(hp, maxHp, block) {
  const hpPct = clamp((hp / maxHp) * 100, 0, 100);
  return `<div>生命 ${hp}/${maxHp}</div><div class="bar hp"><span style="width:${hpPct}%"></span></div>
    <div>格挡 ${block}</div><div class="bar block"><span style="width:${clamp(block * 5, 0, 100)}%"></span></div>`;
}

function renderHand() {
  $('hand').innerHTML = state.hand.map((card) => cardHtml(card, card.cost > state.energy)).join('');
  document.querySelectorAll('.card.in-hand').forEach((el) => {
    el.addEventListener('click', () => playCard(el.dataset.id));
    el.addEventListener('dragstart', (event) => {
      state.draggedCardId = el.dataset.id;
      event.dataTransfer.setData('text/plain', el.dataset.id);
    });
  });
}

function cardHtml(card, disabled = false) {
  const typeLabel = card.type === 'attack' ? '攻击' : '技能';
  return `<button class="card in-hand ${disabled ? 'disabled' : ''}" draggable="true" data-id="${card.id}">
    <span class="cost">${card.cost}</span>
    <h3>${card.name}</h3>
    <p>${card.text}</p>
    <div class="type">${typeLabel}</div>
  </button>`;
}

function playCard(cardId, zone = null) {
  const index = state.hand.findIndex((card) => card.id === cardId);
  if (index < 0) return;
  const card = state.hand[index];
  if (card.cost > state.energy) {
    addLog(`${card.name} 真气不足。`);
    renderCombat();
    return;
  }
  if (zone === 'enemy' && card.type !== 'attack') return;
  if (zone === 'player' && card.type === 'attack') return;

  if (state.firstCardBonus) {
    state.energy += 1;
    state.firstCardBonus = false;
    addLog('太极图流转：本场首次出牌+1真气。');
  }

  state.energy -= card.cost;
  state.hand.splice(index, 1);
  if (card.type === 'attack') {
    let damage = card.value;
    if (card.name === '破甲掌' && state.enemyIntent.type === 'attack') damage += 5;
    state.enemy.hp -= damage;
    addLog(`${card.name} 命中，造成 ${damage} 点伤害。`);
  } else if (card.name === '运气') {
    draw(1);
    addLog('运气：抽1张牌。');
  } else if (card.name === '丹田吐纳') {
    draw(2);
    addLog('丹田吐纳：抽2张牌。');
  } else if (card.name === '聚气') {
    state.energy += 1;
    addLog('聚气：额外获得1点真气。');
  } else {
    state.player.block += card.value;
    addLog(`${card.name}：获得 ${card.value} 点格挡。`);
  }
  state.discardPile.push(card);
  if (state.enemy.hp <= 0) {
    winCombat();
    return;
  }
  renderCombat();
}

function endTurn() {
  state.discardPile.push(...state.hand.splice(0));
  if (state.enemyIntent.type === 'attack') {
    const damage = Math.max(0, state.enemyIntent.value - state.player.block);
    state.player.hp -= damage;
    addLog(`${state.enemy.name} 攻击，造成 ${damage} 点伤害。`);
  } else {
    const heal = Math.floor(state.enemyIntent.value / 2);
    state.enemy.hp = Math.min(state.enemy.maxHp, state.enemy.hp + heal);
    addLog(`${state.enemy.name} 蓄势调息，回复 ${heal} 点生命。`);
  }
  if (state.player.hp <= 0) {
    endRun(false);
    return;
  }
  startTurn();
}

function winCombat() {
  const floor = mapPlan[state.floorIndex].floor;
  let gold = 25 + floor * 3 + (state.difficulty === 'hard' ? 10 : 0);
  if (hasRelic('铜钱剑穗')) gold += 20;
  state.player.gold += gold;
  state.logs.push(`击败 ${state.enemy.name}，获得 ${gold} 金币。`);
  if ([5, 8].includes(floor)) {
    const relic = relics[Math.floor(Math.random() * relics.length)];
    state.player.relics.push(relic);
    state.logs.push(`获得遗物：${relic.name}。`);
  }
  if (floor % 2 === 0) {
    showCardReward();
  } else {
    completeFloor();
  }
}

function showCardReward() {
  $('reward-options').innerHTML = shuffle(cards.slice(5)).slice(0, 3).map((card, index) => {
    const copy = clone(card);
    return `<button class="card reward-card" data-index="${index}">
      <span class="cost">${copy.cost}</span><h3>${copy.name}</h3><p>${copy.text}</p><div class="type">加入卡组</div>
    </button>`;
  }).join('');
  const optionData = [...$('reward-options').querySelectorAll('.reward-card')].map((el) => {
    const name = el.querySelector('h3').textContent;
    return cards.find((card) => card.name === name);
  });
  document.querySelectorAll('.reward-card').forEach((el) => {
    el.addEventListener('click', () => {
      const selected = optionData[Number(el.dataset.index)];
      state.deck.push(clone(selected));
      state.logs.push(`选择卡牌：${selected.name}。`);
      completeFloor();
    });
  });
  $('skip-card').onclick = completeFloor;
  showScreen('reward-screen');
}

function completeFloor() {
  state.floorIndex += 1;
  if (state.floorIndex >= mapPlan.length) {
    endRun(true);
    return;
  }
  renderMap();
  showScreen('map-screen');
}

function endRun(win) {
  $('result-title').textContent = win ? '名震江湖！' : '败走江湖';
  $('result-summary').innerHTML = `<p>生命：${Math.max(0, state.player.hp)}/${state.player.maxHp}</p>
    <p>金币：${state.player.gold}</p>
    <p>卡组：${state.deck.length} 张</p>
    <p>遗物：${state.player.relics.map((r) => r.name).join('、')}</p>`;
  showScreen('result-screen');
}

function addLog(line) {
  state.logs.push(line);
}

function setupDragAndDrop() {
  document.querySelectorAll('.drop-zone').forEach((zone) => {
    zone.addEventListener('dragover', (event) => {
      event.preventDefault();
      zone.classList.add('drag-over');
    });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', (event) => {
      event.preventDefault();
      zone.classList.remove('drag-over');
      const cardId = event.dataTransfer.getData('text/plain') || state.draggedCardId;
      playCard(cardId, zone.dataset.zone);
      state.draggedCardId = null;
    });
  });
}

function boot() {
  setupDifficultyButtons();
  setupDragAndDrop();
  $('start-run').addEventListener('click', startRun);
  $('end-turn').addEventListener('click', endTurn);
  $('restart').addEventListener('click', () => showScreen('start-screen'));
}

boot();
