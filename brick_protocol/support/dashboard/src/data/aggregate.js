// 수신 측 집계 재계산: buildings/detail(사실) → 파생 합계.
// 발행은 "그 빌딩만" 보내니, byDisplay·부하·links 같은 합계는 여기서 다시 센다.
// dashboard_export(파이썬)의 집계와 같은 규칙. (seed 받을 때 packet 의 파이썬 집계와 대조해 드리프트 감지 가능.)

export const DISP_ORDER = [
  'running', 'closure_pending', 'archived_stale', 'stopped', 'review', 'incomplete', 'closed', 'unknown',
]

export function recompute(packet) {
  if (!packet) return packet
  const buildings = packet.buildings || []
  const detail = packet.detail || {}

  const byDisplay = Object.fromEntries(DISP_ORDER.map((k) => [k, 0]))
  const byState = {}
  for (const b of buildings) {
    if (b.disp in byDisplay) byDisplay[b.disp] += 1
    else byDisplay.unknown += 1
    if (b.state) byState[b.state] = (byState[b.state] || 0) + 1
  }
  const stalePending = byDisplay.archived_stale || 0

  // 프로젝트별 카운트 (라벨·방향성은 seed 의 projects 에서, 없으면 id)
  // 선언된 동네는 빌딩 0개여도 자리를 유지한다(seed 의 projects 가 사실).
  const projMap = {}
  for (const p of packet.projects || []) {
    projMap[p.id] = {
      id: p.id, label: p.label || p.id, direction: p.direction, total: 0,
      counts: Object.fromEntries(DISP_ORDER.map((k) => [k, 0])), stalePending: 0,
    }
  }
  for (const b of buildings) {
    const id = b.project
    const p = projMap[id] || (projMap[id] = {
      id, label: id, total: 0,
      counts: Object.fromEntries(DISP_ORDER.map((k) => [k, 0])), stalePending: 0,
    })
    p.total += 1
    if (b.disp in p.counts) p.counts[b.disp] += 1
    else p.counts.unknown += 1
    if (b.disp === 'archived_stale') p.stalePending += 1
  }

  // 에이전트 부하 (안 닫힌 빌딩의 currentAgent) — 명단은 packet.agents 유지
  const load = {}
  for (const b of buildings) {
    if (b.state !== 'closed' && b.currentAgent) load[b.currentAgent] = (load[b.currentAgent] || 0) + 1
  }
  const agents = (packet.agents || []).map((a) => ({ ...a, load: load[a.id] || 0 }))

  // 링크 집계
  const movement = {}, dispositions = {}
  for (const b of buildings) {
    if (b.movement) movement[b.movement] = (movement[b.movement] || 0) + 1
    if (b.dispositionOwner) dispositions[b.dispositionOwner] = (dispositions[b.dispositionOwner] || 0) + 1
  }
  const fan = { fan_in_buildings: 0, fan_in_points: 0, fan_out_buildings: 0, fan_out_points: 0 }
  for (const v of Object.values(detail)) {
    const gi = (v.groups || []).filter((g) => g.group_role === 'fan_in')
    const go = (v.groups || []).filter((g) => g.group_role === 'fan_out')
    if (gi.length) { fan.fan_in_buildings += 1; fan.fan_in_points += gi.length }
    if (go.length) { fan.fan_out_buildings += 1; fan.fan_out_points += go.length }
  }

  return {
    ...packet,
    summary: {
      ...(packet.summary || {}),
      projects: Object.keys(projMap).length,
      buildings: buildings.length,
      byState, byDisplay, stalePending,
    },
    projects: Object.values(projMap),
    agents,
    links: { movement, dispositions, fan },
  }
}

// 빌딩 델타 1건을 packet 에 적용 (서버·클라 공용 규칙). 집계는 건드리지 않음(recompute 가 담당).
// 키 = (project, building_id) 복합: 같은 building_id 가 두 동네에 있어도 서로 못 덮는다.
// 레거시(델타에 building_key 없음 / 행에 key 없음)는 building_id 단독 키로 동작 유지.
export function buildingKeyOf(b) {
  if (!b) return ''
  return b.key || (b.project ? b.project + '/' + b.id : b.id)
}
export function applyDelta(packet, delta) {
  const base = packet || { buildings: [], detail: {} }
  const deltaKey = delta.building_key || delta.building_id
  // 레거시 델타(building_key 없음)는 레거시 행(key/project 없는 행)만 지운다 —
  // 프로젝트 키가 붙은 행을 id 단독으로 지우면 동네 간 클로버(S5-FIX: 같은 id가
  // 두 동네에 있을 때 레거시 델타 하나가 전 동네 행을 갈아치웠다).
  const hits = delta.building_key
    ? (b) => buildingKeyOf(b) === deltaKey
    : (b) => !(b.key || b.project) && b.id === delta.building_id
  const buildings = (base.buildings || []).filter((b) => !hits(b))
  if (!delta.removed && delta.building) buildings.push(delta.building)
  const detailEntries = { ...(base.detail || {}) }
  if (delta.removed) delete detailEntries[deltaKey]
  else if (delta.detail) detailEntries[deltaKey] = delta.detail
  return { ...base, buildings, detail: detailEntries, generatedAt: delta.generatedAt || base.generatedAt }
}
