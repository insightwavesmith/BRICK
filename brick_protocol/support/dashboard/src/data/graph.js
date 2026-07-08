// 브릭 그래프(detail.bricks + detail.edges) → 깊이별 타임라인 rows 로 투영한다.
// 읽기 전용. 구조(누가 어떤 브릭, fan-out/fan-in)는 building-map 의 사실 그대로 쓰고,
// done/now/wait 는 빌딩 상태 + 프론티어(currentBrick) 로 파생한다(파생임을 화면에 명시).

const isBoundary = (ref) => typeof ref === 'string' && ref.startsWith('building-boundary')

function commonPrefix(names) {
  if (!names.length) return ''
  let p = names[0]
  for (const n of names) while (p && !n.startsWith(p)) p = p.slice(0, -1)
  return p
}

export function buildTimeline(detail, building) {
  if (!detail) return null
  const bricks = detail.bricks || []
  const edges = detail.edges || []
  const byRef = {}
  bricks.forEach((b) => { byRef[b.ref] = b })

  const nodes = new Set(bricks.map((b) => b.ref))
  edges.forEach((e) => { if (e.source) nodes.add(e.source); if (e.target) nodes.add(e.target) })

  const adj = {}, indeg = {}, kindOf = {}
  nodes.forEach((n) => { adj[n] = []; indeg[n] = 0 })
  edges.forEach((e) => {
    if (!(e.source in adj) || !(e.target in indeg)) return
    adj[e.source].push(e.target); indeg[e.target]++
    kindOf[`${e.source}->${e.target}`] = e.kind
  })

  // Kahn 위상정렬 + 최장경로 깊이
  const depth = {}; nodes.forEach((n) => { depth[n] = 0 })
  const ind = { ...indeg }
  const q = [...nodes].filter((n) => ind[n] === 0)
  while (q.length) {
    const n = q.shift()
    for (const m of adj[n]) {
      depth[m] = Math.max(depth[m], depth[n] + 1)
      if (--ind[m] === 0) q.push(m)
    }
  }

  const maxD = Math.max(0, ...Object.values(depth))
  const levels = []
  for (let dd = 0; dd <= maxD; dd++) {
    const ns = [...nodes].filter((n) => depth[n] === dd)
    if (ns.length) levels.push(ns)
  }

  const closed = !!building && building.state === 'closed'
  let frontierDepth = -1
  if (!closed && building && building.currentBrick) {
    const cb = building.currentBrick
    for (const n of nodes) {
      const tail = n.replace(/^brick-/, '')
      if (cb === tail || cb.endsWith(tail) || tail.endsWith(cb)) { frontierDepth = depth[n]; break }
    }
  }

  const realNames = bricks.filter((b) => !isBoundary(b.ref)).map((b) => b.name)
  const pre = commonPrefix(realNames)
  const bid = (building && building.id) || ''
  // 빌딩 id 에서 따온 접두어(이름이 빌딩 id 로 시작하면 그만큼 떼되 하이픈 경계까지)
  const bidPrefixFor = (s) => {
    let k = 0
    while (k < bid.length && k < s.length && bid[k] === s[k]) k++
    while (k > 0 && s[k - 1] !== '-') k--
    return s.slice(0, k)
  }
  const shortName = (b) => {
    if (isBoundary(b.ref)) return '빌딩 닫힘'
    let s = b.name || b.ref
    const candidates = [pre, bidPrefixFor(s)].filter((p) => p && s.startsWith(p))
    const best = candidates.sort((a, c) => c.length - a.length)[0]
    if (best) s = s.slice(best.length)
    return s || b.name || b.ref
  }

  const statusOf = (n) => {
    if (isBoundary(n)) return 'boundary'
    if (closed) return 'done'
    if (frontierDepth < 0) return 'wait'
    if (depth[n] < frontierDepth) return 'done'
    if (depth[n] === frontierDepth) return 'now'
    return 'wait'
  }

  const rows = levels.map((ns) =>
    ns.map((n) => {
      const b = byRef[n] || { ref: n, name: n, agent: '' }
      return { ref: n, name: shortName(b), agent: b.agent || '', boundary: isBoundary(n), status: statusOf(n) }
    })
  )

  const gates = []
  for (let i = 0; i < rows.length - 1; i++) {
    const cur = rows[i].map((c) => c.ref)
    const nxt = rows[i + 1].map((c) => c.ref)
    const kinds = new Set()
    for (const s of cur) for (const t of nxt) { const k = kindOf[`${s}->${t}`]; if (k) kinds.add(k) }
    let label = null
    if (kinds.has('fan_out')) label = '분기 (fan-out)'
    else if (kinds.has('fan_in')) label = '합류 (fan-in)'
    const up = rows[i], dn = rows[i + 1]
    const upDone = up.every((c) => c.status === 'done' || c.status === 'boundary')
    const dnDone = dn.every((c) => c.status === 'done' || c.status === 'boundary')
    const dnNow = dn.some((c) => c.status === 'now')
    let state = 'wait'
    if (closed) state = 'pass'
    else if (upDone && dnDone) state = 'pass'
    else if (upDone && dnNow) state = 'wait'
    gates.push({ label, state })
  }

  return { rows, gates, closed, frontierDepth }
}

// 그래프가 있는 빌딩들 중 가장 보여줄 만한(병렬/합류 있는) 것을 고른다.
export function pickFeatured(detail) {
  const ids = Object.keys(detail || {})
  if (!ids.length) return null
  let best = ids[0], bestScore = -1
  for (const id of ids) {
    const v = detail[id]
    const groups = v.groups || []
    const fan = groups.filter((g) => g.group_role === 'fan_in' || g.group_role === 'fan_out').length
    const score = fan * 100 + (v.bricks || []).length
    if (score > bestScore) { bestScore = score; best = id }
  }
  return best
}
